# Head First 地基 + 身分橋接 — Stage 1-2

> **"地基打得好，上面蓋幾層都不怕。地基歪了，第三層就開始漏水。"**

這份指南涵蓋 [`002_shop_schema.sql`](../migrations/002_shop_schema.sql) 的 **第 34–192 行**。

打開 SQL 檔案放在旁邊，我們邊看邊學。

---

## 搭配閱讀

| 你在讀的 | SQL 行號 | 學什麼 |
|----------|----------|--------|
| Stage 1：Foundation | 34–71 | ULID、enum types、audit trigger |
| Stage 2：Identity | 74–192 | Auth bridge、profiles、自動註冊 |

---

# Stage 1：Foundation（地基）

> **📖 SQL 第 34–71 行**

## 1.1 Extensions — 先裝工具

打開 SQL 第 42 行，你會看到一行註解：

```sql
-- NOTE: schema, extensions, generate_ulid() 已移至 001_extensions.sql
```

在 `001_extensions.sql` 裡，我們已經啟用了三個 extension：

| Extension | 幹嘛用的 |
|-----------|----------|
| `pgcrypto` | 提供 `gen_random_bytes()`，ULID 需要它產生隨機部分 |
| `moddatetime` | 自動更新 `updated_at` 欄位的 trigger 工具 |
| `pg_trgm` | 三元組（trigram）索引，讓 `LIKE '%關鍵字%'` 也能用 index |

這些 extension 不在 `002_shop_schema.sql` 裡面，但 Stage 1 的所有功能都依賴它們。

> ### 🧠 你的大腦在想…
>
> 「為什麼 extension 要拆到另一個檔案？」
>
> 因為 extension 是**全域**的（database-level），不屬於任何 schema。
> 而且 `CREATE EXTENSION IF NOT EXISTS` 需要 superuser 權限——在 Supabase 上，
> 你得透過 Dashboard 或 migration 來啟用，不能跟業務 schema 混在一起。

---

## 1.2 ULID vs UUID vs BIGINT — 選主鍵

在你建任何表之前，先搞懂這三個選項。這個決定會影響**整個 schema 的每一張表**。

| | ULID | UUID v4 | BIGINT |
|---|---|---|---|
| **長度** | 26 字元（Crockford Base32） | 36 字元（含 `-`） | 8 bytes |
| **排序性** | 時間排序（前 10 碼 = 毫秒時戳） | 隨機，無排序性 | 嚴格遞增 |
| **B-Tree 友善度** | 優秀（新資料追加在尾端） | 差（隨機插入 → page splits） | 最佳 |
| **分散式安全** | 安全（時間 + 隨機 = 極低碰撞） | 安全（128-bit 隨機） | 危險（sequence 碰撞） |
| **可讀性** | 中（`01HXY8Z3K4...`） | 低（`550e8400-e29b-...`） | 高（`42`） |

**我們選 ULID，理由三條**：

1. **B-Tree 友善**：ULID 的前綴是時間戳，新 row 永遠插在 index 尾端，不會造成 page split
2. **分散式安全**：多個 server 同時產生 ID 不會碰撞，未來拆服務不用改 PK 策略
3. **可讀且可排序**：肉眼看得出先後順序，debug 時很方便

> ### 🧠 你的大腦在想…
>
> 「UUID 不是 Supabase 的預設嗎？為什麼要換？」
>
> 是的，`auth.users` 用 UUID——那是 Supabase 管的，我們不碰。
> 但**業務表的 PK 我們自己決定**。UUID v4 的隨機性會造成 B-Tree 的 page split，
> 當資料量到百萬級時，INSERT 效能會明顯下降。
> ULID 保留了「全球唯一」的特性，同時避開了這個問題。

---

## 1.3 Enum Types — 資料庫層的驗證

> **📖 SQL 第 45–53 行**

打開 SQL，你會看到 9 個 enum type：

```sql
-- 第 45 行
do $$ begin
  create type shop.company_type as enum (
    'retailer','wholesaler','manufacturer','distributor'
  );
exception when duplicate_object then null;
end $$;
```

一共定義了這些 enum：

| Enum | 用在哪 | 值 |
|------|--------|-----|
| `company_type` | 公司類型 | retailer, wholesaler, manufacturer, distributor |
| `product_status` | 商品狀態 | draft, publish, archived, trash |
| `product_type` | 商品類型 | physical, digital, virtual, grouped, variable |
| `order_status` | 訂單狀態 | pending → confirmed → processing → shipped → delivered / cancelled / refunded |
| `payment_status` | 付款狀態 | pending → processing → paid / failed / refunded / partially_refunded / cancelled |
| `payment_method` | 付款方式 | credit_card, debit_card, line_pay, apple_pay, google_pay, bank_transfer, cash_on_delivery, points |
| `discount_type` | 折扣類型 | fixed, percentage, free_shipping |
| `movement_reason` | 庫存異動原因 | sale, return, restock, adjustment, manual, transfer |
| `address_label` | 地址標籤 | home, office, shipping, billing, other |

### 為什麼用 enum 不用 varchar + CHECK？

| | Enum | VARCHAR + CHECK |
|---|---|---|
| **驗證層** | 型別層（type-level） | 約束層（constraint-level） |
| **錯誤訊息** | `invalid input value for enum shop.order_status` | `violates check constraint "chk_order_status"` |
| **新增值** | `ALTER TYPE ... ADD VALUE`（需要 migration） | `ALTER TABLE ... DROP/ADD CONSTRAINT`（需要 migration） |
| **跨表共用** | 天然共用（type 是全域的） | 每張表要寫一次 CHECK |
| **儲存空間** | 4 bytes（內部 OID） | 依字串長度而定 |
| **型別安全** | 編譯期檢查（不能塞錯型別） | 執行期檢查（INSERT 時才報錯） |

**結論**：enum 更安全、更省空間、跨表共用不重複。

### 為什麼要用 `do $$ ... exception when duplicate_object` 這個寫法？

```sql
do $$ begin
  create type shop.product_status as enum ('draft','publish','archived','trash');
exception when duplicate_object then null;
end $$;
```

這叫做**冪等 migration（idempotent migration）**。

`CREATE TYPE` 不支援 `IF NOT EXISTS`（不像 `CREATE TABLE`）。如果你跑第二次 migration，
沒有 exception handler 就會直接報錯。用 `exception when duplicate_object then null` 的意思是：

> 「如果這個 type 已經存在了，就當沒事。」

這讓你的 migration 可以**安全地重跑**，不怕重複執行。

> ### 沒有 Dumb Questions ❓
>
> **Q：enum 加新值容易嗎？**
>
> A：加值用 `ALTER TYPE shop.order_status ADD VALUE 'on_hold';`，很簡單。
> 但**刪除值或重新命名**很痛——要建新 type、搬資料、刪舊 type。
> 所以定義 enum 時要想清楚，寧可一開始多放幾個值。
>
> **Q：那 enum 適合放「會經常增減的選項」嗎？**
>
> A：不適合。如果選項會頻繁變動（例如商品標籤），用 `TEXT` + 另一張 lookup table 更好。
> Enum 適合放「穩定的狀態機」——像訂單狀態、付款方式這種很少變動的東西。

---

## 1.4 handle_audit_fields() — 自動填審計欄位

> **📖 SQL 第 56–71 行**

很多表都會有 `created_by` 和 `updated_by` 欄位。你不想每次 INSERT/UPDATE 都手動填——所以用 trigger 自動搞定。

```sql
-- 第 56-71 行
create or replace function shop.handle_audit_fields()
returns trigger
language plpgsql
security definer
set search_path = shop
as $$
begin
  if tg_op = 'INSERT' then
    new.created_by = coalesce(new.created_by, shop.get_current_user_id());
    new.updated_by = coalesce(new.updated_by, shop.get_current_user_id());
  elsif tg_op = 'UPDATE' then
    new.updated_by = coalesce(shop.get_current_user_id(), new.updated_by);
  end if;
  return new;
end;
$$;
```

逐行拆解：

| 行號 | 程式碼 | 解釋 |
|------|--------|------|
| 59 | `security definer` | 用**函式擁有者**的權限執行（通常是 `postgres`），而不是呼叫者的權限 |
| 60 | `set search_path = shop` | 鎖定搜尋路徑，防止 search_path injection 攻擊 |
| 63 | `if tg_op = 'INSERT'` | `tg_op` 是 trigger 特殊變數，告訴你這是 INSERT 還是 UPDATE |
| 64 | `coalesce(new.created_by, shop.get_current_user_id())` | 如果前端有傳 `created_by` 就用前端的，沒有就自動抓當前使用者 |
| 67 | UPDATE 時的 `coalesce` 順序反過來 | UPDATE 時**優先用系統抓到的使用者**，確保 `updated_by` 不被前端覆蓋 |

> ### 🧠 你的大腦在想…
>
> 「INSERT 和 UPDATE 的 coalesce 順序不一樣？」
>
> 對。INSERT 時，你可能是 service_role 幫別人建資料，所以**尊重前端傳入的值**。
> UPDATE 時，你要確保 `updated_by` 是**真正執行操作的人**，所以系統值優先。
>
> 這個微妙的差異很容易被忽略，但它保護了審計紀錄的可信度。

---

# Stage 2：Identity（身分橋接）

> **📖 SQL 第 74–192 行**

---

## 2.1 Auth Bridge Pattern — 為什麼要多一層？

先看問題：

```
Supabase 的 auth.users 用 UUID 當 PK。
我們的業務表用 ULID 當 PK。
型別不一樣，不能直接 FK。
```

就算勉強用 UUID 當 FK，你的業務表就**硬綁死在 Supabase 的 auth 系統**上了。
哪天換認證方式（例如從 Supabase Auth 換到 Clerk），整個 schema 的 FK 都要改。

**解法：Auth Bridge**

```
┌──────────────┐
│  auth.users  │  Supabase 管的，UUID PK
│  (UUID)      │
└──────┬───────┘
       │ auth_user_id (UUID FK)
┌──────▼───────┐
│  shop.users  │  我們的橋接表，ULID PK
│  (ULID)      │
└──────┬───────┘
       │ user_id (TEXT FK)
┌──────▼───────┐
│  所有業務表  │  只認 shop.users.id
└──────────────┘
```

**原則：業務表永遠不直接 reference `auth.users`。**

---

## 2.2 shop.users — 橋接表

> **📖 SQL 第 89–96 行**

```sql
-- 第 89-94 行
create table if not exists shop.users (
  id            text primary key default public.generate_ulid(),
  auth_user_id  uuid unique not null references auth.users(id) on delete cascade,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now()
);

-- 第 96 行
create index if not exists idx_users_auth on shop.users(auth_user_id);
```

只有四個欄位。對，就這麼少。

| 欄位 | 型別 | 說明 |
|------|------|------|
| `id` | `TEXT` (ULID) | 業務世界的主鍵，所有其他表 FK 都指向這裡 |
| `auth_user_id` | `UUID` | 指向 `auth.users(id)`，唯一且不可為空 |
| `created_at` | `TIMESTAMPTZ` | 建立時間 |
| `updated_at` | `TIMESTAMPTZ` | 更新時間 |

`on delete cascade`：當 Supabase 的 auth.users 刪除帳號時，對應的 shop.users 也會自動刪掉。

第 96 行的 index `idx_users_auth` 很重要——`get_current_user_id()` 每次都要用 `auth_user_id` 查詢，沒 index 就是全表掃描。

> ### 沒有 Dumb Questions ❓
>
> **Q：users 表只有兩個「有意義」的欄位，感覺很浪費？**
>
> A：這不是浪費，這是**解耦的代價**。
> 想像你有 20 張業務表，每張都 FK 到 `shop.users.id`。
> 現在 Supabase 改了 auth 系統，或者你想換到另一個認證服務——
> 你只需要改 `shop.users` 這一張表的 `auth_user_id` 欄位。
> 其他 20 張表？完全不用動。
>
> 兩個欄位，換來的是**整個 schema 的穩定性**。
>
> **Q：為什麼不直接把 email、username 這些放在 users 表？**
>
> A：因為那些是 profile 資訊，會變動、會被 UI 查詢、需要 index。
> Bridge 表的職責是**只做橋接**——UUID ↔ ULID 的翻譯。越簡單越好。
> Profile 資訊放在下一張表 `shop.profiles`。

---

## 2.3 get_current_user_id() — 從 UUID 翻譯成 ULID

> **📖 SQL 第 98–109 行**

這是整個系統最常被呼叫的 helper function。

```sql
-- 第 99-107 行
create or replace function shop.get_current_user_id()
returns text
language sql
stable
security definer
set search_path = shop
as $$
  select id from shop.users where auth_user_id = (select auth.uid()) limit 1;
$$;

-- 第 109 行
grant execute on function shop.get_current_user_id() to authenticated;
```

逐行拆解：

| 關鍵字 | 為什麼 |
|--------|--------|
| `language sql` | 純 SQL（不是 plpgsql），PostgreSQL 可以 inline 最佳化 |
| `stable` | 告訴 optimizer：同一個 transaction 內，相同輸入會回傳相同結果——可以被快取 |
| `security definer` | 用函式擁有者的權限執行（能讀 `shop.users`，即使呼叫者沒有直接 SELECT 權限） |
| `set search_path = shop` | 安全鎖定，避免 search_path 被污染 |
| `(select auth.uid())` | 括號很重要！下面解釋 |
| `grant execute ... to authenticated` | 沒有這行，前端呼叫會得到 `permission denied` |

### `(SELECT auth.uid())` vs `auth.uid()` — 一個括號的差異

```sql
-- 寫法 A：沒括號
select id from shop.users where auth_user_id = auth.uid();

-- 寫法 B：有括號
select id from shop.users where auth_user_id = (select auth.uid());
```

兩個寫法結果一樣，但效能天差地遠。

- **寫法 A**：`auth.uid()` 被當成 **correlated subquery**，每一行都呼叫一次
- **寫法 B**：`(SELECT auth.uid())` 被 PostgreSQL 最佳化為 **initPlan**，整個查詢只算一次

在 RLS policy 裡，你的表可能有百萬行。每行都呼叫一次 `auth.uid()` 和只呼叫一次，差距是**百萬倍**。

> ### 🧠 你的大腦在想…
>
> 「就一個括號，效能差百萬倍？」
>
> 真的。你可以用 `EXPLAIN ANALYZE` 驗證——
> 沒括號的版本會在 filter 裡看到 function call，有括號的會看到一個 `InitPlan` 節點。
> 這是 Supabase 官方文件也推薦的寫法。記住它，所有 RLS policy 都要這樣寫。

---

## 2.4 shop.profiles — 使用者資料

> **📖 SQL 第 112–127 行**

```sql
-- 第 112-123 行
create table if not exists shop.profiles (
  id           text primary key references shop.users(id) on delete cascade,
  username     varchar(60)  not null,
  full_name    varchar(250) not null default '',
  display_name varchar(250) not null default '',
  avatar_url   text,
  phone        varchar(50),
  is_staff     boolean      not null default false,
  metadata     jsonb        not null default '{}'::jsonb,
  created_at   timestamptz  not null default now(),
  updated_at   timestamptz  not null default now()
);

-- 第 125-126 行
create unique index if not exists uq_profiles_username on shop.profiles(username);
create index if not exists idx_profiles_metadata on shop.profiles using gin(metadata);
```

**關鍵設計**：

1. **PK 就是 FK**：`id text primary key references shop.users(id)` — 這是 1:1 關係的標準做法。profiles 的 `id` 和 users 的 `id` 完全一樣，不用額外的 `user_id` 欄位。

2. **username 唯一索引**（第 125 行）：用 `CREATE UNIQUE INDEX` 而不是 `UNIQUE` constraint — 效果一樣，但 index 可以加 `WHERE` 條件（partial index），未來彈性更大。

3. **metadata GIN 索引**（第 126 行）：`jsonb` 欄位用 GIN 索引，讓你可以高效查詢 `metadata @> '{"vip": true}'` 這類條件。

> ### 沒有 Dumb Questions ❓
>
> **Q：為什麼不把 email 存在 profiles 裡？**
>
> A：因為 email 已經存在 `auth.users` 裡了。如果你再存一份，就有兩個 source of truth。
> 使用者改了 email，你要同步兩個地方——一定會有 desync 的時候。
>
> 正確做法：需要 email 時，透過 `shop.get_my_email()` function 去 `auth.users` 查。
> 單一來源，零同步風險。

---

## 2.5 handle_new_user() — 自動註冊 trigger

> **📖 SQL 第 129–179 行**

當使用者透過 Supabase Auth 註冊時，我們要自動在 `shop.users` 和 `shop.profiles` 建立對應的資料。

```sql
-- 第 129-174 行
create or replace function shop.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = shop
as $$
declare
  new_user_id text;
  base_username text;
  final_username text;
  suffix int := 0;
begin
  -- 建立橋接記錄
  insert into shop.users (auth_user_id)
  values (new.id)
  returning id into new_user_id;

  -- 產生不會碰撞的 username
  base_username := coalesce(
    new.raw_user_meta_data ->> 'username',
    split_part(new.email, '@', 1)
  );
  final_username := base_username;

  loop
    begin
      insert into shop.profiles (id, username, full_name, display_name)
      values (
        new_user_id,
        final_username,
        coalesce(new.raw_user_meta_data ->> 'full_name', ''),
        coalesce(new.raw_user_meta_data ->> 'display_name',
                 split_part(new.email, '@', 1))
      );
      exit;  -- 成功就跳出 loop
    exception when unique_violation then
      suffix := suffix + 1;
      final_username := base_username || suffix::text;
      if suffix > 100 then
        raise exception 'Could not generate unique username for %', new.email;
      end if;
    end;
  end loop;

  return new;
end;
$$;
```

然後掛上 trigger（第 176–179 行）：

```sql
drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function shop.handle_new_user();
```

### 流程圖解

```
使用者按下「註冊」
       │
       ▼
auth.users INSERT 一筆新資料（UUID PK）
       │
       ▼
trigger 觸發 shop.handle_new_user()
       │
       ├──► INSERT shop.users（產生 ULID，關聯 auth UUID）
       │
       ▼
   取 username（從 raw_user_meta_data 或 email 前綴）
       │
       ▼
   嘗試 INSERT shop.profiles
       │
       ├── 成功 → 完成！
       │
       └── unique_violation（username 重複）
              │
              ▼
         加上數字後綴（alice → alice1 → alice2）
              │
              └── 重試，最多 100 次
```

### username 碰撞處理

為什麼要用 loop + exception 而不是先 SELECT 檢查？

```sql
-- ❌ 不好的做法（race condition）
if not exists (select 1 from shop.profiles where username = base_username) then
  insert into shop.profiles (id, username, ...) values (...);
end if;

-- ✅ 正確做法（optimistic insert + catch）
loop
  begin
    insert into shop.profiles (...) values (...);
    exit;
  exception when unique_violation then
    -- 加後綴重試
  end;
end loop;
```

先 SELECT 再 INSERT 有 race condition：兩個人同時註冊 `alice`，兩個都 SELECT 到「不存在」，然後一個成功一個失敗。

用 `INSERT` + `exception when unique_violation` 是 **optimistic concurrency control**——先試，失敗再調整。
資料庫的 unique index 是最終裁判，不會有 race condition。

---

## 2.6 get_my_email() — 安全取得 email

> **📖 SQL 第 182–192 行**

```sql
-- 第 182-190 行
create or replace function shop.get_my_email()
returns text
language sql
stable
security definer
set search_path = shop
as $$
  select email from auth.users where id = (select auth.uid());
$$;

-- 第 192 行
grant execute on function shop.get_my_email() to authenticated;
```

**為什麼需要這個 function？**

`auth.users` 是 Supabase 的內部表，一般使用者沒有 SELECT 權限。
如果你建一個 view 來暴露 email，RLS 可能會遞迴呼叫自己（因為 view 裡面的查詢也要過 RLS）。

`SECURITY DEFINER` function 完美解決這個問題：
- 用 postgres 的權限讀 `auth.users`（繞過 RLS）
- 但只回傳**當前使用者自己的 email**（因為 `where id = (select auth.uid())`）
- 不會造成 RLS 遞迴

> ### 🧠 你的大腦在想…
>
> 「SECURITY DEFINER 不是很危險嗎？它繞過了所有權限檢查耶。」
>
> 沒錯，所以你要確保三件事：
> 1. `set search_path = shop` — 防止 search_path injection
> 2. 查詢條件鎖定當前使用者 — `where id = (select auth.uid())`
> 3. 只 GRANT 給需要的 role — `grant execute ... to authenticated`
>
> SECURITY DEFINER 不是「壞的」，它是 PostgreSQL 裡**權限提升**的標準做法。
> 就像 Unix 的 `setuid`——關鍵是你在函式裡**只做該做的事**。

---

## 重點子彈 🎯

### Stage 1：Foundation

- [ ] **ULID > UUID > BIGINT**（業務表主鍵）：時間排序、B-Tree 友善、分散式安全
- [ ] **Enum type** 比 `VARCHAR + CHECK` 更安全、更省空間、跨表共用
- [ ] `CREATE TYPE` 不支援 `IF NOT EXISTS`，要用 `do $$ begin ... exception when duplicate_object then null; end $$` 做冪等 migration
- [ ] `handle_audit_fields()` trigger 自動填 `created_by`/`updated_by`
- [ ] INSERT 時尊重前端傳入值，UPDATE 時系統值優先——保護審計紀錄可信度
- [ ] 所有 `SECURITY DEFINER` function 都必須加 `SET search_path = shop`

### Stage 2：Identity

- [ ] **Auth Bridge Pattern**：`auth.users` (UUID) → `shop.users` (ULID) → 所有業務表
- [ ] 業務表**永遠不直接 reference `auth.users`**
- [ ] `(SELECT auth.uid())` 加括號 = initPlan 最佳化 = 只算一次，不加括號 = 每行算一次
- [ ] `shop.profiles` 的 PK 就是 FK（1:1 關係的標準做法）
- [ ] Email 不存在 profiles 裡——用 `get_my_email()` 從 `auth.users` 查，避免 desync
- [ ] `handle_new_user()` 用 optimistic insert + loop 處理 username 碰撞，沒有 race condition
- [ ] 每個 helper function 都要 `GRANT EXECUTE TO authenticated`，否則前端會 permission denied

---

## 動手做 🛠️

### 練習 1：讀懂 EXPLAIN

在 Supabase SQL Editor 裡跑這兩個查詢，比較 `EXPLAIN ANALYZE` 的輸出差異：

```sql
-- A：沒括號
explain analyze
select id from shop.users where auth_user_id = auth.uid();

-- B：有括號
explain analyze
select id from shop.users where auth_user_id = (select auth.uid());
```

找到 `InitPlan` 節點了嗎？如果 A 版本沒有 `InitPlan`，你就知道為什麼要加括號了。

### 練習 2：模擬 username 碰撞

```sql
-- 先手動建立一個使用者
insert into auth.users (id, email, raw_user_meta_data, encrypted_password, aud, role)
values (
  gen_random_uuid(),
  'alice@example.com',
  '{"username": "alice"}'::jsonb,
  crypt('test1234', gen_salt('bf')),
  'authenticated',
  'authenticated'
);

-- 再建一個同名的
insert into auth.users (id, email, raw_user_meta_data, encrypted_password, aud, role)
values (
  gen_random_uuid(),
  'alice.smith@example.com',
  '{"username": "alice"}'::jsonb,
  crypt('test1234', gen_salt('bf')),
  'authenticated',
  'authenticated'
);

-- 檢查結果
select id, username from shop.profiles order by created_at;
-- 你應該會看到 alice 和 alice1
```

### 練習 3：驗證 Bridge Pattern

```sql
-- 這個查詢應該可以跑
select p.username, p.display_name
from shop.profiles p
join shop.users u on u.id = p.id;

-- 這個查詢不該出現在你的業務表裡
-- （反面教材：直接 join auth.users）
select p.username, a.email
from shop.profiles p
join auth.users a on a.id = ???;  -- ❌ 型別不對，也不該這樣做
```

想一想：如果 `shop.profiles` 的 FK 直接指向 `auth.users`，上面的 join 該怎麼寫？型別會出什麼問題？

---

> **下一章**：[02_organization-catalog.md](02_organization-catalog.md) — Stage 3-4：公司、門市、商品目錄

---

← [00_README](00_README.md) | [02 組織 + 商品 →](02_organization-catalog.md)

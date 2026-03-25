# Head First 安全防線 — Stage 9：RLS + Policies + GRANTs

> **"沒有 RLS 的 Supabase，就像沒有鎖的保險箱——裡面再值錢也沒用。"**

這份指南涵蓋 [`002_shop_schema.sql`](../migrations/002_shop_schema.sql) 的 **第 646–1012 行**。

打開 SQL 檔案放在旁邊，我們邊看邊學。

---

## 搭配閱讀

| 你在讀的 | SQL 行號 | 學什麼 |
|----------|----------|--------|
| Stage 9：Security | 646–1012 | RLS 三層防禦、Helper Functions、Policies、GRANTs |

---

# Stage 9：Security — RLS + Policies + GRANTs

> **📖 SQL 第 646–1012 行**

## 9.0 為什麼這是最重要的一章？

RLS 是 Supabase 的靈魂 —— **不是可選的**。

Supabase 把 PostgreSQL 直接暴露給前端。你的 `anon` key 會被寫進 JavaScript bundle、
被任何人用 DevTools 看到。沒有 RLS 的話，任何人拿到 `anon` key 就能：

```
SELECT * FROM shop.orders;            -- 看到所有人的訂單
DELETE FROM shop.products WHERE true;  -- 刪掉全部商品
UPDATE shop.profiles SET is_staff = true WHERE id = '我的ID';  -- 自己升級成管理員
```

> ### 🧠 你的大腦在想…
>
> 「我用 authenticated role 不就安全了？anon 又不能改資料。」
>
> 錯。`authenticated` 只代表「登入了」，不代表「有權限」。
> 一個已登入的顧客，如果沒有 RLS，照樣可以 `SELECT * FROM shop.orders`
> 看到**所有人的訂單**。RLS 才是「你只能看到自己的訂單」的那道牆。

---

## 9.1 三層防禦模型

Supabase 的安全是三層 AND 邏輯 —— **三層都要通過**，請求才會成功：

```
┌─────────────────────────────────────────────────────────────────┐
│ Layer 1: ALTER TABLE ... ENABLE ROW LEVEL SECURITY              │
│          → 預設 deny all（連 SELECT 都不行）                      │
├─────────────────────────────────────────────────────────────────┤
│ Layer 2: CREATE POLICY ...                                      │
│          → 定義「誰」能對「哪些 row」做「什麼操作」                   │
├─────────────────────────────────────────────────────────────────┤
│ Layer 3: GRANT ...                                              │
│          → 角色層級的表操作權限（能不能 SELECT？能不能 INSERT？）      │
└─────────────────────────────────────────────────────────────────┘

  三層全部是 AND —— 少一層都不行！
```

| 層 | 控制的是 | 類比 |
|----|---------|------|
| **ENABLE RLS** | 啟動門禁系統 | 大樓啟用門禁卡 |
| **POLICY** | 哪張卡能進哪一層 | 員工卡只能到自己的樓層 |
| **GRANT** | 什麼角色有什麼卡 | 訪客只有「大廳」卡、員工有「辦公區」卡 |

> ### 💡 關鍵概念
>
> 如果只啟用了 RLS（Layer 1）但沒寫任何 Policy（Layer 2），
> **所有人（包括 service_role 以外的角色）都看不到任何資料**。
> 這就是「default deny」—— 寧可鎖死，也不要漏資料。

---

## 9.2 RLS Helper Functions（SQL 第 657–724 行）

在寫 Policy 之前，我們先準備好「工具函數」。

### 為什麼要用 Helper Function？

```sql
-- ❌ 反模式：在 Policy 裡直接寫 inline JOIN/EXISTS
create policy "bad" on shop.order_items for select
  using (exists (
    select 1 from shop.orders
    where orders.id = order_items.order_id
      and orders.customer_id = shop.get_current_user_id()
  ));

-- ✅ 正確：用 Helper Function
create policy "good" on shop.order_items for select
  using (shop.is_order_owner(order_id) or shop.is_staff());
```

為什麼 Helper Function 更好？四個原因：

| 原因 | 說明 |
|------|------|
| **效能** | `STABLE` 讓 query planner 在同一 statement 內快取結果 |
| **可讀性** | Policy 只有一行，一眼看懂 |
| **維護性** | 邏輯改一處，所有用到的 Policy 都更新 |
| **避免 RLS 遞迴** | inline 查詢可能觸發目標表自己的 RLS → 無限遞迴 |

---

### 9.2.1 `shop.is_staff()`（SQL 第 659–672 行）

```sql
-- 第 659 行
create or replace function shop.is_staff()
returns boolean
language sql
stable                           -- ① 可快取
security definer                 -- ② 以建立者身分執行
set search_path = shop           -- ③ 防止 search_path 注入
as $$
  select coalesce(
    (select is_staff from shop.profiles
     where id = shop.get_current_user_id()),
    false
  );
$$;

-- 第 672 行
grant execute on function shop.is_staff() to authenticated;  -- ④ 授權
```

> ### 🧠 你的大腦在想…
>
> 「`SECURITY DEFINER` 是什麼？為什麼不用預設的 `SECURITY INVOKER`？」
>
> 預設是 `INVOKER` —— 函數以「呼叫者」的身分執行，受呼叫者的 RLS 限制。
> 但 `is_staff()` 需要查 `shop.profiles` 表，而 `profiles` 本身也有 RLS。
> 如果用 `INVOKER`，查詢會被 profiles 的 RLS 再過濾一次 → 可能遞迴。
> `SECURITY DEFINER` 讓函數以「建立者」（通常是 superuser）身分執行，
> **繞過 RLS** 直接查表，避免遞迴問題。

---

### 每個 Helper Function 必備的 4 件事

這是鐵律，少一個就會出事：

| # | 必備項目 | 原因 | 忘記的後果 |
|---|---------|------|-----------|
| 1 | `STABLE` | 告訴 query planner 函數不修改資料，同一 statement 內可快取 | 每一行都重新執行 → 效能災難 |
| 2 | `SECURITY DEFINER` | 以建立者身分執行，繞過 RLS 避免遞迴 | RLS 無限遞迴 → 查詢失敗 |
| 3 | `SET search_path = shop` | 鎖定 search_path，防止惡意 schema 注入 | 攻擊者建立同名函數竊取資料 |
| 4 | `GRANT EXECUTE` | 授權指定角色呼叫 | `permission denied for function` 錯誤 |

---

### 9.2.2 `shop.is_store_staff(p_store_id text)`（SQL 第 674–689 行）

```sql
-- 第 674 行
create or replace function shop.is_store_staff(p_store_id text)
returns boolean
language sql stable security definer set search_path = shop
as $$
  select exists (
    select 1 from shop.store_staff
    where store_id = p_store_id
      and staff_id = shop.get_current_user_id()
      and deleted_at is null           -- 軟刪除的員工不算
  );
$$;

-- 第 689 行
grant execute on function shop.is_store_staff(text) to authenticated;
```

注意 `deleted_at is null` —— 即使 `store_staff` 裡有這個人的記錄，
只要被軟刪除了，就不算是店員。

---

### 9.2.3 `shop.is_order_owner(p_order_id text)`（SQL 第 692–706 行）

```sql
-- 第 692 行
create or replace function shop.is_order_owner(p_order_id text)
returns boolean
language sql stable security definer set search_path = shop
as $$
  select exists (
    select 1 from shop.orders
    where id = p_order_id
      and customer_id = shop.get_current_user_id()
  );
$$;

-- 第 706 行
grant execute on function shop.is_order_owner(text) to authenticated;
```

這個函數會被 `order_items`、`order_coupons` 的 Policy 大量使用 ——
子表透過 Helper Function 繼承父表的 ownership，不用 inline JOIN。

---

### 9.2.4 `shop.is_product_visible(p_product_id text)`（SQL 第 709–724 行）

```sql
-- 第 709 行
create or replace function shop.is_product_visible(p_product_id text)
returns boolean
language sql stable security definer set search_path = shop
as $$
  select exists (
    select 1 from shop.products
    where id = p_product_id
      and status = 'publish'          -- 只有已發布的
      and deleted_at is null          -- 且未被刪除的
  );
$$;

-- 第 724 行
grant execute on function shop.is_product_visible(text) to authenticated, anon;
```

注意：這是**唯一**同時授權給 `authenticated` **和** `anon` 的 Helper Function。
因為未登入的訪客也需要瀏覽已上架的商品。

---

## 9.3 進階模式：JWT Claims-Based（SQL 第 726–752 行）

### `shop.is_super_admin()`

```sql
-- 第 739 行
create or replace function shop.is_super_admin()
returns boolean
language sql stable security definer set search_path = shop
as $$
  select coalesce(
    (select auth.jwt()) -> 'app_metadata' ->> 'role' = 'super_admin',
    false
  );
$$;

-- 第 752 行
grant execute on function shop.is_super_admin() to authenticated;
```

> ### 🧠 你的大腦在想…
>
> 「`app_metadata` 和 `user_metadata` 有什麼不同？」
>
> | | `app_metadata` | `user_metadata` |
> |---|---|---|
> | **誰能改** | 只有後端（service_role） | 前端也能改（`supabase.auth.updateUser()`） |
> | **安全性** | 前端無法竄改 | 前端可以竄改 |
> | **用途** | 角色、權限、付費等級 | 偏好設定、暱稱、頭像 |
>
> **鐵律：權限相關的資料，永遠放 `app_metadata`，絕不放 `user_metadata`。**

### 如何設定 super_admin？

只能從後端（service_role）操作：

```sql
UPDATE auth.users
SET raw_app_meta_data = raw_app_meta_data || '{"role":"super_admin"}'::jsonb
WHERE id = 'user-uuid';
```

適用場景：跨店管理員、平台營運人員、客服角色。

---

## 9.4 進階模式：Time-Window 時效限制（SQL 第 754–779 行）

### `shop.can_cancel_order(p_order_id text)`

```sql
-- 第 763 行
create or replace function shop.can_cancel_order(p_order_id text)
returns boolean
language sql stable security definer set search_path = shop
as $$
  select exists (
    select 1 from shop.orders
    where id = p_order_id
      and customer_id = shop.get_current_user_id()  -- 是自己的訂單
      and status = 'pending'                          -- 還在 pending
      and created_at > now() - interval '24 hours'   -- 24 小時內
  );
$$;

-- 第 779 行
grant execute on function shop.can_cancel_order(text) to authenticated;
```

三個條件 **全部 AND**：

| 條件 | 意義 |
|------|------|
| `customer_id = 目前使用者` | 只能取消自己的訂單 |
| `status = 'pending'` | 已出貨的不能取消 |
| `created_at > now() - interval '24 hours'` | 超過 24 小時不能取消 |

### 前端怎麼知道取消失敗了？

RLS Policy 拒絕時，不會報錯 —— **UPDATE 靜默返回 0 rows affected**。

```typescript
const { data, error, count } = await supabase
  .from('orders')
  .update({ status: 'cancelled' })
  .eq('id', orderId)
  .select();

if (data?.length === 0 && !error) {
  // Policy 拒絕了，但不是 error
  alert('已超過取消期限，請聯繫客服');
}
```

> ### 📌 沒有 Dumb Questions
>
> **Q：為什麼 RLS 拒絕不回傳 error？**
>
> A：這是 PostgreSQL 的設計。RLS 的 `USING` clause 是一個 filter，
> 不符合條件的 row 直接「消失」—— 對使用者來說，就像那筆資料不存在。
> 這樣設計的好處是不會洩漏「這筆資料存在但你沒權限」的資訊。
> 壞處是前端需要自己判斷 `0 rows affected` 的情境。

---

## 9.5 批量啟用 RLS（SQL 第 781–799 行）

```sql
-- 第 783 行
do $$
declare
  tbl text;
begin
  foreach tbl in array array[
    'users', 'profiles', 'companies', 'stores', 'store_staff',
    'products', 'product_images', 'reviews', 'stocks',
    'inventory_movements', 'coupons', 'addresses',
    'orders', 'order_items', 'order_coupons',
    'payments', 'point_rewards',
    'terms', 'term_taxonomy', 'term_relationships'
  ]
  loop
    execute format(
      'alter table shop.%I enable row level security;', tbl
    );
  end loop;
end;
$$;
```

一次對 **全部 20 張表** 啟用 RLS。

啟用之後，所有角色（除了 table owner 和 superuser）**預設什麼都看不到**。
接下來要一張表一張表地寫 Policy，把「門」打開。

> ### 🧠 你的大腦在想…
>
> 「為什麼用 loop 不一張張寫？」
>
> 因為 `ALTER TABLE ... ENABLE ROW LEVEL SECURITY` 每張表都一樣，
> 沒有任何參數差異。用 loop 可以：
> 1. 保證不會漏掉任何表（清單和其他地方一致）
> 2. 未來新增表只要加到陣列裡

---

## 9.6 Policies — 逐表分析（SQL 第 801–955 行）

這是最長的一段。我們用一張總表先建立全貌，然後挑重點深入。

### 全表 Policy 總覽

| 表 | SELECT | INSERT | UPDATE | DELETE | service_role |
|----|--------|--------|--------|--------|-------------|
| **users** | authenticated（全部） | —（trigger 管理） | — | — | all |
| **profiles** | authenticated（全部） | — | 自己的 | — | all |
| **products** | auth+anon（published 或 author 或 staff） | staff | staff | staff | all |
| **product_images** | auth+anon（visible 或 staff） | staff | staff | staff | all |
| **reviews** | auth+anon（visible 或自己的或 staff） | 自己的 | 自己的 | staff | all |
| **orders** | 自己的 或 staff 或 super_admin | 自己的 | staff/super_admin + 取消（24h） | — | all |
| **order_items** | owner 或 staff | owner 或 staff | staff | staff | all |
| **order_coupons** | owner 或 staff | staff | staff | staff | all |
| **addresses** | 自己的 或 staff | 自己的 | 自己的 | 自己的 | all |
| **payments** | 自己的 或 staff | 自己的 或 staff | staff | — | all |
| **point_rewards** | 自己的 或 staff | staff | — | — | all |
| **stores** | auth+anon（全部） | staff | staff | staff | all |
| **companies** | staff only | staff | staff | staff | all |
| **stocks** | staff 或 store_staff | staff | staff | staff | all |
| **inventory_movements** | staff 或 store_staff | staff | staff | staff | all |
| **coupons** | auth+anon（有效期內+啟用） 或 staff | staff | staff | staff | all |
| **store_staff** | 自己的 或 staff | staff | staff | staff | all |
| **terms** | auth+anon（全部） | staff | staff | staff | all |
| **term_taxonomy** | auth+anon（全部） | staff | staff | staff | all |
| **term_relationships** | auth+anon（全部） | staff | staff | staff | all |

---

### 重點 Policy 深入解析

#### users（SQL 第 803–805 行）

```sql
-- 第 804 行
create policy "users_select" on shop.users
  for select to authenticated using (true);
create policy "users_service_role" on shop.users
  for all to service_role using (true) with check (true);
```

`users` 表只有 SELECT —— 因為 INSERT 由 auth trigger 自動處理，
不允許使用者直接寫入。

---

#### products —— 三種可見性（SQL 第 812–826 行）

```sql
-- 第 813 行
create policy "products_select" on shop.products
  for select to authenticated, anon
  using (
    (status = 'publish' and deleted_at is null)   -- 已上架 → 任何人
    or author_id = shop.get_current_user_id()      -- 草稿 → 只有作者
    or shop.is_staff()                              -- 全部 → 管理員
  );
```

三個條件用 `OR` 連接 —— 只要符合其中一個就能看到：

| 條件 | 誰能看 | 場景 |
|------|--------|------|
| `status='publish' AND deleted_at IS NULL` | 所有人（含 anon） | 已上架商品頁 |
| `author_id = 目前使用者` | 作者本人 | 草稿管理 |
| `shop.is_staff()` | 管理員 | 後台管理 |

---

#### orders —— 最複雜的 Policy 組合（SQL 第 852–869 行）

```sql
-- 第 853 行：SELECT
create policy "orders_select" on shop.orders for select to authenticated
  using (
    customer_id = shop.get_current_user_id()
    or shop.is_staff()
    or shop.is_super_admin()        -- JWT claims pattern
  );

-- 第 859 行：INSERT（只能建立自己的訂單）
create policy "orders_insert" on shop.orders for insert to authenticated
  with check (customer_id = shop.get_current_user_id());

-- 第 862 行：UPDATE（管理員/super_admin）
create policy "orders_update_staff" on shop.orders for update to authenticated
  using (shop.is_staff() or shop.is_super_admin());

-- 第 865 行：UPDATE（顧客 24h 內取消）—— Time-Window pattern
create policy "orders_cancel_own" on shop.orders for update to authenticated
  using (shop.can_cancel_order(id))
  with check (status = 'cancelled');   -- 只允許改成 cancelled
```

注意 `orders_cancel_own` 的 `WITH CHECK` —— 即使 `USING` 通過了，
`WITH CHECK` 確保顧客**只能把狀態改成 `cancelled`**，不能改成其他值。

> ### 📌 沒有 Dumb Questions
>
> **Q：同一張表可以有多個 UPDATE policy 嗎？**
>
> A：可以！PostgreSQL 會用 **OR** 合併同類型的 policies。
> 所以 `orders_update_staff` 和 `orders_cancel_own` 是「staff 可以任意改
> **或者** 顧客在 24h 內只能改成 cancelled」。

---

#### order_items / order_coupons —— 子表繼承（SQL 第 871–893 行）

```sql
-- 第 872 行
create policy "order_items_select" on shop.order_items
  for select to authenticated
  using (shop.is_order_owner(order_id) or shop.is_staff());
```

子表的 ownership 不是直接比對 `customer_id`（因為子表沒有這個欄位），
而是透過 `shop.is_order_owner(order_id)` 去父表查。

這就是 Helper Function 的威力 —— 一行搞定「這筆訂單明細是不是我的」。

---

#### coupons —— 動態時效（SQL 第 938–945 行）

```sql
-- 第 939 行
create policy "coupons_select" on shop.coupons
  for select to authenticated, anon
  using (
    (is_active = true and deleted_at is null
     and (starts_at is null or starts_at <= now())
     and (expires_at is null or expires_at > now()))
    or shop.is_staff()
  );
```

一般使用者只能看到**當下有效**的優惠券：

| 條件 | 意義 |
|------|------|
| `is_active = true` | 已啟用 |
| `deleted_at is null` | 未被刪除 |
| `starts_at <= now()` | 已經開始（或沒設開始時間） |
| `expires_at > now()` | 還沒到期（或沒設到期時間） |

管理員（`shop.is_staff()`）可以看到所有優惠券，包括過期的和草稿。

---

#### stocks / inventory_movements —— 門市層級（SQL 第 932–936 行）

```sql
-- 第 933 行
create policy "stocks_select" on shop.stocks
  for select to authenticated
  using (shop.is_staff() or shop.is_store_staff(store_id));
```

這裡用了 `is_store_staff(store_id)` —— 門市員工**只能看到自己門市的庫存**，
不能看到其他門市的。而全域管理員（`is_staff()`）可以看到所有門市。

---

## 9.7 批量 Staff 寫入 Policies（SQL 第 957–979 行）

9 張管理員管理的表，INSERT/UPDATE/DELETE 的 Policy 完全一樣：

```sql
-- 第 957 行
do $$
declare
  tbl text;
begin
  foreach tbl in array array[
    'companies', 'stores', 'stocks', 'store_staff',
    'inventory_movements', 'coupons',
    'terms', 'term_taxonomy', 'term_relationships'
  ]
  loop
    execute format('
      create policy "%1$s_insert_staff" on shop.%1$s
        for insert to authenticated with check (shop.is_staff());
      create policy "%1$s_update_staff" on shop.%1$s
        for update to authenticated using (shop.is_staff());
      create policy "%1$s_delete_staff" on shop.%1$s
        for delete to authenticated using (shop.is_staff());
      create policy "%1$s_service_role" on shop.%1$s
        for all to service_role using (true) with check (true);
    ', tbl);
  end loop;
end;
$$;
```

一個 loop 產生 **9 x 4 = 36 條 Policy**。

注意 `%1$s` 的用法 —— 這是 `format()` 的「位置參數引用」語法，
表示「重複使用第 1 個參數」，避免重複寫表名。

---

## 9.8 GRANTs（SQL 第 981–1012 行）

```sql
-- 第 983 行
do $$
declare
  tbl text;
begin
  -- 所有 20 張表：authenticated 有完整 CRUD，service_role 有 ALL
  foreach tbl in array array[
    'users', 'profiles', 'companies', 'stores', 'store_staff',
    'products', 'product_images', 'reviews', 'stocks',
    'inventory_movements', 'coupons', 'addresses',
    'orders', 'order_items', 'order_coupons',
    'payments', 'point_rewards',
    'terms', 'term_taxonomy', 'term_relationships'
  ]
  loop
    execute format('grant select on shop.%I to authenticated;', tbl);
    execute format('grant insert, update, delete on shop.%I to authenticated;', tbl);
    execute format('grant all on shop.%I to service_role;', tbl);
  end loop;

  -- 8 張公開可讀表：anon 有 SELECT
  foreach tbl in array array[
    'products', 'product_images', 'stores',
    'terms', 'term_taxonomy', 'term_relationships',
    'coupons', 'reviews'
  ]
  loop
    execute format('grant select on shop.%I to anon;', tbl);
  end loop;
end;
$$;
```

### GRANT 和 Policy 的關係

這是最容易搞混的地方：

```
                          GRANT                    Policy
                    ┌──────────────┐         ┌──────────────┐
                    │ 角色能不能做  │   AND   │ 能做哪些 row  │
                    │ 這個操作？    │         │              │
                    └──────────────┘         └──────────────┘

  GRANT SELECT → authenticated 可以 SELECT（表層級）
  Policy using(customer_id = ...) → 但只能 SELECT 自己的 row（行層級）
```

| | GRANT | Policy |
|---|---|---|
| **控制層級** | 整張表 | 逐行 |
| **問的問題** | 「authenticated 能不能 SELECT shop.orders？」 | 「這一行 order，這個使用者能不能看到？」 |
| **關係** | AND（兩個都要通過） | AND（兩個都要通過） |
| **忘記設定** | `permission denied for table orders` | 查詢成功但回傳 0 rows |

> ### 🧠 你的大腦在想…
>
> 「既然 Policy 已經在做過濾了，為什麼還需要 GRANT？」
>
> 因為它們是不同層級的檢查。GRANT 是 PostgreSQL 原生的權限系統，
> RLS Policy 是額外的行層級過濾。兩者獨立運作，**都要通過**。
>
> 實務上，你通常會給 `authenticated` 比較寬鬆的 GRANT（SELECT + INSERT + UPDATE + DELETE），
> 然後用 Policy 做精細的行層級控制。
> 但 `anon` 只給 SELECT GRANT，因為匿名使用者連操作的機會都不應該有。

---

## 9.9 service_role Policy —— 別忘了後端！

**每張表都需要這一條**：

```sql
create policy "xxx_service_role" on shop.xxx
  for all to service_role
  using (true) with check (true);
```

為什麼？因為 RLS 啟用後，**連 service_role 也會受到影響**（除非是 table owner）。
沒有這條 Policy，你的：

- ETL 排程無法讀寫資料
- Cron Jobs 跑不動
- Webhooks 寫不進去
- Edge Functions 存取被拒

`using (true) with check (true)` 就是「全部通過」—— service_role 是後端專用的，
不會暴露給前端，所以給全部權限是安全的。

> ### 📌 沒有 Dumb Questions
>
> **Q：可以之後再加 RLS 嗎？**
>
> A：技術上可以，但**絕對不建議**。從你 `CREATE TABLE` 的那一刻起，
> 如果沒有 RLS，任何拿到 `anon` key 的人就有完整存取權。
> Supabase 的 Dashboard 也會在沒有 RLS 的表旁邊顯示警告。
> **正確做法：建表 → 立刻啟用 RLS → 寫 Policy → 設 GRANT。**
>
> **Q：如果忘了 `GRANT EXECUTE` 會怎樣？**
>
> A：函數存在，但 `authenticated` 使用者呼叫時會得到 `permission denied for function shop.is_staff`。
> Policy 裡面引用了這個函數 → Policy 評估失敗 → **所有 row 都被拒絕**。
> 表面症狀是「查詢回來是空的」，很難 debug。
>
> **Q：為什麼 `point_balances` view 用 `security_invoker` 而不是 `security_definer`？**
>
> A：因為 View 和 Function 的語意不同。View 用 `SECURITY INVOKER`
> 表示「以呼叫者的身分查詢」—— 這樣 View 會**尊重呼叫者的 RLS**。
> 如果用 `SECURITY DEFINER`，View 會繞過 RLS，所有人都能看到所有紅利餘額。

---

## 🎯 重點子彈

### 三層防禦

- [ ] **Layer 1**：`ALTER TABLE ... ENABLE ROW LEVEL SECURITY` → 預設全拒絕
- [ ] **Layer 2**：`CREATE POLICY` → 定義「誰對哪些 row 做什麼」
- [ ] **Layer 3**：`GRANT` → 角色層級的表操作權限
- [ ] 三層是 **AND** 關係，少一層都不行

### Helper Functions

- [ ] 所有 RLS Helper 都必須有：`STABLE` + `SECURITY DEFINER` + `SET search_path` + `GRANT EXECUTE`
- [ ] 用 Helper Function 取代 inline JOIN/EXISTS —— 效能、可讀、可維護、防遞迴
- [ ] `is_product_visible()` 是唯一同時 GRANT 給 `anon` 的 Helper

### 進階模式

- [ ] **JWT Claims**：`app_metadata` 只能後端改，比 `user_metadata` 安全
- [ ] **Time-Window**：`can_cancel_order()` 用三個 AND 條件限制取消時效
- [ ] RLS 拒絕 = 靜默 0 rows，不是 error —— 前端要自己判斷

### Policies

- [ ] 同一張表可以有多個同類 Policy，PostgreSQL 用 OR 合併
- [ ] `WITH CHECK` 控制**寫入的值**（`orders_cancel_own` 只允許改成 `cancelled`）
- [ ] 子表用 Helper Function 繼承父表 ownership（`is_order_owner(order_id)`）
- [ ] 公開可讀的表用 `to authenticated, anon`

### GRANTs

- [ ] GRANT = 表層級操作權限，Policy = 行層級過濾，兩者 AND
- [ ] `anon` 只給 SELECT，且只給 8 張公開表
- [ ] `service_role` 每張表都要有 `for all using(true) with check(true)` Policy

---

## 🛠️ 動手做

### 練習 1：用不同角色測試 RLS

在 Supabase SQL Editor 裡，你可以模擬不同角色：

```sql
-- 模擬 anon 角色
set role anon;
select * from shop.products;        -- 應該只看到 published 商品
select * from shop.orders;          -- 應該回傳 error（anon 沒有 GRANT）
reset role;

-- 模擬 authenticated 角色（某個使用者）
set role authenticated;
set request.jwt.claims = '{"sub":"user-uuid-here","app_metadata":{}}';
select * from shop.orders;          -- 應該只看到自己的訂單
select * from shop.companies;       -- 應該回傳空（不是 staff）
reset role;

-- 模擬 staff
set role authenticated;
set request.jwt.claims = '{"sub":"staff-uuid-here","app_metadata":{}}';
-- （前提：該 user 的 profiles.is_staff = true）
select * from shop.orders;          -- 應該看到所有訂單
reset role;
```

### 練習 2：測試 Time-Window Policy

```sql
-- 建立一筆測試訂單
set role authenticated;
set request.jwt.claims = '{"sub":"test-customer-uuid"}';

-- 嘗試取消 24h 內的 pending 訂單
update shop.orders set status = 'cancelled'
where id = 'recent-order-id';
-- 預期：成功（1 row affected）

-- 嘗試取消 24h 前的訂單
update shop.orders set status = 'cancelled'
where id = 'old-order-id';
-- 預期：0 rows affected（靜默拒絕）

-- 嘗試把訂單改成 'delivered'（不是 cancelled）
update shop.orders set status = 'delivered'
where id = 'recent-order-id';
-- 預期：0 rows affected（WITH CHECK 拒絕）

reset role;
```

### 練習 3：驗證 Helper Function 的安全屬性

```sql
-- 檢查所有 Helper Function 是否都有正確的安全屬性
select
  p.proname as function_name,
  case p.provolatile
    when 's' then 'STABLE ✅'
    when 'i' then 'IMMUTABLE'
    when 'v' then 'VOLATILE ❌'
  end as volatility,
  case p.prosecdef
    when true then 'SECURITY DEFINER ✅'
    else 'SECURITY INVOKER ❌'
  end as security,
  p.proconfig as config   -- 應該包含 search_path=shop
from pg_proc p
join pg_namespace n on p.pronamespace = n.oid
where n.nspname = 'shop'
  and p.proname in (
    'is_staff', 'is_store_staff', 'is_order_owner',
    'is_product_visible', 'is_super_admin', 'can_cancel_order'
  );
```

### 練習 4：列出所有表的 RLS 狀態和 Policy 數量

```sql
select
  c.relname as table_name,
  c.relrowsecurity as rls_enabled,
  count(pol.polname) as policy_count
from pg_class c
join pg_namespace n on c.relnamespace = n.oid
left join pg_policy pol on pol.polrelid = c.oid
where n.nspname = 'shop'
  and c.relkind = 'r'
group by c.relname, c.relrowsecurity
order by c.relname;
-- 每張表都應該 rls_enabled = true 且 policy_count >= 2
```

---

## 🧭 下一步

RLS 設好了，但安全不只是 Policy。接下來你需要：

1. **前端錯誤處理**：處理 RLS 靜默拒絕（0 rows affected）的 UX
2. **監控**：Supabase Logs 可以看到被 RLS 拒絕的查詢
3. **測試**：每次改 Policy 都要跑完整的角色測試
4. **稽核**：定期用練習 3、4 的 SQL 檢查安全屬性

---

[← 04 折扣 + 交易](04_coupons-commerce.md) | [06 自動化 →](06_automation.md)

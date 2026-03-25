# Head First Supabase E-Commerce Database

> **"如果你的資料庫設計得好，程式碼就寫得少。"**

歡迎來到這份教學指南。我們要從零開始，用 10 個 Stage 蓋出一個**真正能上線的電商資料庫**。

不是玩具。不是 demo。是你真的可以拿去接金流、管庫存、跑 RLS 的那種。

---

## 這份指南適合誰？

你如果符合以下任一條件，這份指南就是為你寫的：

- 聽過 Supabase 但還沒真正設計過 schema
- 寫過 SQL 但不確定「Supabase 原生」該怎麼做
- 想把舊系統（SQL Server / MySQL / WordPress）搬到 Supabase
- 想理解為什麼電商資料庫要「這樣」設計

---

## 搭配檔案

| 檔案 | 用途 |
|------|------|
| `01_shop_supabase_native_schema.sql` | 完整可執行的 SQL schema（v3.0, 1,047 行） |
| `00_README.md` | 你正在讀的這份教學指南 |

**使用方式**：邊讀指南，邊打開 `.sql` 檔案對照。每個 Stage 都有對應的 SQL 段落。

---

## 全景地圖

先看大局。這 20 張表分成 10 個 Stage，每個 Stage 學一個核心概念：

```
Stage 1   Foundation        ── 地基（ULID、enum、extensions）
Stage 2   Identity          ── 誰是誰（auth bridge）
Stage 3   Organization      ── 公司 → 門市 → 店員
Stage 4   Catalog           ── 商品目錄
Stage 5   Taxonomy          ── 分類系統
Stage 6   Inventory         ── 庫存快照 + 異動紀錄
Stage 7   Coupons & Addr    ── 折扣券 & 地址簿
Stage 8   Commerce          ── 訂單、付款、紅利點數
Stage 9   Security          ── RLS、Policy、GRANT
Stage 10  Automation        ── Trigger、Realtime、Storage
```

它們的依賴關係長這樣：

```
                    ┌─────────────┐
                    │  auth.users │  (Supabase 管理)
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │    users    │  Stage 2 (ULID bridge)
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  profiles   │  Stage 2
                    └──────┬──────┘
           ┌───────────────┼───────────────┐
           │               │               │
    ┌──────▼──────┐ ┌──────▼──────┐ ┌──────▼──────┐
    │  companies  │ │  products   │ │  addresses  │
    │  Stage 3    │ │  Stage 4    │ │  Stage 7    │
    └──────┬──────┘ └──┬─────┬───┘ └──────┬──────┘
           │           │     │            │
    ┌──────▼──────┐    │  ┌──▼─────┐ ┌────▼──────┐
    │   stores    │    │  │reviews │ │  orders   │
    │  Stage 3    │    │  │Stage 4 │ │  Stage 8  │
    └──────┬──────┘    │  └────────┘ └──┬──┬──┬──┘
           │           │                │  │  │
    ┌──────▼──────┐ ┌──▼───────┐    ┌──▼┐ │ ┌▼────────┐
    │ store_staff │ │  stocks  │    │OI │ │ │payments │
    │  Stage 3    │ │ Stage 6  │    │S8 │ │ │ Stage 8 │
    └─────────────┘ └──────────┘    └───┘ │ └─────────┘
                                          │
                                   ┌──────▼──────┐
                                   │point_rewards│
                                   │  Stage 8    │
                                   └─────────────┘
```

---

## Stage 1: Foundation — 在蓋房子之前，先打地基

> **你的大腦在想**：「不就建個表嗎，為什麼要搞這麼多前置作業？」
>
> **答案**：因為 ID 格式、型別系統、擴充套件，這三件事一旦決定就很難改。先花 5 分鐘做對，省你未來 50 小時的 migration 地獄。

### 學習重點

- [x] 為什麼用 ULID 而不是 UUID 或 BIGINT
- [x] 什麼是 enum type，為什麼不用 varchar + CHECK
- [x] Extensions 的角色

### ULID vs UUID vs BIGINT — 一次搞懂

| | BIGINT (SERIAL) | UUID v4 | ULID |
|---|---|---|---|
| 長度 | 8 bytes | 36 chars | **26 chars** |
| 可排序 | 單機遞增 | 完全隨機 | **按時間排序** |
| B-Tree 效能 | 順序寫入 | 隨機寫入（頁分裂） | **順序寫入** |
| 分散式安全 | 需要 sequence | 安全 | **安全** |
| 可讀性 | `42` | `550e8400-e29b-41d4-a716-446655440000` | `01HXYZ1234ABCDEFGH` |

> **腦筋急轉彎**：如果你的電商系統未來要水平擴展（多台 DB），BIGINT 的 sequence 會撞號。UUID 不會撞但 index 效能差。ULID 兩個問題都解決了。

### 為什麼用 Enum 而不是 VARCHAR？

```sql
-- 這樣寫，'pendnig' 這種 typo 也能存進去 ❌
status varchar(50) not null default 'pending'

-- 這樣寫，資料庫幫你擋住 typo ✅
status public.order_status not null default 'pending'
-- order_status = ('pending','confirmed','processing','shipped',
--                 'delivered','cancelled','refunded')
```

> **Head First 原則**：讓錯誤在最靠近源頭的地方被攔截。資料庫比應用程式更早碰到資料，所以驗證放在 DB 層最安全。

### 重要觀念：Extensions

```sql
create extension if not exists pgcrypto;     -- ULID 需要的隨機數
create extension if not exists moddatetime;  -- Supabase 原生的 updated_at trigger
create extension if not exists pg_trgm;      -- 商品模糊搜尋
```

把 extensions 想像成「PostgreSQL 的外掛」。Supabase 預裝了很多，你只需要啟用。

---

## Stage 2: Identity — Auth Bridge 模式

> **你的大腦在想**：「Supabase 已經有 auth.users 了，為什麼還要自己建 users 表？」
>
> **這可能是整份 schema 最重要的設計決策。**

### 問題場景

```
auth.users (Supabase 管理)
  ├── id: UUID        ← Supabase 決定的格式
  ├── email
  └── raw_user_meta_data

你的業務表
  ├── orders.customer_id → ???
  ├── products.author_id → ???
  └── reviews.customer_id → ???
```

如果業務表直接 FK 到 `auth.users(id)`：

1. **型別被綁死**：所有 FK 都必須用 UUID
2. **耦合 Supabase 內部**：auth schema 的結構改了你就爆了
3. **違反 ULID 慣例**：業務表應該統一用 TEXT

### 解法：Bridge Table

```
auth.users (UUID)
     │
     ▼
public.users (ULID)  ← 橋接表，只有 id + auth_user_id
     │
     ▼
public.profiles      ← 擴充資料（username, avatar, is_staff...）
```

```sql
-- Bridge: UUID → ULID
create table public.users (
  id            text primary key default generate_ulid(),
  auth_user_id  uuid unique not null references auth.users(id) on delete cascade,
  created_at    timestamptz not null default now()
);
```

現在所有業務表都只需要：

```sql
customer_id text references public.users(id)  -- 統一 TEXT，乾淨
```

### 關鍵 Helper Function

```sql
-- auth UUID → 業務 ULID（RLS 和業務邏輯都用這個）
create function public.get_current_user_id() returns text ...
  select id from public.users where auth_user_id = (select auth.uid());
```

> **注意 `(SELECT auth.uid())` 的括號**。沒有括號的 `auth.uid()` 在 RLS policy 裡會**每一列都重新計算**。加了 `SELECT` 變成 initPlan，PostgreSQL 只算一次。這是 Supabase 官方推薦的最佳化。

### 自動建立帳號

當用戶透過 Supabase Auth 註冊時，trigger 自動建立 `users` + `profiles`：

```sql
create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();
```

`handle_new_user()` 內部還處理了 **username 碰撞**（user1@gmail.com 和 user1@yahoo.com 都想叫 `user1`），用 loop + exception 自動加數字後綴。

### 沒有 Dumb Questions

> **Q: profiles 為什麼不存 email？**
>
> A: 因為 `auth.users` 已經存了。如果你在 profiles 也存一份，兩邊會 desync（用戶改了 email 但 profiles 裡的沒更新）。需要 email 時用 `get_my_email()` function 或 join auth.users。
>
> **Q: users 表看起來好浪費，只有兩個欄位？**
>
> A: 它的價值不在欄位多寡，而在**解耦**。它是 auth 世界（UUID）和業務世界（ULID）之間的翻譯層。20 張業務表都指向它，而不是指向 Supabase 的內部表。

---

## Stage 3: Organization — 公司、門市、店員

> **你的大腦在想**：「電商不就是賣東西嗎，為什麼要管公司和門市？」
>
> **因為真實世界的電商是多門市的。** 一個品牌（Company）底下有多家門市（Store），每家門市有自己的店員和庫存。

### 層級結構

```
Company (品牌/公司)
  └── Store (門市/倉庫)
       └── Store Staff (店員，有角色)
```

### Soft Delete 模式

核心業務實體用 `deleted_at` 而不是真的刪除：

```sql
deleted_at timestamptz  -- NULL = 活的, 有值 = 軟刪除
```

配合 partial index 確保查詢效能：

```sql
create index idx_companies_active on companies(id) where deleted_at is null;
```

> **什麼時候用 soft delete？什麼時候 hard delete？**
>
> | 場景 | 策略 | 原因 |
> |------|------|------|
> | companies / stores / products | Soft delete | 有歷史訂單引用，不能真刪 |
> | inventory_movements | **永不刪除** | 審計軌跡，append-only |
> | 日誌、爬蟲結果 | Hard delete + archive | 量大，soft delete 會讓表膨脹 |

### Store Staff 的角色設計

```sql
roles text[] not null default array['staff']::text[]
-- 例如: '{manager,cashier}', '{stock_keeper}'
```

用 `text[]` 而不是單一 `permission text`，因為一個店員可能同時是收銀員和庫存管理員。

---

## Stage 4: Catalog — 商品建模的藝術

> **你的大腦在想**：「商品不就是名稱 + 價格嗎？」
>
> **沒那麼簡單。** 一個好的商品表要處理：變體（顏色/尺寸）、SEO slug、搜尋、圖片、定價層級、稅率。

### First-Class Columns vs JSONB — 怎麼選？

**黃金法則**：會被 `WHERE`、`ORDER BY`、`JOIN` 的欄位 → 獨立 column。其他 → jsonb。

```sql
-- 這些會被查詢/排序/過濾，所以是獨立欄位 ✅
price            numeric(12,2)   -- WHERE price BETWEEN 100 AND 500
sku              varchar(100)    -- WHERE sku = 'ABC-123'
status           product_status  -- WHERE status = 'publish'

-- 這些是彈性屬性，丟 jsonb ✅
metadata         jsonb           -- {"color": "red", "size": "L", "material": "cotton"}
```

> **反模式警告（anti-patterns.md S6）**：
> 把 price 放在 `metadata->>'price'` 裡？恭喜你，每次查詢都要全表掃描 + type casting。別這樣做。

### 商品變體 (Variants)

一件 T-shirt 有 3 個顏色 × 3 個尺寸 = 9 個變體。怎麼存？

```
products (id: 'ABC', type: 'variable', title: 'Basic Tee')
  ├── products (id: 'ABC-R-S', parent_id: 'ABC', sku: 'TEE-RED-S')
  ├── products (id: 'ABC-R-M', parent_id: 'ABC', sku: 'TEE-RED-M')
  └── ...
```

`parent_id` 自引用：父商品是 `variable` 型，子商品是實際可購買的 SKU。

### 搜尋索引

```sql
-- 模糊搜尋（打錯字也能找到）
create index idx_products_title_trgm
  on products using gin(title gin_trgm_ops);

-- 全文搜尋（「紅色 棉質 T-shirt」）
create index idx_products_search
  on products using gin(to_tsvector('simple', coalesce(title,'') || ' ' || coalesce(description,'')));
```

`pg_trgm` 讓你搜 "Tshrt" 也能找到 "T-shirt"。`tsvector` 讓你搜多個關鍵字。兩個索引互補。

### Product Images — 不要存 Binary

```sql
create table product_images (
  storage_path text not null,  -- 'product-images/ABC/main.webp'
  is_primary   boolean,
  sort_order   smallint
);
```

圖片放 Supabase Storage（S3 相容），資料庫只存路徑。Stage 10 會設定 Storage bucket 和 RLS。

---

## Stage 5: Taxonomy — 彈性分類系統

> **你的大腦在想**：「分類不就建一張 categories 表嗎？」
>
> **如果你只需要分類，那確實。** 但如果你還需要 tags、品牌、顏色、材質、場合……每個分類維度建一張表？

### 三表模式（源自 WordPress，但仍然好用）

```
terms (字彙)          ← "Electronics", "Red", "Nike", "Summer"
  │
term_taxonomy (分類法) ← term + 它屬於哪種分類維度
  │                      ("Electronics" 是 category)
  │                      ("Red" 是 color)
  │                      ("Nike" 是 brand)
  │
term_relationships    ← 多對多關聯到任何實體
                         (product 'ABC' ←→ category 'Electronics')
                         (product 'ABC' ←→ brand 'Nike')
```

**好處**：一套表處理所有分類維度，不需要為每個維度建新表。

**壞處**：`object_id` 是多態的（polymorphic），沒有 FK constraint。如果你需要嚴格 FK，考慮分表。

> **何時該用這個模式，何時不該？**
>
> | 場景 | 用 taxonomy | 用獨立表 |
> |------|:-----------:|:---------:|
> | 分類/標籤/品牌（維度常變動） | **Yes** | |
> | 商品顏色/尺寸（屬性） | **Yes** | |
> | 會員等級（固定、少量） | | **Yes** |
> | 付款方式（有特殊邏輯） | | **Yes** |

---

## Stage 6: Inventory — 快照 + 日誌雙表模式

> **你的大腦在想**：「庫存不就是 products 加個 quantity 欄位嗎？」
>
> **錯。** 因為庫存是「多門市」的，而且你需要知道**為什麼**數量會變。

### 兩張表的分工

```
stocks (快照)                    inventory_movements (日誌)
┌──────────────────────┐        ┌───────────────────────────┐
│ store_id + product_id │        │ store_id + product_id     │
│ quantity: 50          │  ←───  │ quantity_delta: -2         │
│                       │        │ reason: 'sale'             │
│ (現在有多少)          │        │ reference_id: 'ORDER-123'  │
└──────────────────────┘        │ (為什麼變了)               │
                                 └───────────────────────────┘
```

- `stocks`：**當前狀態**，每個 store × product 一列。可 UPDATE。
- `inventory_movements`：**歷史紀錄**，append-only。永不 UPDATE / DELETE。

> **腦筋急轉彎**：如果只有 stocks 表，老闆問你「上週三那批貨為什麼少了 50 件」，你能回答嗎？
>
> 不能。因為你只知道「現在有多少」，不知道「什麼時候因為什麼原因變了多少」。
>
> 這就是為什麼需要 movements。

### reason enum

```sql
create type movement_reason as enum
  ('sale', 'return', 'restock', 'adjustment', 'manual', 'transfer');
```

每次庫存變動都有明確原因，不是一句含糊的 note。

---

## Stage 7: Coupons & Addresses — FK 依賴排序

> **你的大腦在想**：「這兩個東西為什麼放在一起？」
>
> **因為它們都必須在 orders 之前建立。** orders 表有 FK 指向 addresses 和 coupons。如果你的 SQL 檔案順序不對，`CREATE TABLE orders` 會失敗。

### 重要觀念：建表順序 = FK 依賴順序

```
❌ 錯誤順序：
  CREATE TABLE orders (...shipping_address_id REFERENCES addresses(id)...)
  CREATE TABLE addresses (...)  ← 還不存在，boom!

✅ 正確順序：
  CREATE TABLE addresses (...)  ← 先建
  CREATE TABLE orders (...)     ← 後建，FK 才能解析
```

### Coupons 的 CHECK 約束

```sql
constraint ck_coupons_discount_value check (discount_value >= 0),
constraint ck_coupons_used_count     check (used_count >= 0),
constraint ck_coupons_dates          check (
  expires_at is null or starts_at is null or expires_at > starts_at
)
```

> **為什麼 CHECK constraint 要有名字？**
>
> 因為未來你可能需要 `ALTER TABLE ... DROP CONSTRAINT ck_coupons_dates`。如果 constraint 沒名字（anonymous），你就得去查 `pg_constraint` 系統表才能找到它的自動生成名。migration-guidelines.md 明確禁止隱式 constraint（M4）。

### Addresses 的 Partial Unique Index

```sql
create unique index uq_addresses_default
  on addresses(customer_id, label) where is_default = true;
```

翻譯：「每個客戶的每種地址標籤（home/office/shipping），最多只能有一個預設地址」。

`WHERE is_default = true` 是 **partial index**，只索引符合條件的列。非預設地址完全不受限制。

---

## Stage 8: Commerce — 交易核心

> **如果你在趕時間，這是最值得仔細讀的 Stage。** 訂單、付款、紅利——搞錯了客戶就損失錢。

### 訂單的金額欄位全部有 CHECK

```sql
constraint ck_orders_subtotal check (subtotal >= 0),
constraint ck_orders_tax      check (tax_total >= 0),
constraint ck_orders_total    check (total >= 0),
-- ... 共 6 個
```

> **為什麼不是 `total = subtotal + tax - discount`？**
>
> 因為 CHECK constraint 不能引用其他欄位的計算結果做跨欄位驗證（PostgreSQL 限制）。更重要的是，實際電商的 total 計算邏輯很複雜（運費減免、紅利折抵、匯率……），把這個邏輯放在應用層更合適。DB 只負責確保「金額不是負的」。

### Order Items — 購買快照

```sql
product_title varchar(255) not null default '',  -- 購買當下的商品名稱
sku           varchar(100),                       -- 購買當下的 SKU
```

> **為什麼要 snapshot？**
>
> 因為商品可能改名、改價、甚至下架。但客戶的歷史訂單應該顯示「他買的時候是什麼」，而不是「商品現在叫什麼」。

### Payments — 生命週期追蹤

```
pending → processing → paid ────→ (完成)
                         │
                         ├──→ refunded
                         └──→ partially_refunded

pending → processing → failed (重試 → 新的 payment record)
```

一筆訂單可以有**多筆** payment（重試、分期、部分退款），所以 payments 是獨立表。

```sql
constraint ck_payments_refund_amount
  check (refund_amount >= 0 and refund_amount <= amount)
```

退款金額不能超過付款金額。這是 DB 層級的防呆。

### Point Rewards — Ledger 模式

```sql
points bigint not null  -- +100 = 賺到, -50 = 花掉
```

**不存餘額**。餘額用 view 計算：

```sql
create view point_balances as
  select customer_id, coalesce(sum(points), 0) as balance
  from point_rewards
  group by customer_id;
```

> **為什麼不存餘額？**
>
> 因為存餘額 = 兩個地方記錄同一件事（交易紀錄 + 餘額欄位），遲早會 desync。
>
> **Ledger 模式**：只存交易（+/-），餘額永遠是 `SUM(points)`，數學保證正確。
>
> 銀行帳戶也是這樣運作的。

---

## Stage 9: Security — RLS 是 Supabase 的靈魂

> **你的大腦在想**：「RLS 好複雜，能不能之後再加？」
>
> **不行。** 在 Supabase 上，如果你的表沒有 RLS，任何拿到 `anon` key 的人都能讀寫你的資料。RLS 不是「加分題」，是「必做題」。

### RLS 三層防護

```
Layer 1: ALTER TABLE ... ENABLE ROW LEVEL SECURITY
         → 啟用 RLS（預設拒絕所有存取）

Layer 2: CREATE POLICY ...
         → 定義誰可以做什麼

Layer 3: GRANT ...
         → 授權 role 對表的基本操作權限
```

三層缺一不可。

### Helper Function 模式（核心）

```sql
-- ❌ 反模式：Policy 裡面寫 JOIN
create policy "bad" on order_items for select
  using (
    exists (
      select 1 from orders
      where orders.id = order_items.order_id
        and orders.customer_id = public.get_current_user_id()
    )
  );

-- ✅ 正確：抽成 helper function
create policy "good" on order_items for select
  using (public.is_order_owner(order_id) or public.is_staff());
```

> **為什麼？**
>
> 1. **效能**：helper function 標記為 `STABLE`，PostgreSQL 可以快取結果
> 2. **可讀性**：policy 一行就看懂意圖
> 3. **可維護性**：改權限邏輯只改一個 function，不是改 20 個 policy
> 4. **避免 RLS 遞迴**：helper 用 `SECURITY DEFINER` 繞過 RLS 檢查

### Helper Function 規範

```sql
create or replace function public.is_staff()
returns boolean
language sql
stable                    -- 允許 query planner 快取
security definer          -- 繞過 RLS（避免遞迴查 profiles）
set search_path = public  -- 安全性：防止 search_path injection
as $$
  select coalesce(
    (select is_staff from profiles where id = public.get_current_user_id()),
    false
  );
$$;

-- 別忘了 GRANT！
grant execute on function public.is_staff() to authenticated;
```

> **每個 helper function 必須具備的 4 件事**：
> 1. `STABLE` — 告訴 planner 可以快取
> 2. `SECURITY DEFINER` — 用建立者權限執行（繞過 RLS）
> 3. `SET search_path = public` — 防注入
> 4. `GRANT EXECUTE` — 否則 authenticated 用戶無法呼叫

### service_role Policy

```sql
-- 每張表都必須有
create policy "xxx_service_role" on public.xxx
  for all to service_role
  using (true) with check (true);
```

> **什麼是 service_role？**
>
> Supabase 有兩種 key：
> - `anon` key → 未登入用戶，受 RLS 限制
> - `service_role` key → 後端服務（ETL、cron job、webhook），**繞過 RLS**
>
> 但 `service_role` 繞過 RLS 的前提是你有對應的 policy。沒有 policy = 連 service_role 也進不去。

### GRANTs

```sql
-- 公開讀取的表（商品、門市、分類）
grant select on public.products to authenticated, anon;

-- 需要登入才能寫的表
grant insert, update, delete on public.orders to authenticated;

-- 後端服務完全存取
grant all on public.orders to service_role;
```

> **GRANT ≠ Policy**
>
> - GRANT 控制的是 **role 對整張表的操作權限**（可以 SELECT？可以 INSERT？）
> - Policy 控制的是 **哪些列**（只能看自己的訂單？還是所有人的？）
>
> 兩者是 AND 關係，都通過才能存取。

---

## Stage 10: Automation — 讓資料庫自己幹活

### updated_at Trigger（moddatetime）

```sql
create trigger trg_orders_updated_at
  before update on orders
  for each row execute function moddatetime(updated_at);
```

`moddatetime` 是 Supabase 內建的 extension，比自己寫 trigger function 更簡潔。每次 UPDATE 自動把 `updated_at` 設為 `now()`。

### Audit Fields Trigger

```sql
create trigger trg_orders_audit
  before insert or update on orders
  for each row execute function handle_audit_fields();
```

自動填入 `created_by` / `updated_by`，不需要應用層手動傳。

### Supabase Realtime

```sql
alter publication supabase_realtime add table public.orders;
alter publication supabase_realtime add table public.stocks;
```

只在**需要即時更新的表**啟用 Realtime，不要全部開。

> **哪些表適合 Realtime？**
>
> | 表 | 啟用？ | 原因 |
> |---|---|---|
> | orders | Yes | 客戶需要看到訂單狀態即時變化 |
> | stocks | Yes | 門市需要看到庫存即時更新 |
> | payments | Yes | 付款狀態回調 |
> | reviews | Yes | 新評價即時顯示 |
> | companies | **No** | 很少變動，不需要即時 |
> | products | **看情況** | 如果有即時編輯功能才需要 |

### Supabase Storage

```sql
-- Bucket 設定（透過 Dashboard 或 SQL）
insert into storage.buckets (id, name, public)
values ('product-images', 'product-images', true);

-- Storage RLS
create policy "public_read" on storage.objects for select
  using (bucket_id = 'product-images');

create policy "staff_upload" on storage.objects for insert to authenticated
  with check (bucket_id = 'product-images' and public.is_staff());
```

圖片上傳由 Storage RLS 控制，不是資料庫 RLS。但我們復用同一個 `is_staff()` helper。

---

## 重點回顧：設計原則速查表

| # | 原則 | 做法 |
|---|------|------|
| 1 | PK 一致性 | `TEXT DEFAULT generate_ulid()` — 所有業務表 |
| 2 | Auth 解耦 | `users` bridge 表，業務表不碰 `auth.users` |
| 3 | 型別一致 | FK 全部 `TEXT`，不混用 UUID/BIGINT |
| 4 | 查詢欄位獨立 | 會被 WHERE/ORDER BY 的欄位不放 jsonb |
| 5 | DB 層驗證 | Named CHECK + Enum types |
| 6 | RLS helper | Policy 不寫 JOIN，抽成 function |
| 7 | `(SELECT auth.uid())` | RLS 裡永遠加括號，initPlan 最佳化 |
| 8 | 完整安全三層 | RLS enable + Policy + GRANT，缺一不可 |
| 9 | service_role policy | 每張表都要，ETL/cron 才能用 |
| 10 | Soft delete | 核心表用 `deleted_at`，大表用 hard delete + archive |
| 11 | 快照 + 日誌 | stocks（當前）+ movements（歷史） |
| 12 | Ledger 模式 | 只存交易，餘額用 SUM 算 |
| 13 | FK 建表順序 | 被引用的表先建 |
| 14 | GRANT EXECUTE | helper function 必須授權 |
| 15 | moddatetime | Supabase 原生 updated_at trigger |

---

## 進階挑戰（想更深入的人）

完成這份 schema 後，你可以嘗試：

1. **Partition**：如果 `inventory_movements` 或 `point_rewards` 預期年增 >1M 列，考慮 `PARTITION BY RANGE (created_at)`
2. **Read Replica**：分析查詢（報表、Dashboard）打 read replica，不要打主庫
3. **Edge Functions**：用 Supabase Edge Functions 處理付款回調（webhook → 更新 payment status）
4. **Database Functions**：把「建立訂單 + 扣庫存 + 記錄 movement」包成一個 `plpgsql` function，確保原子性
5. **Full-Text Search**：用 `to_tsvector` + `ts_rank` 做商品搜尋排序

---

## 參考資源

- **Schema SQL**：`01_shop_supabase_native_schema.sql`（本目錄）
- **Supabase 設計規範**：`../../agent-init/skills/supabase/` 目錄
  - `pk-convention.md` — ULID 主鍵慣例
  - `rls-patterns.md` — RLS 正確寫法
  - `anti-patterns.md` — 反模式清單
  - `migration-guidelines.md` — Migration 規範
  - `performance-linter.md` — 效能守門員
  - `query-patterns.md` — 查詢模式
  - `scaling-guidelines.md` — 擴展紅線

---

## 在 Studio 中驗證你的電商 Schema

> **前置要求**：已讀完 [01_supabase-studio.md](../01_supabase-studio.md)

跑完 `01_shop_supabase_native_schema.sql` 之後，打開 `http://localhost:54323` 逐項驗證：

### Table Editor 驗證

```
📝 驗證清單
1. 切到 public schema → 確認看到全部 20 張表
2. 點進 orders → 檢查 FK 關聯
   - customer_id → users(id) ✅
   - store_id → stores(id) ✅
3. 點進 products → 確認 CHECK constraint
   - price > 0 ✅
4. 點進 stocks → 確認 updated_at trigger 有掛上
5. 開啟 orders 的 Realtime（僅此表需要即時更新）
```

### SQL Editor 驗證

```sql
-- 確認 ULID 函數正常
SELECT generate_ulid();  -- 應回傳 26 字元字串

-- 確認 Enum 型別
SELECT enum_range(NULL::public.order_status);

-- 查詢效能：orders 大量資料時是否走 index
EXPLAIN ANALYZE
SELECT * FROM orders WHERE store_id = '01HXY...' AND status = 'pending';
```

### RLS 驗證

```sql
-- 確認所有業務表都啟用了 RLS
SELECT tablename, rowsecurity
FROM pg_tables
WHERE schemaname = 'public' AND rowsecurity = false;
-- 理想結果：空（全部都是 true）

-- 測試 anon 角色看不到資料
SET ROLE anon;
SELECT * FROM orders;  -- 應回傳 0 行
RESET ROLE;
```

### API Docs 驗證

```bash
# 用 curl 測試 PostgREST
curl 'http://localhost:54321/rest/v1/products?select=id,name,price&limit=5' \
  -H "apikey: YOUR_ANON_KEY"
```

---

> **最後一句話**
>
> 資料庫不會因為「資料太多」而死。
> 它會因為「被要求做錯誤的事情」而死。
>
> 設計對了，PostgreSQL 可以處理你想像不到的規模。
> 設計錯了，100 筆資料也能讓你的查詢跑 10 秒。
>
> *— scaling-guidelines.md*

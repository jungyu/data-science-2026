# Stage 7-8：優惠券 + 地址 + 交易核心

> **對應 SQL**：[`002_shop_schema.sql`](../migrations/002_shop_schema.sql) 第 448-643 行
>
> 這一章你會學到：
> 1. 為什麼 coupons 和 addresses 必須在 orders **之前**建立（FK 依賴順序）
> 2. 電商最核心的交易表：訂單、明細、付款、點數
> 3. Snapshot pattern — 為什麼訂單要「拍快照」而不是 JOIN 商品表
> 4. Append-only ledger — 銀行等級的點數設計

---

## 搭配閱讀

| 你在讀的 | SQL 行號 | 學什麼 |
|----------|----------|--------|
| Stage 7：Coupons & Addresses | 448-504 | FK 依賴順序、partial unique index、CHECK 約束命名 |
| Stage 8：Commerce | 507-643 | 訂單、快照、付款生命週期、append-only 帳本 |

---

# Stage 7：Coupons & Addresses（SQL 第 448-504 行）

## 為什麼這兩張表放在一起？

因為它們都是 `orders` 的 **前置依賴**。

想像你正在蓋房子：

- `addresses` = 門牌地址 — 訂單要寄到哪裡
- `coupons` = 折價券規則 — 訂單要打什麼折

你不能先蓋屋頂再蓋地基。同理，你不能先 CREATE TABLE orders 再 CREATE TABLE addresses。

---

### 🧠 你的大腦在想…

> 「FK 依賴順序到底是什麼意思？」

看這個例子：

```sql
-- ❌ 錯誤順序：orders 先建，addresses 還不存在
CREATE TABLE orders (
  ...
  shipping_address_id REFERENCES shop.addresses(id)  -- 💥 ERROR!
);
CREATE TABLE addresses (...);

-- ✅ 正確順序：先建被參照的表
CREATE TABLE addresses (...);   -- 第一步
CREATE TABLE orders (
  ...
  shipping_address_id REFERENCES shop.addresses(id)  -- 現在可以了
);
```

PostgreSQL 在建立 FK 時，會**立刻檢查目標表是否存在**。不存在就直接報錯，不會「等一下再檢查」。

> **規則**：被 REFERENCES 的表，永遠要先建。

---

## 7.1 `shop.coupons` — 優惠券（SQL 第 457-482 行）

```sql
-- SQL 第 457-480 行
create table if not exists shop.coupons (
  id                    text primary key default public.generate_ulid(),
  code                  varchar(100)         not null,
  description           text                 not null default '',
  discount_type         shop.discount_type not null default 'fixed',
  discount_value        numeric(10,2)        not null default 0,
  min_order_amount      numeric(10,2),
  max_discount          numeric(10,2),
  max_uses              integer,
  max_uses_per_customer integer,
  used_count            integer              not null default 0,
  starts_at             timestamptz,
  expires_at            timestamptz,
  is_active             boolean              not null default true,
  metadata              jsonb                not null default '{}'::jsonb,
  created_at            timestamptz          not null default now(),
  updated_at            timestamptz          not null default now(),
  deleted_at            timestamptz,
  created_by            text references shop.users(id) on delete set null,
  updated_by            text references shop.users(id) on delete set null,
  constraint ck_coupons_discount_value check (discount_value >= 0),
  constraint ck_coupons_used_count     check (used_count >= 0),
  constraint ck_coupons_dates          check (
    expires_at is null or starts_at is null or expires_at > starts_at
  )
);

-- SQL 第 482 行
create unique index if not exists uq_coupons_code
  on shop.coupons(code) where deleted_at is null;
```

---

### `discount_type` 列舉型別

回頭看 SQL 第 51 行，你會找到：

```sql
create type shop.discount_type as enum ('fixed', 'percentage', 'free_shipping');
```

| 值 | 意思 | discount_value 的用法 |
|----|------|----------------------|
| `fixed` | 固定金額折抵 | 折 100 元 → `discount_value = 100` |
| `percentage` | 百分比折扣 | 打八折 → `discount_value = 20`（折 20%） |
| `free_shipping` | 免運 | `discount_value` 通常為 0 |

---

### 為什麼 CHECK 約束要取名字？

看 SQL 第 477-479 行：

```sql
constraint ck_coupons_discount_value check (discount_value >= 0),
constraint ck_coupons_used_count     check (used_count >= 0),
constraint ck_coupons_dates          check (...)
```

對比匿名寫法：

```sql
check (discount_value >= 0)   -- PostgreSQL 自動產生名字：coupons_discount_value_check
```

**命名的好處**：

1. **ALTER TABLE 時可以精準操作**：
   ```sql
   ALTER TABLE shop.coupons DROP CONSTRAINT ck_coupons_dates;
   -- 如果是匿名的，你得先去查自動產生的名字
   ```

2. **錯誤訊息更清楚**：
   ```
   ERROR: new row violates check constraint "ck_coupons_dates"
   -- 一眼就知道是日期檢查失敗
   ```

3. **Migration 可預測**：CI/CD 不會因為自動命名規則改變而壞掉。

---

### 日期 CHECK 的邏輯拆解

SQL 第 479 行：

```sql
constraint ck_coupons_dates check (
  expires_at is null or starts_at is null or expires_at > starts_at
)
```

這行用白話文說就是：「**如果開始和結束日期都填了，結束必須晚於開始**。」

用真值表來看：

| starts_at | expires_at | 條件結果 | 通過？ |
|-----------|------------|----------|--------|
| NULL | NULL | `true OR true` | 通過 |
| 2025-01-01 | NULL | `true` (第一個 OR) | 通過 |
| NULL | 2025-12-31 | `true` (第二個 OR) | 通過 |
| 2025-01-01 | 2025-12-31 | `12-31 > 01-01` = true | 通過 |
| 2025-12-31 | 2025-01-01 | `01-01 > 12-31` = false | **拒絕** |

> **關鍵**：SQL 的 OR 是短路求值。只要前面有一個 `true`，後面就不看了。

---

### Partial Unique Index — 「軟刪除友善」的唯一約束

SQL 第 482 行：

```sql
create unique index if not exists uq_coupons_code
  on shop.coupons(code) where deleted_at is null;
```

這表示：
- **未刪除的**優惠券，`code` 必須唯一
- **已刪除的**優惠券（`deleted_at IS NOT NULL`），`code` 可以重複

為什麼？想像這個情境：

1. 建立優惠券 `SUMMER2025`
2. 活動結束，軟刪除這張優惠券
3. 明年想再用 `SUMMER2025` → 如果用普通 UNIQUE，會撞到已刪除的那筆

Partial unique index 解決了這個問題：只對「活的」資料做唯一檢查。

---

## 7.2 `shop.addresses` — 收件地址（SQL 第 484-504 行）

```sql
-- SQL 第 484-500 行
create table if not exists shop.addresses (
  id           text primary key default public.generate_ulid(),
  customer_id  text                 not null references shop.users(id) on delete cascade,
  label        shop.address_label not null default 'home',
  recipient    varchar(200)         not null default '',
  phone        varchar(50)          not null default '',
  country_code varchar(10)          not null default '',
  state        varchar(50)          not null default '',
  city         varchar(50)          not null default '',
  zip_code     varchar(20)          not null default '',
  address_1    varchar(255)         not null default '',
  address_2    varchar(255)         not null default '',
  is_default   boolean              not null default false,
  metadata     jsonb                not null default '{}'::jsonb,
  created_at   timestamptz          not null default now(),
  updated_at   timestamptz          not null default now()
);

-- SQL 第 503-504 行
create unique index if not exists uq_addresses_default
  on shop.addresses(customer_id, label) where is_default = true;
```

---

### `address_label` 列舉型別

SQL 第 53 行：

```sql
create type shop.address_label as enum ('home', 'office', 'shipping', 'billing', 'other');
```

同一個客戶可以有多個地址，用 `label` 區分用途。

---

### Partial Unique Index 的精妙設計

SQL 第 503-504 行：

```sql
create unique index ... on shop.addresses(customer_id, label) where is_default = true;
```

翻譯成白話文：

> **「每位客戶在每種地址類型下，最多只能有一個預設地址。」**

具體來說：

| customer_id | label | is_default | 允許？ |
|-------------|-------|------------|--------|
| Alice | home | true | 允許 — Alice 的第一個預設家用地址 |
| Alice | home | true | **拒絕** — Alice 已經有預設 home 了 |
| Alice | home | false | 允許 — 不是預設，不受此 index 限制 |
| Alice | office | true | 允許 — office 是另一種 label |
| Bob | home | true | 允許 — 不同客戶 |

> **重點**：`where is_default = true` 讓這個 index 只「看見」預設地址。
> 非預設地址想建幾筆都行，完全不受限。

### 沒有 Dumb Questions ❓

**Q：為什麼 addresses 用 `on delete cascade` 而 coupons 用 `on delete set null`？**

A：語意不同。

- `addresses.customer_id ON DELETE CASCADE` — 客戶刪除時，他的地址也沒有意義了，一起刪。
- `coupons.created_by ON DELETE SET NULL` — 建立優惠券的管理員離職了，優惠券本身還是有效的，只是把 `created_by` 設成 NULL。

**Q：為什麼地址表沒有 `deleted_at` 做軟刪除？**

A：因為地址跟客戶生命週期綁定（CASCADE）。客戶刪了地址也刪。如果只是客戶想「隱藏」某個地址，可以在 `metadata` 裡加 `{"archived": true}`，或未來加一個 `archived_at` 欄位。

---

# Stage 8：Commerce — 交易核心（SQL 第 507-643 行）

> **這是整個 schema 最重要的部分 — 牽扯到錢。**
>
> 錢的邏輯寫錯，客戶會投訴、會退款、會上新聞。
> 所以你會看到這裡的 CHECK 約束特別多、型別特別嚴格。

---

## 8.1 `shop.orders` — 訂單主表（SQL 第 522-558 行）

```sql
-- SQL 第 522-550 行
create table if not exists shop.orders (
  id                  text primary key default public.generate_ulid(),
  customer_id         text                not null references shop.users(id) on delete restrict,
  parent_id           text references shop.orders(id) on delete set null,
  status              shop.order_status not null default 'pending',
  num_items_sold      integer             not null default 0,
  subtotal            numeric(12,2)       not null default 0,
  tax_total           numeric(12,2)       not null default 0,
  shipping_total      numeric(12,2)       not null default 0,
  discount_total      numeric(12,2)       not null default 0,
  total               numeric(12,2)       not null default 0,
  currency            varchar(3)          not null default 'TWD',
  shipping_address_id text references shop.addresses(id) on delete set null,
  billing_address_id  text references shop.addresses(id) on delete set null,
  returning_customer  boolean,
  note                text                not null default '',
  metadata            jsonb               not null default '{}'::jsonb,
  created_at          timestamptz         not null default now(),
  updated_at          timestamptz         not null default now(),
  deleted_at          timestamptz,
  created_by          text references shop.users(id) on delete set null,
  updated_by          text references shop.users(id) on delete set null,
  constraint ck_orders_num_items check (num_items_sold >= 0),
  constraint ck_orders_subtotal  check (subtotal >= 0),
  constraint ck_orders_tax       check (tax_total >= 0),
  constraint ck_orders_shipping  check (shipping_total >= 0),
  constraint ck_orders_discount  check (discount_total >= 0),
  constraint ck_orders_total     check (total >= 0)
);
```

---

### 6 個金額 CHECK — 為什麼每個都要檢查？

SQL 第 544-549 行，六個 CHECK 確保所有金額 `>= 0`：

```sql
constraint ck_orders_num_items check (num_items_sold >= 0),
constraint ck_orders_subtotal  check (subtotal >= 0),
constraint ck_orders_tax       check (tax_total >= 0),
constraint ck_orders_shipping  check (shipping_total >= 0),
constraint ck_orders_discount  check (discount_total >= 0),
constraint ck_orders_total     check (total >= 0)
```

> **為什麼不寫一個就好？**
>
> 因為每個欄位可能被不同的程式碼路徑更新。
> `subtotal` 由購物車計算，`tax_total` 由稅率引擎計算，`shipping_total` 由物流 API 回傳。
> 每個來源都可能出 bug，所以**每個欄位都要自保**。

---

### `parent_id` — 自參照 FK（子訂單 / 拆單）

SQL 第 525 行：

```sql
parent_id text references shop.orders(id) on delete set null,
```

這是一個**自參照外鍵**（self-referencing FK）。用途：

- **拆單**：一筆訂單拆成多個出貨批次，每批是一個子訂單
- **加購**：原訂單成立後，客戶追加商品
- **退貨重建**：部分退貨後，建立新的子訂單

```
Order #001 (parent)
  ├── Order #001-A (parent_id = #001) — 台北倉出貨
  └── Order #001-B (parent_id = #001) — 高雄倉出貨
```

---

### 🧠 你的大腦在想…

> 「為什麼不用 CHECK 強制 `total = subtotal + tax_total + shipping_total - discount_total`？」

好問題。理論上可以寫：

```sql
constraint ck_orders_total_calc check (
  total = subtotal + tax_total + shipping_total - discount_total
)
```

但**真實電商不會這樣做**，原因：

1. **免運券**：shipping_total 被折掉，但 total 不一定等於上面的公式
2. **點數折抵**：用 500 點折 50 元，這個折抵不在 discount_total 裡
3. **匯率換算**：跨幣別訂單有四捨五入差異
4. **平台抽成**：total 可能是扣掉平台費後的金額

> **結論**：金額驗證應該在 Application Layer（後端程式碼）做，不應該用 CHECK 硬綁。
> Database CHECK 只確保「不是負數」這種基本物理限制。

---

### `returning_customer` — 為什麼用 `boolean` 而不是查詢？

SQL 第 536 行。這是一個**反正規化欄位**。

理論上你可以用子查詢判斷：

```sql
SELECT EXISTS(
  SELECT 1 FROM shop.orders
  WHERE customer_id = ? AND id != current_order_id
);
```

但在訂單列表頁面，如果每筆訂單都跑這個子查詢，效能會很差。
把結果在下單時寫入 `returning_customer`，查詢時直接讀就好。

> 這就是**有意識的反正規化** — 用空間換時間，但你知道為什麼這樣做。

---

## 8.2 `shop.order_items` — 訂單明細（SQL 第 560-583 行）

```sql
-- SQL 第 560-579 行
create table if not exists shop.order_items (
  id                  text primary key default public.generate_ulid(),
  order_id            text          not null references shop.orders(id) on delete cascade,
  product_id          text          not null references shop.products(id) on delete restrict,
  variation_id        text references shop.products(id) on delete set null,
  product_title       varchar(255)  not null default '',   -- snapshot at purchase
  sku                 varchar(100),                        -- snapshot at purchase
  quantity            numeric(10,2) not null default 1,
  unit_price          numeric(12,2) not null default 0,
  gross_revenue       numeric(12,2) not null default 0,
  net_revenue         numeric(12,2) not null default 0,
  coupon_amount       numeric(12,2) not null default 0,
  tax_amount          numeric(12,2) not null default 0,
  shipping_amount     numeric(12,2) not null default 0,
  shipping_tax_amount numeric(12,2) not null default 0,
  created_at          timestamptz   not null default now(),
  updated_at          timestamptz   not null default now(),
  constraint ck_order_items_quantity   check (quantity > 0),
  constraint ck_order_items_unit_price check (unit_price >= 0)
);
```

---

### Snapshot Pattern — 最重要的電商設計模式

注意 SQL 第 565-566 行的註解：

```sql
product_title  varchar(255) not null default '',   -- snapshot at purchase
sku            varchar(100),                        -- snapshot at purchase
```

**為什麼要把商品名稱和 SKU 複製到訂單明細裡？**

想像這個時間線：

```
1月：商品名稱 = "經典白T恤"，價格 = 590
2月：客戶下單買了這件 T 恤
3月：商品改名為 "基本款白T恤"，價格調為 690
4月：客戶看訂單紀錄 → 應該顯示什麼？
```

- **如果用 JOIN**：`SELECT p.title FROM products p JOIN order_items oi ...` → 顯示「基本款白T恤」 → **錯！客戶買的時候叫「經典白T恤」**
- **如果用 Snapshot**：`SELECT oi.product_title FROM order_items oi` → 顯示「經典白T恤」 → **對！**

> **Snapshot = 購買當下的事實記錄。**
>
> 商品可以改名、調價、甚至下架，但訂單明細永遠記著客戶「當時」買了什麼。

---

### `variation_id` — 變體商品

SQL 第 564 行：

```sql
variation_id text references shop.products(id) on delete set null,
```

還記得 Stage 4 的 `products.parent_id` 嗎？一件 T 恤有「白色 M 號」「黑色 L 號」等變體。

- `product_id` = 父商品（T恤）
- `variation_id` = 具體變體（白色 M 號）

為什麼 `product_id` 用 `on delete restrict` 而 `variation_id` 用 `on delete set null`？

- 不能刪除有訂單的主商品（restrict = 保護歷史紀錄）
- 變體可以被整理掉，但訂單還在（set null = 變體沒了，訂單不受影響）

---

### 收入拆解欄位

SQL 第 569-574 行記錄了一筆訂單明細的完整收入拆解：

| 欄位 | 意思 |
|------|------|
| `gross_revenue` | 毛收入（quantity × unit_price） |
| `net_revenue` | 淨收入（扣除折扣和稅後） |
| `coupon_amount` | 此明細分攤到的優惠券折扣 |
| `tax_amount` | 稅額 |
| `shipping_amount` | 運費分攤 |
| `shipping_tax_amount` | 運費的稅額 |

> 這些欄位讓你可以直接在 order_items 層級做**收入分析**，不需要回去 JOIN orders 表重算。

---

## 8.3 `shop.order_coupons` — 訂單-優惠券關聯表（SQL 第 585-593 行）

```sql
-- SQL 第 585-591 行
create table if not exists shop.order_coupons (
  order_id         text          not null references shop.orders(id) on delete cascade,
  coupon_id        text          not null references shop.coupons(id) on delete restrict,
  discount_amount  numeric(12,2) not null default 0,
  created_at       timestamptz   not null default now(),
  primary key (order_id, coupon_id)
);
```

這是一張經典的 **Junction Table**（關聯表 / 多對多中間表）。

- 一筆訂單可以用多張優惠券
- 一張優惠券可以被多筆訂單使用
- `discount_amount` 記錄**這張券在這筆訂單**實際折了多少

為什麼用**複合主鍵** `(order_id, coupon_id)` 而不是另建 `id`？

因為同一張券不應該在同一筆訂單中使用兩次。複合主鍵同時解決了：
1. 唯一性約束（不重複使用）
2. 主鍵需求（不需要額外的 id 欄位）

---

## 8.4 `shop.payments` — 付款記錄（SQL 第 595-622 行）

```sql
-- SQL 第 595-616 行
create table if not exists shop.payments (
  id                text primary key default public.generate_ulid(),
  order_id          text                  not null references shop.orders(id) on delete restrict,
  customer_id       text                  not null references shop.users(id) on delete restrict,
  amount            numeric(12,2)         not null default 0,
  currency          varchar(3)            not null default 'TWD',
  method            shop.payment_method not null,
  provider          varchar(50)           not null default '',
  provider_tx_id    varchar(255),
  status            shop.payment_status not null default 'pending',
  paid_at           timestamptz,
  refunded_at       timestamptz,
  refund_amount     numeric(12,2)         not null default 0,
  failure_reason    text,
  metadata          jsonb                 not null default '{}'::jsonb,
  created_at        timestamptz           not null default now(),
  updated_at        timestamptz           not null default now(),
  created_by        text references shop.users(id) on delete set null,
  updated_by        text references shop.users(id) on delete set null,
  constraint ck_payments_amount        check (amount >= 0),
  constraint ck_payments_refund_amount check (refund_amount >= 0 and refund_amount <= amount)
);
```

---

### 付款生命週期

```
pending → processing → paid ────→ (完成)
                         │
                         ├──→ refunded        (全額退款)
                         └──→ partially_refunded (部分退款)

pending → processing → failed (失敗 → 建立新的 payment 記錄重試)
```

幾個關鍵設計決策：

**1. 一筆訂單可以有多筆 payment**

為什麼？

- 第一次刷卡失敗 → 建立第二筆 payment 重試
- 分期付款 → 每期一筆 payment
- 部分退款 → 原始 payment 狀態改為 `partially_refunded`

**2. `provider` + `provider_tx_id` — 外部金流對帳**

```sql
provider       varchar(50)  not null default '',   -- 'stripe', 'linepay', 'ecpay'
provider_tx_id varchar(255),                        -- 金流商的交易編號
```

當客戶說「我付了但沒收到貨」，你需要拿 `provider_tx_id` 去金流商後台查對帳。

SQL 第 621-622 行還建了 partial index：

```sql
create index if not exists idx_payments_provider_tx
  on shop.payments(provider_tx_id) where provider_tx_id is not null;
```

> 不是所有 payment 都有 provider_tx_id（例如貨到付款在建立時還沒有），所以用 partial index 節省空間。

**3. 退款金額 CHECK**

SQL 第 615 行：

```sql
constraint ck_payments_refund_amount check (refund_amount >= 0 and refund_amount <= amount)
```

翻譯：**退款金額不能是負數，也不能超過付款金額。**

你不可能退 1,500 元給一個只付了 1,000 元的人。

---

### `payment_status` 列舉型別

SQL 第 49 行：

```sql
create type shop.payment_status as enum (
  'pending', 'processing', 'paid', 'failed',
  'refunded', 'partially_refunded', 'cancelled'
);
```

### `payment_method` 列舉型別

SQL 第 50 行：

```sql
create type shop.payment_method as enum (
  'credit_card', 'debit_card', 'line_pay', 'apple_pay',
  'google_pay', 'bank_transfer', 'cash_on_delivery', 'points'
);
```

> 注意 `points` 也是一種付款方式 — 這和下面的 `point_rewards` 表配合使用。

---

## 8.5 `shop.point_rewards` — 點數帳本（SQL 第 624-636 行）

```sql
-- SQL 第 625-632 行
create table if not exists shop.point_rewards (
  id           text primary key default public.generate_ulid(),
  customer_id  text   not null references shop.users(id) on delete restrict,
  order_id     text references shop.orders(id) on delete restrict,
  points       bigint not null,   -- +earn, -spend
  description  text   not null default '',
  created_at   timestamptz not null default now()
);
```

### Append-Only Ledger — 只進不改的帳本

這張表的設計哲學：**只有 INSERT，永遠不 UPDATE 也不 DELETE。**

每一筆記錄就是一個「異動事件」：

| points | description | 意思 |
|--------|-------------|------|
| +100 | 訂單 #001 購物回饋 | 賺點 |
| -50 | 訂單 #002 折抵 | 花點 |
| +50 | 退貨 #002 退還點數 | 退點 |
| +200 | 生日禮 | 贈點 |

### 🧠 你的大腦在想…

> 「為什麼不在 users 表加一個 `point_balance` 欄位？每次加減就好了啊。」

因為**兩個來源的真相 = 遲早不同步**。

想像這個情境：

```
users.point_balance = 150
point_rewards 表的 SUM(points) = 200
```

誰對？你不知道。是忘了扣點？還是多扣了？沒有記錄可查。

**Append-only 的好處**：

1. **完整的稽核軌跡**：每一筆變動都有記錄，可以追溯
2. **單一真相來源**：餘額永遠是 `SUM(points)`，沒有第二個數字可以矛盾
3. **易除錯**：出問題時，從頭到尾看記錄就能找到原因
4. **併發安全**：不需要 `UPDATE balance = balance + 100` 這種容易 race condition 的操作

> **銀行也是這樣做的。** 你的存款餘額不是存在某個欄位裡的數字，而是所有交易記錄的加總。

---

## 8.6 `shop.point_balances` — 點數餘額 VIEW（SQL 第 638-643 行）

```sql
-- SQL 第 638-643 行
create or replace view shop.point_balances
  with (security_invoker = true)
  as
  select customer_id, coalesce(sum(points), 0) as balance
  from shop.point_rewards
  group by customer_id;
```

### `security_invoker = true` 是什麼？

PostgreSQL 的 VIEW 預設用**建立者的權限**（security_definer）來執行。

也就是說，如果 DBA 建了這個 view，任何人查這個 view 都等於用 DBA 的權限在查 — **繞過了 RLS！**

`security_invoker = true` 改成用**呼叫者的權限**：

- 客戶 A 查 `point_balances` → 只看到自己的點數（因為 RLS 限制）
- DBA 查 `point_balances` → 看到所有人的點數（DBA 不受 RLS 限制）

> **在 Supabase 裡，這是必須的。** 因為 Supabase 靠 RLS 做權限控管，如果 view 繞過 RLS，等於把所有客戶的點數餘額公開給所有人。

### `COALESCE(SUM(points), 0)` — 為什麼需要 COALESCE？

如果一個客戶**從來沒有任何點數記錄**，`SUM(points)` 會回傳 `NULL`，不是 `0`。

`COALESCE` 把 `NULL` 轉成 `0`，讓前端不用額外處理空值。

---

## 重點子彈 🎯

### Stage 7

- **FK 依賴順序**：被 REFERENCES 的表必須先建。addresses 和 coupons 是 orders 的前置依賴。
- **命名 CHECK 約束**：`constraint ck_xxx check (...)` 比匿名 CHECK 好維護、好除錯、好 migrate。
- **Partial Unique Index**：`WHERE deleted_at IS NULL` 讓軟刪除和唯一約束和平共存。
- **地址預設 index**：`WHERE is_default = true` 限制「每客戶每種 label 最多一個預設」。
- **`discount_type` enum**：三種折扣類型（fixed / percentage / free_shipping）用 enum 約束合法值。

### Stage 8

- **金額 CHECK >= 0**：每個金額欄位獨立保護，因為它們來自不同的計算來源。
- **不要用 CHECK 驗證合計公式**：真實電商的 total 計算太複雜（免運、點數、匯率），交給後端處理。
- **Snapshot Pattern**：order_items 複製 product_title 和 sku，確保歷史訂單不受商品變更影響。
- **Junction Table (order_coupons)**：複合主鍵同時解決唯一性和主鍵需求。
- **Payment lifecycle**：pending → processing → paid → refunded，一筆訂單可以有多筆 payment。
- **`refund_amount <= amount` CHECK**：退款不能超過付款金額，數學上的硬限制。
- **Append-only Ledger (point_rewards)**：永遠不 UPDATE，餘額永遠用 SUM 計算，避免兩個真相來源。
- **`security_invoker = true`**：VIEW 遵守呼叫者的 RLS，不繞過權限控管。

---

## 動手做 🛠️

### 練習 1：優惠券日期驗證

試著插入以下資料，預測哪些會成功、哪些會被 CHECK 擋下：

```sql
-- (a)
INSERT INTO shop.coupons (code, discount_value, starts_at, expires_at)
VALUES ('TEST1', 100, '2025-12-01', '2025-06-01');

-- (b)
INSERT INTO shop.coupons (code, discount_value, starts_at, expires_at)
VALUES ('TEST2', 100, NULL, '2025-12-31');

-- (c)
INSERT INTO shop.coupons (code, discount_value)
VALUES ('TEST3', -50);
```

<details>
<summary>答案</summary>

- **(a) 拒絕** — `expires_at (06-01) > starts_at (12-01)` 為 false，違反 `ck_coupons_dates`
- **(b) 通過** — `starts_at IS NULL` 為 true，短路求值直接通過
- **(c) 拒絕** — `discount_value >= 0` 為 false，違反 `ck_coupons_discount_value`

</details>

### 練習 2：理解 Snapshot Pattern

假設你有以下情境：

```sql
-- 1月：商品上架
INSERT INTO shop.products (id, title, price) VALUES ('P001', 'MacBook Air', 35900);

-- 2月：客戶下單
INSERT INTO shop.order_items (order_id, product_id, product_title, sku, unit_price, quantity)
VALUES ('O001', 'P001', 'MacBook Air', 'MBA-2025-M3', 35900, 1);

-- 3月：商品改名調價
UPDATE shop.products SET title = 'MacBook Air M3', price = 37900 WHERE id = 'P001';
```

問題：
1. 客戶 3 月查看 2 月的訂單，應該顯示什麼商品名稱和價格？
2. 如果你用 `JOIN products` 來顯示，會出什麼問題？
3. Snapshot pattern 如何解決這個問題？

### 練習 3：Append-Only Ledger 計算

給定以下 point_rewards 記錄：

| customer_id | points | description |
|-------------|--------|-------------|
| C001 | +500 | 首購回饋 |
| C001 | -200 | 訂單折抵 |
| C001 | +100 | 評價獎勵 |
| C001 | -50 | 訂單折抵 |

1. 寫一個 SQL 查詢計算 C001 的點數餘額
2. 如果你在 users 表存了 `point_balance = 400`，但計算結果是 350，你怎麼找出差異？
3. 為什麼 append-only 設計讓除錯更容易？

### 練習 4：付款退款驗證

試著預測以下操作是否合法：

```sql
-- 付了 1000 元
INSERT INTO shop.payments (order_id, customer_id, amount, method, status)
VALUES ('O001', 'C001', 1000, 'credit_card', 'paid');

-- 嘗試退 1200 元
UPDATE shop.payments SET refund_amount = 1200, status = 'refunded'
WHERE order_id = 'O001';
```

<details>
<summary>答案</summary>

**拒絕** — 違反 `ck_payments_refund_amount`：`refund_amount (1200) <= amount (1000)` 為 false。

你最多只能退 1000 元。如果客戶真的需要退超過付款金額（例如加上補償），應該用另一筆獨立的 payment 記錄處理。

</details>

---

> **下一章**：Stage 9 — Security（RLS + Policies + GRANTs）。
> 我們會學到如何用 Row Level Security 確保每個客戶只能看到自己的訂單和點數。

---

[← 03 分類 + 庫存](03_taxonomy-inventory.md) | [05 安全 RLS →](05_security-rls.md)

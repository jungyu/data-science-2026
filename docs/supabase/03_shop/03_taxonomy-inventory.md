# Stage 5-6：分類系統 + 庫存模式

> **對應 SQL**：[`002_shop_schema.sql`](../migrations/002_shop_schema.sql) 第 356-445 行
>
> 這一章你會學到兩件事：
> 1. 如何用三張表搞定「所有分類需求」（Taxonomy）
> 2. 如何讓庫存同時回答「現在有多少」和「為什麼變了」（Inventory）

---

## Stage 5：Taxonomy — 分類系統（SQL 第 356-402 行）

### 你的大腦在想 🧠

> 「商品需要分類（3C、食品）、標籤（新品、熱銷）、品牌（Nike、Apple）、顏色（紅、藍）……
> 難道每種分類都要建一張表嗎？」

不用。WordPress 20 年前就解決了這個問題——**三張表搞定一切**。

---

### 三表模式總覽

```
terms（字彙表）           ← 純粹的「詞」：Electronics、Red、Nike、Summer
  │
term_taxonomy（分類法）   ← 詞 + 分類維度
  │                        「Electronics」是 category
  │                        「Red」是 color
  │                        「Nike」是 brand
  │
term_relationships        ← 多型態關聯（object_id → 任何實體）
                            商品 'ABC' ↔ category 'Electronics'
                            商品 'ABC' ↔ brand 'Nike'
```

把它想成圖書館：

- **terms** = 卡片目錄上的「字」
- **term_taxonomy** = 這張卡片放在哪個「抽屜」（分類、標籤、品牌……）
- **term_relationships** = 哪些「書」被貼了這張卡片

---

### 5.1 `shop.terms` — 字彙表（SQL 第 367-378 行）

```sql
-- SQL 第 367-375 行
create table if not exists shop.terms (
  id         text primary key default public.generate_ulid(),
  name       varchar(200)  not null,
  slug       varchar(255)  not null,
  term_group integer       not null default 0,
  metadata   jsonb         not null default '{}'::jsonb,
  created_at timestamptz   not null default now(),
  updated_at timestamptz   not null default now()
);

-- SQL 第 377 行：slug 必須唯一
create unique index if not exists uq_terms_slug on shop.terms(slug);
-- SQL 第 378 行：metadata 用 GIN 索引加速 jsonb 查詢
create index if not exists idx_terms_metadata on shop.terms using gin(metadata);
```

| 欄位 | 型別 | 說明 |
|------|------|------|
| `id` | TEXT (ULID) | 主鍵，自動產生 |
| `name` | VARCHAR(200) | 顯示名稱，例如「電子產品」 |
| `slug` | VARCHAR(255) | URL-safe 識別碼，例如 `electronics`（**唯一**） |
| `term_group` | INTEGER | 分組編號，預設 0，可用來把相關詞歸在一起 |
| `metadata` | JSONB | 額外資料（圖片 URL、排序權重……），GIN 索引 |

**重點**：這張表只管「詞彙」本身，不管它是分類、標籤還是品牌。

---

### 5.2 `shop.term_taxonomy` — 分類法（SQL 第 380-392 行）

```sql
-- SQL 第 380-390 行
create table if not exists shop.term_taxonomy (
  id          text primary key default public.generate_ulid(),
  term_id     text         not null references shop.terms(id) on delete cascade,
  taxonomy    varchar(50)  not null,   -- 'category', 'tag', 'brand', 'color'
  description text         not null default '',
  parent_id   text references shop.term_taxonomy(id) on delete set null,
  count       integer      not null default 0,
  created_at  timestamptz  not null default now(),
  updated_at  timestamptz  not null default now(),
  constraint  ak_term_taxonomy unique (term_id, taxonomy)
);
```

| 欄位 | 型別 | 說明 |
|------|------|------|
| `term_id` | TEXT FK → terms | 指向哪個詞彙 |
| `taxonomy` | VARCHAR(50) | 分類維度：`'category'`、`'tag'`、`'brand'`、`'color'` |
| `parent_id` | TEXT FK → self | **自我引用**，讓分類可以有層級 |
| `count` | INTEGER | 反正規化計數——這個分類下有幾個東西 |

#### 關鍵約束

```
constraint ak_term_taxonomy unique (term_id, taxonomy)
```

**同一個詞可以出現在不同維度**。例如「Apple」可以同時是：
- brand 維度下的 Apple（品牌）
- category 維度下的 Apple（水果分類）

但同一個詞在同一個維度只能出現一次。

#### 層級分類（parent_id）

```
Electronics (parent_id = null)
  ├── Computers (parent_id → Electronics)
  │     ├── Laptops
  │     └── Desktops
  └── Phones (parent_id → Electronics)
        ├── iPhone
        └── Android
```

`ON DELETE SET NULL`：刪除父分類時，子分類不會跟著消失，只是變成頂層分類。

---

### 5.3 `shop.term_relationships` — 多型態關聯（SQL 第 394-402 行）

```sql
-- SQL 第 394-400 行
create table if not exists shop.term_relationships (
  object_id        text    not null,   -- 多型態：product、order 等
  term_taxonomy_id text    not null references shop.term_taxonomy(id) on delete cascade,
  term_order       integer not null default 0,
  created_at       timestamptz not null default now(),
  primary key (object_id, term_taxonomy_id)
);
```

| 欄位 | 型別 | 說明 |
|------|------|------|
| `object_id` | TEXT | **多型態 ID** — 可以是 product ID、order ID、任何東西 |
| `term_taxonomy_id` | TEXT FK → term_taxonomy | 指向哪個分類法紀錄 |
| `term_order` | INTEGER | 排序用 |

**複合主鍵**：`(object_id, term_taxonomy_id)` — 同一個物件不能被同一個分類貼兩次。

---

### 你的大腦在想 🧠

> 「等等，`object_id` 沒有 FK 約束？這樣不會有孤兒資料嗎？」

你說得對。這是刻意的設計取捨。

#### 多型態 FK 的取捨

| | 優點 | 缺點 |
|---|------|------|
| **用多型態** | 一組表處理**所有**分類維度；新增維度不用改 schema | 沒有 FK 約束，可能產生孤兒紀錄 |
| **用專屬表** | 完整的參照完整性 | 每種分類都要建表，schema 膨脹 |

**緩解策略**：
1. 應用層驗證 — 寫入前檢查 `object_id` 是否存在
2. 定期清理 — 排程 job 掃描孤兒紀錄
3. Trigger — 在相關表刪除時連帶清理 `term_relationships`

---

### 沒有 Dumb Questions ❓

**Q：什麼時候該用 Taxonomy，什麼時候該用專屬表？**

| 場景 | Taxonomy | 專屬表 |
|------|:--------:|:------:|
| 商品分類 / 標籤 / 品牌（維度常常新增） | ✅ | |
| 商品顏色 / 尺寸（屬性） | ✅ | |
| 會員等級（固定、少量、有特殊邏輯） | | ✅ |
| 付款方式（需要特殊欄位和流程） | | ✅ |
| SEO 關鍵字（純標記，無階層） | ✅ | |

**經驗法則**：如果這個分類「只是貼標籤」→ Taxonomy；如果「有自己的商業邏輯」→ 專屬表。

**Q：`count` 欄位不是反正規化嗎？為什麼不用 COUNT() 查？**

A：是反正規化。但在分類列表頁面，你不想每次都 JOIN + GROUP BY 來算數量。`count` 欄位可以用 Trigger 或排程更新，換取列表頁的查詢速度。

**Q：`term_group` 是做什麼用的？**

A：把相關的字彙分成群組。例如 term_group = 1 是「顏色系列」、term_group = 2 是「尺寸系列」。在 WordPress 裡這個欄位很少用到，但保留彈性。

---

## Stage 6：Inventory — 庫存模式（SQL 第 405-445 行）

### 你的大腦在想 🧠

> 「庫存不就是一個數字嗎？建一張表存 quantity 不就好了？」

如果老闆問你：**「上週三為什麼少了 50 件？」**

你只有一張 `stocks` 表，上面寫著 `quantity = 150`。
你能回答嗎？**不能。** 因為你只知道「現在有多少」，不知道「什麼時候變的、為什麼變的」。

**這就是為什麼庫存永遠需要兩張表。**

---

### 雙表模式：快照 + 日誌

```
stocks（快照）                      inventory_movements（日誌）
┌───────────────────────┐          ┌────────────────────────────┐
│ store_id + product_id │          │ store_id + product_id      │
│ quantity: 50          │   ←────  │ quantity_delta: -2          │
│                       │          │ reason: 'sale'              │
│ （現在有多少）         │          │ reference_id: 'ORDER-123'   │
└───────────────────────┘          │ （為什麼變了）              │
                                   └────────────────────────────┘
```

- **stocks**：隨時可以 UPDATE — 它是**快照**，永遠反映「此刻」的狀態
- **inventory_movements**：永遠只能 INSERT — 它是**日誌**，一旦寫入就不能改

---

### 6.1 `shop.stocks` — 庫存快照（SQL 第 415-427 行）

```sql
-- SQL 第 415-425 行
create table if not exists shop.stocks (
  id         text primary key default public.generate_ulid(),
  store_id   text          not null references shop.stores(id) on delete cascade,
  product_id text          not null references shop.products(id) on delete restrict,
  quantity   numeric(10,2) not null default 0,
  low_stock_threshold integer,
  created_at timestamptz   not null default now(),
  updated_at timestamptz   not null default now(),
  constraint ck_stocks_quantity  check (quantity >= 0),
  constraint ck_stocks_threshold check (low_stock_threshold is null or low_stock_threshold >= 0)
);

-- SQL 第 427 行：每個門市×商品只能有一列
create unique index if not exists uq_stocks_store_product
  on shop.stocks(store_id, product_id);
```

| 欄位 | 型別 | 說明 |
|------|------|------|
| `store_id` | TEXT FK → stores | 哪間門市 |
| `product_id` | TEXT FK → products | 哪個商品 |
| `quantity` | NUMERIC(10,2) | 目前數量（**CHECK >= 0**，不能變負數） |
| `low_stock_threshold` | INTEGER | 低庫存警報門檻（可為 NULL = 不設警報） |

#### 關鍵設計

1. **唯一索引** `(store_id, product_id)` — 每個門市的每個商品只有**一列**
2. **`ON DELETE RESTRICT`** on product_id — 有庫存紀錄的商品**不能刪除**
3. **`NUMERIC(10,2)`** — 不是 INTEGER！因為有些商品按重量賣（例如 0.5 公斤）
4. **`CHECK (quantity >= 0)`** — 資料庫層面阻止超賣

---

### 6.2 `shop.inventory_movements` — 庫存異動日誌（SQL 第 429-445 行）

```sql
-- SQL 第 429-440 行
create table if not exists shop.inventory_movements (
  id             text primary key default public.generate_ulid(),
  store_id       text                 not null references shop.stores(id) on delete restrict,
  product_id     text                 not null references shop.products(id) on delete restrict,
  quantity_delta  numeric(10,2)       not null,   -- 正數=入庫，負數=出庫
  reason         shop.movement_reason not null default 'manual',
  reference_type varchar(50),
  reference_id   text,
  note           text                 not null default '',
  created_at     timestamptz          not null default now(),
  created_by     text references shop.users(id) on delete set null
);
```

| 欄位 | 型別 | 說明 |
|------|------|------|
| `quantity_delta` | NUMERIC(10,2) | **正數** = 入庫，**負數** = 出庫 |
| `reason` | shop.movement_reason | 異動原因（enum，見下方） |
| `reference_type` | VARCHAR(50) | 來源類型，例如 `'order'`、`'transfer'` |
| `reference_id` | TEXT | 來源 ID，例如 `'ORDER-123'` |
| `created_by` | TEXT FK → users | 誰做了這次異動 |

#### `movement_reason` 列舉（SQL 第 52 行）

```sql
create type shop.movement_reason as enum
  ('sale', 'return', 'restock', 'adjustment', 'manual', 'transfer');
```

| 值 | 說明 | quantity_delta |
|----|------|:-------------:|
| `sale` | 賣出 | 負數 |
| `return` | 退貨 | 正數 |
| `restock` | 進貨 | 正數 |
| `adjustment` | 盤點調整 | 正或負 |
| `manual` | 人工操作（預設） | 正或負 |
| `transfer` | 門市間調撥 | 一正一負（成對） |

每一筆異動都有明確的**原因**，不是一個含糊的 note 欄位。

#### 索引設計（SQL 第 442-445 行）

```sql
-- 按門市+商品查詢歷史
create index if not exists idx_inv_movements_store_product
  on shop.inventory_movements(store_id, product_id);

-- 按時間範圍查詢
create index if not exists idx_inv_movements_created
  on shop.inventory_movements(created_at);

-- 部分索引：只索引有 reference 的紀錄
create index if not exists idx_inv_movements_ref
  on shop.inventory_movements(reference_type, reference_id)
  where reference_type is not null;
```

**部分索引**（partial index）是個好招：不是每筆異動都有 `reference_type`（例如手動盤點可能沒有），所以只在有值的時候建索引，節省空間。

---

### 沒有 Dumb Questions ❓

**Q：為什麼 `quantity` 用 `NUMERIC(10,2)` 而不是 `INTEGER`？**

A：有些商品按重量或容量賣。例如咖啡豆 0.5 公斤、布料 2.3 公尺。如果用 INTEGER，這些商品的庫存管理就會出問題。

**Q：為什麼 `product_id` 的 FK 用 `ON DELETE RESTRICT` 而不是 `CASCADE`？**

A：有庫存紀錄的商品不應該被直接刪除。想像你刪了一個商品，所有異動紀錄也跟著消失——老闆查帳就抓狂了。正確做法是先清空庫存、確認異動紀錄不再需要（或 archive），再刪除商品。

**Q：`inventory_movements` 為什麼沒有 `updated_at`？**

A：因為它是 **append-only** — 一旦寫入就**永遠不改**。如果盤點發現錯誤，正確做法是寫一筆新的 `adjustment`，不是回去改舊的紀錄。這是**帳本原則**（ledger principle）。

**Q：`stocks` 和 `movements` 的數字會不會對不上？**

A：會。這是快照 + 日誌模式的已知風險。緩解方式：
1. 用 Trigger 讓每次 INSERT movements 自動更新 stocks
2. 排程 job 做核對：`SELECT SUM(quantity_delta) FROM movements` 應該等於 `stocks.quantity`
3. 發現差異時寫一筆 `adjustment` 修正

**Q：門市間調撥（transfer）怎麼記？**

A：同一批操作寫兩筆 movement：
- 門市 A：`quantity_delta = -10, reason = 'transfer', reference_id = 'TRF-001'`
- 門市 B：`quantity_delta = +10, reason = 'transfer', reference_id = 'TRF-001'`

用同一個 `reference_id` 把它們關聯起來。

---

### 你的大腦在想 🧠

> 「所以每次賣一件商品，我要同時做兩件事：
> 1. UPDATE stocks SET quantity = quantity - 1
> 2. INSERT INTO inventory_movements (quantity_delta = -1, reason = 'sale')
>
> 這不就需要 Transaction 嗎？」

**完全正確。** 這兩個操作必須包在同一個 Transaction 裡，要嘛都成功、要嘛都不做。
這也是為什麼 README 的「進階挑戰」建議你把它包成一個 `plpgsql` function。

---

## 重點子彈 🎯

### Stage 5 — Taxonomy

- ✅ **三表模式**：`terms`（字彙）→ `term_taxonomy`（分類法）→ `term_relationships`（關聯）
- ✅ **一組表打天下**：分類、標籤、品牌、顏色……都用同一組表，靠 `taxonomy` 欄位區分
- ✅ **唯一約束** `(term_id, taxonomy)`：同一個詞在同一個維度只能出現一次
- ✅ **層級分類**：`parent_id` 自我引用，支援無限層級
- ✅ **多型態 FK**：`object_id` 是 TEXT、沒有 FK 約束 — 換取彈性，犧牲參照完整性
- ✅ **slug 唯一索引**：URL-safe 的識別碼，GIN 索引加速 metadata 查詢

### Stage 6 — Inventory

- ✅ **快照 + 日誌**：`stocks`（現在有多少）+ `inventory_movements`（為什麼變了）
- ✅ **stocks 可以 UPDATE**，**movements 永遠只能 INSERT**（append-only / 帳本原則）
- ✅ **NUMERIC(10,2)**：支援按重量、容量等非整數單位的商品
- ✅ **CHECK >= 0**：資料庫層面阻止超賣
- ✅ **ON DELETE RESTRICT**：有庫存紀錄的商品不能被刪除
- ✅ **movement_reason enum**：六種明確原因，不是含糊的文字欄位
- ✅ **部分索引**：`WHERE reference_type IS NOT NULL` — 只索引有來源的紀錄
- ✅ **唯一索引** `(store_id, product_id)`：每個門市×商品只有一列快照

---

## 動手做 🛠️

### 練習 1：建立分類結構

在 Supabase SQL Editor 裡，建立以下分類結構：

```sql
-- 1. 新增字彙
insert into shop.terms (name, slug) values
  ('電子產品', 'electronics'),
  ('手機',     'phones'),
  ('筆電',     'laptops'),
  ('紅色',     'red'),
  ('Apple',    'apple');

-- 2. 把字彙放進分類法
-- 先建頂層分類
insert into shop.term_taxonomy (term_id, taxonomy, description)
  select id, 'category', '頂層分類'
  from shop.terms where slug = 'electronics';

-- 再建子分類（parent_id 指向「電子產品」的 term_taxonomy id）
insert into shop.term_taxonomy (term_id, taxonomy, parent_id)
  select t.id, 'category', tt.id
  from shop.terms t, shop.term_taxonomy tt
  where t.slug = 'phones'
    and tt.term_id = (select id from shop.terms where slug = 'electronics');

-- 3. 同一個字「Apple」同時存在兩個維度
insert into shop.term_taxonomy (term_id, taxonomy)
  select id, 'brand' from shop.terms where slug = 'apple';

insert into shop.term_taxonomy (term_id, taxonomy)
  select id, 'category' from shop.terms where slug = 'apple';

-- 4. 驗證：Apple 應該出現兩次（brand + category）
select t.name, tt.taxonomy
from shop.terms t
join shop.term_taxonomy tt on tt.term_id = t.id
where t.slug = 'apple';
```

### 練習 2：庫存異動流程

模擬一次完整的「進貨 → 賣出 → 查帳」流程：

```sql
-- 假設你已有 store_id 和 product_id（用你自己的資料替換）

-- 1. 進貨 100 件
begin;
  -- 更新快照
  insert into shop.stocks (store_id, product_id, quantity, low_stock_threshold)
  values ('YOUR_STORE_ID', 'YOUR_PRODUCT_ID', 100, 10)
  on conflict (store_id, product_id)
  do update set quantity = shop.stocks.quantity + 100,
                updated_at = now();

  -- 記錄異動
  insert into shop.inventory_movements
    (store_id, product_id, quantity_delta, reason, note)
  values
    ('YOUR_STORE_ID', 'YOUR_PRODUCT_ID', 100, 'restock', '首批進貨');
commit;

-- 2. 賣出 3 件
begin;
  update shop.stocks
  set quantity = quantity - 3, updated_at = now()
  where store_id = 'YOUR_STORE_ID'
    and product_id = 'YOUR_PRODUCT_ID';

  insert into shop.inventory_movements
    (store_id, product_id, quantity_delta, reason, reference_type, reference_id)
  values
    ('YOUR_STORE_ID', 'YOUR_PRODUCT_ID', -3, 'sale', 'order', 'ORD-001');
commit;

-- 3. 查帳：這個商品的所有異動紀錄
select reason, quantity_delta, reference_type, reference_id, created_at
from shop.inventory_movements
where store_id = 'YOUR_STORE_ID'
  and product_id = 'YOUR_PRODUCT_ID'
order by created_at;

-- 4. 驗算：movements 加總應該等於 stocks.quantity
select
  s.quantity as snapshot_qty,
  (select sum(m.quantity_delta)
   from shop.inventory_movements m
   where m.store_id = s.store_id
     and m.product_id = s.product_id) as calculated_qty
from shop.stocks s
where s.store_id = 'YOUR_STORE_ID'
  and s.product_id = 'YOUR_PRODUCT_ID';
-- 如果這兩個數字不一樣，就該寫一筆 adjustment 了！
```

### 練習 3：思考題

1. 如果 `inventory_movements` 預期每天新增 10 萬筆，你會怎麼優化？（提示：想想 `PARTITION BY RANGE`）
2. 如何用 SQL 找出「過去 7 天庫存低於警報門檻的門市×商品」？
3. 如果要支援「批次到期日」（例如食品保質期），現有 schema 該怎麼擴充？

---

> **下一章**：[`04_coupons-commerce.md`](04_coupons-commerce.md) — Stage 7-8：折扣券 + 交易核心

---

[← 02 組織 + 商品](02_organization-catalog.md) | [04 折扣 + 交易 →](04_coupons-commerce.md)

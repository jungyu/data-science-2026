# Head First 組織層級 + 商品建模 — Stage 3-4

> **"公司開門市、門市請店員、店員賣商品——資料庫只是把這件事寫成表格。"**

對照檔案：[`002_shop_schema.sql`](../migrations/002_shop_schema.sql) **第 195–353 行**

在 Stage 1-2 我們蓋好了地基（ULID、enum、extensions）和身分橋接。現在要開始建「業務」了——誰擁有這家店？店開在哪？誰在裡面上班？賣什麼東西？

這兩個 Stage 會教你三件事：

1. **階層關係**的建模技巧（Company → Store → Staff）
2. **Soft Delete** 的設計取捨
3. **商品目錄**的欄位設計哲學（什麼該是欄位、什麼該丟 JSONB）

---

## Stage 3：Organization（SQL 第 195–263 行）

### 大局觀：三層架構

```
shop.companies   （品牌 / 公司）
  └── shop.stores      （門市 / 倉庫）
       └── shop.store_staff  （店員，附帶角色）
```

這就是一個標準的「總部 → 分店 → 人員」結構。現實世界長什麼樣，資料庫就建什麼樣。

---

### 3-1 `shop.companies`（SQL 第 203–224 行）

打開 SQL 檔案，找到第 203 行：

```sql
create table if not exists shop.companies (
  id              text primary key default public.generate_ulid(),
  name            varchar(100)       not null,
  type            shop.company_type not null default 'retailer',
  supervisor_id   text references shop.users(id) on delete set null,
  description     text               not null default '',
  country_code    varchar(10)        not null default '',
  tax_id          varchar(50)        not null default '',
  url             varchar(255)       not null default '',
  email           varchar(255)       not null default '',
  phone           varchar(50)        not null default '',
  metadata        jsonb              not null default '{}'::jsonb,
  created_at      timestamptz        not null default now(),
  updated_at      timestamptz        not null default now(),
  deleted_at      timestamptz,
  created_by      text references shop.users(id) on delete set null,
  updated_by      text references shop.users(id) on delete set null
);
```

> ### 你的大腦在想 🧠
>
> **「`supervisor_id` 用 `ON DELETE SET NULL`？那主管離職了怎麼辦？」**
>
> 好問題。SET NULL 的意思是：如果那個 user 被刪了，supervisor_id 會被設成 NULL——公司還在，只是暫時沒有主管。
>
> 對比一下：如果你用 CASCADE，刪主管就會連公司一起刪——這顯然是災難。
>
> 如果你用 RESTRICT，主管帳號就刪不掉——但有時候你確實需要先砍帳號、再補上新主管。
>
> **SET NULL 是「保留記錄、清除引用」的最安全選擇。**

#### 值得注意的欄位

| 欄位 | 設計理由 |
|------|---------|
| `type` | 用 `shop.company_type` enum，不是 varchar。enum 是資料庫層級的約束，比應用層驗證更可靠。 |
| `metadata` | JSONB 萬用口袋。公司的 logo URL、營業時間、特殊設定⋯⋯不值得為它們各開一個欄位的東西，全丟這裡。 |
| `deleted_at` | Soft delete 標記。`NULL` = 活的，有值 = 被刪了。後面會詳細講。 |
| `created_by` / `updated_by` | 審計欄位（audit fields）。誰建的？誰改的？出事可以追。 |

#### 索引設計（SQL 第 222–224 行）

```sql
create index idx_companies_supervisor on shop.companies(supervisor_id)
  where supervisor_id is not null;                          -- 第 222 行

create index idx_companies_metadata on shop.companies
  using gin(metadata);                                      -- 第 223 行

create index idx_companies_active on shop.companies(id)
  where deleted_at is null;                                 -- 第 224 行
```

重點是第 224 行的 **partial index**：只索引 `deleted_at IS NULL` 的記錄。為什麼？

因為 99% 的查詢都是「找活的公司」。被軟刪的公司只在報表或稽核時才會查。Partial index 讓常用查詢更快、索引更小。

---

### 3-2 `shop.stores`（SQL 第 226–249 行）

```sql
create table if not exists shop.stores (
  id              text primary key default public.generate_ulid(),
  company_id      text not null references shop.companies(id) on delete restrict,
  name            varchar(100)       not null,
  supervisor_id   text references shop.users(id) on delete set null,
  -- ...地址欄位省略...
  is_active       boolean            not null default true,
  metadata        jsonb              not null default '{}'::jsonb,
  -- ...時間戳省略...
  deleted_at      timestamptz
);
```

> ### 你的大腦在想 🧠
>
> **「`company_id` 用 `ON DELETE RESTRICT`？這代表什麼？」**
>
> 代表你**不能刪除一個還有門市的公司**。資料庫會直接報錯擋下來。
>
> 這是刻意的。想像一下：如果你不小心刪了公司，底下的 10 家門市、50 個店員、1000 筆訂單全部連鎖消失——這種事只要發生一次，你就會被叫去寫檢討報告。
>
> RESTRICT 就是資料庫幫你裝的安全鎖。要刪公司？先把底下的門市處理完再說。

#### `is_active` vs `deleted_at`：兩種不同的「不見了」

這張表同時有 `is_active`（第 238 行）和 `deleted_at`（第 242 行），這不是重複設計：

| 狀態 | `is_active` | `deleted_at` | 意義 |
|------|:-----------:|:------------:|------|
| 正常營業 | `true` | `NULL` | 一切正常 |
| 暫停營業 | `false` | `NULL` | 過年休息、裝修中——隨時可以重新開啟 |
| 永久關閉 | 任意 | 有值 | 這家店不會再回來了，但歷史資料保留 |

**`is_active` 是業務開關，`deleted_at` 是存在開關。** 兩者語意不同。

#### 複合 Partial Index（SQL 第 249 行）

```sql
create index idx_stores_active on shop.stores(id)
  where deleted_at is null and is_active = true;
```

只索引「活的且營業中」的門市。大部分商業查詢要的就是這個子集。

---

### 3-3 `shop.store_staff`（SQL 第 251–263 行）

```sql
create table if not exists shop.store_staff (
  id         text primary key default public.generate_ulid(),
  store_id   text   not null references shop.stores(id) on delete cascade,
  staff_id   text   not null references shop.users(id) on delete cascade,
  roles      text[] not null default array['staff']::text[],
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  deleted_at timestamptz
);
```

兩個設計決策需要說明：

#### 決策 1：為什麼 `roles` 用 `text[]` 而不是另開一張 join table？

```sql
-- 用 text[] 的寫法（我們的選擇）
roles text[] not null default array['staff']::text[]
-- 實際資料：'{manager,cashier}'

-- 另一種做法：開 join table
-- store_staff_roles (store_staff_id, role_name)
```

**選 `text[]` 的理由**：

- 角色數量很少（manager、cashier、staff⋯⋯通常不超過 5 種）
- 一個店員通常只有 1-3 個角色
- 不需要對角色做 JOIN 查詢或聚合分析
- 少一張表 = 少一次 JOIN = 查詢更簡單

> ### 沒有 Dumb Questions ❓
>
> **Q：「那如果未來角色變多了怎麼辦？」**
>
> A：如果角色超過 10 種，或者需要對角色做複雜的權限管理（角色繼承、角色群組），那就該抽成獨立的 `roles` 表 + join table。但對一個電商系統來說，店員角色通常就那幾種，text[] 夠用了。
>
> **Q：「text[] 可以加索引嗎？」**
>
> A：可以。用 GIN 索引：`CREATE INDEX ON shop.store_staff USING GIN(roles);`
> 這樣 `WHERE 'manager' = ANY(roles)` 就可以走索引。但這張表的資料量通常不大，暫時不需要。
>
> **Q：「store_id 和 staff_id 都用 ON DELETE CASCADE，這安全嗎？」**
>
> A：安全。store_staff 是**關聯表**，它的存在意義就是「某人在某店上班」。如果店沒了，或人沒了，這條關聯就沒有意義了。CASCADE 在這裡是正確的。

#### 決策 2：Unique Index with Soft Delete（SQL 第 261–262 行）

```sql
create unique index uq_store_staff
  on shop.store_staff(store_id, staff_id) where deleted_at is null;
```

這是一個 **partial unique index**：只有在 `deleted_at IS NULL` 的記錄中，(store_id, staff_id) 必須唯一。

為什麼不是普通的 UNIQUE 約束？因為如果一個店員離職（soft delete），未來又回來上班，你需要能新增一筆新記錄。普通 UNIQUE 會把「已刪除」的那筆也算進去，導致衝突。

---

### Soft Delete 設計模式總結

你已經在三張表裡看到了 `deleted_at`。什麼時候該用、什麼時候不該用？

| 用 Soft Delete | 不用（Hard Delete） | 不刪（Append-Only） |
|:---:|:---:|:---:|
| companies | 日誌（log） | inventory_movements |
| stores | 爬蟲結果（crawl data） | — |
| products | 臨時快取 | — |
| store_staff | — | — |

**規則**：

- **有歷史 FK 引用的**（訂單引用商品、出貨單引用門市）→ Soft Delete，因為刪了會斷鏈
- **純量大的記錄性資料**（日誌、爬蟲結果）→ Hard Delete 或 TTL 清理，省空間
- **異動追蹤類**（庫存移動）→ Append-Only，永遠不刪，每筆都是歷史

---

### ON DELETE 策略速查表

| 策略 | SQL | 行為 | 適用場景 | 本檔案範例 |
|------|-----|------|---------|-----------|
| **CASCADE** | `on delete cascade` | 刪父 → 子一起刪 | 關聯表、附屬資料 | store_staff（第 253–254 行） |
| **RESTRICT** | `on delete restrict` | 有子 → 擋住不讓刪 | 核心業務實體 | stores.company_id（第 228 行） |
| **SET NULL** | `on delete set null` | 刪父 → 子的 FK 設 NULL | 可選引用 | companies.supervisor_id（第 207 行） |

> ### 你的大腦在想 🧠
>
> **「那 `SET DEFAULT` 呢？」**
>
> 存在，但很少用。它會把 FK 設回 DEFAULT 值——但大部分 FK 的 DEFAULT 是 NULL，所以效果跟 SET NULL 一樣。只有在你有「預設指向」的場景才有意義（例如：刪了指定倉庫，訂單自動改指向「預設倉庫」）。

---

## Stage 4：Catalog（SQL 第 266–353 行）

商品目錄是電商系統的心臟。這一節我們要學的不只是「怎麼建表」，而是**為什麼這樣建**。

---

### 4-1 `shop.products`（SQL 第 278–317 行）

這是整個 schema 裡欄位最多的表，每個欄位都有設計理由。

```sql
create table if not exists shop.products (
  id               text primary key default public.generate_ulid(),
  author_id        text references shop.users(id) on delete set null,
  parent_id        text references shop.products(id) on delete set null,
  title            varchar(255)         not null,
  slug             varchar(255)         not null,
  description      text                 not null default '',
  excerpt          text                 not null default '',
  status           shop.product_status not null default 'draft',
  type             shop.product_type   not null default 'physical',
  sku              varchar(100),
  barcode          varchar(100),
  price            numeric(12,2)        not null default 0,
  compare_at_price numeric(12,2),
  cost_price       numeric(12,2),
  currency         varchar(3)           not null default 'TWD',
  weight_g         integer,
  is_taxable       boolean              not null default true,
  tax_rate         numeric(5,4),
  metadata         jsonb                not null default '{}'::jsonb,
  -- ...時間戳與審計欄位...
  constraint ck_products_price            check (price >= 0),
  constraint ck_products_compare_at_price check (compare_at_price is null or compare_at_price >= 0),
  constraint ck_products_cost_price       check (cost_price is null or cost_price >= 0)
);
```

#### 核心設計原則：First-Class Column vs JSONB

這是最重要的決定：什麼該是「正式欄位」，什麼該丟進 `metadata` JSONB？

```
問自己三個問題：
  ┌──────────────────────────────────────────┐
  │  這個值會出現在 WHERE 條件嗎？            │ → 正式欄位
  │  這個值會出現在 ORDER BY 嗎？             │ → 正式欄位
  │  這個值會被 JOIN 引用嗎？                 │ → 正式欄位
  │  以上都不是？                              │ → metadata jsonb
  └──────────────────────────────────────────┘
```

| 正式欄位（可查、可排、可索引） | JSONB（靈活但不常查） |
|:---:|:---:|
| price, sku, status, type | 顏色選項、尺寸表、材質說明 |
| slug, title, barcode | SEO 設定、自訂標籤 |
| weight_g, currency, tax_rate | 供應商備註、內部編號 |

> ### 反面教材 Anti-Pattern 🚫
>
> **千萬不要把 price 放進 JSONB。**
>
> ```sql
> -- ❌ 這樣做
> metadata->>'price'   -- 回傳的是 text，不是 numeric
>                      -- 無法直接比較大小、無法加索引、精度容易跑掉
>
> -- ✅ 正確做法
> price numeric(12,2)  -- 資料庫強制型別、可索引、精度保證
> ```
>
> 金額、庫存數量、狀態碼——任何需要精確計算或頻繁查詢的值，都必須是正式欄位。

#### Named CHECK Constraints（SQL 第 303–305 行）

```sql
constraint ck_products_price            check (price >= 0),
constraint ck_products_compare_at_price check (compare_at_price is null or compare_at_price >= 0),
constraint ck_products_cost_price       check (cost_price is null or cost_price >= 0)
```

三個重點：

1. **有名字**：`ck_products_price` 比系統自動生成的 `products_price_check` 好讀得多。出錯時，錯誤訊息會顯示這個名字，除錯效率大增。
2. **允許 NULL**：`compare_at_price` 和 `cost_price` 可以是 NULL（代表「沒設定」），但如果有值就必須 >= 0。
3. **資料庫層約束**：不管你的應用程式寫得多爛，價格永遠不會是負數。這就是 defense in depth。

#### Variant 模式：parent_id 自引用（SQL 第 281 行）

```sql
parent_id text references shop.products(id) on delete set null,
```

這是電商系統經典的「變體商品」設計：

```
T-shirt (type='variable', parent_id=NULL)    ← 父商品，不能直接買
  ├── T-shirt Red/S   (type='physical', parent_id='...')  ← 實際 SKU
  ├── T-shirt Red/M   (type='physical', parent_id='...')  ← 實際 SKU
  ├── T-shirt Blue/S  (type='physical', parent_id='...')  ← 實際 SKU
  └── T-shirt Blue/M  (type='physical', parent_id='...')  ← 實際 SKU
```

- **父商品**（`type='variable'`）：展示用，沒有 SKU，不直接銷售
- **子商品**：真正的庫存單位（SKU），有價格、有庫存、可以下單
- `parent_id` 指向同一張表的 `id` → **自引用 FK**（self-referential foreign key）

> ### 沒有 Dumb Questions ❓
>
> **Q：「為什麼不另開一張 `product_variants` 表？」**
>
> A：因為子商品和父商品的結構完全一樣——都有 price、sku、status、metadata。如果分成兩張表，你會重複定義一模一樣的欄位，而且查詢時永遠要 UNION 兩張表。自引用讓所有商品都在同一張表，查詢簡單。
>
> **Q：「那怎麼查所有變體？」**
>
> A：`SELECT * FROM shop.products WHERE parent_id = '父商品ID' AND deleted_at IS NULL;`
>
> **Q：「自引用會不會造成無限遞迴？」**
>
> A：在這個設計裡只有兩層（父 + 子），不是樹狀結構。如果你需要多層分類，那要用 `ltree` 或 recursive CTE——但那是 Stage 5 分類系統的事了。

#### 搜尋索引（SQL 第 315–317 行）

```sql
-- Trigram 模糊搜尋（第 315 行）
create index idx_products_title_trgm on shop.products
  using gin(title gin_trgm_ops);

-- 全文搜尋（第 316–317 行）
create index idx_products_search on shop.products
  using gin(to_tsvector('simple', coalesce(title,'') || ' ' || coalesce(description,'')));
```

兩種搜尋，解決不同問題：

| 索引 | 用途 | 範例 |
|------|------|------|
| `gin_trgm_ops`（pg_trgm） | 模糊比對、拼錯容忍 | "Tshrt" 可以找到 "T-shirt" |
| `tsvector`（全文搜尋） | 關鍵字搜尋、語意匹配 | "棉質 短袖" 找到含有這兩個詞的商品 |

> ### 你的大腦在想 🧠
>
> **「`gin_trgm_ops` 是怎麼讓 'Tshrt' 找到 'T-shirt' 的？」**
>
> pg_trgm 會把字串拆成三字元組（trigrams）：
>
> ```
> 'T-shirt' → {"  t", " t-", "t-s", "-sh", "shi", "hir", "irt", "rt "}
> 'Tshrt'   → {"  t", " ts", "tsh", "shr", "hrt", "rt "}
> ```
>
> 然後計算兩組 trigram 的重疊比例。重疊越多 = 越像。所以即使你少打了幾個字、打錯字、或忘了連字號，都還是能找到。
>
> 這就是為什麼電商搜尋框可以容忍使用者的各種打法。

#### Partial Unique Indexes（SQL 第 308–309 行）

```sql
create unique index uq_products_slug on shop.products(slug)
  where deleted_at is null;

create unique index uq_products_sku on shop.products(sku)
  where sku is not null and deleted_at is null;
```

- **slug**：活的商品中 slug 必須唯一（SEO 網址用），但被刪的可以重複
- **sku**：活的且有 SKU 的商品中 SKU 必須唯一。注意 `sku is not null` 這個條件——因為父商品（type='variable'）沒有 SKU，不加這個條件會讓多個 NULL SKU 被索引排斥（雖然 PostgreSQL 的 UNIQUE 其實允許多個 NULL，但語意上更清楚）

---

### 4-2 `shop.product_images`（SQL 第 320–333 行）

```sql
create table if not exists shop.product_images (
  id           text primary key default public.generate_ulid(),
  product_id   text         not null references shop.products(id) on delete cascade,
  storage_path text         not null,
  alt_text     varchar(255) not null default '',
  sort_order   smallint     not null default 0,
  is_primary   boolean      not null default false,
  created_at   timestamptz  not null default now(),
  updated_at   timestamptz  not null default now()
);
```

關鍵設計：

1. **`storage_path`，不是 BLOB**：圖片存在 Supabase Storage，這裡只存路徑引用。為什麼？因為圖片放資料庫會讓備份變大 100 倍、查詢變慢、CDN 無法快取。
2. **`sort_order`**：控制圖片排序。0 = 第一張，1 = 第二張⋯⋯
3. **`is_primary`**：標記主圖。

#### 每個商品只能有一張主圖（SQL 第 332–333 行）

```sql
create unique index uq_product_images_primary
  on shop.product_images(product_id) where is_primary = true;
```

又一個 **partial unique index**！只在 `is_primary = true` 的記錄中，`product_id` 必須唯一。

白話文：每個商品可以有很多圖片，但**只能有一張被標記為主圖**。如果你試圖把第二張圖也設成 `is_primary = true`，資料庫會報錯。

這比在應用層檢查可靠一百倍。

---

### 4-3 `shop.reviews`（SQL 第 336–353 行）

```sql
create table if not exists shop.reviews (
  id          text primary key default public.generate_ulid(),
  product_id  text        not null references shop.products(id) on delete cascade,
  customer_id text        not null references shop.users(id) on delete cascade,
  rating      smallint    not null,
  title       varchar(255) not null default '',
  body        text        not null default '',
  is_verified boolean     not null default false,
  is_visible  boolean     not null default true,
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now(),
  constraint ck_reviews_rating check (rating between 1 and 5)
);
```

#### rating CHECK（SQL 第 347 行）

```sql
constraint ck_reviews_rating check (rating between 1 and 5)
```

`BETWEEN 1 AND 5` 是 PostgreSQL 的語法糖，等同 `rating >= 1 AND rating <= 5`。不管前端怎麼傳，資料庫層保證評分只有 1-5 星。

#### 一人一評論（SQL 第 352–353 行）

```sql
create unique index uq_reviews_customer_product
  on shop.reviews(product_id, customer_id);
```

注意：這個 unique index **沒有** `WHERE deleted_at IS NULL` 條件，因為 reviews 表沒有 `deleted_at` 欄位。一個客戶對一個商品只能留一則評論，就是這麼簡單。

#### `is_verified` 和 `is_visible`

| 欄位 | 意義 | 誰控制 |
|------|------|--------|
| `is_verified` | 這個人真的買過這個商品 | 系統自動設定（比對訂單記錄） |
| `is_visible` | 評論是否顯示在前台 | 管理員手動控制（可以隱藏不當內容） |

---

### 預告：為什麼訂單要快照商品資料？

在 Stage 8（order_items），你會看到訂單明細裡會複製一份商品名稱和價格，而不是只存 `product_id`。

為什麼？因為商品可能會：
- 改名（"夏季 T-shirt" → "經典 T-shirt"）
- 改價（原價 599 → 特價 399）
- 被軟刪（下架了）

如果訂單只存 FK，三個月後你查歷史訂單，看到的會是**現在的**商品資料，不是**當時的**。這在財務上是災難。

所以 Stage 8 會用 `product_name`、`unit_price` 等欄位做快照（snapshot）。先記住這個概念。

---

## 重點子彈 🎯

### Stage 3：Organization

- [ ] Company → Store → Staff 是「總部 → 分店 → 人員」的標準三層架構
- [ ] `ON DELETE RESTRICT`（第 228 行）：擋住危險的連鎖刪除，保護核心實體
- [ ] `ON DELETE SET NULL`（第 207 行）：保留記錄、清除可選引用
- [ ] `ON DELETE CASCADE`（第 253–254 行）：適用於關聯表，父沒了子也沒意義
- [ ] `is_active` 是業務開關，`deleted_at` 是存在開關——語意不同，不是重複
- [ ] `text[]` 陣列型別適合小型角色集合，比 join table 簡單
- [ ] Partial unique index（第 261 行）讓 soft delete 和 uniqueness 共存

### Stage 4：Catalog

- [ ] **First-Class Column 原則**：WHERE / ORDER BY / JOIN 會用到的 → 正式欄位；其餘 → JSONB
- [ ] **永遠不要把金額放進 JSONB**——型別不安全、無法索引、精度會跑掉
- [ ] Named CHECK constraints（第 303–305 行）讓錯誤訊息可讀，除錯更快
- [ ] parent_id 自引用實現「父商品 + 變體 SKU」模式，比另開表更簡潔
- [ ] `gin_trgm_ops`（第 315 行）：模糊搜尋，容忍拼錯
- [ ] `tsvector`（第 316–317 行）：全文搜尋，語意匹配
- [ ] Partial unique index 讓 slug 和 SKU 在「活的」記錄中唯一
- [ ] 圖片存 Storage 路徑（不是 BLOB），partial unique index 保證每商品只有一張主圖
- [ ] 評論用 CHECK 約束限制 1-5 星，unique index 保證一人一評

---

## 動手做 🔨

### 練習 1：讀懂 ON DELETE 行為

在 SQL Editor 裡跑以下情境，觀察結果：

```sql
-- 1. 先建一家公司和一家門市
insert into shop.companies (name, type)
  values ('測試品牌', 'retailer')
  returning id;
-- 記下回傳的 company_id

insert into shop.stores (company_id, name)
  values ('上面的ID', '台北旗艦店');

-- 2. 試著刪除公司
delete from shop.companies where name = '測試品牌';
-- 預期：報錯！因為底下還有門市（ON DELETE RESTRICT）

-- 3. 先刪門市，再刪公司
delete from shop.stores where name = '台北旗艦店';
delete from shop.companies where name = '測試品牌';
-- 預期：成功
```

**思考題**：如果把 `shop.stores.company_id` 改成 `ON DELETE CASCADE`，步驟 2 會發生什麼事？這在商業上可以接受嗎？

---

### 練習 2：體驗 Partial Unique Index

```sql
-- 1. 新增一個店員到某門市
insert into shop.store_staff (store_id, staff_id, roles)
  values ('某個store_id', '某個user_id', '{manager,cashier}');

-- 2. 再新增一次同樣的組合
insert into shop.store_staff (store_id, staff_id, roles)
  values ('某個store_id', '某個user_id', '{staff}');
-- 預期：報錯！unique 約束阻止重複

-- 3. 把第一筆軟刪
update shop.store_staff set deleted_at = now()
  where store_id = '某個store_id' and staff_id = '某個user_id';

-- 4. 再新增一次
insert into shop.store_staff (store_id, staff_id, roles)
  values ('某個store_id', '某個user_id', '{staff}');
-- 預期：成功！因為 partial unique index 只管 deleted_at IS NULL 的記錄
```

---

### 練習 3：pg_trgm 模糊搜尋

```sql
-- 確認 extension 已安裝
-- （Stage 1 已經 CREATE EXTENSION pg_trgm）

-- 插入測試商品
insert into shop.products (title, slug, price)
  values ('經典 T-shirt 純棉', 'classic-tshirt-cotton', 599);

-- 模糊搜尋：故意打錯字
select title, similarity(title, 'Tshrt') as score
from shop.products
where title % 'Tshrt'
order by score desc;

-- 全文搜尋
select title
from shop.products
where to_tsvector('simple', coalesce(title,'') || ' ' || coalesce(description,''))
   @@ to_tsquery('simple', '純棉');
```

**觀察**：`similarity()` 回傳 0-1 的分數，`%` 運算子是「相似度超過閾值」的簡寫。你可以用 `SET pg_trgm.similarity_threshold = 0.3;` 調整敏感度。

---

### 練習 4：CHECK Constraint 的防護力

```sql
-- 試著插入負數價格
insert into shop.products (title, slug, price)
  values ('測試商品', 'test-product', -100);
-- 預期：報錯！ck_products_price 阻止了

-- 試著插入 0 星評論
insert into shop.reviews (product_id, customer_id, rating)
  values ('某product_id', '某user_id', 0);
-- 預期：報錯！ck_reviews_rating 要求 BETWEEN 1 AND 5

-- 試著插入 6 星評論
insert into shop.reviews (product_id, customer_id, rating)
  values ('某product_id', '某user_id', 6);
-- 預期：同樣報錯
```

**結論**：不管前端驗證寫得多完美，永遠在資料庫層再擋一次。因為 API 可以被繞過，但 CHECK constraint 繞不過。

---

下一章：[`03_taxonomy-inventory.md`](03_taxonomy-inventory.md) — Stage 5-6：分類系統 + 庫存模式

---

[← 01 地基 + 身分](01_foundation-identity.md) | [03 分類 + 庫存 →](03_taxonomy-inventory.md)

# Head First SQL Editor 精通 — 工程師的主戰場

> **"Table Editor 是觀光客用的。SQL Editor 才是居民用的。"**
>
> 你的大腦在想：「我會用 Table Editor 了，為什麼還要學 SQL Editor？」
>
> 因為 SQL 可以 version control。GUI 操作不行。你在 Table Editor 做的每一個改動，都應該能用 SQL 重現。
> 這就是為什麼正式團隊都用 migration 檔（純 SQL），而不是截圖加備註。

![SQL Editor](https://supabase.com/images/features/sql-editor.png)

![SQL Editor Tabs](https://supabase.com/_next/image?q=75&url=%2Fimages%2Fblog%2Flw14-tabs-dashboard-updates%2Fsql-editor-tabs.jpg&w=3840)

---

## 前置要求

- Docker 已跑起來（`supabase start` 成功）
- 瀏覽器打開 `http://localhost:54323`
- 已讀完 `01_supabase-studio.md` + `02` Schema 策略

> 還沒跑起來？先去看 `../labs/05_lab-docker-supabase.md`。

---

## Part 1: 基本操作流程

打開 Studio → 左側選單點 **SQL Editor**。你會看到一個空白的編輯區。

### 五步驟操作循環

```
1. 打開 SQL Editor（左側選單 💻 圖示）
2. 點左上角 + 新增 query tab
3. 在編輯區撰寫 SQL
4. 按 ▶ Run（或 Cmd+Enter / Ctrl+Enter）
5. 下方看結果（表格或錯誤訊息）
```

就這麼簡單。但魔鬼在細節。

### 你的大腦在想：「這跟 pgAdmin 有什麼不一樣？」

差別在：Supabase SQL Editor **直接連到你的專案 PostgreSQL**，不用另外設定連線。而且它內建了一堆範本（Templates），新手不用從零開始。

> **Head First 小技巧**：每個 tab 可以命名。養成習慣，給 tab 取有意義的名字：
> - `debug_orders` — 除錯用
> - `test_rls` — 測試 RLS Policy
> - `create_tables` — DDL 操作
> - `seed_data` — 測試資料
>
> 三個月後你會感謝自己。

---

## Part 2: CRUD 完整實戰

CRUD = Create, Read, Update, Delete。這四個操作是所有應用程式的基礎。

我們用一個「實驗管理系統」的情境來練習。

---

### CREATE — 建表

```sql
CREATE TABLE public.experiments (
  id TEXT PRIMARY KEY DEFAULT generate_ulid(),
  name TEXT NOT NULL,
  config JSONB NOT NULL DEFAULT '{}'::jsonb,
  status TEXT NOT NULL DEFAULT 'draft',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 加上欄位註解（好習慣）
COMMENT ON TABLE public.experiments IS '實驗管理表';
COMMENT ON COLUMN public.experiments.config IS '實驗設定，JSONB 格式';
COMMENT ON COLUMN public.experiments.status IS 'draft | running | completed | archived';
```

> **腦筋急轉彎：為什麼 `config` 用 JSONB 不用 TEXT？**
>
> → JSONB 可以**索引**、**查詢內部欄位**、**局部更新**。TEXT 只能整段取出來，改完整段塞回去。
>
> 想像一下：你有一個設定檔 `{"variant_count": 3, "traffic_split": [0.33, 0.33, 0.34]}`。
> 用 JSONB，你可以直接查 `config->>'variant_count' = '3'`。
> 用 TEXT，你只能把整段字串撈出來，在應用程式端 parse。

#### 動手做

```
📝 Exercise 2.1: 建立 experiments 表
1. 打開 SQL Editor，新增 tab 命名為 "create_tables"
2. 貼上上面的 CREATE TABLE SQL
3. 按 Cmd+Enter 執行
4. 切到 Table Editor → 確認表已出現
5. 點進去看欄位定義是否正確
```

---

### INSERT — 新增資料

```sql
-- 單筆新增
INSERT INTO experiments (name, config)
VALUES (
  'A/B 測試 v1',
  '{"variant_count": 3, "traffic_split": [0.33, 0.33, 0.34]}'::jsonb
);

-- 多筆新增（seed data）
INSERT INTO experiments (name, config, status) VALUES
  ('推薦演算法 A', '{"model": "collaborative", "k": 10}'::jsonb, 'running'),
  ('推薦演算法 B', '{"model": "content-based", "features": 50}'::jsonb, 'running'),
  ('舊版 UI 測試', '{"layout": "classic"}'::jsonb, 'completed'),
  ('新版定價方案', '{"tiers": [9.99, 19.99, 49.99]}'::jsonb, 'draft');
```

> **你的大腦在想：「`generate_ulid()` 是哪來的？」**
>
> 好問題。這是我們自己建的 helper function（Part 5 會教）。如果你的資料庫裡還沒有這個 function，先把 `id` 改成 `UUID` 型別配 `gen_random_uuid()` 也行。重點是：**主鍵自動產生，不要讓前端傳。**

---

### SELECT — 查詢（含 JSONB 操作）

查詢是你最常用的操作。先從基本的來：

```sql
-- 基本查詢：看所有實驗
SELECT * FROM experiments;

-- 條件查詢：只看 running 的
SELECT id, name, status FROM experiments
WHERE status = 'running';

-- 排序 + 限制
SELECT name, created_at FROM experiments
ORDER BY created_at DESC
LIMIT 5;
```

#### JSONB 查詢 — 進入深水區

```sql
-- 取出 JSONB 內部值（->> 回傳 TEXT）
SELECT name, config->>'variant_count' AS variants
FROM experiments
WHERE config->>'variant_count' = '3';

-- 取出 JSONB 內部值（-> 回傳 JSONB）
SELECT name, config->'traffic_split' AS splits
FROM experiments
WHERE config ? 'traffic_split';

-- JSONB 包含查詢（@> 運算子）
SELECT * FROM experiments
WHERE config @> '{"model": "collaborative"}'::jsonb;

-- 查詢 JSONB 陣列
SELECT name, config->'tiers' AS pricing
FROM experiments
WHERE config @> '{"tiers": [19.99]}'::jsonb;
```

> **腦筋急轉彎：`->` 和 `->>` 到底差在哪？**
>
> | 運算子 | 回傳型別 | 用途 |
> |--------|----------|------|
> | `->` | JSONB | 要繼續操作 JSONB（例如再 `->` 一層） |
> | `->>` | TEXT | 要拿最終值來比較或顯示 |
>
> 記憶法：多一個 `>` = 多擠一步 = 變成純文字。

#### 動手做

```
📝 Exercise 2.2: JSONB 查詢
1. 新增 tab 命名為 "jsonb_queries"
2. 用 @> 查出所有 model 為 "collaborative" 的實驗
3. 用 ->> 列出所有實驗的 status
4. 嘗試查詢 config 裡有 "tiers" key 的實驗（提示：用 ? 運算子）
```

---

### UPDATE — 更新

```sql
-- 基本更新
UPDATE experiments
SET status = 'running', updated_at = NOW()
WHERE name = 'A/B 測試 v1';

-- JSONB 局部更新（用 || 合併）
UPDATE experiments
SET config = config || '{"priority": "high"}'::jsonb
WHERE status = 'running';

-- JSONB 刪除某個 key
UPDATE experiments
SET config = config - 'priority'
WHERE name = '推薦演算法 B';
```

> **注意**：`updated_at = NOW()` 是手動更新。Part 5 會教你用 Trigger 自動更新。

---

### DELETE — 刪除

```sql
-- 條件刪除
DELETE FROM experiments WHERE status = 'draft';

-- 刪除全部（危險！通常不會這樣做）
-- DELETE FROM experiments;

-- 更安全的做法：軟刪除（soft delete）
ALTER TABLE experiments ADD COLUMN deleted_at TIMESTAMPTZ;

UPDATE experiments
SET deleted_at = NOW()
WHERE status = 'completed';
```

> **Head First 原則**：正式環境幾乎不用 `DELETE`。用 soft delete（加 `deleted_at` 欄位）。
> 因為刪了就沒了，但標記刪除可以救回來。

---

### 電商實戰範例 — 用 e-Commerce Schema 練習 CRUD

> 以下範例來自 `e-Commerce/01_shop_supabase_native_schema.sql`。
> 如果你已經跑過該 schema，可以直接在 SQL Editor 操作真實電商資料。

#### 建表：商品目錄（Stage 4）

```sql
-- 這是電商 Schema 的 products 表（簡化版，完整版見 e-Commerce schema）
CREATE TABLE IF NOT EXISTS public.products (
  id               TEXT PRIMARY KEY DEFAULT generate_ulid(),
  title            VARCHAR(255)         NOT NULL,
  slug             VARCHAR(255)         NOT NULL,
  status           public.product_status NOT NULL DEFAULT 'draft',
  price            NUMERIC(12,2)        NOT NULL DEFAULT 0,
  compare_at_price NUMERIC(12,2),
  currency         VARCHAR(3)           NOT NULL DEFAULT 'TWD',
  metadata         JSONB                NOT NULL DEFAULT '{}'::jsonb,
  created_at       TIMESTAMPTZ          NOT NULL DEFAULT NOW(),
  updated_at       TIMESTAMPTZ          NOT NULL DEFAULT NOW(),
  deleted_at       TIMESTAMPTZ,
  CONSTRAINT ck_products_price CHECK (price >= 0)
);
```

> 注意 `NUMERIC(12,2)` — 金額**永遠**不要用 FLOAT，否則 `0.1 + 0.2 = 0.30000000000000004`。

#### 新增：商品資料

```sql
INSERT INTO products (title, slug, price, status, metadata) VALUES
  ('MacBook Pro 14"', 'macbook-pro-14', 59900, 'publish',
   '{"color": "太空灰", "ram": "16GB", "storage": "512GB"}'::jsonb),
  ('AirPods Pro', 'airpods-pro', 7490, 'publish',
   '{"color": "白色", "anc": true}'::jsonb),
  ('Magic Keyboard', 'magic-keyboard', 3490, 'draft',
   '{"layout": "繁體中文", "backlit": true}'::jsonb);
```

#### 查詢：JSONB 操作

```sql
-- 找出所有 16GB RAM 的商品
SELECT title, price, metadata->>'color' AS 顏色
FROM products
WHERE metadata @> '{"ram": "16GB"}'::jsonb;

-- 找出所有已上架且價格 > 5000 的商品
SELECT title, price, status
FROM products
WHERE status = 'publish' AND price > 5000
ORDER BY price DESC;

-- 用模糊搜尋找商品（需要 pg_trgm extension）
SELECT title, price FROM products
WHERE title ILIKE '%macbook%';
```

#### 更新：商品上架

```sql
UPDATE products
SET status = 'publish', updated_at = NOW()
WHERE slug = 'magic-keyboard';
```

#### 軟刪除：下架商品

```sql
-- 電商不用 DELETE，用 soft delete
UPDATE products
SET deleted_at = NOW()
WHERE slug = 'magic-keyboard';

-- 查詢時排除已刪除
SELECT * FROM products WHERE deleted_at IS NULL;
```

---

## Part 3: Index — 效能的關鍵

### 為什麼要 Index？

沒有 Index 的查詢 = **每次都全表掃描**（Seq Scan）。

想像你在圖書館找一本書。沒有分類系統，你只能從第一個書架開始，一本一本看書名。有了分類索引，你直接翻目錄，跳到正確的書架。

Index 就是資料庫的目錄。

---

### 基本 B-Tree Index

最常見的 Index 類型。適合等值查詢（`=`）和範圍查詢（`>`, `<`, `BETWEEN`）。

```sql
CREATE INDEX idx_experiments_status ON experiments(status);
```

建好之後，`WHERE status = 'running'` 就不用全表掃描了。

---

### JSONB GIN Index

JSONB 欄位要用 GIN（Generalized Inverted Index），不是 B-Tree。

```sql
CREATE INDEX idx_experiments_config ON experiments USING GIN(config);
```

建好之後，`@>` 包含查詢和 `?` key 存在查詢都會走這個 Index。

---

### Composite Index（複合索引）

如果你常常 `WHERE status = 'x' ORDER BY created_at DESC`，就建一個複合 Index：

```sql
CREATE INDEX idx_experiments_status_created
ON experiments(status, created_at DESC);
```

> **腦筋急轉彎：「加了 Index 一定比較快嗎？」**
>
> **不一定！**
>
> 1. **小表**（< 1000 行）加 Index 反而更慢，因為 PostgreSQL 要多維護一棵 B-Tree
> 2. **寫入密集**的表，每次 INSERT/UPDATE 都要同步更新 Index
> 3. **低選擇性**的欄位（例如 boolean 只有 true/false）加 Index 效果不大
>
> 經驗法則：
> - 表 > 10000 行 + 查詢頻繁 → 加 Index
> - 表 < 1000 行 → 不用加
> - 不確定 → 用 EXPLAIN ANALYZE 測（下一節教你）

#### 動手做

```
📝 Exercise 3.1: 建立 Index
1. 新增 tab 命名為 "indexes"
2. 建立 status 的 B-Tree Index
3. 建立 config 的 GIN Index
4. 建立 (status, created_at) 的 Composite Index
5. 執行後到 Table Editor → 選 experiments → 看 Indexes 分頁，確認三個都在
```

### 電商 Index 實戰

電商 Schema 的 products 表用了**6 種不同的 Index**，是學習 Index 策略的最佳教材：

```sql
-- 1. 基本 B-Tree：按狀態查詢
CREATE INDEX idx_products_status ON products(status) WHERE deleted_at IS NULL;

-- 2. 唯一索引 + 部分條件：slug 不能重複（但已刪除的除外）
CREATE UNIQUE INDEX uq_products_slug ON products(slug) WHERE deleted_at IS NULL;

-- 3. 唯一索引 + NULL 忽略：SKU 可以為 NULL，但非 NULL 必須唯一
CREATE UNIQUE INDEX uq_products_sku ON products(sku) WHERE sku IS NOT NULL AND deleted_at IS NULL;

-- 4. JSONB GIN Index：搜尋 metadata 內部
CREATE INDEX idx_products_metadata ON products USING GIN(metadata);

-- 5. pg_trgm GIN Index：模糊搜尋商品名稱
CREATE INDEX idx_products_title_trgm ON products USING GIN(title gin_trgm_ops);

-- 6. 全文搜尋 Index：tsvector
CREATE INDEX idx_products_search ON products
  USING GIN(to_tsvector('simple', coalesce(title,'') || ' ' || coalesce(description,'')));
```

> **腦筋急轉彎：為什麼 `idx_products_status` 後面有 `WHERE deleted_at IS NULL`？**
>
> 這叫**部分索引（Partial Index）**。只索引「未刪除」的商品。
> 好處：Index 更小、更快。因為你 99% 的查詢都是查未刪除的商品。

---

## Part 4: EXPLAIN ANALYZE — 你的查詢醫生

EXPLAIN ANALYZE 是 PostgreSQL 最強大的診斷工具。它告訴你：**資料庫到底怎麼執行你的查詢。**

### 基本用法

在任何 `SELECT` 前面加上 `EXPLAIN ANALYZE`：

```sql
EXPLAIN ANALYZE
SELECT * FROM experiments WHERE status = 'running';
```

### 怎麼讀輸出？

```
-- 沒有 Index 的情況（或小表）
Seq Scan on experiments  (cost=0.00..35.50 rows=1000 width=128)
  Filter: (status = 'running'::text)
  Rows Removed by Filter: 997
  actual time=0.025..0.831 ms
  Planning Time: 0.082 ms
  Execution Time: 0.915 ms
```

```
-- 有 Index 的情況
Index Scan using idx_experiments_status on experiments  (cost=0.15..8.17 rows=3 width=128)
  Index Cond: (status = 'running'::text)
  actual time=0.015..0.023 ms
  Planning Time: 0.095 ms
  Execution Time: 0.048 ms
```

### 關鍵指標速查表

| 指標 | 意思 | 好壞 |
|------|------|------|
| **Seq Scan** | 全表掃描，逐行檢查 | 通常不好（大表） |
| **Index Scan** | 走索引找到行 | 好 |
| **Bitmap Index Scan** | 批量走索引 | 還行（多筆匹配時） |
| **cost** | 預估成本（任意單位） | 越低越好 |
| **actual time** | 真實執行時間（ms） | 越低越好 |
| **rows** | 實際掃描/回傳行數 | 越接近預估越好 |
| **Rows Removed by Filter** | 掃描了但不符合條件的行數 | 越大代表越浪費 |
| **Planning Time** | 查詢計劃時間 | 通常很小，可忽略 |
| **Execution Time** | 總執行時間 | 核心指標 |

### 你的大腦在想：「Seq Scan 一定是壞事嗎？」

不一定。如果表只有 50 行，Seq Scan 可能比 Index Scan 更快（因為不用先查 Index 再查表）。PostgreSQL 的查詢優化器很聰明，它會自己判斷。

**真正的紅燈**是：大表（> 10000 行）+ Seq Scan + Rows Removed by Filter 很大。

### EXPLAIN 進階：JSONB 查詢

```sql
-- 沒有 GIN Index
EXPLAIN ANALYZE
SELECT * FROM experiments WHERE config @> '{"model": "collaborative"}'::jsonb;
-- 預期：Seq Scan（全表掃描）

-- 加了 GIN Index 之後
EXPLAIN ANALYZE
SELECT * FROM experiments WHERE config @> '{"model": "collaborative"}'::jsonb;
-- 預期：Bitmap Index Scan using idx_experiments_config
```

#### 動手做

```
📝 Exercise 4.1: EXPLAIN ANALYZE 實戰
1. 先刪掉所有 Index：
   DROP INDEX IF EXISTS idx_experiments_status;
   DROP INDEX IF EXISTS idx_experiments_config;
   DROP INDEX IF EXISTS idx_experiments_status_created;
2. 執行 EXPLAIN ANALYZE SELECT * FROM experiments WHERE status = 'running';
   → 記下 Execution Time
3. 重新建立 idx_experiments_status
4. 再執行一次同樣的 EXPLAIN ANALYZE
   → 比較 Execution Time
5. 對 config @> 查詢做同樣的實驗（先不加 GIN → 加 GIN → 比較）
```

> **Head First 原則**：不要憑感覺加 Index。用 EXPLAIN ANALYZE 測量，用數據說話。

### 電商 EXPLAIN 實戰

```sql
-- 測試電商查詢效能：找出某店鋪的 pending 訂單
EXPLAIN ANALYZE
SELECT o.id, o.total, o.status, p.full_name AS customer
FROM orders o
JOIN profiles p ON p.id = o.customer_id
WHERE o.store_id = '01HXY...'
  AND o.status = 'pending'
  AND o.deleted_at IS NULL
ORDER BY o.created_at DESC
LIMIT 20;

-- 測試商品模糊搜尋
EXPLAIN ANALYZE
SELECT id, title, price FROM products
WHERE title ILIKE '%air%' AND deleted_at IS NULL;
```

> 如果看到 `Seq Scan on orders`，代表需要加 composite index：
> ```sql
> CREATE INDEX idx_orders_store_status ON orders(store_id, status) WHERE deleted_at IS NULL;
> ```

---

## Part 5: Function & Trigger

### 為什麼要把邏輯放在資料庫？

你的大腦可能在抗議：「邏輯應該放在應用程式端啊！」

沒錯，**大部分邏輯**放應用程式端。但有些邏輯**不管從哪裡寫入都要執行**：

- `updated_at` 自動更新
- 主鍵自動產生（ULID / UUID）
- 資料驗證（例如 status 只能是特定值）

這些邏輯放在 Trigger 裡，Python 可以繞過你的應用邏輯，但**繞不過 Trigger**。

---

### Function：自動更新 `updated_at`

```sql
CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

這個 Function 做一件事：把 `updated_at` 設成當前時間。

- `NEW` = 即將被寫入的那一行（更新後的版本）
- `RETURN NEW` = 讓更新繼續執行

---

### Trigger：自動觸發

```sql
CREATE TRIGGER trg_experiments_updated
BEFORE UPDATE ON public.experiments
FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
```

拆解：

| 部分 | 意思 |
|------|------|
| `BEFORE UPDATE` | 在 UPDATE 發生**之前**觸發 |
| `ON public.experiments` | 監聽 experiments 表 |
| `FOR EACH ROW` | 每一行都觸發（不是整個 statement 觸發一次） |
| `EXECUTE FUNCTION` | 執行我們剛寫的 function |

現在試試：

```sql
UPDATE experiments SET name = '改個名字' WHERE status = 'running';

-- 檢查 updated_at 是否自動更新
SELECT name, updated_at FROM experiments WHERE status = 'running';
```

> **腦筋急轉彎：BEFORE 和 AFTER 的差別？**
>
> - `BEFORE`：可以**修改**即將寫入的值（像我們改 `updated_at`）
> - `AFTER`：值已經寫入，只能做「副作用」（例如寫 log、發通知）
>
> 要改資料 → 用 `BEFORE`。要記錄/通知 → 用 `AFTER`。

---

### `generate_ulid()` — 跨表通用的主鍵產生器

```sql
CREATE OR REPLACE FUNCTION public.generate_ulid()
RETURNS TEXT AS $$
DECLARE
  timestamp  BIGINT;
  unix_ts    BIGINT;
  ulid       TEXT;
  encoding   TEXT := '0123456789ABCDEFGHJKMNPQRSTVWXYZ';
  i          INTEGER;
  rand_bytes BYTEA;
BEGIN
  unix_ts := EXTRACT(EPOCH FROM clock_timestamp()) * 1000;
  ulid := '';
  -- Encode timestamp (10 chars)
  timestamp := unix_ts;
  FOR i IN REVERSE 9..0 LOOP
    ulid := ulid || substr(encoding, (timestamp % 32)::integer + 1, 1);
    timestamp := timestamp / 32;
  END LOOP;
  -- Encode randomness (16 chars)
  rand_bytes := gen_random_bytes(10);
  FOR i IN 0..9 LOOP
    ulid := ulid || substr(encoding, (get_byte(rand_bytes, i) % 32) + 1, 1);
  END LOOP;
  RETURN ulid;
END;
$$ LANGUAGE plpgsql VOLATILE;
```

> **為什麼用 ULID 不用 UUID？**
>
> | 特性 | UUID v4 | ULID |
> |------|---------|------|
> | 排序 | 隨機，無法排序 | 時間戳開頭，天然有序 |
> | 索引效率 | 差（隨機插入 B-Tree 碎片化） | 好（接近順序插入） |
> | 可讀性 | `550e8400-e29b-41d4...` | `01HXY8Z3K4...` |
>
> 在高寫入場景下，ULID 的 Index 效能明顯優於 UUID。

#### 動手做

```
📝 Exercise 5.1: Function & Trigger
1. 建立 set_updated_at() function
2. 建立 trg_experiments_updated trigger
3. UPDATE 任一筆 experiments，只改 name
4. SELECT 那筆資料，確認 updated_at 已自動更新
5. （加分）建立 generate_ulid() function，然後 SELECT generate_ulid() 看看產生的值
```

---

## Part 6: 內建範本速覽

SQL Editor 左側有個 **Templates** 區塊（或點 + 旁邊的下拉選單）。Supabase 內建了很多實用範本：

| 範本名稱 | 用途 | 適合時機 |
|----------|------|----------|
| **Quick Start** | 快速建表 + 插入範例資料 | 剛開始學的時候 |
| **User Management Starter** | 建立使用者管理架構 | 需要 Auth 整合 |
| **RBAC（角色權限）** | Role-Based Access Control 完整設定 | 需要細緻權限控制 |
| **Full-Text Search** | 全文檢索設定 | 需要搜尋功能 |
| **RLS Policies** | Row Level Security 範例 | 設定資料隔離（下一章重點） |
| **Functions** | 常用 function 範例 | 需要 DB 端邏輯 |

> **Head First 小技巧**：不要直接用範本的 SQL 跑在正式環境。先在一個新 tab 裡讀懂它在做什麼，再根據你的需求修改。範本是**學習工具**，不是**複製貼上工具**。

---

## Part 7: 進階技巧

### Tab 管理最佳實踐

```
✅ 命名規則：[用途]_[目標]
   create_tables
   seed_data
   debug_orders
   test_rls_policies
   perf_explain

✅ 常用查詢 pin 起來（右鍵 → Pin）
✅ 不用的 tab 關掉（保持工作區乾淨）
✅ 重要的查詢存成 .sql 檔案，放進 Git
```

---

### 快捷鍵

| 快捷鍵 | 功能 | 備註 |
|--------|------|------|
| `Cmd+Enter` | 執行整段查詢 | 最常用 |
| `Cmd+Shift+Enter` | 執行選取部分 | 選取幾行就跑幾行 |
| `Cmd+/` | 註解/取消註解 | 快速切換 |
| `Cmd+D` | 選取下一個相同字串 | 批量編輯 |
| `Cmd+Shift+K` | 刪除整行 | |

> Windows / Linux 用戶：把 `Cmd` 換成 `Ctrl`。

---

### 常用診斷查詢

這些查詢你會反覆用到。建議存成獨立 tab 並 pin 起來。

```sql
-- 查看所有表的大小（含 Index）
SELECT
  relname AS table_name,
  pg_size_pretty(pg_total_relation_size(relid)) AS total_size,
  pg_size_pretty(pg_relation_size(relid)) AS data_size,
  pg_size_pretty(pg_total_relation_size(relid) - pg_relation_size(relid)) AS index_size
FROM pg_catalog.pg_statio_user_tables
ORDER BY pg_total_relation_size(relid) DESC;
```

```sql
-- 查看未使用的 Index（浪費空間 + 拖慢寫入）
SELECT
  schemaname,
  indexrelname AS index_name,
  relname AS table_name,
  idx_scan AS times_used,
  pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes
WHERE idx_scan = 0
ORDER BY pg_relation_size(indexrelid) DESC;
```

```sql
-- 查看目前 connection 數量
SELECT count(*) FROM pg_stat_activity;
```

```sql
-- 查看正在執行的慢查詢（> 1 秒）
SELECT pid, now() - pg_stat_activity.query_start AS duration, query
FROM pg_stat_activity
WHERE state = 'active'
  AND now() - pg_stat_activity.query_start > interval '1 second';
```

---

## 自我檢查清單

完成這一章後，你應該能打勾：

```
□ 我能在 SQL Editor 完成 CRUD 全套操作（CREATE TABLE, INSERT, SELECT, UPDATE, DELETE）
□ 我知道 JSONB 的 -> 和 ->> 運算子差在哪裡
□ 我能用 @> 做 JSONB 包含查詢
□ 我能建立 B-Tree Index、GIN Index 和 Composite Index
□ 我知道什麼時候該加 Index，什麼時候不該
□ 我能用 EXPLAIN ANALYZE 判斷查詢是否走 Index
□ 我能讀懂 EXPLAIN 的 Seq Scan vs Index Scan vs Bitmap Index Scan
□ 我能建立 Function 和 Trigger（set_updated_at 範例）
□ 我知道 JSONB 欄位該用 GIN Index
□ 我知道 BEFORE vs AFTER Trigger 的差別
□ 我養成了 Tab 命名 + Pin 的好習慣
```

---

## 下一步

你已經掌握了 SQL Editor 的核心技能。接下來進入最重要的安全議題：

→ `04_auth-and-rls.md` — Auth & RLS 實戰，學會保護你的資料。

> **記住**：沒有 RLS 的 Supabase 表 = 裸奔。下一章教你怎麼穿上盔甲。

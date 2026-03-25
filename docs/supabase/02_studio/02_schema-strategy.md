# Head First Schema 策略 — 不要把所有東西塞進 public

> **"一個 Supabase project = 一個 PostgreSQL DB。你不能再建另一個 DB，但你可以用 Schema 分區。"**

---

> ### 你的大腦在想 🧠
>
> 「我有 crawler、電商、RAG 三個專案，要建三個 Supabase project 嗎？」
>
> 答案：不用。用 Schema 分區就好。
>
> 一個 project 裡可以有很多 schema，每個 schema 就像一個「資料夾」，
> 把相關的表、function、view 放在一起。乾淨、清楚、不會互相踩到。

---

## 關鍵觀念：一個 Project = 一個 PostgreSQL DB

這是很多人搞混的地方，讓我們先釐清：

```
┌─────────────────────────────────────────────┐
│  Supabase Project                           │
│  ┌─────────────────────────────────────┐    │
│  │  PostgreSQL Database（只有一個！）    │    │
│  │                                     │    │
│  │  ┌──────────┐  ┌──────────┐        │    │
│  │  │  public   │  │   auth   │        │    │
│  │  │  schema   │  │  schema  │        │    │
│  │  └──────────┘  └──────────┘        │    │
│  │  ┌──────────┐  ┌──────────┐        │    │
│  │  │ storage  │  │ extensions│        │    │
│  │  │  schema  │  │  schema   │        │    │
│  │  └──────────┘  └──────────┘        │    │
│  │  ┌──────────┐  ┌──────────┐        │    │
│  │  │ crawler  │  │   rag    │  ← 你建的│    │
│  │  │  schema  │  │  schema  │        │    │
│  │  └──────────┘  └──────────┘        │    │
│  └─────────────────────────────────────┘    │
└─────────────────────────────────────────────┘
```

**三件事你必須知道**：

1. **Supabase 不支援在同一個 project 裡建多個 database**
   - 一個 project = 一個 DB，就這樣

2. **PostgreSQL 本身也不建議 multi-database**
   - Cross-database query 需要用 `dblink` 或 `postgres_fdw`，又慢又麻煩
   - 你沒辦法在兩個 DB 之間做 JOIN

3. **正確做法：用 Schema 分區**
   - 同一個 DB 內的不同 schema 可以自由 JOIN
   - 可以共用 function 和 extension
   - 權限控制也很靈活

> ### 腦筋急轉彎 🧠
>
> **Q：`public` schema 有什麼特別的？為什麼 Supabase 預設用它？**
>
> A：在 PostgreSQL 裡，`public` 是預設的 `search_path`。
> 當你寫 `SELECT * FROM users` 而不指定 schema，PostgreSQL 會去 `public` 找。
> Supabase 的 PostgREST（API 服務）也預設只暴露 `public` schema。

---

## 三種分區策略比較

| 策略 | 做法 | 適合場景 | 風險 |
|------|------|---------|------|
| **Schema 分區** | `CREATE SCHEMA crawler;` | 多領域單 project | 推薦 🔥 |
| **Table 命名空間** | `crawler_jobs`, `crawler_results` | 小專案、快速原型 | 表太多會亂 |
| **多 Project** | `supabase projects create` | 完全隔離、不同產品線 | 成本高、無法跨庫查詢 |

讓我們用一個具體例子來比較：

```
假設你有 3 個領域：電商、爬蟲、RAG，每個領域 5-10 張表。

❌ 全部塞 public（Table 命名空間）：
   public.ecommerce_users
   public.ecommerce_orders
   public.ecommerce_products
   public.crawler_jobs
   public.crawler_results
   public.crawler_configs
   public.rag_documents
   public.rag_embeddings
   → 15-30 張表全擠在 public，Table Editor 一片混亂

✅ Schema 分區：
   public.profiles          ← 共用的使用者資料
   shop.orders              ← 電商核心
   shop.products
   crawler.jobs             ← 爬蟲 pipeline
   crawler.results
   rag.documents            ← 向量搜尋
   rag.embeddings
   → 每個 schema 只有自己領域的表，清清楚楚
```

---

## 正體中文編碼：你不需要擔心

> **你的大腦在想：「建 Schema 的時候需要設定 UTF-8 嗎？像 MySQL 的 `utf8mb4`？」**
>
> 不用。PostgreSQL 的 UTF-8 = MySQL 的 utf8mb4。預設就是完整 Unicode。

這是 MySQL 出身的工程師最常問的問題，讓我們一次講清楚：

| | MySQL | PostgreSQL (Supabase) |
|--|--|--|
| UTF-8 實作 | `utf8` = 最多 3 bytes（不支援 emoji❌） | `UTF8` = 真正的 UTF-8（1-4 bytes✅） |
| 完整 Unicode | 需要改用 `utf8mb4` | **預設就是完整的** |
| emoji / CJK 支援 | `utf8mb4` 才行 | 預設就行 |
| 正體中文儲存 | `utf8mb4` + `utf8mb4_unicode_ci` | `UTF8` + `en_US.UTF-8`（預設就夠） |

```sql
-- 確認你的資料庫編碼（在 SQL Editor 執行）
SHOW server_encoding;   -- UTF8
SHOW lc_collate;        -- en_US.UTF-8
SHOW lc_ctype;          -- en_US.UTF-8
```

**三件事你必須知道**：

1. **`CREATE SCHEMA` 不能設定編碼** — 編碼是在 Database 層級決定的，Schema 只是命名空間
2. **Supabase 預設 UTF-8** — 所有 Unicode 字元（包含繁體中文、日文、emoji）都能正確儲存
3. **排序（Collation）預設按 Unicode code point** — 不是筆畫或注音。99% 的情況你不需要改

```sql
-- 如果你真的需要中文筆畫排序（極少用到）
SELECT name FROM products ORDER BY name COLLATE "zh-Hant-x-icu";

-- 大部分情況，你的排序是基於時間，不是中文
SELECT * FROM products ORDER BY created_at DESC;  -- 這就夠了
```

> **腦筋急轉彎：「那 `CREATE SCHEMA crawler;` 的 schema 名稱可以用中文嗎？」**
>
> 技術上可以（`CREATE SCHEMA "爬蟲";`），但**千萬不要**。
> Schema 名稱會出現在 SQL、API URL、程式碼裡，用英文保持一致性。

---

## Schema 分區實戰

### 建議的 Schema 分層

```
public        → API Gateway（bridge functions，PostgREST 唯一暴露層）
shop          → 電商核心業務（商品、訂單、使用者管理）
crawler       → Playwright pipeline（爬蟲任務、結果）
rag           → 向量搜尋 + 知識庫
analytics     → 跨域觀測（事件匯流、聚合快照、分析 function）
```

**為什麼 `public` 不放業務邏輯？**

因為 `public` schema 會被 PostgREST 自動暴露成 REST API。如果你把所有表都放在 `public`，它們全部都會變成公開的 API endpoint（除非你用 RLS 擋住）。

比較好的做法是：
- `public` 只放「需要透過 API 存取的表」和「共用 helper function」
- 純後端邏輯（如 crawler pipeline）放在自己的 schema，不暴露 API

---

### 動手做：建立你的 Schema 結構

打開 SQL Editor（`http://localhost:54323`），貼上以下 SQL：

```sql
-- ============================================
-- Step 1: 建立 Schema
-- ============================================
CREATE SCHEMA IF NOT EXISTS shop;
CREATE SCHEMA IF NOT EXISTS crawler;
CREATE SCHEMA IF NOT EXISTS rag;
CREATE SCHEMA IF NOT EXISTS analytics;

-- 確認建立成功
SELECT schema_name
FROM information_schema.schemata
WHERE schema_name IN ('shop', 'crawler', 'rag', 'analytics');
```

按 `Cmd+Enter` 執行。你應該看到四個 schema 名稱。

```sql
-- ============================================
-- Step 1.5: 設定權限（很重要！不做會踩坑）
-- ============================================
-- Supabase 的 anon / authenticated role 預設只能存取 public schema。
-- 如果你希望透過 API 或 bridge function 存取自訂 schema，必須授權。

-- 授權 role 可以「看到」這些 schema
GRANT USAGE ON SCHEMA shop TO anon, authenticated;
GRANT USAGE ON SCHEMA crawler TO anon, authenticated;
GRANT USAGE ON SCHEMA rag TO anon, authenticated;
GRANT USAGE ON SCHEMA analytics TO anon, authenticated;

-- 授權 role 可以讀取這些 schema 裡「現有的」表
GRANT SELECT ON ALL TABLES IN SCHEMA shop TO anon, authenticated;
GRANT SELECT ON ALL TABLES IN SCHEMA crawler TO anon, authenticated;
GRANT SELECT ON ALL TABLES IN SCHEMA rag TO anon, authenticated;
GRANT SELECT ON ALL TABLES IN SCHEMA analytics TO anon, authenticated;

-- 設定未來在這些 schema 建的新表，自動授權（不然每次建表都要重跑 GRANT）
ALTER DEFAULT PRIVILEGES IN SCHEMA shop GRANT SELECT ON TABLES TO anon, authenticated;
ALTER DEFAULT PRIVILEGES IN SCHEMA crawler GRANT SELECT ON TABLES TO anon, authenticated;
ALTER DEFAULT PRIVILEGES IN SCHEMA rag GRANT SELECT ON TABLES TO anon, authenticated;
ALTER DEFAULT PRIVILEGES IN SCHEMA analytics GRANT SELECT ON TABLES TO anon, authenticated;
```

> ### 你的大腦在想 🧠
>
> **「為什麼只 GRANT SELECT，不給 INSERT / UPDATE / DELETE？」**
>
> 因為這些 schema 是後端 pipeline 用的。前端透過 bridge function（`SECURITY DEFINER`）
> 間接操作就好，不需要直接寫入。如果某個 schema 確實需要前端寫入，再加：
> ```sql
> GRANT INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA shop TO authenticated;
> ALTER DEFAULT PRIVILEGES IN SCHEMA shop
>   GRANT INSERT, UPDATE, DELETE ON TABLES TO authenticated;
> ```

```sql
-- ============================================
-- Step 1.6: 設定 search_path（選用）
-- ============================================
-- 預設 search_path 是 public，查詢其他 schema 的表必須加前綴：
--   SELECT * FROM crawler.jobs;     -- 要寫 crawler.
--
-- 如果你經常操作多個 schema，可以擴展 search_path：
ALTER ROLE postgres SET search_path TO public, shop, crawler, rag, analytics;

-- 設定後重新連線生效。之後可以直接寫：
--   SELECT * FROM jobs;  -- PostgreSQL 會依序在 public → shop → crawler → ... 找
--
-- ⚠️ 注意：如果不同 schema 有同名表（如 public.logs 和 analytics.logs），
--    search_path 會找到第一個符合的。建議表名不要跨 schema 重複。
```

```sql
-- ============================================
-- Step 2: 在 crawler schema 建表
-- ============================================
CREATE TABLE crawler.jobs (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  url TEXT NOT NULL,
  status TEXT DEFAULT 'pending'
    CHECK (status IN ('pending', 'running', 'done', 'failed')),
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE crawler.results (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  job_id BIGINT REFERENCES crawler.jobs(id) ON DELETE CASCADE,
  title TEXT,
  content TEXT,
  scraped_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE crawler.configs (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  selectors JSONB NOT NULL DEFAULT '{}',
  max_depth INT DEFAULT 3,
  created_at TIMESTAMPTZ DEFAULT now()
);
```

```sql
-- ============================================
-- Step 3: 在 rag schema 建表
-- ============================================
CREATE TABLE rag.documents (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  source TEXT NOT NULL,
  content TEXT NOT NULL,
  metadata JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE rag.embeddings (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  document_id BIGINT REFERENCES rag.documents(id) ON DELETE CASCADE,
  chunk_index INT NOT NULL,
  chunk_text TEXT NOT NULL,
  -- embedding vector 欄位等啟用 pgvector 後再加
  created_at TIMESTAMPTZ DEFAULT now()
);
```

```sql
-- ============================================
-- Step 3.5: 在 shop schema 建示範表
-- ============================================
CREATE TABLE shop.products (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  name TEXT NOT NULL,
  price NUMERIC(10,2) NOT NULL CHECK (price >= 0),
  stock INT NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE shop.orders (
  id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  product_id BIGINT REFERENCES shop.products(id) ON DELETE RESTRICT,
  quantity INT NOT NULL CHECK (quantity > 0),
  total NUMERIC(10,2) NOT NULL,
  status TEXT DEFAULT 'pending'
    CHECK (status IN ('pending', 'paid', 'shipped', 'cancelled')),
  created_at TIMESTAMPTZ DEFAULT now()
);
```

> **注意**：這裡用 `ON DELETE RESTRICT`（不是 CASCADE）。刪商品時如果還有訂單參照，
> PostgreSQL 會拒絕刪除——這是商業邏輯上正確的行為：你不該刪掉有訂單紀錄的商品。

```sql
-- ============================================
-- Step 4: 插入測試資料
-- ============================================
INSERT INTO crawler.jobs (url, status) VALUES
  ('https://example.com/page1', 'pending'),
  ('https://example.com/page2', 'running'),
  ('https://example.com/page3', 'done');

INSERT INTO rag.documents (source, content) VALUES
  ('wiki/postgresql', '# PostgreSQL 是什麼？\n\nPostgreSQL 是一個開源的關聯式資料庫...'),
  ('wiki/supabase', '# Supabase 是什麼？\n\nSupabase 是開源的 Firebase 替代方案...');

INSERT INTO shop.products (name, price, stock) VALUES
  ('PostgreSQL 實戰手冊', 580.00, 50),
  ('Supabase 入門套件', 1200.00, 20);

INSERT INTO shop.orders (product_id, quantity, total, status) VALUES
  (1, 2, 1160.00, 'paid'),
  (2, 1, 1200.00, 'pending');
```

現在，切到 Table Editor 驗證結果 → 詳細操作見下方 [Table Editor 操作不同 Schema](#table-editor-操作不同-schema) 段落。

---

## Schema vs public 的 RLS 差異

這是一個很重要的觀念，值得單獨拿出來講：

```
┌─────────────────────────────────────────────────┐
│  PostgREST（API 服務）                           │
│                                                  │
│  預設暴露：public schema 的所有表                  │
│  不暴露：其他 schema（crawler, rag, analytics）    │
│                                                  │
│  public.users    →  GET /rest/v1/users     ✅    │
│  public.orders   →  GET /rest/v1/orders    ✅    │
│  crawler.jobs    →  ❌ 沒有 API endpoint         │
│  rag.documents   →  ❌ 沒有 API endpoint         │
└─────────────────────────────────────────────────┘
```

**這代表什麼？**

| Schema | 有 REST API？ | 需要 RLS？ | 存取方式 |
|--------|-------------|-----------|---------|
| `public` | 有，自動生成 | **一定要**（不然任何人都能讀寫） | 前端 SDK、curl、PostgREST |
| `crawler` | 沒有 | 看情況（後端直連就不一定需要） | Database Function、psql、後端服務直連 |
| `rag` | 沒有 | 看情況 | 同上 |

**對於純後端 pipeline（如 crawler），不暴露 API 反而更安全。**

但如果你的前端需要查詢 crawler 的狀態怎麼辦？用 Database Function 當橋樑：

```sql
-- 在 public schema 建一個 function，間接查詢 crawler schema
CREATE OR REPLACE FUNCTION public.get_crawler_stats()
RETURNS TABLE(status TEXT, count BIGINT)
LANGUAGE sql
STABLE
SECURITY DEFINER  -- 用 function owner 的權限執行
AS $$
  SELECT status, count(*)
  FROM crawler.jobs
  GROUP BY status;
$$;
```

這樣：
- `crawler.jobs` 本身沒有 REST API（安全）
- 前端透過 `rpc('get_crawler_stats')` 呼叫這個 function（受控）
- 你可以在 function 裡加邏輯，決定回傳什麼資料（靈活）

> ⚠️ **`SECURITY DEFINER` 安全須知**
>
> `SECURITY DEFINER` 表示這個 function 用**建立者（owner）的權限**執行，而不是呼叫者的權限。
> 這代表它會**繞過 RLS**。使用時必須注意：
>
> 1. **function 內部自己做權限檢查**（例如檢查 `auth.uid()`）
> 2. **只回傳聚合/摘要資料**，不要回傳原始 row（上面的範例只回傳 count，是安全的）
> 3. **不要在 function 裡接受使用者輸入直接拼 SQL**，避免 SQL injection
>
> 如果你的 function 不需要跨 schema 存取，用預設的 `SECURITY INVOKER` 就好。

**測試一下**：

```bash
# 透過 API 呼叫 function
curl 'http://localhost:54321/rest/v1/rpc/get_crawler_stats' \
  -H "apikey: YOUR_ANON_KEY" \
  -H "Authorization: Bearer YOUR_ANON_KEY"
```

```sql
-- 或者在 SQL Editor 直接呼叫
SELECT * FROM public.get_crawler_stats();

-- 預期結果：
--  status  | count
-- ---------+-------
--  pending |     1
--  running |     1
--  done    |     1
```

---

## Table Editor 操作不同 Schema

讓我們確認你會在 Table Editor 裡切換 schema：

```
📝 Step-by-step：在 Table Editor 操作 crawler schema

1. 打開 Table Editor（左邊 sidebar 點 Table Editor）

2. 找到上方的 schema 選擇器
   ┌─────────────────────────┐
   │  Schema: [public ▼]     │  ← 就是這個下拉選單
   └─────────────────────────┘

3. 點擊下拉 → 選擇 "crawler"
   ┌─────────────────────────┐
   │  ☑ public               │
   │  ☐ auth                 │
   │  ☐ storage              │
   │  ☑ crawler        ← 選這個
   │  ☐ rag                  │
   │  ☐ analytics            │
   └─────────────────────────┘

4. 現在你看到 crawler schema 的表：
   - jobs（3 筆資料）
   - results（0 筆）
   - configs（0 筆）

5. 點進 jobs → 你可以直接在 GUI：
   - 新增一筆（點 + Insert row）
   - 修改資料（直接點格子編輯）
   - 查看欄位定義（點上方的欄位名稱）

6. 切到 "shop" → 看到 products（2 筆）和 orders（2 筆）

7. 切到 "rag" → 看到 documents（2 筆）和 embeddings（0 筆）
```

> ### 腦筋急轉彎 🧠
>
> **Q：如果你在 Table Editor 看不到新建的表，第一件事檢查什麼？**
>
> A：Schema 選擇器！預設只顯示 `public`。
> 你剛建的表在 `crawler`、`shop`、`rag` schema，不會出現在 `public` 的列表裡。
> 切換 schema 選擇器就能看到了。

> ### 你的大腦在想 🧠
>
> 「那我在 Table Editor 的 crawler schema 裡新增一張表，跟在 SQL Editor 寫 `CREATE TABLE crawler.xxx` 有什麼差？」
>
> 功能上沒差——Table Editor 背後也是跑 SQL。
> 但差別在於：**Table Editor 的操作不會留下 SQL 紀錄**。
>
> 如果你在 Table Editor 建了一張表，然後跑 `supabase db diff`，它會幫你生成對應的 migration SQL。
> 但最佳實踐還是：在 SQL Editor 寫好 SQL → 存成 migration 檔。
> 完整的 migration 工作流請見 [06_migration-workflow.md](06_migration-workflow.md)。

---

## 動手做：多 Schema 完整練習

```
📝 Exercise: 建立 multi-schema 環境（預計 15 分鐘）

Part 1：建立結構（SQL Editor）
1. 確認 crawler schema 已建立（前面的步驟）
2. 確認 rag schema 已建立
3. 在 analytics schema 建一張 logs 表：
   CREATE TABLE analytics.logs (
     id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
     event TEXT NOT NULL,
     payload JSONB DEFAULT '{}',
     created_at TIMESTAMPTZ DEFAULT now()
   );

Part 2：跨 schema 查詢（SQL Editor）
4. 寫一個 JOIN 查詢 crawler.jobs 和 crawler.results：
   SELECT j.url, j.status, r.title
   FROM crawler.jobs j
   LEFT JOIN crawler.results r ON r.job_id = j.id;

5. 寫一個查詢統計每個 schema 有多少張表：
   SELECT schemaname, count(*) as table_count
   FROM pg_tables
   WHERE schemaname IN ('shop', 'crawler', 'rag', 'analytics')
   GROUP BY schemaname
   ORDER BY table_count DESC;

Part 3：GUI 驗證（Table Editor）
6. 切到 Table Editor → 用 schema 選擇器分別檢視
   - public：看有哪些預設表
   - shop：應該有 2 張表（products, orders）
   - crawler：應該有 3 張表
   - rag：應該有 2 張表
   - analytics：應該有 1 張表

Part 4：API 橋樑（SQL Editor）
7. 建立一個 public function 查詢 crawler.jobs 統計
   （參考上面的 get_crawler_stats 範例）

8. 用 API Docs 頁面確認：
   - public 的表出現在 REST API ✅
   - crawler/rag 的表不在 REST API ❌（這是正確的！）
   - get_crawler_stats function 出現在 API Docs ✅
```

---

## 砍掉重練：清空 Schema

練習到一半搞亂了？想從頭來過？這很正常。以下是三種常見的「重置」方式。

### 方法 1：清空單一 Schema（最常用）

把某個 schema 整個砍掉再重建，裡面的表、function、view 全部消失：

```sql
-- 例：重建 crawler schema
DROP SCHEMA crawler CASCADE;
CREATE SCHEMA crawler;
```

> ⚠️ `CASCADE` 會連同該 schema 下的**所有物件**一起刪除，包含表、function、view、trigger、type。

### 方法 2：重建 public Schema

`public` 比較特殊，刪掉之後要補回預設權限：

```sql
-- 砍掉整個 public schema
DROP SCHEMA public CASCADE;

-- 重建空的 public + 恢復預設權限
CREATE SCHEMA public;
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO public;
```

**這會影響什麼？**
- `public` 裡的所有表、function、RLS policy → 全部消失
- `auth`、`storage`、`extensions` schema → **不受影響**
- 如果有開 Realtime 訂閱 → 需要重新設定

### 方法 3：只刪表，保留 Function / Type

如果你只想清掉表和資料，但保留寫好的 function：

```sql
-- 刪除 public schema 裡的所有表（保留 function、type）
DO $$ DECLARE
  r RECORD;
BEGIN
  FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
    EXECUTE 'DROP TABLE IF EXISTS public.' || quote_ident(r.tablename) || ' CASCADE';
  END LOOP;
END $$;
```

要清其他 schema，把 `'public'` 換成目標 schema 名稱即可。

### 遇到 Foreign Key 卡住怎麼辦？

當兩張表有 FK 關聯（例如 `crawler.results.job_id → crawler.jobs.id`），直接刪會報錯：

```
ERROR: cannot drop table crawler.jobs because other objects depend on it
DETAIL: constraint results_job_id_fkey on table crawler.results depends on table crawler.jobs
```

這是因為 PostgreSQL 保護你，不讓你刪掉別人還在參照的表。以下是四種解法：

#### 解法 1：用 CASCADE 連鎖刪除（最直接）

```sql
-- 刪表：CASCADE 會自動刪除所有依賴這張表的 FK constraint
DROP TABLE crawler.jobs CASCADE;
-- ⚠️ 注意：這不會刪 results 表本身，只會刪掉 results 上的 FK constraint
--    results 表還在，但 job_id 欄位不再有 FK 保護
```

```sql
-- 刪資料：CASCADE 搭配 ON DELETE CASCADE 的 FK 設計
-- 如果建表時寫了 REFERENCES crawler.jobs(id) ON DELETE CASCADE
-- 那刪 jobs 的一筆資料，對應的 results 資料會自動跟著刪
DELETE FROM crawler.jobs WHERE id = 1;
-- → results 裡 job_id = 1 的資料也會自動消失
```

#### 解法 2：按順序刪（先子後父）

```sql
-- 先刪子表（有 FK 的那張），再刪父表
DROP TABLE crawler.results;   -- 子表先走
DROP TABLE crawler.jobs;      -- 父表再走，不會報錯
```

```sql
-- 清資料也一樣：先清子表
TRUNCATE crawler.results;
TRUNCATE crawler.jobs;
```

#### 解法 3：暫時關掉 FK 檢查（清資料用）

```sql
-- TRUNCATE 支援一次清多張表 + 自動處理 FK
TRUNCATE crawler.jobs, crawler.results;
-- ⚠️ 如果其他表也參照 jobs，需要全部列出來

-- 或者用 CASCADE 讓 TRUNCATE 自動找出所有關聯表一起清
TRUNCATE crawler.jobs CASCADE;
-- → 會連 results 的資料一起清空（表結構保留）
```

#### 解法 4：手動解除 FK 再操作

```sql
-- 先查出 FK constraint 名稱
SELECT conname, conrelid::regclass, confrelid::regclass
FROM pg_constraint
WHERE confrelid = 'crawler.jobs'::regclass;
-- 結果例：results_job_id_fkey | crawler.results | crawler.jobs

-- 手動刪除 FK constraint
ALTER TABLE crawler.results DROP CONSTRAINT results_job_id_fkey;

-- 現在可以自由操作了
DROP TABLE crawler.jobs;       -- 不會報錯
-- 或
DELETE FROM crawler.jobs;      -- 不會報錯

-- 操作完畢後，如果 results 表還在，記得補回 FK
ALTER TABLE crawler.results
  ADD CONSTRAINT results_job_id_fkey
  FOREIGN KEY (job_id) REFERENCES crawler.jobs(id) ON DELETE CASCADE;
```

#### FK 解法對照

| 情境 | 推薦解法 |
|------|---------|
| 整張表不要了 | 解法 1（`DROP TABLE ... CASCADE`）或解法 2（按順序刪） |
| 清空資料但保留表結構 | 解法 3（`TRUNCATE ... CASCADE`） |
| 只刪特定幾筆資料 | 確認建表時有 `ON DELETE CASCADE`，直接 `DELETE` 就好 |
| 想精確控制哪些 constraint 要拆 | 解法 4（手動解除 FK） |

> ### 你的大腦在想 🧠
>
> **「`ON DELETE CASCADE` 和 `DROP TABLE ... CASCADE` 的 CASCADE 是同一個意思嗎？」**
>
> 不是！這是最容易搞混的地方：
>
> | | 作用對象 | 效果 |
> |--|---------|------|
> | `ON DELETE CASCADE`（建表時設定） | **資料層級** | 刪父表的一筆 row → 子表對應的 row 自動跟著刪 |
> | `DROP TABLE ... CASCADE`（DDL 指令） | **結構層級** | 刪表時 → 自動移除其他表上依賴它的 constraint |
> | `TRUNCATE ... CASCADE`（DML 指令） | **資料層級** | 清空表時 → 連同有 FK 參照的子表資料一起清空 |
>
> 三個 `CASCADE` 長得一樣，但作用範圍完全不同。

---

### 重置方法總整理

| 情境 | 推薦方法 |
|------|---------|
| 練習搞砸了，想整個重來 | 方法 1（單一 schema）或方法 2（public） |
| 只是資料亂了，結構沒問題 | `TRUNCATE` 個別表就好（有 FK 參考上方解法） |
| 想保留 function，只砍表 | 方法 3 |
| 想重置整個 project（包含 auth） | Supabase Dashboard → Settings → General → Delete project |
| 重建 schema 後記得重跑 | Step 1.5 的 `GRANT USAGE` + `ALTER DEFAULT PRIVILEGES` |

> ### 腦筋急轉彎 🧠
>
> **Q：為什麼 `DROP SCHEMA public CASCADE` 不會影響 `auth` 和 `storage`？**
>
> A：因為它們是**不同的 schema**。`CASCADE` 只會刪除被指定 schema 裡面的物件，
> 不會跨到其他 schema。這也是 Schema 分區的好處之一——爆炸半徑被限制在單一 schema 內。

---

## 你的專案該用哪種策略？

做決定之前，先回答一個問題：

```
你的專案有幾個獨立的業務領域？

├── 1 個領域（例如：只做電商）
│   └── 用 public 就好，不需要自訂 schema
│
├── 2-4 個領域（例如：電商 + 爬蟲 + RAG）
│   └── Schema 分區（推薦 🔥）
│       每個領域一個 schema，public 放共用的東西
│
├── 5+ 個領域
│   └── Schema 分區 + 考慮拆 project
│       太多 schema 也會混亂，評估是否需要獨立部署
│
└── 完全不同的產品（例如：公司 A 產品 + 公司 B 產品）
    └── 多 Project
        不同的 team、不同的部署、不同的帳單
```

> ### 腦筋急轉彎 🧠
>
> **Q：什麼時候 Schema 分區不夠用，必須拆成多個 Project？**
>
> A：當兩個業務需要：
> - 不同的 Supabase 版本或設定
> - 不同的計費方式
> - 完全獨立的資安邊界（如：醫療 vs 電商）
> - 不同的 region（如：一個在美國、一個在亞洲）
>
> 如果只是「表太多會混亂」，Schema 分區就夠了。

---

## 連結到後續 Stage

你在這份教程裡建立的 schema 結構，會在後續的課程中真正填入業務邏輯：

| Schema | 對應 Stage | 預計表數量 | 教程位置 |
|--------|-----------|-----------|---------|
| `shop` (電商) | Stage 3 | 約 20 張 | [03_shop/](../03_shop/00_README.md) |
| `crawler` | Stage 4 | 約 10 張 | [04_crawler/](../04_crawler/00_README.md) |
| `rag` | Stage 5 | 約 7 張 | [05_rag/](../05_rag/00_README.md) |
| `analytics` | 跨域 | 5 表 + 3 MATVIEW + 20 functions | [06_analytics/](../06_analytics/00_README.md) |

> **注意**：電商 Schema 使用獨立的 `shop` schema。
> PostgREST 預設只暴露 `public`，如果你希望 `shop` 的表也有 REST API，有兩種做法：
>
> **做法 A：修改 PostgREST 暴露的 schema（Supabase Cloud）**
> 1. Dashboard → Settings → API → Schema Settings
> 2. 在 `Exposed schemas` 加入 `shop`
> 3. 儲存後，`shop.products` 就會出現在 REST API
>
> **做法 B：本地開發用 `config.toml`**
> ```toml
> # supabase/config.toml
> [api]
> schemas = ["public", "shop"]
> ```
> 重啟 `supabase stop && supabase start` 生效。
>
> **做法 C：不暴露 schema，用 Database Function 橋接**（本文前面示範的方式）

```
現在的你                         未來的你
    │                               │
    ▼                               ▼
建好 schema 骨架              每個 schema 裡都有
（空的資料夾）                完整的表、index、RLS、function
```

---

## 重點回顧

```
✅ 一個 Supabase project = 一個 PostgreSQL DB
✅ 用 Schema 分區，不要建多個 DB
✅ public schema 會被 PostgREST 暴露成 REST API
✅ 非 public schema 的表需要透過 Database Function 存取
✅ 自訂 schema 必須 GRANT USAGE 給 anon/authenticated，否則存取不了
✅ ALTER DEFAULT PRIVILEGES 確保未來建的表自動有權限
✅ search_path 決定查詢時 PostgreSQL 去哪些 schema 找表
✅ SECURITY DEFINER function 會繞過 RLS，要小心使用
✅ Table Editor 的 schema 選擇器可以切換不同 schema
✅ 正式結構變更用 SQL Editor + migration，不要只用 GUI
```

**下一步**：打開 `03_sql-editor-mastery.md`，學會在 SQL Editor 裡做 CRUD、建 Index、用 `EXPLAIN ANALYZE` 分析效能。

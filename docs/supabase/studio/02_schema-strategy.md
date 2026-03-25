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
   app.orders               ← 電商核心
   app.products
   crawler.jobs             ← 爬蟲 pipeline
   crawler.results
   rag.documents            ← 向量搜尋
   rag.embeddings
   → 每個 schema 只有自己領域的表，清清楚楚
```

---

### 正體中文編碼：你不需要擔心

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
public        → Supabase 預設（auth bridge, shared helpers）
app           → SaaS 核心業務（電商、使用者管理）
crawler       → Playwright pipeline（爬蟲任務、結果）
rag           → 向量搜尋 + 知識庫
analytics     → logs / metrics（分析、監控）
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
CREATE SCHEMA IF NOT EXISTS crawler;
CREATE SCHEMA IF NOT EXISTS rag;
CREATE SCHEMA IF NOT EXISTS analytics;

-- 確認建立成功
SELECT schema_name
FROM information_schema.schemata
WHERE schema_name IN ('crawler', 'rag', 'analytics');
```

按 `Cmd+Enter` 執行。你應該看到三個 schema 名稱。

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
-- Step 4: 插入測試資料
-- ============================================
INSERT INTO crawler.jobs (url, status) VALUES
  ('https://example.com/page1', 'pending'),
  ('https://example.com/page2', 'running'),
  ('https://example.com/page3', 'done');

INSERT INTO rag.documents (source, content) VALUES
  ('wiki/postgresql', '# PostgreSQL 是什麼？\n\nPostgreSQL 是一個開源的關聯式資料庫...'),
  ('wiki/supabase', '# Supabase 是什麼？\n\nSupabase 是開源的 Firebase 替代方案...');
```

現在，**切到 Table Editor**：

```
📝 關鍵步驟：在 Table Editor 查看你剛建的表

1. 打開 Table Editor
2. 看上方的 schema 選擇器 → 預設顯示 "public"
3. 點擊下拉選單 → 選擇 "crawler"
4. 你會看到三張表：jobs, results, configs
5. 點進 jobs → 你剛插入的三筆測試資料就在那裡
6. 切換到 "rag" schema → 看到 documents 和 embeddings
```

> ### 腦筋急轉彎 🧠
>
> **Q：如果你在 Table Editor 看不到新建的表，第一件事檢查什麼？**
>
> A：Schema 選擇器！預設只顯示 `public`。
> 你剛建的表在 `crawler` 和 `rag` schema，不會出現在 `public` 的列表裡。
> 切換 schema 選擇器就能看到了。

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

6. 試試切到 "rag" → 看到 documents 和 embeddings
```

> ### 你的大腦在想 🧠
>
> 「那我在 Table Editor 的 crawler schema 裡新增一張表，跟在 SQL Editor 寫 `CREATE TABLE crawler.xxx` 有什麼差？」
>
> 功能上沒差——Table Editor 背後也是跑 SQL。
> 但差別在於：**Table Editor 的操作不會留下 SQL 紀錄**。
>
> 如果你在 Table Editor 建了一張表，然後跑 `supabase db diff`，它會幫你生成對應的 migration SQL。
> 但最佳實踐還是：在 SQL Editor 寫好 SQL → 存成 migration 檔。

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
   WHERE schemaname IN ('public', 'crawler', 'rag', 'analytics')
   GROUP BY schemaname
   ORDER BY table_count DESC;

Part 3：GUI 驗證（Table Editor）
6. 切到 Table Editor → 用 schema 選擇器分別檢視
   - public：看有哪些預設表
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
| `public` (電商 + 共用) | Stage 3 | 約 20 張 | [e-Commerce/](../e-Commerce/00_README.md) |
| `crawler` | Stage 4 | 約 10 張 | [crawler/](../crawler/00_README.md) |
| `rag` | Stage 5 | 約 7 張 | [RAG/](../RAG/00_README.md) |

> **注意**：目前電商 Schema 使用 `public`（因為 PostgREST 預設只暴露 public）。
> 在實際多領域專案中，你可以把電商移到 `app` schema 並設定 PostgREST 的 `db-schemas`。

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
✅ Table Editor 的 schema 選擇器可以切換不同 schema
✅ 正式結構變更用 SQL Editor + migration，不要只用 GUI
```

**下一步**：打開 `03_sql-editor-mastery.md`，學會在 SQL Editor 裡做 CRUD、建 Index、用 `EXPLAIN ANALYZE` 分析效能。

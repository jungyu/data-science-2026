---
name: supabase-schema-design-production
description: "生產級 Schema 設計：ULID 強制、資料分層、多租戶模型、資料科學表範例"
triggers:
  - "schema design"
  - "新增表"
  - "資料模型"
  - "多租戶"
  - "project_id"
finish_conditions:
  - "所有表使用 ULID (TEXT PK)"
  - "業務表包含 project_id"
  - "JSONB 僅用於非結構化資料"
  - "表名符合模組前綴慣例"
references:
  - docs/supabase/e-Commerce/README.md
  - docs/supabase/crawler/HEAD-FIRST-crawler-db.md
---

# Schema Design（生產級）

> ⚠️ **前置條件**：已完成 `foundations/schema-basics.md` 的學習。
> 本文件對應 e-Commerce Stage 1-10 和 Crawler HEAD-FIRST 的進階規範。

---

## 目的

強制分層架構、ULID 統一、多租戶模型、表結構一致性。避免 AI 在進階專案中產生不合規的 schema。

## Repo Reality

- `docs/supabase/e-Commerce/README.md` — 20 張表的完整電商 schema（ULID、Auth Bridge、RLS）
- `docs/supabase/e-Commerce/shop_supabase_native_schema.sql` — 電商 schema SQL
- `docs/supabase/crawler/HEAD-FIRST-crawler-db.md` — 10 張表，29 個違規修正

---

## 核心原則

### 1. Domain-Scoped Schema（領域隔離）

**來自 `migrations/001_extensions.sql`**：每個業務領域使用獨立 schema，不要全部擠在 `public`。

```sql
CREATE SCHEMA IF NOT EXISTS shop;
CREATE SCHEMA IF NOT EXISTS crawler;
CREATE SCHEMA IF NOT EXISTS rag;
CREATE SCHEMA IF NOT EXISTS analytics;
```

**好處**：
- 命名空間隔離（不同 schema 可有同名表，如 `crawler.tags` / `rag.tags`）
- RLS helper function 可用 `SET search_path = <schema>` 限縮作用域
- 每個 schema 可獨立 GRANT/REVOKE
- PostgREST 只暴露 `public` schema → 業務邏輯隱藏在各自 schema

**共用基礎設施放 `public`**：`generate_ulid()`、auth bridge functions。

**Schema 依賴順序**（必須在 migration header 明確宣告）：

```
001_extensions.sql      ← 共用基礎（schema + extensions + ULID）
002_shop_schema.sql
003_crawler_schema.sql
004_rag_schema.sql
005_analytics_schema.sql ← 依賴 002-004
006_public_api.sql       ← 依賴 002-005
```

### 2. 資料分層架構

```
Raw Layer       = 原始資料（爬蟲抓取、API 匯入、CSV 上傳）
Staging Layer   = 清理 / 轉換後的中繼資料
Analytics Layer = 聚合、特徵、模型輸入/輸出
Metadata Layer  = 實驗追蹤、資料集註冊
```

**不可違反**：
- 不要在 Raw 表直接做分析查詢 → 先 ETL 到 Staging/Analytics
- 不要在 DB 存大型二進位（模型權重、圖片原檔）→ 放 Storage，DB 只存 path
- 原始資料盡量 append-only（方便回溯）

### 3. 多租戶模型

使用 **single database + shared tables + tenant scoping**（e-Commerce Stage 2 教的模式）：

```sql
-- 所有業務表必須有 project_id
project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE
```

權限查詢走 helper functions，不在每張表重寫 JOIN。

### 4. 表結構必備欄位（ULID 版）

```sql
id TEXT PRIMARY KEY DEFAULT generate_ulid(),
created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
```

使用者操作的資料加：`created_by TEXT NOT NULL REFERENCES users(id)`

updated_at trigger（**優先用 moddatetime**，不要手寫）：

```sql
-- ✅ 推薦：moddatetime extension（001_extensions.sql 已啟用）
CREATE TRIGGER trg_<table>_updated_at
  BEFORE UPDATE ON <schema>.<table>
  FOR EACH ROW EXECUTE FUNCTION moddatetime(updated_at);

-- 批次建立（來自 003_crawler_schema.sql）
DO $$
DECLARE tbl TEXT;
BEGIN
  FOREACH tbl IN ARRAY ARRAY['sources','crawl_runs','articles','tags']
  LOOP
    EXECUTE format('
      DROP TRIGGER IF EXISTS trg_%1$s_updated_at ON crawler.%1$s;
      CREATE TRIGGER trg_%1$s_updated_at
        BEFORE UPDATE ON crawler.%1$s
        FOR EACH ROW EXECUTE FUNCTION moddatetime(updated_at);
    ', tbl);
  END LOOP;
END;
$$;
```

### 5. JSONB 使用原則

**黃金法則**（e-Commerce Stage 4）：
> 會被 `WHERE`、`ORDER BY`、`JOIN` 的欄位 → 獨立 column。其他 → JSONB。

**適合 JSONB**：爬蟲原始 payload、模型超參數、實驗配置、外部 API 回應。
**禁止 JSONB**：`project_id`、`status`、`name`、任何 filter/sort 欄位。

**JSONB 必須加 GIN index**（來自 `004_rag_schema.sql`）：

```sql
CREATE INDEX IF NOT EXISTS idx_chunks_metadata ON rag.chunks USING GIN(metadata);
CREATE INDEX IF NOT EXISTS idx_events_payload ON analytics.events USING GIN(payload);
```

### 6. 狀態機模式（Process State Machine）

**來自 `004_rag_schema.sql`**：用 CHECK constraint 定義明確狀態集合，追蹤處理管線。

```sql
-- 文件處理管線（RAG ingestion）
process_status TEXT NOT NULL DEFAULT 'uploaded',
CONSTRAINT ck_documents_process_status
  CHECK (process_status IN (
    'uploaded', 'parsed', 'chunked', 'embedded', 'ready', 'failed', 'stale'
  ))
```

```sql
-- 任務佇列（Crawler lease-based queue）
status TEXT NOT NULL DEFAULT 'pending',
CONSTRAINT ck_crawl_queue_status
  CHECK (status IN ('pending','leased','running','done','failed','skipped','dead'))
```

**規則**：
- 狀態名稱用小寫英文，不要用數字代碼
- 狀態集合用 CHECK constraint 強制，不要只靠 application 層
- append-heavy 的 state-machine 表（如 `crawl_queue`）不需要 `updated_at` trigger

### 7. 反正規化 + Trigger 強制一致性

**來自 `004_rag_schema.sql`**：當 RLS 或查詢效能需要時，可反正規化欄位，但**必須用 trigger 維護一致性**。

```sql
-- chunks 表反正規化 collection_id 和 owner_id（從 documents 繼承）
CREATE TABLE IF NOT EXISTS rag.chunks (
  document_id   TEXT NOT NULL REFERENCES rag.documents(id),
  collection_id TEXT NOT NULL REFERENCES rag.collections(id),  -- 反正規化
  owner_id      TEXT,                                           -- 反正規化
  ...
);

-- Trigger：INSERT/UPDATE 時自動同步
CREATE OR REPLACE FUNCTION rag.sync_chunk_from_document()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER
SET search_path = rag, auth, public AS $$
DECLARE
  v_collection_id TEXT; v_owner_id TEXT;
BEGIN
  SELECT d.collection_id, d.owner_id INTO v_collection_id, v_owner_id
  FROM rag.documents d WHERE d.id = NEW.document_id;
  NEW.collection_id := v_collection_id;
  NEW.owner_id := v_owner_id;
  RETURN NEW;
END;
$$;

CREATE TRIGGER trg_chunks_sync_collection
  BEFORE INSERT OR UPDATE OF document_id ON rag.chunks
  FOR EACH ROW EXECUTE FUNCTION rag.sync_chunk_from_document();
```

**何時該反正規化**：
- RLS policy 需要某欄位（如 `owner_id`）但原表在上游 → 反正規化 + trigger
- 高頻 JOIN 查詢的 FK 層級太深（3+ 層）→ 反正規化到葉節點

**何時不該**：小表、低頻查詢、RLS 不需要的欄位。

### 8. 軟外鍵與多型關聯（Soft FK / Polymorphic Relations）

**來自 `004_rag_schema.sql`**：當一張表需要引用多種來源時。

```sql
-- documents 可來自 crawler、手動上傳、URL 等
source_ref_type TEXT,   -- 'crawler_article', 'upload', 'url'
source_ref_id   TEXT,   -- 對應來源的 ID

CONSTRAINT ck_documents_source_type
  CHECK (source_type IN ('text', 'pdf', 'html', 'markdown', 'url', 'crawler'))
```

**規則**：
- `source_ref_type` + `source_ref_id` 搭配使用，不用 FK constraint
- 加 partial composite index：`WHERE source_ref_type IS NOT NULL`
- 在 application 層驗證引用完整性

### 9. 欄位級存取控制（Column-Level Security via Views）

**來自 `004_rag_schema.sql`**：PostgreSQL 沒有原生 column-level RLS，用 `security_invoker` VIEW 解決。

```sql
-- 隱藏 embedding 向量（~6KB/row），前端只查 VIEW
CREATE OR REPLACE VIEW rag.chunks_safe
  WITH (security_invoker = true)
  AS SELECT
    id, document_id, collection_id, content, chunk_index,
    token_count, metadata, created_at, updated_at
    -- embedding 欄位被排除！
  FROM rag.chunks;

GRANT SELECT ON rag.chunks_safe TO authenticated, anon;
```

**何時該用**：
- 大型欄位（vector、大 JSONB payload、raw_html）不該讓一般查詢回傳
- 敏感欄位只有 SECURITY DEFINER function 需要

### 10. 模組表命名建議

| 模組 | Schema | 範例（來自 migrations） |
|------|--------|----------------------|
| 電商 | `shop` | `shop.products`, `shop.orders`, `shop.reviews` |
| 爬蟲 | `crawler` | `crawler.sources`, `crawler.crawl_runs`, `crawler.articles` |
| RAG | `rag` | `rag.collections`, `rag.documents`, `rag.chunks` |
| 分析 | `analytics` | `analytics.events`, `analytics.daily_shop_stats` |
| 資料集 | `public` 或自訂 | `datasets`, `dataset_versions` |
| 實驗 | `public` 或自訂 | `experiments`, `experiment_runs` |

---

## 實際範例：Crawler 的 sources 表（修正後）

來自 `migrations/003_crawler_schema.sql`：

```sql
CREATE TABLE IF NOT EXISTS crawler.sources (
  id               TEXT PRIMARY KEY DEFAULT public.generate_ulid(),
  project_id       TEXT         NOT NULL,
  code             TEXT         NOT NULL,
  name             TEXT         NOT NULL,
  base_url         TEXT,
  config           JSONB        NOT NULL DEFAULT '{}'::JSONB,
  is_enabled       BOOLEAN      NOT NULL DEFAULT TRUE,
  created_by       TEXT,
  created_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
  updated_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
  CONSTRAINT uq_sources_code_per_project UNIQUE (project_id, code)
);

CREATE INDEX IF NOT EXISTS idx_sources_project ON crawler.sources(project_id);
CREATE INDEX IF NOT EXISTS idx_sources_enabled ON crawler.sources(project_id, is_enabled)
  WHERE is_enabled = TRUE;  -- Partial index
```

## 常見錯誤

- ❌ 所有表擠在 `public` schema → 用 domain-scoped schema（shop/crawler/rag/analytics）
- ❌ 原始爬蟲資料和分析結果混同一表 → 分層：raw → staging → analytics
- ❌ 模型權重塞 DB → 放 Storage，DB 只存 metadata + path
- ❌ 超參數拆 100 個欄位 → JSONB
- ❌ 可篩選欄位放 JSONB → 拉出為獨立 column
- ❌ 反正規化欄位沒有 trigger → 資料不一致
- ❌ 狀態欄位沒有 CHECK constraint → 無效狀態進入 DB
- ❌ 手寫 `updated_at` trigger → 用 moddatetime extension

## 參考來源

- `docs/supabase/migrations/001_extensions.sql` — Schema + Extensions + ULID
- `docs/supabase/migrations/003_crawler_schema.sql` — Crawler 完整範例
- `docs/supabase/migrations/004_rag_schema.sql` — RAG 向量搜尋 + 反正規化 + 狀態機
- `docs/supabase/e-Commerce/README.md` — Stage 1-10 完整架構
- `docs/supabase/crawler/HEAD-FIRST-crawler-db.md` — 29 違規修正

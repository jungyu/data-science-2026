---
name: supabase-migration-guidelines-production
description: "生產級 Migration 規範：檔案命名、必備元素、Index 策略、冪等性"
triggers:
  - "migration"
  - "CREATE TABLE"
  - "ALTER TABLE"
  - "supabase db push"
finish_conditions:
  - "Migration 含 table + index + trigger + RLS + GRANT"
  - "所有 DDL 冪等"
  - "FK 有 index"
references:
  - docs/supabase/e-Commerce/README.md
  - docs/supabase/crawler/HEAD-FIRST-crawler-db.md
---

# Migration Guidelines（生產級）

> ⚠️ **前置條件**：已完成 `foundations/schema-basics.md`。

## Repo Reality

- `docs/supabase/e-Commerce/README.md` — Stage 2-3: Auth Bridge + 完整 migration 範例
- `docs/supabase/crawler/HEAD-FIRST-crawler-db.md` — Stage 1-4: 從錯誤到正確的 migration

---

## 檔案命名與執行順序

### 命名規範

`NNN_<scope>_<description>.sql`（用序號管理依賴順序）

```
001_extensions.sql          ← 共用基礎（schema + extensions + ULID）
002_shop_schema.sql
003_crawler_schema.sql
004_rag_schema.sql
005_analytics_schema.sql    ← 依賴 002-004
006_public_api.sql          ← 依賴 002-005
```

### 執行順序宣告（必備 header）

**來自 `migrations/001_extensions.sql`**：每份 migration 開頭必須宣告自身位置和依賴。

```sql
-- ============================================================
-- 003: Crawler Schema v3.0
-- ============================================================
-- 執行順序：
--   001_extensions.sql        ← 共用基礎
--   002_shop_schema.sql
--   003_crawler_schema.sql    ← 你在這裡
--   004_rag_schema.sql
--   005_analytics_schema.sql  ← 依賴 002-004
-- ============================================================
```

## 一份 Migration 的必備元素

**來自 `migrations/003_crawler_schema.sql` 的完整範例**：

```sql
-- 1. Table（Domain-scoped schema）
CREATE TABLE IF NOT EXISTS crawler.sources (
  id              TEXT PRIMARY KEY DEFAULT public.generate_ulid(),
  project_id      TEXT         NOT NULL,
  code            TEXT         NOT NULL,
  name            TEXT         NOT NULL,
  config          JSONB        NOT NULL DEFAULT '{}'::JSONB,
  is_enabled      BOOLEAN      NOT NULL DEFAULT TRUE,
  created_by      TEXT,
  created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
  CONSTRAINT uq_sources_code_per_project UNIQUE (project_id, code)
);

-- 2. Indexes（含 partial index）
CREATE INDEX IF NOT EXISTS idx_sources_project ON crawler.sources(project_id);
CREATE INDEX IF NOT EXISTS idx_sources_enabled ON crawler.sources(project_id, is_enabled)
  WHERE is_enabled = TRUE;

-- 3. Trigger（moddatetime，批次建立）
-- 見下方「moddatetime 批次 trigger」

-- 4. RLS
ALTER TABLE crawler.sources ENABLE ROW LEVEL SECURITY;

-- 5. Policies（用 helper function）
CREATE POLICY "sources_select" ON crawler.sources
  FOR SELECT TO authenticated
  USING (crawler.has_project_access(project_id));
CREATE POLICY "sources_service_role" ON crawler.sources
  FOR ALL TO service_role USING (true) WITH CHECK (true);

-- 6. Grants
GRANT SELECT ON crawler.sources TO authenticated;
GRANT INSERT, UPDATE, DELETE ON crawler.sources TO authenticated;
GRANT ALL ON crawler.sources TO service_role;
```

## moddatetime 批次 Trigger

**來自 `migrations/003_crawler_schema.sql`**：用 DO block 批次建立，避免重複代碼。

```sql
DO $$
DECLARE tbl TEXT;
BEGIN
  FOREACH tbl IN ARRAY ARRAY[
    'sources', 'crawl_runs', 'source_pages', 'articles',
    'article_assets', 'tags', 'publish_targets', 'article_publications'
  ]
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

**注意**：state-machine 表（如 `crawl_queue`）不需要 `updated_at` trigger。

## RLS 批次啟用

```sql
DO $$
DECLARE tbl TEXT;
BEGIN
  FOREACH tbl IN ARRAY ARRAY[
    'sources', 'crawl_runs', 'crawl_queue', 'source_pages',
    'articles', 'article_assets', 'tags', 'article_tags',
    'publish_targets', 'article_publications'
  ]
  LOOP
    EXECUTE format('ALTER TABLE crawler.%I ENABLE ROW LEVEL SECURITY;', tbl);
  END LOOP;
END;
$$;
```

## Lease-Based RPC Function

**來自 `migrations/003_crawler_schema.sql`**：分散式任務佇列的 lease 函式。

```sql
CREATE OR REPLACE FUNCTION crawler.lease_next_crawl_job(
  p_worker_id TEXT,
  p_lease_duration INTERVAL DEFAULT INTERVAL '5 minutes'
)
RETURNS SETOF crawler.crawl_queue
LANGUAGE SQL
SECURITY DEFINER
SET search_path = crawler
AS $$
  UPDATE crawler.crawl_queue
  SET status = 'leased',
      lease_token = gen_random_uuid()::TEXT,
      leased_at = NOW(),
      lease_expires_at = NOW() + p_lease_duration,
      worker_id = p_worker_id
  WHERE id = (
    SELECT id FROM crawler.crawl_queue
    WHERE (status = 'pending' AND scheduled_at <= NOW())
       OR (status = 'leased' AND lease_expires_at < NOW())
    ORDER BY priority DESC, scheduled_at ASC
    LIMIT 1
    FOR UPDATE SKIP LOCKED    -- 關鍵！避免 worker 競爭鎖定
  )
  RETURNING *;
$$;

GRANT EXECUTE ON FUNCTION crawler.lease_next_crawl_job(TEXT, INTERVAL) TO authenticated;
```

**教學重點**：`FOR UPDATE SKIP LOCKED` 讓多個 worker 同時搶任務不會互相阻塞。

## PostgREST API Gateway Layer

**來自 `migrations/006_public_api.sql`**：業務邏輯在各自 schema，`public` function = API endpoint。

```sql
-- 命名慣例：api_{domain}_{action}
CREATE OR REPLACE FUNCTION public.api_shop_list_products(
  p_limit    INTEGER DEFAULT 20,
  p_offset   INTEGER DEFAULT 0,
  p_sort_by  TEXT DEFAULT 'created_at',
  p_sort_dir TEXT DEFAULT 'desc'
)
RETURNS TABLE (
  id TEXT, title TEXT, price NUMERIC, ...
)
LANGUAGE SQL
STABLE
SECURITY DEFINER          -- 用 function owner 權限（繞過 RLS）
SET search_path = public  -- 安全性
AS $$
  SELECT ... FROM shop.products p
  LEFT JOIN shop.product_images pi ON ...
  WHERE p.status = 'publish'
  ORDER BY ...
  LIMIT p_limit OFFSET p_offset;
$$;

GRANT EXECUTE ON FUNCTION public.api_shop_list_products(INTEGER, INTEGER, TEXT, TEXT)
  TO anon, authenticated;
```

**前端呼叫**：`supabase.rpc('api_shop_list_products', { p_limit: 20 })`

**設計原則**：
- PostgREST 只暴露 `public` schema → 業務邏輯隱藏
- `SECURITY DEFINER` → function 自行做存取控制，不依賴 RLS
- `RETURNS TABLE(...)` → 明確回傳型別，不用 `SETOF`
- 命名 `api_{domain}_{action}` → API Docs 按 domain 自然分組

## 冪等性

所有 DDL **必須**冪等：

```sql
CREATE TABLE IF NOT EXISTS ...
CREATE INDEX IF NOT EXISTS ...
CREATE OR REPLACE FUNCTION ...
DROP TRIGGER IF EXISTS ... ;  -- trigger 要先 DROP 再 CREATE
```

## Index 策略

| Tier | 說明 | 範例 |
|------|------|------|
| 1 | FK 欄位（必做） | `idx_articles_source ON crawler.articles(source_id)` |
| 2 | RLS helper 用的 composite（必做） | `idx_pm_project_user ON project_members(project_id, user_id, status)` |
| 3 | 列表查詢 composite | `idx_crawl_runs_source ON crawler.crawl_runs(source_id, created_at DESC)` |
| 4 | Partial index | `idx_sources_enabled ON crawler.sources(project_id, is_enabled) WHERE is_enabled = TRUE` |
| 5 | GIN for JSONB | `idx_chunks_metadata ON rag.chunks USING GIN(metadata)` |
| 6 | GIN for FTS | `idx_chunks_fts ON rag.chunks USING GIN(to_tsvector('simple', content))` |
| 7 | HNSW for vector | `idx_chunks_embedding ON rag.chunks USING hnsw(embedding vector_cosine_ops)` |
| 8 | Unique partial | `uq_queue_pending ON crawler.crawl_queue(source_id, url) WHERE status = 'pending'` |

## 新增表 Checklist

```
□ id TEXT PRIMARY KEY DEFAULT public.generate_ulid()
□ 表放在正確的 domain schema（不要全擠 public）
□ project_id + created_at + updated_at 必備
□ FK 型別一致（TEXT）
□ Status 欄位有 CHECK constraint
□ Tier 1: 所有 FK 有 index
□ Tier 4+: JSONB/FTS/Vector 有對應 index
□ updated_at trigger（moddatetime）
□ RLS enabled + policies + GRANT
□ service_role policy
□ 所有 DDL 冪等（IF NOT EXISTS / CREATE OR REPLACE）
□ Migration header 宣告執行順序
□ 年資料量 >10M？規劃 partition
□ 需要 API endpoint？加 public.api_* function
```

## 禁止事項

| 禁止 | 原因 |
|------|------|
| ❌ migration 不含 RLS | 表對 authenticated 完全開放 |
| ❌ migration 不含 index | FK 和 RLS 都慢 |
| ❌ 隱式 constraint | 難以後續修改 |
| ❌ 大量 data migration 不分批 | 鎖表風險 |
| ❌ 手寫 updated_at trigger | 用 moddatetime extension |
| ❌ 重複寫 RLS/trigger 代碼 | 用 DO block 批次建立 |
| ❌ 沒有執行順序宣告 | schema 依賴不明確 |

## 參考來源

- `docs/supabase/migrations/001_extensions.sql` — Schema + Extensions + ULID
- `docs/supabase/migrations/003_crawler_schema.sql` — Lease RPC + 批次 trigger/RLS
- `docs/supabase/migrations/004_rag_schema.sql` — Sync trigger + HNSW index
- `docs/supabase/migrations/006_public_api.sql` — PostgREST gateway layer
- `docs/supabase/crawler/HEAD-FIRST-crawler-db.md` — 完整修正範例
- `docs/supabase/e-Commerce/README.md` — 20 張表的 migration 範本

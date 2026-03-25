-- ============================================================
-- Supabase RAG Schema  v3.0
-- ============================================================
--
-- Design principles:
--   - pgvector for embedding storage and similarity search
--   - Collections as tenant scope (equivalent to project_id)
--   - Documents → Chunks two-level hierarchy
--   - TEXT + ULID primary keys (pk-convention compliant)
--   - RLS via helper functions only, no EXISTS/JOIN in policy
--   - GRANT + service_role policy on every table
--   - All DDL idempotent (IF NOT EXISTS)
--   - Compatible with existing crawler schema
--
-- Compliance:
--   pk-convention.md ✅  schema-design.md ✅  rls-patterns.md ✅
--   performance-linter.md ✅  anti-patterns.md ✅  migration-guidelines.md ✅
--   query-patterns.md ✅  scaling-guidelines.md ✅
--
-- Prerequisites:
--   - Supabase project with pgvector extension enabled
--   - Supabase Storage bucket "rag-documents" created
--
-- Execution order: tables → indexes → triggers → RLS → policies → grants
-- NOTE: extensions/ULID 已移至 001_extensions.sql
-- ============================================================


-- NOTE: schema, extensions, generate_ulid() 已移至 001_extensions.sql

-- ============================================================
-- 1. CORE FUNCTIONS
-- ============================================================

-- NOTE: updated_at 改用 moddatetime extension（見 STAGE 9 TRIGGERS）
-- 移除手寫 set_updated_at()，改用 moddatetime(updated_at)

-- auth bridge（教學簡化版）
-- production 應有完整 users table + get_current_user_id()
CREATE OR REPLACE FUNCTION rag.get_current_owner_id()
RETURNS TEXT
LANGUAGE SQL
STABLE
SECURITY DEFINER
SET search_path = rag
AS $$
  SELECT (SELECT auth.uid())::TEXT;
$$;


-- ============================================================
-- 2. EMBEDDING_MODELS（Embedding 模型註冊）
-- ============================================================
CREATE TABLE IF NOT EXISTS rag.embedding_models (
  id          TEXT PRIMARY KEY DEFAULT public.generate_ulid(),
  name        TEXT        NOT NULL UNIQUE,
  provider    TEXT        NOT NULL DEFAULT 'openai',
  dimensions  INTEGER     NOT NULL,
  max_tokens  INTEGER,
  description TEXT,
  config      JSONB       NOT NULL DEFAULT '{}'::JSONB,
  is_active   BOOLEAN     NOT NULL DEFAULT TRUE,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  -- 強制 1536 維度
  CONSTRAINT ck_embedding_models_dimensions CHECK (dimensions = 1536)
);

INSERT INTO rag.embedding_models (name, provider, dimensions, max_tokens, description)
VALUES
  ('text-embedding-3-small', 'openai', 1536, 8191, 'OpenAI 小型 embedding 模型，性價比最高'),
  ('text-embedding-3-large-matryoshka', 'openai', 1536, 8191, 'OpenAI 大型模型 Matryoshka 降維到 1536'),
  ('text-embedding-ada-002', 'openai', 1536, 8191, 'OpenAI 舊版 embedding 模型（相容用途）')
ON CONFLICT (name) DO NOTHING;


-- ============================================================
-- 3. COLLECTIONS（知識庫集合 — RAG 的 tenant scope 單位）
-- ============================================================
CREATE TABLE IF NOT EXISTS rag.collections (
  id                TEXT PRIMARY KEY DEFAULT public.generate_ulid(),
  name              TEXT        NOT NULL,
  code              TEXT        NOT NULL UNIQUE,
  description       TEXT,

  embedding_model_id TEXT       NOT NULL REFERENCES rag.embedding_models(id),

  chunking_strategy JSONB       NOT NULL DEFAULT '{
    "method": "recursive",
    "chunk_size": 512,
    "chunk_overlap": 50,
    "separators": ["\n\n", "\n", "。", ".", " "]
  }'::JSONB,

  metadata          JSONB       NOT NULL DEFAULT '{}'::JSONB,
  is_active         BOOLEAN     NOT NULL DEFAULT TRUE,

  -- owner（教學簡化版，不直接 FK auth.users）
  owner_id          TEXT,

  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- ============================================================
-- 4. DOCUMENTS（原始文件）
-- ============================================================
CREATE TABLE IF NOT EXISTS rag.documents (
  id              TEXT PRIMARY KEY DEFAULT public.generate_ulid(),
  collection_id   TEXT        NOT NULL REFERENCES rag.collections(id) ON DELETE CASCADE,

  title           TEXT        NOT NULL,
  source_type     TEXT        NOT NULL DEFAULT 'text',
  source_url      TEXT,

  -- crawler 整合（軟連結）
  source_ref_type TEXT,
  source_ref_id   TEXT,

  -- 儲存
  storage_bucket  TEXT,
  storage_path    TEXT,
  content_text    TEXT,

  -- 高頻查詢欄位（抽出為 column，不放 JSONB）
  mime_type       TEXT,
  lang            TEXT,
  author          TEXT,
  published_at    TIMESTAMPTZ,

  -- Ingestion Pipeline 狀態機
  process_status  TEXT        NOT NULL DEFAULT 'uploaded',
  process_error   TEXT,
  chunk_count     INTEGER     NOT NULL DEFAULT 0,
  token_count     INTEGER,
  content_hash    TEXT,

  chunking_override JSONB,

  -- RLS 快取（trigger 自動填入）
  owner_id        TEXT,
  -- 審計欄位
  created_by      TEXT,

  metadata        JSONB       NOT NULL DEFAULT '{}'::JSONB,

  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  CONSTRAINT ck_documents_source_type
    CHECK (source_type IN ('text', 'pdf', 'html', 'markdown', 'url', 'crawler')),
  CONSTRAINT ck_documents_process_status
    CHECK (process_status IN (
      'uploaded', 'parsed', 'chunked', 'embedded', 'ready', 'failed', 'stale'
    ))
);


-- ============================================================
-- 5. CHUNKS（文件切片 + Embedding 向量）
-- ============================================================
CREATE TABLE IF NOT EXISTS rag.chunks (
  id              TEXT PRIMARY KEY DEFAULT public.generate_ulid(),
  document_id     TEXT        NOT NULL REFERENCES rag.documents(id) ON DELETE CASCADE,

  -- 反正規化（trigger 強制一致性）
  collection_id   TEXT        NOT NULL REFERENCES rag.collections(id) ON DELETE CASCADE,

  content         TEXT        NOT NULL,
  chunk_index     INTEGER     NOT NULL,
  token_count     INTEGER,

  -- embedding 向量（固定 1536 維）
  embedding       vector(1536),

  start_char      INTEGER,
  end_char        INTEGER,
  page_number     INTEGER,

  chunking_method TEXT,
  overlap_prev    BOOLEAN     NOT NULL DEFAULT FALSE,
  overlap_next    BOOLEAN     NOT NULL DEFAULT FALSE,

  -- RLS 快取（trigger 自動填入）
  owner_id        TEXT,

  metadata        JSONB       NOT NULL DEFAULT '{}'::JSONB,

  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  CONSTRAINT uq_chunks_document_index UNIQUE (document_id, chunk_index)
);


-- ============================================================
-- 6. TAGS（語意標籤）
-- ============================================================
CREATE TABLE IF NOT EXISTS rag.tags (
  id          TEXT PRIMARY KEY DEFAULT public.generate_ulid(),
  taxonomy    TEXT        NOT NULL DEFAULT 'topic',
  name        TEXT        NOT NULL,
  slug        TEXT,
  description TEXT,
  parent_id   TEXT REFERENCES rag.tags(id) ON DELETE SET NULL,
  metadata    JSONB       NOT NULL DEFAULT '{}'::JSONB,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  CONSTRAINT uq_tags_taxonomy_name UNIQUE (taxonomy, name)
);

CREATE TABLE IF NOT EXISTS rag.chunk_tags (
  chunk_id    TEXT NOT NULL REFERENCES rag.chunks(id) ON DELETE CASCADE,
  tag_id      TEXT NOT NULL REFERENCES rag.tags(id) ON DELETE CASCADE,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (chunk_id, tag_id)
);


-- ============================================================
-- 7. QUERY_LOGS（查詢紀錄與評估追蹤）
-- ============================================================
CREATE TABLE IF NOT EXISTS rag.query_logs (
  id              TEXT PRIMARY KEY DEFAULT public.generate_ulid(),
  collection_id   TEXT        NOT NULL REFERENCES rag.collections(id) ON DELETE CASCADE,

  query_text      TEXT        NOT NULL,
  query_embedding vector(1536),

  top_k           INTEGER     NOT NULL DEFAULT 5,
  similarity_threshold FLOAT8,

  generated_answer TEXT,
  llm_model       TEXT,
  prompt_tokens   INTEGER,
  completion_tokens INTEGER,

  -- Ragas 評估指標
  eval_faithfulness    FLOAT8,
  eval_answer_relevance FLOAT8,
  eval_context_recall  FLOAT8,
  eval_context_precision FLOAT8,

  user_rating     SMALLINT,
  user_feedback   TEXT,

  -- Agentic RAG 追蹤
  session_id      TEXT,
  parent_query_id TEXT REFERENCES rag.query_logs(id),
  iteration       INTEGER     NOT NULL DEFAULT 1,
  agent_action    TEXT,

  created_by      TEXT,

  metadata        JSONB       NOT NULL DEFAULT '{}'::JSONB,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- ============================================================
-- 7a. QUERY_LOG_RESULTS（檢索結果明細 — 正規化）
-- ============================================================
CREATE TABLE IF NOT EXISTS rag.query_log_results (
  id          TEXT PRIMARY KEY DEFAULT public.generate_ulid(),
  query_id    TEXT        NOT NULL REFERENCES rag.query_logs(id) ON DELETE CASCADE,
  chunk_id    TEXT        NOT NULL REFERENCES rag.chunks(id) ON DELETE CASCADE,
  rank        INTEGER     NOT NULL,
  score       FLOAT8      NOT NULL,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);


-- ============================================================
-- 8. INDEXES
-- ============================================================
-- Tier 1: FK indexes（必備）
CREATE INDEX IF NOT EXISTS idx_collections_code ON rag.collections(code);
CREATE INDEX IF NOT EXISTS idx_collections_embedding_model ON rag.collections(embedding_model_id);
CREATE INDEX IF NOT EXISTS idx_collections_owner ON rag.collections(owner_id) WHERE owner_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_documents_collection ON rag.documents(collection_id);
CREATE INDEX IF NOT EXISTS idx_documents_status ON rag.documents(process_status);
CREATE INDEX IF NOT EXISTS idx_documents_hash ON rag.documents(content_hash) WHERE content_hash IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_documents_source_ref ON rag.documents(source_ref_type, source_ref_id) WHERE source_ref_type IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_documents_owner ON rag.documents(owner_id) WHERE owner_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_documents_lang ON rag.documents(lang) WHERE lang IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_chunks_document ON rag.chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_collection ON rag.chunks(collection_id);
CREATE INDEX IF NOT EXISTS idx_chunks_owner ON rag.chunks(owner_id) WHERE owner_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_chunks_metadata ON rag.chunks USING GIN(metadata);

CREATE INDEX IF NOT EXISTS idx_tags_taxonomy ON rag.tags(taxonomy, name);
CREATE INDEX IF NOT EXISTS idx_tags_parent ON rag.tags(parent_id) WHERE parent_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_chunk_tags_tag ON rag.chunk_tags(tag_id);

CREATE INDEX IF NOT EXISTS idx_query_logs_collection ON rag.query_logs(collection_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_query_logs_session ON rag.query_logs(session_id) WHERE session_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_query_logs_parent ON rag.query_logs(parent_query_id) WHERE parent_query_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_query_log_results_query ON rag.query_log_results(query_id);
CREATE INDEX IF NOT EXISTS idx_query_log_results_chunk ON rag.query_log_results(chunk_id);
CREATE INDEX IF NOT EXISTS idx_query_log_results_chunk_score ON rag.query_log_results(chunk_id, score DESC);

-- Vector index（HNSW — 高精度語意搜尋）
CREATE INDEX IF NOT EXISTS idx_chunks_embedding_hnsw ON rag.chunks
  USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);

-- FTS GIN index（hybrid search 必備）
CREATE INDEX IF NOT EXISTS idx_chunks_fts ON rag.chunks
  USING GIN (to_tsvector('simple', content));


-- ============================================================
-- 9. TRIGGERS
-- ============================================================

-- updated_at triggers（moddatetime — Supabase 原生方式）
DO $$
DECLARE
  tbl TEXT;
BEGIN
  FOREACH tbl IN ARRAY ARRAY[
    'embedding_models', 'collections', 'documents', 'chunks',
    'tags', 'query_logs'
  ]
  LOOP
    EXECUTE format('
      DROP TRIGGER IF EXISTS trg_%1$s_updated_at ON rag.%1$s;
      CREATE TRIGGER trg_%1$s_updated_at
        BEFORE UPDATE ON rag.%1$s
        FOR EACH ROW EXECUTE FUNCTION moddatetime(updated_at);
    ', tbl);
  END LOOP;
END;
$$;

-- 自動從 collection 傳播 owner_id 到 documents
CREATE OR REPLACE FUNCTION rag.sync_document_owner()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = rag
AS $$
BEGIN
  SELECT owner_id INTO NEW.owner_id
  FROM rag.collections
  WHERE id = NEW.collection_id;
  RETURN NEW;
END;
$$;

CREATE TRIGGER trg_documents_sync_owner
  BEFORE INSERT OR UPDATE OF collection_id ON rag.documents
  FOR EACH ROW EXECUTE FUNCTION rag.sync_document_owner();

-- 強制 chunks.collection_id 與 document 一致 + 傳播 owner_id
CREATE OR REPLACE FUNCTION rag.sync_chunk_from_document()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = rag
AS $$
DECLARE
  v_collection_id TEXT;
  v_owner_id TEXT;
BEGIN
  SELECT d.collection_id, d.owner_id
  INTO v_collection_id, v_owner_id
  FROM rag.documents d
  WHERE d.id = NEW.document_id;

  NEW.collection_id := v_collection_id;
  NEW.owner_id := v_owner_id;
  RETURN NEW;
END;
$$;

CREATE TRIGGER trg_chunks_sync_collection
  BEFORE INSERT OR UPDATE OF document_id ON rag.chunks
  FOR EACH ROW EXECUTE FUNCTION rag.sync_chunk_from_document();


-- ============================================================
-- 10. RLS HELPER FUNCTIONS
-- ============================================================
-- rls-patterns: helper MUST be STABLE, SECURITY DEFINER, SET search_path
-- scaling-guidelines: auth.uid() MUST be wrapped as (SELECT auth.uid())

CREATE OR REPLACE FUNCTION rag.is_collection_owner(p_collection_id TEXT)
RETURNS BOOLEAN
LANGUAGE SQL
STABLE
SECURITY DEFINER
SET search_path = rag
AS $$
  SELECT EXISTS (
    SELECT 1 FROM rag.collections
    WHERE id = p_collection_id AND owner_id = (SELECT auth.uid())::TEXT
  );
$$;

CREATE OR REPLACE FUNCTION rag.is_collection_active(p_collection_id TEXT)
RETURNS BOOLEAN
LANGUAGE SQL
STABLE
SECURITY DEFINER
SET search_path = rag
AS $$
  SELECT COALESCE(
    (SELECT is_active FROM rag.collections WHERE id = p_collection_id),
    FALSE
  );
$$;

CREATE OR REPLACE FUNCTION rag.can_read_collection(p_collection_id TEXT)
RETURNS BOOLEAN
LANGUAGE SQL
STABLE
SECURITY DEFINER
SET search_path = rag
AS $$
  SELECT COALESCE(
    (SELECT is_active OR owner_id = (SELECT auth.uid())::TEXT
     FROM rag.collections WHERE id = p_collection_id),
    FALSE
  );
$$;


-- ============================================================
-- 11. SEARCH FUNCTIONS
-- ============================================================

CREATE OR REPLACE FUNCTION rag.match_chunks(
  query_embedding vector(1536),
  p_collection_id TEXT,
  p_top_k INTEGER DEFAULT 5,
  p_similarity_threshold FLOAT8 DEFAULT 0.7
)
RETURNS TABLE (
  id TEXT,
  document_id TEXT,
  content TEXT,
  chunk_index INTEGER,
  metadata JSONB,
  similarity FLOAT8
)
LANGUAGE SQL
SECURITY DEFINER
SET search_path = rag
STABLE
AS $$
  SELECT
    c.id, c.document_id, c.content, c.chunk_index, c.metadata,
    1 - (c.embedding <=> query_embedding) AS similarity
  FROM rag.chunks c
  WHERE c.collection_id = p_collection_id
    AND c.embedding IS NOT NULL
    AND 1 - (c.embedding <=> query_embedding) >= p_similarity_threshold
  ORDER BY c.embedding <=> query_embedding
  LIMIT p_top_k;
$$;

CREATE OR REPLACE FUNCTION rag.match_chunks_with_document(
  query_embedding vector(1536),
  p_collection_id TEXT,
  p_top_k INTEGER DEFAULT 5,
  p_similarity_threshold FLOAT8 DEFAULT 0.7
)
RETURNS TABLE (
  chunk_id TEXT,
  document_id TEXT,
  document_title TEXT,
  source_url TEXT,
  content TEXT,
  chunk_index INTEGER,
  page_number INTEGER,
  chunk_metadata JSONB,
  similarity FLOAT8
)
LANGUAGE SQL
SECURITY DEFINER
SET search_path = rag
STABLE
AS $$
  SELECT
    c.id AS chunk_id, c.document_id,
    d.title AS document_title, d.source_url,
    c.content, c.chunk_index, c.page_number,
    c.metadata AS chunk_metadata,
    1 - (c.embedding <=> query_embedding) AS similarity
  FROM rag.chunks c
  JOIN rag.documents d ON d.id = c.document_id
  WHERE c.collection_id = p_collection_id
    AND c.embedding IS NOT NULL
    AND 1 - (c.embedding <=> query_embedding) >= p_similarity_threshold
  ORDER BY c.embedding <=> query_embedding
  LIMIT p_top_k;
$$;

CREATE OR REPLACE FUNCTION rag.hybrid_search(
  query_text TEXT,
  query_embedding vector(1536),
  p_collection_id TEXT,
  p_top_k INTEGER DEFAULT 5,
  p_semantic_weight FLOAT8 DEFAULT 0.7,
  p_similarity_threshold FLOAT8 DEFAULT 0.5
)
RETURNS TABLE (
  chunk_id TEXT,
  document_id TEXT,
  content TEXT,
  metadata JSONB,
  semantic_score FLOAT8,
  fulltext_score FLOAT8,
  combined_score FLOAT8
)
LANGUAGE SQL
SECURITY DEFINER
SET search_path = rag
STABLE
AS $$
  WITH semantic AS (
    SELECT c.id, c.document_id, c.content, c.metadata,
      1 - (c.embedding <=> query_embedding) AS score
    FROM rag.chunks c
    WHERE c.collection_id = p_collection_id AND c.embedding IS NOT NULL
    ORDER BY c.embedding <=> query_embedding
    LIMIT p_top_k * 3
  ),
  fulltext AS (
    SELECT c.id,
      ts_rank(to_tsvector('simple', c.content), plainto_tsquery('simple', query_text)) AS score
    FROM rag.chunks c
    WHERE c.collection_id = p_collection_id
      AND to_tsvector('simple', c.content) @@ plainto_tsquery('simple', query_text)
  ),
  combined AS (
    SELECT s.id, s.document_id, s.content, s.metadata,
      s.score AS semantic_score,
      COALESCE(f.score, 0) AS fulltext_score,
      (p_semantic_weight * s.score + (1 - p_semantic_weight) * COALESCE(f.score, 0)) AS combined_score
    FROM semantic s LEFT JOIN fulltext f ON f.id = s.id
  )
  SELECT id AS chunk_id, document_id, content, metadata,
    semantic_score, fulltext_score, combined_score
  FROM combined
  WHERE semantic_score >= p_similarity_threshold
  ORDER BY combined_score DESC
  LIMIT p_top_k;
$$;


-- ============================================================
-- 12. ANALYTICS FUNCTIONS
-- ============================================================

CREATE OR REPLACE FUNCTION rag.collection_stats(p_collection_id TEXT)
RETURNS TABLE (
  total_documents BIGINT,
  total_chunks BIGINT,
  chunks_with_embedding BIGINT,
  avg_chunk_tokens FLOAT8,
  total_queries BIGINT,
  avg_faithfulness FLOAT8
)
LANGUAGE SQL
SECURITY DEFINER
SET search_path = rag
STABLE
AS $$
  SELECT
    (SELECT count(*) FROM rag.documents WHERE collection_id = p_collection_id),
    (SELECT count(*) FROM rag.chunks WHERE collection_id = p_collection_id),
    (SELECT count(*) FROM rag.chunks WHERE collection_id = p_collection_id AND embedding IS NOT NULL),
    (SELECT avg(token_count) FROM rag.chunks WHERE collection_id = p_collection_id),
    (SELECT count(*) FROM rag.query_logs WHERE collection_id = p_collection_id),
    (SELECT avg(eval_faithfulness) FROM rag.query_logs WHERE collection_id = p_collection_id AND eval_faithfulness IS NOT NULL);
$$;

CREATE OR REPLACE FUNCTION rag.top_hit_chunks(
  p_collection_id TEXT,
  p_limit INTEGER DEFAULT 20
)
RETURNS TABLE (
  chunk_id TEXT,
  document_id TEXT,
  content TEXT,
  hit_count BIGINT,
  avg_score FLOAT8,
  avg_rank FLOAT8
)
LANGUAGE SQL
SECURITY DEFINER
SET search_path = rag
STABLE
AS $$
  SELECT r.chunk_id, c.document_id, c.content,
    count(*) AS hit_count, avg(r.score) AS avg_score, avg(r.rank) AS avg_rank
  FROM rag.query_log_results r
  JOIN rag.chunks c ON c.id = r.chunk_id
  WHERE c.collection_id = p_collection_id
  GROUP BY r.chunk_id, c.document_id, c.content
  ORDER BY hit_count DESC
  LIMIT p_limit;
$$;


-- ============================================================
-- 13. ROW LEVEL SECURITY
-- ============================================================

ALTER TABLE rag.embedding_models ENABLE ROW LEVEL SECURITY;
ALTER TABLE rag.collections ENABLE ROW LEVEL SECURITY;
ALTER TABLE rag.documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE rag.chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE rag.tags ENABLE ROW LEVEL SECURITY;
ALTER TABLE rag.chunk_tags ENABLE ROW LEVEL SECURITY;
ALTER TABLE rag.query_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE rag.query_log_results ENABLE ROW LEVEL SECURITY;


-- ============================================================
-- 14. POLICIES
-- ============================================================
-- rls-patterns: helper function only, no inline JOIN/EXISTS
-- migration-guidelines: must include service_role policy

-- embedding_models
CREATE POLICY "embedding_models_read" ON rag.embedding_models
  FOR SELECT TO authenticated, anon USING (TRUE);
CREATE POLICY "embedding_models_service" ON rag.embedding_models
  FOR ALL TO service_role USING (TRUE) WITH CHECK (TRUE);

-- collections
CREATE POLICY "collections_read" ON rag.collections
  FOR SELECT TO authenticated, anon
  USING (is_active = TRUE OR owner_id = rag.get_current_owner_id());
CREATE POLICY "collections_insert" ON rag.collections
  FOR INSERT TO authenticated
  WITH CHECK (owner_id = rag.get_current_owner_id());
CREATE POLICY "collections_update" ON rag.collections
  FOR UPDATE TO authenticated
  USING (owner_id = rag.get_current_owner_id());
CREATE POLICY "collections_delete" ON rag.collections
  FOR DELETE TO authenticated
  USING (owner_id = rag.get_current_owner_id());
CREATE POLICY "collections_service" ON rag.collections
  FOR ALL TO service_role USING (TRUE) WITH CHECK (TRUE);

-- documents
CREATE POLICY "documents_read" ON rag.documents
  FOR SELECT TO authenticated, anon
  USING (owner_id = rag.get_current_owner_id() OR rag.is_collection_active(collection_id));
CREATE POLICY "documents_write" ON rag.documents
  FOR INSERT TO authenticated
  WITH CHECK (rag.is_collection_owner(collection_id));
CREATE POLICY "documents_update" ON rag.documents
  FOR UPDATE TO authenticated
  USING (owner_id = rag.get_current_owner_id());
CREATE POLICY "documents_delete" ON rag.documents
  FOR DELETE TO authenticated
  USING (owner_id = rag.get_current_owner_id());
CREATE POLICY "documents_service" ON rag.documents
  FOR ALL TO service_role USING (TRUE) WITH CHECK (TRUE);

-- chunks
CREATE POLICY "chunks_read" ON rag.chunks
  FOR SELECT TO authenticated, anon
  USING (owner_id = rag.get_current_owner_id() OR rag.is_collection_active(collection_id));
CREATE POLICY "chunks_write" ON rag.chunks
  FOR INSERT TO authenticated
  WITH CHECK (rag.is_collection_owner(collection_id));
CREATE POLICY "chunks_update" ON rag.chunks
  FOR UPDATE TO authenticated
  USING (owner_id = rag.get_current_owner_id());
CREATE POLICY "chunks_delete" ON rag.chunks
  FOR DELETE TO authenticated
  USING (owner_id = rag.get_current_owner_id());
CREATE POLICY "chunks_service" ON rag.chunks
  FOR ALL TO service_role USING (TRUE) WITH CHECK (TRUE);

-- ============================================================
-- PATTERN: Column-Level Security（欄位級存取控制）
-- ============================================================
-- 教學重點：
--   - PostgreSQL 沒有原生 column-level RLS（只有 row-level）
--   - 解法：用 VIEW 遮蔽敏感欄位，前端只查 VIEW
--   - embedding vector（1536 維 float）佔 ~6KB/row，不該讓一般查詢回傳
--   - 只有 search function（SECURITY DEFINER）才需要讀 embedding
--   - View 用 security_invoker = true：RLS 用呼叫者身份檢查
--
-- 效果：
--   SELECT * FROM rag.chunks          → 包含 embedding（後端/search function 用）
--   SELECT * FROM rag.chunks_safe     → 不含 embedding（前端 API 用）

CREATE OR REPLACE VIEW rag.chunks_safe
  WITH (security_invoker = true)
  AS
  SELECT
    id, document_id, collection_id,
    content, chunk_index, token_count,
    -- embedding 欄位被排除！
    start_char, end_char, page_number,
    chunking_method, overlap_prev, overlap_next,
    owner_id, metadata, created_at, updated_at
  FROM rag.chunks;

-- View 不需要 ENABLE RLS（它繼承底層 table 的 RLS）
-- 但需要 GRANT
GRANT SELECT ON rag.chunks_safe TO authenticated, anon;
GRANT ALL ON rag.chunks_safe TO service_role;

-- tags
CREATE POLICY "tags_read" ON rag.tags
  FOR SELECT TO authenticated, anon USING (TRUE);
CREATE POLICY "tags_service" ON rag.tags
  FOR ALL TO service_role USING (TRUE) WITH CHECK (TRUE);

CREATE POLICY "chunk_tags_read" ON rag.chunk_tags
  FOR SELECT TO authenticated, anon USING (TRUE);
CREATE POLICY "chunk_tags_service" ON rag.chunk_tags
  FOR ALL TO service_role USING (TRUE) WITH CHECK (TRUE);

-- query_logs
CREATE POLICY "query_logs_read" ON rag.query_logs
  FOR SELECT TO authenticated
  USING (rag.can_read_collection(collection_id));
CREATE POLICY "query_logs_insert" ON rag.query_logs
  FOR INSERT TO authenticated
  WITH CHECK (rag.can_read_collection(collection_id));
CREATE POLICY "query_logs_service" ON rag.query_logs
  FOR ALL TO service_role USING (TRUE) WITH CHECK (TRUE);

-- query_log_results
CREATE POLICY "query_log_results_read" ON rag.query_log_results
  FOR SELECT TO authenticated
  USING (
    rag.can_read_collection(
      (SELECT collection_id FROM rag.query_logs WHERE id = query_log_results.query_id)
    )
  );
CREATE POLICY "query_log_results_insert" ON rag.query_log_results
  FOR INSERT TO authenticated
  WITH CHECK (
    rag.can_read_collection(
      (SELECT collection_id FROM rag.query_logs WHERE id = query_log_results.query_id)
    )
  );
CREATE POLICY "query_log_results_service" ON rag.query_log_results
  FOR ALL TO service_role USING (TRUE) WITH CHECK (TRUE);


-- ============================================================
-- 15. GRANTS
-- ============================================================
-- migration-guidelines: 每張表必須有 GRANT

GRANT SELECT ON rag.embedding_models TO authenticated, anon;
GRANT ALL ON rag.embedding_models TO service_role;

GRANT SELECT ON rag.collections TO authenticated, anon;
GRANT INSERT, UPDATE, DELETE ON rag.collections TO authenticated;
GRANT ALL ON rag.collections TO service_role;

GRANT SELECT ON rag.documents TO authenticated, anon;
GRANT INSERT, UPDATE, DELETE ON rag.documents TO authenticated;
GRANT ALL ON rag.documents TO service_role;

GRANT SELECT ON rag.chunks TO authenticated, anon;
GRANT INSERT, UPDATE, DELETE ON rag.chunks TO authenticated;
GRANT ALL ON rag.chunks TO service_role;

GRANT SELECT ON rag.tags TO authenticated, anon;
GRANT INSERT, UPDATE, DELETE ON rag.tags TO authenticated;
GRANT ALL ON rag.tags TO service_role;

GRANT SELECT ON rag.chunk_tags TO authenticated, anon;
GRANT INSERT, UPDATE, DELETE ON rag.chunk_tags TO authenticated;
GRANT ALL ON rag.chunk_tags TO service_role;

GRANT SELECT ON rag.query_logs TO authenticated;
GRANT INSERT, UPDATE ON rag.query_logs TO authenticated;
GRANT ALL ON rag.query_logs TO service_role;

GRANT SELECT ON rag.query_log_results TO authenticated;
GRANT INSERT ON rag.query_log_results TO authenticated;
GRANT ALL ON rag.query_log_results TO service_role;

-- Helper functions
GRANT EXECUTE ON FUNCTION rag.get_current_owner_id() TO authenticated;
GRANT EXECUTE ON FUNCTION rag.is_collection_owner(TEXT) TO authenticated;
GRANT EXECUTE ON FUNCTION rag.is_collection_active(TEXT) TO authenticated, anon;
GRANT EXECUTE ON FUNCTION rag.can_read_collection(TEXT) TO authenticated, anon;
GRANT EXECUTE ON FUNCTION rag.match_chunks(vector, TEXT, INTEGER, FLOAT8) TO authenticated, anon;
GRANT EXECUTE ON FUNCTION rag.match_chunks_with_document(vector, TEXT, INTEGER, FLOAT8) TO authenticated, anon;
GRANT EXECUTE ON FUNCTION rag.hybrid_search(TEXT, vector, TEXT, INTEGER, FLOAT8, FLOAT8) TO authenticated, anon;
GRANT EXECUTE ON FUNCTION rag.collection_stats(TEXT) TO authenticated;
GRANT EXECUTE ON FUNCTION rag.top_hit_chunks(TEXT, INTEGER) TO authenticated;


-- ============================================================
-- 16. DEVELOPMENT HELPER（部署前移除）
-- ============================================================
-- CREATE POLICY "dev_all" ON rag.collections FOR ALL USING (TRUE);
-- CREATE POLICY "dev_all" ON rag.documents FOR ALL USING (TRUE);
-- CREATE POLICY "dev_all" ON rag.chunks FOR ALL USING (TRUE);
-- CREATE POLICY "dev_all" ON rag.query_logs FOR ALL USING (TRUE);
-- CREATE POLICY "dev_all" ON rag.query_log_results FOR ALL USING (TRUE);

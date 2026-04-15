-- =============================================================
-- migrations/001_initial_schema.sql
-- Bazi RAG Executable Schema — PostgreSQL + pgvector
-- =============================================================

BEGIN;

-- -------------------------------------------------------------
-- 0. Extensions
-- -------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS vector;

-- -------------------------------------------------------------
-- 1. Schema
-- -------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS bazi;

-- -------------------------------------------------------------
-- 2. Utility functions
-- -------------------------------------------------------------

CREATE OR REPLACE FUNCTION bazi.set_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION bazi.null_if_blank(p_text TEXT)
RETURNS TEXT
LANGUAGE SQL
IMMUTABLE
AS $$
  SELECT NULLIF(TRIM(p_text), '');
$$;

-- -------------------------------------------------------------
-- 3. Core tables
-- -------------------------------------------------------------

-- 3.1 knowledge_atoms
-- 每一筆代表一個可獨立引用的命理知識原子
CREATE TABLE IF NOT EXISTS bazi.knowledge_atoms (
  id                      BIGSERIAL PRIMARY KEY,
  atom_code               TEXT        NOT NULL UNIQUE,

  source_book             TEXT        NOT NULL,
  source_priority         SMALLINT    NOT NULL
                          CHECK (source_priority >= 1 AND source_priority <= 9),
  chapter                 TEXT,
  section                 TEXT,
  title                   TEXT,

  original_text           TEXT        NOT NULL,
  modern_interpretation   TEXT,
  embedding_text          TEXT        NOT NULL,

  normalized_tags         JSONB       NOT NULL DEFAULT '[]'::JSONB,
  logic_type              JSONB       NOT NULL DEFAULT '[]'::JSONB,
  conditions              JSONB       NOT NULL DEFAULT '[]'::JSONB,

  -- 高頻過濾欄位：避免每次都硬查 JSONB
  day_master_tags         TEXT[]      NOT NULL DEFAULT '{}',
  month_branch_tags       TEXT[]      NOT NULL DEFAULT '{}',
  ten_god_tags            TEXT[]      NOT NULL DEFAULT '{}',
  pattern_tags            TEXT[]      NOT NULL DEFAULT '{}',
  seasonal_tags           TEXT[]      NOT NULL DEFAULT '{}',

  citation_path           JSONB       NOT NULL DEFAULT '{}'::JSONB,
  notes                   TEXT,

  status                  TEXT        NOT NULL DEFAULT 'active'
                          CHECK (status IN ('active', 'draft', 'deprecated', 'archived')),

  embedding               vector(1536), -- 維度依 embedding model 而定

  created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  CONSTRAINT knowledge_atoms_normalized_tags_is_array
    CHECK (JSONB_TYPEOF(normalized_tags) = 'array'),
  CONSTRAINT knowledge_atoms_logic_type_is_array
    CHECK (JSONB_TYPEOF(logic_type) = 'array'),
  CONSTRAINT knowledge_atoms_conditions_is_array
    CHECK (JSONB_TYPEOF(conditions) = 'array'),
  CONSTRAINT knowledge_atoms_citation_path_is_object
    CHECK (JSONB_TYPEOF(citation_path) = 'object')
);

COMMENT ON TABLE bazi.knowledge_atoms IS
'八字 RAG 核心知識原子表，每筆盡量只承載一個邏輯命題。';

COMMENT ON COLUMN bazi.knowledge_atoms.embedding IS
'pgvector embedding，維度 1536；更換 embedding model 需同步 migration。';

CREATE TRIGGER trg_knowledge_atoms_updated_at
  BEFORE UPDATE ON bazi.knowledge_atoms
  FOR EACH ROW EXECUTE FUNCTION bazi.set_updated_at();


-- 3.2 knowledge_relations
CREATE TABLE IF NOT EXISTS bazi.knowledge_relations (
  id                      BIGSERIAL PRIMARY KEY,
  from_atom_id            BIGINT      NOT NULL REFERENCES bazi.knowledge_atoms(id) ON DELETE CASCADE,
  relation_type           TEXT        NOT NULL,
  -- supports | contradicts | extends | cites | applies_to
  to_atom_id              BIGINT      NOT NULL REFERENCES bazi.knowledge_atoms(id) ON DELETE CASCADE,
  weight                  NUMERIC(6,4) NOT NULL DEFAULT 1.0,
  created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  CONSTRAINT knowledge_relations_no_self_loop
    CHECK (from_atom_id <> to_atom_id)
);

COMMENT ON TABLE bazi.knowledge_relations IS
'知識原子間的關係表，模擬輕量圖譜，支援 supports / contradicts / extends / cites / applies_to。';


-- 3.3 rule_definitions
CREATE TABLE IF NOT EXISTS bazi.rule_definitions (
  id                      BIGSERIAL PRIMARY KEY,
  rule_code               TEXT        NOT NULL,
  version                 INTEGER     NOT NULL DEFAULT 1,
  rule_type               TEXT        NOT NULL,
  -- strength | pattern | seasonal_adjustment | conflict
  description             TEXT        NOT NULL,

  input_requirements      JSONB       NOT NULL DEFAULT '{}'::JSONB,
  conditions              JSONB       NOT NULL DEFAULT '[]'::JSONB,
  outputs                 JSONB       NOT NULL DEFAULT '{}'::JSONB,

  priority                INTEGER     NOT NULL DEFAULT 100,
  status                  TEXT        NOT NULL DEFAULT 'active'
                          CHECK (status IN ('active', 'draft', 'deprecated', 'archived')),

  created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  CONSTRAINT rule_definitions_unique_code_version
    UNIQUE (rule_code, version),
  CONSTRAINT rule_definitions_input_requirements_is_object
    CHECK (JSONB_TYPEOF(input_requirements) = 'object'),
  CONSTRAINT rule_definitions_conditions_is_array
    CHECK (JSONB_TYPEOF(conditions) = 'array'),
  CONSTRAINT rule_definitions_outputs_is_object
    CHECK (JSONB_TYPEOF(outputs) = 'object')
);

COMMENT ON TABLE bazi.rule_definitions IS
'規則引擎定義表，供 deterministic / symbolic 層使用，支援版本化。';

CREATE TRIGGER trg_rule_definitions_updated_at
  BEFORE UPDATE ON bazi.rule_definitions
  FOR EACH ROW EXECUTE FUNCTION bazi.set_updated_at();


-- 3.4 bazi_charts
CREATE TABLE IF NOT EXISTS bazi.bazi_charts (
  id                      BIGSERIAL PRIMARY KEY,
  chart_code              TEXT        NOT NULL UNIQUE,

  input_payload           JSONB       NOT NULL,
  chart_payload           JSONB       NOT NULL,
  feature_payload         JSONB       NOT NULL, -- Rule Engine 輸出

  created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  CONSTRAINT bazi_charts_input_is_object
    CHECK (JSONB_TYPEOF(input_payload) = 'object'),
  CONSTRAINT bazi_charts_chart_is_object
    CHECK (JSONB_TYPEOF(chart_payload) = 'object'),
  CONSTRAINT bazi_charts_feature_is_object
    CHECK (JSONB_TYPEOF(feature_payload) = 'object')
);

COMMENT ON TABLE bazi.bazi_charts IS
'排盤記錄與規則特徵，供除錯、追蹤與評估使用。';


-- 3.5 retrieval_logs
CREATE TABLE IF NOT EXISTS bazi.retrieval_logs (
  id                      BIGSERIAL PRIMARY KEY,
  retrieval_code          TEXT        NOT NULL UNIQUE,
  chart_id                BIGINT      REFERENCES bazi.bazi_charts(id) ON DELETE SET NULL,

  retrieval_input         JSONB       NOT NULL,
  symbolic_candidates     JSONB       NOT NULL DEFAULT '[]'::JSONB,
  metadata_candidates     JSONB       NOT NULL DEFAULT '[]'::JSONB,
  vector_candidates       JSONB       NOT NULL DEFAULT '[]'::JSONB,
  fused_results           JSONB       NOT NULL DEFAULT '[]'::JSONB,

  created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE bazi.retrieval_logs IS
'每次查詢的多路檢索過程記錄，用於除錯與評估。';


-- 3.6 generation_logs
CREATE TABLE IF NOT EXISTS bazi.generation_logs (
  id                      BIGSERIAL PRIMARY KEY,
  generation_code         TEXT        NOT NULL UNIQUE,
  chart_id                BIGINT      REFERENCES bazi.bazi_charts(id) ON DELETE SET NULL,
  retrieval_id            BIGINT      REFERENCES bazi.retrieval_logs(id) ON DELETE SET NULL,

  prompt_snapshot         JSONB       NOT NULL, -- 含 system / context / format blocks
  output_text             TEXT        NOT NULL,
  output_structured       JSONB,               -- 解析後的結構化輸出

  groundedness_score      NUMERIC(4,3),        -- 可追溯比例 0.0 - 1.0
  hallucination_flags     JSONB        NOT NULL DEFAULT '[]'::JSONB,

  model_id                TEXT,
  latency_ms              INTEGER,

  created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE bazi.generation_logs IS
'生成過程記錄，含 prompt snapshot 與 grounded 評分。';


-- 3.7 evaluation_cases
CREATE TABLE IF NOT EXISTS bazi.evaluation_cases (
  id                      BIGSERIAL PRIMARY KEY,
  case_code               TEXT        NOT NULL UNIQUE,

  input_payload           JSONB       NOT NULL,
  expected_chart          JSONB,
  expected_features       JSONB,
  expected_atom_codes     JSONB,               -- ["atom_code_1", "atom_code_2"]
  expected_source_books   JSONB,               -- ["子平真詮", "滴天髓"]
  output_check_rules      JSONB        NOT NULL DEFAULT '[]'::JSONB,

  notes                   TEXT,
  status                  TEXT        NOT NULL DEFAULT 'active'
                          CHECK (status IN ('active', 'draft', 'deprecated')),

  created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE bazi.evaluation_cases IS
'黃金評估案例集，用於回歸測試與指標計算。';


-- -------------------------------------------------------------
-- 4. Indexes
-- -------------------------------------------------------------

-- knowledge_atoms — B-tree
CREATE INDEX IF NOT EXISTS idx_ka_source_priority
  ON bazi.knowledge_atoms (source_priority, source_book);

CREATE INDEX IF NOT EXISTS idx_ka_status
  ON bazi.knowledge_atoms (status);

-- knowledge_atoms — GIN (array)
CREATE INDEX IF NOT EXISTS idx_ka_day_master_tags
  ON bazi.knowledge_atoms USING GIN (day_master_tags);

CREATE INDEX IF NOT EXISTS idx_ka_month_branch_tags
  ON bazi.knowledge_atoms USING GIN (month_branch_tags);

CREATE INDEX IF NOT EXISTS idx_ka_ten_god_tags
  ON bazi.knowledge_atoms USING GIN (ten_god_tags);

CREATE INDEX IF NOT EXISTS idx_ka_pattern_tags
  ON bazi.knowledge_atoms USING GIN (pattern_tags);

CREATE INDEX IF NOT EXISTS idx_ka_seasonal_tags
  ON bazi.knowledge_atoms USING GIN (seasonal_tags);

-- knowledge_atoms — GIN (JSONB)
CREATE INDEX IF NOT EXISTS idx_ka_normalized_tags_gin
  ON bazi.knowledge_atoms USING GIN (normalized_tags);

CREATE INDEX IF NOT EXISTS idx_ka_logic_type_gin
  ON bazi.knowledge_atoms USING GIN (logic_type);

CREATE INDEX IF NOT EXISTS idx_ka_conditions_gin
  ON bazi.knowledge_atoms USING GIN (conditions);

-- knowledge_atoms — pgvector HNSW (cosine)
-- 適合 PoC 階段；資料量大後可評估 IVFFlat
CREATE INDEX IF NOT EXISTS idx_ka_embedding_hnsw_cosine
  ON bazi.knowledge_atoms
  USING HNSW (embedding vector_cosine_ops);

-- knowledge_relations
CREATE INDEX IF NOT EXISTS idx_kr_from_atom
  ON bazi.knowledge_relations (from_atom_id);

CREATE INDEX IF NOT EXISTS idx_kr_to_atom
  ON bazi.knowledge_relations (to_atom_id);

CREATE INDEX IF NOT EXISTS idx_kr_relation_type
  ON bazi.knowledge_relations (relation_type);

-- rule_definitions
CREATE INDEX IF NOT EXISTS idx_rd_rule_type_status
  ON bazi.rule_definitions (rule_type, status);

CREATE INDEX IF NOT EXISTS idx_rd_priority
  ON bazi.rule_definitions (priority);

-- retrieval_logs
CREATE INDEX IF NOT EXISTS idx_rl_chart_id
  ON bazi.retrieval_logs (chart_id);

-- generation_logs
CREATE INDEX IF NOT EXISTS idx_gl_chart_id
  ON bazi.generation_logs (chart_id);

CREATE INDEX IF NOT EXISTS idx_gl_retrieval_id
  ON bazi.generation_logs (retrieval_id);


-- -------------------------------------------------------------
-- 5. Core retrieval function
-- filter → vector → SQL rerank
-- -------------------------------------------------------------

CREATE OR REPLACE FUNCTION bazi.match_knowledge_atoms (
  query_embedding       vector(1536),
  p_day_master_tags     TEXT[]    DEFAULT '{}',
  p_month_branch_tags   TEXT[]    DEFAULT '{}',
  p_pattern_tags        TEXT[]    DEFAULT '{}',
  p_seasonal_tags       TEXT[]    DEFAULT '{}',
  p_top_k               INTEGER   DEFAULT 12,
  p_candidate_limit     INTEGER   DEFAULT 50
)
RETURNS TABLE (
  atom_id               BIGINT,
  atom_code             TEXT,
  source_book           TEXT,
  source_priority       SMALLINT,
  title                 TEXT,
  original_text         TEXT,
  modern_interpretation TEXT,
  normalized_tags       JSONB,
  logic_type            JSONB,
  vector_score          DOUBLE PRECISION,
  source_priority_score DOUBLE PRECISION,
  symbolic_match_score  DOUBLE PRECISION,
  metadata_overlap_score DOUBLE PRECISION,
  final_score           DOUBLE PRECISION
)
LANGUAGE SQL
STABLE
AS $$
  WITH candidate_pool AS (
    SELECT *
    FROM bazi.knowledge_atoms
    WHERE status = 'active'
      AND (
        (ARRAY_LENGTH(p_day_master_tags, 1) > 0   AND day_master_tags   @> p_day_master_tags)
        OR (ARRAY_LENGTH(p_month_branch_tags, 1) > 0 AND month_branch_tags && p_month_branch_tags)
        OR (ARRAY_LENGTH(p_pattern_tags, 1) > 0   AND pattern_tags      && p_pattern_tags)
        OR (ARRAY_LENGTH(p_seasonal_tags, 1) > 0  AND seasonal_tags     && p_seasonal_tags)
        -- fallback: 無過濾條件時全文召回
        OR (
          ARRAY_LENGTH(p_day_master_tags, 1) = 0
          AND ARRAY_LENGTH(p_month_branch_tags, 1) = 0
          AND ARRAY_LENGTH(p_pattern_tags, 1) = 0
          AND ARRAY_LENGTH(p_seasonal_tags, 1) = 0
        )
      )
  ),
  vector_ranked AS (
    SELECT
      id,
      atom_code,
      source_book,
      source_priority,
      title,
      original_text,
      modern_interpretation,
      normalized_tags,
      logic_type,
      1.0 - (embedding <=> query_embedding) AS vector_score
    FROM candidate_pool
    WHERE embedding IS NOT NULL
    ORDER BY embedding <=> query_embedding
    LIMIT p_candidate_limit
  ),
  reranked AS (
    SELECT
      *,
      CASE source_priority
        WHEN 1 THEN 1.00
        WHEN 2 THEN 0.85
        WHEN 3 THEN 0.70
        ELSE        0.50
      END AS source_priority_score,

      CASE
        WHEN logic_type ? 'pattern_definition'
          OR logic_type ? 'strength_assessment'  THEN 1.00
        WHEN logic_type ? 'seasonal_adjustment'
          OR logic_type ? 'ten_god_relation'      THEN 0.85
        ELSE                                           0.70
      END AS symbolic_match_score,

      CASE
        WHEN ARRAY_LENGTH(p_day_master_tags, 1) > 0
          AND day_master_tags @> p_day_master_tags   THEN 1.00
        WHEN ARRAY_LENGTH(p_month_branch_tags, 1) > 0
          AND month_branch_tags && p_month_branch_tags THEN 0.90
        ELSE                                               0.70
      END AS metadata_overlap_score
    FROM vector_ranked
  )
  SELECT
    id                    AS atom_id,
    atom_code,
    source_book,
    source_priority,
    title,
    original_text,
    modern_interpretation,
    normalized_tags,
    logic_type,
    vector_score,
    source_priority_score,
    symbolic_match_score,
    metadata_overlap_score,
    (
      vector_score           * 0.45
      + source_priority_score  * 0.20
      + symbolic_match_score   * 0.20
      + metadata_overlap_score * 0.15
    ) AS final_score
  FROM reranked
  ORDER BY final_score DESC
  LIMIT p_top_k;
$$;

COMMENT ON FUNCTION bazi.match_knowledge_atoms IS
'三段式 RAG 檢索：metadata filter → pgvector cosine → SQL rerank。
 呼叫方式：SELECT * FROM bazi.match_knowledge_atoms(
   query_embedding := $1::vector,
   p_day_master_tags := ARRAY[''甲''],
   p_month_branch_tags := ARRAY[''申''],
   p_pattern_tags := ARRAY[''正官格'']
 );';


-- -------------------------------------------------------------
-- 6. Seed: rule_definitions (Level 1 骨架規則)
-- -------------------------------------------------------------

INSERT INTO bazi.rule_definitions
  (rule_code, version, rule_type, description, input_requirements, conditions, outputs, priority)
VALUES
(
  'STRENGTH_DAYMASTER_MONTH_SUPPORT',
  1,
  'strength',
  '月令生扶日主：月支五行與日主同行或生扶，計入身強因子',
  '{"required_fields": ["day_master", "month_commander", "hidden_stems"]}'::JSONB,
  '[
    {"field": "month_hidden_stems", "operator": "contains_same_element_as", "value": "day_master_element"}
  ]'::JSONB,
  '{"add_strength_factor": "month_support", "strength_score_delta": 2}'::JSONB,
  10
),
(
  'PATTERN_ZHENGGUANGE_BASIC',
  1,
  'pattern',
  '正官格基本成立條件：月令藏干透出正官，無明顯破格',
  '{"required_fields": ["day_master", "month_commander", "four_pillars", "hidden_stems"]}'::JSONB,
  '[
    {"field": "month_hidden_ten_god", "operator": "contains", "value": "正官"},
    {"field": "risk_flags", "operator": "not_contains", "value": "傷官見官"}
  ]'::JSONB,
  '{"candidate_pattern": "正官格", "confidence": "high"}'::JSONB,
  20
),
(
  'SEASONAL_ADJ_JIA_WINTER',
  1,
  'seasonal_adjustment',
  '甲木冬生需火調候：甲木日主生於冬季，以火為調候喜神',
  '{"required_fields": ["day_master", "season"]}'::JSONB,
  '[
    {"field": "day_master", "operator": "eq", "value": "甲"},
    {"field": "season", "operator": "in", "value": ["winter", "late_autumn"]}
  ]'::JSONB,
  '{"adjustment_needed": ["火"], "reason": "寒木需火暖局"}'::JSONB,
  30
)
ON CONFLICT (rule_code, version) DO NOTHING;


-- -------------------------------------------------------------
-- 7. Seed: knowledge_atoms (子平真詮首批範例)
-- -------------------------------------------------------------

INSERT INTO bazi.knowledge_atoms
  (atom_code, source_book, source_priority, chapter, section, title,
   original_text, modern_interpretation, embedding_text,
   normalized_tags, logic_type, conditions,
   day_master_tags, month_branch_tags, pattern_tags, seasonal_tags,
   citation_path)
VALUES
(
  'ziping-jia-001',
  '子平真詮', 1,
  '論甲木', '甲木總論',
  '甲木冬生調候',
  '甲木參天，脫胎要火。',
  '甲木如高大之木，生於寒冬時節，必須以火暖局，否則寒木難以發榮。',
  '甲木 冬季 寒濕 調候 火 日主特性 需火',
  '["甲木", "調候", "火", "冬季", "日主特性"]'::JSONB,
  '["day_master_nature", "seasonal_adjustment"]'::JSONB,
  '[{"field":"day_master","operator":"eq","value":"甲"},{"field":"season","operator":"in","value":["winter","late_autumn"]}]'::JSONB,
  ARRAY['甲'],
  ARRAY['子', '亥'],
  ARRAY[]::TEXT[],
  ARRAY['winter', 'late_autumn'],
  '{"book":"子平真詮","chapter":"論甲木","line_range":"12-18"}'::JSONB
),
(
  'ziping-zhengguange-001',
  '子平真詮', 1,
  '論正官', '正官格總論',
  '正官格成立核心條件',
  '官以剋身，透出為格，無傷則貴。',
  '正官能剋日主，若透出天干成格，且沒有傷官剋制，則為正官格，具有貴氣。',
  '正官格 成立條件 月令透干 無傷 貴氣',
  '["正官格", "格局定義", "成立條件", "傷官"]'::JSONB,
  '["pattern_definition"]'::JSONB,
  '[{"field":"month_hidden_ten_god","operator":"contains","value":"正官"},{"field":"risk_flags","operator":"not_contains","value":"傷官見官"}]'::JSONB,
  ARRAY[]::TEXT[],
  ARRAY[]::TEXT[],
  ARRAY['正官格'],
  ARRAY[]::TEXT[],
  '{"book":"子平真詮","chapter":"論正官","line_range":"1-8"}'::JSONB
),
(
  'ziping-shenruo-001',
  '子平真詮', 1,
  '論用神', '用神與強弱',
  '身強宜洩宜剋',
  '身強者，宜洩宜剋，財官食傷皆宜。',
  '日主身強，適合以食傷洩秀、財星耗身、官殺剋制，這些都是適當的用神方向。',
  '身強 用神 洩 剋 財官食傷 強弱判定',
  '["身強", "用神", "食傷", "財星", "官殺"]'::JSONB,
  '["strength_assessment", "general_principle"]'::JSONB,
  '[{"field":"day_master_strength","operator":"in","value":["strong","very_strong"]}]'::JSONB,
  ARRAY[]::TEXT[],
  ARRAY[]::TEXT[],
  ARRAY[]::TEXT[],
  ARRAY[]::TEXT[],
  '{"book":"子平真詮","chapter":"論用神","line_range":"22-28"}'::JSONB
)
ON CONFLICT (atom_code) DO NOTHING;


-- -------------------------------------------------------------
-- 8. Seed: evaluation_cases (Phase 0 黃金案例)
-- -------------------------------------------------------------

INSERT INTO bazi.evaluation_cases
  (case_code, input_payload, expected_chart, expected_features,
   expected_atom_codes, expected_source_books, notes)
VALUES
(
  'eval-001-jiamu-shen',
  '{"birth_datetime":"1990-08-15T14:30:00","timezone":"Asia/Taipei","gender":"male","use_true_solar_time":true}'::JSONB,
  '{"day_master":"甲","month_commander":"申","season":"autumn"}'::JSONB,
  '{"candidate_patterns":["正官格"],"strength":"moderately_strong"}'::JSONB,
  '["ziping-zhengguange-001", "ziping-shenruo-001"]'::JSONB,
  '["子平真詮"]'::JSONB,
  '申月甲木正官格標準案例'
),
(
  'eval-002-jiamu-zi',
  '{"birth_datetime":"1985-12-15T10:00:00","timezone":"Asia/Taipei","gender":"female","use_true_solar_time":true}'::JSONB,
  '{"day_master":"甲","month_commander":"子","season":"winter"}'::JSONB,
  '{"seasonal_adjustment_needed":["火"]}'::JSONB,
  '["ziping-jia-001"]'::JSONB,
  '["子平真詮"]'::JSONB,
  '子月甲木冬生調候案例'
)
ON CONFLICT (case_code) DO NOTHING;


COMMIT;

-- =============================================================
-- Usage example:
--
-- SELECT * FROM bazi.match_knowledge_atoms(
--   query_embedding := '[...]'::vector,
--   p_day_master_tags := ARRAY['甲'],
--   p_month_branch_tags := ARRAY['申'],
--   p_pattern_tags := ARRAY['正官格']
-- );
-- =============================================================

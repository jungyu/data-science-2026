-- =========================================================
-- TCM Diagnostic RAG System Schema
-- version: v0.1
-- target: PostgreSQL 15+ / Supabase
-- =========================================================

begin;

-- ---------------------------------------------------------
-- 0. Extensions
-- ---------------------------------------------------------

create extension if not exists vector;
create extension if not exists pg_trgm;
create extension if not exists unaccent;

-- ---------------------------------------------------------
-- 1. Utility functions
-- ---------------------------------------------------------

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

-- ---------------------------------------------------------
-- 2. Domain-like constraints via CHECK
-- ---------------------------------------------------------
-- Note:
-- MVP 先用 text + check constraint
-- 若型別穩定，再考慮升級成 enum type

-- ---------------------------------------------------------
-- 3. Source documents
-- ---------------------------------------------------------

create table if not exists public.source_documents (
  id text primary key,
  source_type text not null
    check (source_type in (
      'html_page',
      'markdown_doc',
      'classic_text',
      'case_record',
      'manual_entry',
      'json_import'
    )),
  title text not null,
  canonical_title text,
  author_name text,
  publisher text,
  edition text,
  language_code text not null default 'zh-Hant',
  authority_level integer not null default 50
    check (authority_level >= 0 and authority_level <= 100),
  citation_tier text not null default 'secondary'
    check (citation_tier in ('primary', 'secondary', 'reference', 'case')),
  source_url text,
  source_ref text,
  license_note text,
  raw_content text,
  clean_markdown text,
  metadata jsonb not null default '{}'::jsonb,
  ingestion_status text not null default 'pending'
    check (ingestion_status in (
      'pending',
      'cleaned',
      'parsed',
      'embedded',
      'failed'
    )),
  ingestion_error text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_source_documents_source_type
  on public.source_documents (source_type);

create index if not exists idx_source_documents_authority_level
  on public.source_documents (authority_level desc);

create index if not exists idx_source_documents_metadata_gin
  on public.source_documents using gin (metadata);

create trigger trg_source_documents_updated_at
before update on public.source_documents
for each row
execute function public.set_updated_at();

-- ---------------------------------------------------------
-- 4. Knowledge atoms
-- ---------------------------------------------------------

create table if not exists public.knowledge_atoms (
  id text primary key,

  source_document_id text references public.source_documents(id) on delete set null,

  atom_type text not null
    check (atom_type in (
      'symptom',
      'sign',
      'tongue_feature',
      'pulse_feature',
      'pattern',
      'pathomechanism',
      'treatment_principle',
      'formula',
      'herb',
      'citation',
      'case'
    )),

  title text not null,
  canonical_name text not null,
  aliases jsonb not null default '[]'::jsonb,

  domain text,
  subdomain text,
  category text,
  subcategory text,

  body_markdown text not null,
  summary_text text,
  embedding_text text,

  -- pgvector dimension 1536 for text-embedding-3-small
  -- adjust via migration if model changes
  embedding vector(1536),

  -- Full text search
  search_vector tsvector,

  quality_score numeric(5,2) not null default 0.00
    check (quality_score >= 0 and quality_score <= 100),
  completeness_score numeric(5,2) not null default 0.00
    check (completeness_score >= 0 and completeness_score <= 100),

  authority_level integer not null default 50
    check (authority_level >= 0 and authority_level <= 100),

  is_active boolean not null default true,

  metadata jsonb not null default '{}'::jsonb,

  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_knowledge_atoms_atom_type
  on public.knowledge_atoms (atom_type);

create index if not exists idx_knowledge_atoms_canonical_name
  on public.knowledge_atoms (canonical_name);

create index if not exists idx_knowledge_atoms_domain
  on public.knowledge_atoms (domain);

create index if not exists idx_knowledge_atoms_category
  on public.knowledge_atoms (category);

create index if not exists idx_knowledge_atoms_source_document_id
  on public.knowledge_atoms (source_document_id);

create index if not exists idx_knowledge_atoms_is_active
  on public.knowledge_atoms (is_active);

create index if not exists idx_knowledge_atoms_authority_level
  on public.knowledge_atoms (authority_level desc);

create index if not exists idx_knowledge_atoms_metadata_gin
  on public.knowledge_atoms using gin (metadata);

create index if not exists idx_knowledge_atoms_aliases_gin
  on public.knowledge_atoms using gin (aliases);

create index if not exists idx_knowledge_atoms_search_vector
  on public.knowledge_atoms using gin (search_vector);

-- ivfflat vector index: tune `lists` value after bulk insert
create index if not exists idx_knowledge_atoms_embedding_ivfflat
  on public.knowledge_atoms
  using ivfflat (embedding vector_cosine_ops)
  with (lists = 100);

create trigger trg_knowledge_atoms_updated_at
before update on public.knowledge_atoms
for each row
execute function public.set_updated_at();

-- ---------------------------------------------------------
-- 5. search_vector auto-update trigger
-- ---------------------------------------------------------

create or replace function public.knowledge_atoms_update_search_vector()
returns trigger
language plpgsql
as $$
begin
  new.search_vector :=
    to_tsvector(
      'simple',
      unaccent(
        coalesce(new.title, '') || ' ' ||
        coalesce(new.canonical_name, '') || ' ' ||
        coalesce(new.summary_text, '') || ' ' ||
        coalesce(new.body_markdown, '')
      )
    );
  return new;
end;
$$;

drop trigger if exists trg_knowledge_atoms_search_vector on public.knowledge_atoms;

create trigger trg_knowledge_atoms_search_vector
before insert or update of title, canonical_name, summary_text, body_markdown
on public.knowledge_atoms
for each row
execute function public.knowledge_atoms_update_search_vector();

-- ---------------------------------------------------------
-- 6. Atom relations
-- ---------------------------------------------------------

create table if not exists public.atom_relations (
  id text primary key,

  from_atom_id text not null references public.knowledge_atoms(id) on delete cascade,
  relation_type text not null
    check (relation_type in (
      'suggests',
      'strengthens',
      'strongly_strengthens',
      'explained_by',
      'belongs_to',
      'treated_by',
      'implemented_by',
      'contains',
      'supports',
      'instantiates',
      'conflicts_with',
      'related_to',
      'alias_of'
    )),
  to_atom_id text not null references public.knowledge_atoms(id) on delete cascade,

  weight numeric(6,4) not null default 0.5000
    check (weight >= 0 and weight <= 1),

  evidence_source_document_id text references public.source_documents(id) on delete set null,
  evidence_note text,

  metadata jsonb not null default '{}'::jsonb,

  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),

  constraint chk_atom_relations_not_self_loop
    check (from_atom_id <> to_atom_id)
);

create index if not exists idx_atom_relations_from_atom_id
  on public.atom_relations (from_atom_id);

create index if not exists idx_atom_relations_to_atom_id
  on public.atom_relations (to_atom_id);

create index if not exists idx_atom_relations_relation_type
  on public.atom_relations (relation_type);

create index if not exists idx_atom_relations_from_relation
  on public.atom_relations (from_atom_id, relation_type);

create index if not exists idx_atom_relations_to_relation
  on public.atom_relations (to_atom_id, relation_type);

create index if not exists idx_atom_relations_metadata_gin
  on public.atom_relations using gin (metadata);

create unique index if not exists uq_atom_relations_edge
  on public.atom_relations (from_atom_id, relation_type, to_atom_id);

create trigger trg_atom_relations_updated_at
before update on public.atom_relations
for each row
execute function public.set_updated_at();

-- ---------------------------------------------------------
-- 7. Diagnostic rules
-- ---------------------------------------------------------

create table if not exists public.diagnostic_rules (
  id text primary key,

  rule_code text not null unique,
  rule_name text not null,

  rule_scope text not null default 'pattern_ranking'
    check (rule_scope in (
      'pattern_ranking',
      'differential_diagnosis',
      'contraindication',
      'question_suggestion'
    )),

  status text not null default 'draft'
    check (status in (
      'draft',
      'active',
      'disabled',
      'archived'
    )),

  priority integer not null default 100,

  target_atom_id text references public.knowledge_atoms(id) on delete set null,

  -- JSONB conditions example:
  -- {
  --   "all_of": [{"type":"symptom","value":"盜汗"}],
  --   "any_of": [{"type":"tongue_feature","value":"舌紅少苔"}],
  --   "none_of": [{"type":"sign","value":"畏寒"}],
  --   "score_delta": 0.35
  -- }
  conditions jsonb not null default '{}'::jsonb,
  actions jsonb not null default '{}'::jsonb,

  explanation text,
  source_document_id text references public.source_documents(id) on delete set null,

  metadata jsonb not null default '{}'::jsonb,

  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_diagnostic_rules_rule_scope
  on public.diagnostic_rules (rule_scope);

create index if not exists idx_diagnostic_rules_status
  on public.diagnostic_rules (status);

create index if not exists idx_diagnostic_rules_priority
  on public.diagnostic_rules (priority asc);

create index if not exists idx_diagnostic_rules_target_atom_id
  on public.diagnostic_rules (target_atom_id);

create index if not exists idx_diagnostic_rules_conditions_gin
  on public.diagnostic_rules using gin (conditions);

create index if not exists idx_diagnostic_rules_actions_gin
  on public.diagnostic_rules using gin (actions);

create index if not exists idx_diagnostic_rules_metadata_gin
  on public.diagnostic_rules using gin (metadata);

create trigger trg_diagnostic_rules_updated_at
before update on public.diagnostic_rules
for each row
execute function public.set_updated_at();

-- ---------------------------------------------------------
-- 8. Query logs
-- ---------------------------------------------------------

create table if not exists public.query_logs (
  id text primary key,

  session_id text,
  user_query text not null,

  normalized_query jsonb not null default '{}'::jsonb,
  extracted_features jsonb not null default '{}'::jsonb,

  top_candidate_patterns jsonb not null default '[]'::jsonb,

  answer_contract jsonb not null default '{}'::jsonb,

  latency_ms integer,
  model_name text,

  created_at timestamptz not null default now()
);

create index if not exists idx_query_logs_session_id
  on public.query_logs (session_id);

create index if not exists idx_query_logs_created_at
  on public.query_logs (created_at desc);

create index if not exists idx_query_logs_extracted_features_gin
  on public.query_logs using gin (extracted_features);

-- ---------------------------------------------------------
-- 9. Retrieval logs
-- ---------------------------------------------------------

create table if not exists public.retrieval_logs (
  id text primary key,

  query_log_id text not null references public.query_logs(id) on delete cascade,

  stage text not null
    check (stage in (
      'fts',
      'vector',
      'relation',
      'rule',
      'rerank',
      'assembly'
    )),

  candidate_atom_id text references public.knowledge_atoms(id) on delete set null,

  raw_score numeric(12,6),
  rerank_score numeric(12,6),

  matched_features jsonb not null default '[]'::jsonb,
  conflict_features jsonb not null default '[]'::jsonb,

  notes text,
  created_at timestamptz not null default now()
);

create index if not exists idx_retrieval_logs_query_log_id
  on public.retrieval_logs (query_log_id);

create index if not exists idx_retrieval_logs_stage
  on public.retrieval_logs (stage);

create index if not exists idx_retrieval_logs_candidate_atom_id
  on public.retrieval_logs (candidate_atom_id);

-- ---------------------------------------------------------
-- 10. Helpful views (MVP)
-- ---------------------------------------------------------

create or replace view public.v_pattern_atoms as
select
  ka.id,
  ka.title,
  ka.canonical_name,
  ka.domain,
  ka.category,
  ka.subcategory,
  ka.summary_text,
  ka.authority_level,
  ka.quality_score,
  ka.completeness_score,
  ka.metadata
from public.knowledge_atoms ka
where ka.atom_type = 'pattern'
  and ka.is_active = true;

create or replace view public.v_symptom_to_pattern_edges as
select
  r.id,
  r.from_atom_id as symptom_atom_id,
  s.canonical_name as symptom_name,
  r.to_atom_id as pattern_atom_id,
  p.canonical_name as pattern_name,
  r.relation_type,
  r.weight,
  r.evidence_note
from public.atom_relations r
join public.knowledge_atoms s on s.id = r.from_atom_id
join public.knowledge_atoms p on p.id = r.to_atom_id
where s.atom_type = 'symptom'
  and p.atom_type = 'pattern'
  and r.relation_type in ('suggests', 'strengthens', 'strongly_strengthens');

-- ---------------------------------------------------------
-- 11. Comments
-- ---------------------------------------------------------

comment on table public.source_documents is
'原始來源文件表：書籍章節、HTML 頁面、醫案資料等。';

comment on table public.knowledge_atoms is
'中醫診斷知識原子表：symptom, pattern, tongue_feature, pulse_feature 等。';

comment on table public.atom_relations is
'知識原子之間的關聯邊，用於 graph-like expansion 與可解釋推理。';

comment on table public.diagnostic_rules is
'辨證規則表，MVP 採 JSONB 條件與動作格式。';

comment on table public.query_logs is
'查詢層日誌，用於評估 normalization 與回答品質。';

comment on table public.retrieval_logs is
'召回與重排序日誌，用於分析 RAG 行為。';

commit;

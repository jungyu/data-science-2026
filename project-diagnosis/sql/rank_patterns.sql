-- =========================================================
-- TCM Diagnostic RAG — Pattern Ranking Query
-- version: v0.1
-- target: PostgreSQL 15+ / Supabase
--
-- Input (bound parameters):
--   :feature_atom_ids  text[]   symptom/sign/tongue/pulse atom ids extracted from query
--   :query_embedding   vector   optional; pass NULL to skip vector route
--   :query_fts         text     optional; pass NULL or '' to skip FTS route
--   :top_k             int      how many pattern candidates to return (e.g. 5)
--
-- Output columns:
--   pattern_id, pattern_name, pattern_family,
--   support_score, conflict_penalty, vector_score, fts_score,
--   final_score, supporting_feature_ids, conflicting_feature_ids
--
-- Score formula (see spec §7.2):
--   final_score =
--     0.55 * support_score
--   - 0.20 * conflict_penalty
--   + 0.15 * vector_score
--   + 0.10 * fts_score
--
-- Notes:
--   - support_score aggregates relation weights from input features → pattern
--     with relation-type multipliers
--   - conflict_penalty aggregates conflicts_with weights
--   - vector_score / fts_score are normalized to [0,1] within the result set
-- =========================================================

with
-- ---------------------------------------------------------
-- 1. Relation-type multipliers
-- ---------------------------------------------------------
relation_weights as (
  select * from (values
    ('suggests'::text,              0.60),
    ('strengthens',                 0.80),
    ('strongly_strengthens',        1.00),
    ('explained_by',                0.50),
    ('belongs_to',                  0.40),
    ('supports',                    0.70),
    ('instantiates',                0.60),
    ('related_to',                  0.30)
  ) as t(relation_type, multiplier)
),

-- ---------------------------------------------------------
-- 2. Support score: Σ (weight × relation_multiplier) for positive edges
--    from any input feature atom → pattern atom
-- ---------------------------------------------------------
support_raw as (
  select
    r.to_atom_id as pattern_id,
    sum(r.weight * coalesce(rw.multiplier, 0.50)) as support_score,
    array_agg(distinct r.from_atom_id) as supporting_feature_ids
  from public.atom_relations r
  left join relation_weights rw on rw.relation_type = r.relation_type
  where r.from_atom_id = any(:feature_atom_ids)
    and r.relation_type in (
      'suggests',
      'strengthens',
      'strongly_strengthens',
      'explained_by',
      'supports',
      'related_to'
    )
  group by r.to_atom_id
),

-- ---------------------------------------------------------
-- 3. Conflict penalty: Σ weight for conflicts_with edges
-- ---------------------------------------------------------
conflict_raw as (
  select
    r.to_atom_id as pattern_id,
    sum(r.weight) as conflict_penalty,
    array_agg(distinct r.from_atom_id) as conflicting_feature_ids
  from public.atom_relations r
  where r.from_atom_id = any(:feature_atom_ids)
    and r.relation_type = 'conflicts_with'
  group by r.to_atom_id
),

-- ---------------------------------------------------------
-- 4. Candidate pattern set: union of support & conflict rows,
--    plus (optionally) vector / FTS hits on pattern atoms
-- ---------------------------------------------------------
candidates as (
  select pattern_id from support_raw
  union
  select pattern_id from conflict_raw
),

pattern_atoms as (
  select
    ka.id as pattern_id,
    ka.canonical_name as pattern_name,
    ka.metadata ->> 'pattern_family' as pattern_family,
    ka.summary_text,
    ka.authority_level,
    ka.embedding,
    ka.search_vector
  from public.knowledge_atoms ka
  where ka.atom_type = 'pattern'
    and ka.is_active = true
    and ka.id in (select pattern_id from candidates)
),

-- ---------------------------------------------------------
-- 5. Vector & FTS scores (normalized within result set)
-- ---------------------------------------------------------
vector_scored as (
  select
    pa.pattern_id,
    case
      when :query_embedding is null or pa.embedding is null then 0.0
      else 1.0 - (pa.embedding <=> :query_embedding)   -- cosine similarity
    end as vector_similarity
  from pattern_atoms pa
),

fts_scored as (
  select
    pa.pattern_id,
    case
      when :query_fts is null or btrim(:query_fts) = '' then 0.0
      else ts_rank_cd(pa.search_vector, plainto_tsquery('simple', :query_fts))
    end as fts_rank
  from pattern_atoms pa
),

vector_normed as (
  select
    pattern_id,
    case
      when max(vector_similarity) over () = min(vector_similarity) over () then 0.0
      else (vector_similarity - min(vector_similarity) over ())
         / nullif(max(vector_similarity) over () - min(vector_similarity) over (), 0)
    end as vector_score
  from vector_scored
),

fts_normed as (
  select
    pattern_id,
    case
      when max(fts_rank) over () = min(fts_rank) over () then 0.0
      else (fts_rank - min(fts_rank) over ())
         / nullif(max(fts_rank) over () - min(fts_rank) over (), 0)
    end as fts_score
  from fts_scored
),

-- ---------------------------------------------------------
-- 6. Final combined ranking
-- ---------------------------------------------------------
combined as (
  select
    pa.pattern_id,
    pa.pattern_name,
    pa.pattern_family,
    pa.summary_text,
    pa.authority_level,
    coalesce(sr.support_score, 0) as support_score,
    coalesce(cr.conflict_penalty, 0) as conflict_penalty,
    coalesce(vn.vector_score, 0) as vector_score,
    coalesce(fn.fts_score, 0) as fts_score,
    coalesce(sr.supporting_feature_ids, array[]::text[]) as supporting_feature_ids,
    coalesce(cr.conflicting_feature_ids, array[]::text[]) as conflicting_feature_ids
  from pattern_atoms pa
  left join support_raw sr on sr.pattern_id = pa.pattern_id
  left join conflict_raw cr on cr.pattern_id = pa.pattern_id
  left join vector_normed vn on vn.pattern_id = pa.pattern_id
  left join fts_normed fn on fn.pattern_id = pa.pattern_id
)

select
  pattern_id,
  pattern_name,
  pattern_family,
  summary_text,
  authority_level,
  round(support_score::numeric, 4) as support_score,
  round(conflict_penalty::numeric, 4) as conflict_penalty,
  round(vector_score::numeric, 4) as vector_score,
  round(fts_score::numeric, 4) as fts_score,
  round(
    (
      0.55 * support_score
    - 0.20 * conflict_penalty
    + 0.15 * vector_score
    + 0.10 * fts_score
    )::numeric,
    4
  ) as final_score,
  supporting_feature_ids,
  conflicting_feature_ids
from combined
order by final_score desc nulls last, support_score desc, authority_level desc
limit :top_k;

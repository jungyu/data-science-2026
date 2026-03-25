# Crawler Schema vs Supabase Guidelines — Strict Audit

Audit of `03_playwright_crawler_schema.sql` against `agent-init/skills/supabase/*.md`.

> Verdict: **29 violations** across 7 categories. 10 Critical, 12 High, 7 Medium.

---

## Category 1: Primary Key Convention (pk-convention.md)

**Guideline**: `id TEXT PRIMARY KEY DEFAULT generate_ulid()`, no SERIAL/BIGINT.

### V-01 [CRITICAL] All 10 tables use `bigserial` instead of ULID

Every table uses:
```sql
id bigserial primary key       -- ❌ violates U1, U2, U3
```

Should be:
```sql
id text primary key default generate_ulid()
```

**Affected**: `sources`, `crawl_runs`, `crawl_queue`, `source_pages`, `articles`, `article_assets`, `tags`, `publish_targets`, `article_publications` (9 tables with id), plus `article_tags` composite PK.

### V-02 [CRITICAL] All FK columns use `bigint` instead of `text`

Every FK reference is:
```sql
source_id bigint not null references public.sources(id)   -- ❌
```

Should be:
```sql
source_id text not null references public.sources(id)
```

**Affected**: 14 FK columns across all tables.

### V-03 [HIGH] `generate_ulid()` function not defined

The schema loads `pgcrypto` and `uuid-ossp` but never defines `generate_ulid()`. This function must exist before any table can use `DEFAULT generate_ulid()`.

**Fix**: Add `generate_ulid()` function definition before all CREATE TABLE statements.

---

## Category 2: Schema Design (schema-design.md)

### V-04 [CRITICAL] No `project_id` on any table

Guideline: "所有業務表必須有 `project_id` 欄位做 tenant scoping"

None of the 10 tables have `project_id`. If this crawler serves multiple projects/tenants, every business table needs it.

**Decision needed**: Is this a single-project crawler (OK to skip) or multi-tenant (must add)? The guidelines say **must add** without exception.

**If multi-tenant**, add to: `sources`, `crawl_runs`, `crawl_queue`, `source_pages`, `articles`, `article_assets`, `tags`, `publish_targets`, `article_publications`.

### V-05 [MEDIUM] No `created_by` on any table

Guideline: user-generated data must have `created_by TEXT NOT NULL REFERENCES users(id)`.

The crawler is a system-level ETL pipeline, so this is partially justified. But `sources` (manually configured) and `publish_targets` (manually configured) should have `created_by`.

### V-06 [MEDIUM] Table naming doesn't follow module prefix convention

Guideline: ETL/crawler tables should use `raw_*`, `staging_*` prefixes.

| Current | Suggested (by guideline) | Layer |
|---------|-------------------------|-------|
| `source_pages` | `raw_source_pages` | Raw (HTML storage) |
| `articles` | `staging_articles` or keep `articles` | Staging (normalized) |
| `crawl_queue` | OK (system table) | System |
| `crawl_runs` | OK (system table) | System |

**Decision needed**: Rename to follow convention or document the exception.

### V-07 [HIGH] `publish_targets` missing `updated_at`

```sql
create table public.publish_targets (
  ...
  created_at timestamptz not null default now()
  -- ❌ missing updated_at
);
```

Guideline: every table must have `created_at` + `updated_at`.

### V-08 [HIGH] `crawl_runs` missing `updated_at`

Same issue — only has `created_at`, no `updated_at`, no trigger.

### V-09 [HIGH] `article_publications` missing `created_at` and `updated_at`

No timestamp columns at all.

### V-10 [MEDIUM] `tags` missing `updated_at`

Only has `created_at`.

---

## Category 3: Migration Guidelines (migration-guidelines.md)

### V-11 [HIGH] DDL not idempotent

All `CREATE TABLE` statements lack `IF NOT EXISTS`:

```sql
create table public.sources (     -- ❌
```

Should be:
```sql
create table if not exists public.sources (  -- ✅
```

Same for all `CREATE INDEX` (missing `IF NOT EXISTS`), all `CREATE TRIGGER` (not idempotent).

### V-12 [HIGH] Trigger function name doesn't match convention

Schema defines:
```sql
create or replace function public.set_updated_at()   -- ❌ non-standard name
```

Guideline mandates:
```sql
create or replace function update_updated_at_column() -- ✅ standard name
```

And trigger naming should be `trg_<table>_updated_at` (partially followed, but trigger references wrong function name).

### V-13 [HIGH] UNIQUE constraints not explicitly named

```sql
unique (source_id, url)           -- ❌ implicit name
unique (article_id, target_id)    -- ❌ implicit name
unique (taxonomy, name)           -- ❌ implicit name
```

Guideline: "隱式 constraint — 難以在後續 migration 修改 → 明確命名 constraint"

Should be:
```sql
constraint uq_source_pages_source_url unique (source_id, url)
constraint uq_article_publications_article_target unique (article_id, target_id)
constraint uq_tags_taxonomy_name unique (taxonomy, name)
```

### V-14 [MEDIUM] Missing GRANT statements

No `GRANT` statements for any table. Guideline requires:

```sql
GRANT SELECT ON public.<table> TO authenticated, anon;
GRANT INSERT, UPDATE, DELETE ON public.<table> TO authenticated;
GRANT ALL ON public.<table> TO service_role;
```

For a crawler ETL pipeline, at minimum `service_role` GRANTs are needed.

---

## Category 4: RLS (rls-patterns.md)

### V-15 [CRITICAL] 7 tables missing RLS enablement

Only 3 tables have RLS enabled. Missing:

| Table | Needs RLS? | Reason |
|-------|-----------|--------|
| `crawl_runs` | Yes | Contains execution data |
| `crawl_queue` | Yes | Contains URLs and payloads |
| `source_pages` | Yes | Contains raw HTML |
| `tags` | Yes | Shared taxonomy |
| `article_tags` | Yes | Join table |
| `publish_targets` | Yes | Contains credentials in config |
| `article_publications` | Yes | Contains remote IDs/URLs |

Guideline: "所有 public 表必須啟用 RLS，無例外。"

### V-16 [HIGH] Policies use `USING (true)` instead of helper functions

```sql
create policy "dev_all_access" on public.sources for all using (true);  -- ❌
```

For dev phase this is understandable, but:
- No `service_role` specific policy
- No `TO authenticated` / `TO service_role` role targeting
- No `WITH CHECK` clause

Guideline pattern:
```sql
CREATE POLICY "sources_service_role"
  ON public.sources FOR ALL TO service_role
  USING (true) WITH CHECK (true);
```

### V-17 [MEDIUM] Lease RPC function missing `SET search_path`

```sql
create or replace function public.lease_next_crawl_job(...)
language sql                    -- ❌ missing SECURITY DEFINER + SET search_path
as $$
```

Guideline: helper functions must have `SET search_path = public`.

---

## Category 5: Index Strategy (migration-guidelines.md, performance-linter.md)

### V-18 [HIGH] 7 FK columns missing dedicated index

| FK Column | Table | Has Index? |
|-----------|-------|-----------|
| `crawl_queue.source_id` | crawl_queue | **No** (only status+priority composite) |
| `source_pages.crawl_run_id` | source_pages | **No** |
| `articles.source_page_id` | articles | **No** |
| `article_assets.source_page_id` | article_assets | **No** |
| `article_tags.tag_id` | article_tags | **No** (PK covers article_id direction only) |
| `article_publications.target_id` | article_publications | **No** |
| `tags.parent_id` | tags | **No** |

Guideline Tier 1: "所有 FK 欄位必須有單欄 index"

### V-19 [HIGH] Lease query lacks optimized index

The RPC does:
```sql
WHERE (status = 'pending' AND scheduled_at <= now())
   OR (status = 'leased' AND lease_expires_at < now())
ORDER BY priority DESC, scheduled_at ASC
```

Current index `(status, priority desc)` doesn't cover `scheduled_at` or `lease_expires_at`. Under load, this becomes a sequential scan within each status partition.

**Recommended**:
```sql
CREATE INDEX idx_crawl_queue_lease_pending
  ON public.crawl_queue(priority DESC, scheduled_at ASC)
  WHERE status = 'pending';

CREATE INDEX idx_crawl_queue_lease_expired
  ON public.crawl_queue(lease_expires_at ASC)
  WHERE status = 'leased';
```

### V-20 [MEDIUM] Missing composite indexes for common query patterns

No composite indexes for typical list queries:
```sql
-- articles by source, sorted by date
CREATE INDEX idx_articles_source_published
  ON public.articles(source_id, published_at DESC);

-- source_pages by source + type
CREATE INDEX idx_source_pages_source_type
  ON public.source_pages(source_id, page_type, fetched_at DESC);
```

---

## Category 6: Large Table Management (large-table-management.md, scaling-guidelines.md)

### V-21 [CRITICAL] `source_pages` is append-heavy but not partitioned

`source_pages` stores raw HTML and will grow rapidly (especially with multiple sources). Guideline says append-heavy tables >1M rows must be partitioned.

```sql
-- ❌ Current: no partition
create table public.source_pages (
  id bigserial primary key,
  ...
);

-- ✅ Should be:
create table public.source_pages (
  id text not null default generate_ulid(),
  ...
  primary key (id, created_at)    -- PK must include partition key
) partition by range (created_at);
```

### V-22 [HIGH] No `autovacuum_vacuum_scale_factor` tuning on append-heavy tables

Guideline: "千萬大表必須覆寫清理閾值"

Missing on: `source_pages`, `crawl_queue`, `articles`, `crawl_runs`.

```sql
ALTER TABLE public.source_pages SET (autovacuum_vacuum_scale_factor = 0.05);
ALTER TABLE public.crawl_queue SET (autovacuum_vacuum_scale_factor = 0.05);
```

### V-23 [MEDIUM] `locked_at` column in `crawl_queue` is dead weight

The `locked_at` column (line 88) is never used in any code or RPC. The lease system uses `leased_at` instead. Should be removed to avoid confusion.

### V-24 [MEDIUM] `publish_targets.target_type` missing CHECK constraint

```sql
target_type text not null,    -- ❌ no CHECK
```

Guideline D3: "Status 欄位沒有 CHECK → 加 CHECK"

Should be:
```sql
target_type text not null
  check (target_type in ('wordpress','notion','ghost','custom_api','internal'))
```

---

## Category 7: Lease RPC & Queue Safety (query-patterns.md, scaling-guidelines.md)

### V-25 [CRITICAL] `lease_next_crawl_job()` returns `SELECT *`

```sql
returning *;    -- ❌ violates "禁止 SELECT *"
```

Should return only needed columns:
```sql
returning id, source_id, url, page_type, lease_token, retry_count, max_retries, payload;
```

### V-26 [HIGH] No `statement_timeout` on RPC function

Guideline: "強制 `statement_timeout` 截斷呆滯查詢"

The lease function can potentially hang if the queue table is locked. Should set:
```sql
SET statement_timeout = '5s'
```

### V-27 [HIGH] No retention/cleanup strategy for `crawl_queue`

Completed/failed jobs stay in `crawl_queue` forever. Guideline says append-heavy tables need lifecycle:

- `done` jobs older than 7 days → delete
- `dead` jobs older than 30 days → archive then delete
- `failed` jobs older than 30 days → archive then delete

### V-28 [HIGH] `source_pages.raw_html` stored in main table

Raw HTML can be 100KB-1MB per row. Storing it inline causes:
- Table bloat (P2: "傳輸不必要的大欄位")
- Every query touching `source_pages` scans this data

**Options**:
- Use TOAST (PostgreSQL handles automatically, but still bloats)
- Move `raw_html` to Supabase Storage, store only path in DB (guideline S4)
- Or at minimum, never `SELECT *` from this table

### V-29 [CRITICAL] `uuid-ossp` extension loaded but not needed

The schema loads `uuid-ossp` (line 5) but:
- If switching to ULID, `uuid-ossp` is unnecessary
- `gen_random_uuid()` used in lease RPC comes from `pgcrypto`, not `uuid-ossp`
- Guideline U1: "業務表不用 UUID"

---

## Summary Table

| Severity | Count | Categories |
|----------|-------|-----------|
| CRITICAL | 6 | V-01, V-02, V-04, V-15, V-21, V-25 |
| HIGH | 14 | V-03, V-07, V-08, V-09, V-11, V-12, V-13, V-16, V-18, V-19, V-22, V-26, V-27, V-28 |
| MEDIUM | 7 | V-05, V-06, V-10, V-14, V-17, V-20, V-23, V-24 |
| INFO | 1 | V-29 |

---

## Recommended Fix Order (Stage by Stage)

### Stage 1: Foundation (must fix before anything else)

1. **Define `generate_ulid()` function** (V-03)
2. **Change all PK to `text default generate_ulid()`** (V-01)
3. **Change all FK to `text`** (V-02)
4. **Add `IF NOT EXISTS` to all DDL** (V-11)
5. **Rename trigger function to `update_updated_at_column()`** (V-12)
6. **Remove `uuid-ossp` extension** (V-29)

### Stage 2: Missing Columns & Constraints

7. **Add `updated_at` to `crawl_runs`, `tags`, `publish_targets`** (V-07, V-08, V-10)
8. **Add `created_at` + `updated_at` to `article_publications`** (V-09)
9. **Add `updated_at` triggers for all tables that have `updated_at`**
10. **Name all UNIQUE constraints explicitly** (V-13)
11. **Add CHECK on `publish_targets.target_type`** (V-24)
12. **Remove dead `locked_at` column** (V-23)

### Stage 3: Indexes

13. **Add missing FK indexes** (7 columns) (V-18)
14. **Add partial indexes for lease query** (V-19)
15. **Add composite indexes for list queries** (V-20)

### Stage 4: RLS & Security

16. **Enable RLS on all 7 missing tables** (V-15)
17. **Add `service_role` policies for all tables** (V-16)
18. **Add `SET search_path` to RPC function** (V-17)
19. **Add GRANT statements** (V-14)
20. **Add `statement_timeout` to RPC** (V-26)
21. **Change `RETURNING *` to explicit columns** (V-25)

### Stage 5: Scaling Preparation

22. **Decide `project_id` strategy** — add if multi-tenant needed (V-04)
23. **Partition `source_pages`** (V-21)
24. **Add autovacuum tuning** (V-22)
25. **Design retention policy for `crawl_queue`** (V-27)
26. **Consider moving `raw_html` to Storage** (V-28)

### Stage 6: Naming & Convention (optional polish)

27. **Add `created_by` to manually-configured tables** (V-05)
28. **Consider table prefix convention** (V-06)

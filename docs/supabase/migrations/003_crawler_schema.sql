-- ============================================================
-- Crawler Schema  v3.0 (post-audit)
-- Fixed per 02_AUDIT-vs-guidelines.md violations
-- ============================================================
--
-- Conventions:
--   - PK: TEXT DEFAULT public.generate_ulid()  (not BIGSERIAL)
--   - FK: TEXT references (type consistency)
--   - Every business table: project_id for tenant scoping
--   - Every table: created_at + updated_at (where applicable)
--   - RLS enabled on ALL tables + helper functions + GRANTs
--   - service_role policy on every table
--   - moddatetime for updated_at (not hand-written trigger)
--   - Named CHECK / UNIQUE constraints
--   - Indexes on all FK columns
--   - SECURITY DEFINER + SET search_path on all functions
--
-- Audit fixes (v2.0 -> v3.0):
--   V-04: project_id added to all business tables
--   V-05: created_by added to sources, publish_targets
--   V-08: updated_at added to crawl_runs + moddatetime trigger
--   V-09: created_at confirmed on article_publications
--   V-10: updated_at confirmed on tags + trigger
--   V-18: FK indexes confirmed on all FK columns
--
-- Original "29 violations" version preserved in git history.
-- See 01_HEAD-FIRST-crawler-db.md for the teaching walkthrough.
-- ============================================================


-- ************************************************************
-- STAGE 1: FOUNDATION
-- ************************************************************

-- NOTE: schema, extensions, generate_ulid() 已移至 001_extensions.sql


-- ************************************************************
-- STAGE 2: SOURCES
-- ************************************************************

create table if not exists crawler.sources (
  id                text primary key default public.generate_ulid(),
  project_id        text         not null,
  code              text         not null,
  name              text         not null,
  description       text,
  base_url          text,
  domain            text,
  crawler_url       text,
  config            jsonb        not null default '{}'::jsonb,
  extractor_schema  jsonb        not null default '{}'::jsonb,
  field_mapping     jsonb        not null default '{}'::jsonb,
  is_enabled        boolean      not null default true,
  schedule_cron     text,
  last_run_at       timestamptz,
  created_by        text,
  created_at        timestamptz  not null default now(),
  updated_at        timestamptz  not null default now(),
  constraint uq_sources_code_per_project unique (project_id, code)
);

create index if not exists idx_sources_project on crawler.sources(project_id);
create index if not exists idx_sources_enabled on crawler.sources(project_id, is_enabled)
  where is_enabled = true;


-- ************************************************************
-- STAGE 3: CRAWL RUNS
-- ************************************************************

create table if not exists crawler.crawl_runs (
  id                  text primary key default public.generate_ulid(),
  project_id          text         not null,
  source_id           text         not null references crawler.sources(id) on delete cascade,
  run_status          text         not null default 'pending',
  started_at          timestamptz,
  finished_at         timestamptz,
  pages_found         integer      not null default 0,
  pages_fetched       integer      not null default 0,
  articles_extracted  integer      not null default 0,
  error_count         integer      not null default 0,
  logs                jsonb        not null default '[]'::jsonb,
  created_at          timestamptz  not null default now(),
  updated_at          timestamptz  not null default now(),
  constraint ck_crawl_runs_status
    check (run_status in ('pending','running','success','partial','failed'))
);

create index if not exists idx_crawl_runs_project on crawler.crawl_runs(project_id);
create index if not exists idx_crawl_runs_source on crawler.crawl_runs(source_id, created_at desc);


-- ************************************************************
-- STAGE 4: CRAWL QUEUE
-- ************************************************************

create table if not exists crawler.crawl_queue (
  id               text primary key default public.generate_ulid(),
  project_id       text         not null,
  source_id        text         not null references crawler.sources(id) on delete cascade,
  url              text         not null,
  page_type        text         not null default 'article',
  priority         integer      not null default 100,
  status           text         not null default 'pending',
  retry_count      integer      not null default 0,
  max_retries      integer      not null default 5,
  scheduled_at     timestamptz  not null default now(),
  locked_at        timestamptz,
  finished_at      timestamptz,
  -- lease-based concurrency control
  lease_token      text,
  leased_at        timestamptz,
  lease_expires_at timestamptz,
  worker_id        text,
  error_code       text,
  error_message    text,
  payload          jsonb        not null default '{}'::jsonb,
  created_at       timestamptz  not null default now(),
  constraint ck_crawl_queue_status
    check (status in ('pending','leased','running','done','failed','skipped','dead'))
);

create index if not exists idx_crawl_queue_project on crawler.crawl_queue(project_id);
create index if not exists idx_crawl_queue_source on crawler.crawl_queue(source_id);
create index if not exists idx_crawl_queue_status on crawler.crawl_queue(status, priority desc);
create index if not exists idx_crawl_queue_lease on crawler.crawl_queue(status, scheduled_at)
  where status = 'pending';
-- 防止 cron 重複塞入相同 source+url 的 pending 任務
create unique index if not exists uq_crawl_queue_pending_source_url
  on crawler.crawl_queue(source_id, url) where status = 'pending';


-- ************************************************************
-- STAGE 5: SOURCE PAGES
-- ************************************************************

create table if not exists crawler.source_pages (
  id             text primary key default public.generate_ulid(),
  project_id     text         not null,
  source_id      text         not null references crawler.sources(id) on delete cascade,
  crawl_run_id   text         references crawler.crawl_runs(id) on delete set null,
  page_type      text         not null default 'article',
  topic          text,
  url            text         not null,
  canonical_url  text,
  title          text,
  raw_html       text,
  snapshot_json  jsonb,
  http_status    integer,
  fetched_at     timestamptz,
  last_seen_at   timestamptz,
  is_available   boolean      not null default true,
  created_at     timestamptz  not null default now(),
  updated_at     timestamptz  not null default now(),
  constraint uq_source_pages_source_url unique (source_id, url),
  constraint ck_source_pages_type
    check (page_type in ('list','article','detail','unknown'))
);

create index if not exists idx_source_pages_project on crawler.source_pages(project_id);
create index if not exists idx_source_pages_source on crawler.source_pages(source_id);
create index if not exists idx_source_pages_crawl_run on crawler.source_pages(crawl_run_id)
  where crawl_run_id is not null;
create index if not exists idx_source_pages_fetched on crawler.source_pages(fetched_at desc);


-- ************************************************************
-- STAGE 6: ARTICLES
-- ************************************************************

create table if not exists crawler.articles (
  id                 text primary key default public.generate_ulid(),
  project_id         text         not null,
  source_id          text         not null references crawler.sources(id) on delete cascade,
  source_page_id     text         references crawler.source_pages(id) on delete set null,
  external_id        text,
  title              text         not null,
  slug               text,
  author_name        text,
  author_url         text,
  abstract           text,
  content_html       text,
  content_text       text,
  published_at       timestamptz,
  source_modified_at timestamptz,
  source_url         text         not null,
  canonical_url      text,
  lang               text,
  meta               jsonb        not null default '{}'::jsonb,
  extraction_data    jsonb        not null default '{}'::jsonb,
  is_published       boolean      not null default true,
  is_available       boolean      not null default true,
  content_hash       text,
  created_at         timestamptz  not null default now(),
  updated_at         timestamptz  not null default now(),
  constraint uq_articles_source_url unique (source_id, source_url)
);

create index if not exists idx_articles_project on crawler.articles(project_id);
create index if not exists idx_articles_source on crawler.articles(source_id);
create index if not exists idx_articles_source_page on crawler.articles(source_page_id)
  where source_page_id is not null;
create index if not exists idx_articles_published on crawler.articles(published_at desc);
create index if not exists idx_articles_hash on crawler.articles(content_hash)
  where content_hash is not null;


-- ************************************************************
-- STAGE 7: ARTICLE ASSETS
-- ************************************************************

create table if not exists crawler.article_assets (
  id             text primary key default public.generate_ulid(),
  project_id     text         not null,
  article_id     text         not null references crawler.articles(id) on delete cascade,
  source_page_id text         references crawler.source_pages(id) on delete set null,
  asset_type     text         not null default 'image',
  original_url   text,
  storage_bucket text,
  storage_path   text,
  mime_type      text,
  alt_text       text,
  caption        text,
  width          integer,
  height         integer,
  checksum       text,
  sort_order     integer      not null default 0,
  created_at     timestamptz  not null default now(),
  updated_at     timestamptz  not null default now(),
  constraint ck_article_assets_type
    check (asset_type in ('image','video','file','audio'))
);

create index if not exists idx_assets_project on crawler.article_assets(project_id);
create index if not exists idx_assets_article on crawler.article_assets(article_id);
create index if not exists idx_assets_source_page on crawler.article_assets(source_page_id)
  where source_page_id is not null;


-- ************************************************************
-- STAGE 8: TAGS
-- ************************************************************

create table if not exists crawler.tags (
  id          text primary key default public.generate_ulid(),
  project_id  text         not null,
  taxonomy    text         not null default 'tag',
  name        text         not null,
  slug        text,
  description text,
  parent_id   text         references crawler.tags(id) on delete set null,
  meta        jsonb        not null default '{}'::jsonb,
  created_at  timestamptz  not null default now(),
  updated_at  timestamptz  not null default now(),
  constraint uq_tags_taxonomy_name unique (taxonomy, name)
);

create index if not exists idx_tags_project on crawler.tags(project_id);
create index if not exists idx_tags_taxonomy on crawler.tags(taxonomy, name);
create index if not exists idx_tags_parent on crawler.tags(parent_id) where parent_id is not null;

create table if not exists crawler.article_tags (
  article_id text not null references crawler.articles(id) on delete cascade,
  tag_id     text not null references crawler.tags(id) on delete cascade,
  created_at timestamptz not null default now(),
  primary key (article_id, tag_id)
);

create index if not exists idx_article_tags_tag on crawler.article_tags(tag_id);


-- ************************************************************
-- STAGE 9: PUBLISH TARGETS
-- ************************************************************

create table if not exists crawler.publish_targets (
  id          text primary key default public.generate_ulid(),
  project_id  text         not null,
  code        text         not null unique,
  name        text         not null,
  target_type text         not null,
  config      jsonb        not null default '{}'::jsonb,
  is_enabled  boolean      not null default true,
  created_by  text,
  created_at  timestamptz  not null default now(),
  updated_at  timestamptz  not null default now()
);

create index if not exists idx_publish_targets_project on crawler.publish_targets(project_id);

create table if not exists crawler.article_publications (
  id               text primary key default public.generate_ulid(),
  project_id       text         not null,
  article_id       text         not null references crawler.articles(id) on delete cascade,
  target_id        text         not null references crawler.publish_targets(id) on delete cascade,
  remote_id        text,
  remote_url       text,
  publish_status   text         not null default 'pending',
  last_published_at timestamptz,
  payload          jsonb        not null default '{}'::jsonb,
  result           jsonb        not null default '{}'::jsonb,
  created_at       timestamptz  not null default now(),
  updated_at       timestamptz  not null default now(),
  constraint uq_article_publications unique (article_id, target_id),
  constraint ck_article_publications_status
    check (publish_status in ('pending','published','failed','deleted'))
);

create index if not exists idx_article_publications_project on crawler.article_publications(project_id);
create index if not exists idx_article_publications_article on crawler.article_publications(article_id);
create index if not exists idx_article_publications_target on crawler.article_publications(target_id);


-- ************************************************************
-- STAGE 10: LEASE RPC
-- ************************************************************

create or replace function crawler.lease_next_crawl_job(
  p_worker_id text,
  p_lease_duration interval default interval '5 minutes'
)
returns setof crawler.crawl_queue
language sql
security definer
set search_path = crawler
as $$
  update crawler.crawl_queue
  set
    status = 'leased',
    lease_token = gen_random_uuid()::text,
    leased_at = now(),
    lease_expires_at = now() + p_lease_duration,
    worker_id = p_worker_id
  where id = (
    select id
    from crawler.crawl_queue
    where (status = 'pending' and scheduled_at <= now())
       or (status = 'leased' and lease_expires_at < now())
    order by priority desc, scheduled_at asc
    limit 1
    for update skip locked
  )
  returning *;
$$;

grant execute on function crawler.lease_next_crawl_job(text, interval) to authenticated;


-- ************************************************************
-- STAGE 11: TRIGGERS (moddatetime)
-- ************************************************************

do $$
declare
  tbl text;
begin
  foreach tbl in array array[
    'sources', 'crawl_runs', 'source_pages', 'articles',
    'article_assets', 'tags', 'publish_targets', 'article_publications'
  ]
  loop
    execute format('
      drop trigger if exists trg_%1$s_updated_at on crawler.%1$s;
      create trigger trg_%1$s_updated_at
        before update on crawler.%1$s
        for each row execute function moddatetime(updated_at);
    ', tbl);
  end loop;
end;
$$;

-- NOTE: crawl_queue is append-heavy / state-machine with lease lifecycle,
-- updated_at not applicable (no moddatetime trigger needed).


-- ************************************************************
-- STAGE 12: RLS + Policies + GRANTs
-- ************************************************************

-- Enable RLS on ALL tables
do $$
declare
  tbl text;
begin
  foreach tbl in array array[
    'sources', 'crawl_runs', 'crawl_queue', 'source_pages',
    'articles', 'article_assets', 'tags', 'article_tags',
    'publish_targets', 'article_publications'
  ]
  loop
    execute format('alter table crawler.%I enable row level security;', tbl);
  end loop;
end;
$$;

-- ************************************************************
-- RLS PATTERN: Multi-Tenant（project_id scoping via JWT）
-- ************************************************************
-- 教學重點：
--   - 每個 crawler 表都有 project_id 欄位
--   - 用 JWT custom claim (app_metadata.project_ids) 做租戶隔離
--   - 用戶只能存取自己 project 的資料
--   - Helper function 封裝 claim 讀取邏輯
--   - service_role 不受限制（後端 pipeline 用）
--
-- JWT app_metadata 範例：
--   { "project_ids": ["demo-project", "prod-project"] }
--
-- 設定方式（Supabase Dashboard → Authentication → Users → Edit User）：
--   或用 SQL：
--   UPDATE auth.users SET raw_app_meta_data =
--     raw_app_meta_data || '{"project_ids":["demo-project"]}'::jsonb
--   WHERE id = 'user-uuid';
-- ************************************************************

-- Helper: 取得當前用戶可存取的 project_ids（從 JWT app_metadata）
create or replace function crawler.get_my_project_ids()
returns text[]
language sql
stable
security definer
set search_path = crawler
as $$
  select coalesce(
    array(
      select jsonb_array_elements_text(
        (select auth.jwt()) -> 'app_metadata' -> 'project_ids'
      )
    ),
    '{}'::text[]
  );
$$;

grant execute on function crawler.get_my_project_ids() to authenticated;

-- Helper: 檢查用戶是否可存取特定 project
create or replace function crawler.has_project_access(p_project_id text)
returns boolean
language sql
stable
security definer
set search_path = crawler
as $$
  select p_project_id = ANY(crawler.get_my_project_ids());
$$;

grant execute on function crawler.has_project_access(text) to authenticated;

-- Sources: 直接檢查 project_id
create policy "sources_select" on crawler.sources
  for select to authenticated
  using (crawler.has_project_access(project_id));
create policy "sources_insert" on crawler.sources
  for insert to authenticated
  with check (crawler.has_project_access(project_id));
create policy "sources_update" on crawler.sources
  for update to authenticated
  using (crawler.has_project_access(project_id));
create policy "sources_delete" on crawler.sources
  for delete to authenticated
  using (crawler.has_project_access(project_id));
create policy "sources_service_role" on crawler.sources
  for all to service_role using (true) with check (true);

-- 有 project_id 欄位的表：直接檢查
do $$
declare
  tbl text;
begin
  foreach tbl in array array[
    'crawl_runs', 'crawl_queue', 'source_pages',
    'articles', 'article_assets'
  ]
  loop
    execute format('
      create policy "%1$s_select" on crawler.%1$s
        for select to authenticated
        using (crawler.has_project_access(project_id));
      create policy "%1$s_insert" on crawler.%1$s
        for insert to authenticated
        with check (crawler.has_project_access(project_id));
      create policy "%1$s_update" on crawler.%1$s
        for update to authenticated
        using (crawler.has_project_access(project_id));
      create policy "%1$s_delete" on crawler.%1$s
        for delete to authenticated
        using (crawler.has_project_access(project_id));
      create policy "%1$s_service_role" on crawler.%1$s
        for all to service_role using (true) with check (true);
    ', tbl);
  end loop;
end;
$$;

-- tags / publish_targets: 有 project_id，一樣做 tenant scoping
-- article_tags / article_publications: 沒有 project_id，透過 FK 繼承
do $$
declare
  tbl text;
begin
  -- 有 project_id 的 reference tables
  foreach tbl in array array['tags', 'publish_targets']
  loop
    execute format('
      create policy "%1$s_select" on crawler.%1$s
        for select to authenticated, anon
        using (crawler.has_project_access(project_id));
      create policy "%1$s_insert" on crawler.%1$s
        for insert to authenticated
        with check (crawler.has_project_access(project_id));
      create policy "%1$s_update" on crawler.%1$s
        for update to authenticated
        using (crawler.has_project_access(project_id));
      create policy "%1$s_delete" on crawler.%1$s
        for delete to authenticated
        using (crawler.has_project_access(project_id));
      create policy "%1$s_service_role" on crawler.%1$s
        for all to service_role using (true) with check (true);
    ', tbl);
  end loop;

  -- 沒有 project_id 的 junction tables（public read, authenticated write）
  foreach tbl in array array['article_tags', 'article_publications']
  loop
    execute format('
      create policy "%1$s_select" on crawler.%1$s
        for select to authenticated, anon using (true);
      create policy "%1$s_insert" on crawler.%1$s
        for insert to authenticated with check (true);
      create policy "%1$s_update" on crawler.%1$s
        for update to authenticated using (true);
      create policy "%1$s_delete" on crawler.%1$s
        for delete to authenticated using (true);
      create policy "%1$s_service_role" on crawler.%1$s
        for all to service_role using (true) with check (true);
    ', tbl);
  end loop;
end;
$$;

-- GRANTs
do $$
declare
  tbl text;
begin
  foreach tbl in array array[
    'sources', 'crawl_runs', 'crawl_queue', 'source_pages',
    'articles', 'article_assets', 'tags', 'article_tags',
    'publish_targets', 'article_publications'
  ]
  loop
    execute format('grant select on crawler.%I to authenticated;', tbl);
    execute format('grant insert, update, delete on crawler.%I to authenticated;', tbl);
    execute format('grant all on crawler.%I to service_role;', tbl);
  end loop;

  -- Public-readable tables
  foreach tbl in array array['tags', 'publish_targets', 'articles']
  loop
    execute format('grant select on crawler.%I to anon;', tbl);
  end loop;
end;
$$;

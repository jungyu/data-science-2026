-- crawler schema migration
-- 建立 crawler schema、核心資料表、索引、updated_at trigger、
-- lease_next_crawl_job() RPC，以及 PostgREST 存取權限。

create schema if not exists crawler;

create extension if not exists pgcrypto with schema extensions;

-- ── updated_at trigger 函式 ──────────────────────────────────────

create or replace function crawler.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

-- ── 1. sources ──────────────────────────────────────────────────

create table if not exists crawler.sources (
  id            uuid        primary key default gen_random_uuid(),
  project_id    text        not null,
  code          text        not null,
  name          text        not null,
  description   text,
  base_url      text,
  domain        text,
  crawler_url   text,
  config        jsonb       not null default '{}'::jsonb,
  extractor_schema jsonb    not null default '{}'::jsonb,
  field_mapping jsonb       not null default '{}'::jsonb,
  is_enabled    boolean     not null default true,
  schedule_cron text,
  last_run_at   timestamptz,
  created_by    text,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now(),
  constraint sources_project_code_key unique (project_id, code)
);

-- ── 2. crawl_runs ───────────────────────────────────────────────

create table if not exists crawler.crawl_runs (
  id                  uuid        primary key default gen_random_uuid(),
  project_id          text        not null,
  source_id           uuid        not null references crawler.sources(id) on delete cascade,
  run_status          text        not null default 'pending',
  started_at          timestamptz,
  finished_at         timestamptz,
  pages_found         integer     not null default 0,
  pages_fetched       integer     not null default 0,
  articles_extracted  integer     not null default 0,
  error_count         integer     not null default 0,
  logs                jsonb       not null default '[]'::jsonb,
  created_at          timestamptz not null default now(),
  updated_at          timestamptz not null default now(),
  constraint crawl_runs_status_check
    check (run_status in ('pending', 'running', 'success', 'partial', 'failed'))
);

-- ── 3. crawl_queue ──────────────────────────────────────────────

create table if not exists crawler.crawl_queue (
  id                uuid        primary key default gen_random_uuid(),
  project_id        text        not null,
  source_id         uuid        not null references crawler.sources(id) on delete cascade,
  url               text        not null,
  page_type         text        not null default 'article',
  priority          integer     not null default 100,
  status            text        not null default 'pending',
  retry_count       integer     not null default 0,
  max_retries       integer     not null default 5,
  scheduled_at      timestamptz not null default now(),
  lease_token       text,
  leased_at         timestamptz,
  lease_expires_at  timestamptz,
  worker_id         text,
  locked_at         timestamptz,
  finished_at       timestamptz,
  error_code        text,
  error_message     text,
  payload           jsonb       not null default '{}'::jsonb,
  created_at        timestamptz not null default now(),
  updated_at        timestamptz not null default now(),
  constraint crawl_queue_page_type_check
    check (page_type in ('list', 'article', 'detail', 'unknown')),
  constraint crawl_queue_status_check
    check (status in ('pending', 'leased', 'running', 'done', 'failed', 'skipped', 'dead'))
);

-- 同一 source+url 在 pending 狀態下唯一（防止重複入列）
create unique index if not exists uq_crawl_queue_pending_source_url
  on crawler.crawl_queue (source_id, url)
  where status = 'pending';

-- lease 搶單順序索引（priority desc → scheduled_at asc → created_at asc）
create index if not exists idx_crawl_queue_lease_order
  on crawler.crawl_queue (source_id, status, priority desc, scheduled_at asc, created_at asc);

-- ── 4. source_pages ─────────────────────────────────────────────

create table if not exists crawler.source_pages (
  id            uuid        primary key default gen_random_uuid(),
  project_id    text        not null,
  source_id     uuid        not null references crawler.sources(id) on delete cascade,
  crawl_run_id  uuid        references crawler.crawl_runs(id) on delete set null,
  page_type     text        not null default 'article',
  topic         text,
  url           text        not null,
  canonical_url text,
  title         text,
  raw_html      text,
  snapshot_json jsonb,
  http_status   integer,
  fetched_at    timestamptz,
  last_seen_at  timestamptz,
  is_available  boolean     not null default true,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now(),
  constraint source_pages_page_type_check
    check (page_type in ('list', 'article', 'detail', 'unknown')),
  constraint source_pages_source_url_key unique (source_id, url)
);

-- ── 5. articles ─────────────────────────────────────────────────

create table if not exists crawler.articles (
  id                  uuid        primary key default gen_random_uuid(),
  project_id          text        not null,
  source_id           uuid        not null references crawler.sources(id) on delete cascade,
  source_page_id      uuid        references crawler.source_pages(id) on delete set null,
  external_id         text,
  title               text        not null,
  slug                text,
  author_name         text,
  author_url          text,
  abstract            text,
  content_html        text,
  content_text        text,
  published_at        timestamptz,
  source_modified_at  timestamptz,
  source_url          text        not null,
  canonical_url       text,
  lang                text,
  meta                jsonb       not null default '{}'::jsonb,
  extraction_data     jsonb       not null default '{}'::jsonb,
  is_published        boolean     not null default true,
  is_available        boolean     not null default true,
  content_hash        text,
  created_at          timestamptz not null default now(),
  updated_at          timestamptz not null default now(),
  constraint articles_source_url_key unique (source_id, source_url)
);

create index if not exists idx_articles_source_page
  on crawler.articles (source_page_id);

-- ── updated_at triggers ─────────────────────────────────────────

drop trigger if exists trg_sources_updated_at on crawler.sources;
create trigger trg_sources_updated_at
  before update on crawler.sources
  for each row execute function crawler.set_updated_at();

drop trigger if exists trg_crawl_runs_updated_at on crawler.crawl_runs;
create trigger trg_crawl_runs_updated_at
  before update on crawler.crawl_runs
  for each row execute function crawler.set_updated_at();

drop trigger if exists trg_crawl_queue_updated_at on crawler.crawl_queue;
create trigger trg_crawl_queue_updated_at
  before update on crawler.crawl_queue
  for each row execute function crawler.set_updated_at();

drop trigger if exists trg_source_pages_updated_at on crawler.source_pages;
create trigger trg_source_pages_updated_at
  before update on crawler.source_pages
  for each row execute function crawler.set_updated_at();

drop trigger if exists trg_articles_updated_at on crawler.articles;
create trigger trg_articles_updated_at
  before update on crawler.articles
  for each row execute function crawler.set_updated_at();

-- ── lease_next_crawl_job() RPC ──────────────────────────────────
--
-- 原子搶單：FOR UPDATE SKIP LOCKED 確保多 Worker 並行安全。
-- 搶到的任務從 pending → leased，並寫入 lease_token / lease_expires_at。
-- 呼叫端在 lease 到期前必須更新狀態（running → done/failed），
-- 否則任務會被其他 Worker 重新搶走。

create or replace function crawler.lease_next_crawl_job(p_worker_id text)
returns setof crawler.crawl_queue
language plpgsql
security definer
set search_path = public, extensions, crawler
as $$
declare
  leased_row crawler.crawl_queue%rowtype;
begin
  with next_job as (
    select cq.id
    from crawler.crawl_queue cq
    where cq.status = 'pending'
      and cq.scheduled_at <= now()
      and cq.retry_count < cq.max_retries
    order by cq.priority desc, cq.scheduled_at asc, cq.created_at asc
    for update skip locked
    limit 1
  )
  update crawler.crawl_queue cq
  set
    status           = 'leased',
    lease_token      = gen_random_uuid()::text,
    leased_at        = now(),
    lease_expires_at = now() + interval '15 minutes',
    worker_id        = p_worker_id,
    updated_at       = now()
  from next_job
  where cq.id = next_job.id
  returning cq.* into leased_row;

  if leased_row.id is null then
    return;
  end if;

  return next leased_row;
end;
$$;

-- ── 權限 ────────────────────────────────────────────────────────

grant usage on schema crawler
  to postgres, anon, authenticated, service_role;

grant all on all tables in schema crawler
  to postgres, service_role;

grant all on all sequences in schema crawler
  to postgres, service_role;

grant execute on function crawler.lease_next_crawl_job(text)
  to postgres, service_role, anon, authenticated;

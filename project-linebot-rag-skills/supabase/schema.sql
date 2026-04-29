create extension if not exists vector;
create extension if not exists pg_trgm;
create extension if not exists unaccent;

create or replace function set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create table if not exists ai_skills (
  skill_id text primary key,
  name text not null,
  description text not null,
  category text not null,
  system_prompt text not null,
  use_when text[] default '{}',
  avoid_when text[] default '{}',
  output_style jsonb default '{}'::jsonb,
  default_temperature numeric default 0.4,
  default_top_p numeric default 0.9,
  version text default '0.1.0',
  enabled boolean default true,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists private_knowledge (
  id uuid primary key default gen_random_uuid(),
  source_id text,
  source_type text not null default 'markdown',
  title text,
  content text not null,
  content_hash text not null unique,
  category text not null,
  tags text[] default '{}',
  metadata jsonb default '{}'::jsonb,
  embedding vector(1536),
  search_vector tsvector generated always as (
    to_tsvector('simple', coalesce(title, '') || ' ' || coalesce(content, ''))
  ) stored,
  knowledge_version integer default 1,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

create table if not exists line_messages (
  id uuid primary key default gen_random_uuid(),
  line_user_id text not null,
  direction text not null check (direction in ('inbound', 'outbound')),
  message_text text not null,
  skill_id text,
  router_result jsonb default '{}'::jsonb,
  rag_used boolean default false,
  created_at timestamptz default now()
);

create table if not exists retrieval_logs (
  id uuid primary key default gen_random_uuid(),
  line_user_id text,
  query text not null,
  skill_id text,
  category_filter text[],
  retrieved_ids uuid[],
  scores jsonb default '{}'::jsonb,
  created_at timestamptz default now()
);

create table if not exists prompt_cache (
  id uuid primary key default gen_random_uuid(),
  cache_key text unique not null,
  user_input text not null,
  skill_id text,
  knowledge_version integer,
  response_text text not null,
  created_at timestamptz default now()
);

create index if not exists private_knowledge_embedding_idx
on private_knowledge
using ivfflat (embedding vector_cosine_ops)
with (lists = 100);

create index if not exists private_knowledge_search_idx
on private_knowledge
using gin(search_vector);

create index if not exists private_knowledge_category_idx
on private_knowledge(category);

create index if not exists line_messages_user_created_idx
on line_messages(line_user_id, created_at desc);

create index if not exists retrieval_logs_user_created_idx
on retrieval_logs(line_user_id, created_at desc);

drop trigger if exists ai_skills_set_updated_at on ai_skills;
create trigger ai_skills_set_updated_at
before update on ai_skills
for each row
execute function set_updated_at();

drop trigger if exists private_knowledge_set_updated_at on private_knowledge;
create trigger private_knowledge_set_updated_at
before update on private_knowledge
for each row
execute function set_updated_at();

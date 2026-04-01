-- migration: lease_next_crawl_job 加入 source_id 過濾
--
-- 原版 RPC 只依 priority 搶全局最高優先任務，
-- 多 source 並存時 worker 可能搶到錯 source，
-- 需要應用層 retry / release 補洞。
--
-- 這版改成：
--   lease_next_crawl_job(p_source_id, p_worker_id)
-- DB 直接過濾 source_id，消除應用層重試邏輯。
--
-- 舊簽名 lease_next_crawl_job(p_worker_id) 同時保留，
-- 避免破壞既有呼叫端（回傳全局最高優先任務，不過濾 source）。

create or replace function crawler.lease_next_crawl_job(
  p_source_id uuid,
  p_worker_id text
)
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
    where cq.source_id   = p_source_id
      and cq.status      = 'pending'
      and cq.scheduled_at <= now()
      and cq.retry_count  < cq.max_retries
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

grant execute on function crawler.lease_next_crawl_job(uuid, text)
  to postgres, service_role, anon, authenticated;

-- ============================================================
-- 010: pg_cron — 排程任務
-- ============================================================
-- pg_cron = PostgreSQL 原生的 cron scheduler
-- 直接在 DB 裡定義排程，不需要外部 cron server
--
-- 教學重點：
--   - cron 表達式：分 時 日 月 週
--   - cron.schedule() 建立 / cron.unschedule() 移除
--   - cron.job 查看所有排程 / cron.job_run_details 查看執行歷史
--   - Supabase Dashboard → Database → Extensions → pg_cron 也可管理
-- ============================================================


-- ============================================================
-- 1. EXTENSION
-- ============================================================
-- pg_cron 在 Supabase 已預裝，但需要啟用
CREATE EXTENSION IF NOT EXISTS pg_cron;

-- pg_cron 需要在 postgres database 的 cron schema 執行
-- Supabase 已處理好這部分，直接用 cron.schedule() 即可


-- ============================================================
-- 2. ANALYTICS — 每日快照刷新
-- ============================================================

-- 2a. 每天 00:15 UTC 刷新所有快照 + MATVIEW
SELECT cron.schedule(
  'analytics-daily-refresh',
  '15 0 * * *',
  $$SELECT analytics.refresh_all()$$
);

-- 2b. 每小時刷新 MATVIEW（即時儀表板用）
SELECT cron.schedule(
  'analytics-hourly-matview',
  '0 * * * *',
  $$
    REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.mv_system_health;
    REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.mv_product_ranking;
    REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.mv_source_health;
  $$
);


-- ============================================================
-- 3. CRAWLER — 排程爬取 + 佇列清理
-- ============================================================

-- 3a. 每小時：掃描 enabled sources，產生 crawl_queue 任務
-- 根據 sources.schedule_cron 判斷是否該執行
SELECT cron.schedule(
  'crawler-schedule-runs',
  '0 * * * *',
  $$
    INSERT INTO crawler.crawl_queue (project_id, source_id, url, page_type, priority)
    SELECT s.project_id, s.id, s.crawler_url, 'list', 200
    FROM crawler.sources s
    WHERE s.is_enabled = TRUE
      AND s.crawler_url IS NOT NULL
      AND (
        s.last_run_at IS NULL
        OR s.last_run_at < NOW() - INTERVAL '1 hour'
      )
    ON CONFLICT (source_id, url) WHERE status = 'pending' DO NOTHING
  $$
);

-- 3b. 每天 03:00：清理過期的 dead / failed queue items（超過 7 天）
SELECT cron.schedule(
  'crawler-queue-cleanup',
  '0 3 * * *',
  $$
    DELETE FROM crawler.crawl_queue
    WHERE status IN ('dead', 'failed', 'done', 'skipped')
      AND created_at < NOW() - INTERVAL '7 days'
  $$
);

-- 3c. 每 5 分鐘：回收過期的 lease（worker 掛掉的情況）
SELECT cron.schedule(
  'crawler-lease-recovery',
  '*/5 * * * *',
  $$
    UPDATE crawler.crawl_queue
    SET status = 'pending',
        lease_token = NULL,
        leased_at = NULL,
        lease_expires_at = NULL,
        worker_id = NULL,
        retry_count = retry_count + 1
    WHERE status = 'leased'
      AND lease_expires_at < NOW()
      AND retry_count < max_retries
  $$
);

-- 3d. 每 5 分鐘：超過 max_retries 的任務標記為 dead
SELECT cron.schedule(
  'crawler-dead-letter',
  '*/5 * * * *',
  $$
    UPDATE crawler.crawl_queue
    SET status = 'dead'
    WHERE status IN ('pending', 'leased')
      AND retry_count >= max_retries
  $$
);


-- ============================================================
-- 4. SHOP — 商務邏輯排程
-- ============================================================

-- 4a. 每天 00:30：停用過期優惠券
SELECT cron.schedule(
  'shop-expire-coupons',
  '30 0 * * *',
  $$
    UPDATE shop.coupons
    SET is_active = FALSE
    WHERE is_active = TRUE
      AND expires_at IS NOT NULL
      AND expires_at < NOW()
  $$
);

-- 4b. 每天 01:00：清理超時未付款訂單（24 小時未付款 → cancelled）
SELECT cron.schedule(
  'shop-cancel-stale-orders',
  '0 1 * * *',
  $$
    UPDATE shop.orders
    SET status = 'cancelled',
        updated_at = NOW()
    WHERE status = 'pending'
      AND created_at < NOW() - INTERVAL '24 hours'
      AND deleted_at IS NULL
  $$
);

-- 4c. 每天 02:00：更新商品評價統計快取（如果有）
-- 範例：把 avg_rating 寫入 products.metadata 快取
SELECT cron.schedule(
  'shop-update-review-stats',
  '0 2 * * *',
  $$
    UPDATE shop.products p
    SET metadata = p.metadata || jsonb_build_object(
      'avg_rating', sub.avg_rating,
      'review_count', sub.review_count,
      'rating_updated_at', NOW()
    )
    FROM (
      SELECT product_id,
        round(avg(rating)::NUMERIC, 1) AS avg_rating,
        count(*) AS review_count
      FROM shop.reviews
      WHERE is_visible = TRUE
      GROUP BY product_id
    ) sub
    WHERE p.id = sub.product_id
      AND p.deleted_at IS NULL
  $$
);


-- ============================================================
-- 5. RAG — 維護任務
-- ============================================================

-- 5a. 每天 04:00：標記 stale 文件（content_hash 不一致）
SELECT cron.schedule(
  'rag-detect-stale',
  '0 4 * * *',
  $$
    UPDATE rag.documents
    SET process_status = 'stale'
    WHERE process_status = 'ready'
      AND content_hash IS NOT NULL
      AND content_hash != md5(coalesce(content_text, ''))
  $$
);

-- 5b. 每週日 05:00：清理孤兒 chunks（document 已刪除）
SELECT cron.schedule(
  'rag-cleanup-orphan-chunks',
  '0 5 * * 0',
  $$
    DELETE FROM rag.chunks c
    WHERE NOT EXISTS (
      SELECT 1 FROM rag.documents d WHERE d.id = c.document_id
    )
  $$
);

-- 5c. 每天 04:30：重新計算 documents.chunk_count
SELECT cron.schedule(
  'rag-sync-chunk-count',
  '30 4 * * *',
  $$
    UPDATE rag.documents d
    SET chunk_count = sub.actual_count
    FROM (
      SELECT document_id, count(*) AS actual_count
      FROM rag.chunks
      GROUP BY document_id
    ) sub
    WHERE d.id = sub.document_id
      AND d.chunk_count != sub.actual_count
  $$
);


-- ============================================================
-- 6. SYSTEM — 全域維護
-- ============================================================

-- 6a. 每天 06:00：清理 analytics.events 超過 90 天的舊事件
SELECT cron.schedule(
  'analytics-events-retention',
  '0 6 * * *',
  $$
    DELETE FROM analytics.events
    WHERE created_at < NOW() - INTERVAL '90 days'
  $$
);

-- 6b. 每天 06:30：清理 pg_net 的舊 response 紀錄
SELECT cron.schedule(
  'pgnet-cleanup',
  '30 6 * * *',
  $$
    DELETE FROM net._http_response
    WHERE created < NOW() - INTERVAL '7 days'
  $$
);

-- 6c. 每天 06:45：清理 cron 執行歷史（保留 30 天）
SELECT cron.schedule(
  'cron-history-cleanup',
  '45 6 * * *',
  $$
    DELETE FROM cron.job_run_details
    WHERE end_time < NOW() - INTERVAL '30 days'
  $$
);


-- ============================================================
-- 7. 管理與監控
-- ============================================================

-- 查看所有排程
-- SELECT jobid, jobname, schedule, command FROM cron.job ORDER BY jobname;

-- 查看最近執行紀錄
-- SELECT j.jobname, d.status, d.return_message,
--   d.start_time, d.end_time,
--   d.end_time - d.start_time AS duration
-- FROM cron.job_run_details d
-- JOIN cron.job j ON j.jobid = d.jobid
-- ORDER BY d.start_time DESC
-- LIMIT 30;

-- 手動執行一次排程（測試用）
-- SELECT cron.schedule('test-run', '* * * * *',
--   $$SELECT analytics.refresh_all()$$);
-- -- 等一分鐘後確認 → 再移除
-- SELECT cron.unschedule('test-run');

-- 移除排程
-- SELECT cron.unschedule('analytics-daily-refresh');

-- 暫停排程（改為永不執行的 cron）
-- UPDATE cron.job SET schedule = '0 0 30 2 *'   -- 2/30 不存在
-- WHERE jobname = 'crawler-schedule-runs';

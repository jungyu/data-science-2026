-- ============================================================
-- Analytics Schema  v1.0
-- Cross-Domain Observability & Business Intelligence
-- ============================================================
--
-- Design principles:
--   - analytics schema = 跨 shop / crawler / rag 的觀測層
--   - 不存原始資料，只存聚合、事件、快照
--   - 大量 function 示範 SQL 分析技巧（教學重點）
--   - Materialized View + pg_cron 刷新模式
--   - Append-only event log（不 UPDATE、不 DELETE）
--   - TEXT + ULID primary keys（與其他 schema 一致）
--   - RLS + GRANT + service_role（後端分析為主）
--
-- Prerequisites:
--   - shop, crawler, rag schema 已建立
--   - pg_cron extension（用於排程刷新 materialized view）
--
-- Execution order:
--   tables → indexes → materialized views → analytics functions →
--   triggers → RLS → policies → grants
-- NOTE: schema/extensions/ULID 已移至 001_extensions.sql
-- ============================================================


-- NOTE: schema, extensions, generate_ulid() 已移至 001_extensions.sql


-- ============================================================
-- 2. TABLES — Event Log（統一事件匯流排）
-- ============================================================
-- 所有 schema 的關鍵事件匯入此表
-- Append-only：永遠不 UPDATE / DELETE，只 INSERT
-- 用 trigger 或 application layer 推送

CREATE TABLE IF NOT EXISTS analytics.events (
  id            TEXT PRIMARY KEY DEFAULT public.generate_ulid(),
  schema_name   TEXT        NOT NULL,
  event_type    TEXT        NOT NULL,
  entity_type   TEXT        NOT NULL,
  entity_id     TEXT,
  actor_id      TEXT,
  payload       JSONB       NOT NULL DEFAULT '{}'::JSONB,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  -- schema_name: 允許已知 schema + 未來擴充
  CONSTRAINT ck_events_schema
    CHECK (schema_name ~ '^[a-z_]+$'),
  -- event_type: 格式為 entity.action（例如 order.created）
  CONSTRAINT ck_events_type
    CHECK (event_type ~ '^[a-z_]+\.[a-z_]+$')
);

CREATE INDEX IF NOT EXISTS idx_events_schema_type
  ON analytics.events(schema_name, event_type, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_events_entity
  ON analytics.events(entity_type, entity_id)
  WHERE entity_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_events_created
  ON analytics.events(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_events_payload
  ON analytics.events USING GIN(payload);


-- ============================================================
-- 3. TABLES — Daily Snapshots（每日聚合快照）
-- ============================================================
-- 為什麼不用 Materialized View 就好？
-- 因為 MATVIEW REFRESH 會整張重建，歷史資料會丟失。
-- Snapshot table 保留每一天的快照，可做趨勢分析。

CREATE TABLE IF NOT EXISTS analytics.daily_shop_stats (
  id              TEXT PRIMARY KEY DEFAULT public.generate_ulid(),
  stat_date       DATE        NOT NULL,
  total_orders    INTEGER     NOT NULL DEFAULT 0,
  total_revenue   NUMERIC(14,2) NOT NULL DEFAULT 0,
  avg_order_value NUMERIC(12,2) NOT NULL DEFAULT 0,
  total_items_sold INTEGER    NOT NULL DEFAULT 0,
  new_customers   INTEGER     NOT NULL DEFAULT 0,
  returning_orders INTEGER    NOT NULL DEFAULT 0,
  top_product_id  TEXT,
  top_product_revenue NUMERIC(12,2),
  metadata        JSONB       NOT NULL DEFAULT '{}'::JSONB,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  CONSTRAINT uq_daily_shop_stats_date UNIQUE (stat_date)
);

CREATE TABLE IF NOT EXISTS analytics.daily_crawler_stats (
  id                  TEXT PRIMARY KEY DEFAULT public.generate_ulid(),
  stat_date           DATE        NOT NULL,
  total_runs          INTEGER     NOT NULL DEFAULT 0,
  successful_runs     INTEGER     NOT NULL DEFAULT 0,
  failed_runs         INTEGER     NOT NULL DEFAULT 0,
  pages_fetched       INTEGER     NOT NULL DEFAULT 0,
  articles_extracted  INTEGER     NOT NULL DEFAULT 0,
  error_count         INTEGER     NOT NULL DEFAULT 0,
  avg_run_duration_s  NUMERIC(10,2),
  busiest_source_id   TEXT,
  metadata            JSONB       NOT NULL DEFAULT '{}'::JSONB,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  CONSTRAINT uq_daily_crawler_stats_date UNIQUE (stat_date)
);

CREATE TABLE IF NOT EXISTS analytics.daily_rag_stats (
  id                    TEXT PRIMARY KEY DEFAULT public.generate_ulid(),
  stat_date             DATE        NOT NULL,
  total_queries         INTEGER     NOT NULL DEFAULT 0,
  total_documents       INTEGER     NOT NULL DEFAULT 0,
  new_documents         INTEGER     NOT NULL DEFAULT 0,
  chunks_embedded       INTEGER     NOT NULL DEFAULT 0,
  avg_faithfulness      FLOAT8,
  avg_answer_relevance  FLOAT8,
  avg_context_precision FLOAT8,
  total_prompt_tokens   BIGINT      NOT NULL DEFAULT 0,
  total_completion_tokens BIGINT    NOT NULL DEFAULT 0,
  metadata              JSONB       NOT NULL DEFAULT '{}'::JSONB,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  CONSTRAINT uq_daily_rag_stats_date UNIQUE (stat_date)
);


-- ============================================================
-- 4. TABLES — Funnel Events（漏斗追蹤）
-- ============================================================

CREATE TABLE IF NOT EXISTS analytics.funnel_events (
  id          TEXT PRIMARY KEY DEFAULT public.generate_ulid(),
  session_id  TEXT        NOT NULL,
  customer_id TEXT,
  step        TEXT        NOT NULL,
  step_order  SMALLINT    NOT NULL,
  product_id  TEXT,
  order_id    TEXT,
  metadata    JSONB       NOT NULL DEFAULT '{}'::JSONB,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  CONSTRAINT ck_funnel_step
    CHECK (step IN ('view', 'add_to_cart', 'checkout', 'payment', 'completed'))
);

CREATE INDEX IF NOT EXISTS idx_funnel_session
  ON analytics.funnel_events(session_id, step_order);
CREATE INDEX IF NOT EXISTS idx_funnel_customer
  ON analytics.funnel_events(customer_id)
  WHERE customer_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_funnel_created
  ON analytics.funnel_events(created_at DESC);


-- ============================================================
-- 5. MATERIALIZED VIEWS — 即時儀表板用（跨 schema JOIN 示範）
-- ============================================================
-- 教學重點：Materialized View 是「預先計算的查詢快照」
-- 用 REFRESH MATERIALIZED VIEW CONCURRENTLY 刷新（不鎖讀）
-- 需要 UNIQUE INDEX 才能用 CONCURRENTLY

-- 5a. 跨域健康總覽
CREATE MATERIALIZED VIEW IF NOT EXISTS analytics.mv_system_health AS
  SELECT
    NOW() AS snapshot_at,
    -- shop
    (SELECT count(*) FROM shop.orders
     WHERE created_at >= CURRENT_DATE) AS today_orders,
    (SELECT coalesce(sum(total), 0) FROM shop.orders
     WHERE created_at >= CURRENT_DATE AND status != 'cancelled') AS today_revenue,
    -- crawler
    (SELECT count(*) FROM crawler.crawl_runs
     WHERE created_at >= CURRENT_DATE) AS today_crawl_runs,
    (SELECT count(*) FROM crawler.crawl_runs
     WHERE created_at >= CURRENT_DATE AND run_status = 'failed') AS today_failed_runs,
    -- rag
    (SELECT count(*) FROM rag.query_logs
     WHERE created_at >= CURRENT_DATE) AS today_rag_queries,
    (SELECT avg(eval_faithfulness) FROM rag.query_logs
     WHERE created_at >= CURRENT_DATE
       AND eval_faithfulness IS NOT NULL) AS today_avg_faithfulness
WITH NO DATA;

CREATE UNIQUE INDEX IF NOT EXISTS uq_mv_system_health
  ON analytics.mv_system_health(snapshot_at);

-- 5b. 商品銷售排行（rolling 30 天）
CREATE MATERIALIZED VIEW IF NOT EXISTS analytics.mv_product_ranking AS
  SELECT
    p.id AS product_id,
    p.title,
    p.price,
    count(DISTINCT oi.order_id) AS order_count,
    coalesce(sum(oi.quantity), 0) AS total_sold,
    coalesce(sum(oi.net_revenue), 0) AS total_revenue,
    avg(r.rating) AS avg_rating,
    count(DISTINCT r.id) AS review_count
  FROM shop.products p
  LEFT JOIN shop.order_items oi ON oi.product_id = p.id
    AND oi.created_at >= CURRENT_DATE - INTERVAL '30 days'
  LEFT JOIN shop.reviews r ON r.product_id = p.id AND r.is_visible = TRUE
  WHERE p.status = 'publish' AND p.deleted_at IS NULL
  GROUP BY p.id, p.title, p.price
WITH NO DATA;

CREATE UNIQUE INDEX IF NOT EXISTS uq_mv_product_ranking
  ON analytics.mv_product_ranking(product_id);

-- 5c. Crawler 來源健康度
CREATE MATERIALIZED VIEW IF NOT EXISTS analytics.mv_source_health AS
  SELECT
    s.id AS source_id,
    s.name AS source_name,
    s.code AS source_code,
    count(cr.id) AS total_runs_30d,
    count(cr.id) FILTER (WHERE cr.run_status = 'success') AS success_runs,
    count(cr.id) FILTER (WHERE cr.run_status = 'failed') AS failed_runs,
    coalesce(sum(cr.articles_extracted), 0) AS articles_30d,
    coalesce(sum(cr.error_count), 0) AS errors_30d,
    max(cr.finished_at) AS last_run_at,
    CASE
      WHEN count(cr.id) = 0 THEN 0
      ELSE round(
        count(cr.id) FILTER (WHERE cr.run_status = 'success')::NUMERIC
        / count(cr.id) * 100, 1
      )
    END AS success_rate_pct
  FROM crawler.sources s
  LEFT JOIN crawler.crawl_runs cr ON cr.source_id = s.id
    AND cr.created_at >= CURRENT_DATE - INTERVAL '30 days'
  WHERE s.is_enabled = TRUE
  GROUP BY s.id, s.name, s.code
WITH NO DATA;

CREATE UNIQUE INDEX IF NOT EXISTS uq_mv_source_health
  ON analytics.mv_source_health(source_id);

-- 初始化 MATVIEW（即使無資料也要 populate，否則 SELECT 會報錯）
REFRESH MATERIALIZED VIEW analytics.mv_system_health;
REFRESH MATERIALIZED VIEW analytics.mv_product_ranking;
REFRESH MATERIALIZED VIEW analytics.mv_source_health;


-- ============================================================
-- 6. FUNCTIONS — Event Helpers
-- ============================================================

-- 6a. 通用事件寫入（供其他 schema 的 trigger 呼叫）
CREATE OR REPLACE FUNCTION analytics.log_event(
  p_schema    TEXT,
  p_type      TEXT,
  p_entity    TEXT,
  p_entity_id TEXT DEFAULT NULL,
  p_actor_id  TEXT DEFAULT NULL,
  p_payload   JSONB DEFAULT '{}'::JSONB
)
RETURNS TEXT
LANGUAGE SQL
SECURITY DEFINER
SET search_path = analytics
AS $$
  INSERT INTO analytics.events (schema_name, event_type, entity_type, entity_id, actor_id, payload)
  VALUES (p_schema, p_type, p_entity, p_entity_id, p_actor_id, p_payload)
  RETURNING id;
$$;

-- 6b. 事件計數（指定時間窗口）
CREATE OR REPLACE FUNCTION analytics.count_events(
  p_schema     TEXT,
  p_event_type TEXT,
  p_since      TIMESTAMPTZ DEFAULT CURRENT_DATE::TIMESTAMPTZ,
  p_until      TIMESTAMPTZ DEFAULT NOW()
)
RETURNS BIGINT
LANGUAGE SQL
STABLE
SECURITY DEFINER
SET search_path = analytics
AS $$
  SELECT count(*)
  FROM analytics.events
  WHERE schema_name = p_schema
    AND event_type  = p_event_type
    AND created_at >= p_since
    AND created_at <  p_until;
$$;


-- ============================================================
-- 7. FUNCTIONS — Time-Series Aggregation（時間序列聚合）
-- ============================================================
-- 教學重點：date_trunc + generate_series 產生完整時間軸（含零值日期）

-- 7a. 通用事件時間序列（任意 granularity）
CREATE OR REPLACE FUNCTION analytics.event_time_series(
  p_schema      TEXT,
  p_event_type  TEXT,
  p_granularity TEXT DEFAULT 'day',    -- 'hour', 'day', 'week', 'month'
  p_days_back   INTEGER DEFAULT 30
)
RETURNS TABLE (
  bucket     TIMESTAMPTZ,
  event_count BIGINT
)
LANGUAGE SQL
STABLE
SECURITY DEFINER
SET search_path = analytics
AS $$
  WITH series AS (
    SELECT generate_series(
      date_trunc(p_granularity, NOW() - (p_days_back || ' days')::INTERVAL),
      date_trunc(p_granularity, NOW()),
      ('1 ' || p_granularity)::INTERVAL
    ) AS bucket
  ),
  counts AS (
    SELECT
      date_trunc(p_granularity, created_at) AS bucket,
      count(*) AS cnt
    FROM analytics.events
    WHERE schema_name = p_schema
      AND event_type  = p_event_type
      AND created_at >= NOW() - (p_days_back || ' days')::INTERVAL
    GROUP BY 1
  )
  SELECT s.bucket, coalesce(c.cnt, 0) AS event_count
  FROM series s
  LEFT JOIN counts c ON c.bucket = s.bucket
  ORDER BY s.bucket;
$$;

-- 7b. Shop 營收時間序列（跨 schema 查詢示範）
CREATE OR REPLACE FUNCTION analytics.revenue_time_series(
  p_granularity TEXT DEFAULT 'day',
  p_days_back   INTEGER DEFAULT 30
)
RETURNS TABLE (
  bucket        TIMESTAMPTZ,
  order_count   BIGINT,
  total_revenue NUMERIC,
  avg_order_value NUMERIC
)
LANGUAGE SQL
STABLE
SECURITY DEFINER
SET search_path = analytics
AS $$
  WITH series AS (
    SELECT generate_series(
      date_trunc(p_granularity, NOW() - (p_days_back || ' days')::INTERVAL),
      date_trunc(p_granularity, NOW()),
      ('1 ' || p_granularity)::INTERVAL
    ) AS bucket
  ),
  agg AS (
    SELECT
      date_trunc(p_granularity, created_at) AS bucket,
      count(*)        AS order_count,
      sum(total)      AS total_revenue,
      avg(total)      AS avg_order_value
    FROM shop.orders
    WHERE status NOT IN ('cancelled', 'refunded')
      AND deleted_at IS NULL
      AND created_at >= NOW() - (p_days_back || ' days')::INTERVAL
    GROUP BY 1
  )
  SELECT
    s.bucket,
    coalesce(a.order_count, 0),
    coalesce(a.total_revenue, 0),
    coalesce(a.avg_order_value, 0)
  FROM series s
  LEFT JOIN agg a ON a.bucket = s.bucket
  ORDER BY s.bucket;
$$;


-- ============================================================
-- 8. FUNCTIONS — Funnel Analysis（漏斗分析）
-- ============================================================
-- 教學重點：window function + conditional aggregation

-- 8a. 漏斗轉換率
CREATE OR REPLACE FUNCTION analytics.funnel_conversion(
  p_days_back INTEGER DEFAULT 7
)
RETURNS TABLE (
  step           TEXT,
  step_order     SMALLINT,
  sessions       BIGINT,
  conversion_pct NUMERIC
)
LANGUAGE SQL
STABLE
SECURITY DEFINER
SET search_path = analytics
AS $$
  WITH step_counts AS (
    SELECT
      step,
      step_order,
      count(DISTINCT session_id) AS sessions
    FROM analytics.funnel_events
    WHERE created_at >= NOW() - (p_days_back || ' days')::INTERVAL
    GROUP BY step, step_order
  ),
  first_step AS (
    SELECT sessions FROM step_counts WHERE step_order = 1
  )
  SELECT
    sc.step,
    sc.step_order,
    sc.sessions,
    CASE
      WHEN fs.sessions = 0 THEN 0
      ELSE round(sc.sessions::NUMERIC / fs.sessions * 100, 2)
    END AS conversion_pct
  FROM step_counts sc
  CROSS JOIN first_step fs
  ORDER BY sc.step_order;
$$;

-- 8b. 漏斗每步流失率（step-over-step）
CREATE OR REPLACE FUNCTION analytics.funnel_dropoff(
  p_days_back INTEGER DEFAULT 7
)
RETURNS TABLE (
  step            TEXT,
  step_order      SMALLINT,
  sessions        BIGINT,
  prev_sessions   BIGINT,
  dropoff_pct     NUMERIC
)
LANGUAGE SQL
STABLE
SECURITY DEFINER
SET search_path = analytics
AS $$
  WITH step_counts AS (
    SELECT
      step,
      step_order,
      count(DISTINCT session_id) AS sessions
    FROM analytics.funnel_events
    WHERE created_at >= NOW() - (p_days_back || ' days')::INTERVAL
    GROUP BY step, step_order
  )
  SELECT
    sc.step,
    sc.step_order,
    sc.sessions,
    lag(sc.sessions) OVER (ORDER BY sc.step_order) AS prev_sessions,
    CASE
      WHEN lag(sc.sessions) OVER (ORDER BY sc.step_order) IS NULL THEN 0
      WHEN lag(sc.sessions) OVER (ORDER BY sc.step_order) = 0 THEN 0
      ELSE round(
        (1 - sc.sessions::NUMERIC / lag(sc.sessions) OVER (ORDER BY sc.step_order)) * 100,
        2
      )
    END AS dropoff_pct
  FROM step_counts sc
  ORDER BY sc.step_order;
$$;


-- ============================================================
-- 9. FUNCTIONS — Cohort Analysis（世代分析）
-- ============================================================
-- 教學重點：CTE + date_trunc 分群 + crosstab 思維

-- 9a. 月份 cohort 留存率
CREATE OR REPLACE FUNCTION analytics.monthly_cohort_retention(
  p_months_back INTEGER DEFAULT 6
)
RETURNS TABLE (
  cohort_month   DATE,
  months_since   INTEGER,
  cohort_size    BIGINT,
  active_users   BIGINT,
  retention_pct  NUMERIC
)
LANGUAGE SQL
STABLE
SECURITY DEFINER
SET search_path = analytics
AS $$
  WITH first_order AS (
    -- 每位顧客的首次下單月份 = cohort
    SELECT
      customer_id,
      date_trunc('month', min(created_at))::DATE AS cohort_month
    FROM shop.orders
    WHERE deleted_at IS NULL
      AND created_at >= (date_trunc('month', NOW()) - (p_months_back || ' months')::INTERVAL)
    GROUP BY customer_id
  ),
  activity AS (
    -- 每位顧客每月是否有活動
    SELECT DISTINCT
      o.customer_id,
      fo.cohort_month,
      date_trunc('month', o.created_at)::DATE AS activity_month
    FROM shop.orders o
    JOIN first_order fo ON fo.customer_id = o.customer_id
    WHERE o.deleted_at IS NULL
  )
  SELECT
    a.cohort_month,
    (EXTRACT(YEAR FROM age(a.activity_month, a.cohort_month)) * 12
     + EXTRACT(MONTH FROM age(a.activity_month, a.cohort_month)))::INTEGER AS months_since,
    count(DISTINCT fo2.customer_id) AS cohort_size,
    count(DISTINCT a.customer_id)   AS active_users,
    round(
      count(DISTINCT a.customer_id)::NUMERIC
      / nullif(count(DISTINCT fo2.customer_id), 0) * 100,
      2
    ) AS retention_pct
  FROM activity a
  JOIN first_order fo2 ON fo2.cohort_month = a.cohort_month
  GROUP BY a.cohort_month, a.activity_month
  ORDER BY a.cohort_month, months_since;
$$;


-- ============================================================
-- 10. FUNCTIONS — RAG Quality Monitoring（RAG 品質監控）
-- ============================================================

-- 10a. RAG 評估指標趨勢（週維度）
CREATE OR REPLACE FUNCTION analytics.rag_quality_trend(
  p_collection_id TEXT DEFAULT NULL,
  p_weeks_back    INTEGER DEFAULT 12
)
RETURNS TABLE (
  week_start          DATE,
  query_count         BIGINT,
  avg_faithfulness    FLOAT8,
  avg_relevance       FLOAT8,
  avg_context_recall  FLOAT8,
  avg_context_precision FLOAT8,
  rated_count         BIGINT,
  avg_user_rating     FLOAT8
)
LANGUAGE SQL
STABLE
SECURITY DEFINER
SET search_path = analytics
AS $$
  SELECT
    date_trunc('week', ql.created_at)::DATE AS week_start,
    count(*)                                AS query_count,
    avg(ql.eval_faithfulness)               AS avg_faithfulness,
    avg(ql.eval_answer_relevance)           AS avg_relevance,
    avg(ql.eval_context_recall)             AS avg_context_recall,
    avg(ql.eval_context_precision)          AS avg_context_precision,
    count(ql.user_rating)                   AS rated_count,
    avg(ql.user_rating)                     AS avg_user_rating
  FROM rag.query_logs ql
  WHERE ql.created_at >= NOW() - (p_weeks_back || ' weeks')::INTERVAL
    AND (p_collection_id IS NULL OR ql.collection_id = p_collection_id)
  GROUP BY 1
  ORDER BY 1;
$$;

-- 10b. 低品質 Chunk 排行（經常被檢索但低分）
CREATE OR REPLACE FUNCTION analytics.low_quality_chunks(
  p_collection_id TEXT,
  p_min_hits      INTEGER DEFAULT 3,
  p_limit         INTEGER DEFAULT 20
)
RETURNS TABLE (
  chunk_id      TEXT,
  document_id   TEXT,
  content_preview TEXT,
  hit_count     BIGINT,
  avg_score     FLOAT8,
  avg_rank      FLOAT8,
  avg_query_faithfulness FLOAT8
)
LANGUAGE SQL
STABLE
SECURITY DEFINER
SET search_path = analytics
AS $$
  SELECT
    r.chunk_id,
    c.document_id,
    left(c.content, 120) AS content_preview,
    count(*)             AS hit_count,
    avg(r.score)         AS avg_score,
    avg(r.rank)          AS avg_rank,
    avg(ql.eval_faithfulness) AS avg_query_faithfulness
  FROM rag.query_log_results r
  JOIN rag.chunks c ON c.id = r.chunk_id
  JOIN rag.query_logs ql ON ql.id = r.query_id
  WHERE c.collection_id = p_collection_id
  GROUP BY r.chunk_id, c.document_id, c.content
  HAVING count(*) >= p_min_hits
  ORDER BY avg(r.score) ASC
  LIMIT p_limit;
$$;

-- 10c. RAG token 消耗統計
CREATE OR REPLACE FUNCTION analytics.rag_token_usage(
  p_granularity TEXT DEFAULT 'day',
  p_days_back   INTEGER DEFAULT 30
)
RETURNS TABLE (
  bucket              TIMESTAMPTZ,
  query_count         BIGINT,
  total_prompt_tokens BIGINT,
  total_completion_tokens BIGINT,
  total_tokens        BIGINT,
  avg_tokens_per_query NUMERIC
)
LANGUAGE SQL
STABLE
SECURITY DEFINER
SET search_path = analytics
AS $$
  WITH series AS (
    SELECT generate_series(
      date_trunc(p_granularity, NOW() - (p_days_back || ' days')::INTERVAL),
      date_trunc(p_granularity, NOW()),
      ('1 ' || p_granularity)::INTERVAL
    ) AS bucket
  ),
  agg AS (
    SELECT
      date_trunc(p_granularity, created_at) AS bucket,
      count(*)                   AS query_count,
      coalesce(sum(prompt_tokens), 0)     AS total_prompt_tokens,
      coalesce(sum(completion_tokens), 0) AS total_completion_tokens,
      coalesce(sum(prompt_tokens) + sum(completion_tokens), 0) AS total_tokens
    FROM rag.query_logs
    WHERE created_at >= NOW() - (p_days_back || ' days')::INTERVAL
    GROUP BY 1
  )
  SELECT
    s.bucket,
    coalesce(a.query_count, 0),
    coalesce(a.total_prompt_tokens, 0),
    coalesce(a.total_completion_tokens, 0),
    coalesce(a.total_tokens, 0),
    CASE WHEN coalesce(a.query_count, 0) = 0 THEN 0
         ELSE round(a.total_tokens::NUMERIC / a.query_count, 1)
    END
  FROM series s
  LEFT JOIN agg a ON a.bucket = s.bucket
  ORDER BY s.bucket;
$$;


-- ============================================================
-- 11. FUNCTIONS — Crawler Monitoring（爬蟲健康監控）
-- ============================================================

-- 11a. 各來源成功率排行
CREATE OR REPLACE FUNCTION analytics.crawler_source_ranking(
  p_days_back INTEGER DEFAULT 30
)
RETURNS TABLE (
  source_id        TEXT,
  source_name      TEXT,
  total_runs       BIGINT,
  success_runs     BIGINT,
  success_rate_pct NUMERIC,
  total_articles   BIGINT,
  total_errors     BIGINT,
  avg_duration_s   NUMERIC,
  last_run_at      TIMESTAMPTZ
)
LANGUAGE SQL
STABLE
SECURITY DEFINER
SET search_path = analytics
AS $$
  SELECT
    s.id,
    s.name,
    count(cr.id)                                               AS total_runs,
    count(cr.id) FILTER (WHERE cr.run_status = 'success')      AS success_runs,
    CASE WHEN count(cr.id) = 0 THEN 0
         ELSE round(
           count(cr.id) FILTER (WHERE cr.run_status = 'success')::NUMERIC
           / count(cr.id) * 100, 1)
    END                                                         AS success_rate_pct,
    coalesce(sum(cr.articles_extracted), 0)                     AS total_articles,
    coalesce(sum(cr.error_count), 0)                            AS total_errors,
    round(avg(EXTRACT(EPOCH FROM (cr.finished_at - cr.started_at)))::NUMERIC, 1) AS avg_duration_s,
    max(cr.finished_at)                                         AS last_run_at
  FROM crawler.sources s
  LEFT JOIN crawler.crawl_runs cr ON cr.source_id = s.id
    AND cr.created_at >= NOW() - (p_days_back || ' days')::INTERVAL
  WHERE s.is_enabled = TRUE
  GROUP BY s.id, s.name
  ORDER BY success_rate_pct DESC, total_articles DESC;
$$;

-- 11b. 爬蟲佇列健康狀態
CREATE OR REPLACE FUNCTION analytics.crawler_queue_health()
RETURNS TABLE (
  status         TEXT,
  count          BIGINT,
  oldest_at      TIMESTAMPTZ,
  avg_retry      NUMERIC
)
LANGUAGE SQL
STABLE
SECURITY DEFINER
SET search_path = analytics
AS $$
  SELECT
    status,
    count(*)                 AS count,
    min(created_at)          AS oldest_at,
    round(avg(retry_count)::NUMERIC, 1) AS avg_retry
  FROM crawler.crawl_queue
  GROUP BY status
  ORDER BY count DESC;
$$;


-- ============================================================
-- 12. FUNCTIONS — Cross-Schema Dashboard（跨域儀表板）
-- ============================================================

-- 12a. 全域健康摘要（單一呼叫取得所有關鍵指標）
CREATE OR REPLACE FUNCTION analytics.system_dashboard(
  p_days_back INTEGER DEFAULT 1
)
RETURNS TABLE (
  domain          TEXT,
  metric          TEXT,
  value           NUMERIC,
  trend_vs_prev   NUMERIC
)
LANGUAGE SQL
STABLE
SECURITY DEFINER
SET search_path = analytics
AS $$
  WITH params AS (
    SELECT
      NOW() - (p_days_back || ' days')::INTERVAL AS since,
      NOW() - (p_days_back * 2 || ' days')::INTERVAL AS prev_since,
      NOW() - (p_days_back || ' days')::INTERVAL AS prev_until
  ),
  -- Shop metrics
  shop_current AS (
    SELECT count(*) AS orders, coalesce(sum(total), 0) AS revenue
    FROM shop.orders, params
    WHERE created_at >= params.since AND deleted_at IS NULL AND status != 'cancelled'
  ),
  shop_prev AS (
    SELECT count(*) AS orders, coalesce(sum(total), 0) AS revenue
    FROM shop.orders, params
    WHERE created_at >= params.prev_since AND created_at < params.prev_until
      AND deleted_at IS NULL AND status != 'cancelled'
  ),
  -- Crawler metrics
  crawler_current AS (
    SELECT count(*) AS runs,
      count(*) FILTER (WHERE run_status = 'failed') AS failed
    FROM crawler.crawl_runs, params
    WHERE created_at >= params.since
  ),
  crawler_prev AS (
    SELECT count(*) AS runs,
      count(*) FILTER (WHERE run_status = 'failed') AS failed
    FROM crawler.crawl_runs, params
    WHERE created_at >= params.prev_since AND created_at < params.prev_until
  ),
  -- RAG metrics
  rag_current AS (
    SELECT count(*) AS queries, avg(eval_faithfulness) AS faith
    FROM rag.query_logs, params
    WHERE created_at >= params.since
  ),
  rag_prev AS (
    SELECT count(*) AS queries, avg(eval_faithfulness) AS faith
    FROM rag.query_logs, params
    WHERE created_at >= params.prev_since AND created_at < params.prev_until
  )
  -- Combine
  SELECT 'shop'::TEXT, 'orders'::TEXT,
    sc.orders::NUMERIC, sc.orders::NUMERIC - sp.orders::NUMERIC
  FROM shop_current sc, shop_prev sp
  UNION ALL
  SELECT 'shop', 'revenue', sc.revenue, sc.revenue - sp.revenue
  FROM shop_current sc, shop_prev sp
  UNION ALL
  SELECT 'crawler', 'runs', cc.runs::NUMERIC, cc.runs::NUMERIC - cp.runs::NUMERIC
  FROM crawler_current cc, crawler_prev cp
  UNION ALL
  SELECT 'crawler', 'failed_runs', cc.failed::NUMERIC, cc.failed::NUMERIC - cp.failed::NUMERIC
  FROM crawler_current cc, crawler_prev cp
  UNION ALL
  SELECT 'rag', 'queries', rc.queries::NUMERIC, rc.queries::NUMERIC - rp.queries::NUMERIC
  FROM rag_current rc, rag_prev rp
  UNION ALL
  SELECT 'rag', 'avg_faithfulness',
    round(rc.faith::NUMERIC, 4),
    round((rc.faith - rp.faith)::NUMERIC, 4)
  FROM rag_current rc, rag_prev rp;
$$;


-- ============================================================
-- 13. FUNCTIONS — Anomaly Detection（異常偵測）
-- ============================================================
-- 教學重點：Z-score 統計方法、window function 進階用法

-- 13a. 通用 Z-score 異常偵測（基於事件數量）
CREATE OR REPLACE FUNCTION analytics.detect_anomalies(
  p_schema      TEXT,
  p_event_type  TEXT,
  p_days_back   INTEGER DEFAULT 30,
  p_z_threshold FLOAT8 DEFAULT 2.0
)
RETURNS TABLE (
  day          DATE,
  event_count  BIGINT,
  mean_count   FLOAT8,
  stddev_count FLOAT8,
  z_score      FLOAT8,
  is_anomaly   BOOLEAN
)
LANGUAGE SQL
STABLE
SECURITY DEFINER
SET search_path = analytics
AS $$
  WITH daily AS (
    SELECT
      created_at::DATE AS day,
      count(*) AS event_count
    FROM analytics.events
    WHERE schema_name = p_schema
      AND event_type  = p_event_type
      AND created_at >= NOW() - (p_days_back || ' days')::INTERVAL
    GROUP BY 1
  ),
  stats AS (
    SELECT
      avg(event_count) AS mean_count,
      stddev(event_count) AS stddev_count
    FROM daily
  )
  SELECT
    d.day,
    d.event_count,
    s.mean_count,
    s.stddev_count,
    CASE WHEN s.stddev_count = 0 THEN 0
         ELSE (d.event_count - s.mean_count) / s.stddev_count
    END AS z_score,
    CASE WHEN s.stddev_count = 0 THEN FALSE
         ELSE abs((d.event_count - s.mean_count) / s.stddev_count) > p_z_threshold
    END AS is_anomaly
  FROM daily d
  CROSS JOIN stats s
  ORDER BY d.day;
$$;


-- ============================================================
-- 14. FUNCTIONS — Data Freshness（資料新鮮度檢查）
-- ============================================================
-- 教學重點：information_schema 查詢、跨 schema 元資料

-- 14a. 各 schema 最新資料時間
CREATE OR REPLACE FUNCTION analytics.data_freshness()
RETURNS TABLE (
  schema_name      TEXT,
  entity           TEXT,
  latest_record_at TIMESTAMPTZ,
  minutes_ago      NUMERIC,
  is_stale         BOOLEAN
)
LANGUAGE SQL
STABLE
SECURITY DEFINER
SET search_path = analytics
AS $$
  -- Shop
  SELECT 'shop'::TEXT, 'orders'::TEXT,
    max(created_at), round(EXTRACT(EPOCH FROM (NOW() - max(created_at))) / 60, 1),
    max(created_at) < NOW() - INTERVAL '24 hours'
  FROM shop.orders
  UNION ALL
  -- Crawler
  SELECT 'crawler', 'crawl_runs',
    max(created_at), round(EXTRACT(EPOCH FROM (NOW() - max(created_at))) / 60, 1),
    max(created_at) < NOW() - INTERVAL '6 hours'
  FROM crawler.crawl_runs
  UNION ALL
  SELECT 'crawler', 'articles',
    max(created_at), round(EXTRACT(EPOCH FROM (NOW() - max(created_at))) / 60, 1),
    max(created_at) < NOW() - INTERVAL '12 hours'
  FROM crawler.articles
  UNION ALL
  -- RAG
  SELECT 'rag', 'documents',
    max(created_at), round(EXTRACT(EPOCH FROM (NOW() - max(created_at))) / 60, 1),
    max(created_at) < NOW() - INTERVAL '24 hours'
  FROM rag.documents
  UNION ALL
  SELECT 'rag', 'query_logs',
    max(created_at), round(EXTRACT(EPOCH FROM (NOW() - max(created_at))) / 60, 1),
    max(created_at) < NOW() - INTERVAL '24 hours'
  FROM rag.query_logs;
$$;


-- ============================================================
-- 15. FUNCTIONS — Snapshot Builders（每日快照產生器）
-- ============================================================
-- 由 pg_cron 每天凌晨呼叫，或手動執行
-- UPSERT pattern：重複執行同一天不會產生重複資料

-- 15a. 產生 Shop 每日快照
CREATE OR REPLACE FUNCTION analytics.build_daily_shop_stats(
  p_date DATE DEFAULT CURRENT_DATE - 1
)
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = analytics
AS $$
DECLARE
  v_top_product_id TEXT;
  v_top_product_rev NUMERIC;
BEGIN
  -- 找出當日最暢銷商品
  SELECT oi.product_id, sum(oi.net_revenue)
  INTO v_top_product_id, v_top_product_rev
  FROM shop.order_items oi
  JOIN shop.orders o ON o.id = oi.order_id
  WHERE o.created_at::DATE = p_date
    AND o.status NOT IN ('cancelled', 'refunded')
    AND o.deleted_at IS NULL
  GROUP BY oi.product_id
  ORDER BY sum(oi.net_revenue) DESC
  LIMIT 1;

  INSERT INTO analytics.daily_shop_stats (
    stat_date, total_orders, total_revenue, avg_order_value,
    total_items_sold, new_customers, returning_orders,
    top_product_id, top_product_revenue
  )
  SELECT
    p_date,
    count(*),
    coalesce(sum(total), 0),
    coalesce(avg(total), 0),
    coalesce(sum(num_items_sold), 0),
    (SELECT count(DISTINCT customer_id)
     FROM shop.orders
     WHERE created_at::DATE = p_date AND deleted_at IS NULL
       AND customer_id NOT IN (
         SELECT DISTINCT customer_id FROM shop.orders
         WHERE created_at::DATE < p_date AND deleted_at IS NULL
       )),
    count(*) FILTER (WHERE returning_customer = TRUE),
    v_top_product_id,
    v_top_product_rev
  FROM shop.orders
  WHERE created_at::DATE = p_date
    AND status NOT IN ('cancelled', 'refunded')
    AND deleted_at IS NULL
  ON CONFLICT (stat_date) DO UPDATE SET
    total_orders       = EXCLUDED.total_orders,
    total_revenue      = EXCLUDED.total_revenue,
    avg_order_value    = EXCLUDED.avg_order_value,
    total_items_sold   = EXCLUDED.total_items_sold,
    new_customers      = EXCLUDED.new_customers,
    returning_orders   = EXCLUDED.returning_orders,
    top_product_id     = EXCLUDED.top_product_id,
    top_product_revenue = EXCLUDED.top_product_revenue,
    created_at         = NOW();
END;
$$;

-- 15b. 產生 Crawler 每日快照
CREATE OR REPLACE FUNCTION analytics.build_daily_crawler_stats(
  p_date DATE DEFAULT CURRENT_DATE - 1
)
RETURNS VOID
LANGUAGE SQL
SECURITY DEFINER
SET search_path = analytics
AS $$
  INSERT INTO analytics.daily_crawler_stats (
    stat_date, total_runs, successful_runs, failed_runs,
    pages_fetched, articles_extracted, error_count,
    avg_run_duration_s, busiest_source_id
  )
  SELECT
    p_date,
    count(*),
    count(*) FILTER (WHERE run_status = 'success'),
    count(*) FILTER (WHERE run_status = 'failed'),
    coalesce(sum(pages_fetched), 0),
    coalesce(sum(articles_extracted), 0),
    coalesce(sum(error_count), 0),
    round(avg(EXTRACT(EPOCH FROM (finished_at - started_at)))::NUMERIC, 1),
    (SELECT source_id FROM crawler.crawl_runs
     WHERE created_at::DATE = p_date
     GROUP BY source_id ORDER BY count(*) DESC LIMIT 1)
  FROM crawler.crawl_runs
  WHERE created_at::DATE = p_date
  ON CONFLICT (stat_date) DO UPDATE SET
    total_runs          = EXCLUDED.total_runs,
    successful_runs     = EXCLUDED.successful_runs,
    failed_runs         = EXCLUDED.failed_runs,
    pages_fetched       = EXCLUDED.pages_fetched,
    articles_extracted  = EXCLUDED.articles_extracted,
    error_count         = EXCLUDED.error_count,
    avg_run_duration_s  = EXCLUDED.avg_run_duration_s,
    busiest_source_id   = EXCLUDED.busiest_source_id,
    created_at          = NOW();
$$;

-- 15c. 產生 RAG 每日快照
CREATE OR REPLACE FUNCTION analytics.build_daily_rag_stats(
  p_date DATE DEFAULT CURRENT_DATE - 1
)
RETURNS VOID
LANGUAGE SQL
SECURITY DEFINER
SET search_path = analytics
AS $$
  INSERT INTO analytics.daily_rag_stats (
    stat_date, total_queries, total_documents, new_documents,
    chunks_embedded, avg_faithfulness, avg_answer_relevance,
    avg_context_precision, total_prompt_tokens, total_completion_tokens
  )
  SELECT
    p_date,
    (SELECT count(*) FROM rag.query_logs WHERE created_at::DATE = p_date),
    (SELECT count(*) FROM rag.documents WHERE process_status = 'ready'),
    (SELECT count(*) FROM rag.documents WHERE created_at::DATE = p_date),
    (SELECT count(*) FROM rag.chunks WHERE embedding IS NOT NULL
       AND created_at::DATE = p_date),
    (SELECT avg(eval_faithfulness) FROM rag.query_logs
     WHERE created_at::DATE = p_date AND eval_faithfulness IS NOT NULL),
    (SELECT avg(eval_answer_relevance) FROM rag.query_logs
     WHERE created_at::DATE = p_date AND eval_answer_relevance IS NOT NULL),
    (SELECT avg(eval_context_precision) FROM rag.query_logs
     WHERE created_at::DATE = p_date AND eval_context_precision IS NOT NULL),
    (SELECT coalesce(sum(prompt_tokens), 0) FROM rag.query_logs
     WHERE created_at::DATE = p_date),
    (SELECT coalesce(sum(completion_tokens), 0) FROM rag.query_logs
     WHERE created_at::DATE = p_date)
  ON CONFLICT (stat_date) DO UPDATE SET
    total_queries         = EXCLUDED.total_queries,
    total_documents       = EXCLUDED.total_documents,
    new_documents         = EXCLUDED.new_documents,
    chunks_embedded       = EXCLUDED.chunks_embedded,
    avg_faithfulness      = EXCLUDED.avg_faithfulness,
    avg_answer_relevance  = EXCLUDED.avg_answer_relevance,
    avg_context_precision = EXCLUDED.avg_context_precision,
    total_prompt_tokens   = EXCLUDED.total_prompt_tokens,
    total_completion_tokens = EXCLUDED.total_completion_tokens,
    created_at            = NOW();
$$;

-- 15d. 一鍵刷新所有快照 + MATVIEW
CREATE OR REPLACE FUNCTION analytics.refresh_all(
  p_date DATE DEFAULT CURRENT_DATE - 1
)
RETURNS TEXT
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = analytics
AS $$
BEGIN
  PERFORM analytics.build_daily_shop_stats(p_date);
  PERFORM analytics.build_daily_crawler_stats(p_date);
  PERFORM analytics.build_daily_rag_stats(p_date);

  REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.mv_system_health;
  REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.mv_product_ranking;
  REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.mv_source_health;

  PERFORM analytics.log_event(
    'analytics', 'snapshot.refreshed', 'daily_stats', p_date::TEXT
  );

  RETURN format('analytics.refresh_all(%s) completed', p_date);
END;
$$;

-- ============================================================
-- pg_cron 排程範例（在 Supabase Dashboard 的 SQL Editor 執行）
-- ============================================================
-- SELECT cron.schedule(
--   'analytics-daily-refresh',
--   '15 0 * * *',              -- 每天 00:15 UTC
--   $$SELECT analytics.refresh_all()$$
-- );
--
-- -- 確認排程
-- SELECT * FROM cron.job;
--
-- -- 移除排程
-- SELECT cron.unschedule('analytics-daily-refresh');


-- ============================================================
-- 16. TRIGGERS — 自動事件推送（示範用）
-- ============================================================
-- 教學重點：trigger function 寫入不同 schema

-- 16a. Shop 訂單狀態變更 → analytics.events
CREATE OR REPLACE FUNCTION analytics.trg_shop_order_event()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = analytics
AS $$
BEGIN
  IF TG_OP = 'INSERT' THEN
    PERFORM analytics.log_event(
      'shop', 'order.created', 'order', NEW.id, NEW.customer_id,
      jsonb_build_object('total', NEW.total, 'status', NEW.status)
    );
  ELSIF TG_OP = 'UPDATE' AND OLD.status IS DISTINCT FROM NEW.status THEN
    PERFORM analytics.log_event(
      'shop',
      CASE NEW.status
        WHEN 'confirmed'  THEN 'order.paid'
        WHEN 'shipped'    THEN 'order.shipped'
        WHEN 'cancelled'  THEN 'order.cancelled'
        ELSE 'order.created'
      END,
      'order', NEW.id, NEW.customer_id,
      jsonb_build_object(
        'old_status', OLD.status,
        'new_status', NEW.status,
        'total', NEW.total
      )
    );
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_order_analytics ON shop.orders;
CREATE TRIGGER trg_order_analytics
  AFTER INSERT OR UPDATE OF status ON shop.orders
  FOR EACH ROW EXECUTE FUNCTION analytics.trg_shop_order_event();

-- 16b. Crawler 執行完成 → analytics.events
CREATE OR REPLACE FUNCTION analytics.trg_crawler_run_event()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = analytics
AS $$
BEGIN
  IF TG_OP = 'UPDATE' AND OLD.run_status != NEW.run_status
     AND NEW.run_status IN ('success', 'failed', 'partial') THEN
    PERFORM analytics.log_event(
      'crawler',
      CASE WHEN NEW.run_status = 'success' THEN 'crawl.completed'
           ELSE 'crawl.failed'
      END,
      'crawl_run', NEW.id, NULL,
      jsonb_build_object(
        'source_id', NEW.source_id,
        'status', NEW.run_status,
        'articles_extracted', NEW.articles_extracted,
        'error_count', NEW.error_count
      )
    );
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_crawl_run_analytics ON crawler.crawl_runs;
CREATE TRIGGER trg_crawl_run_analytics
  AFTER UPDATE OF run_status ON crawler.crawl_runs
  FOR EACH ROW EXECUTE FUNCTION analytics.trg_crawler_run_event();

-- 16c. RAG 查詢 → analytics.events
CREATE OR REPLACE FUNCTION analytics.trg_rag_query_event()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = analytics
AS $$
BEGIN
  PERFORM analytics.log_event(
    'rag', 'query.executed', 'query_log', NEW.id, NEW.created_by,
    jsonb_build_object(
      'collection_id', NEW.collection_id,
      'top_k', NEW.top_k,
      'llm_model', NEW.llm_model,
      'prompt_tokens', NEW.prompt_tokens
    )
  );
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_rag_query_analytics ON rag.query_logs;
CREATE TRIGGER trg_rag_query_analytics
  AFTER INSERT ON rag.query_logs
  FOR EACH ROW EXECUTE FUNCTION analytics.trg_rag_query_event();


-- ============================================================
-- 17. RLS + POLICIES
-- ============================================================

ALTER TABLE analytics.events ENABLE ROW LEVEL SECURITY;
ALTER TABLE analytics.daily_shop_stats ENABLE ROW LEVEL SECURITY;
ALTER TABLE analytics.daily_crawler_stats ENABLE ROW LEVEL SECURITY;
ALTER TABLE analytics.daily_rag_stats ENABLE ROW LEVEL SECURITY;
ALTER TABLE analytics.funnel_events ENABLE ROW LEVEL SECURITY;

-- Analytics 以後端為主，authenticated 可讀，寫入靠 trigger / service_role
DO $$
DECLARE
  tbl TEXT;
BEGIN
  FOREACH tbl IN ARRAY ARRAY[
    'events', 'daily_shop_stats', 'daily_crawler_stats',
    'daily_rag_stats', 'funnel_events'
  ]
  LOOP
    EXECUTE format('
      CREATE POLICY "%1$s_select" ON analytics.%1$s
        FOR SELECT TO authenticated USING (TRUE);
      CREATE POLICY "%1$s_service" ON analytics.%1$s
        FOR ALL TO service_role USING (TRUE) WITH CHECK (TRUE);
    ', tbl);
  END LOOP;
END;
$$;

-- funnel_events 允許 authenticated 寫入（前端推送）
CREATE POLICY "funnel_events_insert" ON analytics.funnel_events
  FOR INSERT TO authenticated WITH CHECK (TRUE);


-- ============================================================
-- 18. GRANTS
-- ============================================================

DO $$
DECLARE
  tbl TEXT;
BEGIN
  FOREACH tbl IN ARRAY ARRAY[
    'events', 'daily_shop_stats', 'daily_crawler_stats',
    'daily_rag_stats', 'funnel_events'
  ]
  LOOP
    EXECUTE format('GRANT SELECT ON analytics.%I TO authenticated;', tbl);
    EXECUTE format('GRANT ALL ON analytics.%I TO service_role;', tbl);
  END LOOP;
END;
$$;

-- funnel_events: 前端可寫入
GRANT INSERT ON analytics.funnel_events TO authenticated;

-- Functions
GRANT EXECUTE ON FUNCTION analytics.log_event(TEXT, TEXT, TEXT, TEXT, TEXT, JSONB) TO authenticated, service_role;
GRANT EXECUTE ON FUNCTION analytics.count_events(TEXT, TEXT, TIMESTAMPTZ, TIMESTAMPTZ) TO authenticated;
GRANT EXECUTE ON FUNCTION analytics.event_time_series(TEXT, TEXT, TEXT, INTEGER) TO authenticated;
GRANT EXECUTE ON FUNCTION analytics.revenue_time_series(TEXT, INTEGER) TO authenticated;
GRANT EXECUTE ON FUNCTION analytics.funnel_conversion(INTEGER) TO authenticated;
GRANT EXECUTE ON FUNCTION analytics.funnel_dropoff(INTEGER) TO authenticated;
GRANT EXECUTE ON FUNCTION analytics.monthly_cohort_retention(INTEGER) TO authenticated;
GRANT EXECUTE ON FUNCTION analytics.rag_quality_trend(TEXT, INTEGER) TO authenticated;
GRANT EXECUTE ON FUNCTION analytics.low_quality_chunks(TEXT, INTEGER, INTEGER) TO authenticated;
GRANT EXECUTE ON FUNCTION analytics.rag_token_usage(TEXT, INTEGER) TO authenticated;
GRANT EXECUTE ON FUNCTION analytics.crawler_source_ranking(INTEGER) TO authenticated;
GRANT EXECUTE ON FUNCTION analytics.crawler_queue_health() TO authenticated;
GRANT EXECUTE ON FUNCTION analytics.system_dashboard(INTEGER) TO authenticated;
GRANT EXECUTE ON FUNCTION analytics.detect_anomalies(TEXT, TEXT, INTEGER, FLOAT8) TO authenticated;
GRANT EXECUTE ON FUNCTION analytics.data_freshness() TO authenticated;
GRANT EXECUTE ON FUNCTION analytics.build_daily_shop_stats(DATE) TO service_role;
GRANT EXECUTE ON FUNCTION analytics.build_daily_crawler_stats(DATE) TO service_role;
GRANT EXECUTE ON FUNCTION analytics.build_daily_rag_stats(DATE) TO service_role;
GRANT EXECUTE ON FUNCTION analytics.refresh_all(DATE) TO service_role;

-- Materialized Views
GRANT SELECT ON analytics.mv_system_health TO authenticated;
GRANT SELECT ON analytics.mv_product_ranking TO authenticated;
GRANT SELECT ON analytics.mv_source_health TO authenticated;

-- ============================================================
-- 009: Webhooks & pg_net — 事件驅動的外部整合
-- ============================================================
-- pg_net = PostgreSQL 原生的 HTTP client extension
-- 可以在 trigger / function 裡直接發 HTTP 請求
--
-- 應用場景：
--   1. 訂單成立 → 通知 LINE / Slack
--   2. Crawler 完成 → 觸發 RAG embedding pipeline
--   3. 付款成功 → 呼叫第三方物流 API
--   4. 庫存低於閾值 → 發送補貨通知
--
-- 教學重點：
--   - pg_net 是非同步的（fire-and-forget），不會阻塞 transaction
--   - 敏感 URL / token 用 Vault 管理（見 011_vault_secrets.sql）
--   - 搭配 Supabase Edge Functions 做更複雜的邏輯
--   - Database Webhooks (Dashboard UI) vs pg_net (SQL) 的差異
-- ============================================================


-- ============================================================
-- 1. EXTENSION
-- ============================================================
CREATE EXTENSION IF NOT EXISTS pg_net;


-- ============================================================
-- 2. WEBHOOK DISPATCHER（通用 webhook 發送器）
-- ============================================================

-- 2a. 通用 webhook 呼叫（POST JSON）
CREATE OR REPLACE FUNCTION analytics.send_webhook(
  p_url     TEXT,
  p_payload JSONB,
  p_headers JSONB DEFAULT '{"Content-Type": "application/json"}'::JSONB
)
RETURNS BIGINT
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = analytics
AS $$
DECLARE
  v_request_id BIGINT;
  v_headers    JSONB;
BEGIN
  -- 合併預設 headers
  v_headers := '{"Content-Type": "application/json"}'::JSONB || p_headers;

  SELECT net.http_post(
    url     := p_url,
    body    := p_payload::TEXT,
    headers := v_headers
  ) INTO v_request_id;

  -- 記錄到 analytics.events
  PERFORM analytics.log_event(
    'analytics', 'snapshot.refreshed', 'webhook',
    v_request_id::TEXT, NULL,
    jsonb_build_object('url', p_url, 'payload_size', length(p_payload::TEXT))
  );

  RETURN v_request_id;
END;
$$;


-- ============================================================
-- 3. SHOP WEBHOOKS
-- ============================================================

-- 3a. 訂單成立 → 呼叫 Edge Function 發送通知
CREATE OR REPLACE FUNCTION shop.notify_order_created()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = shop
AS $$
DECLARE
  v_edge_url TEXT;
  v_payload  JSONB;
BEGIN
  -- Edge Function URL（實際部署時用 Vault 或環境變數）
  -- 這裡用 placeholder，學生需替換成自己的 project URL
  v_edge_url := 'https://YOUR_PROJECT.supabase.co/functions/v1/order-notification';

  v_payload := jsonb_build_object(
    'event', 'order.created',
    'order_id', NEW.id,
    'customer_id', NEW.customer_id,
    'total', NEW.total,
    'currency', NEW.currency,
    'created_at', NEW.created_at
  );

  -- 非同步發送（不阻塞 INSERT transaction）
  PERFORM net.http_post(
    url     := v_edge_url,
    body    := v_payload::TEXT,
    headers := jsonb_build_object(
      'Content-Type', 'application/json',
      'Authorization', 'Bearer ' || current_setting('app.settings.service_role_key', TRUE)
    )
  );

  RETURN NEW;
END;
$$;

-- 註：預設不啟用 trigger，學生自行決定是否開啟
-- DROP TRIGGER IF EXISTS trg_order_webhook ON shop.orders;
-- CREATE TRIGGER trg_order_webhook
--   AFTER INSERT ON shop.orders
--   FOR EACH ROW EXECUTE FUNCTION shop.notify_order_created();

-- 3b. 庫存低於閾值 → 補貨通知
CREATE OR REPLACE FUNCTION shop.notify_low_stock()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = shop
AS $$
BEGIN
  IF NEW.low_stock_threshold IS NOT NULL
     AND NEW.quantity <= NEW.low_stock_threshold
     AND (OLD.quantity IS NULL OR OLD.quantity > OLD.low_stock_threshold) THEN

    PERFORM net.http_post(
      url  := 'https://YOUR_PROJECT.supabase.co/functions/v1/stock-alert',
      body := jsonb_build_object(
        'event', 'stock.low',
        'store_id', NEW.store_id,
        'product_id', NEW.product_id,
        'quantity', NEW.quantity,
        'threshold', NEW.low_stock_threshold
      )::TEXT,
      headers := '{"Content-Type": "application/json"}'::JSONB
    );
  END IF;

  RETURN NEW;
END;
$$;

-- DROP TRIGGER IF EXISTS trg_stock_alert ON shop.stocks;
-- CREATE TRIGGER trg_stock_alert
--   AFTER UPDATE OF quantity ON shop.stocks
--   FOR EACH ROW EXECUTE FUNCTION shop.notify_low_stock();


-- ============================================================
-- 4. CRAWLER → RAG PIPELINE WEBHOOK
-- ============================================================

-- Crawler 完成 → 觸發 RAG embedding pipeline
-- 把新抓到的文章送去 Edge Function 做 chunking + embedding
CREATE OR REPLACE FUNCTION crawler.notify_article_ready()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = crawler
AS $$
BEGIN
  -- 只在新文章 INSERT 時觸發
  IF TG_OP = 'INSERT' AND NEW.is_published = TRUE THEN
    PERFORM net.http_post(
      url  := 'https://YOUR_PROJECT.supabase.co/functions/v1/rag-ingest',
      body := jsonb_build_object(
        'event', 'article.ready_for_rag',
        'article_id', NEW.id,
        'source_id', NEW.source_id,
        'title', NEW.title,
        'source_url', NEW.source_url,
        'content_length', length(coalesce(NEW.content_text, ''))
      )::TEXT,
      headers := '{"Content-Type": "application/json"}'::JSONB
    );
  END IF;

  RETURN NEW;
END;
$$;

-- DROP TRIGGER IF EXISTS trg_article_to_rag ON crawler.articles;
-- CREATE TRIGGER trg_article_to_rag
--   AFTER INSERT ON crawler.articles
--   FOR EACH ROW EXECUTE FUNCTION crawler.notify_article_ready();


-- ============================================================
-- 5. RAG 文件處理完成 → 通知
-- ============================================================

CREATE OR REPLACE FUNCTION rag.notify_document_ready()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = rag
AS $$
BEGIN
  -- 只在狀態變為 ready 或 failed 時通知
  IF OLD.process_status IS DISTINCT FROM NEW.process_status
     AND NEW.process_status IN ('ready', 'failed') THEN
    PERFORM net.http_post(
      url  := 'https://YOUR_PROJECT.supabase.co/functions/v1/document-status',
      body := jsonb_build_object(
        'event', 'document.' || NEW.process_status,
        'document_id', NEW.id,
        'collection_id', NEW.collection_id,
        'title', NEW.title,
        'status', NEW.process_status,
        'error', NEW.process_error,
        'chunk_count', NEW.chunk_count
      )::TEXT,
      headers := '{"Content-Type": "application/json"}'::JSONB
    );
  END IF;

  RETURN NEW;
END;
$$;

-- DROP TRIGGER IF EXISTS trg_document_status_webhook ON rag.documents;
-- CREATE TRIGGER trg_document_status_webhook
--   AFTER UPDATE OF process_status ON rag.documents
--   FOR EACH ROW EXECUTE FUNCTION rag.notify_document_ready();


-- ============================================================
-- 6. 查看 pg_net 請求紀錄
-- ============================================================
-- pg_net 的請求會記錄在 net._http_response 表
--
-- -- 查看最近的 webhook 請求
-- SELECT
--   id, status_code, content_type,
--   left(content::TEXT, 200) AS response_preview,
--   created
-- FROM net._http_response
-- ORDER BY created DESC
-- LIMIT 20;
--
-- -- 檢查失敗的請求
-- SELECT id, status_code, content, timed_out, error_msg, created
-- FROM net._http_response
-- WHERE status_code >= 400 OR timed_out = TRUE OR error_msg IS NOT NULL
-- ORDER BY created DESC;


-- ============================================================
-- 7. Edge Function 範例架構（參考）
-- ============================================================
--
-- supabase/functions/
-- ├── order-notification/    ← 訂單通知（LINE / Email）
-- │   └── index.ts
-- ├── stock-alert/           ← 庫存警告（Slack / Email）
-- │   └── index.ts
-- ├── rag-ingest/            ← Crawler → RAG pipeline
-- │   └── index.ts           ← 接收文章 → chunking → embedding → 寫入 rag.chunks
-- └── document-status/       ← RAG 處理完成通知
--     └── index.ts
--
-- 建立 Edge Function：
--   supabase functions new order-notification
--   supabase functions deploy order-notification

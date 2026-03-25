# Head First 生產運維三件套 — Cron、Webhook、Vault

> **_「你的系統不能只在你盯著螢幕的時候才工作。它必須在你睡覺的時候也能自己動。」_**
>
> 你的大腦在想：「我已經建好了 shop、crawler、RAG，夠了吧？」
>
> 不夠。你蓋好了一棟大樓，但沒有請保全、沒有裝監視器、沒有排班表。
> 誰來清理過期優惠券？誰來刷新統計快照？庫存見底了誰通知你？
>
> 這三個 extension 就是你的自動化運維基礎。

---

## 前置要求

- 已完成 `07_analytics-and-matview.md`（有 analytics schema 和 MATVIEW）
- Docker 跑著（`supabase start`）
- 瀏覽器打開 Studio `http://localhost:54323`
- 已執行過 001~008 的 migration（shop / crawler / rag / analytics schema 都在）

> 還沒跑起來？先去看 `06_migration-workflow.md`。

---

## Part 1: 開場 — 你的系統睡覺時誰在工作？

你花了好幾週打造了三個子系統：

- **Shop** — 電商：商品、訂單、優惠券、庫存
- **Crawler** — 爬蟲：排程爬取、佇列管理、文章儲存
- **RAG** — 知識庫：文件、分塊、向量搜尋

它們都能跑了。但你閉上眼睛想一想：

```
❓ 過期的優惠券誰來關掉？
❓ 爬蟲 worker 掛了，lease 誰來回收？
❓ MATVIEW 多久刷新一次？誰來刷？
❓ 庫存低於閾值，誰通知你去補貨？
❓ API Key 放在程式碼裡，安全嗎？
```

答案就是今天的三件套：

```
┌─────────────────────────────────────────────────────────┐
│                   生產運維三件套                          │
│                                                         │
│   ⏰ pg_cron          🌐 pg_net          🔐 Vault       │
│   ─────────          ────────          ──────────       │
│   排程任務            HTTP 請求          金鑰保險箱      │
│   「幾點做什麼」      「通知誰」          「密碼放哪」    │
│                                                         │
│        │                  │                  │          │
│        ▼                  ▼                  ▼          │
│   ┌─────────┐      ┌──────────┐      ┌──────────┐      │
│   │ 定時刷新 │      │ Slack 通知│      │ 安全儲存 │      │
│   │ 過期清理 │      │ LINE 推播 │      │ API Keys │      │
│   │ 佇列回收 │      │ Edge Func │      │ Tokens   │      │
│   └─────────┘      └──────────┘      └──────────┘      │
│                                                         │
│   Cron schedules → Webhook notifies → Vault secures    │
└─────────────────────────────────────────────────────────┘
```

三者的關係：**Cron 決定「什麼時候做」，Webhook 負責「通知外部」，Vault 保護「通知用的密鑰」。**

---

## Part 2: pg_cron — 資料庫裡的 crontab

### 什麼是 pg_cron？

你用過 Linux 的 `crontab` 嗎？pg_cron 就是 PostgreSQL 版的 crontab。

不需要外部 cron server，不需要額外的 container，直接在資料庫裡排程。

### 啟用 Extension

```sql
-- pg_cron 在 Supabase 已預裝，但需要啟用
CREATE EXTENSION IF NOT EXISTS pg_cron;
```

### Cron 表達式語法

五個欄位，從左到右：

```
┌───────── 分鐘 (0-59)
│ ┌─────── 小時 (0-23)
│ │ ┌───── 日   (1-31)
│ │ │ ┌─── 月   (1-12)
│ │ │ │ ┌─ 星期 (0-7, 0 和 7 都是週日)
│ │ │ │ │
* * * * *
```

常見範例：

| 表達式 | 意思 |
|--------|------|
| `15 0 * * *` | 每天 00:15 |
| `*/5 * * * *` | 每 5 分鐘 |
| `30 0 * * *` | 每天 00:30 |
| `0 * * * *` | 每小時整點 |
| `0 5 * * 0` | 每週日 05:00 |
| `0 6 * * *` | 每天 06:00 |

> **你的大腦在想：「`*/5` 是什麼意思？」**
>
> `/` 是「每隔」的意思。`*/5` = 每隔 5。所以 `*/5 * * * *` = 每 5 分鐘執行一次。
> `*/10 * * * *` = 每 10 分鐘。`0 */2 * * *` = 每 2 小時的整點。

### 核心 API

```sql
-- 建立排程
SELECT cron.schedule(
  'job-name',          -- 排程名稱（唯一識別）
  '15 0 * * *',        -- cron 表達式
  $$你要執行的 SQL$$    -- 要跑的 SQL 指令
);

-- 移除排程
SELECT cron.unschedule('job-name');

-- 查看所有排程
SELECT jobid, jobname, schedule, command
FROM cron.job
ORDER BY jobname;

-- 查看執行歷史
SELECT j.jobname, d.status, d.return_message,
  d.start_time, d.end_time,
  d.end_time - d.start_time AS duration
FROM cron.job_run_details d
JOIN cron.job j ON j.jobid = d.jobid
ORDER BY d.start_time DESC
LIMIT 30;
```

### 真實排程範例（來自 010_cron_jobs.sql）

我們在 migration 裡定義了 12 個排程。以下是最重要的五個：

**1. 每日快照刷新（analytics）**

```sql
-- 每天 00:15 UTC 刷新所有分析快照 + MATVIEW
SELECT cron.schedule(
  'analytics-daily-refresh',
  '15 0 * * *',
  $$SELECT analytics.refresh_all()$$
);
```

**2. 過期 lease 回收（crawler）**

```sql
-- 每 5 分鐘：回收過期的 lease（worker 掛掉的情況）
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
```

**3. 過期優惠券停用（shop）**

```sql
-- 每天 00:30：停用過期優惠券
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
```

**4. 孤兒 chunks 清理（rag）**

```sql
-- 每週日 05:00：清理孤兒 chunks（document 已刪除但 chunk 還在）
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
```

**5. 事件保留期限（analytics）**

```sql
-- 每天 06:00：清理超過 90 天的舊事件
SELECT cron.schedule(
  'analytics-events-retention',
  '0 6 * * *',
  $$
    DELETE FROM analytics.events
    WHERE created_at < NOW() - INTERVAL '90 days'
  $$
);
```

> **腦筋急轉彎：「為什麼 crawler-lease-recovery 要每 5 分鐘跑一次？」**
>
> 想像一下：有個 worker 正在處理一個 URL，lease 拿到了，然後 worker 掛了（OOM、網路斷線、container 被殺）。
> 這個 URL 的狀態是 `leased`，但永遠不會完成。如果沒有人回收它，這個 URL 就永遠卡住了。
>
> 5 分鐘是個平衡：夠頻繁不會讓任務卡太久，又不會太頻繁造成不必要的 UPDATE。
> 而且 lease 本身有 `lease_expires_at`，只有真的過期了才會被回收，不會搶走正在執行中的任務。

---

## Part 3: pg_net — 從資料庫發 HTTP 請求

### 什麼是 pg_net？

一般來說，資料庫只能被動地等別人來查詢。pg_net 讓 PostgreSQL 主動發出 HTTP 請求。

這意味著：**資料庫裡發生了事情，可以立刻通知外部系統。**

### 啟用 Extension

```sql
CREATE EXTENSION IF NOT EXISTS pg_net;
```

### 核心 API

```sql
-- 發送 POST 請求（非同步，fire-and-forget）
SELECT net.http_post(
  url     := 'https://example.com/webhook',
  body    := '{"event": "order.created", "id": "123"}'::TEXT,
  headers := '{"Content-Type": "application/json"}'::JSONB
);
-- 回傳 request_id (BIGINT)

-- 查看請求結果
SELECT id, status_code, content, timed_out, error_msg, created
FROM net._http_response
ORDER BY created DESC
LIMIT 10;
```

> **你的大腦在想：「fire-and-forget 是什麼意思？」**
>
> `net.http_post()` 只是把請求丟出去，不會等回應。
> 你的 INSERT/UPDATE transaction 照常 commit，不會因為外部 API 慢或掛掉而被卡住。
> 結果會非同步寫入 `net._http_response` 表，你可以稍後去查。

### 通用 Webhook 發送器

先建一個通用的 webhook 函數，所有場景都能用：

```sql
-- 通用 webhook 呼叫（POST JSON）
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

  RETURN v_request_id;
END;
$$;
```

### 四個真實 Webhook 場景

**場景 1：訂單成立 → 呼叫 Edge Function**

```sql
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
```

**場景 2：庫存低於閾值 → Slack 告警**

```sql
CREATE OR REPLACE FUNCTION shop.notify_low_stock()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = shop
AS $$
BEGIN
  -- 只在庫存「剛好」跌破閾值時觸發（避免重複通知）
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
```

**場景 3：Crawler 完成 → 觸發 RAG pipeline**

```sql
CREATE OR REPLACE FUNCTION crawler.notify_article_ready()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = crawler
AS $$
BEGIN
  IF TG_OP = 'INSERT' AND NEW.is_published = TRUE THEN
    PERFORM net.http_post(
      url  := 'https://YOUR_PROJECT.supabase.co/functions/v1/rag-ingest',
      body := jsonb_build_object(
        'event', 'article.ready_for_rag',
        'article_id', NEW.id,
        'title', NEW.title,
        'content_length', length(coalesce(NEW.content_text, ''))
      )::TEXT,
      headers := '{"Content-Type": "application/json"}'::JSONB
    );
  END IF;

  RETURN NEW;
END;
$$;
```

**場景 4：RAG 文件處理完成 → 狀態通知**

```sql
CREATE OR REPLACE FUNCTION rag.notify_document_ready()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = rag
AS $$
BEGIN
  IF OLD.process_status IS DISTINCT FROM NEW.process_status
     AND NEW.process_status IN ('ready', 'failed') THEN
    PERFORM net.http_post(
      url  := 'https://YOUR_PROJECT.supabase.co/functions/v1/document-status',
      body := jsonb_build_object(
        'event', 'document.' || NEW.process_status,
        'document_id', NEW.id,
        'title', NEW.title,
        'status', NEW.process_status,
        'chunk_count', NEW.chunk_count
      )::TEXT,
      headers := '{"Content-Type": "application/json"}'::JSONB
    );
  END IF;

  RETURN NEW;
END;
$$;
```

### Trigger 連接模式

Webhook function 寫好了，還需要 trigger 才會自動觸發：

```sql
-- 訂單成立時觸發
CREATE TRIGGER trg_order_webhook
  AFTER INSERT ON shop.orders
  FOR EACH ROW EXECUTE FUNCTION shop.notify_order_created();

-- 庫存變動時觸發
CREATE TRIGGER trg_stock_alert
  AFTER UPDATE OF quantity ON shop.stocks
  FOR EACH ROW EXECUTE FUNCTION shop.notify_low_stock();

-- 新文章入庫時觸發
CREATE TRIGGER trg_article_to_rag
  AFTER INSERT ON crawler.articles
  FOR EACH ROW EXECUTE FUNCTION crawler.notify_article_ready();

-- RAG 處理狀態變更時觸發
CREATE TRIGGER trg_document_status_webhook
  AFTER UPDATE OF process_status ON rag.documents
  FOR EACH ROW EXECUTE FUNCTION rag.notify_document_ready();
```

> **腦筋急轉彎：「為什麼 pg_net 是 fire-and-forget？不等回應不危險嗎？」**
>
> 想想看：如果 `net.http_post()` 會等回應，那你的 `INSERT INTO shop.orders` 就要等 Slack API 回應。
> Slack 慢了 3 秒？你的訂單寫入就慢 3 秒。Slack 掛了？你的訂單寫入就失敗。
>
> 這完全不合理。訂單寫入是核心業務，通知是附加功能。核心不能被附加功能拖累。
>
> 所以 fire-and-forget 是正確的設計。通知失敗了？查 `net._http_response` 表，重送就好。

---

## Part 4: Supabase Vault — API Key 不能寫死在程式碼裡

### 問題

回頭看 Part 3 的 webhook functions — 那些 URL 和 Authorization header 裡的 token，你打算怎麼管理？

```sql
-- ❌ 千萬不要這樣做
v_edge_url := 'https://my-project.supabase.co/functions/v1/order-notification';
'Authorization', 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'
```

API Key 寫死在 function 裡面 = **安全災難**：

1. 任何有 `pg_proc` 讀取權限的人都能看到你的 key
2. 換 key 要改 function 程式碼，然後重新部署
3. 不同環境（dev / staging / prod）不能用不同的 key
4. 沒有 audit log，不知道誰讀了什麼

### 啟用 Extension

```sql
-- Supabase Cloud 已預裝，local dev 也支援
CREATE EXTENSION IF NOT EXISTS supabase_vault;
```

### 核心 API

```sql
-- 建立 secret（值會加密儲存）
SELECT vault.create_secret(
  'sk-your-actual-api-key',       -- secret 值
  'openai_api_key',               -- 名稱（唯一識別）
  'OpenAI API key for RAG'        -- 描述
);

-- 查看所有 secrets（不顯示值，只顯示 metadata）
SELECT id, name, description, created_at, updated_at
FROM vault.secrets
ORDER BY name;

-- 讀取解密後的值（只有 SECURITY DEFINER function 能讀）
SELECT name, decrypted_secret
FROM vault.decrypted_secrets
WHERE name = 'openai_api_key';
```

### 四個必備 Secrets

我們在 `011_vault_secrets.sql` 裡建立了四個 secret：

```sql
DO $$
BEGIN
  -- 1. OpenAI API Key（RAG embedding 用）
  PERFORM vault.create_secret(
    'sk-your-openai-api-key-here',
    'openai_api_key',
    'OpenAI API key for RAG embedding generation'
  );

  -- 2. LINE Messaging API Token（訂單通知用）
  PERFORM vault.create_secret(
    'your-line-channel-access-token',
    'line_channel_token',
    'LINE Messaging API channel access token'
  );

  -- 3. Slack Webhook URL（監控告警用）
  PERFORM vault.create_secret(
    'https://hooks.slack.com/services/YOUR/WEBHOOK/URL',
    'slack_webhook_url',
    'Slack incoming webhook for system alerts'
  );

  -- 4. Supabase Service Role Key（Edge Function 呼叫用）
  PERFORM vault.create_secret(
    'your-service-role-key',
    'supabase_service_role_key',
    'Supabase service role key for internal API calls'
  );
EXCEPTION
  WHEN OTHERS THEN
    RAISE NOTICE 'Vault secrets creation skipped: %', SQLERRM;
END;
$$;
```

> **你的大腦在想：「為什麼要用 `DO $$ ... EXCEPTION ... $$`？」**
>
> 兩個原因：
> 1. **Vault 不可用時不中斷 migration** — 某些環境可能沒裝 Vault extension
> 2. **重複執行不報錯** — name 衝突時自動 skip，讓 migration 是 idempotent 的

### Helper Functions — SECURITY DEFINER 模式

Secret 存進 Vault 了，但誰能讀？**只有 SECURITY DEFINER function 能讀。**

這是 Vault 的安全設計：前端（anon / authenticated）永遠看不到 secret 值。

```sql
-- RAG 用的 OpenAI Key
CREATE OR REPLACE FUNCTION rag.get_openai_key()
RETURNS TEXT
LANGUAGE SQL
SECURITY DEFINER
SET search_path = rag
AS $$
  SELECT decrypted_secret FROM vault.decrypted_secrets
  WHERE name = 'openai_api_key' LIMIT 1;
$$;

GRANT EXECUTE ON FUNCTION rag.get_openai_key() TO service_role;

-- Shop 用的 LINE Token
CREATE OR REPLACE FUNCTION shop.get_line_token()
RETURNS TEXT
LANGUAGE SQL
SECURITY DEFINER
SET search_path = shop
AS $$
  SELECT decrypted_secret FROM vault.decrypted_secrets
  WHERE name = 'line_channel_token' LIMIT 1;
$$;

GRANT EXECUTE ON FUNCTION shop.get_line_token() TO service_role;

-- Analytics 用的 Slack Webhook URL
CREATE OR REPLACE FUNCTION analytics.get_slack_webhook()
RETURNS TEXT
LANGUAGE SQL
SECURITY DEFINER
SET search_path = analytics
AS $$
  SELECT decrypted_secret FROM vault.decrypted_secrets
  WHERE name = 'slack_webhook_url' LIMIT 1;
$$;

GRANT EXECUTE ON FUNCTION analytics.get_slack_webhook() TO service_role;
```

### Vault + pg_net 整合：安全地發 Slack 通知

這是三件套整合的經典範例：

```sql
-- 用 Vault 的 Slack URL 安全地發送告警
CREATE OR REPLACE FUNCTION analytics.send_slack_alert(p_message TEXT)
RETURNS BIGINT
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = analytics
AS $$
DECLARE
  v_webhook_url TEXT;
  v_request_id  BIGINT;
BEGIN
  -- 從 Vault 取得 Slack webhook URL（不是寫死的！）
  v_webhook_url := analytics.get_slack_webhook();

  -- 用 pg_net 發送 HTTP POST
  SELECT net.http_post(
    url     := v_webhook_url,
    body    := jsonb_build_object('text', p_message)::TEXT,
    headers := '{"Content-Type": "application/json"}'::JSONB
  ) INTO v_request_id;

  RETURN v_request_id;
END;
$$;

-- 使用方式：
-- SELECT analytics.send_slack_alert('Crawler 失敗率超過 50%！');
```

### Dashboard 管理

除了 SQL，你也可以在 Studio 裡管理 Vault：

**Settings → Vault** → 你會看到所有 secrets 的列表（值是隱藏的）。可以新增、編輯、刪除。

> **腦筋急轉彎：「為什麼 helper function 要放在各自的 schema 裡（rag.get_openai_key, shop.get_line_token）？」**
>
> 最小權限原則。每個 schema 的 function 只能讀取自己需要的 secret。
> `rag.get_openai_key()` 不能讀 `slack_webhook_url`。
> 如果某個 schema 被入侵了，攻擊者只能拿到那個 schema 的 secret，不是全部。

---

## Part 5: 三件套整合 — 完整場景

來看一個端到端的場景，感受三件套如何協作：

### 場景：每天凌晨自動刷新分析快照，異常時發 Slack 通知

```
凌晨 00:15 UTC
      │
      ▼
┌──────────────┐
│   pg_cron    │  schedule: '15 0 * * *'
│              │  job: 'analytics-daily-refresh'
└──────┬───────┘
       │ 執行
       ▼
┌──────────────┐
│ analytics.   │  刷新所有 MATVIEW
│ refresh_all()│  更新 daily snapshots
└──────┬───────┘
       │ 檢查結果
       ▼
┌──────────────┐
│ detect_      │  比較今天 vs 昨天
│ anomalies()  │  營收暴跌 > 30%?
└──────┬───────┘
       │ 異常！
       ▼
┌──────────────┐
│ send_slack_  │  從 Vault 取得 webhook URL
│ alert()      │  (analytics.get_slack_webhook)
└──────┬───────┘
       │ 安全發送
       ▼
┌──────────────┐
│   pg_net     │  net.http_post() → Slack API
│ (fire-and-   │  非同步，不阻塞
│  forget)     │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│   Slack      │  #alerts 頻道收到通知：
│   Channel    │  「營收暴跌 42%，請檢查！」
└──────────────┘
```

**在這個流程中：**

| 角色 | 負責 |
|------|------|
| **pg_cron** | 每天 00:15 自動觸發 refresh_all() |
| **pg_net** | 非同步發送 HTTP POST 到 Slack |
| **Vault** | 安全儲存 Slack webhook URL，不暴露在程式碼中 |

三件套各司其職，缺一不可。

---

## Part 6: 動手做 — 在 Studio 驗證

### Step 1: 確認 Extensions 已啟用

在 SQL Editor 執行：

```sql
-- 檢查三個 extension 的狀態
SELECT extname, extversion
FROM pg_extension
WHERE extname IN ('pg_cron', 'pg_net', 'supabase_vault')
ORDER BY extname;
```

```
📝 驗證清單
□ 看到 pg_cron — 版本號
□ 看到 pg_net — 版本號
□ 看到 supabase_vault — 版本號
（如果缺少，用 CREATE EXTENSION IF NOT EXISTS ... 啟用）
```

### Step 2: 建立測試 Cron Job

```sql
-- 建立一個每分鐘執行的測試 job
SELECT cron.schedule(
  'test-heartbeat',
  '* * * * *',
  $$SELECT 1 AS heartbeat$$
);

-- 確認已建立
SELECT jobid, jobname, schedule, command
FROM cron.job
WHERE jobname = 'test-heartbeat';
```

等 2-3 分鐘，然後檢查執行紀錄：

```sql
-- 查看執行歷史
SELECT j.jobname, d.status, d.return_message,
  d.start_time, d.end_time
FROM cron.job_run_details d
JOIN cron.job j ON j.jobid = d.jobid
WHERE j.jobname = 'test-heartbeat'
ORDER BY d.start_time DESC
LIMIT 5;
```

```
📝 驗證清單
□ cron.job 裡看到 test-heartbeat
□ cron.job_run_details 有執行紀錄
□ status 是 'succeeded'
```

清理：

```sql
-- 測試完畢，移除
SELECT cron.unschedule('test-heartbeat');
```

### Step 3: 測試 pg_net Webhook

用 webhook.site 或 httpbin.org 測試：

```sql
-- 發送測試 webhook（替換成你的 webhook.site URL）
SELECT net.http_post(
  url     := 'https://webhook.site/YOUR-UUID-HERE',
  body    := '{"test": true, "message": "Hello from pg_net!"}'::TEXT,
  headers := '{"Content-Type": "application/json"}'::JSONB
);
```

```sql
-- 檢查結果
SELECT id, status_code, left(content::TEXT, 200) AS response,
  timed_out, error_msg, created
FROM net._http_response
ORDER BY created DESC
LIMIT 5;
```

```
📝 驗證清單
□ net.http_post() 回傳了 request_id
□ net._http_response 裡有紀錄
□ status_code 是 200
□ webhook.site 上看到了你的請求
```

### Step 4: 測試 Vault Secret 讀取

```sql
-- 透過 helper function 讀取（正確做法）
SELECT analytics.get_slack_webhook() AS slack_url;

-- 如果有值，表示 Vault 運作正常
-- 如果回傳 NULL，表示 secret 尚未建立
```

```
📝 驗證清單
□ helper function 回傳了 secret 值
□ 直接查 vault.decrypted_secrets 也能看到（測試環境）
□ 理解為什麼生產環境不該直接查 vault.decrypted_secrets
```

### Step 5: 查看所有已建立的 Cron Jobs

```sql
-- 010_cron_jobs.sql 建立了哪些排程？
SELECT jobid, jobname, schedule,
  left(command, 60) AS command_preview
FROM cron.job
ORDER BY jobname;
```

你應該會看到類似這樣的結果：

```
 jobname                     | schedule      | command_preview
-----------------------------+---------------+------------------------------------------
 analytics-daily-refresh     | 15 0 * * *    | SELECT analytics.refresh_all()
 analytics-events-retention  | 0 6 * * *     | DELETE FROM analytics.events WHERE ...
 analytics-hourly-matview    | 0 * * * *     | REFRESH MATERIALIZED VIEW CONCURRENTLY...
 crawler-dead-letter         | */5 * * * *   | UPDATE crawler.crawl_queue SET status...
 crawler-lease-recovery      | */5 * * * *   | UPDATE crawler.crawl_queue SET status...
 crawler-queue-cleanup       | 0 3 * * *     | DELETE FROM crawler.crawl_queue WHERE...
 crawler-schedule-runs       | 0 * * * *     | INSERT INTO crawler.crawl_queue ...
 cron-history-cleanup        | 45 6 * * *    | DELETE FROM cron.job_run_details WHERE...
 pgnet-cleanup               | 30 6 * * *    | DELETE FROM net._http_response WHERE...
 rag-cleanup-orphan-chunks   | 0 5 * * 0     | DELETE FROM rag.chunks c WHERE NOT...
 rag-detect-stale            | 0 4 * * *     | UPDATE rag.documents SET process_status...
 rag-sync-chunk-count        | 30 4 * * *    | UPDATE rag.documents d SET chunk_count...
 shop-cancel-stale-orders    | 0 1 * * *     | UPDATE shop.orders SET status = ...
 shop-expire-coupons         | 30 0 * * *    | UPDATE shop.coupons SET is_active...
 shop-update-review-stats    | 0 2 * * *     | UPDATE shop.products p SET metadata...
```

---

## 搭配檔案

| 檔案 | 用途 |
|------|------|
| `../migrations/009_webhooks.sql` | Webhook 完整 SQL — 4 個場景的 function + trigger |
| `../migrations/010_cron_jobs.sql` | Cron 完整 SQL — 15 個排程任務 |
| `../migrations/011_vault_secrets.sql` | Vault 完整 SQL — 4 個 secret + helper functions |
| `07_analytics-and-matview.md` | Analytics MATVIEW（搭配 cron 刷新） |

---

## 自我檢查清單

```
□ 我能說出 cron 表達式的五個欄位：分 時 日 月 週
□ 我會用 cron.schedule() 建立排程，cron.unschedule() 移除排程
□ 我知道用 cron.job_run_details 查看執行歷史和錯誤訊息
□ 我理解 net.http_post() 是非同步的（fire-and-forget），不會阻塞 transaction
□ 我會用 vault.create_secret() 建立 secret，用 vault.decrypted_secrets 讀取
□ 我理解 SECURITY DEFINER helper function 模式：每個 schema 只讀自己的 secret
□ 我能寫出 Webhook trigger 模式：AFTER INSERT/UPDATE → webhook function → net.http_post()
□ 我能說出三件套的整合流程：Cron 排程 → 業務邏輯 → Vault 取密鑰 → pg_net 發通知
□ 我在 Studio 裡驗證了 cron job 的建立和執行
□ 我在 Studio 裡測試了 pg_net 發送 HTTP 請求
```

---

## 下一步

你的系統現在有了自動化運維能力：定時任務、事件通知、安全金鑰管理。

接下來學習如何把這些能力暴露給前端：

→ `09_api-gateway-pattern.md` — API Gateway 模式：Edge Functions + RLS + Webhook 的完整整合。

> **最後提醒**：API Key 永遠不要寫死在 function 程式碼裡。用 Vault 存、用 helper function 讀。
> 這不是「最佳實踐」，這是「最低要求」。

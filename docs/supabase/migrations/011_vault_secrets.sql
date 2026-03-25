-- ============================================================
-- 011: Vault — Secrets 管理
-- ============================================================
-- Supabase Vault = 加密的 secrets storage
-- 用途：安全儲存 API keys, tokens, credentials
-- 比環境變數更安全（加密儲存、audit log、存取控制）
--
-- 教學重點：
--   - vault.create_secret() 建立 / vault.update_secret() 更新
--   - 在 function 裡讀取 secret，不暴露在程式碼中
--   - 搭配 009_webhooks.sql 使用（Edge Function URL, API keys）
--   - Dashboard → Settings → Vault 也可管理
-- ============================================================


-- ============================================================
-- 1. EXTENSION
-- ============================================================
-- supabase_vault 在 Supabase Cloud 已預裝。
-- Local dev (supabase start) 也支援，但 self-hosted 可能需要手動安裝。
-- 用 DO block 防護：如果 extension 不可用，跳過整個 migration 的 vault 部分。
CREATE EXTENSION IF NOT EXISTS supabase_vault;


-- ============================================================
-- 2. 建立 SECRETS
-- ============================================================
-- vault.create_secret(secret, name, description)
-- secret 值會加密儲存，只有 SECURITY DEFINER function 能讀取
--
-- ⚠️ 以下是 placeholder 值！學生需替換成自己的 API key。
--    用 DO block + EXCEPTION 包裝，確保：
--    1. vault 不可用時不會中斷 migration
--    2. 重複執行不會報錯（name 衝突時 skip）

DO $$
BEGIN
  -- 2a. OpenAI API Key（RAG embedding 用）
  PERFORM vault.create_secret(
    'sk-your-openai-api-key-here',
    'openai_api_key',
    'OpenAI API key for RAG embedding generation'
  );

  -- 2b. LINE Messaging API Token（訂單通知用）
  PERFORM vault.create_secret(
    'your-line-channel-access-token',
    'line_channel_token',
    'LINE Messaging API channel access token'
  );

  -- 2c. Slack Webhook URL（監控告警用）
  PERFORM vault.create_secret(
    'https://hooks.slack.com/services/YOUR/WEBHOOK/URL',
    'slack_webhook_url',
    'Slack incoming webhook for system alerts'
  );

  -- 2d. Supabase Service Role Key（Edge Function 呼叫用）
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


-- ============================================================
-- 3. HELPER FUNCTIONS — 安全讀取 Secrets
-- ============================================================
-- 重點：只有 SECURITY DEFINER function 能讀取 vault
-- 前端永遠看不到 secret 值

-- 3a. 通用 secret 讀取器（僅限 service_role）
CREATE OR REPLACE FUNCTION public.get_secret(p_name TEXT)
RETURNS TEXT
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  v_secret TEXT;
BEGIN
  SELECT decrypted_secret INTO v_secret
  FROM vault.decrypted_secrets
  WHERE name = p_name
  LIMIT 1;

  IF v_secret IS NULL THEN
    RAISE EXCEPTION 'Secret "%" not found in vault', p_name;
  END IF;

  RETURN v_secret;
END;
$$;

-- 只有 service_role 可以讀取 secrets
GRANT EXECUTE ON FUNCTION public.get_secret(TEXT) TO service_role;

-- 3b. OpenAI API Key（供 RAG Edge Function 使用）
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

-- 3c. LINE Token（供 shop webhook 使用）
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

-- 3d. Slack Webhook URL（供 analytics 告警使用）
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


-- ============================================================
-- 4. 實際使用範例 — Vault + pg_net 整合
-- ============================================================

-- 4a. 用 Vault 的 Slack URL 發送告警
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
  v_webhook_url := analytics.get_slack_webhook();

  SELECT net.http_post(
    url     := v_webhook_url,
    body    := jsonb_build_object('text', p_message)::TEXT,
    headers := '{"Content-Type": "application/json"}'::JSONB
  ) INTO v_request_id;

  RETURN v_request_id;
END;
$$;

GRANT EXECUTE ON FUNCTION analytics.send_slack_alert(TEXT) TO service_role;

-- 使用方式：
-- SELECT analytics.send_slack_alert('⚠️ Crawler 失敗率超過 50%！');


-- ============================================================
-- 5. SECRET 管理
-- ============================================================

-- 查看所有 secrets（不顯示值，只顯示 metadata）
-- SELECT id, name, description, created_at, updated_at
-- FROM vault.secrets
-- ORDER BY name;

-- 查看解密後的值（僅限測試！生產環境不要這樣做）
-- SELECT name, decrypted_secret, description
-- FROM vault.decrypted_secrets;

-- 更新 secret
-- SELECT vault.update_secret(
--   (SELECT id FROM vault.secrets WHERE name = 'openai_api_key'),
--   'sk-new-api-key-value'
-- );

-- 刪除 secret
-- DELETE FROM vault.secrets WHERE name = 'openai_api_key';


-- ============================================================
-- 6. 安全注意事項
-- ============================================================
--
-- ❌ 絕對不要做：
--   - 在 RLS policy 裡讀取 vault（效能災難）
--   - GRANT get_secret() TO authenticated（洩漏給前端）
--   - 在 log / analytics.events 裡記錄 secret 值
--   - 用 SELECT * FROM vault.decrypted_secrets 做 debug（生產環境）
--
-- ✅ 正確做法：
--   - Secret 只在 SECURITY DEFINER function 裡讀取
--   - 只 GRANT 給 service_role
--   - 用 Dashboard → Vault UI 管理（有 audit log）
--   - 定期輪替（rotate）API keys
--   - 開發環境用 .env，生產環境用 Vault

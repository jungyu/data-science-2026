# 本地啟動指南

從空的 checkout 到能收發訊息的本地 webhook 服務，最短路徑。

## 1. 建立 Python 環境

在專案根目錄執行：

```bash
cp .env.example .env
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

> 後續所有 Python 指令都需在 venv 啟用狀態下執行，或改用 `.venv/bin/python` 的絕對路徑。

## 2. 填入 `.env`

最少需填入以下六個值（詳細取得方式見 [憑證取得教學](./credential-provisioning.md)）：

```bash
LINE_CHANNEL_SECRET=...
LINE_CHANNEL_ACCESS_TOKEN=...
OPENAI_API_KEY=...
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=...
SUPABASE_DB_URL=postgresql://postgres@db.<project-ref>.supabase.co:5432/postgres
PGPASSWORD=...        # 密碼獨立存放，避免特殊字元被 shell 解析
```

**各變數用途：**

| 變數 | 使用方 |
|------|--------|
| `SUPABASE_URL` + `SUPABASE_SERVICE_ROLE_KEY` | App 運行期間（Supabase Python client） |
| `SUPABASE_DB_URL` + `PGPASSWORD` | `psql` 套用 SQL schema |
| `LINE_*` | Webhook 簽章驗證 + Push API |
| `OPENAI_API_KEY` | Router、Generator、Embeddings |

> **密碼含特殊字元（`@` `#` `^` 等）時**：不要把密碼放在 `SUPABASE_DB_URL` 裡。改用 `PGPASSWORD` 獨立存放，並用 `export` 搭配**單引號**設定：
> ```bash
> export SUPABASE_DB_URL='postgresql://postgres@db.<project-ref>.supabase.co:5432/postgres'
> export PGPASSWORD='你的原始密碼'
> ```

## 3. 套用 Supabase Schema

**驗證連線：**

```bash
psql "$SUPABASE_DB_URL" -c "select 1;"
# 期望：?column? → 1
```

**執行腳本（schema + functions + seed + skills，約 30 秒）：**

```bash
./scripts/apply_supabase_sql.sh
```

腳本依序執行：

1. 讀取 `.env`
2. 套用 `supabase/schema.sql`（建立資料表與索引）
3. 套用 `supabase/functions.sql`（`match_private_knowledge` 混合檢索函式）
4. 套用 `supabase/seed.sql`（初始資料）
5. 執行 `scripts/seed_skills.py`（將 `skills/*/SKILL.md` 寫入 `ai_skills`）

**只套用 SQL，跳過 skill seed：**

```bash
SKIP_SKILL_SEED=1 ./scripts/apply_supabase_sql.sh
```

**手動逐步執行：**

```bash
psql "$SUPABASE_DB_URL" -v ON_ERROR_STOP=1 -f supabase/schema.sql
psql "$SUPABASE_DB_URL" -v ON_ERROR_STOP=1 -f supabase/functions.sql
psql "$SUPABASE_DB_URL" -v ON_ERROR_STOP=1 -f supabase/seed.sql
.venv/bin/python scripts/seed_skills.py
```

## 4. 啟動 App

```bash
./scripts/run_local.sh
```

等同於手動執行：

```bash
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port "${APP_PORT:-8000}" --reload
```

**Health check：**

```bash
curl http://127.0.0.1:8000/health
# 期望：{"status":"ok"}
```

## 5. 打通 LINE Webhook（ngrok）

LINE Webhook 需要一個公開的 HTTPS URL，本地開發使用 ngrok 建立 tunnel。ngrok 的原理、安裝、進階使用與 GCP 部署替代方案詳見 [tunnel.md](./tunnel.md)。

**快速啟動（已安裝 ngrok 者）：**

另開一個 terminal，執行：

```bash
ngrok http 8000
```

取得 `https://xxxx.ngrok-free.app` 後，前往 [LINE Developers Console](https://developers.line.biz/console/)：

1. 選擇你的 Channel → **Messaging API** 分頁
2. **Webhook URL** 填入：`https://xxxx.ngrok-free.app/api/line/webhook`
3. 點「**Update**」→ 開啟「**Use webhook**」toggle → 點「**Verify**」
4. Verify 顯示 `200 OK` 即表示打通

> **ngrok 免費帳號注意**：每次重啟 ngrok，URL 都會改變，需重新到 Developers Console 更新 Webhook URL。若需固定 URL，可改用 Cloudflare Tunnel 或部署到 GCP Cloud Run，詳見 [tunnel.md](./tunnel.md)。

## 6. 匯入知識庫

```bash
# 範例：匯入 RAG 相關文件
.venv/bin/python scripts/ingest_markdown.py \
  docs/RAG/*.md \
  docs/RAG/LangGraph/*.md \
  --category rag
```

`--category` 的值必須對應 skill 的 `rag_categories` 設定，否則 retriever 找不到資料。詳見 [specs](./specs/README.md#知識庫匯入規格ingest_markdownpy)。

## 7. 首次驗收清單

傳一則訊息給 bot 後，確認以下各項：

- [ ] `POST /api/line/webhook` 回傳 `200 OK`
- [ ] `line_messages` 新增一筆 `direction=inbound` 記錄
- [ ] bot 透過 LINE Push API 發出回覆（手機收到訊息）
- [ ] `line_messages` 新增一筆 `direction=outbound` 記錄
- [ ] 若 router 判斷需要 RAG，`retrieval_logs` 新增一筆記錄

## 8. 測試

執行全部測試：

```bash
pytest
```

執行單一測試檔：

```bash
pytest tests/test_line_webhook.py
pytest tests/test_router.py
```

## 9. 常見問題

**`Invalid LINE signature`**

- 確認 `LINE_CHANNEL_SECRET` 填的是正確的 Messaging API channel secret
- 確認 ngrok URL 已更新到 LINE Developers Console，且 webhook 指向這個本地 process

**`psql: could not translate host name ...`**

- 密碼含特殊字元導致 host 解析失敗，改用 `export PGPASSWORD='...'` 分離存放
- 確認 `SUPABASE_DB_URL` 不含密碼

**`psql: command not found`**

- 安裝 PostgreSQL client tools：`brew install libpq` (macOS)
- 或直接在 Supabase Dashboard 的 SQL Editor 貼上執行

**`seed_skills.py` 失敗（auth error）**

- 確認 `SUPABASE_URL` 與 `SUPABASE_SERVICE_ROLE_KEY` 正確
- 確認使用的是 service role key（不是 anon key）

**`ModuleNotFoundError: No module named 'openai'`**

- 表示使用的是系統 Python，而非 venv
- 改用 `.venv/bin/python` 執行，或先 `source .venv/bin/activate`

**`401 Missing scopes: api.responses.write`**

- OpenAI Restricted key 缺少 Responses → Write 權限
- 修改權限後需刪除重建舊 key，權限不會即時生效
- 詳見 [憑證取得教學](./credential-provisioning.md)

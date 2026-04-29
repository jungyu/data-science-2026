# 憑證取得教學（中文版）

最後更新：2026-04-29

本指南說明如何逐步取得本專案所需的六個憑證，並填入 `.env`。
完成後請繼續閱讀 [setup.md](./setup.md)。

需要取得的憑證：

| 步驟 | 憑證 / 動作 | 來源 |
|------|------------|------|
| 1-2 | `LINE_CHANNEL_SECRET` | LINE Official Account Manager → Messaging API 設定頁 |
| 1-3 | `LINE_CHANNEL_ACCESS_TOKEN` | LINE Developers Console → channel → Messaging API tab |
| 1-4 | 關閉自動回覆、啟用 Webhook | LINE Official Account Manager → 設定 → 回應設定 |
| 3 | `SUPABASE_URL` | Supabase Project Settings → API |
| 4 | `SUPABASE_SERVICE_ROLE_KEY` | Supabase Project Settings → API |
| 5 | `SUPABASE_DB_URL` | Supabase → Connect → 連線字串 |
| 6 | `OPENAI_API_KEY` | platform.openai.com → API keys |

---

## 開始前準備

請先確認以下帳號已可使用：

1. **LINE 帳號** — 可登入 LINE Official Account Manager 與 LINE Developers Console
2. **Supabase 帳號** — 可建立或管理 Project（[supabase.com](https://supabase.com)）
3. **OpenAI Platform 帳號** — 有 API 存取權限並已設定付款方式（[platform.openai.com](https://platform.openai.com)）

> ⚠️ 憑證只能放在 `.env` 或伺服器端的 secret store。絕對不能上傳到 git。

---

## `.env` 最終範本

完成所有步驟後，你的 `.env` 應該長這樣：

```bash
LINE_CHANNEL_SECRET=<步驟 1 複製的值>
LINE_CHANNEL_ACCESS_TOKEN=<步驟 2 複製的值>
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<步驟 4 複製的值>
SUPABASE_DB_URL=postgresql://postgres@db.<project-ref>.supabase.co:5432/postgres
PGPASSWORD=<你的原始密碼，不需要任何編碼>
OPENAI_API_KEY=<步驟 6 複製的值>
```

---

## 步驟 1｜取得 LINE 憑證（LINE_CHANNEL_SECRET + LINE_CHANNEL_ACCESS_TOKEN）

兩個 LINE 憑證可以在同一個流程中取得，依序完成 1-1 → 1-2 → 1-3 即可。

### 1-1 建立 LINE Official Account（已有可跳過）

1. 前往 [LINE Official Account Manager](https://manager.line.biz/)
2. 點選右上角「建立」→「建立 LINE 官方帳號」
3. 依序填入名稱、類別（個人 / 公司皆可）、同意條款
4. 完成後記下帳號 ID（格式類似 `@xxx`），URL 中也會出現帳號的數字 ID

### 1-2 申請開通 Messaging API → 取得 LINE_CHANNEL_SECRET

1. 前往以下網址（將 `[id]` 替換成你的帳號數字 ID）：
   ```
   https://manager.line.biz/account/[id]/setting/messaging-api
   ```
   或從 LINE Official Account Manager →「設定」→「Messaging API」也能到達同一頁
2. 點選「**開通**」申請啟用 Messaging API
3. 選擇或建立一個 **Provider**（可用你的名字或公司名）
4. 確認後頁面會顯示 **Channel secret**，點「**複製**」

> 📎 [官方教學文件](https://developers.line.biz/en/docs/messaging-api/getting-started/#create-oa-business-id)

### 填入 `.env`

```bash
LINE_CHANNEL_SECRET=<貼上剛才複製的 Channel secret>
```

> 若需要重新產生 secret，點「Reissue」，舊的 secret 會立即失效。

---

### 1-3 取得 LINE_CHANNEL_ACCESS_TOKEN

Messaging API 開通後，前往 LINE Developers Console 取得 Channel Access Token：

1. 前往以下網址（將 `[channel_id]` 替換成你的 Channel 數字 ID）：
   ```
   https://developers.line.biz/console/channel/[channel_id]
   ```
   或從 [LINE Developers Console](https://developers.line.biz/console/) → 選 Provider → 選剛建立的 channel
2. 上方頁籤選「**Messaging API**」
3. 往下捲到「**Channel access token**」區塊
4. 點選「**Issue**」取得一個 Long-lived token，點「**複製**」

> **選哪種 token？**
> - **Long-lived token**：操作最簡單，MVP 期間推薦使用
> - **Channel access token v2.1**：可設定到期時間，正式上線後建議換用

### 填入 `.env`

```bash
LINE_CHANNEL_ACCESS_TOKEN=<貼上剛才取得的 token>
```

---

### 1-4 關閉自動回覆、啟用 Webhook（必做）

LINE 官方帳號預設開啟「自動回應」，若不關閉，每則用戶訊息會同時觸發 webhook bot 回覆 **和** 內建自動回應，造成重複訊息。

**在 LINE Official Account Manager 關閉自動回應：**

1. 前往 [LINE Official Account Manager](https://manager.line.biz/) → 選取你的帳號
2. 左側選單 →「**設定**」→「**回應設定**」
3. 依照下表調整各項設定：

| 設定項目 | 建議值 | 說明 |
|----------|--------|------|
| 自動回應訊息 | **停用** | 避免和 bot 回覆重複出現 |
| 加入好友的歡迎訊息 | 停用（建議） | 可由 bot 自行處理歡迎訊息 |

**Webhook 啟用須等 App 跑起來後在步驟 7 一起設定**（需要先填入 ngrok URL，才能開啟 toggle）。

---

## 步驟 3｜取得 SUPABASE_URL

`SUPABASE_URL` 是 Supabase Project 的 REST API 基礎網址。

### 建立 Supabase Project（已有可跳過）

1. 前往 [supabase.com](https://supabase.com) 並登入
2. 若是首次使用，需先建立 **Organization**：
   - 點選「**New organization**」
   - 填入 Organization 名稱（個人使用填自己名字即可）
   - Plan 選「**Free**」→ 點「**Create organization**」
3. 在 Organization 下點選「**New project**」
4. 填寫：
   - **Name**：隨意（例如 `linebot-rag`）
   - **Database Password**：設一個強密碼，**立刻記下來**，後面 `SUPABASE_DB_URL` 會用到
   - **Region**：選離你最近的區域（台灣使用者可選 Northeast Asia - Tokyo）
4. 點「**Create new project**」，等待約 1 分鐘初始化完成

### 取得 Project URL

1. 進入 Project dashboard
2. 左側選單 →「**Project Settings**」→「**API**」
3. 找到「**Project URL**」，點「Copy」

格式通常是：

```
https://<project-ref>.supabase.co
```

### 填入 `.env`

```bash
SUPABASE_URL=https://<project-ref>.supabase.co
```

---

## 步驟 4｜取得 SUPABASE_SERVICE_ROLE_KEY

`SUPABASE_SERVICE_ROLE_KEY` 是高權限的伺服器端金鑰，本專案用來寫入 logs、seed skills，以及呼叫需要繞過 RLS 的 REST endpoint。

### 取得方式

1. 在同一個「**Project Settings**」→「**API**」頁面
2. 往下捲到「**Project API keys**」區塊
3. 找到「**service_role**」那一列，點「**Reveal**」→「**Copy**」

### 填入 `.env`

```bash
SUPABASE_SERVICE_ROLE_KEY=<貼上 service_role key>
```

> ⚠️ 這把 key 會繞過 Row Level Security，只能在後端使用，絕不能暴露給前端或截圖分享。

---

## 步驟 5｜取得 SUPABASE_DB_URL

`SUPABASE_DB_URL` 是 psql 連線字串，供 `apply_supabase_sql.sh` 套用 schema、functions、seed SQL 使用。

### 取得方式

1. 在 Project dashboard，左側選單點「**Connect**」
2. 頁籤選「**Direct connection**」
3. 複製顯示的連線字串，格式如下：
   ```
   postgresql://postgres:[YOUR-PASSWORD]@db.<project-ref>.supabase.co:5432/postgres
   ```
4. 將 `[YOUR-PASSWORD]` **替換成你在建立 Project 時設定的 Database Password**

### 填入 `.env`

密碼從 URL 移出，改由 `PGPASSWORD` 獨立存放，避免密碼含特殊字元（`@` `#` `%` 等）時 psql 解析錯誤：

```bash
SUPABASE_DB_URL=postgresql://postgres@db.<project-ref>.supabase.co:5432/postgres
PGPASSWORD=<你的原始密碼，不需要任何編碼>
```

### 驗證連線

使用 `export` 加單引號明確設定，避免 zsh 解析密碼特殊字元時出錯：

```bash
export SUPABASE_DB_URL='postgresql://postgres@db.<project-ref>.supabase.co:5432/postgres'
export PGPASSWORD='你的原始密碼'
psql "$SUPABASE_DB_URL" -c "select 1;"
```

出現 `?column? = 1` 代表連線成功。

---

## 步驟 6｜取得 OPENAI_API_KEY

`OPENAI_API_KEY` 用於 Router（意圖分類）、Generator（回覆生成）與 Embedding（RAG 向量化）。

### 取得方式

1. 前往 [platform.openai.com](https://platform.openai.com)，登入帳號
2. 左側選單點「**API keys**」
3. 點「**+ Create new secret key**」
4. 填入 Name（例如 `linebot-rag-local`）
5. **Permissions** 選「**Restricted**」，展開「Model capabilities」依下表設定：

| 子權限項目 | 設定值 | 原因 |
|------------|--------|------|
| List models | None | 不需要列出模型清單 |
| Responses (`/v1/responses`) | **Write** | Generator 回覆生成走此 API（必須是 Write，Request 不夠）|
| Chat completions (`/v1/chat/completions`) | **Request** | Router 意圖分類 |
| Embeddings (`/v1/embeddings`) | **Request** | RAG 向量化 |
| Text-to-speech、Realtime、Images、Moderations | None | 本專案不需要 |

> ⚠️ **Restricted key 修改權限後不會即時生效**，必須刪掉舊 key 重新建立新 key，並更新 `.env` 的 `OPENAI_API_KEY`。
>
> 若不確定權限是否設對，可先用 **All** 權限的 key 驗證 bot 能正常回應，確認後再換成 Restricted key。

6. 點「**Create secret key**」
7. **立刻複製**，這是唯一可以看到完整 key 的時機

### 設定月預算與用量通知

第一次使用 API 的帳號預設沒有預算上限，建議設定避免意外超支：

1. 左側選單點「**Limits**」
2. 在「**Organization budget**」點「**Edit budget**」，設定月上限（開發期間 $5 即可）
3. 點「**Add alert**」新增兩條通知：
   - **80%** usage alert → 提前預警
   - **100%** usage alert → 確認上限

### 費用估算（每次 LINE 對話）

| 步驟 | 模型 | 每次約花費 |
|------|------|-----------|
| Router 意圖分類 | gpt-5.4-mini | ~$0.001 |
| Generator 回覆生成 | gpt-5.5 | ~$0.01–0.03 |
| Embeddings（RAG） | text-embedding-3-small | 幾乎免費 |

$5 月預算約可跑 150–400 次完整對話，開發測試期間足夠。

### Tier 1 Rate Limit 注意事項

新帳號從 **Usage tier 1** 開始，每分鐘請求數（RPM）和 token 數（TPM）有上限。密集測試時若看到 **429 Too Many Requests** 錯誤，稍等一分鐘再試即可。累積消費超過 $50 後會自動升到 Tier 2，限制放寬。

### 填入 `.env`

```bash
OPENAI_API_KEY=<貼上剛才複製的 key>
```

---

## 完成後驗證清單

填完 `.env` 後，執行以下指令依序確認：

```bash
cd project-linebot-rag-skills
source .venv/bin/activate

# 1. 設定環境變數（單引號避免特殊字元被 shell 解析）
export SUPABASE_DB_URL='postgresql://postgres@db.<project-ref>.supabase.co:5432/postgres'
export PGPASSWORD='你的原始密碼'

# 2. 驗證 DB 連線
psql "$SUPABASE_DB_URL" -c "select 1;"

# 3. 套用 schema + seed（約需 30 秒）
./scripts/apply_supabase_sql.sh

# 4. 啟動 App
./scripts/run_local.sh
```

另開一個 terminal 確認 health check：

```bash
curl http://127.0.0.1:8000/health
# 期望：{"status":"ok"}
```

---

## 步驟 7｜設定 LINE Webhook URL（ngrok）

### 7-1 啟動 ngrok

App 必須已在執行（`./scripts/run_local.sh`），再另開一個 terminal：

```bash
ngrok http 8000
```

ngrok 會印出類似以下的輸出：

```
Forwarding  https://xxxx-xx-xxx-xxx-xxx.ngrok-free.app -> http://localhost:8000
```

複製 `https://` 開頭的那串 URL（每次重啟 ngrok 都會換）。

> ⚠️ **ngrok free 帳號限制**：每次重啟 URL 都會改變，需重新更新 LINE Webhook URL。如果需要固定 URL 可升級 ngrok 付費方案，或改用 Cloudflare Tunnel。

### 7-2 設定 LINE Webhook URL

1. 前往 [LINE Developers Console](https://developers.line.biz/console/)
2. 開啟你的 Messaging API channel →「**Messaging API**」頁籤
3. 找到「**Webhook URL**」欄位，填入：
   ```
   https://xxxx-xx-xxx-xxx-xxx.ngrok-free.app/api/line/webhook
   ```
   注意結尾必須是 `/api/line/webhook`
4. 點「**Update**」儲存
5. 開啟「**Use webhook**」toggle（需先填入 URL 才能開啟）
6. 點「**Verify**」— 出現 `Success` 代表 LINE 可以打到你的 server

### 7-3 傳訊息給 Bot 前的確認清單

Verify 成功後，傳訊息前先確認以下項目：

| 項目 | 確認方式 |
|------|----------|
| App 仍在執行 | terminal 沒有 error，`curl http://127.0.0.1:8000/health` 回 `{"status":"ok"}` |
| ngrok 仍在執行 | ngrok terminal 沒有關閉 |
| 自動回應已停用 | LINE Official Account Manager → 設定 → 回應設定（見步驟 1-4）|
| Use webhook 已開啟 | LINE Developers Console → Messaging API → Use webhook = ON |

### 7-4 觀察 App 日誌

傳訊息後，在 App 的 terminal 觀察輸出：

```
INFO: 127.0.0.1:xxxxx - "POST /api/line/webhook HTTP/1.1" 200 OK
```

出現 `POST /api/line/webhook 200` 代表 webhook 收到訊息並處理成功。

若看到 `400` 或 `500`，代表簽章驗證失敗或處理錯誤：
- `400`：`LINE_CHANNEL_SECRET` 可能填錯，確認 `.env` 的值與 Console 一致
- `500`：查看 terminal 的 traceback 找出錯誤原因

---

## 官方文件參考

- LINE Messaging API 入門：[developers.line.biz/en/docs/messaging-api/getting-started/](https://developers.line.biz/en/docs/messaging-api/getting-started/)
- LINE webhook 簽章驗證：[developers.line.biz/en/docs/messaging-api/verify-webhook-signature/](https://developers.line.biz/en/docs/messaging-api/verify-webhook-signature/)
- LINE channel access token：[developers.line.biz/en/docs/basics/channel-access-token/](https://developers.line.biz/en/docs/basics/channel-access-token/)
- Supabase API keys：[supabase.com/docs/guides/api/api-keys](https://supabase.com/docs/guides/api/api-keys)
- Supabase 連線字串：[supabase.com/docs/guides/database/connecting-to-postgres](https://supabase.com/docs/guides/database/connecting-to-postgres)
- OpenAI API key：[platform.openai.com/docs/quickstart](https://platform.openai.com/docs/quickstart)
- OpenAI 模型總覽：[platform.openai.com/docs/models](https://platform.openai.com/docs/models)
- OpenAI Embeddings 模型（確認 `EMBEDDING_MODEL` 最新名稱）：[platform.openai.com/docs/guides/embeddings](https://platform.openai.com/docs/guides/embeddings)

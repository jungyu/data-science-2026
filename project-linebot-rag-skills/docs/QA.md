# 常見問題排查（QA）

整理本專案從環境設定到 bot 正常回覆整個打通過程中，實際遭遇過的所有問題。每則問題包含症狀、根因與修法。

---

## 目錄

1. [Python 環境](#1-python-環境)
2. [Supabase 資料庫連線](#2-supabase-資料庫連線)
3. [Schema 套用與 Seed](#3-schema-套用與-seed)
4. [OpenAI API Key 權限](#4-openai-api-key-權限)
5. [LINE Webhook 設定](#5-line-webhook-設定)
6. [RAG 知識庫檢索](#6-rag-知識庫檢索)
7. [Bot 回覆異常](#7-bot-回覆異常)
8. [其他限制與注意事項](#8-其他限制與注意事項)

---

## 1. Python 環境

### 1-1 `ModuleNotFoundError: No module named 'openai'`（或其他 pydantic、httpx）

**症狀**

```
ModuleNotFoundError: No module named 'openai'
```

App terminal 出現 traceback，或 `seed_skills.py` 執行失敗。

**根因**

呼叫的 `python` 或 `uvicorn` 指向系統 Python（`/usr/bin/python3` 或 `/usr/local/bin/python3`），而非專案的 venv。系統 Python 沒有安裝 `openai`、`pydantic` 等套件。

可用以下指令確認：

```bash
which python     # 若不是 .../project-linebot-rag-skills/.venv/bin/python，就是問題所在
which uvicorn
```

**修法**

所有 Python 指令改用絕對路徑：

```bash
.venv/bin/python scripts/seed_skills.py
.venv/bin/uvicorn app.main:app --reload
```

或先啟用 venv 再執行：

```bash
source .venv/bin/activate
python scripts/seed_skills.py
```

專案腳本已改為固定路徑，`apply_supabase_sql.sh` 使用 `.venv/bin/python`，`run_local.sh` 使用 `.venv/bin/uvicorn`，正常情況下不需手動處理。

---

### 1-2 App 跑起來但套件行為異常

**症狀**

`./scripts/run_local.sh` 顯示 uvicorn 啟動，但 traceback 裡的 Python 路徑是 `/usr/local/lib/python3.12/...`。

**根因**

`run_local.sh` 原本直接呼叫 `uvicorn`，若系統 PATH 的 uvicorn 先於 venv 的 uvicorn，就會用系統版本啟動。

**修法**

`run_local.sh` 改為：

```bash
exec "${PROJECT_ROOT}/.venv/bin/uvicorn" app.main:app ...
```

若自行撰寫啟動指令，同樣改用 `.venv/bin/uvicorn`。

---

## 2. Supabase 資料庫連線

### 2-1 `psql: could not translate host name "^415@db.xxx.supabase.co"`

**症狀**

```
psql: error: could not translate host name "^415@db.xxx.supabase.co" to address: nodename nor servname provided, or not known
```

**根因**

Supabase 提供的 Direct Connection 字串格式為：

```
postgresql://postgres:[YOUR-PASSWORD]@db.<ref>.supabase.co:5432/postgres
```

若密碼含 `@`、`^`、`#`、`%` 等特殊字元，psql 會在解析 URI 時把密碼的一部分誤當作 host 名稱的前綴，導致 host 解析失敗。

**修法**

將密碼從 URL 移除，改用 `PGPASSWORD` 環境變數獨立存放：

```bash
# SUPABASE_DB_URL 不含密碼
SUPABASE_DB_URL=postgresql://postgres@db.<ref>.supabase.co:5432/postgres

# 密碼單獨設定
PGPASSWORD=你的原始密碼
```

psql 會自動讀取 `PGPASSWORD`，不需放進 URL。

---

### 2-2 `source .env` 後 `PGPASSWORD` 仍解析錯誤

**症狀**

`.env` 裡已設 `PGPASSWORD`，但 `source .env` 後執行 `psql` 仍然失敗，或密碼中的特殊字元被 shell 解析掉。

**根因**

zsh / bash 在 `source .env` 時，對未加引號的特殊字元（`^`、`!`、`@` 等）會嘗試解析，導致變數值被截斷或變形。

**修法**

不要用 `source .env` 設定含特殊字元的環境變數，改用 `export` 搭配**單引號**直接在 shell 設定：

```bash
export SUPABASE_DB_URL='postgresql://postgres@db.<ref>.supabase.co:5432/postgres'
export PGPASSWORD='你的原始密碼（含特殊字元原樣貼入）'
```

單引號內的內容 shell 完全不解析，原始字元原封不動傳入。

---

### 2-3 `psql: command not found`

**症狀**

```
psql: command not found
```

**根因**

系統未安裝 PostgreSQL client tools。

**修法**

macOS（Homebrew）：

```bash
brew install libpq
echo 'export PATH="/opt/homebrew/opt/libpq/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

或直接在 [Supabase Dashboard → SQL Editor](https://supabase.com/dashboard) 貼上 SQL 手動執行，不依賴本地 psql。

---

## 3. Schema 套用與 Seed

### 3-1 `seed_skills.py` 失敗：auth error / 403

**症狀**

```
supabase.exceptions.APIError: {"code": 403, "message": "..."}
```

或類似的認證錯誤。

**根因**

`SUPABASE_URL` 或 `SUPABASE_SERVICE_ROLE_KEY` 填錯，或使用的是 `anon` key（權限不足以寫入 `ai_skills`）。

**修法**

確認 `.env` 使用的是 **service_role** key（不是 anon key）：

- 前往 Supabase Dashboard → Project Settings → API
- 「Project API keys」區塊，`service_role` 那一列的值
- anon key 開頭通常較短，service_role key 較長

---

### 3-2 `ingest_markdown.py` 失敗：`400 Bad Request`

**症狀**

```
httpx.HTTPStatusError: Client error '400 Bad Request' for url https://...
```

執行 `ingest_markdown.py` 匯入知識庫時發生。

**根因**

`private_knowledge.content_hash` 欄位缺少 UNIQUE constraint。Supabase 的 upsert 操作（`on_conflict=content_hash`）要求衝突欄位必須有 UNIQUE 或 PRIMARY KEY constraint，否則回傳 400。

**修法**

在 Supabase Dashboard → SQL Editor 執行：

```sql
ALTER TABLE private_knowledge
  ADD CONSTRAINT private_knowledge_content_hash_key UNIQUE (content_hash);
```

當前 `supabase/schema.sql` 已包含此 constraint（`content_hash text not null unique`），全新部署不需手動補。若是舊資料庫，需執行上面的 ALTER TABLE。

---

### 3-3 `apply_supabase_sql.sh` 執行到一半失敗

**症狀**

Schema 套用成功，但 `seed_skills.py` 跑不起來（`ModuleNotFoundError`）。

**根因**

腳本原本呼叫系統 `python`，見 [1-1](#1-1-modulenotfounderror-no-module-named-openai或其他-pydantic、httpx)。

**修法**

腳本已改為使用 `.venv/bin/python`，確認使用最新版本的 `scripts/apply_supabase_sql.sh`。

---

## 4. OpenAI API Key 權限

### 4-1 `401 Missing scopes: api.responses.write`

**症狀**

```
openai.AuthenticationError: Error code: 401 - {'error': {'message': 'Missing scopes: api.responses.write', ...}}
```

Bot 有啟動，也收到訊息，但無法生成回覆。

**根因**

本專案 Router 和 Generator 都使用 **OpenAI Responses API**（`/v1/responses`），而非 Chat Completions API：

```python
response = await client.responses.create(model=..., input=...)
```

若使用 Restricted key，Responses 子權限必須設為 **Write**（不是 Read、也不是 None）。

**修法**

1. 前往 [platform.openai.com → API keys](https://platform.openai.com/api-keys)
2. 找到你的 Restricted key，點「Edit」
3. 在「Model capabilities」找到「**Responses**」，改為「**Write**」
4. **刪除舊 key，重新建立新 key** — 修改權限不會讓舊 key 即時生效
5. 更新 `.env` 的 `OPENAI_API_KEY`

若不確定權限設定是否正確，可先改用「All」權限的 key 驗證 bot 能正常運作，確認後再換回 Restricted key。

---

### 4-2 換了新 key 但還是 401

**症狀**

重新建立 Restricted key 後，`.env` 也更新了，但仍然 401。

**根因**

- App 沒有重啟，仍在使用舊 key 的 OpenAI client instance
- `.env` 雖然改了，但 `run_local.sh` 啟動的 process 讀取的是啟動當下的環境變數

**修法**

重新啟動 App（Ctrl+C 後再執行 `./scripts/run_local.sh`）。若使用 `--reload` 模式，改動 `.env` 不會自動熱重載，需手動重啟。

---

## 5. LINE Webhook 設定

### 5-1 傳訊息後 bot 完全沒反應（無 log）

**症狀**

App 有在跑，ngrok 也在跑，傳訊息後 App terminal 完全沒有 `POST /api/line/webhook` 的 log。

**根因（依可能性排序）**

1. Developers Console 的「**Use webhook**」toggle 沒有開啟
2. Webhook URL 尚未儲存（沒有點「Update」）
3. ngrok 已重啟但 Webhook URL 沒有更新

**修法**

前往 [LINE Developers Console](https://developers.line.biz/console/) → Messaging API 頁籤：

1. 確認 Webhook URL 填的是目前的 ngrok URL
2. 點「**Update**」儲存
3. 確認「**Use webhook**」toggle 是開啟的（綠色）
4. 點「**Verify**」確認 LINE 可以連到你的 server

---

### 5-2 `400 Invalid LINE signature`

**症狀**

```
HTTP 400 Bad Request: Invalid LINE signature
```

App terminal 出現，bot 不回應。

**根因**

- `LINE_CHANNEL_SECRET` 填錯（例如填了 Channel Access Token 的值）
- 請求不是從 LINE server 發來的（例如直接用 curl 測試，沒有帶正確 signature）

**修法**

確認 `.env` 的 `LINE_CHANNEL_SECRET` 與 LINE Developers Console → 你的 channel → Basic settings → Channel secret 一致。

---

### 5-3 用戶收到兩則回覆（bot 回覆 + 自動回應）

**症狀**

傳訊息後收到兩則：一則是 bot 生成的，另一則是 LINE 固定的自動回應訊息（例如「您好，感謝您的訊息...」）。

**根因**

LINE 官方帳號預設開啟「自動回應訊息」，Webhook 和自動回應會同時觸發。

**修法**

前往 [LINE Official Account Manager](https://manager.line.biz/) → 設定 → 回應設定：

- 「**自動回應訊息**」→ 改為「**停用**」

---

### 5-4 ngrok 重啟後 bot 沒反應

**症狀**

昨天正常的 bot，今天重開後傳訊息沒反應。

**根因**

ngrok 免費帳號每次重啟都會產生新的 URL，LINE Developers Console 的 Webhook URL 還是舊的。

**修法**

每次重啟 ngrok 後：

1. 從 ngrok terminal 複製新的 `https://xxxx.ngrok-free.app` URL
2. 前往 LINE Developers Console → Messaging API → Webhook URL
3. 貼入新 URL（結尾加 `/api/line/webhook`）
4. 點「Update」→ 點「Verify」確認連通

長期使用建議：升級 ngrok 付費方案取得固定網域，改用 Cloudflare Tunnel，或直接部署到 GCP Cloud Run。詳見 [tunnel.md](./tunnel.md)。

---

## 6. RAG 知識庫檢索

### 6-1 bot 回覆「目前知識庫沒有足夠資料」——但資料已匯入

**症狀**

`ingest_markdown.py` 執行成功（例如「Ingested 199 chunks」），但 bot 仍回覆「目前知識庫沒有足夠資料」。

**根因**

`rag_categories` 與 ingest 使用的 `--category` 不一致。Retriever 以 `WHERE category = ANY(rag_categories)` 過濾資料，若 category 不在白名單內，即使資料存在也查不到。

常見情況：

```
ingest 時：python scripts/ingest_markdown.py docs/RAG/*.md --category rag
Router 路由到：rag_categories = ["engineering", "architecture", "code"]
結果："rag" 不在白名單 → 查無資料
```

**修法**

確認以下三處的 category 值一致：

| 位置 | 確認方式 |
|------|---------|
| `skills/tech-architect/SKILL.md` 的 `rag_categories` | 必須包含 ingest 用的 category 值（如 `rag`） |
| `app/router/intent_router.py` 的 heuristic rag_categories | 同上 |
| `app/router/prompts.py` Rule 8 的合法 category 列表 | Router LLM 才會知道有哪些合法值 |

實際修法（三處都加上 `"rag"`）：

```yaml
# skills/tech-architect/SKILL.md
rag_categories:
  - engineering
  - architecture
  - code
  - rag        # ← 加這行
```

```python
# app/router/intent_router.py heuristic fallback
rag_categories=["engineering", "architecture", "code", "rag"],  # ← 加 "rag"
```

```
# app/router/prompts.py Rule 8
rag_categories 只從以下清單選擇：rag、engineering、architecture、code、...
```

---

### 6-2 bot 回覆帶有「層級：application」前綴

**症狀**

```
層級：application
目前知識庫沒有足夠資料。
RAG 是先檢索外部知識...
```

**根因**

`skills/tech-architect/SKILL.md` 的 system prompt 包含「先判斷問題屬於哪一層」的指令，模型把中間推理步驟（「層級：application」）直接輸出到回覆中。

**修法**

從 skill 的 system prompt 移除所有要求模型輸出分類前綴的指令。System prompt 只描述**回覆風格**，不要求模型輸出結構化的中間推理結果。

---

### 6-3 bot 每次都說「目前知識庫不足」，但有時又正常

**症狀**

有時 bot 能正常引用知識庫，有時卻說「目前知識庫沒有足夠資料」，同樣問題表現不一致。

**根因**

Router 使用 LLM 分類，LLM 每次輸出的 `rag_categories` 可能不同。若某次 LLM 輸出了不存在的 category（例如 `"rag-langchain"`），retriever 過濾後找不到資料。

**修法**

在 Router prompt 明確列出所有合法 category 值（見 `app/router/prompts.py` Rule 8），減少 LLM 自由發明不存在 category 的機率。同時確認 heuristic fallback 的 `rag_categories` 包含所有實際使用的 category。

---

## 7. Bot 回覆異常

### 7-1 bot 回覆「系統暫時無法完成此請求」

**症狀**

傳訊息給 bot，收到「系統暫時無法完成此請求，請稍後再試。」App terminal 看到 `POST /api/line/webhook 200 OK`，但沒有其他錯誤訊息。

**根因**

`webhook.py` 的 `generate_response` 呼叫被包在 `try/except` 裡，例外被靜默吞掉，只回傳 fallback 訊息，不顯示原始錯誤。

**修法**

在 except block 加上 logging：

```python
except Exception:
    logger.exception("generate_response failed")  # ← 印出完整 traceback
    responses = ["系統暫時無法完成此請求，請稍後再試。"]
```

加上後，App terminal 就會印出真正的錯誤原因（如 401、ModuleNotFoundError 等）。

---

### 7-2 傳訊息後 App terminal 有 `POST 200 OK`，但 LINE 沒有收到回覆

**症狀**

App 正常處理 webhook（log 顯示 200），但手機的 LINE 始終沒有收到 bot 回覆。

**根因（依可能性排序）**

1. `generate_response` 丟出例外，被 except 吞掉，Push API 沒有被呼叫
2. `LINE_CHANNEL_ACCESS_TOKEN` 填錯，Push API 呼叫失敗
3. Push API 呼叫成功，但訊息送達延遲（LINE server 偶爾有延遲）

**排查方式**

確認 `logger.exception` 已加入 except block（見 7-1），重傳訊息後觀察 terminal 有沒有 traceback。若有，依錯誤訊息排查。

---

## 8. 其他限制與注意事項

### 8-1 Supabase 需先建 Organization 才能建 Project

**症狀**

登入 Supabase 後，嘗試建立新 Project 時找不到入口，或沒有地方可以建 Project。

**說明**

Supabase 的 Project 必須隸屬於一個 Organization。首次使用時，需先點「**New organization**」建立 org（免費方案即可），再在 org 下建立 Project。

---

### 8-2 LINE 免費方案每月 200 則 Push Message 上限

**說明**

LINE 官方帳號免費方案的 Push Message 每月上限為 **200 則**（每封送到一位用戶算一則）。超出後需升級付費方案或等下個月重置。

個人開發測試不太會觸及，但若有多人測試或密集使用，需注意用量。

---

### 8-3 OpenAI Restricted key 修改權限後必須重建

**說明**

修改 OpenAI Restricted key 的子權限（例如把 Responses 從 None 改為 Write），**舊 key 不會即時生效**。必須刪掉舊 key，重新建立新 key，才能使用新的權限。

每次重建 key 後，記得更新 `.env` 的 `OPENAI_API_KEY` 並重啟 App。

---

### 8-4 知識庫匯入的 `--category` 值要預先規劃

**說明**

`ingest_markdown.py` 的 `--category` 值會直接存入 `private_knowledge.category`，並作為 retriever 的過濾條件。合法 category 值需在以下三處同步維護：

1. skill 定義的 `rag_categories`（`skills/*/SKILL.md`）
2. heuristic fallback 的 `rag_categories`（`app/router/intent_router.py`）
3. Router prompt 的合法 category 列表（`app/router/prompts.py`）

新增 category 時，記得同步更新以上三處，否則 retriever 的 category filter 會靜默過濾掉對應的資料。

---

### 8-5 IVFFlat 索引對小資料量效果有限

**說明**

`private_knowledge` 的向量索引使用 IVFFlat（`lists = 100`）。IVFFlat 在資料量少於 `lists` 數量時，向量搜尋的 recall 可能下降。

MVP 期間資料量通常遠低於 100 個 cluster 的最佳範圍，若遇到向量搜尋找不到明顯相關結果的問題，可考慮：

- 暫時移除 IVFFlat 索引，改用全表掃描（精確搜尋，小資料量仍夠快）
- 或降低 `lists` 參數值（例如改為 10）

---

## 快速對照表

| 症狀 | 最可能的根因 | 章節 |
|------|------------|------|
| `ModuleNotFoundError` | 系統 Python 而非 venv | [1-1](#1-1-modulenotfounderror-no-module-named-openai或其他-pydantic、httpx) |
| `could not translate host name` | 密碼含特殊字元 | [2-1](#2-1-psql-could-not-translate-host-name-415dbxxxsupabaseco) |
| ingest 400 Bad Request | content_hash 缺 UNIQUE constraint | [3-2](#3-2-ingest_markdownpy-失敗400-bad-request) |
| `401 Missing scopes: api.responses.write` | Restricted key 缺 Responses Write | [4-1](#4-1-401-missing-scopes-apiresponseswrite) |
| 傳訊息無反應（無 log） | Use webhook 未開啟 / URL 未更新 | [5-1](#5-1-傳訊息後-bot-完全沒反應無-log) |
| 收到兩則回覆 | 自動回應未關閉 | [5-3](#5-3-用戶收到兩則回覆bot-回覆--自動回應) |
| 「目前知識庫沒有足夠資料」 | rag_categories 與 --category 不對應 | [6-1](#6-1-bot-回覆目前知識庫沒有足夠資料——但資料已匯入) |
| 回覆帶「層級：application」 | skill prompt 輸出中間推理步驟 | [6-2](#6-2-bot-回覆帶有層級application-前綴) |
| 「系統暫時無法完成此請求」 | except 吞掉例外，需加 logging | [7-1](#7-1-bot-回覆系統暫時無法完成此請求) |

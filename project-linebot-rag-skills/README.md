# project-linebot-rag-skills

具備 skill 路由、Supabase RAG 檢索、短期對話記憶的私人 LINE Bot。

## 系統架構

```
LINE 用戶訊息
    ↓
LINE Webhook（FastAPI）
    ↓
Router — 意圖分類 + emotion 偵測（gpt-5.4-mini）
    ↓
Retriever — 向量 + 全文混合檢索（pgvector + pg_trgm）
    ↓
Generator — 依 skill system prompt 生成回覆（gpt-5.5）
    ↓
LINE Push API → 回覆用戶
```

每個環節獨立成模組，routing、retrieval、generation 分離，所有決策可透過 schema 與 log 追蹤。

## 專案結構

```
project-linebot-rag-skills/
├── app/
│   ├── generator/      # 回覆生成（responder、prompts、formatter）
│   ├── line/           # LINE webhook、client、schemas
│   ├── rag/            # embedder、retriever、reranker、chunker
│   ├── router/         # 意圖路由、emotion 偵測、prompts
│   ├── skills/         # skill loader、registry
│   ├── storage/        # Supabase client、各 repo
│   ├── config.py
│   ├── dependencies.py
│   └── main.py
├── docs/
│   ├── adr/            # 架構決策紀錄
│   ├── credential-provisioning.md  # 憑證取得教學（正體中文）
│   └── setup.md        # 本地啟動指南
├── scripts/
│   ├── apply_supabase_sql.sh   # 套用 schema + seed
│   ├── ingest_markdown.py      # 將 markdown 寫入知識庫
│   ├── run_local.sh            # 啟動 App
│   └── seed_skills.py          # 將 skills/ 寫入 Supabase
├── skills/             # skill 定義（SKILL.md）
├── supabase/           # schema.sql、functions.sql、seed.sql
└── tests/
```

## 快速啟動

### 1. 建立環境

```bash
cp .env.example .env
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 2. 填入憑證

編輯 `.env`，填入以下六個必要值（詳見 [憑證取得教學](./docs/credential-provisioning.md)）：

```bash
LINE_CHANNEL_SECRET=...
LINE_CHANNEL_ACCESS_TOKEN=...
OPENAI_API_KEY=...
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=...
SUPABASE_DB_URL=postgresql://postgres@db.<project-ref>.supabase.co:5432/postgres
PGPASSWORD=...          # 密碼含特殊字元時分離存放，psql 自動讀取
```

### 3. 套用 DB Schema

```bash
# 設定環境變數（單引號避免特殊字元被 shell 解析）
export SUPABASE_DB_URL='postgresql://postgres@db.<project-ref>.supabase.co:5432/postgres'
export PGPASSWORD='你的原始密碼'

# 驗證連線
psql "$SUPABASE_DB_URL" -c "select 1;"

# 套用 schema + functions + seed + skills（約 30 秒）
./scripts/apply_supabase_sql.sh
```

### 4. 啟動 App

```bash
./scripts/run_local.sh
```

Health check：

```bash
curl http://127.0.0.1:8000/health
# 期望：{"status":"ok"}
```

### 5. 打通 LINE Webhook（ngrok）

```bash
# 另開 terminal
ngrok http 8000
```

取得 `https://xxxx.ngrok-free.app` 後，前往 [LINE Developers Console](https://developers.line.biz/console/)：

1. Messaging API → Webhook URL 填入：`https://xxxx.ngrok-free.app/api/line/webhook`
2. 點「Update」→ 開啟「Use webhook」toggle → 點「Verify」

### 6. 匯入知識庫

```bash
# 範例：匯入 RAG 相關文件
.venv/bin/python scripts/ingest_markdown.py \
  docs/RAG/*.md \
  docs/RAG/LangGraph/*.md \
  --category rag
```

## 環境變數說明

| 變數 | 用途 |
|------|------|
| `LINE_CHANNEL_SECRET` | 驗證 webhook 簽章 |
| `LINE_CHANNEL_ACCESS_TOKEN` | 呼叫 LINE Push API |
| `OPENAI_API_KEY` | Router / Generator / Embeddings |
| `ROUTER_MODEL` | 意圖分類模型（預設 gpt-5.4-mini） |
| `GENERATOR_MODEL` | 回覆生成模型（預設 gpt-5.5） |
| `EMBEDDING_MODEL` | 向量化模型（預設 text-embedding-3-small） |
| `SUPABASE_URL` | Supabase REST API 基礎網址 |
| `SUPABASE_SERVICE_ROLE_KEY` | 高權限 server-side key |
| `SUPABASE_DB_URL` | psql 連線字串（不含密碼） |
| `PGPASSWORD` | DB 密碼（獨立存放，避免特殊字元解析問題） |

## 已知注意事項

**密碼含特殊字元（`@` `#` `^` 等）**

`SUPABASE_DB_URL` 不要把密碼放在 URL 裡，改用 `PGPASSWORD` 獨立存放，否則 psql 會把密碼的一部分誤解析為 host。

**OpenAI API Key 權限**

需使用 Restricted key，必須開啟的子權限：

| 子權限 | 值 |
|--------|-----|
| Responses (`/v1/responses`) | Write |
| Chat completions (`/v1/chat/completions`) | Request |
| Embeddings (`/v1/embeddings`) | Request |

修改 Restricted key 權限後需刪除重建，舊 key 不會即時生效。

**`apply_supabase_sql.sh` 使用 venv Python**

腳本已固定使用 `.venv/bin/python`，不依賴系統 PATH。

**知識庫 category 須與 skill 的 `rag_categories` 對應**

`ingest_markdown.py` 的 `--category` 值必須出現在對應 skill 的 `rag_categories` 清單裡，否則 retriever 的 category filter 會找不到資料。

**ngrok free 帳號每次重啟 URL 都會改變**

需重新更新 LINE Developers Console 的 Webhook URL。

## 測試

```bash
pytest
```

## 文件

- [憑證取得教學](./docs/credential-provisioning.md)
- [本地啟動指南](./docs/setup.md)
- [架構決策紀錄](./docs/adr/)

# project-linebot-rag-skills

具備 skill 路由、Supabase RAG 檢索、短期對話記憶的私人 LINE Bot。
支援多 AI provider：**OpenAI、Anthropic Claude、Google Gemini、GitHub Copilot**，切換只需改 `.env`。

## 系統架構

```
LINE 用戶訊息
    ↓
LINE Webhook（FastAPI）
    ↓
LangGraph StateGraph
  ├─ route       — 意圖分類 + skill 解析 + emotion 偵測
  ├─ retrieve    — 向量 + 全文混合檢索（pgvector + pg_trgm）
  ├─ generate    — 依 skill system prompt 生成回覆
  └─ push        — 透過 LINE Push API 回覆用戶
```

每個環節獨立成模組，routing、retrieval、generation 分離，所有決策可透過 schema 與 log 追蹤。

### 為什麼用 LangGraph

P1（[spec-12](./docs/ai-agent/specs/spec-12-graph-refactor.md)）把線性 pipeline 重構為 LangGraph StateGraph，**行為等價但結構升級**。原因：

- **可分支**：後續 phase（[spec-15](./docs/ai-agent/specs/spec-15-sufficiency-clarify.md) sufficiency 判定 / [spec-17](./docs/ai-agent/specs/spec-17-judge-reflection.md) judge）需要條件 edge，線性函式串接做不到
- **可迴圈**：reflection 需要「judge fail → 重生成」迴圈
- **可並行**：multi-seed 檢索（[spec-14](./docs/ai-agent/specs/spec-14-multi-seed-retrieval.md)）需要 fan-out / fan-in
- **可審查**：state 一覽即知，每個 node 的 input / output 明確

完整教學藍圖見 [docs/ai-agent/plan/roadmap.md](./docs/ai-agent/plan/roadmap.md)；LangGraph 概念補充見 [docs/RAG/LangGraph](./docs/RAG/LangGraph/)。

## 專案結構

```
project-linebot-rag-skills/
├── app/
│   ├── ai/
│   │   ├── factory.py          # build_llm() / build_embedder() — provider 選擇邏輯
│   │   └── providers/
│   │       ├── openai_provider.py      # OpenAI Responses API + Embeddings
│   │       ├── anthropic_provider.py   # Anthropic Claude Messages API
│   │       └── gemini_provider.py      # Google Gemini generate + embed
│   ├── generator/      # 回覆生成（responder、prompts、formatter）
│   ├── line/           # LINE webhook、client、schemas
│   ├── rag/            # embedder protocol、retriever、reranker、chunker
│   ├── router/         # 意圖路由 protocol、emotion 偵測、prompts
│   ├── skills/         # skill loader、registry
│   ├── storage/        # Supabase client、各 repo
│   ├── config.py
│   ├── dependencies.py
│   └── main.py
├── docs/
│   ├── credential-provisioning.md  # 憑證取得教學（正體中文）
│   └── setup.md                    # 本地啟動指南
├── scripts/
│   ├── apply_supabase_sql.sh   # 套用 schema + seed
│   ├── ingest_markdown.py      # 將 markdown 寫入知識庫
│   ├── run_local.sh            # 啟動 App（macOS / Linux）
│   ├── run_local.ps1           # 啟動 App（Windows PowerShell）
│   ├── run_local.bat           # 啟動 App（Windows cmd.exe）
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
python -m pip install -e ".[dev]"
```

Windows PowerShell：

```powershell
Copy-Item .env.example .env
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

### 2. 選擇 AI Provider 並填入憑證

編輯 `.env`，先選擇 provider，再填入對應金鑰（詳見 [憑證取得教學](./docs/credential-provisioning.md)）。

**OpenAI（預設）**

```bash
AI_PROVIDER=openai
OPENAI_API_KEY=sk-...
ROUTER_MODEL=gpt-4.1-mini
GENERATOR_MODEL=gpt-4.1
EMBEDDING_MODEL=text-embedding-3-small
```

**Anthropic Claude**

```bash
AI_PROVIDER=claude
ANTHROPIC_API_KEY=sk-ant-...
ROUTER_MODEL=claude-haiku-4-5-20251001
GENERATOR_MODEL=claude-sonnet-4-6
# pip install -e ".[claude]"
```

**Google Gemini**

```bash
AI_PROVIDER=gemini
GEMINI_API_KEY=AIza...
# 穩定版
ROUTER_MODEL=gemini-2.5-flash
GENERATOR_MODEL=gemini-2.5-pro
EMBEDDING_MODEL=gemini-embedding-2
EMBEDDING_PROVIDER=gemini
# 試驗版（3.1 preview）
# ROUTER_MODEL=gemini-3.1-flash-lite-preview
# GENERATOR_MODEL=gemini-3.1-pro-preview
# EMBEDDING_MODEL=gemini-embedding-2-preview
# python -m pip install -e ".[gemini]"
```

**GitHub Copilot**

```bash
AI_PROVIDER=github_copilot
GITHUB_COPILOT_TOKEN=ghu_...
GITHUB_COPILOT_BASE_URL=https://api.githubcopilot.com
ROUTER_MODEL=gpt-4o-mini
GENERATOR_MODEL=gpt-4o
```

> `EMBEDDING_PROVIDER` 可與 `AI_PROVIDER` 分開設定。例如用 Claude 生成、OpenAI 做 embedding。

此外填入 LINE 與 Supabase 必要值：

```bash
LINE_CHANNEL_SECRET=...
LINE_CHANNEL_ACCESS_TOKEN=...
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=...
SUPABASE_DB_URL=postgresql://postgres@db.<project-ref>.supabase.co:5432/postgres
PGPASSWORD=...
```

### 3. 安裝 Provider SDK（非 OpenAI 時）

```bash
# Claude
python -m pip install -e ".[claude]"

# Gemini
python -m pip install -e ".[gemini]"

# 全部
python -m pip install -e ".[all-providers]"
```

> ⚠️ **必須用 `python -m pip`，不要直接用 `pip`。**
> venv 裡若同時存在多個 Python 版本目錄，`pip` 可能對應到舊版解譯器，導致套件裝進錯誤的 site-packages，啟動時拋出 `ModuleNotFoundError`。

### 4. 套用 DB Schema

```bash
export SUPABASE_DB_URL='postgresql://postgres@db.<project-ref>.supabase.co:5432/postgres'
export PGPASSWORD='你的原始密碼'

# 驗證連線
psql "$SUPABASE_DB_URL" -c "select 1;"

# 套用 schema + functions + seed + skills（約 30 秒）
./scripts/apply_supabase_sql.sh
```

### 5. 啟動 App

```bash
./scripts/run_local.sh
```

Windows PowerShell：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_local.ps1
```

Windows cmd.exe：

```cmd
scripts\run_local.bat
```

Health check：

```bash
curl http://127.0.0.1:8000/health
# 期望：{"status":"ok"}
```

### 6. 打通 LINE Webhook（ngrok）

```bash
ngrok http 8000
```

取得 `https://xxxx.ngrok-free.app` 後，前往 [LINE Developers Console](https://developers.line.biz/console/)：

1. Messaging API → Webhook URL 填入：`https://xxxx.ngrok-free.app/api/line/webhook`
2. 點「Update」→ 開啟「Use webhook」toggle → 點「Verify」

### 7. 匯入知識庫

```bash
.venv/bin/python scripts/ingest_markdown.py \
  docs/RAG/*.md \
  --category rag
```

## 環境變數說明

### 通用

| 變數 | 用途 |
|------|------|
| `LINE_CHANNEL_SECRET` | 驗證 webhook 簽章 |
| `LINE_CHANNEL_ACCESS_TOKEN` | 呼叫 LINE Push API |
| `SUPABASE_URL` | Supabase REST API 基礎網址 |
| `SUPABASE_SERVICE_ROLE_KEY` | 高權限 server-side key |
| `SUPABASE_DB_URL` | psql 連線字串（不含密碼） |
| `PGPASSWORD` | DB 密碼（獨立存放，避免特殊字元解析問題） |

### AI Provider

| 變數 | 用途 |
|------|------|
| `AI_PROVIDER` | LLM 後端：`openai` \| `claude` \| `gemini` \| `github_copilot`（預設 `openai`） |
| `EMBEDDING_PROVIDER` | Embedding 後端：`openai` \| `gemini`（預設 `openai`） |
| `ROUTER_MODEL` | 意圖分類用模型 |
| `GENERATOR_MODEL` | 回覆生成用模型 |
| `EMBEDDING_MODEL` | 向量化模型 |
| `OPENAI_API_KEY` | OpenAI 金鑰 |
| `ANTHROPIC_API_KEY` | Anthropic Claude 金鑰 |
| `GEMINI_API_KEY` | Google Gemini 金鑰 |
| `GITHUB_COPILOT_TOKEN` | GitHub Copilot token |
| `GITHUB_COPILOT_BASE_URL` | Copilot API endpoint（預設 `https://api.githubcopilot.com`） |

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

**Claude / Gemini 無內建 embedding 時**

Anthropic 目前不提供 embedding API。使用 `AI_PROVIDER=claude` 時，建議保留 `EMBEDDING_PROVIDER=openai` 並填入 `OPENAI_API_KEY`。

**`apply_supabase_sql.sh` 使用 venv Python**

腳本已固定使用 `.venv/bin/python`，不依賴系統 PATH。

**知識庫 category 須與 skill 的 `rag_categories` 對應**

`ingest_markdown.py` 的 `--category` 值必須出現在對應 skill 的 `rag_categories` 清單裡，否則 retriever 的 category filter 會找不到資料。

**ngrok free 帳號每次重啟 URL 都會改變**

需重新更新 LINE Developers Console 的 Webhook URL。

**venv 多 Python 版本導致 `ModuleNotFoundError`**

venv 內若同時存在 `python3.12`、`python3.14` 等多個目錄，`pip` 指令可能對應到舊版 Python，把套件裝進錯誤的 site-packages。所有安裝指令都應使用 `python -m pip install`，確保套件裝進當前解譯器對應的目錄。

## 測試

```bash
pytest
```

## 文件

- [憑證取得教學（LINE + OpenAI + Supabase）](./docs/credential-provisioning.md)
- [Anthropic Claude API 憑證申請指南](./docs/claude-credential-provisioning.md)
- [Google Gemini 憑證申請指南](./docs/gemini-credential-provisioning.md)
- [GitHub Copilot / GitHub Models API 憑證申請指南](./docs/github-copilot-credential-provisioning.md)
- [本地啟動指南](./docs/setup.md)

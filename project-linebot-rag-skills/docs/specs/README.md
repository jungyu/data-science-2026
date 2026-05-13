# 系統規格文件

本文件為 `project-linebot-rag-skills` 的實作規格索引，涵蓋 API、資料結構、處理流程與整合契約。程式碼是最終的 source of truth；本文件補充「為什麼這樣設計」與「各元件的界面契約」。

---

## 目錄

1. [API Endpoints](#api-endpoints)
2. [處理流程（Message Pipeline）](#處理流程message-pipeline)
3. [Router 輸出契約（RouterResult）](#router-輸出契約routerresult)
4. [Skill 定義格式（SKILL.md）](#skill-定義格式skillmd)
5. [資料庫 Schema](#資料庫-schema)
6. [混合檢索 SQL 函式（match_private_knowledge）](#混合檢索-sql-函式match_private_knowledge)
7. [知識庫匯入規格](#知識庫匯入規格)
8. [Analytics CLI](#analytics-cli)
9. [環境變數](#環境變數)
10. [OpenAI API 使用規格](#openai-api-使用規格)

---

## API Endpoints

| Method | Path | 說明 |
|--------|------|------|
| `GET` | `/health` | 健康檢查，回傳 `{"status": "ok"}` |
| `POST` | `/api/line/webhook` | LINE Messaging API webhook 入口 |

### `POST /api/line/webhook`

**Headers**

| Header | 必填 | 說明 |
|--------|------|------|
| `x-line-signature` | ✅ | HMAC-SHA256 簽章，用 `LINE_CHANNEL_SECRET` 驗證 |
| `Content-Type` | ✅ | `application/json` |

**Request Body（LINE 原生格式）**

```json
{
  "destination": "<bot_user_id>",
  "events": [
    {
      "type": "message",
      "replyToken": "...",
      "source": { "type": "user", "userId": "U..." },
      "timestamp": 1714000000000,
      "message": { "id": "...", "type": "text", "text": "使用者訊息" }
    }
  ]
}
```

**Response**

```json
{ "ok": true }
```

簽章驗證失敗回傳 `400 Bad Request`。

**行為**

- 每則 `type == "message"` 且 `message.type == "text"` 的事件，在 Background Task 非同步處理
- Webhook handler 本身在 5 秒內回應 200，不等待 LLM 結果
- 實際回覆透過 LINE Push API 非同步發送

---

## 處理流程（Message Pipeline）

實際 pipeline 由 **LangGraph StateGraph** 串接（`app/graph/rag_graph.py`），不是線性呼叫；
依 `GRAPH_VARIANT` 切換 basic / selfrag / reflection 三變體（spec-19）。下圖為 reflection
變體（功能最完整）的節點順序：

```
LINE 用戶傳訊息
        ↓
[webhook] /api/line/webhook
    — 驗 HMAC-SHA256 簽章 → 失敗 400
    — 解析事件 → 寫 line_messages(inbound)
    — 帶 thread_id config 呼叫 graph.ainvoke（spec-21）
        ↓
═══ LangGraph 開始 ═══
        ↓
[input_guard] 字數 / poison 檢查（spec-30）
        ↓
[route] IntentRouter → RouterResult（target_skill / emotion / mode）
        ↓
[extract_features] LLM 抽取主題 / qualifier / intent（spec-13）
        ↓
[fan_out_to_retrieve] 多 seed 並行向量+全文檢索（spec-14）
        ↓
[fuse_scores] RRF 合併（spec-14）
        ↓
[rerank] Cross-encoder 重排，失敗靜默 fallback 回 RRF（spec-04 / spec-28）
        ↓
[check_sufficiency] 判斷檢索是否足夠（spec-15）
    │ insufficient → [clarify] 反問使用者，跳過後續
    └ sufficient   ↓
[build_answer_contract] Stage 1：抽取 key_findings / citations / caveats（spec-16）
        ↓
[render_narrative] Stage 2：依 mode + emotion 寫成 markdown（spec-01/02/16）
        ↓
[judge] 4 軸結構化評分（spec-17）
    │ pass               ↓
    │ retry (≤ max)      → 回到 render_narrative，帶 feedback
    │ fail + hitl_enabled → [human_review] interrupt before push（spec-21）
    │ fail + !hitl       → force_push 加品質警告 prefix
        ↓
[push] 透過 channels[name] 推送
═══ LangGraph 結束 ═══
        ↓
[outbound 落庫]
    — 若 graph 被 interrupt：mark_pending_review，不送 outbound、不 push
    — 否則寫 line_messages(outbound)，tracer 寫 .traces/{thread_id}.json
      （OBSERVABILITY_PERSIST=true 時同步寫 Supabase graph_traces，spec-22）
```

### Variant 差異對照

| Variant | clarify | rerank | judge | 用途 |
|---------|---------|--------|-------|------|
| `basic` | ✗ | ✗ | ✗ | 教學最小骨架，無自我檢查 |
| `selfrag` | ✓ | ✓ | ✗ | 偵測資料不足時反問，但不評分 |
| `reflection` | ✓ | ✓ | ✓ | 加 4 軸 judge + retry / HITL（預設） |

---

## Router 輸出契約（RouterResult）

Router 呼叫 LLM 後輸出 JSON，由 `RouterResult` Pydantic model 驗證。

```python
class RouterResult(BaseModel):
    target_skill: SkillId       # 目標 skill
    is_rag_required: bool       # 是否需要 RAG 檢索
    rag_query: str              # 改寫後的檢索 query
    rag_categories: list[str]   # category 白名單（對應 ingest --category）
    emotion_state: EmotionState # 情緒狀態
    response_mode: ResponseMode # 回覆模式
    confidence: float           # 0.0 ~ 1.0，< 0.55 觸發 heuristic fallback
```

### SkillId（合法值）

| 值 | 對應情境 |
|----|---------|
| `tech_architect` | 系統架構、DB、API、RAG、部署 |
| `data_scientist` | 資料分析、模型評估、實驗設計 |
| `business_strategist` | 商業模式、定價、市場策略 |
| `philosophical_dialectic` | 價值觀、邏輯辯證、概念分析 |
| `emotional_calibration` | 焦慮、孤獨、挫折、現實校準 |
| `general_chat` | 一般閒聊、未匹配情境的保底 |

### EmotionState（合法值）

`neutral` / `curious` / `urgent` / `confused` / `frustrated` / `anxious` / `reflective`

### ResponseMode（合法值）

| 值 | 說明 |
|----|------|
| `brief` | 簡短直接 |
| `structured` | 分點結構化 |
| `step_by_step` | 逐步說明 |
| `decision_support` | 決策框架輔助 |
| `debugging` | 除錯導向 |
| `reflection` | 反思與情緒回應 |

### rag_categories 合法值

`rag` / `engineering` / `architecture` / `code` / `analytics` / `experiments` / `metrics` / `strategy` / `market` / `product` / `philosophy` / `notes`

**Single source of truth**：[`app/router/categories.py::VALID_RAG_CATEGORIES`](../../app/router/categories.py)（spec-03）。
- `IntentRouter` heuristic 與 prompt 的合法清單都應從此匯入，避免兩端 drift
- LLM 輸出若含非法 category，會在 `_normalize_result` 階段被過濾

> **重要**：`rag_categories` 的值必須與 `ingest_markdown.py --category` 使用的值對應，否則 retriever 的 category filter 會找不到資料。

---

## Skill 定義格式（SKILL.md）

每個 skill 放在 `skills/<skill_id>/SKILL.md`，包含 YAML frontmatter 與 system prompt。

### Frontmatter 欄位

```yaml
---
skill_id: tech_architect          # 對應 SkillId，必填
name: 技術架構師                   # 顯示名稱，必填
category: engineering             # skill 本身的分類
version: 0.1.0                    # 語意版本
description: "..."                # 一行描述
use_when:                         # Router 判斷依據（文字描述）
  - 使用者詢問系統設計
avoid_when:                       # Router 判斷依據（文字描述）
  - 使用者只是情緒抒發
default_temperature: 0.3          # Generator 溫度（0.0 ~ 1.0）
rag_categories:                   # 此 skill 可用的 RAG category 白名單
  - engineering
  - architecture
  - code
  - rag
---

{system_prompt 正文}
```

### System Prompt 設計原則

- 描述**如何回覆**，不描述要輸出什麼結構
- 不要要求模型輸出分類前綴（如「層級：xxx」），這些會直接出現在使用者看到的訊息中
- 若 RAG context 不足，鼓勵模型誠實說明，而非憑空生成

### Skill 載入來源（spec-08）

| `SKILL_SOURCE` | 行為 |
|---|---|
| `file`（預設）| 從 `skills/*/SKILL.md` 載入，修改後需重啟 |
| `supabase`    | 從 `ai_skills` 表載入，每 `SKILL_RELOAD_INTERVAL` 秒（預設 600s）重新拉取 |

`supabase` 模式由 `app/main.py::lifespan` 啟動背景 task；拉取失敗保留上一輪 skills，
不中斷服務。runtime 替換透過 `app/dependencies.py::replace_skill_registry`。

---

## 資料庫 Schema

完整 DDL 見 [`supabase/schema.sql`](../../supabase/schema.sql)。

### `ai_skills`

| 欄位 | 型別 | 說明 |
|------|------|------|
| `skill_id` | `text PK` | Skill 唯一識別碼 |
| `name` | `text` | 顯示名稱 |
| `description` | `text` | 一行描述 |
| `category` | `text` | Skill 分類 |
| `system_prompt` | `text` | Generator 使用的 system prompt |
| `use_when` | `text[]` | 適用情境說明 |
| `avoid_when` | `text[]` | 不適用情境說明 |
| `default_temperature` | `numeric` | 預設 0.4 |
| `default_top_p` | `numeric` | 預設 0.9 |
| `version` | `text` | 預設 `0.1.0` |
| `enabled` | `boolean` | 是否啟用 |

### `private_knowledge`

| 欄位 | 型別 | 說明 |
|------|------|------|
| `id` | `uuid PK` | 自動產生 |
| `source_id` | `text` | 來源識別碼（通常為檔名） |
| `source_type` | `text` | 來源類型，預設 `markdown` |
| `title` | `text` | chunk 標題 |
| `content` | `text` | chunk 內容 |
| `content_hash` | `text UNIQUE` | 內容雜湊，用於 upsert 去重 |
| `category` | `text` | 對應 ingest `--category` 值 |
| `tags` | `text[]` | 標籤 |
| `embedding` | `vector(1536)` | OpenAI text-embedding-3-small 向量 |
| `search_vector` | `tsvector` | 自動由 title + content 產生 |
| `knowledge_version` | `integer` | 預設 1 |

### `line_messages`

| 欄位 | 型別 | 說明 |
|------|------|------|
| `id` | `uuid PK` | 自動產生 |
| `line_user_id` | `text` | LINE 使用者 ID |
| `direction` | `text` | `inbound`（收）或 `outbound`（發） |
| `message_text` | `text` | 訊息內容 |
| `skill_id` | `text` | 使用的 skill（outbound 才有） |
| `router_result` | `jsonb` | Router 完整輸出（outbound 才有） |
| `rag_used` | `boolean` | 是否有使用 RAG |

### `retrieval_logs`

| 欄位 | 型別 | 說明 |
|------|------|------|
| `id` | `uuid PK` | 自動產生 |
| `line_user_id` | `text` | 查詢的使用者 |
| `query` | `text` | 改寫後的檢索 query |
| `skill_id` | `text` | 當時的 skill |
| `category_filter` | `text[]` | 使用的 category 篩選 |
| `retrieved_ids` | `uuid[]` | 最終回傳的 chunk ID 列表 |
| `scores` | `jsonb` | 每個 chunk 的 vector / keyword / combined score |

### `prompt_cache`（spec-05，由 `ResponseGenerator` 自動讀寫）

| 欄位 | 型別 | 說明 |
|------|------|------|
| `id` | `uuid PK` | 自動產生 |
| `cache_key` | `text UNIQUE` | `sha256(skill_id:knowledge_version:normalized_input)` |
| `user_input` | `text` | 原始使用者輸入 |
| `skill_id` | `text` | 使用的 skill |
| `knowledge_version` | `integer` | 對應的 `private_knowledge` 最大版本號 |
| `response_text` | `text` | 快取的回覆內容 |

**快取條件**：`is_rag_required=True` 且 `rag_chunks` 非空才寫入；避免快取「知識庫不足」回覆。
`knowledge_version` 變動後 cache_key 自然失配 → 重新生成（不需手動清表）。

### `hitl_pending_reviews`（spec-21，opt-in 啟用 HITL 才需要建表）

| 欄位 | 型別 | 說明 |
|------|------|------|
| `thread_id` | `text PK` | LangGraph thread_id（webhook 用 `line-{user_id}-{message_id}`） |
| `line_user_id` | `text` | 對應的使用者 |
| `status` | `text` | `pending` / `approved` / `revised` / `dropped` |
| `created_at` / `updated_at` | `timestamptz` | — |

HITL interrupt 觸發時由 `messages_repo.mark_pending_review` 寫入；CLI
`scripts/review_queue.py` 列出與處理。

### `graph_traces`（spec-22，opt-in，由 `OBSERVABILITY_PERSIST=true` 啟用）

| 欄位 | 型別 | 說明 |
|------|------|------|
| `id` | `uuid PK` | 自動產生 |
| `thread_id` / `variant` | `text` | 對應 graph invocation |
| `started_at` / `finished_at` | `timestamptz` | 計算 total_duration_ms |
| `total_input_tokens` / `total_output_tokens` | `int` | 跨整次 graph 累積 |
| `total_cost_usd` | `numeric(10,6)` | 依 `app/observability/pricing.py` 估算 |
| `payload` | `jsonb` | `GraphTracer.finalize()` 完整原始 events |

套用：`bash scripts/apply_supabase_traces.sh`（讀 `SUPABASE_DB_URL`）。
本機 `.traces/*.json` 永遠會寫；Supabase 是額外的 opt-in 出口。

---

## 混合檢索 SQL 函式（match_private_knowledge）

**函式簽章**

```sql
match_private_knowledge(
  query_embedding vector(1536),
  query_text      text,
  match_count     int  DEFAULT 8,
  category_filter text[] DEFAULT null
)
```

**回傳欄位**

| 欄位 | 說明 |
|------|------|
| `id` | chunk UUID |
| `title` | chunk 標題 |
| `content` | chunk 內容 |
| `category` | 資料 category |
| `metadata` | 額外 metadata |
| `vector_score` | cosine similarity（0 ~ 1） |
| `keyword_score` | ts_rank 關鍵字分數 |
| `combined_score` | RRF 合併分數（最終排序依據） |

**RRF 計算公式**

```
combined_score = 1/(60 + vector_rank) + 1/(60 + keyword_rank)
```

兩路各取 `match_count × 3` 筆候選，再以 RRF 合併後取最終 `match_count` 筆。`category_filter = null` 時不過濾，搜尋全庫。

---

## 知識庫匯入規格

實際匯入由 `scripts/ingest.py` 統一 CLI 提供六個子命令（spec-25），各對應一個
`app/ingest/ingesters/*.py`：

```bash
.venv/bin/python scripts/ingest.py markdown --paths "docs/RAG/*.md" --category rag
.venv/bin/python scripts/ingest.py pdf      --paths "docs/sources/*.pdf" --category regulations
.venv/bin/python scripts/ingest.py csv      --path data/faq.csv --mode row_per_doc \
                                            --text-columns question,answer --category faq
.venv/bin/python scripts/ingest.py notion   --database-id <id> --category company-wiki
.venv/bin/python scripts/ingest.py web      --urls urls/nextjs.txt --category nextjs
.venv/bin/python scripts/ingest.py articles --category nextjs
```

**Notion ingestion**（spec-25）支援兩種模式：
- `--database-id`：列出 database 所有 page
- `--page-id`：單一 page
- heading_1~3 自動切 `section_path`；`content_hash = sha256(page_id + last_edited_time)`
  讓 IngestionPipeline 跳過未變動的 page（增量更新）

**Notion Export ZIP**（spec-07）走另一個入口：
```bash
.venv/bin/python scripts/ingest_notion_export.py <dir-or-zip> [--category notion]
```
解壓 .zip 後走 MarkdownIngester；不打 Notion API。

**舊版相容** `scripts/ingest_markdown.py` 仍保留作 thin wrapper（內部走同一條
IngestionPipeline），既有 cron / docs 不需改。

**統一行為**

1. Ingester yield Document（含 sections / source_id / content_hash / category / tags / metadata）
2. IngestionPipeline 把 section 切 chunk、依 `content_hash` upsert
3. 呼叫 embedding provider（由 `EMBEDDING_PROVIDER` 決定）產生向量
4. Upsert 到對應 store（由 `KNOWLEDGE_STORE_BACKEND` 決定：supabase / sqlite_vec / pinecone）

**注意**

- `--category` 的值必須出現在 `app/router/categories.py::VALID_RAG_CATEGORIES`、對應 skill
  的 `rag_categories` 清單與 Router prompt 的合法值列表中，否則 retriever 找不到資料
- `private_knowledge.content_hash` 需有 UNIQUE constraint，upsert 才能正常執行

---

## Analytics CLI

### `scripts/analyze_retrieval.py`（spec-09）

讀 `retrieval_logs` 表回答常見品質問題，四種互斥模式：

```bash
# 1. 近 7 天找不到資料的 query（依出現次數排序）
.venv/bin/python scripts/analyze_retrieval.py --empty-hits [--days 7]

# 2. 命中但分數低於 threshold 的 query（升序）
.venv/bin/python scripts/analyze_retrieval.py --low-score [--threshold 0.3] [--days 7]

# 3. 各 category 被查詢的次數 + 平均最高分
.venv/bin/python scripts/analyze_retrieval.py --category-stats [--days 30]

# 4. 模糊比對特定 query 的所有歷史記錄
.venv/bin/python scripts/analyze_retrieval.py --query "LangGraph 是什麼"
```

PostgREST 不直接支援 GROUP BY 與 jsonb path filter；CLI 拉 rows 後在 Python
端聚合（個人使用量級已足夠）。純函式聚合邏輯在
[`app/eval/retrieval_analytics.py`](../../app/eval/retrieval_analytics.py)，便於單測。

### `scripts/trace.py`（spec-22）

```bash
.venv/bin/python scripts/trace.py show <thread_id>
.venv/bin/python scripts/trace.py summary --last 50
.venv/bin/python scripts/trace.py top --by duration --limit 5
```

讀 `.traces/{thread_id}.json`；資料來源由每次 `graph.ainvoke` 結束時 TracerRegistry
寫入（`OBSERVABILITY_ENABLED=true`，預設開）。

### `scripts/review_queue.py`（spec-21）

```bash
.venv/bin/python scripts/review_queue.py list
.venv/bin/python scripts/review_queue.py show <thread_id>
.venv/bin/python scripts/review_queue.py approve <thread_id>
.venv/bin/python scripts/review_queue.py revise <thread_id> --text "..."
.venv/bin/python scripts/review_queue.py drop <thread_id>
```

HITL 啟用後（`HITL_ENABLED=true`），judge fail 達 retry 上限或命中
`hitl_always_review_skills` 時，graph 在 `human_review` 前 interrupt；
此 CLI 透過 LangGraph `Command(resume=...)` 完成審核並 push。

---

## 環境變數

完整清單與預設值請看 [`app/config.py`](../../app/config.py)；以下列舉常用與本輪
新增的設定（spec-08 / spec-21 / spec-22）。

### 必填

| 變數 | 說明 |
|------|------|
| `LINE_CHANNEL_SECRET` | Webhook 簽章驗證 |
| `LINE_CHANNEL_ACCESS_TOKEN` | LINE Push API 授權 |
| `OPENAI_API_KEY` | Router / Generator / Embeddings（OpenAI provider） |
| `SUPABASE_URL` | Supabase REST API 基礎網址 |
| `SUPABASE_SERVICE_ROLE_KEY` | 高權限 server-side key |
| `SUPABASE_DB_URL` | psql 連線字串（**不含密碼**；spec-21 postgres checkpointer 也用此值） |
| `PGPASSWORD` | DB 密碼（分離存放，避免特殊字元解析問題） |

### 模型與檢索

| 變數 | 預設值 | 說明 |
|------|--------|------|
| `AI_PROVIDER` | `openai` | `openai` / `claude` / `gemini` / `github_copilot` |
| `EMBEDDING_PROVIDER` | `openai` | `openai` / `gemini` / `huggingface` |
| `ROUTER_MODEL` | `gpt-4.1-mini` | 意圖分類 LLM |
| `GENERATOR_MODEL` | `gpt-4.1` | 回覆生成 LLM |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | 向量化模型 |
| `KNOWLEDGE_TOP_K` | `8` | 初始召回 chunk 數 |
| `FINAL_CONTEXT_K` | `4` | Rerank 後傳入 Generator 的 chunk 數 |
| `LINE_MAX_MESSAGE_CHARS` | `4500` | LINE 單則訊息最大字元數 |
| `ROUTER_CONFIDENCE_THRESHOLD` | `0.55` | 低於此值觸發 heuristic fallback |
| `RERANKER_ENABLED` | `false` | spec-04/28；缺 key 時靜默 fallback 回 RRF |
| `COHERE_API_KEY` | — | 啟用 Cohere reranker；空字串時自動降級為 RRF |

### Graph / Judge / HITL（spec-15 / 17 / 19 / 21）

| 變數 | 預設值 | 說明 |
|------|--------|------|
| `GRAPH_VARIANT` | `reflection` | `basic` / `selfrag` / `reflection` |
| `JUDGE_ENABLED` | `true` | 開啟 4 軸 judge 評分 |
| `JUDGE_MIN_AXIS` | `6` | 各軸最低分；低於即 fail |
| `JUDGE_MIN_MEAN` | `7.0` | 平均最低分 |
| `MAX_REFLECTION_RETRIES` | `1` | retry 上限，達上限後強推或進 HITL |
| `HITL_ENABLED` | `false` | 啟用後 judge fail 達上限會 interrupt 等待人工 review |
| `HITL_ALWAYS_REVIEW_SKILLS` | `[]` | 列入的 skill 無條件 interrupt |
| `CHECKPOINT_BACKEND` | `memory` | `memory` / `sqlite` / `postgres` / `none` |
| `CHECKPOINT_SQLITE_PATH` | `.checkpoints/rag.db` | sqlite 路徑 |

### Skill 載入（spec-08）

| 變數 | 預設值 | 說明 |
|------|--------|------|
| `SKILL_SOURCE` | `file` | `file`（讀 `skills/*/SKILL.md`）或 `supabase`（讀 `ai_skills` 表）|
| `SKILL_RELOAD_INTERVAL` | `600` | 秒；`supabase` 模式下定時重新拉取，`<=0` 停用 |

### Observability（spec-22）

| 變數 | 預設值 | 說明 |
|------|--------|------|
| `OBSERVABILITY_ENABLED` | `true` | 寫本機 `.traces/*.json` |
| `OBSERVABILITY_PERSIST` | `false` | 同時寫 Supabase `graph_traces` 表（需先跑 `apply_supabase_traces.sh`） |
| `TRACE_DIR` | `.traces` | 本機 trace 檔目錄 |

---

## OpenAI API 使用規格

此專案使用 **Responses API**（`/v1/responses`），而非 Chat Completions API。

```python
response = await client.responses.create(
    model="gpt-4.1-mini",   # 或 gpt-4.1
    input=prompt,           # 字串或 message list
)
return response.output_text
```

### Restricted Key 必要權限

使用 OpenAI Restricted Key 時，需開啟以下子權限：

| 子權限 | 端點 | 必要值 |
|--------|------|--------|
| Responses | `/v1/responses` | **Write** |
| Chat completions | `/v1/chat/completions` | Request |
| Embeddings | `/v1/embeddings` | Request |

> Responses 需設定為 **Write**（不是 Read）才能呼叫 `responses.create`。修改 Restricted key 權限後需**刪除重建**，舊 key 不會即時生效。

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
7. [知識庫匯入規格（ingest_markdown.py）](#知識庫匯入規格ingest_markdownpy)
8. [環境變數](#環境變數)
9. [OpenAI API 使用規格](#openai-api-使用規格)

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

```
LINE 用戶傳訊息
        ↓
[1] Signature Verification
    — HMAC-SHA256(body, CHANNEL_SECRET)
    — 驗證失敗 → 400，流程終止
        ↓
[2] Save Inbound Message
    — 寫入 line_messages（direction=inbound）
        ↓
[3] Build Recent History
    — 從 line_messages 取最近 N 輪對話摘要
        ↓
[4] Intent Router
    — LLM（Responses API）解析意圖 → RouterResult JSON
    — confidence < 0.55 或 LLM 失敗 → heuristic fallback
        ↓
[5] Skill Lookup
    — 從 skill_registry 取 target_skill 的 SkillDefinition
    — 找不到 → fallback 到 general_chat
        ↓
[6] RAG Retrieval（is_rag_required = true 時執行）
    — embed(rag_query) → pgvector 向量搜尋
    — tsvector 全文搜尋
    — RRF 合併排名，取 top_k=8
    — reranker 取最終 final_context_k=4
    — 寫入 retrieval_logs
        ↓
[7] Response Generation
    — render_synthesis_prompt（skill system prompt + RAG context + history）
    — Generator LLM（Responses API）生成回覆
    — is_rag_required=true 且無 chunks → 前綴「目前知識庫沒有足夠資料」
    — split_for_line 切割至 4500 字以內
        ↓
[8] LINE Push API
    — push_text 發送回覆給使用者
        ↓
[9] Save Outbound Message
    — 寫入 line_messages（direction=outbound，含 router_result、rag_used）
```

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

### `prompt_cache`

| 欄位 | 型別 | 說明 |
|------|------|------|
| `id` | `uuid PK` | 自動產生 |
| `cache_key` | `text UNIQUE` | 快取索引鍵 |
| `user_input` | `text` | 原始使用者輸入 |
| `skill_id` | `text` | 使用的 skill |
| `knowledge_version` | `integer` | 對應的知識庫版本 |
| `response_text` | `text` | 快取的回覆內容 |

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

## 知識庫匯入規格（ingest_markdown.py）

```bash
.venv/bin/python scripts/ingest_markdown.py <files...> --category <category>
```

| 參數 | 說明 |
|------|------|
| `<files...>` | 一或多個 Markdown 檔案路徑，支援 glob |
| `--category` | 寫入 `private_knowledge.category` 的值 |

**行為**

1. 讀取每個 `.md` 檔案
2. 依 heading 或固定大小切割成 chunk
3. 計算每個 chunk 的 `content_hash`（SHA-256）
4. 呼叫 OpenAI `text-embedding-3-small` 產生 1536 維向量
5. Upsert 到 `private_knowledge`（以 `content_hash` 判斷是否重複）

**注意**

- `--category` 的值必須出現在對應 skill 的 `rag_categories` 清單與 Router prompt 的合法值列表中，否則 retriever 找不到資料
- `private_knowledge.content_hash` 需有 UNIQUE constraint，upsert 才能正常執行

---

## 環境變數

| 變數 | 必填 | 預設值 | 說明 |
|------|------|--------|------|
| `LINE_CHANNEL_SECRET` | ✅ | — | Webhook 簽章驗證 |
| `LINE_CHANNEL_ACCESS_TOKEN` | ✅ | — | LINE Push API 授權 |
| `OPENAI_API_KEY` | ✅ | — | Router / Generator / Embeddings |
| `SUPABASE_URL` | ✅ | — | Supabase REST API 基礎網址 |
| `SUPABASE_SERVICE_ROLE_KEY` | ✅ | — | 高權限 server-side key |
| `SUPABASE_DB_URL` | ✅ | — | psql 連線字串（**不含密碼**） |
| `PGPASSWORD` | ✅ | — | DB 密碼（分離存放，避免特殊字元解析問題） |
| `ROUTER_MODEL` | — | `gpt-4.1-mini` | 意圖分類 LLM |
| `GENERATOR_MODEL` | — | `gpt-4.1` | 回覆生成 LLM |
| `EMBEDDING_MODEL` | — | `text-embedding-3-small` | 向量化模型 |
| `KNOWLEDGE_TOP_K` | — | `8` | 初始召回 chunk 數 |
| `FINAL_CONTEXT_K` | — | `4` | Rerank 後傳入 Generator 的 chunk 數 |
| `LINE_MAX_MESSAGE_CHARS` | — | `4500` | LINE 單則訊息最大字元數 |
| `ROUTER_CONFIDENCE_THRESHOLD` | — | `0.55` | 低於此值觸發 heuristic fallback |

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

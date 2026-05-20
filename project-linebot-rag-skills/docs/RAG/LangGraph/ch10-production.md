# 第 10 章：Production 化與常見地雷

> 「Demo 跑起來」和「上線不會被罵」是兩件事。

## Production 升級清單

從 ch09 的 MVP 到能上線，你還欠這些：

### 🟥 必做
- [ ] Checkpointer 換 PostgreSQL（不用 InMemorySaver）
- [ ] LLM 加 timeout / retry
- [ ] LLM 改用 structured output（JSON mode）
- [ ] Retrieval 換 pgvector hybrid
- [ ] 加 telemetry（latency、token、cost）

### 🟨 強烈建議
- [ ] Reranker（cross-encoder）
- [ ] Grounding check（獨立節點）
- [ ] Citation builder（最終答案附引用）
- [ ] Safety gate（高風險領域）
- [ ] Human review UI

### 🟩 進階
- [ ] Trace replay dashboard
- [ ] A/B test 不同 reflection prompt
- [ ] Cost budget 控制（state 加 token quota）

## pgvector：你的最佳搭配

### 為什麼 pgvector？

- ✅ 已有 PostgreSQL → 不需要新組件
- ✅ SQL join、metadata filter、audit 一條龍
- ✅ 適合 < 1M 筆資料（你的場景剛好）

### Schema 起手式

```sql
create extension if not exists vector;

create table knowledge_atoms (
    id uuid primary key default gen_random_uuid(),
    domain text not null,        -- tcm / bazi / law
    category text not null,      -- pulse / disease / rule
    title text,
    content text not null,
    embedding_text text not null,
    embedding vector(1536),
    tags text[],
    metadata jsonb,
    source text,
    confidence numeric default 1.0,
    created_at timestamptz default now()
);

create index idx_atoms_embedding
on knowledge_atoms
using ivfflat (embedding vector_cosine_ops)
with (lists = 100);
```

### Hybrid 查詢（推薦）

```sql
select *,
       1 - (embedding <=> $1::vector) as similarity
from knowledge_atoms
where domain = 'tcm'        -- 先 filter
  and category = 'pulse'
order by embedding <=> $1::vector
limit 10;
```

> ⚠️ 常見錯誤：`embedding <=> $1` 會報 `operator does not exist`。要寫 `$1::vector` 強制轉型。

## 不要只用 vector：要 + Rule Engine

純 vector 處理不了：

- 干支關係（八字）
- 五行相剋（中醫）
- 病機推導
- Rule chaining

### Rule schema

```sql
create table rule_definitions (
    id uuid primary key default gen_random_uuid(),
    rule_type text,
    condition jsonb not null,
    conclusion jsonb not null,
    priority int default 0,
    created_at timestamptz default now()
);
```

### 範例（中醫）

```json
condition: {"pulse": ["floating", "rapid"], "symptoms": ["fever"]}
conclusion: {"pattern": "外感風熱", "treatment": "清熱解表"}
```

### 完整 Hybrid 流程

```
1. vector retrieve → 找語義相似
2. rule match → 找符合條件
3. merge → rerank
4. generate
```

## Observability：兩張一定要建的表

### retrieval_log
```sql
create table retrieval_log (
    id uuid primary key default gen_random_uuid(),
    query text,
    rewritten_query text,
    retrieved_ids uuid[],
    scores float[],
    created_at timestamptz default now()
);
```

### agent_trace
```sql
create table agent_trace (
    id uuid primary key default gen_random_uuid(),
    thread_id text,
    step text,
    state jsonb,
    created_at timestamptz default now()
);
```

有了這兩張表，使用者抱怨時你能完整重建現場。

## 高風險領域的特別架構

中醫 / 命理 / 法規 / 財務建議補三個節點：

```
[Generate Draft] → [Grounding Check] → [Reflect] ──┐
                                                    │
                                          ┌─────────┼─────────┐
                                          ↓                   ↓
                                    [Citation Builder]  [Human Review]
                                          ↓
                                     [Safety Gate]
                                          ↓
                                       [Finalize]
```

- **Grounding Check**：獨立檢查每個 claim 是否有文件支持
- **Citation Builder**：產出可追溯引用
- **Safety Gate**：finalize 前最後一道安全濾網

## 常見地雷集

### 🪤 地雷 1：Decision 用自由文字
模型某天回 `"REWRITE"`、某天回 `"rewrite the query"`，router 崩。
→ 用 `Literal` + Hard guard。

### 🪤 地雷 2：忘記 max_attempts
無限迴圈、帳單爆掉。
→ State 一定要有 `attempt_count`。

### 🪤 地雷 3：InMemorySaver 上 production
重啟就沒了。
→ 用 PostgreSQL checkpointer。

### 🪤 地雷 4：把 routing 邏輯放進 LLM prompt
模型自己判要走哪。
→ 模型只產 decision，graph 才 routing。

### 🪤 地雷 5：Reflect node 順便改答案
責任爆炸，很難 audit。
→ 拆出 `regenerate` node。

### 🪤 地雷 6：retrieved_docs 直接塞 JSON 給模型
格式太亂，reflect 判錯。
→ 用 `format_docs_for_prompt()`。

### 🪤 地雷 7：節點偷用全域變數
Checkpoint 還原失敗。
→ 跨節點的東西全進 state。

### 🪤 地雷 8：Vector 查詢忘記 `::vector` 轉型
PostgreSQL 報錯。
→ `embedding <=> $1::vector`。

### 🪤 地雷 9：沒有 retrieval_history
系統一直查同樣 query。
→ State 加 `retrieval_history`，retrieve node 檢查重複。

### 🪤 地雷 10：用 vector 處理規則邏輯
五行生剋、干支關係 vector 做不到。
→ 加 rule engine。

## 成本控制

長迴圈會燒錢。建議在 state 加：

```python
total_input_tokens: int
total_output_tokens: int
estimated_cost_usd: float
```

routing 時可以加：

```python
if state["estimated_cost_usd"] > state["budget_usd"]:
    return "human_review"
```

## 測試策略

### 單元測試（每個 node）
```python
def test_reflect_returns_human_review_when_ungrounded():
    state = {"draft_answer": "胡說的", "retrieved_docs": [], ...}
    result = reflect_answer(state)
    assert result["reflection"]["decision"] in ["human_review", "retrieve_again"]
```

### 路由測試
```python
def test_router_forces_human_review_at_max_attempts():
    state = {"attempt_count": 3, "max_attempts": 3, "reflection": {"decision": "finalize"}}
    assert route_after_reflection(state) == "human_review"
```

### 整合測試（golden cases）
建一組 (query, expected_path) pair，每次部署前跑一遍。

## 一張總圖：完整 Production 架構

```
                ┌─────────────────────┐
                │  Frontend / API     │
                └──────────┬──────────┘
                           ↓
                ┌──────────────────────┐
                │   LangGraph Agent    │
                │  (StateGraph + CP)   │
                └──┬────────────────┬──┘
                   │                │
        ┌──────────↓──────┐    ┌────↓─────────┐
        │  PostgreSQL     │    │  LLM Provider│
        │  + pgvector     │    │  (OpenAI...) │
        │  + checkpoints  │    └──────────────┘
        │  + rules        │
        │  + traces       │
        └─────────────────┘
                   ↓
           ┌───────────────┐
           │ Observability │
           │ (Grafana ...) │
           └───────────────┘
```

## 最後給你的三句話

1. **LLM 負責想內容，Graph 負責管流程。**
2. **失敗不該是終局，而是中間步驟。**
3. **這套架構不是讓 AI 更聰明，是讓 AI 的錯誤可以被系統修正。**

把這三句話刻在團隊白板上。

---

恭喜你讀完整份指南。下一步建議：

- 把 [ch09 程式碼](ch09-langgraph-in-action.md) 真的跑起來
- 換上你的 retriever
- 寫第一個 reflection prompt
- 觀察它在你的真實資料上怎麼失敗
- 然後回頭讀對應章節調整

> 「Read once. Build twice. Reflect forever.」

---

## 想完整 production 化？

本章是概念導論。如果你要把這套架構真的跑成 24/7 服務，請接著看 **[Lesson 5：Production 化](../../Lesson_5_Production/README.md)**——以本專案 [`app/`](../../../app/) 真實程式為主軸，10 章漸進實作：Supabase schema、Repo pattern、Channel 抽象、Router、Query 理解、Multi-seed 檢索、兩階段生成、Judge 迴圈、觀測安全、部署清單。

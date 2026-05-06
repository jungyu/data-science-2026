# Spec-12：線性 → LangGraph 等價重構（P1）

## 背景

現行 `app/line/webhook.py` 的 `process_text_event()` 以線性函式呼叫串起 `IntentRouter` → `RAGRetriever` → `ResponseGenerator` → LINE Push。流程清楚但無法表達條件分支、迴圈、並行，無法承載後續 P2–P4 的功能。

本 spec 的目標是**把線性流程重構為 LangGraph，但行為完全一致**——同一則輸入，前後輸出 byte-for-byte 相同（或僅日誌時間戳差異）。學生在這個階段學會 graph 的基本骨架，下一個 phase 才在 graph 上加新功能。

## 設計

### Graph 結構（P1 等價形式）

```
START → route → retrieve → generate → push → END
```

四個 node 全部線性串接，**沒有條件 edge、沒有迴圈**。每個 node 都是現有服務的薄包裝，不改服務本身的介面。

### State Schema

```python
class RAGState(TypedDict, total=False):
    # 輸入
    user_input: str
    line_user_id: str
    recent_history: str

    # route 產出
    router_result: RouterResult

    # retrieve 產出
    rag_chunks: list[KnowledgeChunk]
    rag_context: str

    # generate 產出
    responses: list[str]
```

`total=False` 讓部分欄位在早期 node 尚未填入時不報錯。後續 phase 會擴充欄位。

### 節點對應

| Node | 包裝對象 | 輸入欄位 | 輸出欄位 |
|------|---------|---------|---------|
| `route` | `IntentRouter.route()` | `user_input`, `recent_history` | `router_result` |
| `retrieve` | `RAGRetriever.retrieve()` | `router_result` | `rag_chunks`, `rag_context` |
| `generate` | `ResponseGenerator.generate()` | `router_result`, `rag_context` | `responses` |
| `push` | `LineClient.push_messages()` | `responses`, `line_user_id` | —（side effect）|

### 等價性保證

- 所有 LLM / DB / API 呼叫由原 service 物件完成，graph 層不直接呼叫
- 不重新計算任何中間結果
- 錯誤處理路徑保持一致（exception 直接往上拋，不在 node 內吞）

### Router LLM 溫度設定

> ⚠️ **Router 應使用低 temperature（建議 0.0–0.2）**（[W1 e2e 驗收](../examples/w1-e2e-verification.md) §「摩擦 3」）
>
> Router LLM 的工作是把 user query 分類到 skill + 決定 `is_rag_required`。同一個 query
> 在不同跑次得到不同 routing 結果（例：`tech_architect` vs `general_chat`）會讓 demo
> 失去一致性，學生 review 自己的 graph 行為時也很困惑。
>
> 修法：在 provider 呼叫 router LLM 時顯式傳 `temperature=0.0`（或極低）。
> Generator 與 narrative renderer **不需要**這個調整——它們的 creativity 對輸出有正面意義。
>
> 進階：用 [task-20 evaluation framework](../tasks/task-20-evaluation.md) 跑 N 次同 case
> 計 majority vote，量化 router 一致性。

## 介面契約

**新增**：`app/graph/__init__.py`、`app/graph/state.py`、`app/graph/nodes.py`、`app/graph/rag_graph.py`

```python
# app/graph/state.py
class RAGState(TypedDict, total=False): ...

# app/graph/nodes.py
async def route_node(state: RAGState, *, services: RuntimeServices) -> RAGState: ...
async def retrieve_node(state: RAGState, *, services: RuntimeServices) -> RAGState: ...
async def generate_node(state: RAGState, *, services: RuntimeServices) -> RAGState: ...
async def push_node(state: RAGState, *, services: RuntimeServices) -> RAGState: ...

# app/graph/rag_graph.py
def build_rag_graph(services: RuntimeServices) -> CompiledGraph: ...
```

**修改**：`app/line/webhook.py`

```python
# Before
await process_text_event(event, services)  # 線性串接函式

# After
graph = services.rag_graph  # 已在 startup 時 build
await graph.ainvoke(initial_state)
```

**移除**：原線性串接函式（避免兩套並存造成學生混淆）。

**依賴新增**：`langgraph >= 0.2.0`（pyproject.toml）。

## 驗收標準

- 重構前後，10 則代表性訊息（涵蓋各 skill）的回覆**逐字相同**
- `webhook.py` 不再直接呼叫 `IntentRouter` / `RAGRetriever` / `ResponseGenerator`
- `app/graph/rag_graph.py` 可單獨 import 並產出可執行 graph（不依賴 LINE webhook 環境）
- 既有 pytest 測試全數通過，不需修改測試案例
- README 與 `docs/setup.md` 更新「為何引入 LangGraph」段落

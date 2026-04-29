# 第 7 章：State Schema 設計

> State 是流程的中樞神經。設計爛，整個 Agent 都會跟著爛。

## State 設計四原則

### 原則 1：把「內容」和「控制」分開

State 裡要清楚分區：

```python
class AgentState(TypedDict):
    # ─── 內容 ───
    user_query: str
    retrieved_docs: List[RetrievalDoc]
    draft_answer: str
    final_answer: str

    # ─── 評估 ───
    reflection: Reflection

    # ─── 控制 ───
    attempt_count: int
    max_attempts: int

    # ─── 觀測 ───
    route_history: List[RouteLog]
    retrieval_history: List[RetrievalLog]
    errors: List[str]
```

### 原則 2：decision 必須是 Literal

```python
Decision = Literal["rewrite_query", "retrieve_again", "finalize", "human_review"]
```

❌ 不要用 `str`。型別系統就是你的第一道防線。

### 原則 3：一定要有 attempt_count

否則無限迴圈。

### 原則 4：reflection 要保留 reasoning

不只 decision，還要記理由。否則 audit 時看不懂為什麼走那條路。

## 最小可用版（MVP）

```python
from typing import TypedDict, List, Literal

Decision = Literal["rewrite_query", "retrieve_again", "finalize", "human_review"]

class RetrievalDoc(TypedDict):
    id: str
    source: str
    score: float
    text: str

class Reflection(TypedDict):
    grounded: bool
    sufficient: bool
    decision: Decision
    reasoning: str

class AgentState(TypedDict):
    user_query: str
    rewritten_query: str
    retrieved_docs: List[RetrievalDoc]
    draft_answer: str
    final_answer: str
    reflection: Reflection
    attempt_count: int
    max_attempts: int
```

## 正式版（Production）

```python
from typing import TypedDict, List, Literal, Dict, Any

Decision = Literal["rewrite_query", "retrieve_again", "finalize", "human_review"]

class RetrievalDoc(TypedDict):
    id: str
    source: str
    score: float
    text: str
    metadata: Dict[str, Any]

class Reflection(TypedDict):
    grounded: bool
    sufficient: bool
    relevance_score: float
    coverage_score: float
    hallucination_risk: float
    missing_topics: List[str]
    reasoning: str
    decision: Decision

class RouteLog(TypedDict):
    from_node: str
    to_node: str
    reason: str
    at: str

class RetrievalLog(TypedDict):
    query: str
    doc_ids: List[str]
    retrieved_at: str

class AgentState(TypedDict, total=False):
    # input
    user_query: str

    # query stages
    normalized_query: str
    rewritten_query: str

    # retrieval
    retrieved_docs: List[RetrievalDoc]
    top_k: int

    # generation
    draft_answer: str
    final_answer: str

    # reflection
    reflection: Reflection

    # loop control
    attempt_count: int
    max_attempts: int

    # observability
    trace_id: str
    route_history: List[RouteLog]
    retrieval_history: List[RetrievalLog]
    errors: List[str]
```

> 💡 **Brain Power**
> `total=False` 是什麼意思？為什麼正式版要用？

<details>
<summary>解答</summary>

`total=False` 表示 TypedDict 的所有欄位都是「可選」的。這對 LangGraph 很重要，因為每個 node 只回傳「要更新的部分」，不是整份 state。如果用 `total=True`（預設），你每次都要回傳所有欄位，超痛苦。
</details>

## 為什麼 retrieval_history 很重要？

避免系統在錯方向上一直查同樣的 query。

```python
def retrieve_node(state):
    query = state["rewritten_query"]

    # 檢查是否查過
    history = state.get("retrieval_history", [])
    if any(h["query"] == query for h in history):
        # 同一個 query 不要重查，強制改寫
        return {"reflection": {..., "decision": "rewrite_query"}}

    docs = retriever.search(query)
    return {
        "retrieved_docs": docs,
        "retrieval_history": history + [{
            "query": query,
            "doc_ids": [d["id"] for d in docs],
            "retrieved_at": now_iso(),
        }]
    }
```

## 為什麼 route_history 很重要？

Audit / debug / replay 神器。

```python
route_history: [
  {"from": "START", "to": "rewrite_query", "reason": "init"},
  {"from": "rewrite_query", "to": "retrieve", "reason": "next"},
  {"from": "reflect", "to": "retrieve", "reason": "evidence insufficient"},
  {"from": "reflect", "to": "rewrite_query", "reason": "wrong direction"},
  {"from": "reflect", "to": "finalize", "reason": "grounded"},
]
```

問題出現時，你能完整回放 agent 的決策軌跡。

## 設計反模式（Anti-patterns）

### ❌ Anti-pattern 1：把 LLM response 整個塞進 state

```python
return {"llm_response": "<整段自然語言>"}
```

之後別的 node 還要 parse。應該在當下就結構化。

### ❌ Anti-pattern 2：用 dict 當 reflection

```python
reflection: dict   # 不知道裡面有什麼
```

之後你連自動補全都沒。用 TypedDict。

### ❌ Anti-pattern 3：忘記 attempt_count

無限迴圈警報。

### ❌ Anti-pattern 4：node 偷偷用全域變數

```python
COUNTER = 0  # 別這樣！

def some_node(state):
    global COUNTER
    COUNTER += 1
    ...
```

Checkpoint 還原時 `COUNTER` 會歸零，state 裡的 `attempt_count` 才會還原。**所有需要跨節點記住的事，都要進 state。**

## 一個 cheat sheet

| 你想做 | 加什麼進 state |
|--------|---------------|
| 防無限迴圈 | `attempt_count`, `max_attempts` |
| 防重複查詢 | `retrieval_history` |
| Audit 流程 | `route_history` |
| Trace 多 thread | `trace_id` |
| 錯誤恢復 | `errors: List[str]` |
| Token 預算控制 | `total_tokens_used` |
| 工具呼叫紀錄 | `tool_calls: List[ToolCall]` |

## 一句話收斂

> State 不是「順手放點東西的地方」，是 Agent 的記憶體位址圖。設計時當資料庫 schema 認真對待。

---

**下一章**：[Reflection Node 深潛](ch08-reflection-node.md)

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

為什麼要分區？四群欄位在工程性質上根本是四種東西：

| 區塊 | 誰會寫 | 讀寫頻率 | 生命週期 | 出問題時要看哪一群 |
|------|--------|---------|---------|------------------|
| **內容** | 多數 node 都會寫 | 高 | 從 query 進來到 final 出去 | 答案不對 |
| **評估** | 只有 reflect node 寫 | 中 | 每輪迴圈刷新 | 路由走錯 |
| **控制** | routing function 讀、特定 node 寫 | 高（讀）/低（寫） | 跨整個 graph | 迴圈失控 |
| **觀測** | 幾乎所有 node 都 append | 高（只 append） | 永久累積 | 事後 audit |

混在一起寫不會壞，但 review code 時你會看到一個 30 個欄位的扁平 TypedDict，無法秒判「這個欄位是業務資料還是 debug 用」。分區是給未來的自己留路標。

### 原則 2：decision 必須是 Literal

```python
Decision = Literal["rewrite_query", "retrieve_again", "finalize", "human_review"]
```

❌ 不要用 `str`。型別系統就是你的第一道防線。背後的「封閉集合」思想完整解釋見 [ch03 §設計原則](ch03-conditional-edges.md#設計原則decision-必須是封閉集合)。

### 原則 3：一定要有 attempt_count

否則無限迴圈。

### 原則 4：reflection 要保留 reasoning

不只 decision，還要記理由。`reasoning` 欄位有兩個用途：

1. **Audit**：事後回看「為什麼第 2 輪決定 rewrite，不是 retrieve_again」
2. **餵給下一輪 reflect**：下次 reflect node 可以讀上一次的 reasoning，避免重複犯同樣的判斷錯誤（例如：上次說「query 太籠統」，這次就別再 retrieve_again 撞牆）

第 2 個用途常被忽略，但它讓 reflection 從「單點評估」升級成「跨輪學習」。

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

正式版會多出幾個 MVP 沒有的欄位，先把它們的角色講清楚再看程式碼：

**Query 為什麼要分兩階段（`normalized_query` + `rewritten_query`）？**

| 欄位 | 做什麼 | 怎麼產生 | 為什麼分開 |
|------|--------|---------|-----------|
| `normalized_query` | 機械式清理：小寫化、去標點、去停用詞、標準化同義詞 | 純規則或輕量函式，不需 LLM | 結果可被 cache，同樣的問題不會重算 |
| `rewritten_query` | 改寫成檢索友善的形式（加領域術語、展開縮寫、改成關鍵字句） | 呼叫 LLM | 需要 inference，每次都付錢 |

把兩階段分開，一來 normalize 結果可以當快取 key，二來如果 retrieve 失敗，reflect 才能診斷「是 normalize 漏掉同義詞？還是 rewrite 改錯方向？」

**`trace_id` 是什麼？**
分散式追蹤（distributed tracing）的標準概念——**用一個唯一 ID 標識「同一次使用者請求」貫穿所有節點、所有外部呼叫的軌跡**。寫進 log 後，你可以在 Grafana / Datadog 之類的工具上把這次請求的所有事件拼回來看。

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

## reflection 的三個 float 是什麼？

正式版的 `Reflection` 比 MVP 多了三個分數欄位，它們不是裝飾，而是把 MVP 的兩個 bool 細化成「**可量化的修正訊號**」：

| 欄位 | 在量化什麼 | 與 MVP bool 的關係 | 取值區間 | 拿到後怎麼用 |
|------|----------|------------------|---------|-----------|
| `relevance_score` | 檢索到的文件**整體跟 query 有多相關** | retrieve 階段的健康度（粗篩） | 0.0–1.0 | 偏低 → `rewrite_query`（查錯方向） |
| `coverage_score` | query 拆出的各面向**被覆蓋的比例** | `sufficient` 的細部刻度 | 0.0–1.0 | 偏低 → `retrieve_again` + 提高 `top_k`（補洞） |
| `hallucination_risk` | 草稿中**未被證據支持的句子比例** | `grounded` 的細部刻度 | 0.0–1.0 | 偏高 → `regenerate`（生成時亂編） |

為什麼要從 bool 升級成 float？因為 bool 的二元決策太粗：`grounded=false` 可能意味著「一句沒出處」也可能意味著「整段都在編」，這兩種狀況的處理策略應該不同。float 提供**漸層**，routing 可以設 threshold（例如 `hallucination_risk > 0.3` 才觸發 regenerate），不會動不動就走極端分支。

> 💡 這三個分數通常由 reflect node 裡的 LLM 在同一次呼叫產出（讓模型同時打三個分），或拆給三個小模型/規則分別計算。實作細節在 [ch08](ch08-reflection-node.md)。

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
  {"from_node": "START", "to_node": "rewrite_query", "reason": "init"},
  {"from_node": "rewrite_query", "to_node": "retrieve", "reason": "next"},
  {"from_node": "reflect", "to_node": "retrieve", "reason": "evidence insufficient"},
  {"from_node": "reflect", "to_node": "rewrite_query", "reason": "wrong direction"},
  {"from_node": "reflect", "to_node": "finalize", "reason": "grounded"},
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

> **TypedDict 是什麼？**
> `typing.TypedDict` 是 Python 的字典型別宣告。**Runtime 行為跟普通 dict 完全一樣**（就是 `{}`），但靜態檢查器（mypy、pyright、IDE）知道每個 key 對應的型別。寫 `reflection["decision"]` 時 IDE 會自動補全可用 key，寫錯 key 名會立刻被標紅。零 runtime 成本、純拿型別保護。

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

## 🔧 真實實作對照：[`app/graph/state.py`](../../../app/graph/state.py)

本書範例專案的 state schema 是「跨 4 個 spec 階段（P1→P4）持續演進」的真實案例，有兩個本章 MVP / 正式版都沒提的進階模式值得學。

### 進階 1：Annotated reducer — fan-out 並行寫入的 merge 策略

```python
# app/graph/state.py:14-32（節錄）
from operator import add
from typing import Annotated, Literal, TypedDict

class RAGState(TypedDict, total=False):
    user_input: str
    # ...
    # —— P2 multi-seed
    seeds: list[str]
    # reducer：fan-out 寫入時用 list append（而非覆寫）
    hits_per_seed: Annotated[list[list[KnowledgeChunk]], add]
    # 每條 seed 並行任務的本地欄位（透過 Send 傳入；總體 state 不直接讀）
    seed: str
    seed_index: int
```

`Annotated[..., add]` 是 LangGraph 的**狀態 merge 策略宣告**。預設情況下，多個節點同時寫同一個欄位 → 後者覆寫前者；但用 `Send` API 把同一個節點 fan-out 成 N 個並行 task（multi-seed 檢索）時，每個 task 都想 append 自己的結果，**覆寫語意會把其他 task 的成果吃掉**。

把欄位標 `Annotated[..., add]` 之後，LangGraph 看到多個 task 同時 return 就會用 `+` 運算子（list 的 `+` 就是 append）把所有結果合併。`add` 來自 `operator.add`，也可以換成自訂 merge function。

> 💡 **何時用 reducer？** 寫線性 graph 用不到；只要你的 graph 出現 `Send`、fan-out / fan-in、或多個 node 並行寫同一欄位 → 必須宣告 reducer，否則 race 會吃掉資料。

### 進階 2：用 inline 註解標出 state 的成長階段

```python
# app/graph/state.py（節錄）
class RAGState(TypedDict, total=False):
    user_input: str
    channel: str                  # "line" | "http" | "stub" | ...
    external_user_id: str

    router_result: RouterResult
    skill: SkillDefinition
    features: ExtractedFeatures

    # —— P2 multi-seed
    seeds: list[str]
    hits_per_seed: Annotated[list[list[KnowledgeChunk]], add]

    # —— P3 sufficiency / clarification
    sufficiency: Literal["sufficient", "insufficient"]
    sufficiency_reasons: list[str]
    clarification_questions: list[str]

    # —— P3 two-stage generator
    answer_contract: AnswerContract

    # —— P4 judge + reflection
    judge_score: JudgeScore | None
    judge_feedback: list[str]
    reflection_retry: int

    # —— task-21 HITL（reflection variant + hitl_enabled 才會用到）
    reviewer_decision: Literal["approve", "revise", "drop"] | None
    reviewer_revised_text: str | None
    # ...
```

每個分區註解都標出該欄位「**為了什麼 spec / 哪個 variant 加的**」。半年後看這份 schema，可以一眼分辨「哪些是基本 RAG 用的、哪些是 reflection variant 才會碰的」——避免新人改 selfrag 時誤動 P4 才有意義的欄位。

### 進階 3：State 用 TypedDict，評估結果用 Pydantic

注意 `judge_score: JudgeScore | None` 的 `JudgeScore` 是 Pydantic BaseModel（[`app/judge/scorer.py:29`](../../../app/judge/scorer.py)）：

```python
# app/judge/scorer.py:29-52
class JudgeScore(BaseModel):
    groundedness: int = Field(..., ge=0, le=10)
    citation_fidelity: int = Field(..., ge=0, le=10)
    format_completeness: int = Field(..., ge=0, le=10)
    uncertainty_honesty: int = Field(..., ge=0, le=10)
    issues: list[str] = Field(default_factory=list)

    def passes(self, *, min_axis: int = 6, min_mean: float = 7.0) -> bool:
        worst = min(self.groundedness, self.citation_fidelity, ...)
        return worst >= min_axis and self.mean >= min_mean
```

**為什麼這裡用 Pydantic 而不是 TypedDict？**

| 場景 | 用什麼 | 為什麼 |
|------|-------|--------|
| 整體 state（RAGState）| TypedDict | 與 dict 介面相容、零包裝、節點之間 merge 高頻、不需要 runtime validation |
| LLM 結構化輸出（JudgeScore）| Pydantic | LLM 可能回出格範圍（`groundedness: 15`），需要 runtime `ge=0, le=10` 驗證；自帶 `passes()` 方法把硬閾值規則綁在資料旁邊 |

**這是 LangGraph 專案的常見混用模式**：state 殼層 TypedDict、跨信任邊界的子物件（LLM 輸出、外部 API 結果）用 Pydantic。

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

# 第 2 章：StateGraph — 流程的中樞神經

> 「沒有共享狀態的 Agent，就像每天失憶的研究助理。」

## 用比喻先抓核心

想像你帶一個研究助理寫報告。你不會每做一步就要他把前面全部忘掉，對吧？你們會共用**一本筆記**：

- 老闆原始問題是什麼？
- 改寫後查詢是什麼？
- 找到了哪些文件？
- 目前答案草稿長怎樣？
- 反思結果如何？
- 還缺什麼？

這本筆記，就是 **State**。

## 先補一個底層概念：狀態機

在資訊科學與系統設計中，**狀態機（State Machine）**，更嚴謹地說是**有限狀態機（Finite State Machine, FSM）**，是一種用來描述系統行為的數學模型與架構範式。

用程式設計的白話說：

> 狀態機定義了一個系統在任意時間點「只能」處於一種特定狀態；而且只有在特定事件觸發時，才能依照明確規則，從一個狀態轉移到另一個狀態。

也就是說，狀態機不是「讓程式自己想去哪」，而是把系統所有可能的狀態與轉移路徑先定義清楚。

## 狀態機的四個核心元素

任何狀態機，不論多複雜，都可以拆成四個基本元素：

| 元素 | 說明 | 在 LangGraph 裡的對應 |
|------|------|----------------------|
| **States** | 系統所有可能存在的情況或模式，數量必須有限 | State 裡的欄位組合與目前節點位置 |
| **Events / Inputs** | 觸發系統反應的外部訊號或條件 | 使用者輸入、LLM 判斷、檢索結果、審核結果 |
| **Transitions** | 從一個狀態變更到另一個狀態的路徑 | Edge / Conditional Edge |
| **Actions / Outputs** | 狀態轉移或進入狀態時實際執行的行為 | Node 函式、工具呼叫、LLM 呼叫 |

> ⚠️ **重點**
> 狀態機的價值不是「把流程畫成圖」，而是確保不合法的事件在特定狀態下不會生效。

## 生活隱喻：捷運驗票閘門

想像一個捷運自動驗票閘門。它只有兩個狀態：

- `Locked`：鎖定，不能通過
- `Unlocked`：解鎖，可以通過

```
       +-------------[ 刷卡 / 成功扣款 ]--------------+
       |                                              |
       v                                              |
  +---------+                                    +-----------+
  |  Locked |                                    |  Unlocked |
  +---------+                                    +-----------+
       ^                                              |
       |                                              |
       +-------------[ 推進閘門 / 通過 ]---------------+
```

在 `Locked` 狀態下：

- 你推進閘門，系統拒絕通行，仍然保持 `Locked`
- 你刷卡成功，系統扣款，轉移到 `Unlocked`

在 `Unlocked` 狀態下：

- 你再次刷卡，系統可能提示已刷過，仍然保持 `Unlocked`
- 你推進閘門通過，系統轉移回 `Locked`

這就是狀態機最重要的工程價值：**在 `Locked` 狀態下，不管你怎麼推閘門，只要沒有刷卡成功這個事件，系統就不可能進入允許通行的行為。**

把這個模型帶回 AI Agent：我們希望 LLM 可以理解語意、生成文字、判斷品質；但我們不希望它任意決定流程能不能跳過審核、能不能無限重試、能不能在證據不足時直接輸出。這些「能不能」要交給狀態機。

## State 是什麼？

在 LangGraph 裡，**每個節點都讀寫同一份 State**。

```
        ┌─────────────────────────────┐
        │       Shared State          │
        │  user_query, docs, draft... │
        └──────────┬──────────────────┘
                   │
       ┌───────────┼───────────┐
       ↓           ↓           ↓
   [Node A]    [Node B]    [Node C]
```

對比一下「沒有共享 state 的世界」：

```
A 的 output → 硬塞給 B → B 的 output → 硬塞給 C
```

這種設計每加一個 node 就要重新接管所有上下文。改一次架構就崩。

## 真實 State Schema 長這樣

以一個 RAG + Reflection agent 為例：

```python
from typing import TypedDict, List, Literal

class RetrievalDoc(TypedDict):
    id: str
    source: str
    score: float
    text: str

class AgentState(TypedDict):
    # 輸入
    user_query: str

    # 改寫
    normalized_query: str
    rewritten_query: str

    # 檢索
    retrieved_docs: List[RetrievalDoc]
    top_k: int

    # 生成
    draft_answer: str
    final_answer: str

    # 反思
    reflection: dict

    # 迴圈控制
    attempt_count: int
    max_attempts: int

    # 可觀測性
    trace_id: str
    errors: List[str]
```

> 💡 **Brain Power**
> 為什麼要把 `attempt_count` 放在 state 裡，而不是用一個全域變數？
>
> （想完再往下看。）

<details>
<summary>解答</summary>

因為 state 會被 checkpoint 存下來。當系統中斷恢復時，全域變數會歸零，但 state 裡的 `attempt_count` 會被還原。這就是為什麼**所有需要跨節點記住的事，都要進 state**。
</details>

## 三個構成要素

LangGraph 官方把 graph 拆成三件事：

| 元件 | 角色 | 比喻 |
|------|------|------|
| **State** | 共享資料結構 | 工作筆記 |
| **Nodes** | 對 state 做事的函式 | 員工 |
| **Edges** | 決定下一步去哪 | 走廊 |

## 為什麼 AI Agent 更需要狀態機？

傳統 LLM 應用常見的是流水線（Pipeline）架構：

```
輸入 → Prompt A → 檢索 B → 生成 C → 輸出
```

這種架構很直覺，但問題是：一旦中間某一步出錯，例如檢索抓到垃圾資料，整條流水線通常會一路錯到底。

LangGraph 把這件事重構成一個**集中式的狀態機（Stateful Graph）**：

- **全域狀態（State）**：系統維護一個共享的記憶體物件，例如 `{"query": ..., "docs": [], "critique": ..., "steps": 0}`
- **節點（Nodes）**：每個節點負責一個清楚的動作，例如檢索、生成、反思、人工審核
- **條件邊（Conditional Edges）**：根據 state 裡的結構化結果決定下一步，例如資料合格就生成，不合格就重新檢索

一個 RAG + Reflection Agent 可能長這樣：

```
[Rewrite Query] → [Retrieve] → [Evaluate Docs]
                                  │
                                  ├─ docs_ok → [Generate]
                                  │
                                  └─ docs_bad && attempts < 3 → [Rewrite Query]
```

在這裡，LLM 可以負責判斷「資料是否足夠」，但**流程能不能重試、最多重試幾次、什麼時候要交給人類審核**，都交給 graph 的狀態機規則。

## 軟體工程上的核心價值：確定性

複雜 AI Agent 最大的麻煩是：LLM 本身是隨機、模糊、容易漂移的。

狀態機的作用，就是用**軟體工程的確定性，去框住 LLM 的不確定性**。

不論 LLM 生成多天馬行空的內容，LangGraph 都會限制它的下一步只能落在已定義的節點、邊與中斷機制裡：

- 合法決策才會被 router 接受
- 不合法輸出會被 fallback 或 human review 接住
- 重試次數可以被 `attempt_count` 和 `max_attempts` 硬性限制
- 每一步 state 都能被 checkpoint、觀測與審計

這也是為什麼 LangGraph 適合承載自我反思、糾錯、動態路由、人機協同這些非線性流程：它不是把控制權交給 prompt，而是把控制權留在系統架構裡。

## 一個 Node 長怎樣？

最簡單的 node 就是一個函式，**輸入 state，回傳要更新的部分**：

```python
def rewrite_query(state: AgentState):
    base = state["user_query"]
    rewritten = llm_rewrite(base)
    return {"rewritten_query": rewritten}
```

注意：你**不需要回整份 state**，只需要回「我要更新什麼」。LangGraph 會自動 merge。

## 🔧 真實實作對照：[`app/graph/variants/basic.py`](../../../app/graph/variants/basic.py)

本書範例專案有一個「最簡 StateGraph」的 production code，全檔 49 行，可以直接對照本章每個概念：

```python
# app/graph/variants/basic.py（節錄）
g = StateGraph(RAGState)                                     # ① 用 state schema 開圖

g.add_node("input_guard", partial(input_guard_node, services=services))   # ② 註冊節點
g.add_node("route", partial(route_node, services=services))
g.add_node("retrieve", partial(retrieve_basic_node, services=services))
g.add_node("generate", partial(generate_basic_node, services=services))
g.add_node("push", partial(push_node, services=services))

g.add_edge(START, "input_guard")                             # ③ 線性 edges
g.add_conditional_edges("input_guard", route_after_input_guard, ["route", "push"])
g.add_edge("route", "retrieve")
g.add_edge("retrieve", "generate")
g.add_edge("generate", "push")
g.add_edge("push", END)

return g.compile()
```

對照本章三件事：
- **State** ← `RAGState`（見 [`app/graph/state.py`](../../../app/graph/state.py)，下面詳述）
- **Nodes** ← 5 個節點函式，全部在 [`app/graph/nodes.py`](../../../app/graph/nodes.py)
- **Edges** ← `add_edge` 線性 + `add_conditional_edges` 分岔（input_guard 後依使用者輸入是否被攔截分流）

> 💡 **`partial(...)` 為什麼這樣寫？** 真實系統的節點需要拿 `services`（LLM client、retriever、settings 等），但 LangGraph 規定節點函式簽名是 `(state) -> dict`。`functools.partial` 把 services 預先綁進去，graph 看到的就是符合簽名的函式。這是把 dependency injection 接到 LangGraph 的標準做法。

### 真實 State 用 `total=False` 怎麼設

```python
# app/graph/state.py（節錄）
class RAGState(TypedDict, total=False):
    user_input: str
    channel: str                  # "line" | "http" | "stub" | ...
    external_user_id: str
    router_result: RouterResult
    features: ExtractedFeatures
    rag_chunks: list[KnowledgeChunk]
    # ... 跨多個 spec 階段持續累積的欄位
```

`total=False` 配上 LangGraph 的「節點只回傳 patch」設計，整個專案才能漸進加欄位（從 P1 到 P4）而不會打破既有節點。

## 為什麼這比「巨型 prompt」好？

很多人做 RAG 是這樣：

```
prompt = f"""
使用者問: {query}
這是文件: {docs}
這是你之前回答的草稿: {draft}
這是你之前的反思: {reflection}
請你決定下一步...
"""
```

問題：

- ❌ Prompt 越長，模型越容易迷路
- ❌ 沒辦法 audit 每一步發生什麼
- ❌ 換模型就要重寫整個 prompt
- ❌ 沒辦法測試單一步驟

用 StateGraph：

- ✅ 每個 node 責任單一
- ✅ 每個 node 可單元測試
- ✅ 整個流程可視化
- ✅ State 可以 dump 出來看

## 設計原則

> **內容歸 LLM，流程歸 Graph。**

- LLM 負責：理解、生成、反思結構化判斷
- Graph 負責：節點順序、狀態更新、條件路由

如果你發現某個 node 又要思考、又要決定流程、又要寫答案，**那就是該拆了**。

## ⚠️ 常見錯誤

1. **把所有東西丟進一個巨型 node**：失去了拆分的意義
2. **State 用自由文字而非結構化欄位**：之後 routing 會崩
3. **節點偷偷用全域變數**：checkpoint 會還原失敗
4. **回傳整份 state 而非 patch**：容易覆蓋掉其他 node 的更新

## 一句話收斂

> StateGraph 把 Agent 行為從「藏在 prompt 裡」提升成「可檢查、可測試、可治理的系統結構」。

---

**下一章**：[Conditional Edges：路口的號誌系統](ch03-conditional-edges.md)

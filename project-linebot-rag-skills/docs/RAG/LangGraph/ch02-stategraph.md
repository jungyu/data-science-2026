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

## 一個 Node 長怎樣？

最簡單的 node 就是一個函式，**輸入 state，回傳要更新的部分**：

```python
def rewrite_query(state: AgentState):
    base = state["user_query"]
    rewritten = llm_rewrite(base)
    return {"rewritten_query": rewritten}
```

注意：你**不需要回整份 state**，只需要回「我要更新什麼」。LangGraph 會自動 merge。

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

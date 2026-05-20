# 第 9 章：實戰 — 完整 LangGraph 程式碼

> 前面講了八章，現在動手。這份骨架可以從 MVP 一路長到 production。

## 目標

這份程式碼有：

- ✅ State
- ✅ Nodes
- ✅ Conditional Edges
- ✅ Checkpointer
- ✅ Interrupt / Human Review
- ✅ Reflection Prompt Loading
- ✅ JSON parse guard

## 目錄結構

```
rag_agent/
├─ app.py                          # 進入點：建圖、初始 state、執行
├─ graph/
│  ├─ state.py                     # 狀態 schema（ch07 設計、TypedDict 型別）
│  ├─ nodes.py                     # 所有節點函式（normalize / rewrite / retrieve / generate / reflect / human_review / finalize）
│  ├─ routing.py                   # 條件邊路由函式（ch08「接線到 LangGraph」的完整實作）
│  └─ build_graph.py               # 組裝 nodes + edges 編譯成可執行 graph
├─ prompts/
│  ├─ reflection-node.system.txt   # ch08 system prompt
│  └─ reflection-node.user.txt     # ch08 user prompt template
├─ infra/
│  ├─ llm.py                       # LLM 呼叫（demo stub，正式換 ChatOpenAI / Bedrock 等）
│  ├─ retriever.py                 # 檢索（demo stub，正式換 pgvector / OpenSearch）
│  └─ utils.py                     # JSON 容錯、文件 prompt 格式化
└─ requirements.txt
```

> 📖 **建議閱讀順序**：state.py（資料形狀）→ nodes.py（單點行為）→ routing.py（決策邏輯）→ build_graph.py（怎麼接起來）→ app.py（怎麼跑）。infra 是替換點，最後看。

## requirements.txt

```txt
langgraph>=0.2
langchain-core>=0.3
pydantic>=2.7
```

正式接模型：
```txt
langchain-openai>=0.2
```

正式持久化：
```txt
langgraph-checkpoint-postgres
psycopg[binary]
```

## graph/state.py

**設計重點**：

- **用 `TypedDict` 而不是 Pydantic** —— LangGraph 的 state 在節點之間靠 dict merge 流動，TypedDict 與 dict 介面相容、零包裝開銷，型別檢查照樣有
- **`Decision` 用 `Literal[...]`** —— 對應 [ch08 原則 3](ch08-reflection-node.md#原則-3decision-必須是封閉集合)「decision 必須是封閉集合」，型別系統直接擋掉拼錯的字串
- **`AgentState` 加 `total=False`** —— 允許節點只回傳「自己更新的欄位」而不是整份 state，LangGraph 慣用模式
- **`route_history` / `retrieval_history`** —— 不是必要欄位，但 debug / 觀測性無價，第一天就保留

```python
from __future__ import annotations
from typing import Literal, TypedDict, List, Dict, Any

# 封閉的 decision 集合——拼錯字串 mypy / IDE 馬上紅
Decision = Literal["rewrite_query", "retrieve_again", "finalize", "human_review"]


class RetrievalDoc(TypedDict):
    id: str
    source: str
    score: float
    text: str
    metadata: Dict[str, Any]


class ReflectionResult(TypedDict):
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


class RetrievalLog(TypedDict):
    query: str
    doc_ids: List[str]


class AgentState(TypedDict, total=False):
    # 輸入 / 查詢演進
    user_query: str               # 原始輸入
    normalized_query: str         # 清理後
    rewritten_query: str          # 改寫後（給 retriever 用）

    # 檢索 / 生成
    retrieved_docs: List[RetrievalDoc]
    top_k: int
    draft_answer: str             # reflect 之前的草稿
    final_answer: str             # finalize 之後的最終答案

    # 反思與迴圈控制
    reflection: ReflectionResult  # ch08 的評估結果
    attempt_count: int            # 已嘗試次數
    max_attempts: int             # 上限——routing.py 守門用
    reviewer_decision: Decision   # human_review resume 後的人類決策

    # 觀測性 / 除錯
    route_history: List[RouteLog]
    retrieval_history: List[RetrievalLog]
    errors: List[str]
```

## infra/utils.py

````python
from __future__ import annotations
import json
from pathlib import Path
from typing import Any, Dict


def read_text_file(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def safe_json_loads(text: str) -> Dict[str, Any]:
    """容錯：清掉 ```json ... ``` 標記。"""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        cleaned = cleaned.replace("json", "", 1).strip()
    return json.loads(cleaned)


def format_docs_for_prompt(docs: list[dict]) -> str:
    blocks = []
    for i, d in enumerate(docs, start=1):
        blocks.append("\n".join([
            f"[Doc {i}]",
            f"id: {d.get('id', '')}",
            f"source: {d.get('source', '')}",
            f"score: {d.get('score', 0.0)}",
            f"text: {d.get('text', '')}",
        ]))
    return "\n\n".join(blocks)
````

## infra/retriever.py

```python
from __future__ import annotations
from typing import List, Dict, Any


def retrieve_documents(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """Stub。之後換成 pgvector hybrid retrieval。"""
    mock_docs = [
        {
            "id": "doc-1",
            "source": "knowledge_base",
            "score": 0.91,
            "text": f"與查詢「{query}」相關的示例文件一。",
            "metadata": {"category": "example"},
        },
        {
            "id": "doc-2",
            "source": "knowledge_base",
            "score": 0.84,
            "text": f"與查詢「{query}」相關的示例文件二。",
            "metadata": {"category": "example"},
        },
    ]
    return mock_docs[:top_k]
```

## infra/llm.py

```python
from __future__ import annotations


def invoke_llm(system_prompt: str, user_prompt: str) -> str:
    """Stub。用 system_prompt 的指紋字串路由到對應的假回應。
    換成真模型時只改這一個函式 body，三個節點都不用動——這就是把
    LLM 接點集中在一個檔案的好處。
    """
    # rewrite_query 節點呼叫——回傳改寫後的查詢字串
    if "Rewrite the query" in system_prompt:
        return user_prompt.strip()

    # generate_draft 節點呼叫——回傳一段假草稿
    if "Generate a grounded answer" in system_prompt:
        return "這是一份根據檢索文件產生的草稿答案。"

    # reflect_answer 節點呼叫——回傳一份結構化的 reflection JSON
    # 故意設 sufficient=False、decision="retrieve_again"，
    # demo 跑起來會走一次「再查一輪」的迴圈
    if "strict reflection and routing node" in system_prompt:
        return """
        {
          "grounded": true,
          "sufficient": false,
          "relevance_score": 0.82,
          "coverage_score": 0.58,
          "hallucination_risk": 0.21,
          "missing_topics": ["關鍵面向尚未完整覆蓋"],
          "reasoning": "Draft is relevant and mostly grounded, but evidence is not yet sufficient.",
          "decision": "retrieve_again"
        }
        """

    return "UNKNOWN"
```

## graph/nodes.py

```python
from __future__ import annotations
from typing import Any, Dict

from langgraph.types import interrupt

from graph.state import AgentState
from infra.llm import invoke_llm
from infra.retriever import retrieve_documents
from infra.utils import read_text_file, safe_json_loads, format_docs_for_prompt


def normalize_query(state: AgentState) -> Dict[str, Any]:
    """正規化輸入：去頭尾空白。實務可加：標點清理、半形/全形轉換、注音轉中文等。"""
    return {"normalized_query": state["user_query"].strip()}


def rewrite_query(state: AgentState) -> Dict[str, Any]:
    """改寫查詢：拉長語意、補關鍵字，提升檢索召回率。
    回傳純文字（不是 JSON）——這個節點職責單一，不需要結構化輸出。"""
    system_prompt = (
        "You are a query rewriting node.\n"
        "Rewrite the query for retrieval. Return plain text only."
    )
    user_prompt = state.get("normalized_query", state["user_query"])
    rewritten = invoke_llm(system_prompt, user_prompt).strip()
    return {"rewritten_query": rewritten}


def retrieve_docs_node(state: AgentState) -> Dict[str, Any]:
    """檢索：優先用 rewritten_query，退到 normalized_query，最後才用原始 user_query。"""
    query = state.get("rewritten_query") or state.get("normalized_query") or state["user_query"]
    top_k = state.get("top_k", 5)
    docs = retrieve_documents(query=query, top_k=top_k)

    # ⚠️ 慣用模式：先複製舊 list 再 append，不要 in-place mutate state
    #   理由：LangGraph 用 dict merge 更新 state，回傳新 list 才能正確被識別為「有變更」
    retrieval_history = list(state.get("retrieval_history", []))
    retrieval_history.append({
        "query": query,
        "doc_ids": [d["id"] for d in docs],
    })

    return {
        "retrieved_docs": docs,
        "retrieval_history": retrieval_history,
    }


def generate_draft(state: AgentState) -> Dict[str, Any]:
    """產生草稿答案。
    關鍵約束：「Do not use outside knowledge」——強迫模型只用檢索結果回答，
    這是 reflect 階段 grounded 評估能成立的前提。"""
    system_prompt = (
        "You are a grounded answer generation node.\n"
        "Generate a grounded answer using only the retrieved documents.\n"
        "Do not use outside knowledge."
    )
    docs_text = format_docs_for_prompt(state.get("retrieved_docs", []))
    user_prompt = (
        f"USER QUESTION:\n{state['user_query']}\n\n"
        f"REWRITTEN QUERY:\n{state.get('rewritten_query', '')}\n\n"
        f"RETRIEVED DOCUMENTS:\n{docs_text}\n"
    )
    draft = invoke_llm(system_prompt, user_prompt).strip()
    return {"draft_answer": draft}


def reflect_answer(state: AgentState) -> Dict[str, Any]:
    """評估 + 路由決策節點。ch08 整章在講這個函式。

    - prompt 從檔案讀，方便不改 code 就調 prompt（可以 git diff、可以 A/B test）
    - JSON parse 失敗 → fail-closed：強制 decision='human_review'，不讓壞答案靜悄悄通過
    - Hard guard 在這裡只放一條（grounded=False 不能 finalize）；完整四條見 ch08
    - 每呼叫一次 attempt_count + 1，max_attempts 守門邏輯在 routing.py
    """
    system_prompt = read_text_file("prompts/reflection-node.system.txt")
    user_template = read_text_file("prompts/reflection-node.user.txt")

    docs_text = format_docs_for_prompt(state.get("retrieved_docs", []))
    user_prompt = (
        user_template
        .replace("{{ user_query }}", state["user_query"])
        .replace("{{ normalized_query }}", state.get("normalized_query", ""))
        .replace("{{ rewritten_query }}", state.get("rewritten_query", ""))
        .replace("{{ retrieved_docs }}", docs_text)
        .replace("{{ draft_answer }}", state.get("draft_answer", ""))
        .replace("{{ attempt_count }}", str(state.get("attempt_count", 0)))
        .replace("{{ max_attempts }}", str(state.get("max_attempts", 3)))
    )

    raw = invoke_llm(system_prompt, user_prompt)

    errors = list(state.get("errors", []))
    try:
        parsed = safe_json_loads(raw)
    except Exception as exc:
        # Fail-closed：parse 失敗就送人類，不讓未知狀態靜悄悄放行
        errors.append(f"reflection_json_parse_error: {exc}")
        parsed = {
            "grounded": False,
            "sufficient": False,
            "relevance_score": 0.0,
            "coverage_score": 0.0,
            "hallucination_risk": 1.0,
            "missing_topics": ["reflection parse failed"],
            "reasoning": "Reflection JSON parsing failed.",
            "decision": "human_review",
        }

    # Hard guard（簡化版，完整四條見 ch08）
    if parsed.get("grounded") is False and parsed.get("decision") == "finalize":
        parsed["decision"] = "human_review"

    return {
        "reflection": parsed,
        "attempt_count": state.get("attempt_count", 0) + 1,
        "errors": errors,
    }


def human_review(state: AgentState) -> Dict[str, Any]:
    """動態 interrupt：跑到這裡時 graph 自動暫停，等外部呼叫 Command(resume=...) 才繼續。

    - Payload 是給前端介面顯示的資訊（問題、AI 草稿、AI 自評）
    - Resume 時前端應回傳 {"decision": "finalize" | "rewrite_query" | "retrieve_again"}
    - 需要 checkpointer 才能用——細節見 ch04 Interrupt 段
    """
    payload = {
        "type": "human_review_required",
        "user_query": state["user_query"],
        "draft_answer": state.get("draft_answer", ""),
        "reflection": state.get("reflection", {}),
    }
    # interrupt() 在此會：序列化 state → 釋放計算資源 → 等待 Command(resume=...)
    # 收到 resume 後，review_result 就是 resume 傳進來的 value
    review_result = interrupt(payload)

    reflection = dict(state.get("reflection", {}))
    reflection["decision"] = review_result.get("decision", "finalize")
    return {
        "reflection": reflection,
        "reviewer_decision": reflection["decision"],
    }


def finalize_answer(state: AgentState) -> Dict[str, Any]:
    """結束節點：把 draft 提升為 final。
    實務可在這裡加 citation_builder（附引用）/ safety_gate（規則攔截）——見 ch06。"""
    return {"final_answer": state.get("draft_answer", "")}
```

## graph/routing.py

```python
from __future__ import annotations
from typing import Literal
from graph.state import AgentState

RouteName = Literal[
    "rewrite_query",
    "retrieve_docs_node",
    "human_review",
    "finalize_answer",
]


def route_after_reflection(state: AgentState) -> RouteName:
    """條件邊路由函式——對應 ch08「接線到 LangGraph」的完整實作。

    設計重點：
    - max_attempts 守門放在這裡（不是 reflect_answer），讓「路由」職責集中
    - 純函式，不打 LLM——決策由 reflect_answer 一次付清，這裡只查 state
    - 未知 decision 預設導向 human_review；LLM 輸出是跨信任邊界，
      即使型別上寫了 Literal，runtime 還是要 fail-closed
    """
    # Guard：超過嘗試上限直接送人，避免 reflect 無限呼叫燒錢
    if state.get("attempt_count", 0) >= state.get("max_attempts", 3):
        return "human_review"

    # 缺 reflection 欄位也送人（fail-closed）
    decision = state.get("reflection", {}).get("decision", "human_review")

    if decision == "rewrite_query":
        return "rewrite_query"
    if decision == "retrieve_again":
        return "retrieve_docs_node"
    if decision == "human_review":
        return "human_review"
    if decision == "finalize":
        return "finalize_answer"
    return "human_review"


def route_after_human_review(state: AgentState) -> RouteName:
    """人類 resume 後的路由。

    這裡刻意不再套 max_attempts 守門，否則流程在「已達上限 → human_review」
    後，人類按 finalize 仍會被 route_after_reflection 送回 human_review，形成死循環。
    人類審核是治理出口，不是另一輪自動重試。
    """
    decision = state.get("reviewer_decision") or state.get("reflection", {}).get("decision", "finalize")
    if decision == "rewrite_query":
        return "rewrite_query"
    if decision == "retrieve_again":
        return "retrieve_docs_node"
    if decision == "human_review":
        return "human_review"
    return "finalize_answer"
```

## graph/build_graph.py

```python
from __future__ import annotations

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver

from graph.state import AgentState
from graph.nodes import (
    normalize_query,
    rewrite_query,
    retrieve_docs_node,
    generate_draft,
    reflect_answer,
    human_review,
    finalize_answer,
)
from graph.routing import route_after_reflection
from graph.routing import route_after_human_review


def build_graph():
    """組裝整張圖。結構：線性開頭 → 條件分岔 → 部分節點回流。"""
    builder = StateGraph(AgentState)

    # === 1. 註冊所有節點（純函式 → 圖上的 node id）===
    builder.add_node("normalize_query", normalize_query)
    builder.add_node("rewrite_query", rewrite_query)
    builder.add_node("retrieve_docs_node", retrieve_docs_node)
    builder.add_node("generate_draft", generate_draft)
    builder.add_node("reflect_answer", reflect_answer)
    builder.add_node("human_review", human_review)
    builder.add_node("finalize_answer", finalize_answer)

    # === 2. 線性開頭：固定走完前置流程 ===
    builder.add_edge(START, "normalize_query")
    builder.add_edge("normalize_query", "rewrite_query")
    builder.add_edge("rewrite_query", "retrieve_docs_node")
    builder.add_edge("retrieve_docs_node", "generate_draft")
    builder.add_edge("generate_draft", "reflect_answer")

    # === 3. 條件邊：reflect 之後依 decision 分岔 ===
    builder.add_conditional_edges(
        "reflect_answer",
        route_after_reflection,
        {
            "rewrite_query":      "rewrite_query",       # 方向錯 → 改寫
            "retrieve_docs_node": "retrieve_docs_node",  # 方向對但證據不足 → 重檢索
            "human_review":       "human_review",        # 高風險 / 超出上限 → 找人
            "finalize_answer":    "finalize_answer",     # 過關 → 收
        },
    )

    # === 4. 人類審完之後，依人類決策回到對應節點 ===
    builder.add_conditional_edges(
        "human_review",
        route_after_human_review,
        {
            "rewrite_query":      "rewrite_query",
            "retrieve_docs_node": "retrieve_docs_node",
            "human_review":       "human_review",
            "finalize_answer":    "finalize_answer",
        },
    )
    builder.add_edge("finalize_answer", END)

    # ⚠️ Demo 用 InMemorySaver——重啟就沒了
    #   Production 換 PostgresSaver / RedisSaver（見 ch04 Production 注意）
    checkpointer = InMemorySaver()
    return builder.compile(checkpointer=checkpointer)
```

> 🔄 **為什麼 human_review 後面也用 conditional edge？**
> 因為人類不一定只會按「通過」。他可能要求 `rewrite_query`、`retrieve_again`，也可能確認可以 `finalize`。這條 conditional edge 讓「人類決策」和「LLM 反思決策」走同一套圖上的節點，而不是在節點裡硬寫 if/else。
>
> 注意：`route_after_human_review` 不再套 `max_attempts` 守門。自動流程達到上限時會送進 human_review；一旦人類已經介入，這就是治理出口，否則人類按 finalize 仍會被送回 human_review，形成死循環。
>
> 🎯 **interrupt 在哪裡發生？**
> 不在 `build_graph` 這裡——是在 `human_review` 節點內呼叫 `interrupt()` 觸發（**動態暫停**）。如果你想改成「跑到 human_review 之前一定暫停」的**靜態模式**，要把 `human_review` 節點改成 no-op 中繼節點，並在 compile 時宣告：
> ```python
> builder.compile(checkpointer=..., interrupt_before=["human_review"])
> ```
> 不要同時保留節點內 `interrupt()` 又加 `interrupt_before`，否則會變成兩段暫停。兩種模式的差異見 [ch04 Interrupt 段](ch04-persistence.md#interrupt暫停等人類)。

## app.py

```python
from __future__ import annotations
from pprint import pprint
from graph.build_graph import build_graph


def main():
    graph = build_graph()

    # thread_id 是這份對話的「存檔檔名」——同一個 thread_id 才能 resume
    # 不同 thread 完全隔離（兩位使用者、兩個分頁不互相覆蓋）。見 ch04
    config = {"configurable": {"thread_id": "demo-thread-001"}}

    # 初始 state：所有 list 欄位先給空 list
    # 避免節點裡 .get() 拿到 None 再 .append() 噴 AttributeError
    initial_state = {
        "user_query": "浮數脈代表什麼？",
        "top_k": 5,
        "attempt_count": 0,
        "max_attempts": 3,
        "route_history": [],
        "retrieval_history": [],
        "errors": [],
    }

    print("=== First invoke ===")
    result = graph.invoke(initial_state, config=config)
    pprint(result)

    # === 如果暫停在 human_review，這樣續跑 ===
    # 第一個參數傳 Command(resume=...) 而不是 dict——告訴 graph：
    #   「這不是新 input，是回應上次的 interrupt()，把這個 value 塞回 interrupt() 的回傳值」
    # config 必須同一個 thread_id 才能接到上次的存檔
    # 細節見 ch04「人類不只是按同意，可以直接改 state」
    #
    # from langgraph.types import Command
    # resumed = graph.invoke(
    #     Command(resume={"decision": "finalize"}),
    #     config=config,
    # )
    # pprint(resumed)


if __name__ == "__main__":
    main()
```

## prompts/reflection-node.system.txt

完整內容見[第 8 章](ch08-reflection-node.md#正式版-prompt-system)。

## prompts/reflection-node.user.txt

完整內容見[第 8 章](ch08-reflection-node.md#正式版-prompt-user)。

## 你之後要替換的三個地方

### A. `invoke_llm()` → 真模型

```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0)

def invoke_llm(system_prompt: str, user_prompt: str) -> str:
    resp = llm.invoke([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ])
    return resp.content
```

### B. `retrieve_documents()` → pgvector

```python
def retrieve_documents(query: str, top_k: int = 5):
    embedding = embed(query)
    rows = db.execute("""
        select id, source, text, metadata,
               1 - (embedding <=> %s::vector) as score
        from knowledge_atoms
        where domain = 'tcm'
        order by embedding <=> %s::vector
        limit %s
    """, (embedding, embedding, top_k))
    return [dict(r) for r in rows]
```

### C. `human_review` resume

實作前端按鈕 → API → `graph.invoke(Command(resume={"decision": "..."}), config)`。

## 跑起來：預期輸出與 HITL 續跑

### 預期輸出（第一次 invoke）

跑 `python app.py` 時，demo stub 的 reflect 會一直回 `retrieve_again`。所以流程不會自然 finalize，而是會被 `max_attempts` 守門送到 `human_review` 暫停。這正好示範「無限迴圈被治理規則收斂」。

暫停後用 `graph.get_state(config)` 看 state，大致會像這樣：

```
{'attempt_count': 3,
 'draft_answer': '這是一份根據檢索文件產生的草稿答案。',
 'errors': [],
 'max_attempts': 3,
 'normalized_query': '浮數脈代表什麼？',
 'reflection': {'coverage_score': 0.58,
                'decision': 'retrieve_again',
                'grounded': True,
                'hallucination_risk': 0.21,
                'missing_topics': ['關鍵面向尚未完整覆蓋'],
                'reasoning': '...',
                'relevance_score': 0.82,
                'sufficient': False},
 'retrieval_history': [{'doc_ids': ['doc-1', 'doc-2'], 'query': '...'},
                       {'doc_ids': ['doc-1', 'doc-2'], 'query': '...'},
                       {'doc_ids': ['doc-1', 'doc-2'], 'query': '...'}],
 'retrieved_docs': [...],
 'rewritten_query': '浮數脈代表什麼？',
 'user_query': '浮數脈代表什麼？'}
```

幾個觀察點：

- `attempt_count: 3` —— reflect 跑到上限
- `retrieval_history` 有三筆 —— 第一次檢索 + 兩次 `retrieve_again`
- `reflection.decision: retrieve_again` —— stub 寫死的決策
- `snapshot.next` 會停在 `human_review` —— 等待 `Command(resume=...)`

> ⚠️ 換成真模型後，reflect 可能回 `finalize`，流程才會自然結束。stub 是故意寫成「永遠不滿意」，用來測 max-attempts 與 HITL。

### 完整 HITL：暫停 → 改 state → 續跑

ch04 + ch08 鋪墊的「人類可以直接改 state 再續跑」——完整 runnable 版本：

```python
from langgraph.types import Command
from graph.build_graph import build_graph

graph = build_graph()
config = {"configurable": {"thread_id": "demo-thread-002"}}

# === Phase 1：第一次跑，會在 human_review 觸發 interrupt() 暫停 ===
graph.invoke({
    "user_query": "浮數脈代表什麼？",
    "top_k": 5, "attempt_count": 0, "max_attempts": 3,
    "route_history": [], "retrieval_history": [], "errors": [],
}, config=config)

# 確認停在哪裡
snapshot = graph.get_state(config)
print("Paused at:", snapshot.next)                  # ('human_review',)
print("Interrupt payload:", snapshot.tasks[0].interrupts)

# === Phase 2（可選）：人類在暫停期間直接改 state ===
# 例：人類覺得 AI 找的文件不對，幫它換掉
graph.update_state(
    config,
    {"retrieved_docs": [{
        "id": "human-1", "source": "expert", "score": 0.99,
        "text": "浮脈主表，數脈主熱，浮數脈為外感風熱證之常見脈象。",
        "metadata": {},
    }]},
)

# === Phase 3：續跑，Command(resume=...) 把人類決策塞回 interrupt() 回傳值 ===
final = graph.invoke(
    Command(resume={"decision": "finalize"}),
    config=config,   # 同一個 thread_id 才能接到上次存檔
)
print("Final:", final["final_answer"])
```

> 🎯 三件事**一起**發生：**改 state**（`update_state`）+ **人類決策**（`Command(resume=...)`）+ **同一個 thread_id**。少任何一件就跑不起來。

## 除錯三招：Inspect、Time-Travel、可視化

### 1. Inspect：看任一時刻的 state

```python
state = graph.get_state(config)
print(state.values)        # 完整 state 內容
print(state.next)          # 下一個要跑的節點
print(state.config)        # 含 checkpoint_id

# 完整歷史
for snap in graph.get_state_history(config):
    print(snap.metadata.get("step"), snap.next, snap.values.get("attempt_count"))
```

### 2. Time-Travel：倒帶到某個 checkpoint，改 state 再跑

```python
history = list(graph.get_state_history(config))
target = history[3]   # 例如 retrieve 之後那一刻

graph.update_state(
    target.config,
    {"retrieved_docs": [...好的文件...]},
)

# 從那點繼續——原本歷史不會被覆蓋，這是「新分支」
graph.invoke(None, config=target.config)
```

完整概念見 [ch04 Time-Travel](ch04-persistence.md#time-travel把-state-倒帶到任何一步)。

### 3. 可視化：把圖畫出來

```python
# Jupyter / Streamlit 印 mermaid 圖
print(graph.get_graph().draw_mermaid())

# 或存成 PNG（需 pygraphviz）
graph.get_graph().draw_mermaid_png(output_file_path="graph.png")
```

> 🌐 設好 `LANGSMITH_API_KEY` 後，每次執行會自動在 LangSmith 網頁渲染動態圖 + 每步 token / state diff（呼應 [README 觀測性護城河](README.md#三背靠-langchain-生態系與-langsmith-的可觀測性)）。

## 單元測試骨架

ch08 強調 reflect node 應該能獨立測試。兩種策略並用：

```python
# tests/test_graph.py
from graph.build_graph import build_graph
from graph import nodes


def test_full_flow_converges_under_max_attempts():
    """整圖測試：即使 reflect 永遠回 retrieve_again，max_attempts 守門也會收斂。"""
    graph = build_graph()
    config = {"configurable": {"thread_id": "test-001"}}

    graph.invoke({
        "user_query": "test", "top_k": 2,
        "attempt_count": 0, "max_attempts": 2,   # 故意設低，加速測試
        "route_history": [], "retrieval_history": [], "errors": [],
    }, config=config)

    snapshot = graph.get_state(config)
    # 超過 max_attempts → 強制送 human_review（routing.py guard）
    assert "human_review" in snapshot.next


def test_hard_guard_blocks_ungrounded_finalize(monkeypatch):
    """節點單測：餵 grounded=False + decision=finalize，驗證 hard guard 改寫成 human_review。"""
    def fake_llm(system, user):
        if "strict reflection" in system:
            return ('{"grounded": false, "sufficient": false, "relevance_score": 0.1, '
                    '"coverage_score": 0.1, "hallucination_risk": 0.9, '
                    '"missing_topics": [], "reasoning": "", "decision": "finalize"}')
        return "stub"

    monkeypatch.setattr(nodes, "invoke_llm", fake_llm)
    monkeypatch.setattr(nodes, "read_text_file", lambda p: "stub-prompt")

    out = nodes.reflect_answer({
        "user_query": "x", "draft_answer": "x",
        "retrieved_docs": [], "attempt_count": 0, "max_attempts": 3,
    })
    assert out["reflection"]["decision"] == "human_review"   # hard guard 啟動
```

> 🧪 **兩種策略並用**：整圖測試（用 stub LLM 跑完整流程，驗證路由邏輯）+ 節點單測（monkeypatch LLM，驗證 hard guard / fail-closed 行為）。reflect 改 prompt 時主要靠後者快速回歸。

## 五個關鍵設計點（再強調）

1. **Reflect 不改答案**
2. **Routing 與 LLM 分離**
3. **Hard guard 攔下亂 finalize**
4. **Max attempts 防無限迴圈**
5. **Checkpointer 是 human-in-the-loop 的前提**

> 💡 **Brain Power**
> 如果你拿掉 `Hard guard`，會發生什麼最壞情況？

<details>
<summary>解答</summary>

模型在證據不足時仍回 `decision: "finalize"`，使用者收到一個「自信但沒根據」的答案。在中醫/法規/財務領域，這就是真實傷害。Hard guard 是系統最後一道防線。
</details>

---

**下一章**：[Production 化與常見地雷](ch10-production.md)

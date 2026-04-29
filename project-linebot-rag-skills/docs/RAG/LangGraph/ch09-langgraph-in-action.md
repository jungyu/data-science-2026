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
├─ app.py
├─ graph/
│  ├─ state.py
│  ├─ nodes.py
│  ├─ routing.py
│  └─ build_graph.py
├─ prompts/
│  ├─ reflection-node.system.txt
│  └─ reflection-node.user.txt
├─ infra/
│  ├─ llm.py
│  ├─ retriever.py
│  └─ utils.py
└─ requirements.txt
```

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

```python
from __future__ import annotations
from typing import Literal, TypedDict, List, Dict, Any

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
    user_query: str
    normalized_query: str
    rewritten_query: str
    retrieved_docs: List[RetrievalDoc]
    top_k: int
    draft_answer: str
    final_answer: str
    reflection: ReflectionResult
    attempt_count: int
    max_attempts: int
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
    """Stub。換成真模型時改這裡即可。"""
    if "Rewrite the query" in system_prompt:
        return user_prompt.strip()

    if "Generate a grounded answer" in system_prompt:
        return "這是一份根據檢索文件產生的草稿答案。"

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
    return {"normalized_query": state["user_query"].strip()}


def rewrite_query(state: AgentState) -> Dict[str, Any]:
    system_prompt = (
        "You are a query rewriting node.\n"
        "Rewrite the query for retrieval. Return plain text only."
    )
    user_prompt = state.get("normalized_query", state["user_query"])
    rewritten = invoke_llm(system_prompt, user_prompt).strip()
    return {"rewritten_query": rewritten}


def retrieve_docs_node(state: AgentState) -> Dict[str, Any]:
    query = state.get("rewritten_query") or state.get("normalized_query") or state["user_query"]
    top_k = state.get("top_k", 5)
    docs = retrieve_documents(query=query, top_k=top_k)

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

    # Hard guard
    if parsed.get("grounded") is False and parsed.get("decision") == "finalize":
        parsed["decision"] = "human_review"

    return {
        "reflection": parsed,
        "attempt_count": state.get("attempt_count", 0) + 1,
        "errors": errors,
    }


def human_review(state: AgentState) -> Dict[str, Any]:
    """interrupt() 暫停 graph，等待外部 resume。需要 checkpointer。"""
    payload = {
        "type": "human_review_required",
        "user_query": state["user_query"],
        "draft_answer": state.get("draft_answer", ""),
        "reflection": state.get("reflection", {}),
    }
    review_result = interrupt(payload)

    reflection = dict(state.get("reflection", {}))
    reflection["decision"] = review_result.get("decision", "finalize")
    return {"reflection": reflection}


def finalize_answer(state: AgentState) -> Dict[str, Any]:
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
    if state.get("attempt_count", 0) >= state.get("max_attempts", 3):
        return "human_review"

    decision = state.get("reflection", {}).get("decision", "human_review")

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


def build_graph():
    builder = StateGraph(AgentState)

    builder.add_node("normalize_query", normalize_query)
    builder.add_node("rewrite_query", rewrite_query)
    builder.add_node("retrieve_docs_node", retrieve_docs_node)
    builder.add_node("generate_draft", generate_draft)
    builder.add_node("reflect_answer", reflect_answer)
    builder.add_node("human_review", human_review)
    builder.add_node("finalize_answer", finalize_answer)

    builder.add_edge(START, "normalize_query")
    builder.add_edge("normalize_query", "rewrite_query")
    builder.add_edge("rewrite_query", "retrieve_docs_node")
    builder.add_edge("retrieve_docs_node", "generate_draft")
    builder.add_edge("generate_draft", "reflect_answer")

    builder.add_conditional_edges(
        "reflect_answer",
        route_after_reflection,
        {
            "rewrite_query": "rewrite_query",
            "retrieve_docs_node": "retrieve_docs_node",
            "human_review": "human_review",
            "finalize_answer": "finalize_answer",
        },
    )

    builder.add_edge("human_review", "reflect_answer")
    builder.add_edge("finalize_answer", END)

    checkpointer = InMemorySaver()
    return builder.compile(checkpointer=checkpointer)
```

## app.py

```python
from __future__ import annotations
from pprint import pprint
from graph.build_graph import build_graph


def main():
    graph = build_graph()

    config = {"configurable": {"thread_id": "demo-thread-001"}}

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

    # 若中斷在 human_review，可用 Command 續跑：
    # from langgraph.types import Command
    # resumed = graph.invoke(
    #     Command(resume={"decision": "finalize"}),
    #     config=config
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

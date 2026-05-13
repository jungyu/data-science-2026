# task-10：實作 LangGraph Self-RAG

> **⚠️ 已被 task-15 取代（superseded by task-15-sufficiency-clarify）**
>
> 本 task 對應的 [spec-10](../specs/spec-10-selfrag.md) 已被 [spec-15](../specs/spec-15-sufficiency-clarify.md) 取代；
> 實作改採 sufficiency + clarify，不再執行本 task 描述的 query 改寫重試流程。
>
> 本文件保留作為設計演進記錄。

> 規格詳見 [spec-10](../specs/spec-10-selfrag.md)

---

請新增 `app/graph/rag_graph.py`，並修改 `app/line/webhook.py`，將現行線性 pipeline 改為 LangGraph StateGraph，支援 query 改寫重試。

## 前置安裝

```bash
pip install langgraph
# pyproject.toml [project.dependencies] 加入 "langgraph"
```

## 步驟 1：定義 `RAGState`（`app/graph/state.py`）

```python
from typing import TypedDict
from app.router.intent_router import RouterResult
from app.retriever.knowledge_retriever import KnowledgeChunk

class RAGState(TypedDict):
    user_input: str
    recent_history: str
    line_user_id: str
    router_result: RouterResult
    rag_chunks: list[KnowledgeChunk]
    rag_context: str
    responses: list[str]
    retry_count: int        # 最多重試 1 次，初始為 0
    rewritten_query: str    # 改寫後的 query，初始為 ""
```

## 步驟 2：實作 `app/graph/nodes.py`

每個節點都是一個接收 `RAGState` 並回傳部分更新的 async function。

```python
import logging
from app.graph.state import RAGState

logger = logging.getLogger(__name__)

async def node_route(state: RAGState, *, router) -> dict:
    result = await router.route(state["user_input"], state["recent_history"])
    return {"router_result": result}

async def node_retrieve(state: RAGState, *, retriever) -> dict:
    query = state.get("rewritten_query") or state["router_result"].rag_query
    router_result = state["router_result"]
    chunks, context = await retriever.retrieve(
        query=query,
        categories=router_result.rag_categories,
    )
    return {"rag_chunks": chunks, "rag_context": context}

def edge_check_retrieval(state: RAGState) -> str:
    """條件邊：有資料→generate；無資料且可重試→rewrite；否則→generate"""
    has_chunks = bool(state.get("rag_chunks"))
    retry_count = state.get("retry_count", 0)
    if not has_chunks and retry_count < 1:
        return "rewrite"
    return "generate"

async def node_rewrite_query(state: RAGState, *, llm_client, model: str) -> dict:
    original_query = state["router_result"].rag_query
    prompt = (
        f"原始 query：{original_query}\n"
        "未找到相關資料，請用不同的詞彙或更廣泛的描述改寫這個 query，以提高檢索命中率。\n"
        "只輸出改寫後的 query 字串，不要解釋。"
    )
    response = await llm_client.responses.create(
        model=model,
        input=prompt,
        max_output_tokens=100,
    )
    rewritten = response.output_text.strip()
    logger.info("retry: rewriting query | original=%s | rewritten=%s", original_query, rewritten)
    return {
        "rewritten_query": rewritten,
        "retry_count": state.get("retry_count", 0) + 1,
    }

async def node_generate(state: RAGState, *, generator, knowledge_version: int = 0) -> dict:
    responses = await generator.generate_response(
        user_input=state["user_input"],
        router_result=state["router_result"],
        skill=None,
        rag_chunks=state.get("rag_chunks", []),
        rag_context=state.get("rag_context", ""),
        recent_history=state.get("recent_history", ""),
        knowledge_version=knowledge_version,
    )
    return {"responses": responses}

async def node_push(state: RAGState, *, line_bot_api) -> dict:
    from linebot.v3.messaging import TextMessage, PushMessageRequest
    messages = [TextMessage(text=r) for r in state["responses"]]
    await line_bot_api.push_message(
        PushMessageRequest(to=state["line_user_id"], messages=messages)
    )
    return {}
```

## 步驟 3：實作 `app/graph/rag_graph.py`

```python
from langgraph.graph import StateGraph, END
from app.graph.state import RAGState
from app.graph.nodes import (
    node_route, node_retrieve, edge_check_retrieval,
    node_rewrite_query, node_generate, node_push,
)
import functools

def build_rag_graph(services) -> object:
    """
    services 需提供：
      services.router, services.retriever, services.generator,
      services.line_bot_api, services.llm_client, services.llm_model
    """
    g = StateGraph(RAGState)

    g.add_node("route",   functools.partial(node_route,         router=services.router))
    g.add_node("retrieve", functools.partial(node_retrieve,     retriever=services.retriever))
    g.add_node("rewrite",  functools.partial(node_rewrite_query, llm_client=services.llm_client, model=services.llm_model))
    g.add_node("generate", functools.partial(node_generate,     generator=services.generator))
    g.add_node("push",     functools.partial(node_push,         line_bot_api=services.line_bot_api))

    g.set_entry_point("route")
    g.add_edge("route", "retrieve")
    g.add_conditional_edges("retrieve", edge_check_retrieval, {"rewrite": "rewrite", "generate": "generate"})
    g.add_edge("rewrite", "retrieve")
    g.add_edge("generate", "push")
    g.add_edge("push", END)

    return g.compile()
```

## 步驟 4：修改 `app/line/webhook.py`

將 `process_text_event()` 中的線性呼叫改為 graph.ainvoke：

```python
from app.graph.rag_graph import build_rag_graph

# 在模組層級（dependencies 初始化後）建立 graph
# rag_graph = build_rag_graph(services)

async def process_text_event(event, rag_graph):
    try:
        initial_state = {
            "user_input": event.message.text,
            "recent_history": "",      # 從 history_repo 讀取後填入
            "line_user_id": event.source.user_id,
            "router_result": None,
            "rag_chunks": [],
            "rag_context": "",
            "responses": [],
            "retry_count": 0,
            "rewritten_query": "",
        }
        await rag_graph.ainvoke(initial_state)
    except Exception:
        logger.exception("process_text_event failed")
```

## 步驟 5：修改 `app/dependencies.py`

```python
from app.graph.rag_graph import build_rag_graph

class RuntimeServices:
    def __init__(self, router, retriever, generator, line_bot_api, llm_client, llm_model):
        self.router = router
        self.retriever = retriever
        self.generator = generator
        self.line_bot_api = line_bot_api
        self.llm_client = llm_client
        self.llm_model = llm_model

services = RuntimeServices(...)
rag_graph = build_rag_graph(services)
```

## 請輸出

1. `app/graph/state.py`（RAGState TypedDict）
2. `app/graph/nodes.py`（5 個節點函式 + 1 個條件邊函式）
3. `app/graph/rag_graph.py`（build_rag_graph）
4. 修改後的 `app/line/webhook.py`（改用 graph.ainvoke）
5. 修改後的 `app/dependencies.py`（RuntimeServices + rag_graph 初始化）
6. 更新後的 `pyproject.toml`（加入 langgraph 依賴）
7. 測試：mock retriever 回傳空列表，確認 edge_check_retrieval 觸發 rewrite 路徑，第二次 retrieve 後進入 generate

## 驗收指令

```bash
pip install -e .

# 啟動服務後，透過 LINE 傳送知識庫不存在的問題
# log 應顯示 "retry: rewriting query"
# log 不應有 exception

# 傳送知識庫存在的問題
# log 不應出現 "retry: rewriting query"
# 正常回覆送達 LINE
```

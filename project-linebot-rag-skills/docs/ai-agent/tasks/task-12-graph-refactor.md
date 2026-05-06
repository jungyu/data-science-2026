# task-12：線性 → LangGraph 等價重構

> 規格詳見 [spec-12](../specs/spec-12-graph-refactor.md)

---

把 `app/line/webhook.py` 的 `process_text_event()` 重構為 LangGraph，**行為完全一致**。本 task 不引入任何新功能（沒有重試、沒有條件分支、沒有迴圈）——只是讓現有流程變成 graph 的形式，作為 P2–P4 的基礎。

## 前置安裝

```bash
python -m pip install -e ".[dev]"
```

`pyproject.toml` 的 `[project.dependencies]` 加入：

```toml
"langgraph>=0.2.0",
```

> 用 `python -m pip` 不要直接用 `pip`（README 已說明原因）。

## 動作邊界

**搬進 graph 的**：route、retrieve（含 `build_context`）、generate、push  
**留在 webhook 的**：inbound message 落庫、recent_history 讀取、skill 預取、outbound message 落庫

理由：persistence 是側 effect，不影響 graph state 流轉；先不動它能讓重構聚焦。

## 步驟 1：建立 `app/graph/` 目錄與 `state.py`

新增 `app/graph/__init__.py`（空檔即可）。

新增 `app/graph/state.py`：

```python
from __future__ import annotations

from typing import TypedDict

from app.rag.schemas import KnowledgeChunk
from app.router.schemas import RouterResult
from app.skills.registry import Skill


class RAGState(TypedDict, total=False):
    # 輸入（webhook 填入）
    user_input: str
    line_user_id: str
    recent_history: str
    skill: Skill

    # route 產出
    router_result: RouterResult

    # retrieve 產出
    rag_chunks: list[KnowledgeChunk]
    rag_context: str

    # generate 產出
    responses: list[str]
```

`total=False` 讓 LangGraph 在 node 尚未填入欄位時不報錯。後續 phase 會再加欄位。

> ⚠️ `Skill` 的實際 import 路徑請對齊 `app/skills/registry.py` 的公開類別名稱；若該檔沒有 export，請從 `app.skills.schemas` import 對應 dataclass / model。

## 步驟 2：實作 `app/graph/nodes.py`

每個 node 是 async function，接 `RAGState` 與所需 service，回傳**部分更新**（dict）。

```python
from __future__ import annotations

import logging
from typing import Any

from app.graph.state import RAGState
from app.dependencies import RuntimeServices

logger = logging.getLogger(__name__)


async def route_node(state: RAGState, services: RuntimeServices) -> dict[str, Any]:
    result = await services.router.route_message(
        state["user_input"],
        state.get("recent_history", "No recent conversation."),
    )
    return {"router_result": result}


async def retrieve_node(state: RAGState, services: RuntimeServices) -> dict[str, Any]:
    router_result = state["router_result"]
    if not router_result.is_rag_required:
        return {"rag_chunks": [], "rag_context": "No retrieved context."}

    chunks = await services.retriever.retrieve(
        router_result.rag_query or state["user_input"],
        categories=router_result.rag_categories,
        top_k=services.settings.knowledge_top_k,
        line_user_id=state["line_user_id"],
        skill_id=router_result.target_skill,
    )
    context = services.retriever.build_context(chunks)
    return {"rag_chunks": chunks, "rag_context": context}


async def generate_node(state: RAGState, services: RuntimeServices) -> dict[str, Any]:
    try:
        responses = await services.responder.generate_response(
            user_input=state["user_input"],
            router_result=state["router_result"],
            skill=state["skill"],
            rag_chunks=state.get("rag_chunks", []),
            rag_context=state.get("rag_context", "No retrieved context."),
            recent_history=state.get("recent_history", "No recent conversation."),
        )
    except Exception:
        logger.exception("generate_response failed")
        responses = ["系統暫時無法完成此請求，請稍後再試。"]
    return {"responses": responses}


async def push_node(state: RAGState, services: RuntimeServices) -> dict[str, Any]:
    await services.line_client.push_text(state["line_user_id"], state["responses"])
    return {}
```

> 兩個重點：
> 1. `generate_node` 內保留原 `try/except` fallback——這是「等價重構」的硬要求
> 2. 不在 graph 內 save_message，留給 webhook 處理

## 步驟 3：實作 `app/graph/rag_graph.py`

```python
from __future__ import annotations

from functools import partial

from langgraph.graph import END, START, StateGraph

from app.dependencies import RuntimeServices
from app.graph.nodes import generate_node, push_node, retrieve_node, route_node
from app.graph.state import RAGState


def build_rag_graph(services: RuntimeServices):
    g = StateGraph(RAGState)

    g.add_node("route", partial(route_node, services=services))
    g.add_node("retrieve", partial(retrieve_node, services=services))
    g.add_node("generate", partial(generate_node, services=services))
    g.add_node("push", partial(push_node, services=services))

    g.add_edge(START, "route")
    g.add_edge("route", "retrieve")
    g.add_edge("retrieve", "generate")
    g.add_edge("generate", "push")
    g.add_edge("push", END)

    return g.compile()
```

> 用 `functools.partial` 把 `services` 綁進每個 node，graph 內部仍以 `state → state` 介面呼叫。

## 步驟 4：在 `dependencies.py` 注入 graph

修改 `app/dependencies.py`：

```python
# 加在檔案上方
from app.graph.rag_graph import build_rag_graph

# 修改 RuntimeServices dataclass，加入 rag_graph 欄位
@dataclass(frozen=True)
class RuntimeServices:
    line_client: LineMessagingClient
    messages_repo: MessagesRepository
    skill_registry: SkillRegistry
    router: IntentRouter
    retriever: RAGRetriever
    responder: ResponseGenerator
    settings: Settings
    rag_graph: Any = None  # 在 get_runtime_services 內 build
```

> `rag_graph` 的型別標 `Any` 即可（langgraph CompiledGraph 不一定 export 公開類別）。也可用 `from langgraph.graph.state import CompiledStateGraph`，但 import 較脆。

修改 `get_runtime_services()`：

```python
@lru_cache(maxsize=1)
def get_runtime_services() -> RuntimeServices:
    settings = get_settings()
    services = RuntimeServices(
        line_client=get_line_client(),
        messages_repo=get_messages_repo(),
        skill_registry=get_skill_registry(),
        router=get_router(),
        retriever=get_retriever(),
        responder=get_responder(),
        settings=settings,
    )
    # graph 需要完整 services；用 object.__setattr__ 因為 dataclass 是 frozen
    object.__setattr__(services, "rag_graph", build_rag_graph(services))
    return services
```

> 也可以把 dataclass 改成 `frozen=False`，看你偏好。`frozen=True` + `__setattr__` 的好處是其它欄位仍 immutable。

加上 `lru_cache` 確保 graph 只 build 一次。

## 步驟 5：重寫 `app/line/webhook.py::process_text_event`

```python
async def process_text_event(event: LineEvent, services: RuntimeServices) -> None:
    user_id = event.source.user_id
    message = event.message
    if user_id is None or message is None or message.text is None:
        return

    # —— inbound 落庫（留在 webhook，不進 graph）
    try:
        await services.messages_repo.save_message(
            line_user_id=user_id,
            direction="inbound",
            message_text=message.text,
        )
    except Exception:
        pass

    recent_history = "No recent conversation."
    try:
        recent_history = await services.messages_repo.build_recent_history(user_id)
    except Exception:
        pass

    # —— graph 執行
    initial_state: RAGState = {
        "user_input": message.text,
        "line_user_id": user_id,
        "recent_history": recent_history,
        # skill 在 route 完才知道，這裡先放預設
        "skill": services.skill_registry.require("general_chat"),
    }

    final_state = await services.rag_graph.ainvoke(initial_state)

    # 若 router 結果指定不同 skill，generate_node 已用了預設 skill 跑出回覆——
    # 這與重構前行為不同。為保等價，在 graph 內處理 skill 解析。見「等價性檢查」段。

    # —— outbound 落庫（留在 webhook）
    router_result = final_state.get("router_result")
    responses = final_state.get("responses", [])
    rag_chunks = final_state.get("rag_chunks", [])

    try:
        await services.messages_repo.save_message(
            line_user_id=user_id,
            direction="outbound",
            message_text="\n\n".join(responses),
            skill_id=router_result.target_skill if router_result else None,
            router_result=router_result.model_dump() if router_result else None,
            rag_used=bool(rag_chunks),
        )
    except Exception:
        pass
```

## 步驟 6：處理 skill 解析（等價性關鍵）

重構前的順序是 `route → 解析 skill → retrieve → generate`。重構後若直接把 skill 預取放在 graph 外，會造成「skill 與 router 結果脫鉤」——P1 的等價性會破。

**做法**：在 `route_node` 內順便解析 skill，寫進 state。

修改 `app/graph/nodes.py::route_node`：

```python
async def route_node(state: RAGState, services: RuntimeServices) -> dict[str, Any]:
    result = await services.router.route_message(
        state["user_input"],
        state.get("recent_history", "No recent conversation."),
    )
    skill = (
        services.skill_registry.get(result.target_skill)
        or services.skill_registry.require("general_chat")
    )
    return {"router_result": result, "skill": skill}
```

`webhook.py` 的 `initial_state` 移除 `skill` 欄位（不必預填）：

```python
initial_state: RAGState = {
    "user_input": message.text,
    "line_user_id": user_id,
    "recent_history": recent_history,
}
```

## 步驟 7：移除舊線性串接函式

`process_text_event` 內原本的 `services.router.route_message → retriever.retrieve → responder.generate_response → line_client.push_text` 直接呼叫**全部刪除**，只保留新的 graph.ainvoke + 前後 persistence。

> 不要兩套並存。學生看兩套會混淆。

## 步驟 8：寫測試

新增 `tests/test_rag_graph_equivalence.py`：

```python
import pytest

from app.graph.rag_graph import build_rag_graph


@pytest.mark.asyncio
async def test_graph_runs_linearly(stub_services):
    """4 個 node 依序跑完，state 累積完整。"""
    graph = build_rag_graph(stub_services)
    final = await graph.ainvoke({
        "user_input": "什麼是 RAG？",
        "line_user_id": "U_test",
        "recent_history": "",
    })
    assert final["router_result"] is not None
    assert "rag_chunks" in final
    assert final["responses"]


@pytest.mark.asyncio
async def test_generate_failure_returns_fallback(stub_services_failing_responder):
    """responder 失敗時，等價於重構前回傳預設錯誤訊息。"""
    graph = build_rag_graph(stub_services_failing_responder)
    final = await graph.ainvoke({
        "user_input": "壞掉的問題",
        "line_user_id": "U_test",
        "recent_history": "",
    })
    assert final["responses"] == ["系統暫時無法完成此請求，請稍後再試。"]


@pytest.mark.asyncio
async def test_no_rag_required_skips_retrieve(stub_services_no_rag):
    """router 回 is_rag_required=False 時，rag_chunks 為空。"""
    graph = build_rag_graph(stub_services_no_rag)
    final = await graph.ainvoke({
        "user_input": "你好",
        "line_user_id": "U_test",
        "recent_history": "",
    })
    assert final["rag_chunks"] == []
```

`stub_services` 在 `tests/conftest.py` 用 `MagicMock` 包成 `RuntimeServices` shape 即可，不需真連 Supabase / LINE。

## 步驟 9：等價性手動驗證

```bash
./scripts/run_local.sh
ngrok http 8000
# 更新 LINE webhook URL → 用 LINE 傳送 10 則代表性訊息
```

10 則訊息建議涵蓋：

- 一般技術問題（觸發 RAG）
- 閒聊（不觸發 RAG）
- 複合問題（router 多分類）
- 知識庫沒涵蓋的問題（看 fallback）
- 觸發 generator 異常的長字串（看 try/except）

**重構前後逐則比對回覆**。可接受差異：log 時間戳、retrieval 隨機性導致的 chunk 順序差。

不可接受差異：回覆主體內容、skill 路由結果、是否觸發 RAG。

## 請輸出

1. `app/graph/__init__.py`（空）
2. `app/graph/state.py`
3. `app/graph/nodes.py`
4. `app/graph/rag_graph.py`
5. 修改後的 `app/dependencies.py`（`RuntimeServices` 加 `rag_graph`、`get_runtime_services` build graph）
6. 修改後的 `app/line/webhook.py`（`process_text_event` 改用 graph.ainvoke）
7. 修改後的 `pyproject.toml`（加 `langgraph>=0.2.0`）
8. `tests/test_rag_graph_equivalence.py` + `tests/conftest.py` 的 stub fixture
9. README 加一段「為什麼引入 LangGraph」（指向 [roadmap.md](../plan/roadmap.md) 與 spec-12）

## 驗收指令

```bash
# 1. 安裝
python -m pip install -e ".[dev]"

# 2. 跑測試
pytest tests/test_rag_graph_equivalence.py -v

# 3. 跑既有測試套件，確認沒回歸
pytest

# 4. 啟動服務（手動驗證等價性）
./scripts/run_local.sh
curl http://127.0.0.1:8000/health  # {"status":"ok"}
```

驗收通過條件：

- 步驟 8 的 3 個測試全綠
- `pytest` 整體無新失敗
- 步驟 9 的 10 則訊息逐則比對通過
- `app/line/webhook.py` 不再 import `IntentRouter` / `RAGRetriever` / `ResponseGenerator`（grep 確認）

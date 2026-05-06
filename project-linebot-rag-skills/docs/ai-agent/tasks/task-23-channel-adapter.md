# task-23：Channel Adapter Layer

> 規格詳見 [spec-23](../specs/spec-23-channel-adapter.md)

---

把 LINE 耦合從 graph 抽出。`RAGState` 改用通用 `external_user_id` + `channel`；`push_node` 委派給 channel adapter。提供 `LineChannel`（既有行為打包）+ `HttpChannel`（新增 web/API endpoint）兩個範例。

## 前置

- task-12 ~ task-19 完成（變體已落地）
- 預期影響面廣（state schema rename、所有 nodes 微調）

## 步驟 1：定義 Channel Protocol

新增 `app/channels/__init__.py`、`app/channels/base.py`：

```python
from __future__ import annotations

from datetime import datetime
from typing import AsyncIterator, Literal, Protocol

from fastapi import Request
from pydantic import BaseModel


class ChannelInput(BaseModel):
    channel: str
    external_user_id: str
    external_message_id: str
    raw_text: str
    metadata: dict = {}


class HistoryMessage(BaseModel):
    role: Literal["user", "assistant"]
    text: str
    timestamp: datetime


class OutputChannel(Protocol):
    name: str

    async def parse_request(self, request: Request) -> list[ChannelInput]: ...
    def build_thread_id(self, inp: ChannelInput) -> str: ...
    async def load_recent_history(
        self, *, external_user_id: str, limit: int = 5
    ) -> list[HistoryMessage]: ...
    def format(self, markdown: str) -> list[str]: ...
    async def push(self, *, recipient_id: str, messages: list[str]) -> None: ...
```

## 步驟 2：State schema rename

修改 `app/graph/state.py`：

```python
class RAGState(TypedDict, total=False):
    user_input: str
    channel: str                              # 新欄位
    external_user_id: str                     # 取代 line_user_id
    external_message_id: str
    recent_history: list[HistoryMessage]      # 改為結構化 list
    # ...其餘不變
```

> **不保留 `line_user_id` alias**：clean break，避免兩套並存混淆學生。grep 全 codebase 把 `line_user_id` 改名（除了 `app/channels/line.py` 內部）。

## 步驟 3：實作 LineChannel

新增 `app/channels/line.py`：把 `app/line/webhook.py`、`app/line/client.py`、`app/line/schemas.py` 的邏輯封裝為 `LineChannel`。重點：

```python
class LineChannel:
    name = "line"

    def __init__(self, settings, messages_repo) -> None:
        self._settings = settings
        self._messages_repo = messages_repo
        self._client = LineMessagingClient(settings)

    async def parse_request(self, request: Request) -> list[ChannelInput]:
        body = await request.body()
        sig = request.headers.get("x-line-signature")
        if not self._client.validate_signature(body, sig):
            raise HTTPException(status_code=400, detail="Invalid LINE signature")
        payload = LineWebhookPayload.model_validate_json(body)
        out = []
        for ev in payload.events:
            if ev.is_text_message and ev.source.user_id:
                out.append(ChannelInput(
                    channel="line",
                    external_user_id=ev.source.user_id,
                    external_message_id=ev.message.id,
                    raw_text=ev.message.text,
                ))
        return out

    def build_thread_id(self, inp: ChannelInput) -> str:
        return f"line-{inp.external_user_id}-{inp.external_message_id}"

    async def load_recent_history(self, *, external_user_id, limit=5) -> list[HistoryMessage]:
        # 從現有 messages_repo 讀，組成結構化 list
        rows = await self._messages_repo.recent(line_user_id=external_user_id, limit=limit)
        return [HistoryMessage(role=r["direction"] == "inbound" and "user" or "assistant",
                               text=r["message_text"], timestamp=r["created_at"])
                for r in rows]

    def format(self, markdown: str) -> list[str]:
        from app.generator.formatter import split_for_line
        return split_for_line(markdown, max_chars=self._settings.line_max_message_chars)

    async def push(self, *, recipient_id, messages) -> None:
        await self._client.push_text(recipient_id, messages)
```

## 步驟 4：實作 HttpChannel

新增 `app/channels/http.py`：

```python
class HttpChannel:
    name = "http"

    def __init__(self, messages_repo) -> None:
        self._messages_repo = messages_repo
        self._inflight: dict[str, list[str]] = {}  # 暫存本次請求的回覆

    async def parse_request(self, request: Request) -> list[ChannelInput]:
        # 由 /api/chat endpoint 直接 build，不用 parse_request
        raise NotImplementedError

    def build_thread_id(self, inp: ChannelInput) -> str:
        return f"http-{inp.external_user_id}-{inp.external_message_id}"

    async def load_recent_history(self, *, external_user_id, limit=5) -> list[HistoryMessage]:
        # 簡化版：用同一份 messages_repo（learn from LINE 累積）
        rows = await self._messages_repo.recent(line_user_id=external_user_id, limit=limit)
        return [HistoryMessage(...) for r in rows]

    def format(self, markdown: str) -> list[str]:
        # web 不切段
        return [markdown]

    async def push(self, *, recipient_id, messages) -> None:
        # HTTP 同步回應 — push 由 endpoint 直接從 final_state 取，這裡 no-op
        pass
```

## 步驟 5：StubChannel

新增 `app/channels/stub.py`：給測試 / eval / demo 用，`push` 寫進 list。

## 步驟 6：改寫 push_node

修改 `app/graph/nodes.py`：

```python
async def push_node(state: RAGState, services: Any) -> dict[str, Any]:
    user_id = state.get("external_user_id", "")
    if user_id.startswith(("U_demo", "U_eval")):
        return {}
    channel = services.channels[state["channel"]]
    decision = state.get("reviewer_decision")
    if decision == "drop":
        return {}
    if decision == "revise" and state.get("reviewer_revised_text"):
        text = state["reviewer_revised_text"]
    else:
        text = "\n\n".join(state.get("responses") or [])
    formatted = channel.format(text)
    await channel.push(recipient_id=user_id, messages=formatted)
    return {}
```

## 步驟 7：新增 `/api/chat` endpoint

新增 `app/api/__init__.py`、`app/api/chat.py`：

```python
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.dependencies import RuntimeServices, get_runtime_services
from app.channels.base import ChannelInput

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    user_id: str
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    responses: list[str]
    citations: list[dict] | None = None
    sufficiency: str | None = None
    judge_score: dict | None = None


@router.post("", response_model=ChatResponse)
async def chat(
    req: ChatRequest, services: RuntimeServices = Depends(get_runtime_services)
) -> ChatResponse:
    channel = services.channels["http"]
    inp = ChannelInput(
        channel="http",
        external_user_id=req.user_id,
        external_message_id=req.session_id or _new_id(),
        raw_text=req.message,
    )
    history = await channel.load_recent_history(external_user_id=req.user_id)
    state = {
        "user_input": req.message,
        "channel": "http",
        "external_user_id": req.user_id,
        "external_message_id": inp.external_message_id,
        "recent_history": history,
    }
    config = {"configurable": {"thread_id": channel.build_thread_id(inp)}}
    final = await services.rag_graph.ainvoke(state, config=config)

    contract = final.get("answer_contract")
    score = final.get("judge_score")
    return ChatResponse(
        responses=final.get("responses", []),
        citations=[c.model_dump() for c in contract.citations] if contract else None,
        sufficiency=final.get("sufficiency"),
        judge_score=score.model_dump() if score else None,
    )


def _new_id() -> str:
    import uuid
    return uuid.uuid4().hex
```

`app/main.py` 加：

```python
from app.api.chat import router as chat_router
app.include_router(chat_router)
```

## 步驟 8：DI

修改 `app/dependencies.py`：

```python
from app.channels.line import LineChannel
from app.channels.http import HttpChannel

@lru_cache(maxsize=1)
def get_channels():
    s = get_settings()
    repo = get_messages_repo()
    return {
        "line": LineChannel(s, repo),
        "http": HttpChannel(repo),
    }


@dataclass
class RuntimeServices:
    # 移除 line_client（內化進 LineChannel）
    channels: dict[str, OutputChannel]
    # ...其他
```

## 步驟 9：webhook.py 改 thin wrapper

修改 `app/line/webhook.py`：邏輯搬到 `LineChannel`，這裡只負責路由：

```python
@router.post("/webhook")
async def line_webhook(request, background_tasks, services=Depends(...)):
    channel = services.channels["line"]
    inputs = await channel.parse_request(request)
    for inp in inputs:
        background_tasks.add_task(_run_through_graph, inp, services)
    return {"ok": True}


async def _run_through_graph(inp, services):
    history = await services.channels["line"].load_recent_history(external_user_id=inp.external_user_id)
    state = {...}
    config = {"configurable": {"thread_id": services.channels["line"].build_thread_id(inp)}}
    await services.rag_graph.ainvoke(state, config=config)
```

## 步驟 10：測試

`tests/test_channels/__init__.py`、`tests/test_channels/test_line.py`、`test_http.py`、`test_stub.py`：每個 channel 一份單元測試。

加整合測試 `tests/test_api_chat.py`：

```python
@pytest.mark.asyncio
async def test_chat_endpoint(stub_services_via_overrides):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        r = await client.post("/api/chat", json={"user_id": "u1", "message": "什麼是 RAG"})
    assert r.status_code == 200
    body = r.json()
    assert body["responses"]
```

## 請輸出

1. `app/channels/{__init__,base,line,http,stub}.py`
2. `app/api/{__init__,chat}.py`
3. 修改後的 `app/graph/state.py`、`nodes.py`、`dependencies.py`、`line/webhook.py`、`main.py`
4. 全 codebase grep 把 `line_user_id` rename 為 `external_user_id`（除 `app/channels/line.py` 內部）
5. 修改後的 `Settings`：加 `enabled_channels: list[str] = ["line", "http"]`
6. `tests/test_channels/`、`tests/test_api_chat.py`
7. README 加「新增 channel」教學段，連向 `app/channels/stub.py` 為範例

## 驗收指令

```bash
pytest tests/test_channels tests/test_api_chat.py -v
pytest

# LINE 端對端
./scripts/run_local.sh
# 用 LINE 傳訊息 → 仍正常收到回覆

# Web 端對端
curl -X POST http://127.0.0.1:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"user_id":"u1","message":"什麼是 RAG？"}'
# 期望：JSON 回傳 responses

# 確認 graph 不含 LINE 字眼
grep -rn "line_user_id\|line_client" app/graph/ app/generator/ app/judge/
# 期望：零命中
```

驗收通過條件：

- LINE 與 HTTP 兩 channel 同 query 內容語意一致
- `app/graph/` 與 `app/generator/` / `app/judge/` 下不出現 "line" 字串（除 type hint）
- `tests/test_channels/` 三個 adapter 各 ≥3 測試
- HITL `thread_id` 命名 `{channel}-{user_id}-{message_id}` 不會撞 thread
- 三變體切換不需動 channel 程式

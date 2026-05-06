# task-31：串流回應（Streaming）

> 規格詳見 [spec-31](../specs/spec-31-streaming.md)

---

本 task 為 HTTP API channel 實作 SSE streaming endpoint，為 LINE channel 實作「占位訊息 + 完整回覆」雙訊息策略，降低使用者感受到的延遲。

## 前置

- P4（spec-17 judge/reflection）已完成
- spec-23（channel adapter）建議先完成（方便區分 channel 類型）
- FastAPI 已安裝

## 步驟 1：Config 新增

`app/config.py`：

```python
STREAMING_ENABLED: bool = Field(default=False, alias="STREAMING_ENABLED")
STREAMING_PLACEHOLDER: str = Field(
    default="⏳ 思考中，請稍候...",
    alias="STREAMING_PLACEHOLDER",
)
```

## 步驟 2：Generator 加 `stream_generate()`

`app/ai/providers/openai_provider.py`（或通用 generator 基底類別）：

```python
from collections.abc import AsyncIterator

async def stream_generate(
    self,
    messages: list[dict],
    model: str | None = None,
    max_tokens: int = 1024,
    temperature: float = 0.3,
) -> AsyncIterator[str]:
    stream = await self._client.chat.completions.create(
        model=model or self.model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
        stream=True,
    )
    async for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            yield delta
```

若有多個 provider（Claude、Gemini 等），在各自的 provider 中實作相同介面。

## 步驟 3：新增 SSE endpoint

新增 `app/api/stream.py`：

```python
from __future__ import annotations

import json
from functools import partial

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.config import get_settings
from app.dependencies import build_runtime_services
from app.graph.rag_graph import build_selfrag_graph

router = APIRouter()


@router.post("/api/stream/query")
async def stream_query(body: dict):
    settings = get_settings()
    services = await build_runtime_services(settings)
    graph = build_selfrag_graph(settings, services)

    query: str = body.get("query", "")
    thread_id: str = body.get("thread_id", "default")

    async def event_stream():
        state = {"query": query, "user_id": thread_id}
        async for event in graph.astream_events(state, version="v2"):
            if event["event"] == "on_chat_model_stream":
                chunk = event["data"]["chunk"]
                token = getattr(chunk, "content", "") or ""
                if token:
                    yield f"data: {json.dumps({'token': token})}\n\n"
        yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

在 `app/main.py` 掛載：

```python
from app.api.stream import router as stream_router
app.include_router(stream_router)
```

## 步驟 4：LINE channel 占位訊息策略

`app/line/webhook.py`（或 `app/channels/line_channel.py`）修改事件處理函式：

```python
async def handle_message(event, graph, settings: Settings) -> None:
    query = event.message.text
    user_id = event.source.user_id
    state = {"query": query, "user_id": user_id}

    if not settings.STREAMING_ENABLED:
        result = await graph.ainvoke(state)
        for text in result.get("responses", []):
            await line_bot_api.push_message(user_id, TextSendMessage(text=text))
        return

    # Step 1: 立刻送占位訊息
    await line_bot_api.push_message(
        user_id, TextSendMessage(text=settings.STREAMING_PLACEHOLDER)
    )

    # Step 2: 等 graph 完整結果
    result = await graph.ainvoke(state)

    # Step 3: 送正文
    for text in result.get("responses", []):
        await line_bot_api.push_message(user_id, TextSendMessage(text=text))
```

## 步驟 5：確認 LangGraph 版本

```bash
python -c "import langgraph; print(langgraph.__version__)"
```

`astream_events` 需要 `langgraph >= 0.2.0`。若版本不足：

```bash
uv pip install "langgraph>=0.2.0"
```

## 步驟 6：撰寫測試

新增 `tests/test_streaming.py`：

```python
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


@pytest.mark.asyncio
async def test_stream_generate_yields_tokens():
    """mock OpenAI stream，驗證 stream_generate 正確 yield token。"""
    from app.ai.providers.openai_provider import OpenAIProvider

    mock_stream = [
        MagicMock(choices=[MagicMock(delta=MagicMock(content="Hello"))]),
        MagicMock(choices=[MagicMock(delta=MagicMock(content=" world"))]),
        MagicMock(choices=[MagicMock(delta=MagicMock(content=None))]),
    ]

    async def async_iter():
        for item in mock_stream:
            yield item

    with patch("openai.AsyncOpenAI") as MockClient:
        instance = MockClient.return_value
        instance.chat.completions.create = AsyncMock(return_value=async_iter())
        provider = OpenAIProvider(api_key="test")
        tokens = []
        async for token in provider.stream_generate([{"role": "user", "content": "hi"}]):
            tokens.append(token)
        assert tokens == ["Hello", " world"]


def test_sse_endpoint_format(test_client):
    """驗證 /api/stream/query 回傳 text/event-stream 且含 done event。"""
    # test_client 是 FastAPI TestClient，用 mock graph
    resp = test_client.post("/api/stream/query", json={"query": "test"})
    assert resp.headers["content-type"].startswith("text/event-stream")
    lines = [l for l in resp.text.split("\n") if l.startswith("data:")]
    last = json.loads(lines[-1][len("data: "):])
    assert last.get("done") is True
```

## 步驟 7：`.env.example` 補充

```dotenv
# 串流回應
STREAMING_ENABLED=false
STREAMING_PLACEHOLDER=⏳ 思考中，請稍候...
```

## 步驟 8：手動驗收（HTTP）

```bash
curl -N -X POST http://localhost:8000/api/stream/query \
  -H "Content-Type: application/json" \
  -d '{"query": "什麼是 RAG？"}'
```

期望看到逐行輸出：

```
data: {"token": "RAG"}
data: {"token": " 是"}
data: {"token": " Retrieval"}
...
data: {"done": true}
```

---

## 里程碑 ✅

- [ ] `POST /api/stream/query` 回傳 `text/event-stream`，`curl -N` 可看到逐 token 輸出
- [ ] TTFB ≤ 800ms（本地 gpt-4o-mini，網路正常時）
- [ ] LINE channel：`STREAMING_ENABLED=true` 時先出現占位訊息，接著出現完整回覆
- [ ] `STREAMING_ENABLED=false`：行為與原本完全相同
- [ ] `pytest tests/test_streaming.py` 全綠

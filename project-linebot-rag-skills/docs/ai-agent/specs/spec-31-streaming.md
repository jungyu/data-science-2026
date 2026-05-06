# Spec-31：串流回應（Streaming）

## 背景

`generate_node` 目前等待 LLM 完整回覆後才送出，使用者在問長問題時感受到數秒延遲（TTFB = Time To First Byte）。本 spec 引入 streaming，讓使用者在 LLM 還在生成時就看到第一個字。

### 兩個 channel 的差異

| Channel | Streaming 支援 | 策略 |
|---------|--------------|------|
| **HTTP API** | ✅ SSE / chunked response | 邊生成邊推送 token |
| **LINE Bot** | ❌ LINE 無 server-push streaming | 先送「思考中...」占位訊息，回覆完成後送正文 |

---

## 設計

### 1. Config 新增

`app/config.py`：

```python
STREAMING_ENABLED: bool = Field(default=False, alias="STREAMING_ENABLED")
STREAMING_PLACEHOLDER: str = Field(
    default="⏳ 思考中，請稍候...",
    alias="STREAMING_PLACEHOLDER",
)
```

### 2. Generator 加串流模式

`app/ai/providers/openai_provider.py`（或通用 generator）新增 `stream_generate` 方法：

```python
from collections.abc import AsyncIterator


async def stream_generate(
    self,
    messages: list[dict],
    model: str | None = None,
    max_tokens: int = 1024,
    temperature: float = 0.3,
) -> AsyncIterator[str]:
    """Yield token chunks as they arrive from the LLM."""
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

### 3. HTTP API：SSE endpoint

`app/api/stream.py`（新增）：

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
    """
    SSE endpoint：每個 token 以 `data: {...}\n\n` 格式推送。
    最後一筆 data 含 `done: true`。
    """
    settings = get_settings()
    services = await build_runtime_services(settings)
    graph = build_selfrag_graph(settings, services)

    query: str = body.get("query", "")
    thread_id: str = body.get("thread_id", "default")

    async def event_stream():
        state = {"query": query, "user_id": thread_id}
        # 使用 LangGraph .astream_events() 來捕捉 generate node 的 token
        async for event in graph.astream_events(state, version="v2"):
            if event["event"] == "on_chat_model_stream":
                chunk = event["data"]["chunk"]
                token = chunk.content if hasattr(chunk, "content") else ""
                if token:
                    yield f"data: {json.dumps({'token': token})}\n\n"
        yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
```

> **LangGraph `astream_events`**：v0.2+ 支援，事件類型為 `on_chat_model_stream`。需確認 `langgraph` 版本 ≥ 0.2.0。

### 4. LINE Channel：占位訊息策略

LINE Bot 不支援 streaming push，改用雙訊息策略：

`app/channels/line_channel.py`（或 `app/line/webhook.py`）：

```python
async def handle_with_placeholder(
    event, graph, state: dict, settings: Settings
) -> None:
    """
    1. 立刻送「思考中...」
    2. 跑 graph（完整等待）
    3. 送最終回覆，並嘗試更新（LINE 不支援 edit，另送新訊息）
    """
    if not settings.STREAMING_ENABLED:
        # 原有行為
        result = await graph.ainvoke(state)
        for text in result.get("responses", []):
            await push_text(event.reply_token, text)
        return

    # Step 1: 占位
    placeholder_id = await push_text_get_id(
        event.source.user_id,
        settings.STREAMING_PLACEHOLDER,
    )

    # Step 2: 等 graph 完整回覆
    result = await graph.ainvoke(state)

    # Step 3: 送正文
    for text in result.get("responses", []):
        await push_text(event.source.user_id, text)
```

### 5. `generate_node` 選擇模式

`app/graph/nodes.py` 的 `generate_node` / `render_narrative_node` 加：

```python
async def render_narrative_node(state: RAGState, settings: Settings, generator) -> dict:
    # 非串流模式（預設）
    if not settings.STREAMING_ENABLED or state.get("channel") != "http":
        response = await generator.generate(...)
        return {"responses": [response]}

    # HTTP 串流模式：收集完整 token 存入 state，SSE endpoint 負責推送
    # graph 仍要等完整回覆才能給 judge node 評分
    tokens: list[str] = []
    async for token in generator.stream_generate(...):
        tokens.append(token)
    response = "".join(tokens)
    return {"responses": [response]}
```

> **設計說明**：`judge_node` 需要完整回覆才能評分，因此 streaming 的「逐 token 推送」只在 HTTP SSE endpoint 透過 `astream_events` 實作，graph 內部節點仍等完整回覆。

### 6. 前端 SSE 使用範例（教學用）

```javascript
const es = new EventSource("/api/stream/query?query=...");
let output = "";

es.onmessage = (e) => {
    const data = JSON.parse(e.data);
    if (data.done) {
        es.close();
        return;
    }
    output += data.token;
    document.getElementById("output").textContent = output;
};
```

---

## TTFB 改善預期

| 場景 | 改善前 TTFB | 改善後 TTFB |
|------|------------|------------|
| 短回覆（< 100 tokens）| ~1.5s | ~0.3s |
| 長回覆（500+ tokens）| ~5–8s | ~0.3s（首 token）|
| LINE（streaming）| 2–4s（等完整）| 1–2s（占位立即出現）|

---

## 可換點 / 不可換點

| | 可換 | 不可換 |
|---|---|---|
| SSE vs WebSocket | ✅ 改 WebSocket 只需換 transport 層 | ❌ `stream_generate()` → `AsyncIterator[str]` 介面 |
| 占位訊息文字 | ✅ `STREAMING_PLACEHOLDER` env var | ❌ LINE channel 不能真正做 streaming push |
| `STREAMING_ENABLED=false` | ✅ 完全退化為現有行為 | ❌ judge node 仍需完整回覆（不做 partial judge）|

---

## 驗收標準

- HTTP API：`POST /api/stream/query` 回傳 `text/event-stream`，`curl -N` 可看到逐 token 輸出
- TTFB ≤ 800ms（本地 gpt-4o-mini 呼叫）
- LINE channel：`STREAMING_ENABLED=true` 時，使用者看到占位訊息，接著看到完整回覆
- `STREAMING_ENABLED=false`：行為與原本完全相同
- pytest `tests/test_streaming.py`：mock LLM stream，驗證 SSE 事件格式正確

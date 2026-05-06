"""Streaming SSE endpoint for HTTP channel (spec-31).

Two modes：
1. streaming_enabled=False → 跑完整 graph，單次回傳完整文字（仍走 SSE 格式）
2. streaming_enabled=True  → 用 LangGraph custom stream writer 即時推送每個 token；
   render_narrative_node 偵測到 channel="http" + streaming_enabled 時改走 stream_render
"""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.dependencies import get_runtime_services

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/api/stream/query")
async def stream_query(request: Request):
    """Server-Sent Events endpoint：依 streaming_enabled 切換真串流 / 單次回覆。

    Body:  {"query": "...", "thread_id": "..."}
    SSE:   data: {"token": "..."}\\n\\n  (per delta)
           data: {"done": true}\\n\\n     (terminator)
    """
    body = await request.json()
    query: str = body.get("query", "")
    thread_id: str = body.get("thread_id", "default")

    services = get_runtime_services()
    settings = services.settings

    # ── Mode 1: streaming disabled ─────────────────────────────────────────
    if not getattr(settings, "streaming_enabled", False):
        async def single_event():
            state = {
                "user_input": query,
                "external_user_id": thread_id,
                "channel": "http",
                "dry_run": True,
            }
            try:
                result = await services.rag_graph.ainvoke(state)
                text = "\n\n".join(result.get("responses") or [""])
                yield f"data: {json.dumps({'token': text})}\n\n"
            except Exception:
                logger.exception("stream_query (single) error")
                yield f"data: {json.dumps({'token': '系統暫時無法完成此請求'})}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"
        return StreamingResponse(single_event(), media_type="text/event-stream")

    # ── Mode 2: streaming enabled — custom stream writer ───────────────────
    async def event_stream():
        state = {
            "user_input": query,
            "external_user_id": thread_id,
            "channel": "http",
            "dry_run": True,   # SSE 是輸出 channel，不要在 push_node 又送一次
        }
        try:
            # stream_mode="custom"：只接收 render_narrative_node 透過 writer 推的 dict
            async for chunk in services.rag_graph.astream(state, stream_mode="custom"):
                if isinstance(chunk, dict):
                    token = chunk.get("token", "")
                    if token:
                        yield f"data: {json.dumps({'token': token})}\n\n"
        except Exception:
            logger.exception("stream_query error")
            yield f"data: {json.dumps({'token': '\\n[系統錯誤，請稍後再試]'})}\n\n"
        yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")

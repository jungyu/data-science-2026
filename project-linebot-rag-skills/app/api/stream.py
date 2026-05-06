"""Streaming SSE endpoint for HTTP channel (spec-31)."""
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
    """Server-Sent Events endpoint: stream RAG response token by token.

    Expects JSON body: {"query": "...", "thread_id": "...", "dry_run": false}
    Each SSE event: data: {"token": "..."}\n\n
    Final event:    data: {"done": true}\n\n
    """
    body = await request.json()
    query: str = body.get("query", "")
    thread_id: str = body.get("thread_id", "default")
    dry_run: bool = body.get("dry_run", False)

    services = get_runtime_services()
    settings = services.settings

    if not getattr(settings, "streaming_enabled", False):
        # Streaming disabled: run graph and return single SSE event
        async def single_event():
            state = {
                "user_input": query,
                "external_user_id": thread_id,
                "channel": "http",
                "dry_run": dry_run,
            }
            result = await services.rag_graph.ainvoke(state)
            text = "\n\n".join(result.get("responses") or [""])
            yield f"data: {json.dumps({'token': text})}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"
        return StreamingResponse(single_event(), media_type="text/event-stream")

    # Streaming enabled: use astream_events to capture LLM token stream
    async def event_stream():
        state = {
            "user_input": query,
            "external_user_id": thread_id,
            "channel": "http",
            "dry_run": True,   # skip push_node (SSE is the output channel)
        }
        try:
            async for event in services.rag_graph.astream_events(state, version="v2"):
                kind = event.get("event", "")
                if kind == "on_chat_model_stream":
                    chunk = event["data"].get("chunk")
                    token = getattr(chunk, "content", "") or ""
                    if token:
                        yield f"data: {json.dumps({'token': token})}\n\n"
        except Exception:
            logger.exception("stream_query error")
        yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")

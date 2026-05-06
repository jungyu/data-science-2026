"""POST /api/chat — Web / API 入口。

對應 spec-23 / task-23 步驟 7。同步請求 → 跑 graph → 回 JSON。
不經 background_tasks，response 直接含 graph 輸出。
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.channels.base import ChannelInput
from app.dependencies import RuntimeServices, get_runtime_services
from app.observability.tracer import reset_current_tracer, set_current_tracer

logger = logging.getLogger(__name__)
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
    judge_warning_prefix: bool = False


@router.post("", response_model=ChatResponse)
async def chat(
    req: ChatRequest,
    services: RuntimeServices = Depends(get_runtime_services),
) -> ChatResponse:
    channel = services.channels["http"]
    inp = ChannelInput(
        channel="http",
        external_user_id=req.user_id,
        external_message_id=req.session_id or uuid.uuid4().hex,
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

    tracer = None
    token = None
    if services.tracer_registry is not None:
        tracer = services.tracer_registry.start(
            thread_id=channel.build_thread_id(inp),
            variant=services.settings.graph_variant,
        )
        token = set_current_tracer(tracer)

    try:
        final = await services.rag_graph.ainvoke(state)
    finally:
        if token is not None:
            reset_current_tracer(token)
        if tracer is not None and services.tracer_registry is not None:
            try:
                services.tracer_registry.write_trace(tracer)
            except Exception:
                logger.exception("write_trace failed")

    contract = final.get("answer_contract")
    score = final.get("judge_score")
    return ChatResponse(
        responses=final.get("responses", []),
        citations=[c.model_dump() for c in contract.citations] if contract else None,
        sufficiency=final.get("sufficiency"),
        judge_score=score.model_dump() if score else None,
        judge_warning_prefix=bool(final.get("judge_warning_prefix")),
    )

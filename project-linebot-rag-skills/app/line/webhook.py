from __future__ import annotations

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request

from app.dependencies import RuntimeServices, get_runtime_services

logger = logging.getLogger(__name__)
from app.line.schemas import LineEvent, LineWebhookPayload


router = APIRouter(prefix="/api/line", tags=["line"])


@router.post("/webhook")
async def line_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    services: RuntimeServices = Depends(get_runtime_services),
) -> dict[str, bool]:
    body = await request.body()
    signature = request.headers.get("x-line-signature")
    if not services.line_client.validate_signature(body, signature):
        raise HTTPException(status_code=400, detail="Invalid LINE signature")

    payload = LineWebhookPayload.model_validate_json(body)
    for event in payload.events:
        if event.is_text_message and event.source.user_id:
            background_tasks.add_task(process_text_event, event, services)
    return {"ok": True}


async def process_text_event(event: LineEvent, services: RuntimeServices) -> None:
    user_id = event.source.user_id
    message = event.message
    if user_id is None or message is None or message.text is None:
        return

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

    router_result = await services.router.route_message(message.text, recent_history)
    skill = services.skill_registry.get(router_result.target_skill) or services.skill_registry.require(
        "general_chat"
    )

    rag_chunks = []
    rag_context = "No retrieved context."
    if router_result.is_rag_required:
        rag_chunks = await services.retriever.retrieve(
            router_result.rag_query or message.text,
            categories=router_result.rag_categories,
            top_k=services.settings.knowledge_top_k,
            line_user_id=user_id,
            skill_id=router_result.target_skill,
        )
        rag_context = services.retriever.build_context(rag_chunks)

    try:
        responses = await services.responder.generate_response(
            user_input=message.text,
            router_result=router_result,
            skill=skill,
            rag_chunks=rag_chunks,
            rag_context=rag_context,
            recent_history=recent_history,
        )
    except Exception:
        logger.exception("generate_response failed")
        responses = ["系統暫時無法完成此請求，請稍後再試。"]

    try:
        await services.line_client.push_text(user_id, responses)
    finally:
        try:
            await services.messages_repo.save_message(
                line_user_id=user_id,
                direction="outbound",
                message_text="\n\n".join(responses),
                skill_id=router_result.target_skill,
                router_result=router_result.model_dump(),
                rag_used=bool(rag_chunks),
            )
        except Exception:
            pass

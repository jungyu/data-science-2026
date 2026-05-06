from __future__ import annotations

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, Request

from app.dependencies import RuntimeServices, get_runtime_services
from app.observability.tracer import reset_current_tracer, set_current_tracer

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/api/line", tags=["line"])


@router.post("/webhook")
async def line_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    services: RuntimeServices = Depends(get_runtime_services),
) -> dict[str, bool]:
    """LINE webhook entry — 解析委派給 LineChannel。"""
    line_channel = services.channels["line"]
    _, inputs = await line_channel.parse_request(request)
    for inp in inputs:
        background_tasks.add_task(process_channel_input, inp, services)
    return {"ok": True}


async def process_channel_input(inp, services: RuntimeServices) -> None:
    """Channel-agnostic 入口：給定 ChannelInput 跑完整 graph。

    本檔在 task-23 前是 LINE-specific；現在 LINE 與 HTTP / 其他 channel 都走這條。
    """
    channel = services.channels.get(inp.channel)
    if channel is None:
        logger.error("process_channel_input: unknown channel %r — dropping message", inp.channel)
        return
    user_id = inp.external_user_id

    # —— inbound 落庫（DB column 仍叫 line_user_id，跨 channel 用同欄位）
    try:
        await services.messages_repo.save_message(
            line_user_id=user_id,
            direction="inbound",
            message_text=inp.raw_text,
        )
    except Exception:
        logger.warning("save_message inbound failed for user=%s", user_id, exc_info=True)

    recent_history = await channel.load_recent_history(external_user_id=user_id)

    initial_state = {
        "user_input": inp.raw_text,
        "channel": inp.channel,
        "external_user_id": user_id,
        "external_message_id": inp.external_message_id,
        "recent_history": recent_history,
        "dry_run": user_id.startswith(("U_demo", "U_eval")),
    }

    tracer = None
    token = None
    if services.tracer_registry is not None:
        tracer = services.tracer_registry.start(
            thread_id=channel.build_thread_id(inp),
            variant=services.settings.graph_variant,
        )
        token = set_current_tracer(tracer)

    final_state = None
    try:
        final_state = await services.rag_graph.ainvoke(initial_state)
    except Exception:
        logger.exception("rag_graph invocation failed")
    finally:
        if token is not None:
            reset_current_tracer(token)
        if tracer is not None and services.tracer_registry is not None:
            try:
                await services.tracer_registry.async_write_trace(tracer)
            except Exception:
                logger.exception("write_trace failed")

    if final_state is None:
        return

    # —— outbound 落庫（讀 final_state）
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
        logger.warning("save_message outbound failed for user=%s", user_id, exc_info=True)


# 向後相容：既有 test_line_webhook.py 直接測 process_text_event
async def process_text_event(event, services: RuntimeServices) -> None:
    """Backward-compat shim：把 LineEvent 包成 ChannelInput 後走 process_channel_input。"""
    from app.channels.base import ChannelInput

    user_id = event.source.user_id
    message = event.message
    if user_id is None or message is None or message.text is None:
        return
    inp = ChannelInput(
        channel="line",
        external_user_id=user_id,
        external_message_id=message.id or "",
        raw_text=message.text,
    )
    await process_channel_input(inp, services)

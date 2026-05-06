"""LINE channel adapter。

對應 spec-23 / task-23 步驟 3。封裝 webhook 解析、推送、歷史對話、訊息切段。
"""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Request

from app.channels.base import ChannelInput
from app.config import Settings
from app.generator.formatter import split_for_line
from app.line.client import LineMessagingClient
from app.line.schemas import LineWebhookPayload


class LineChannel:
    name = "line"

    def __init__(self, settings: Settings, messages_repo: Any) -> None:
        self._settings = settings
        self._messages_repo = messages_repo
        self._client = LineMessagingClient(settings)

    @property
    def client(self) -> LineMessagingClient:
        """暴露 client 給 webhook 簽章驗證用。"""
        return self._client

    def validate_signature(self, body: bytes, signature: str | None) -> bool:
        return self._client.validate_signature(body, signature)

    async def parse_request(self, request: Request) -> tuple[bytes, list[ChannelInput]]:
        body = await request.body()
        sig = request.headers.get("x-line-signature")
        if not self._client.validate_signature(body, sig):
            raise HTTPException(status_code=400, detail="Invalid LINE signature")

        payload = LineWebhookPayload.model_validate_json(body)
        out: list[ChannelInput] = []
        for ev in payload.events:
            if ev.is_text_message and ev.source.user_id and ev.message and ev.message.text:
                out.append(
                    ChannelInput(
                        channel="line",
                        external_user_id=ev.source.user_id,
                        external_message_id=ev.message.id,
                        raw_text=ev.message.text,
                    )
                )
        return body, out

    def build_thread_id(self, inp: ChannelInput) -> str:
        return f"line-{inp.external_user_id}-{inp.external_message_id}"

    async def load_recent_history(
        self, *, external_user_id: str, limit: int = 5
    ) -> str:
        try:
            return await self._messages_repo.build_recent_history(
                external_user_id, limit=limit
            )
        except Exception:
            return "No recent conversation."

    def format(self, markdown: str) -> list[str]:
        return split_for_line(markdown, max_chars=self._settings.line_max_message_chars)

    async def push(self, *, recipient_id: str, messages: list[str]) -> None:
        await self._client.push_text(recipient_id, messages)

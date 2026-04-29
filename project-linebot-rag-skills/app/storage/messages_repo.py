from __future__ import annotations

from typing import Any

from app.storage.supabase_client import SupabaseRestClient


class MessagesRepository:
    def __init__(self, client: SupabaseRestClient) -> None:
        self._client = client

    async def save_message(
        self,
        *,
        line_user_id: str,
        direction: str,
        message_text: str,
        skill_id: str | None = None,
        router_result: dict[str, Any] | None = None,
        rag_used: bool = False,
    ) -> None:
        await self._client.insert(
            "line_messages",
            {
                "line_user_id": line_user_id,
                "direction": direction,
                "message_text": message_text,
                "skill_id": skill_id,
                "router_result": router_result or {},
                "rag_used": rag_used,
            },
        )

    async def list_recent_messages(self, line_user_id: str, limit: int = 5) -> list[dict[str, Any]]:
        return await self._client.select(
            "line_messages",
            {
                "select": "direction,message_text,created_at",
                "line_user_id": f"eq.{line_user_id}",
                "order": "created_at.desc",
                "limit": str(limit),
            },
        )

    async def build_recent_history(self, line_user_id: str, limit: int = 5) -> str:
        rows = await self.list_recent_messages(line_user_id, limit=limit)
        if not rows:
            return "No recent conversation."

        lines: list[str] = []
        for row in reversed(rows):
            speaker = "user" if row["direction"] == "inbound" else "assistant"
            lines.append(f"{speaker}: {row['message_text']}")
        return "\n".join(lines)

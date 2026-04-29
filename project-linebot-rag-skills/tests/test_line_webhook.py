import asyncio
import base64
import hashlib
import hmac

import httpx

from app.dependencies import get_runtime_services
from app.main import create_app
from app.rag.schemas import KnowledgeChunk
from app.router.schemas import RouterResult
from app.skills.loader import SkillDefinition


class FakeLineClient:
    def __init__(self, secret: str) -> None:
        self.secret = secret
        self.pushed_messages: list[tuple[str, list[str] | str]] = []

    def validate_signature(self, body: bytes, signature: str | None) -> bool:
        digest = hmac.new(self.secret.encode("utf-8"), body, hashlib.sha256).digest()
        expected = base64.b64encode(digest).decode("utf-8")
        return signature == expected

    async def push_text(self, user_id: str, messages: list[str] | str) -> None:
        self.pushed_messages.append((user_id, messages))


class FakeMessagesRepo:
    def __init__(self) -> None:
        self.saved_messages = []

    async def save_message(self, **kwargs) -> None:
        self.saved_messages.append(kwargs)

    async def build_recent_history(self, line_user_id: str, limit: int = 5) -> str:
        return "user: previous question"


class FakeRouter:
    async def route_message(self, user_input: str, recent_history: str) -> RouterResult:
        return RouterResult(
            target_skill="general_chat",
            is_rag_required=False,
            rag_query=user_input,
            rag_categories=[],
            emotion_state="neutral",
            response_mode="brief",
            confidence=0.9,
        )


class FakeRetriever:
    async def retrieve(self, *args, **kwargs) -> list[KnowledgeChunk]:
        return []

    def build_context(self, chunks: list[KnowledgeChunk]) -> str:
        return "No retrieved context."


class FakeResponder:
    async def generate_response(self, **kwargs) -> list[str]:
        return ["假回覆"]


class FakeSkillRegistry:
    def __init__(self) -> None:
        self.skill = SkillDefinition(
            skill_id="general_chat",
            name="一般對話",
            description="desc",
            category="general",
            system_prompt="prompt",
        )

    def get(self, skill_id: str) -> SkillDefinition | None:
        return self.skill

    def require(self, skill_id: str) -> SkillDefinition:
        return self.skill


class FakeSettings:
    knowledge_top_k = 8


def build_signature(secret: str, body: bytes) -> str:
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).digest()
    return base64.b64encode(digest).decode("utf-8")


def test_line_webhook_accepts_valid_signature_and_runs_background_task() -> None:
    secret = "unit-test-secret"
    line_client = FakeLineClient(secret)
    messages_repo = FakeMessagesRepo()
    app = create_app()
    app.dependency_overrides[get_runtime_services] = lambda: type(
        "Services",
        (),
        {
            "line_client": line_client,
            "messages_repo": messages_repo,
            "skill_registry": FakeSkillRegistry(),
            "router": FakeRouter(),
            "retriever": FakeRetriever(),
            "responder": FakeResponder(),
            "settings": FakeSettings(),
        },
    )()
    body = b"""
    {
      "destination": "bot",
      "events": [
        {
          "type": "message",
          "replyToken": "token",
          "source": {"type": "user", "userId": "U123"},
          "timestamp": 1,
          "message": {"id": "1", "type": "text", "text": "hello"}
        }
      ]
    }
    """

    async def send_request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.post(
                "/api/line/webhook",
                content=body,
                headers={"x-line-signature": build_signature(secret, body)},
            )

    response = asyncio.run(send_request())

    assert response.status_code == 200
    assert line_client.pushed_messages == [("U123", ["假回覆"])]
    assert len(messages_repo.saved_messages) == 2


def test_line_webhook_rejects_invalid_signature() -> None:
    secret = "unit-test-secret"
    app = create_app()
    app.dependency_overrides[get_runtime_services] = lambda: type(
        "Services",
        (),
        {
            "line_client": FakeLineClient(secret),
            "messages_repo": FakeMessagesRepo(),
            "skill_registry": FakeSkillRegistry(),
            "router": FakeRouter(),
            "retriever": FakeRetriever(),
            "responder": FakeResponder(),
            "settings": FakeSettings(),
        },
    )()

    async def send_request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.post(
                "/api/line/webhook",
                json={"destination": "bot", "events": []},
                headers={"x-line-signature": "bad"},
            )

    response = asyncio.run(send_request())

    assert response.status_code == 400

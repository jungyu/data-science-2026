import asyncio
import base64
import hashlib
import hmac

import httpx

from app.dependencies import get_runtime_services
from app.graph.feature_extractor import ExtractedFeatures
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

    async def retrieve_for_seed(self, *args, **kwargs) -> list[KnowledgeChunk]:
        return []

    async def log_fused_retrieval(self, **kwargs) -> None:
        pass

    def build_context(self, chunks: list[KnowledgeChunk]) -> str:
        return "No retrieved context."


class FakeResponder:
    async def generate_response(self, **kwargs) -> list[str]:
        return ["假回覆"]


class FakeFeatureExtractor:
    async def extract(self, *, user_input, recent_history=None) -> ExtractedFeatures:
        return ExtractedFeatures(
            primary_topic=user_input[:50],
            qualifiers=[],
            intent="other",
            entities=[],
            raw_query=user_input,
        )


class FakeSeedExpander:
    def expand(self, features, *, max_seeds=5):
        return [features.primary_topic] if features.primary_topic else []


class FakeSufficiencyChecker:
    def check(self, *, chunks, features):
        # FakeRetriever 永遠回 [] 觸發 insufficient；但 FakeRouter is_rag_required=False
        # 所以 check_sufficiency_node 會在前面的 short-circuit 跑「sufficient」分支
        return ("sufficient", [])


class FakeClarifier:
    async def generate_questions(self, **kwargs):
        return ["fallback q"]


class FakeContractBuilder:
    def build(self, **kwargs):
        from app.generator.contract import AnswerContract

        return AnswerContract(summary="s", key_findings=[], caveats=[], citations=[])


class FakeNarrativeRenderer:
    async def render(self, **kwargs) -> list[str]:
        return ["假回覆"]


class FakeJudge:
    async def judge(self, **kwargs):
        return None  # graceful pass-through


class FakeLineChannel:
    """模擬 LineChannel：簽章驗證、parse_request、push 都委派給 FakeLineClient。"""

    name = "line"

    def __init__(self, line_client, messages_repo) -> None:
        self._client = line_client
        self._messages_repo = messages_repo

    async def parse_request(self, request):
        from fastapi import HTTPException

        from app.channels.base import ChannelInput
        from app.line.schemas import LineWebhookPayload

        body = await request.body()
        sig = request.headers.get("x-line-signature")
        if not self._client.validate_signature(body, sig):
            raise HTTPException(status_code=400, detail="Invalid LINE signature")
        payload = LineWebhookPayload.model_validate_json(body)
        out = []
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

    def build_thread_id(self, inp) -> str:
        return f"line-{inp.external_user_id}-{inp.external_message_id}"

    async def load_recent_history(self, *, external_user_id, limit=5) -> str:
        return await self._messages_repo.build_recent_history(external_user_id, limit=limit)

    def format(self, markdown: str) -> list[str]:
        return [markdown]

    async def push(self, *, recipient_id, messages) -> None:
        await self._client.push_text(recipient_id, messages)


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
    final_context_k = 4
    line_max_message_chars = 4500
    fusion_strategy = "max"
    max_seeds = 5
    sufficiency_min_chunks = 2
    sufficiency_min_top_score = 0.4
    sufficiency_min_feature_overlap = 1
    judge_enabled = True
    judge_min_axis = 6
    judge_min_mean = 7.0
    max_reflection_retries = 1
    graph_variant = "reflection"
    hitl_enabled = False
    hitl_always_review_skills: list = []
    checkpoint_backend = "none"
    checkpoint_sqlite_path = ".checkpoints/test.db"


def build_signature(secret: str, body: bytes) -> str:
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).digest()
    return base64.b64encode(digest).decode("utf-8")


def _build_fake_services(line_client, messages_repo):
    """Build a duck-typed RuntimeServices including a real compiled rag_graph."""
    from app.graph.rag_graph import build_rag_graph

    services = type(
        "Services",
        (),
        {
            "line_client": line_client,
            "messages_repo": messages_repo,
            "skill_registry": FakeSkillRegistry(),
            "router": FakeRouter(),
            "retriever": FakeRetriever(),
            "responder": FakeResponder(),
            "feature_extractor": FakeFeatureExtractor(),
            "seed_expander": FakeSeedExpander(),
            "sufficiency_checker": FakeSufficiencyChecker(),
            "clarifier": FakeClarifier(),
            "contract_builder": FakeContractBuilder(),
            "narrative_renderer": FakeNarrativeRenderer(),
            "judge": FakeJudge(),
            "settings": FakeSettings(),
            "tracer_registry": None,
            "channels": {"line": FakeLineChannel(line_client, messages_repo)},
        },
    )()
    services.rag_graph = build_rag_graph(services)
    return services


def test_line_webhook_accepts_valid_signature_and_runs_background_task() -> None:
    secret = "unit-test-secret"
    line_client = FakeLineClient(secret)
    messages_repo = FakeMessagesRepo()
    app = create_app()
    app.dependency_overrides[get_runtime_services] = lambda: _build_fake_services(
        line_client, messages_repo
    )
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


def test_line_webhook_passes_thread_id_config_to_graph() -> None:
    """spec-21 §「config 與 thread_id」：webhook 呼叫 graph.ainvoke 必須帶
    `config={"configurable": {"thread_id": ...}}`，否則 checkpointer / HITL
    在 production 路徑都不會生效。"""
    secret = "unit-test-secret"
    line_client = FakeLineClient(secret)
    messages_repo = FakeMessagesRepo()
    services = _build_fake_services(line_client, messages_repo)

    captured: dict = {}
    real_ainvoke = services.rag_graph.ainvoke

    async def spy_ainvoke(state, config=None, **kw):
        captured["config"] = config
        return await real_ainvoke(state, config=config, **kw) if config else await real_ainvoke(state, **kw)

    services.rag_graph.ainvoke = spy_ainvoke  # type: ignore[method-assign]

    app = create_app()
    app.dependency_overrides[get_runtime_services] = lambda: services

    body = b"""
    {
      "destination": "bot",
      "events": [
        {
          "type": "message",
          "replyToken": "token",
          "source": {"type": "user", "userId": "U999"},
          "timestamp": 1,
          "message": {"id": "msg-42", "type": "text", "text": "hi"}
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
    assert captured.get("config") is not None, "graph.ainvoke 未收到 config"
    thread_id = captured["config"]["configurable"]["thread_id"]
    # FakeLineChannel.build_thread_id 回 line-{user}-{msg_id}
    assert thread_id == "line-U999-msg-42"


def test_line_webhook_rejects_invalid_signature() -> None:
    secret = "unit-test-secret"
    app = create_app()
    app.dependency_overrides[get_runtime_services] = lambda: _build_fake_services(
        FakeLineClient(secret), FakeMessagesRepo()
    )

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

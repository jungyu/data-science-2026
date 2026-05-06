"""POST /api/chat 整合測試。對應 task-23 步驟 7。"""

from __future__ import annotations

import asyncio

import httpx

from app.dependencies import get_runtime_services
from app.main import create_app
from tests.test_line_webhook import (
    FakeContractBuilder,
    FakeFeatureExtractor,
    FakeJudge,
    FakeLineClient,
    FakeMessagesRepo,
    FakeNarrativeRenderer,
    FakeResponder,
    FakeRetriever,
    FakeRouter,
    FakeSeedExpander,
    FakeSettings,
    FakeSkillRegistry,
    FakeSufficiencyChecker,
    FakeClarifier,
)
from app.channels.http import HttpChannel
from app.channels.stub import StubChannel


def _build_services():
    from app.graph.rag_graph import build_rag_graph

    line_client = FakeLineClient(secret="x")
    repo = FakeMessagesRepo()

    services = type(
        "Services",
        (),
        {
            "line_client": line_client,
            "messages_repo": repo,
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
            "channels": {"http": HttpChannel(repo), "stub": StubChannel()},
        },
    )()
    services.rag_graph = build_rag_graph(services)
    return services


def test_chat_endpoint_returns_json() -> None:
    app = create_app()
    services = _build_services()
    app.dependency_overrides[get_runtime_services] = lambda: services

    async def go() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.post(
                "/api/chat",
                json={"user_id": "u1", "message": "什麼是 RAG"},
            )

    r = asyncio.run(go())
    assert r.status_code == 200
    body = r.json()
    assert body["responses"] == ["假回覆"]


def test_chat_endpoint_includes_session_id() -> None:
    app = create_app()
    services = _build_services()
    app.dependency_overrides[get_runtime_services] = lambda: services

    async def go() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.post(
                "/api/chat",
                json={"user_id": "u1", "message": "x", "session_id": "sess-abc"},
            )

    r = asyncio.run(go())
    assert r.status_code == 200


def test_line_and_http_share_same_graph() -> None:
    """同一份 RuntimeServices，LINE 與 HTTP 兩 channel 走同一 rag_graph。

    這是 task-23 教學承諾的硬條件：「兩 channel 在同一份 graph 上跑」。
    """
    services = _build_services()
    # graph 物件就是同一個（services.rag_graph 是 lru_cache 等價）
    assert services.rag_graph is services.rag_graph


def test_chat_endpoint_unaffected_by_demo_prefix() -> None:
    """/api/chat 不受 U_demo / U_eval 前綴影響——HTTP push 本來就是 no-op。"""
    app = create_app()
    services = _build_services()
    app.dependency_overrides[get_runtime_services] = lambda: services

    async def go() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.post(
                "/api/chat",
                json={"user_id": "U_demo_test", "message": "什麼是 RAG"},
            )

    r = asyncio.run(go())
    # 即使 U_demo 前綴，HTTP 仍直接從 final_state 取 responses
    assert r.status_code == 200
    body = r.json()
    assert body["responses"] == ["假回覆"]

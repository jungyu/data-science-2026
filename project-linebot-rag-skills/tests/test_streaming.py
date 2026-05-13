"""spec-31 acceptance tests for streaming.

涵蓋三層：
1. NarrativeRenderer.stream_render() — 串流路徑 + fallback
2. OpenAIChatLLM.stream_complete() — async generator behavior
3. SSE endpoint — disabled / enabled 兩條路徑（mock graph）
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.generator.contract import AnswerContract, Citation, KeyFinding
from app.generator.narrative import NarrativeRenderer
from app.skills.loader import SkillDefinition


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_contract() -> AnswerContract:
    cit = Citation(chunk_id="c-1", source="docs/x.md", snippet="片段")
    return AnswerContract(
        summary="RAG 是檢索增強生成",
        key_findings=[KeyFinding(point="先檢索後生成", citations=["c-1"])],
        caveats=["僅供參考"],
        next_steps=[],
        citations=[cit],
    )


def _make_skill() -> SkillDefinition:
    return SkillDefinition(
        skill_id="general_chat",
        name="一般對話",
        description="d",
        category="general",
        system_prompt="prompt",
    )


class _FakeStreamingLLM:
    """yield 預設 chunks 的 mock LLM。"""

    def __init__(self, chunks: list[str], *, fail: bool = False) -> None:
        self._chunks = chunks
        self._fail = fail

    async def complete(self, prompt: str) -> str:
        return "".join(self._chunks)

    async def stream_complete(self, prompt: str):
        if self._fail:
            raise RuntimeError("stream failure")
        for c in self._chunks:
            yield c


class _NonStreamingLLM:
    """只實作 complete，沒有 stream_complete — 觸發 fallback path。"""

    async def complete(self, prompt: str) -> str:
        return "non-streaming complete"


# ── NarrativeRenderer.stream_render ──────────────────────────────────────────

class TestStreamRender:
    @pytest.mark.asyncio
    async def test_stream_yields_chunks(self):
        llm = _FakeStreamingLLM(["你好", "，", "RAG"])
        renderer = NarrativeRenderer(llm=llm)

        chunks: list[str] = []
        async for tok in renderer.stream_render(
            contract=_make_contract(),
            skill=_make_skill(),
            response_mode="brief",
        ):
            chunks.append(tok)

        assert chunks == ["你好", "，", "RAG"]

    @pytest.mark.asyncio
    async def test_stream_falls_back_to_complete_when_no_stream_method(self):
        llm = _NonStreamingLLM()
        renderer = NarrativeRenderer(llm=llm)

        chunks: list[str] = []
        async for tok in renderer.stream_render(
            contract=_make_contract(),
            skill=_make_skill(),
            response_mode="brief",
        ):
            chunks.append(tok)

        # 退化路徑：一次 yield 全部
        assert chunks == ["non-streaming complete"]

    @pytest.mark.asyncio
    async def test_stream_failure_yields_template_fallback(self):
        llm = _FakeStreamingLLM(["x"], fail=True)
        renderer = NarrativeRenderer(llm=llm)

        chunks: list[str] = []
        async for tok in renderer.stream_render(
            contract=_make_contract(),
            skill=_make_skill(),
            response_mode="brief",
        ):
            chunks.append(tok)

        # fallback 模板包含 contract summary
        full = "".join(chunks)
        assert "RAG 是檢索增強生成" in full
        assert "降級輸出" in full

    @pytest.mark.asyncio
    async def test_stream_no_llm_yields_template(self):
        renderer = NarrativeRenderer(llm=None)
        chunks: list[str] = []
        async for tok in renderer.stream_render(
            contract=_make_contract(),
            skill=_make_skill(),
            response_mode="brief",
        ):
            chunks.append(tok)
        full = "".join(chunks)
        assert "RAG 是檢索增強生成" in full


# ── OpenAIChatLLM.stream_complete ────────────────────────────────────────────

class TestOpenAIChatStream:
    @pytest.mark.asyncio
    async def test_yields_only_non_empty_deltas(self):
        from app.ai.providers.openai_provider import OpenAIChatLLM

        async def fake_stream():
            for content in ["Hello", " ", "world", None, ""]:
                delta = MagicMock()
                delta.content = content
                choice = MagicMock(delta=delta)
                yield MagicMock(choices=[choice])

        # The OpenAI client method itself is async; create returns the iterator
        llm = OpenAIChatLLM(api_key="k", base_url="https://test", model="gpt-4o-mini")
        llm._client.chat.completions.create = AsyncMock(return_value=fake_stream())

        out: list[str] = []
        async for delta in llm.stream_complete("test"):
            out.append(delta)

        assert out == ["Hello", " ", "world"]


# ── SSE endpoint ─────────────────────────────────────────────────────────────

class TestSseEndpoint:
    def test_disabled_streaming_returns_single_event(self):
        """streaming_enabled=False → ainvoke 路徑，回傳完整文字 + done。"""
        from fastapi.testclient import TestClient
        from app.main import app
        from app.dependencies import get_runtime_services

        # mock services with streaming disabled and a graph that returns a fixed response
        @dataclass
        class _S:
            streaming_enabled: bool = False

        mock_graph = MagicMock()
        mock_graph.ainvoke = AsyncMock(return_value={"responses": ["完整回覆"]})
        mock_services = MagicMock()
        mock_services.settings = _S()
        mock_services.rag_graph = mock_graph

        app.dependency_overrides = {}  # ensure clean
        with patch("app.api.stream.get_runtime_services", return_value=mock_services):
            with TestClient(app) as client:
                resp = client.post("/api/stream/query", json={"query": "test"})
                assert resp.status_code == 200
                assert resp.headers["content-type"].startswith("text/event-stream")
                body = resp.text
                # SSE 內 JSON 用 ensure_ascii=True（預設）→ 中文以 \uXXXX 編碼
                # decode 回中文驗證
                import json as _j
                tokens = []
                for line in body.split("\n"):
                    if line.startswith("data:"):
                        data = _j.loads(line[len("data: "):])
                        if "token" in data:
                            tokens.append(data["token"])
                assert "完整回覆" in "".join(tokens)
                assert '"done": true' in body

    def test_oversized_body_returns_413(self):
        """spec-31：HTTP 層 body size 限制（32KB），超過拒絕。"""
        from fastapi.testclient import TestClient
        from app.main import app

        @dataclass
        class _S:
            streaming_enabled: bool = False
            security_max_input_chars: int = 1000

        mock_services = MagicMock()
        mock_services.settings = _S()

        with patch("app.api.stream.get_runtime_services", return_value=mock_services):
            with TestClient(app) as client:
                # 40KB query → exceed 32KB body cap
                big_query = "x" * 40000
                resp = client.post("/api/stream/query", json={"query": big_query})
                assert resp.status_code == 413

    def test_query_exceeding_max_chars_returns_413(self):
        """query 超過 security_max_input_chars 直接拒絕（不浪費 graph 資源）。"""
        from fastapi.testclient import TestClient
        from app.main import app

        @dataclass
        class _S:
            streaming_enabled: bool = False
            security_max_input_chars: int = 50

        mock_services = MagicMock()
        mock_services.settings = _S()

        with patch("app.api.stream.get_runtime_services", return_value=mock_services):
            with TestClient(app) as client:
                resp = client.post(
                    "/api/stream/query", json={"query": "x" * 100}
                )
                assert resp.status_code == 413
                assert "exceeds 50 chars" in resp.text

    def test_invalid_json_returns_400(self):
        from fastapi.testclient import TestClient
        from app.main import app

        with TestClient(app) as client:
            resp = client.post(
                "/api/stream/query",
                content="not json {",
                headers={"content-type": "application/json"},
            )
            assert resp.status_code == 400

    def test_enabled_streaming_uses_custom_stream_mode(self):
        """streaming_enabled=True → astream(stream_mode='custom')，逐 token 推送。"""
        from fastapi.testclient import TestClient
        from app.main import app

        @dataclass
        class _S:
            streaming_enabled: bool = True

        async def fake_astream(state, config=None, stream_mode="custom"):
            # spec-21：stream endpoint 現在會帶 thread_id config
            assert stream_mode == "custom"
            assert config and config["configurable"]["thread_id"]
            for tok in ["第一", "段", "回覆"]:
                yield {"token": tok}

        mock_graph = MagicMock()
        mock_graph.astream = fake_astream
        mock_services = MagicMock()
        mock_services.settings = _S()
        mock_services.rag_graph = mock_graph

        with patch("app.api.stream.get_runtime_services", return_value=mock_services):
            with TestClient(app) as client:
                resp = client.post("/api/stream/query", json={"query": "test"})
                assert resp.status_code == 200
                body = resp.text
                # 三個 token 各成一個 SSE 事件
                assert body.count("data:") >= 4   # 3 tokens + done
                import json as _j
                tokens = []
                for line in body.split("\n"):
                    if line.startswith("data:"):
                        data = _j.loads(line[len("data: "):])
                        if "token" in data:
                            tokens.append(data["token"])
                assert "第一" in tokens
                assert "段" in tokens
                assert "回覆" in tokens
                assert '"done": true' in body

"""spec-26 acceptance tests for app/graph/query_transform.py."""
from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.graph.query_transform import query_transform_node


@dataclass
class _Settings:
    query_transform_strategy: str = "none"
    hyde_model: str = ""
    hyde_max_tokens: int = 150
    step_back_model: str = ""
    decompose_max_subqueries: int = 3
    router_model: str = "gpt-4o-mini"
    openai_api_key: str = "test-key"
    openai_base_url: str = "https://api.openai.com/v1"


@dataclass
class _Services:
    settings: _Settings


def _mock_openai_chat_response(content: str):
    """Build a mock that emulates AsyncOpenAI().chat.completions.create()."""
    mock_message = MagicMock()
    mock_message.content = content
    mock_choice = MagicMock(message=mock_message)
    mock_resp = MagicMock(choices=[mock_choice])
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)
    return mock_client


# ── strategy = none ──────────────────────────────────────────────────────────

class TestNoneStrategy:
    @pytest.mark.asyncio
    async def test_passthrough(self):
        services = _Services(settings=_Settings(query_transform_strategy="none"))
        state = {"user_input": "什麼是 RAG？"}
        result = await query_transform_node(state, services)

        assert result["transformed_queries"] == ["什麼是 RAG？"]
        assert result["hyde_doc"] is None
        assert result["transform_strategy"] == "none"

    @pytest.mark.asyncio
    async def test_unknown_strategy_falls_back_to_none(self):
        services = _Services(settings=_Settings(query_transform_strategy="bogus"))
        state = {"user_input": "test"}
        result = await query_transform_node(state, services)

        assert result["transformed_queries"] == ["test"]
        assert result["transform_strategy"] == "none"


# ── strategy = hyde ──────────────────────────────────────────────────────────

class TestHydeStrategy:
    @pytest.mark.asyncio
    async def test_hyde_generates_hypothetical_doc(self):
        services = _Services(settings=_Settings(query_transform_strategy="hyde"))
        state = {"user_input": "什麼是向量資料庫？"}

        mock_client = _mock_openai_chat_response(
            "向量資料庫是專門用來儲存和搜尋高維度向量的資料庫系統。"
        )
        with patch("openai.AsyncOpenAI", return_value=mock_client):
            result = await query_transform_node(state, services)

        assert result["transform_strategy"] == "hyde"
        assert result["hyde_doc"] is not None
        assert "向量" in result["hyde_doc"]
        # transformed_queries[0] = hyde_doc, [1] = original
        assert len(result["transformed_queries"]) == 2
        assert result["transformed_queries"][0] == result["hyde_doc"]
        assert result["transformed_queries"][1] == "什麼是向量資料庫？"

    @pytest.mark.asyncio
    async def test_hyde_failure_falls_back_gracefully(self):
        services = _Services(settings=_Settings(query_transform_strategy="hyde"))
        state = {"user_input": "test"}

        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(side_effect=RuntimeError("LLM down"))
        with patch("openai.AsyncOpenAI", return_value=mock_client):
            result = await query_transform_node(state, services)

        assert result["transform_strategy"] == "none"
        assert result["transformed_queries"] == ["test"]
        assert result["hyde_doc"] is None


# ── strategy = step_back ─────────────────────────────────────────────────────

class TestStepBackStrategy:
    @pytest.mark.asyncio
    async def test_step_back_returns_two_queries(self):
        services = _Services(settings=_Settings(query_transform_strategy="step_back"))
        state = {"user_input": "React 18 的 useTransition 怎麼用？"}

        mock_client = _mock_openai_chat_response("React Hooks 有哪些？")
        with patch("openai.AsyncOpenAI", return_value=mock_client):
            result = await query_transform_node(state, services)

        assert result["transform_strategy"] == "step_back"
        assert len(result["transformed_queries"]) == 2
        assert result["transformed_queries"][0] == "React Hooks 有哪些？"  # 抽象問題
        assert result["transformed_queries"][1] == "React 18 的 useTransition 怎麼用？"  # 原問題
        assert result["hyde_doc"] is None


# ── strategy = decompose ─────────────────────────────────────────────────────

class TestDecomposeStrategy:
    @pytest.mark.asyncio
    async def test_decompose_compound_query(self):
        services = _Services(
            settings=_Settings(query_transform_strategy="decompose", decompose_max_subqueries=3)
        )
        state = {"user_input": "React 18 的 SSR 和 Next.js 的 streaming 怎麼搭？"}

        json_payload = (
            '{"questions": ["React 18 SSR 是什麼？", "Next.js streaming 是什麼？", '
            '"如何整合？"]}'
        )
        mock_client = _mock_openai_chat_response(json_payload)
        with patch("openai.AsyncOpenAI", return_value=mock_client):
            result = await query_transform_node(state, services)

        assert result["transform_strategy"] == "decompose"
        assert len(result["transformed_queries"]) == 3
        assert "React 18 SSR" in result["transformed_queries"][0]

    @pytest.mark.asyncio
    async def test_decompose_caps_at_max(self):
        services = _Services(
            settings=_Settings(query_transform_strategy="decompose", decompose_max_subqueries=2)
        )
        state = {"user_input": "test"}

        # LLM returns 5 subqueries — should be truncated to 2
        json_payload = '{"questions": ["q1", "q2", "q3", "q4", "q5"]}'
        mock_client = _mock_openai_chat_response(json_payload)
        with patch("openai.AsyncOpenAI", return_value=mock_client):
            result = await query_transform_node(state, services)

        assert len(result["transformed_queries"]) == 2

    @pytest.mark.asyncio
    async def test_decompose_invalid_json_falls_back_to_original(self):
        services = _Services(settings=_Settings(query_transform_strategy="decompose"))
        state = {"user_input": "single question"}

        # malformed JSON
        mock_client = _mock_openai_chat_response("not valid json {")
        with patch("openai.AsyncOpenAI", return_value=mock_client):
            result = await query_transform_node(state, services)

        # Implementation catches JSONDecodeError → uses [user_input]
        # OR may fall through to outer except → strategy=none
        assert result["transformed_queries"] == ["single question"]

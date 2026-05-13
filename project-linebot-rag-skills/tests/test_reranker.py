"""spec-28 acceptance tests for app/rag/reranker.py."""
from __future__ import annotations

import sys
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.rag.reranker import (
    BgeReranker,
    CohereReranker,
    make_reranker,
    select_top_chunks,
)
from app.rag.schemas import KnowledgeChunk


@dataclass
class _Settings:
    reranker_enabled: bool = True
    reranker_provider: str = "cohere"
    reranker_model: str = "rerank-multilingual-v3.0"
    reranker_top_n: int = 5
    cohere_api_key: str = "test-key"
    bge_reranker_model: str = "BAAI/bge-reranker-base"


def _make_chunks(n: int) -> list[KnowledgeChunk]:
    return [
        KnowledgeChunk(
            id=f"c-{i}",
            content=f"chunk {i}",
            category="general",
            combined_score=float(i) / max(n - 1, 1),
        )
        for i in range(n)
    ]


# ── select_top_chunks (fallback path) ────────────────────────────────────────

class TestSelectTopChunks:
    def test_sorts_descending(self):
        chunks = _make_chunks(5)
        result = select_top_chunks(chunks, 3)
        assert len(result) == 3
        assert result[0].id == "c-4"  # highest score
        assert result[1].id == "c-3"
        assert result[2].id == "c-2"

    def test_limit_larger_than_input(self):
        chunks = _make_chunks(2)
        result = select_top_chunks(chunks, 10)
        assert len(result) == 2

    def test_empty(self):
        assert select_top_chunks([], 5) == []


# ── make_reranker factory ────────────────────────────────────────────────────

class TestMakeReranker:
    def test_disabled_returns_none(self):
        s = _Settings(reranker_enabled=False)
        assert make_reranker(s) is None

    def test_cohere_missing_api_key_returns_none(self, caplog):
        """spec-04 §Fallback：缺 COHERE_API_KEY 時靜默降回 RRF，不拋。"""
        import logging
        s = _Settings(reranker_enabled=True, reranker_provider="cohere", cohere_api_key="")
        with caplog.at_level(logging.WARNING):
            result = make_reranker(s)
        assert result is None
        assert any("COHERE_API_KEY" in rec.message for rec in caplog.records)

    def test_unknown_provider_raises(self):
        s = _Settings(reranker_enabled=True, reranker_provider="unknown")
        with pytest.raises(ValueError, match="Unknown reranker_provider"):
            make_reranker(s)

    def test_cohere_provider_returns_instance(self):
        # mock cohere module so import doesn't require the real package
        mock_cohere = MagicMock()
        mock_cohere.AsyncClientV2 = MagicMock(return_value=MagicMock())
        with patch.dict(sys.modules, {"cohere": mock_cohere}):
            s = _Settings(reranker_enabled=True, reranker_provider="cohere")
            r = make_reranker(s)
            assert isinstance(r, CohereReranker)


# ── CohereReranker behavior (mocked client) ──────────────────────────────────

class TestCohereReranker:
    @pytest.mark.asyncio
    async def test_rerank_reorders_and_sets_score(self):
        # Cohere returns results sorted by relevance with index pointing to input docs
        mock_response = MagicMock()
        mock_response.results = [
            MagicMock(index=2, relevance_score=0.95),
            MagicMock(index=0, relevance_score=0.70),
        ]
        mock_client = MagicMock()
        mock_client.rerank = AsyncMock(return_value=mock_response)

        mock_cohere = MagicMock()
        mock_cohere.AsyncClientV2 = MagicMock(return_value=mock_client)

        with patch.dict(sys.modules, {"cohere": mock_cohere}):
            r = CohereReranker(api_key="test", model="rerank-multilingual-v3.0")
            chunks = _make_chunks(5)
            result = await r.rerank("query", chunks, top_n=2)

            assert len(result) == 2
            assert result[0].id == "c-2"
            assert result[0].combined_score == pytest.approx(0.95)
            assert result[1].id == "c-0"
            assert result[1].combined_score == pytest.approx(0.70)

    @pytest.mark.asyncio
    async def test_rerank_empty_chunks(self):
        mock_cohere = MagicMock()
        mock_cohere.AsyncClientV2 = MagicMock(return_value=MagicMock())
        with patch.dict(sys.modules, {"cohere": mock_cohere}):
            r = CohereReranker(api_key="test")
            assert await r.rerank("query", [], top_n=5) == []

    @pytest.mark.asyncio
    async def test_rerank_api_failure_falls_back_to_rrf(self, caplog):
        """spec-04 §Fallback：Cohere API 拋例外（超時 / 限流）時不打斷，依
        既有 combined_score 排序回傳 top_n。"""
        import logging

        mock_client = MagicMock()
        mock_client.rerank = AsyncMock(side_effect=RuntimeError("cohere down"))

        mock_cohere = MagicMock()
        mock_cohere.AsyncClientV2 = MagicMock(return_value=mock_client)

        with patch.dict(sys.modules, {"cohere": mock_cohere}):
            r = CohereReranker(api_key="test")
            chunks = _make_chunks(5)
            with caplog.at_level(logging.WARNING):
                result = await r.rerank("query", chunks, top_n=3)
            # 回 3 筆且依 combined_score 倒序（=RRF fallback 行為）
            assert [c.id for c in result] == ["c-4", "c-3", "c-2"]
            assert any("Cohere rerank failed" in rec.message for rec in caplog.records)

    @pytest.mark.asyncio
    async def test_top_n_capped_at_input_size(self):
        """top_n=10 with only 3 chunks should request top_n=3 from Cohere."""
        mock_response = MagicMock()
        mock_response.results = [
            MagicMock(index=0, relevance_score=0.5),
        ]
        mock_client = MagicMock()
        mock_client.rerank = AsyncMock(return_value=mock_response)

        mock_cohere = MagicMock()
        mock_cohere.AsyncClientV2 = MagicMock(return_value=mock_client)

        with patch.dict(sys.modules, {"cohere": mock_cohere}):
            r = CohereReranker(api_key="test")
            await r.rerank("query", _make_chunks(3), top_n=10)
            # Verify Cohere was called with capped top_n
            call_kwargs = mock_client.rerank.call_args.kwargs
            assert call_kwargs["top_n"] == 3


# ── BgeReranker integration (skip if not installed) ──────────────────────────

class TestBgeReranker:
    @pytest.mark.asyncio
    async def test_bge_reranker_with_mocked_module(self):
        """Mock sentence_transformers to avoid loading 200MB+ model in tests."""
        mock_st = MagicMock()
        mock_model = MagicMock()
        # CrossEncoder.predict is sync, returns list of float scores
        mock_model.predict = MagicMock(return_value=[0.9, 0.5, 0.7])
        mock_st.CrossEncoder = MagicMock(return_value=mock_model)

        with patch.dict(sys.modules, {"sentence_transformers": mock_st}):
            r = BgeReranker(model_name="dummy")
            chunks = _make_chunks(3)
            result = await r.rerank("query", chunks, top_n=2)

            assert len(result) == 2
            # Highest mocked score is 0.9 (index 0), then 0.7 (index 2)
            assert result[0].id == "c-0"
            assert result[0].combined_score == pytest.approx(0.9)
            assert result[1].id == "c-2"
            assert result[1].combined_score == pytest.approx(0.7)

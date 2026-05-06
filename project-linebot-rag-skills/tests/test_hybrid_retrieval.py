"""spec-27 acceptance tests for hybrid retrieval weight threading.

驗證 settings.hybrid_enabled / weights 是否正確透傳：
  RAGRetriever → store.search → SearchFilters → KnowledgeRepository → RPC params
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from unittest.mock import AsyncMock

import pytest

from app.config import Settings
from app.rag.retriever import RAGRetriever
from app.rag.schemas import KnowledgeChunk
from app.storage.knowledge_store import SearchFilters


# ── Settings validator ──────────────────────────────────────────────────────

class TestHybridConfigValidator:
    def test_disabled_skips_validation(self):
        # Even with weights summing to 0.5, validator passes when hybrid disabled
        s = Settings(
            hybrid_enabled=False,
            hybrid_vector_weight=0.3,
            hybrid_keyword_weight=0.2,
        )
        assert s.hybrid_enabled is False

    def test_enabled_requires_weights_sum_to_1(self):
        with pytest.raises(ValueError, match="must equal 1.0"):
            Settings(
                hybrid_enabled=True,
                hybrid_vector_weight=0.8,
                hybrid_keyword_weight=0.5,
            )

    def test_enabled_default_weights_pass(self):
        s = Settings(
            hybrid_enabled=True,
            hybrid_vector_weight=0.7,
            hybrid_keyword_weight=0.3,
        )
        assert s.hybrid_enabled is True
        assert s.hybrid_vector_weight + s.hybrid_keyword_weight == pytest.approx(1.0)


# ── SearchFilters carries weights ────────────────────────────────────────────

class TestSearchFiltersDefaults:
    def test_default_weights_vector_only(self):
        f = SearchFilters()
        assert f.vector_weight == 1.0
        assert f.keyword_weight == 0.0

    def test_can_set_weights(self):
        f = SearchFilters(vector_weight=0.6, keyword_weight=0.4)
        assert f.vector_weight == 0.6
        assert f.keyword_weight == 0.4


# ── RAGRetriever weight threading ────────────────────────────────────────────

@dataclass
class _StubEmbedder:
    async def embed_query(self, text: str) -> list[float]:
        return [0.1] * 4


@dataclass
class _CapturingStore:
    """Captures the SearchFilters that retriever passed in."""
    name: str = "stub"
    captured_filters: SearchFilters | None = None

    async def search(
        self,
        *,
        query_embedding: list[float],
        query_text: str | None = None,
        filters: SearchFilters | None = None,
        top_k: int = 8,
    ) -> list[KnowledgeChunk]:
        self.captured_filters = filters
        return []


@dataclass
class _StubLogsRepo:
    async def log_retrieval(self, record) -> None:
        pass


@dataclass
class _StubSettings:
    hybrid_enabled: bool = False
    hybrid_vector_weight: float = 0.7
    hybrid_keyword_weight: float = 0.3


class TestRetrieverThreading:
    @pytest.mark.asyncio
    async def test_hybrid_disabled_passes_vector_only_weights(self):
        store = _CapturingStore()
        retriever = RAGRetriever(
            embedder=_StubEmbedder(),
            store=store,
            logs_repo=_StubLogsRepo(),
            settings=_StubSettings(hybrid_enabled=False),
        )
        await retriever.retrieve_for_seed("query", categories=None, top_k=5)

        assert store.captured_filters is not None
        assert store.captured_filters.vector_weight == 1.0
        assert store.captured_filters.keyword_weight == 0.0

    @pytest.mark.asyncio
    async def test_hybrid_enabled_passes_configured_weights(self):
        store = _CapturingStore()
        retriever = RAGRetriever(
            embedder=_StubEmbedder(),
            store=store,
            logs_repo=_StubLogsRepo(),
            settings=_StubSettings(
                hybrid_enabled=True,
                hybrid_vector_weight=0.6,
                hybrid_keyword_weight=0.4,
            ),
        )
        await retriever.retrieve_for_seed("query", categories=None, top_k=5)

        assert store.captured_filters.vector_weight == pytest.approx(0.6)
        assert store.captured_filters.keyword_weight == pytest.approx(0.4)

    @pytest.mark.asyncio
    async def test_no_settings_defaults_to_vector_only(self):
        """Backwards compatibility: retriever without settings field."""
        store = _CapturingStore()
        retriever = RAGRetriever(
            embedder=_StubEmbedder(),
            store=store,
            logs_repo=_StubLogsRepo(),
            settings=None,
        )
        await retriever.retrieve_for_seed("query", categories=None, top_k=5)

        assert store.captured_filters.vector_weight == 1.0
        assert store.captured_filters.keyword_weight == 0.0

    @pytest.mark.asyncio
    async def test_categories_still_threaded(self):
        store = _CapturingStore()
        retriever = RAGRetriever(
            embedder=_StubEmbedder(),
            store=store,
            logs_repo=_StubLogsRepo(),
            settings=_StubSettings(hybrid_enabled=True),
        )
        await retriever.retrieve_for_seed(
            "query", categories=["tech", "tutorial"], top_k=5
        )
        assert store.captured_filters.categories == ["tech", "tutorial"]


# ── KnowledgeRepository RPC param threading ──────────────────────────────────

class TestRepoRpcParams:
    @pytest.mark.asyncio
    async def test_rpc_receives_weights(self):
        from app.storage.knowledge_repo import KnowledgeRepository

        captured: dict[str, Any] = {}

        class _StubClient:
            async def rpc(self, name, params):
                captured["name"] = name
                captured["params"] = params
                return []

        repo = KnowledgeRepository(_StubClient())
        await repo.match_private_knowledge(
            query_embedding=[0.1, 0.2],
            query_text="test query",
            top_k=5,
            vector_weight=0.6,
            keyword_weight=0.4,
        )

        assert captured["name"] == "match_private_knowledge"
        assert captured["params"]["vector_weight"] == pytest.approx(0.6)
        assert captured["params"]["keyword_weight"] == pytest.approx(0.4)
        assert captured["params"]["query_text"] == "test query"
        assert captured["params"]["match_count"] == 5

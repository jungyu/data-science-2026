import asyncio

import pytest

from app.rag.retriever import RAGRetriever
from app.rag.schemas import KnowledgeChunk


class FakeEmbedder:
    async def embed_query(self, text: str) -> list[float]:
        return [0.1, 0.2, 0.3]


class BrokenEmbedder:
    async def embed_query(self, text: str) -> list[float]:
        raise RuntimeError("boom")


class FakeKnowledgeRepository:
    async def match_private_knowledge(
        self,
        *,
        query_embedding: list[float],
        query_text: str,
        categories: list[str] | None = None,
        top_k: int = 8,
    ) -> list[KnowledgeChunk]:
        return [
            KnowledgeChunk(
                id="a",
                title="Spec A",
                content="Chunk A",
                category="engineering",
                combined_score=0.4,
            ),
            KnowledgeChunk(
                id="b",
                title="Spec B",
                content="Chunk B",
                category="engineering",
                combined_score=0.9,
            ),
        ]


class FakeLogsRepository:
    def __init__(self) -> None:
        self.records = []

    async def log_retrieval(self, record) -> None:
        self.records.append(record)


def test_retriever_returns_ranked_chunks_and_logs() -> None:
    logs_repo = FakeLogsRepository()
    retriever = RAGRetriever(
        embedder=FakeEmbedder(),
        knowledge_repo=FakeKnowledgeRepository(),
        logs_repo=logs_repo,
        final_context_k=1,
    )

    results = asyncio.run(
        retriever.retrieve(
            "webhook architecture",
            categories=["engineering"],
            line_user_id="U123",
            skill_id="tech_architect",
        )
    )

    assert [chunk.id for chunk in results] == ["b"]
    assert len(logs_repo.records) == 1
    assert logs_repo.records[0].retrieved_ids == ["b"]


def test_retriever_returns_empty_list_on_failure() -> None:
    retriever = RAGRetriever(
        embedder=BrokenEmbedder(),
        knowledge_repo=FakeKnowledgeRepository(),
        logs_repo=FakeLogsRepository(),
    )

    results = asyncio.run(retriever.retrieve("will fail"))
    assert results == []

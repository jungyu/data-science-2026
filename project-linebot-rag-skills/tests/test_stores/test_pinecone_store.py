"""PineconeStore 測試（mock index，不需 API key）。對應 task-24 步驟 9。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from app.storage.knowledge_store import KnowledgeChunkInsert, SearchFilters
from app.storage.stores.pinecone_store import PineconeStore


@dataclass
class _Match:
    id: str
    score: float
    metadata: dict


@dataclass
class _QueryResp:
    matches: list[_Match]


@dataclass
class MockPineconeIndex:
    upserts: list[list[dict]] = field(default_factory=list)
    deletes: list[dict] = field(default_factory=list)
    last_query: dict = field(default_factory=dict)
    healthy: bool = True

    def query(self, *, vector, top_k, include_metadata, filter):
        self.last_query = {"vector": vector, "top_k": top_k, "filter": filter}
        return _QueryResp(matches=[
            _Match(
                id="a",
                score=0.85,
                metadata={"content": "alpha", "category": "general", "tags": []},
            ),
        ])

    def upsert(self, *, vectors):
        self.upserts.append(list(vectors))

    def delete(self, *, filter):
        self.deletes.append(filter)

    def describe_index_stats(self):
        if not self.healthy:
            raise RuntimeError("down")
        return {"namespaces": {}}


@pytest.mark.asyncio
async def test_search_returns_chunks():
    idx = MockPineconeIndex()
    store = PineconeStore(index=idx)
    results = await store.search(
        query_embedding=[0.1, 0.2],
        filters=SearchFilters(categories=["general"]),
        top_k=3,
    )
    assert results[0].id == "a"
    assert results[0].combined_score == 0.85
    # filter 已轉成 Pinecone 語法
    assert idx.last_query["filter"] == {"category": {"$in": ["general"]}}


@pytest.mark.asyncio
async def test_search_no_filter_when_no_categories():
    idx = MockPineconeIndex()
    store = PineconeStore(index=idx)
    await store.search(query_embedding=[0.1, 0.2], top_k=3)
    assert idx.last_query["filter"] is None


@pytest.mark.asyncio
async def test_upsert_serializes_vectors():
    idx = MockPineconeIndex()
    store = PineconeStore(index=idx)

    n = await store.upsert([
        KnowledgeChunkInsert(
            id="x1", content="hello", category="g", embedding=[0.1, 0.2],
            content_hash="h1", title="T", tags=["a"],
            metadata={"k": "v"}, source_id="s1",
        ),
    ])
    assert n == 1
    pushed = idx.upserts[0][0]
    assert pushed["id"] == "x1"
    assert pushed["values"] == [0.1, 0.2]
    assert pushed["metadata"]["content"] == "hello"
    assert pushed["metadata"]["source_id"] == "s1"
    assert pushed["metadata"]["k"] == "v"


@pytest.mark.asyncio
async def test_delete_uses_metadata_filter():
    idx = MockPineconeIndex()
    store = PineconeStore(index=idx)
    await store.delete_by_source("s1")
    assert idx.deletes == [{"source_id": "s1"}]


@pytest.mark.asyncio
async def test_health_check_passes():
    store = PineconeStore(index=MockPineconeIndex())
    assert await store.health_check() is True


@pytest.mark.asyncio
async def test_health_check_fails():
    store = PineconeStore(index=MockPineconeIndex(healthy=False))
    assert await store.health_check() is False

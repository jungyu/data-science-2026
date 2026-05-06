"""SupabaseStore 測試（mock client）。對應 task-24 步驟 9。"""

from __future__ import annotations

import pytest

from app.rag.schemas import KnowledgeChunk
from app.storage.knowledge_store import KnowledgeChunkInsert, SearchFilters
from app.storage.stores.supabase_store import SupabaseStore


class MockSupabaseClient:
    def __init__(self) -> None:
        self.upsert_calls: list[tuple[str, list[dict], dict]] = []
        self.select_calls = 0

    async def upsert(self, table, rows, *, on_conflict=None):
        self.upsert_calls.append((table, list(rows), {"on_conflict": on_conflict}))

    async def select(self, table, params=None):
        self.select_calls += 1
        return []


class MockRepo:
    def __init__(self) -> None:
        self.search_calls: list[dict] = []

    async def match_private_knowledge(
        self, *, query_embedding, query_text, categories=None, top_k=8,
        vector_weight=1.0, keyword_weight=0.0
    ):
        self.search_calls.append({
            "query_embedding": query_embedding,
            "query_text": query_text,
            "categories": categories,
            "top_k": top_k,
            "vector_weight": vector_weight,
            "keyword_weight": keyword_weight,
        })
        return [
            KnowledgeChunk(id="a", content="x", category="general", combined_score=0.8),
        ]


@pytest.mark.asyncio
async def test_search_delegates_to_repo():
    client = MockSupabaseClient()
    repo = MockRepo()
    store = SupabaseStore(client=client, repo=repo)

    results = await store.search(
        query_embedding=[0.1, 0.2],
        query_text="hello",
        filters=SearchFilters(categories=["x"]),
        top_k=5,
    )
    assert results[0].id == "a"
    assert repo.search_calls[0]["categories"] == ["x"]
    assert repo.search_calls[0]["top_k"] == 5


@pytest.mark.asyncio
async def test_upsert_drops_id_field():
    client = MockSupabaseClient()
    store = SupabaseStore(client=client, repo=MockRepo())

    n = await store.upsert([
        KnowledgeChunkInsert(
            id="my-id-not-uuid",
            content="x",
            category="g",
            embedding=[0.1, 0.2],
            content_hash="h1",
        ),
    ])
    assert n == 1
    table, rows, opts = client.upsert_calls[0]
    assert table == "private_knowledge"
    assert opts["on_conflict"] == "content_hash"
    # id 應被剝除（讓 Supabase auto-gen UUID）
    assert "id" not in rows[0]
    assert rows[0]["content"] == "x"


@pytest.mark.asyncio
async def test_health_check_passes():
    store = SupabaseStore(client=MockSupabaseClient(), repo=MockRepo())
    assert await store.health_check() is True


@pytest.mark.asyncio
async def test_health_check_fails_on_exception():
    class BrokenClient:
        async def select(self, *a, **k):
            raise RuntimeError("down")
        async def upsert(self, *a, **k):
            pass

    store = SupabaseStore(client=BrokenClient(), repo=MockRepo())
    assert await store.health_check() is False

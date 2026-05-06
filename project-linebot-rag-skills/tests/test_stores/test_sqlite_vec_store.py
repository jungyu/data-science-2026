"""SqliteVecStore 真實 round-trip 測試（無雲端依賴）。對應 task-24 步驟 9。"""

from __future__ import annotations

import pytest

from app.storage.knowledge_store import KnowledgeChunkInsert, SearchFilters
from app.storage.stores.sqlite_vec_store import SqliteVecStore


def _insert(id: str, content: str, category: str, embedding: list[float], **meta) -> KnowledgeChunkInsert:
    return KnowledgeChunkInsert(
        id=id, content=content, category=category,
        embedding=embedding,
        content_hash=f"h_{id}",
        title=meta.pop("title", None),
        tags=meta.pop("tags", []),
        metadata=meta,
        source_id=f"src_{id}",
    )


@pytest.mark.asyncio
async def test_roundtrip_upsert_and_search(tmp_path):
    store = SqliteVecStore(path=str(tmp_path / "test.db"), dim=3)
    await store.upsert([
        _insert("a", "alpha content", "general", [0.1, 0.2, 0.3]),
        _insert("b", "beta content", "general", [0.5, 0.5, 0.5]),
    ])

    results = await store.search(
        query_embedding=[0.1, 0.2, 0.3], top_k=5
    )
    assert len(results) == 2
    # a 與查詢向量重合 → 排第一
    assert results[0].id == "a"
    assert results[0].vector_score > results[1].vector_score


@pytest.mark.asyncio
async def test_category_filter(tmp_path):
    store = SqliteVecStore(path=str(tmp_path / "test.db"), dim=3)
    await store.upsert([
        _insert("a", "x", "alpha", [0.1, 0.2, 0.3]),
        _insert("b", "x", "beta", [0.1, 0.2, 0.3]),
    ])

    results = await store.search(
        query_embedding=[0.1, 0.2, 0.3],
        filters=SearchFilters(categories=["beta"]),
        top_k=5,
    )
    assert len(results) == 1
    assert results[0].id == "b"


@pytest.mark.asyncio
async def test_upsert_replaces_existing(tmp_path):
    store = SqliteVecStore(path=str(tmp_path / "test.db"), dim=3)
    await store.upsert([_insert("a", "v1", "general", [0.1, 0.2, 0.3])])
    await store.upsert([_insert("a", "v2", "general", [0.1, 0.2, 0.3])])

    results = await store.search(query_embedding=[0.1, 0.2, 0.3], top_k=5)
    assert len(results) == 1
    assert results[0].content == "v2"


@pytest.mark.asyncio
async def test_delete_by_source(tmp_path):
    store = SqliteVecStore(path=str(tmp_path / "test.db"), dim=3)
    await store.upsert([
        _insert("a1", "x", "g", [0.1, 0.2, 0.3]),
        _insert("a2", "x", "g", [0.4, 0.4, 0.4]),
    ])

    deleted = await store.delete_by_source("src_a1")
    assert deleted == 1

    results = await store.search(query_embedding=[0.1, 0.2, 0.3], top_k=5)
    ids = {r.id for r in results}
    assert "a1" not in ids
    assert "a2" in ids


@pytest.mark.asyncio
async def test_metadata_round_trip(tmp_path):
    store = SqliteVecStore(path=str(tmp_path / "test.db"), dim=3)
    await store.upsert([
        _insert("a", "x", "g", [0.1, 0.2, 0.3], page_number=42, source_url="https://x"),
    ])

    results = await store.search(query_embedding=[0.1, 0.2, 0.3], top_k=5)
    assert results[0].metadata["page_number"] == 42
    assert results[0].metadata["source_url"] == "https://x"


@pytest.mark.asyncio
async def test_health_check(tmp_path):
    store = SqliteVecStore(path=str(tmp_path / "test.db"), dim=3)
    assert await store.health_check() is True


@pytest.mark.asyncio
async def test_search_returns_at_most_top_k(tmp_path):
    store = SqliteVecStore(path=str(tmp_path / "test.db"), dim=3)
    await store.upsert(
        [_insert(f"c{i}", "x", "g", [0.1 * i, 0.0, 0.0]) for i in range(10)]
    )
    results = await store.search(query_embedding=[0.1, 0.0, 0.0], top_k=3)
    assert len(results) == 3


@pytest.mark.asyncio
async def test_source_hash_returns_none_when_not_present(tmp_path):
    store = SqliteVecStore(path=str(tmp_path / "test.db"), dim=3)
    assert await store.source_hash("nonexistent") is None


@pytest.mark.asyncio
async def test_source_hash_returns_hash_after_upsert(tmp_path):
    store = SqliteVecStore(path=str(tmp_path / "test.db"), dim=3)
    chunk = _insert("x", "content", "general", [0.1, 0.2, 0.3])
    await store.upsert([chunk])
    result = await store.source_hash("src_x")
    assert result == "h_x"

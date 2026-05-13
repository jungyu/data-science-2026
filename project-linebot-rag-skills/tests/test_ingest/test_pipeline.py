"""IngestionPipeline 測試 — 用 stub ingester / embedder / store。對應 task-25 步驟 11。"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import AsyncIterator

import pytest

from app.ingest.document import Document, DocumentSection
from app.ingest.pipeline import IngestionPipeline


class _StubEmbedder:
    async def embed_query(self, text: str) -> list[float]:
        # 用文字長度作 fake embedding 第一維，方便 assert
        return [float(len(text)), 0.0, 0.0]


class _StubStore:
    def __init__(self, *, stored_hash: str | None = None) -> None:
        self.upserts: list[list] = []
        self._stored_hash = stored_hash

    async def source_hash(self, source_id: str) -> str | None:
        return self._stored_hash

    async def upsert(self, chunks) -> int:
        self.upserts.append(list(chunks))
        return len(chunks)


class _StubIngester:
    name = "stub"

    def __init__(self, docs: list[Document]) -> None:
        self._docs = docs

    def required_settings(self) -> list[str]:
        return []

    async def yield_documents(self) -> AsyncIterator[Document]:
        for d in self._docs:
            yield d


def _doc(*, source_type: str = "markdown", sections: list[DocumentSection] | None = None) -> Document:
    return Document(
        source_id="doc-1",
        source_type=source_type,
        title="Title",
        sections=sections or [DocumentSection(text="hello world")],
        fetched_at=datetime.now(timezone.utc),
        content_hash="h1",
        category="general",
        source_url="https://example.com/1",
    )


@pytest.mark.asyncio
async def test_pipeline_chunks_embeds_upserts():
    store = _StubStore()
    pipeline = IngestionPipeline(embedder=_StubEmbedder(), store=store)
    stats = await pipeline.run(_StubIngester([_doc()]))
    assert stats.docs == 1
    assert stats.chunks == 1
    inserts = store.upserts[0]
    assert inserts[0].id.startswith("doc-1#")
    # source_url 應流到 metadata
    assert inserts[0].metadata["source_url"] == "https://example.com/1"


@pytest.mark.asyncio
async def test_pipeline_pdf_path_carries_page_number():
    store = _StubStore()
    sections = [
        DocumentSection(text="page 1 text", page_number=1),
        DocumentSection(text="page 42 text about advanced topic", page_number=42),
    ]
    pipeline = IngestionPipeline(embedder=_StubEmbedder(), store=store)
    await pipeline.run(_StubIngester([_doc(source_type="pdf", sections=sections)]))

    metas = [c.metadata for c in store.upserts[0]]
    assert any(m["page_number"] == 1 for m in metas)
    assert any(m["page_number"] == 42 for m in metas)


@pytest.mark.asyncio
async def test_pipeline_skips_empty_documents():
    store = _StubStore()
    empty_doc = _doc(sections=[DocumentSection(text="")])
    pipeline = IngestionPipeline(embedder=_StubEmbedder(), store=store)
    stats = await pipeline.run(_StubIngester([empty_doc]))
    assert stats.docs == 0
    assert stats.skipped == 1
    assert store.upserts == []


@pytest.mark.asyncio
async def test_pipeline_uses_per_source_chunker():
    """CSV 用 NoOpChunker（不切），長文本仍只產 1 chunk。"""
    store = _StubStore()
    long_csv_row = "question: " + "x" * 3000
    pipeline = IngestionPipeline(embedder=_StubEmbedder(), store=store)
    await pipeline.run(
        _StubIngester([_doc(source_type="csv", sections=[DocumentSection(text=long_csv_row)])])
    )
    assert len(store.upserts[0]) == 1


@pytest.mark.asyncio
async def test_pipeline_section_path_carried():
    store = _StubStore()
    sections = [
        DocumentSection(
            text="content",
            section_path=["第 3 章", "3.2 節"],
        ),
    ]
    pipeline = IngestionPipeline(embedder=_StubEmbedder(), store=store)
    await pipeline.run(_StubIngester([_doc(sections=sections)]))
    assert store.upserts[0][0].metadata["section_path"] == ["第 3 章", "3.2 節"]


# ── 增量跳過 ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_pipeline_unchanged_skip_when_hash_matches():
    """store 已有相同 content_hash → unchanged+1，不呼叫 upsert。"""
    store = _StubStore(stored_hash="h1")   # h1 == _doc() 的 content_hash
    pipeline = IngestionPipeline(embedder=_StubEmbedder(), store=store)
    stats = await pipeline.run(_StubIngester([_doc()]))
    assert stats.unchanged == 1
    assert stats.docs == 0
    assert store.upserts == []


@pytest.mark.asyncio
async def test_pipeline_reingest_when_hash_differs():
    """store 裡的 hash 與 doc 不同（內容更新）→ 照常 embed + upsert。"""
    store = _StubStore(stored_hash="old-hash")   # != "h1"
    pipeline = IngestionPipeline(embedder=_StubEmbedder(), store=store)
    stats = await pipeline.run(_StubIngester([_doc()]))
    assert stats.docs == 1
    assert stats.unchanged == 0
    assert store.upserts != []


@pytest.mark.asyncio
async def test_pipeline_first_ingest_when_not_in_store():
    """store 回 None（從未 ingest）→ 照常處理。"""
    store = _StubStore(stored_hash=None)
    pipeline = IngestionPipeline(embedder=_StubEmbedder(), store=store)
    stats = await pipeline.run(_StubIngester([_doc()]))
    assert stats.docs == 1
    assert stats.unchanged == 0


# ── spec-06 knowledge_version ────────────────────────────────────────────────


class _VersionedStubStore(_StubStore):
    """支援 next_knowledge_version 的 stub；測 pipeline 是否會把版本印到 chunk 上。"""

    def __init__(self, *, stored_hash: str | None = None, next_version: int = 7) -> None:
        super().__init__(stored_hash=stored_hash)
        self._next_version = next_version

    async def next_knowledge_version(self) -> int:
        return self._next_version


@pytest.mark.asyncio
async def test_pipeline_stamps_knowledge_version_when_store_supports_it():
    """spec-06：store 有 next_knowledge_version 時，所有 chunk 都用同一版號。"""
    store = _VersionedStubStore(next_version=7)
    pipeline = IngestionPipeline(embedder=_StubEmbedder(), store=store)
    await pipeline.run(_StubIngester([_doc()]))
    assert all(c.knowledge_version == 7 for c in store.upserts[0])


@pytest.mark.asyncio
async def test_pipeline_falls_back_when_store_lacks_versioning():
    """store 沒實作 next_knowledge_version → chunk.knowledge_version=None
    （insert 走 schema 預設值，sqlite_vec / pinecone 也不會炸）。"""
    store = _StubStore()
    pipeline = IngestionPipeline(embedder=_StubEmbedder(), store=store)
    await pipeline.run(_StubIngester([_doc()]))
    assert all(c.knowledge_version is None for c in store.upserts[0])


@pytest.mark.asyncio
async def test_pipeline_continues_when_next_knowledge_version_raises():
    """store.next_knowledge_version 失敗時降級為 None，pipeline 不打斷。"""

    class _BrokenStore(_StubStore):
        async def next_knowledge_version(self) -> int:
            raise RuntimeError("boom")

    store = _BrokenStore()
    pipeline = IngestionPipeline(embedder=_StubEmbedder(), store=store)
    stats = await pipeline.run(_StubIngester([_doc()]))
    assert stats.docs == 1
    assert all(c.knowledge_version is None for c in store.upserts[0])

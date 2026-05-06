"""Per-source chunker 測試。對應 task-25 步驟 8。"""

from __future__ import annotations

from app.ingest.chunkers import (
    DEFAULT_CHUNKERS,
    MarkdownHeadingChunker,
    NoOpChunker,
    PageBoundaryChunker,
    chunker_for,
)


def test_no_op_chunker_returns_single_chunk():
    assert NoOpChunker().chunk("hello world") == ["hello world"]


def test_no_op_chunker_handles_empty():
    assert NoOpChunker().chunk("") == []
    assert NoOpChunker().chunk("   ") == []


def test_markdown_chunker_splits_long_text():
    text = "段" * 3000
    chunks = MarkdownHeadingChunker(max_chars=500).chunk(text)
    assert len(chunks) >= 5
    assert all(len(c) <= 500 for c in chunks)


def test_page_boundary_keeps_short_pages():
    """page 短時不切。"""
    chunks = PageBoundaryChunker(max_chars=2400).chunk("一個短頁面內容")
    assert chunks == ["一個短頁面內容"]


def test_page_boundary_splits_long_pages():
    text = "段" * 5000
    chunks = PageBoundaryChunker(max_chars=2000).chunk(text)
    assert len(chunks) >= 2
    assert all(len(c) <= 2000 for c in chunks)


def test_chunker_for_dispatches_by_source_type():
    assert isinstance(chunker_for("csv"), NoOpChunker)
    assert isinstance(chunker_for("pdf"), PageBoundaryChunker)
    assert isinstance(chunker_for("markdown"), MarkdownHeadingChunker)
    assert isinstance(chunker_for("web"), MarkdownHeadingChunker)


def test_chunker_for_unknown_falls_back_to_markdown():
    assert isinstance(chunker_for("unknown_source"), MarkdownHeadingChunker)


def test_default_chunkers_registry_complete():
    """spec-25 §「Per-source chunkers」表格中所有 source 都有預設。"""
    expected = {"markdown", "web", "notion", "pdf", "csv", "docx", "manual"}
    assert expected.issubset(DEFAULT_CHUNKERS.keys())

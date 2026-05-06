"""對應 task-25 步驟 13：Citation source 帶 page_number / section_path。"""

from __future__ import annotations

from app.generator.contract import _source_from_chunk
from app.rag.schemas import KnowledgeChunk


def _chunk(**meta) -> KnowledgeChunk:
    return KnowledgeChunk(
        id="c1",
        title="Title",
        content="x",
        category="general",
        metadata=meta,
        combined_score=0.7,
    )


def test_source_uses_metadata_url():
    src = _source_from_chunk(_chunk(source_url="https://example.com/1"))
    assert src == "https://example.com/1"


def test_source_appends_page_number():
    src = _source_from_chunk(_chunk(source_url="https://x", page_number=42))
    assert src == "https://x (p.42)"


def test_source_appends_section_path():
    src = _source_from_chunk(_chunk(
        source_url="https://x",
        section_path=["第 3 章", "3.2 節"],
    ))
    assert src == "https://x (第 3 章 > 3.2 節)"


def test_source_combines_page_and_section():
    src = _source_from_chunk(_chunk(
        source_url="https://x",
        page_number=42,
        section_path=["第 3 章", "3.2 節"],
    ))
    assert src == "https://x (p.42, 第 3 章 > 3.2 節)"


def test_source_falls_back_to_title():
    src = _source_from_chunk(_chunk())
    assert src == "Title"


def test_source_with_title_and_page_number():
    src = _source_from_chunk(_chunk(page_number=10))
    assert src == "Title (p.10)"


def test_source_without_url_or_title():
    chunk = KnowledgeChunk(id="c1", content="x", category="rag")
    assert _source_from_chunk(chunk) == "rag"

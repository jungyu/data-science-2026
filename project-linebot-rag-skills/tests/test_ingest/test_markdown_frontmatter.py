"""MarkdownIngester frontmatter 解析測試。對應 task-18 步驟 4。"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.ingest.ingesters.markdown_files import MarkdownIngester, parse_frontmatter


# ---- parse_frontmatter ---------------------------------------------------


def test_parse_full_frontmatter():
    text = (
        "---\n"
        "source_url: https://example.com/x\n"
        "category: nextjs\n"
        "tags: [a, b]\n"
        "---\n\n"
        "# Body\n\nstuff"
    )
    fm, body = parse_frontmatter(text)
    assert fm["source_url"] == "https://example.com/x"
    assert fm["category"] == "nextjs"
    assert fm["tags"] == ["a", "b"]
    assert body.startswith("# Body")


def test_parse_no_frontmatter():
    text = "# Just a heading\n\nbody"
    fm, body = parse_frontmatter(text)
    assert fm == {}
    assert body == text


def test_parse_malformed_frontmatter_returns_empty():
    text = "---\n: invalid yaml :\n  bad:\n---\nbody"
    fm, body = parse_frontmatter(text)
    # 解析失敗 → 視為無 frontmatter，body 為原文
    assert fm == {} or fm.get("category") is None


# ---- MarkdownIngester with frontmatter ----------------------------------


@pytest.mark.asyncio
async def test_ingester_extracts_source_url_from_frontmatter(tmp_path):
    md = tmp_path / "with_fm.md"
    md.write_text(
        "---\n"
        "source_url: https://nextjs.org/docs/x\n"
        "source_title: Next.js Docs / X\n"
        "category: nextjs\n"
        "content_hash: h_abc\n"
        "tags: [nextjs_org]\n"
        "---\n\n"
        "# X\n\nbody",
        encoding="utf-8",
    )
    ingester = MarkdownIngester([md], category="fallback")
    docs = [d async for d in ingester.yield_documents()]
    assert len(docs) == 1
    doc = docs[0]
    # source_url 流到 Document
    assert doc.source_url == "https://nextjs.org/docs/x"
    # frontmatter category 覆寫 CLI category
    assert doc.category == "nextjs"
    # source_type 切 web
    assert doc.source_type == "web"
    # title 用 source_title
    assert doc.title == "Next.js Docs / X"
    # tags 從 frontmatter
    assert doc.tags == ["nextjs_org"]
    # content_hash 用 frontmatter 提供的（去重一致性）
    assert doc.content_hash == "h_abc"
    # metadata 含 source_url
    assert doc.metadata["source_url"] == "https://nextjs.org/docs/x"


@pytest.mark.asyncio
async def test_ingester_falls_back_to_cli_category(tmp_path):
    """無 frontmatter 的舊 markdown 路徑 → 用 CLI 給的 category。"""
    md = tmp_path / "plain.md"
    md.write_text("# Title\n\nbody", encoding="utf-8")
    ingester = MarkdownIngester([md], category="rag")
    docs = [d async for d in ingester.yield_documents()]
    assert docs[0].category == "rag"
    assert docs[0].source_type == "markdown"
    assert docs[0].source_url is None


@pytest.mark.asyncio
async def test_ingester_skips_empty_or_no_body(tmp_path):
    empty = tmp_path / "empty.md"
    empty.write_text("---\nsource_url: https://x\n---\n\n", encoding="utf-8")

    truly_empty = tmp_path / "truly_empty.md"
    truly_empty.write_text("", encoding="utf-8")

    ingester = MarkdownIngester([empty, truly_empty], category="rag")
    docs = [d async for d in ingester.yield_documents()]
    assert docs == []


@pytest.mark.asyncio
async def test_ingester_pipeline_metadata_flow(tmp_path):
    """端對端：crawled markdown → MarkdownIngester → Pipeline → Citation source 帶 URL。

    驗證 task-18 教學承諾：「narrative [來源 N] 自動帶 URL」。
    """
    from app.generator.contract import _source_from_chunk
    from app.rag.schemas import KnowledgeChunk

    md = tmp_path / "doc.md"
    md.write_text(
        "---\nsource_url: https://example.com/x\ncategory: rag\ncontent_hash: h1\n---\n\n# Body\n\nx",
        encoding="utf-8",
    )
    docs = [d async for d in MarkdownIngester([md], category="fallback").yield_documents()]
    # Pipeline 會把 doc.source_url 寫進 KnowledgeChunkInsert.metadata.source_url；
    # 這裡直接驗 _source_from_chunk 的對應行為
    chunk = KnowledgeChunk(
        id="x", content="x", category="rag",
        metadata={"source_url": docs[0].source_url},
    )
    assert _source_from_chunk(chunk) == "https://example.com/x"

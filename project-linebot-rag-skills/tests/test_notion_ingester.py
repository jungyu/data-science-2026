"""spec-25 §「Notion ingester 設計」驗收：

1. database_id → 列出多 page → 每個 page 一份 Document
2. heading block 結構 → section_path
3. last_edited_time → content_hash；同一 page 重跑回相同 hash
4. 一般 paragraph / list 都應流入 section.text
"""

from __future__ import annotations

from typing import Any

import pytest

from app.ingest.ingesters.notion import NotionIngester


class _FakeNotionClient:
    """模擬 notion-client AsyncClient 的最小介面。

    建構時餵 (page metadata, page blocks) 對應表；不打真 API。
    """

    def __init__(
        self,
        *,
        pages: list[dict[str, Any]],
        blocks_by_page: dict[str, list[dict[str, Any]]],
    ) -> None:
        self._pages = pages
        self._blocks = blocks_by_page

        # 提供 client.databases / pages / blocks 的命名空間
        outer = self

        class _Databases:
            async def query(self, *, database_id, start_cursor=None):
                return {"results": outer._pages, "has_more": False}

        class _Pages:
            async def retrieve(self, *, page_id):
                for p in outer._pages:
                    if p["id"] == page_id:
                        return p
                raise KeyError(page_id)

        class _BlocksChildren:
            async def list(self, *, block_id, start_cursor=None):
                return {
                    "results": outer._blocks.get(block_id, []),
                    "has_more": False,
                }

        class _Blocks:
            def __init__(self) -> None:
                self.children = _BlocksChildren()

        self.databases = _Databases()
        self.pages = _Pages()
        self.blocks = _Blocks()


def _heading(level: int, text: str) -> dict:
    return {
        "type": f"heading_{level}",
        f"heading_{level}": {"rich_text": [{"plain_text": text}]},
    }


def _para(text: str) -> dict:
    return {
        "type": "paragraph",
        "paragraph": {"rich_text": [{"plain_text": text}]},
    }


def _bullet(text: str) -> dict:
    return {
        "type": "bulleted_list_item",
        "bulleted_list_item": {"rich_text": [{"plain_text": text}]},
    }


def _title_page(page_id: str, title: str, last_edited: str) -> dict:
    return {
        "id": page_id,
        "url": f"https://notion.so/{page_id}",
        "last_edited_time": last_edited,
        "properties": {
            "Name": {
                "type": "title",
                "title": [{"plain_text": title}],
            }
        },
    }


@pytest.mark.asyncio
async def test_database_query_yields_one_doc_per_page():
    pages = [
        _title_page("p1", "First Page", "2026-05-01T00:00:00Z"),
        _title_page("p2", "Second Page", "2026-05-02T00:00:00Z"),
    ]
    blocks = {
        "p1": [_para("hello from p1")],
        "p2": [_para("hello from p2")],
    }
    client = _FakeNotionClient(pages=pages, blocks_by_page=blocks)
    ing = NotionIngester(
        api_key="dummy",
        database_id="db",
        category="company-wiki",
        client=client,
    )

    docs = [d async for d in ing.yield_documents()]
    assert len(docs) == 2
    assert {d.source_id for d in docs} == {"p1", "p2"}
    assert {d.title for d in docs} == {"First Page", "Second Page"}
    for d in docs:
        assert d.category == "company-wiki"
        assert d.source_type == "notion"


@pytest.mark.asyncio
async def test_headings_become_section_path():
    """spec-25：heading_1/2 結構應流入 section_path。"""
    pages = [_title_page("p1", "Doc", "2026-05-01T00:00:00Z")]
    blocks = {
        "p1": [
            _heading(1, "Chapter 1"),
            _para("intro to chapter 1"),
            _heading(2, "Section 1.1"),
            _bullet("bullet under 1.1"),
            _para("more text under 1.1"),
            _heading(1, "Chapter 2"),
            _para("intro to chapter 2"),
        ],
    }
    client = _FakeNotionClient(pages=pages, blocks_by_page=blocks)
    ing = NotionIngester(
        api_key="x", database_id="db", category="wiki", client=client
    )
    docs = [d async for d in ing.yield_documents()]
    assert len(docs) == 1
    sections = docs[0].sections
    paths = [s.section_path for s in sections]
    # 3 段內容對應 3 個 section_path 狀態
    assert paths == [
        ["Chapter 1"],
        ["Chapter 1", "Section 1.1"],
        ["Chapter 2"],
    ]
    # heading_1 重新進入時要截掉 Section 1.1
    texts = [s.text for s in sections]
    assert "bullet under 1.1" in texts[1]
    assert "more text under 1.1" in texts[1]
    assert texts[2] == "intro to chapter 2"


@pytest.mark.asyncio
async def test_content_hash_stable_for_same_last_edited():
    """spec-25 §「last_edited_time」：同 page 同 last_edited → hash 穩定，
    供 IngestionPipeline 增量略過。"""
    pages = [_title_page("p1", "Doc", "2026-05-01T00:00:00Z")]
    blocks = {"p1": [_para("body")]}
    client = _FakeNotionClient(pages=pages, blocks_by_page=blocks)
    ing = NotionIngester(api_key="x", database_id="db", category="c", client=client)
    docs_1 = [d async for d in ing.yield_documents()]
    docs_2 = [d async for d in ing.yield_documents()]
    assert docs_1[0].content_hash == docs_2[0].content_hash
    # last_edited 改變後 hash 也變
    pages[0]["last_edited_time"] = "2026-05-99T00:00:00Z"
    docs_3 = [d async for d in ing.yield_documents()]
    assert docs_3[0].content_hash != docs_1[0].content_hash


@pytest.mark.asyncio
async def test_page_id_path_retrieves_single_page():
    """page_id 模式（非 database）走 pages.retrieve。"""
    pages = [_title_page("p1", "Single", "2026-05-01T00:00:00Z")]
    blocks = {"p1": [_para("solo")]}
    client = _FakeNotionClient(pages=pages, blocks_by_page=blocks)
    ing = NotionIngester(
        api_key="x", page_id="p1", category="c", client=client
    )
    docs = [d async for d in ing.yield_documents()]
    assert len(docs) == 1
    assert docs[0].source_id == "p1"


@pytest.mark.asyncio
async def test_empty_page_returns_no_document():
    """全空 page（heading 但沒內容）不產 Document。"""
    pages = [_title_page("p1", "Empty", "2026-05-01T00:00:00Z")]
    blocks = {"p1": []}
    client = _FakeNotionClient(pages=pages, blocks_by_page=blocks)
    ing = NotionIngester(
        api_key="x", database_id="db", category="c", client=client
    )
    docs = [d async for d in ing.yield_documents()]
    assert docs == []


def test_constructor_requires_database_or_page_id():
    with pytest.raises(ValueError, match="database_id or page_id"):
        NotionIngester(api_key="x", category="c")


# ── paginate（has_more=True 邊界）─────────────────────────────────────────────


class _PaginatingDatabaseClient:
    """每次 query 回固定 batch 大小，依 start_cursor 切；模擬 Notion 真實 paginate。"""

    def __init__(self, all_pages: list[dict], batch_size: int = 1) -> None:
        self._all = all_pages
        self._batch = batch_size
        self.query_calls = 0
        outer = self

        class _Databases:
            async def query(self, *, database_id, start_cursor=None):
                outer.query_calls += 1
                start = int(start_cursor) if start_cursor else 0
                end = start + outer._batch
                batch = outer._all[start:end]
                has_more = end < len(outer._all)
                return {
                    "results": batch,
                    "has_more": has_more,
                    "next_cursor": str(end) if has_more else None,
                }

        class _Pages:
            async def retrieve(self, *, page_id):
                raise NotImplementedError

        class _BlocksChildren:
            async def list(self, *, block_id, start_cursor=None):
                return {"results": [_para(f"body {block_id}")], "has_more": False}

        class _Blocks:
            def __init__(self) -> None:
                self.children = _BlocksChildren()

        self.databases = _Databases()
        self.pages = _Pages()
        self.blocks = _Blocks()


@pytest.mark.asyncio
async def test_database_paginates_until_has_more_false():
    """spec-25：has_more=True 時用 next_cursor 連續查；驗收 yield 出全部 page。"""
    pages = [
        _title_page(f"p{i}", f"Page {i}", "2026-05-01T00:00:00Z")
        for i in range(5)
    ]
    client = _PaginatingDatabaseClient(pages, batch_size=2)
    ing = NotionIngester(
        api_key="x", database_id="db", category="c", client=client
    )
    docs = [d async for d in ing.yield_documents()]
    # 5 pages、batch=2 → 3 次 query（2 + 2 + 1，第 3 次 has_more=False）
    assert client.query_calls == 3
    assert {d.source_id for d in docs} == {f"p{i}" for i in range(5)}

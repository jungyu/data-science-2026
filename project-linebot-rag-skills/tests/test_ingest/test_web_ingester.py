"""WebIngester 單元測試 — mock Playwright，不打真實網路。

測試要點：
1. html_to_markdown 純函式（selector 路徑 + readability fallback）
2. content_hash_of / url_to_filename 純函式
3. is_allowed_by_robots（allow / disallow 兩分支）
4. WebIngester.yield_documents：mock fetch_html，驗證 Document 結構
5. robots.txt 封鎖時跳過、html 為空時跳過
"""

from __future__ import annotations

import asyncio
import sys
from datetime import timezone
from typing import AsyncIterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ingest.document import Document
from app.ingest.ingesters.web import (
    WebIngester,
    content_hash_of,
    html_to_markdown,
    is_allowed_by_robots,
    url_to_filename,
)


# ── 純函式 ──────────────────────────────────────────────────────────────────


def test_content_hash_of_is_16_hex_chars():
    h = content_hash_of("<html>hello</html>")
    assert len(h) == 16
    assert all(c in "0123456789abcdef" for c in h)


def test_content_hash_of_deterministic():
    html = "<p>same content</p>"
    assert content_hash_of(html) == content_hash_of(html)


def test_url_to_filename_basic():
    name = url_to_filename("https://nextjs.org/docs/routing/introduction")
    assert name.endswith(".md")
    assert "nextjs" in name
    assert "/" not in name


def test_url_to_filename_truncates_long_url():
    long_url = "https://example.com/" + "a" * 300
    assert len(url_to_filename(long_url)) <= 200


def test_html_to_markdown_readability_fallback():
    html = "<html><body><article><p>Hello World</p></article></body></html>"
    rule = {"main_selector": None, "remove_selectors": [], "wait_selector": None}
    result = html_to_markdown(html, rule=rule)
    assert "Hello World" in result


def test_html_to_markdown_with_selector():
    html = (
        "<html><body>"
        "<nav>Nav</nav>"
        "<main><article><p>Main content</p></article></main>"
        "</body></html>"
    )
    rule = {"main_selector": "main article", "remove_selectors": ["nav"], "wait_selector": None}
    result = html_to_markdown(html, rule=rule)
    assert "Main content" in result
    assert "Nav" not in result


def test_html_to_markdown_selector_miss_falls_back():
    html = "<html><body><p>Fallback content</p></body></html>"
    rule = {"main_selector": "div.nonexistent", "remove_selectors": [], "wait_selector": None}
    result = html_to_markdown(html, rule=rule)
    assert "Fallback content" in result


def test_is_allowed_by_robots_allows_when_unreachable():
    rp_cache: dict = {}
    with patch("app.ingest.ingesters.web.robotparser.RobotFileParser") as MockRP:
        mock_rp = MagicMock()
        mock_rp.read.side_effect = Exception("network error")
        MockRP.return_value = mock_rp
        result = is_allowed_by_robots("https://example.com/page", rp_cache=rp_cache)
    assert result is True


def test_is_allowed_by_robots_respects_disallow():
    rp_cache: dict = {}
    with patch("app.ingest.ingesters.web.robotparser.RobotFileParser") as MockRP:
        mock_rp = MagicMock()
        mock_rp.read.return_value = None
        mock_rp.can_fetch.return_value = False
        MockRP.return_value = mock_rp
        result = is_allowed_by_robots("https://example.com/private", rp_cache=rp_cache)
    assert result is False


# ── WebIngester 整合 ──────────────────────────────────────────────────────


FAKE_HTML = "<html><body><article><p>測試內容</p></article></body></html>"
FAKE_TITLE = "測試頁面"


def _make_fake_ingester(urls: list[str] | None = None) -> WebIngester:
    return WebIngester(
        urls or ["https://example.com/test"],
        category="test",
        concurrency=1,
        delay=0.0,
        respect_robots=False,
    )


def _playwright_sys_mock(fake_pw_class):
    """Return a sys.modules patch dict that stubs out the playwright package."""
    async_api_stub = MagicMock()
    async_api_stub.async_playwright = fake_pw_class
    return {
        "playwright": MagicMock(),
        "playwright.async_api": async_api_stub,
    }


@pytest.mark.asyncio
async def test_web_ingester_yields_document():
    ingester = _make_fake_ingester()

    async def fake_fetch(browser, url, *, wait_selector):
        return FAKE_HTML, FAKE_TITLE

    class _FakeBrowser:
        async def close(self):
            pass

    class _FakePW:
        chromium = MagicMock()

        async def __aenter__(self):
            self.chromium.launch = AsyncMock(return_value=_FakeBrowser())
            return self

        async def __aexit__(self, *_):
            pass

    docs: list[Document] = []
    with patch.dict(sys.modules, _playwright_sys_mock(_FakePW)), \
         patch("app.ingest.ingesters.web.fetch_html", side_effect=fake_fetch), \
         patch("app.ingest.ingesters.web.asyncio.sleep", new_callable=AsyncMock):
        async for doc in ingester.yield_documents():
            docs.append(doc)

    assert len(docs) == 1
    doc = docs[0]
    assert doc.source_type == "web"
    assert doc.source_url == "https://example.com/test"
    assert doc.category == "test"
    assert "測試內容" in doc.sections[0].text
    assert doc.title == FAKE_TITLE
    assert doc.fetched_at.tzinfo == timezone.utc
    assert len(doc.content_hash) == 16


@pytest.mark.asyncio
async def test_web_ingester_skips_on_fetch_error():
    ingester = _make_fake_ingester()

    async def bad_fetch(browser, url, *, wait_selector):
        raise RuntimeError("network error")

    class _FakeBrowser:
        async def close(self):
            pass

    class _FakePW:
        chromium = MagicMock()

        async def __aenter__(self):
            self.chromium.launch = AsyncMock(return_value=_FakeBrowser())
            return self

        async def __aexit__(self, *_):
            pass

    docs: list[Document] = []
    with patch.dict(sys.modules, _playwright_sys_mock(_FakePW)), \
         patch("app.ingest.ingesters.web.fetch_html", side_effect=bad_fetch):
        async for doc in ingester.yield_documents():
            docs.append(doc)

    assert docs == []


@pytest.mark.asyncio
async def test_web_ingester_skips_robots_blocked():
    ingester = WebIngester(
        ["https://example.com/blocked"],
        category="test",
        delay=0.0,
        respect_robots=True,
    )

    class _FakeBrowser:
        async def close(self):
            pass

    class _FakePW:
        chromium = MagicMock()

        async def __aenter__(self):
            self.chromium.launch = AsyncMock(return_value=_FakeBrowser())
            return self

        async def __aexit__(self, *_):
            pass

    docs: list[Document] = []
    with patch.dict(sys.modules, _playwright_sys_mock(_FakePW)), \
         patch("app.ingest.ingesters.web.is_allowed_by_robots", return_value=False):
        async for doc in ingester.yield_documents():
            docs.append(doc)

    assert docs == []


def test_web_ingester_required_settings_is_empty():
    ingester = _make_fake_ingester()
    assert ingester.required_settings() == []


def test_web_ingester_name():
    assert WebIngester([], category="x").name == "web"

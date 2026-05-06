"""SupabaseArticleIngester 單元測試 — mock httpx，不打真實 Supabase。

測試要點：
1. 正常文章 → yield 正確的 Document 欄位
2. content_text 為空的列 → 跳過
3. category 為 None → 補預設值 "general"
4. since 參數 → 加到 query params
5. category 參數 → 加到 query params
6. content_hash 正確傳遞（pipeline 用來判斷是否跳過 embed）
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ingest.ingesters.supabase_articles import SupabaseArticleIngester


def _make_settings(
    supabase_url: str = "https://test.supabase.co",
    supabase_service_role_key: str = "test-key",
) -> MagicMock:
    s = MagicMock()
    s.supabase_url = supabase_url
    s.supabase_service_role_key = supabase_service_role_key
    return s


def _make_row(
    *,
    source_url: str = "https://example.com/article-1",
    title: str = "Test Article",
    content_text: str = "Hello world content",
    content_hash: str = "abc123",
    category: str | None = "nextjs",
    source_type: str = "web",
    meta: dict | None = None,
    created_at: str = "2026-05-01T00:00:00+00:00",
) -> dict:
    return {
        "source_url": source_url,
        "title": title,
        "content_text": content_text,
        "content_hash": content_hash,
        "category": category,
        "source_type": source_type,
        "meta": meta or {"tags": ["react", "nextjs"]},
        "created_at": created_at,
    }


def _mock_response(rows: list[dict]):
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json.return_value = rows
    return resp


# ── 主流程 ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_yields_document_with_correct_fields():
    row = _make_row()
    ingester = SupabaseArticleIngester(_make_settings())

    with patch("httpx.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=_mock_response([row])
        )
        docs = [doc async for doc in ingester.yield_documents()]

    assert len(docs) == 1
    doc = docs[0]
    assert doc.source_id == "https://example.com/article-1"
    assert doc.source_url == "https://example.com/article-1"
    assert doc.source_type == "web"
    assert doc.title == "Test Article"
    assert doc.content_hash == "abc123"
    assert doc.category == "nextjs"
    assert doc.tags == ["react", "nextjs"]
    assert doc.sections[0].text == "Hello world content"
    assert doc.fetched_at.tzinfo == timezone.utc


@pytest.mark.asyncio
async def test_skips_empty_content_text():
    rows = [
        _make_row(content_text=""),
        _make_row(content_text="   "),
        _make_row(content_text="valid content", source_url="https://example.com/2"),
    ]
    ingester = SupabaseArticleIngester(_make_settings())

    with patch("httpx.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=_mock_response(rows)
        )
        docs = [doc async for doc in ingester.yield_documents()]

    assert len(docs) == 1
    assert docs[0].source_url == "https://example.com/2"


@pytest.mark.asyncio
async def test_category_none_defaults_to_general():
    row = _make_row(category=None)
    ingester = SupabaseArticleIngester(_make_settings())

    with patch("httpx.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__.return_value.get = AsyncMock(
            return_value=_mock_response([row])
        )
        docs = [doc async for doc in ingester.yield_documents()]

    assert docs[0].category == "general"


# ── Query params ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_category_filter_added_to_params():
    ingester = SupabaseArticleIngester(_make_settings(), category="nextjs")
    captured_params: dict = {}

    async def fake_get(url, *, headers, params):
        captured_params.update(params)
        return _mock_response([])

    with patch("httpx.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__.return_value.get = AsyncMock(
            side_effect=fake_get
        )
        async for _ in ingester.yield_documents():
            pass

    assert captured_params.get("category") == "eq.nextjs"


@pytest.mark.asyncio
async def test_since_filter_added_to_params():
    since = datetime(2026, 5, 1, tzinfo=timezone.utc)
    ingester = SupabaseArticleIngester(_make_settings(), since=since)
    captured_params: dict = {}

    async def fake_get(url, *, headers, params):
        captured_params.update(params)
        return _mock_response([])

    with patch("httpx.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__.return_value.get = AsyncMock(
            side_effect=fake_get
        )
        async for _ in ingester.yield_documents():
            pass

    assert "created_at" in captured_params
    assert captured_params["created_at"].startswith("gte.")


@pytest.mark.asyncio
async def test_accept_profile_header_is_crawler():
    ingester = SupabaseArticleIngester(_make_settings())
    captured_headers: dict = {}

    async def fake_get(url, *, headers, params):
        captured_headers.update(headers)
        return _mock_response([])

    with patch("httpx.AsyncClient") as MockClient:
        MockClient.return_value.__aenter__.return_value.get = AsyncMock(
            side_effect=fake_get
        )
        async for _ in ingester.yield_documents():
            pass

    assert captured_headers.get("Accept-Profile") == "crawler"


# ── 其他 ─────────────────────────────────────────────────────────────────────

def test_name():
    ingester = SupabaseArticleIngester(_make_settings())
    assert ingester.name == "supabase_articles"


def test_required_settings():
    ingester = SupabaseArticleIngester(_make_settings())
    assert "supabase_url" in ingester.required_settings()
    assert "supabase_service_role_key" in ingester.required_settings()

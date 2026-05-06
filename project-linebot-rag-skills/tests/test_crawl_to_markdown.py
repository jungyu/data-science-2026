"""Crawler 純函式測試 — 不需 playwright / 網路。

對應 task-18 步驟 11。
"""

from __future__ import annotations

from pathlib import Path

import pytest


# 把 scripts/ 加進 sys.path 才能 import scripts.crawl_to_markdown
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.crawl_to_markdown import (  # noqa: E402
    content_hash_of,
    existing_hash,
    html_to_markdown,
    is_allowed_by_robots,
    make_frontmatter,
    url_to_filename,
)


# ---- url_to_filename -----------------------------------------------------


def test_url_to_filename_basic():
    assert url_to_filename("https://nextjs.org/docs/app/rendering") == \
        "nextjs_org__docs_app_rendering.md"


def test_url_to_filename_strips_www():
    assert url_to_filename("https://www.example.com/foo/bar") == \
        "example_com__foo_bar.md"


def test_url_to_filename_handles_root():
    assert url_to_filename("https://example.com/") == "example_com__index.md"


def test_url_to_filename_truncates_long():
    long_path = "/x" * 200
    fn = url_to_filename(f"https://example.com{long_path}")
    assert len(fn) <= 200


def test_url_to_filename_sanitizes_special_chars():
    fn = url_to_filename("https://example.com/path?q=1&x=2")
    # 檔名不含 ? = & 等不安全字元
    assert "?" not in fn
    assert "&" not in fn


# ---- html_to_markdown ----------------------------------------------------


def test_html_to_markdown_strips_nav_via_remove_selectors():
    html = (
        "<html><body>"
        "<main><article>"
        "  <nav class='sidebar'>nav links</nav>"
        "  <h1>Title</h1><p>Body content</p>"
        "</article></main></body></html>"
    )
    out = html_to_markdown(
        html,
        rule={
            "main_selector": "main article",
            "remove_selectors": ["nav", ".sidebar"],
        },
    )
    assert "nav" not in out.lower()
    assert "Title" in out
    assert "Body content" in out


def test_html_to_markdown_falls_back_to_readability():
    """Selector 找不到時走 readability fallback。"""
    html = "<html><body><article><h1>T</h1><p>x</p></article></body></html>"
    out = html_to_markdown(html, rule={"main_selector": "div.nonexistent"})
    # 仍應抽出 body 內容
    assert "x" in out


def test_html_to_markdown_no_selector_uses_readability():
    """Rule 無 main_selector → 走 readability。"""
    html = (
        "<html><body><article><h1>Hello</h1><p>World content</p></article></body></html>"
    )
    out = html_to_markdown(html, rule={"main_selector": None})
    assert "Hello" in out or "World content" in out


# ---- frontmatter ---------------------------------------------------------


def test_make_frontmatter_contains_required_fields():
    fm_text = make_frontmatter(
        url="https://example.com/x",
        title="Example",
        category="nextjs",
        content_hash="abc123",
    )
    assert fm_text.startswith("---\n")
    assert fm_text.endswith("---\n\n")
    assert "source_url: https://example.com/x" in fm_text
    assert "content_hash: abc123" in fm_text
    assert "category: nextjs" in fm_text
    assert "crawled_at:" in fm_text


def test_existing_hash_reads_from_file(tmp_path):
    path = tmp_path / "x.md"
    path.write_text(
        "---\nsource_url: https://x\ncontent_hash: h_abc\n---\n\nbody",
        encoding="utf-8",
    )
    assert existing_hash(path) == "h_abc"


def test_existing_hash_returns_none_for_missing():
    assert existing_hash(Path("/nonexistent/path.md")) is None


def test_existing_hash_returns_none_for_no_frontmatter(tmp_path):
    path = tmp_path / "x.md"
    path.write_text("# just a heading", encoding="utf-8")
    assert existing_hash(path) is None


# ---- content_hash --------------------------------------------------------


def test_content_hash_deterministic():
    assert content_hash_of("hello") == content_hash_of("hello")
    assert content_hash_of("hello") != content_hash_of("world")


def test_content_hash_length():
    h = content_hash_of("anything")
    assert len(h) == 16


# ---- robots.txt ----------------------------------------------------------


def test_robots_allows_when_unreachable():
    """robots.txt 抓不到 → 預設允許 + warning。"""
    rp_cache: dict = {}
    # 用不存在的 host 模擬 unreachable
    allowed = is_allowed_by_robots(
        "https://this-host-does-not-exist-xyz.example/foo",
        rp_cache=rp_cache,
    )
    assert allowed is True


def test_robots_caches_per_host():
    rp_cache: dict = {}
    is_allowed_by_robots("https://example.com/a", rp_cache=rp_cache)
    is_allowed_by_robots("https://example.com/b", rp_cache=rp_cache)
    # cache key 是 base URL；同 host 兩次 → 一筆 cache
    assert len(rp_cache) == 1

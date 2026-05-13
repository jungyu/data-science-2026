"""drone_data/03 — 從 OpenAlex API 直接擷取 drone 論文 metadata 寫入 articles。

取代 IEEE Xplore 搜尋頁的合規路徑：
    IEEE Xplore 的 ToS 禁止自動化爬取搜尋頁。OpenAlex 是 OurResearch 提供
    的免費學術 metadata 庫，涵蓋 IEEE / Elsevier / Springer 等出版社的論文
    （含 IEEE Xplore 收錄項），且：
      - 完全免費，無 API key（建議帶 mailto 進 polite pool）
      - 提供 cursor pagination，可處理大量結果
      - abstract 以 "inverted index" 格式回傳，需重建為文字

本範例對等於使用者原本想要的查詢：
    drone, 2020–2026, 比對 IEEE 出版品

與 Playwright pipeline 的差異：
    本腳本直接呼叫 REST API，**繞過 crawl_queue**，直接 upsert 到 articles。
    source.code = "openalex-drone"，source.crawler_url 紀錄查詢字串供追溯。

執行方式：
    python examples/drone_data/03_ingest_openalex.py
    python examples/drone_data/03_ingest_openalex.py --max-pages 5
    python examples/drone_data/03_ingest_openalex.py --year-from 2023

備註：
    OpenAlex 鼓勵在 User-Agent 帶 mailto；本腳本從環境變數
    OPENALEX_MAILTO 讀取（沒設定也能跑，但會被歸到 anonymous pool 較慢）。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from utils.db_types import (
    ArticleInsert,
    ArticleMeta,
    SourceConfig,
    SourceInsert,
    to_insert_dict,
)
from utils.supabase_client import get_crawler_table
from utils.time_helpers import now_iso

PROJECT_ID = os.getenv("PROJECT_ID", "demo-project")
OPENALEX_MAILTO = os.getenv("OPENALEX_MAILTO", "")

API_ROOT = "https://api.openalex.org/works"
DEFAULT_QUERY = "drone"
DEFAULT_YEAR_FROM = 2020
DEFAULT_YEAR_TO = 2026
DEFAULT_PER_PAGE = 25
DEFAULT_MAX_PAGES = 4   # 共 100 筆，避免一次拉太多


# ── source 設定 ───────────────────────────────────────────────────

OPENALEX_SOURCE = SourceInsert(
    project_id=PROJECT_ID,
    code="openalex-drone",
    name="OpenAlex — Drone Research",
    description="OpenAlex API 擷取 drone 主題、2020-2026 的學術 metadata（含 IEEE 收錄項）",
    base_url="https://openalex.org",
    domain="api.openalex.org",
    crawler_url=f"{API_ROOT}?search={DEFAULT_QUERY}",
    config=SourceConfig(),
    is_enabled=True,
    created_by="seed-script:drone_data",
)


# ── OpenAlex 工具 ─────────────────────────────────────────────────

def _build_url(
    query: str, year_from: int, year_to: int, per_page: int, cursor: str
) -> str:
    """組裝 OpenAlex /works 查詢 URL。"""
    params = {
        "search": query,
        "filter": f"publication_year:{year_from}-{year_to}",
        "per-page": str(per_page),
        "cursor": cursor,
    }
    if OPENALEX_MAILTO:
        params["mailto"] = OPENALEX_MAILTO
    return f"{API_ROOT}?{urllib.parse.urlencode(params)}"


def _fetch_page(url: str) -> dict[str, Any]:
    """以 stdlib 對 OpenAlex 發 GET；回傳 JSON。"""
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "project-playwright/drone_data (educational)"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _rebuild_abstract(inverted_index: dict[str, list[int]] | None) -> str | None:
    """OpenAlex 的 abstract 以「字 → 位置列表」的 inverted index 儲存。

    例如：{"hello": [0], "world": [1]} → "hello world"
    """
    if not inverted_index:
        return None
    position_to_word: dict[int, str] = {}
    for word, positions in inverted_index.items():
        for pos in positions:
            position_to_word[pos] = word
    if not position_to_word:
        return None
    return " ".join(
        position_to_word[i] for i in sorted(position_to_word)
    )


def _work_to_article(work: dict[str, Any], source_id: str) -> ArticleInsert:
    """將 OpenAlex Work 轉換為 ArticleInsert。"""
    title = (work.get("title") or "").strip() or "(untitled)"
    doi = work.get("doi")
    source_url = doi or work.get("id") or ""

    abstract = _rebuild_abstract(work.get("abstract_inverted_index"))

    # 第一作者
    authorships = work.get("authorships") or []
    first_author = (
        authorships[0].get("author", {}).get("display_name")
        if authorships
        else None
    )

    venue = (work.get("primary_location") or {}).get("source") or {}
    publisher = venue.get("host_organization_name") or venue.get("display_name")

    raw_hash = hashlib.sha256(
        f"{work.get('id', '')}|{title}|{work.get('updated_date', '')}".encode()
    ).hexdigest()

    return ArticleInsert(
        project_id=PROJECT_ID,
        source_id=source_id,
        title=title[:500],
        source_url=source_url,
        external_id=work.get("id"),
        author_name=first_author,
        abstract=abstract,
        published_at=work.get("publication_date"),
        canonical_url=doi,
        lang=work.get("language"),
        meta=ArticleMeta(
            categories=[c["display_name"] for c in (work.get("concepts") or [])[:5]],
            keywords=(work.get("keywords") or [])[:10],
            source_labels=[publisher] if publisher else [],
            extra={
                "cited_by_count": work.get("cited_by_count"),
                "type": work.get("type"),
                "open_access": (work.get("open_access") or {}).get("oa_status"),
            },
        ),
        is_published=True,
        is_available=bool(source_url),
        content_hash=raw_hash,
    )


# ── pipeline 主體 ─────────────────────────────────────────────────

def seed_source() -> dict:
    payload = to_insert_dict(OPENALEX_SOURCE)
    result = (
        get_crawler_table("sources")
        .upsert(payload, on_conflict="project_id,code")
        .execute()
    )
    return result.data[0]


def ingest(
    source_id: str, query: str, year_from: int, year_to: int, max_pages: int
) -> tuple[int, int]:
    """逐頁拉取 OpenAlex；每頁 upsert articles，回傳 (inserted, total_fetched)。"""
    inserted = 0
    total = 0
    cursor = "*"  # OpenAlex cursor pagination 起始符

    for page_idx in range(1, max_pages + 1):
        url = _build_url(query, year_from, year_to, DEFAULT_PER_PAGE, cursor)
        print(f"[fetch] page {page_idx}: {url}")
        body = _fetch_page(url)

        results = body.get("results") or []
        if not results:
            print("  → 無更多結果，提前結束")
            break
        total += len(results)

        rows = [to_insert_dict(_work_to_article(w, source_id)) for w in results]
        if rows:
            result = (
                get_crawler_table("articles")
                .upsert(rows, on_conflict="source_id,source_url")
                .execute()
            )
            inserted += len(result.data or [])
            print(f"  → upsert {len(result.data or [])} 筆")

        cursor = (body.get("meta") or {}).get("next_cursor") or ""
        if not cursor:
            print("  → cursor 用盡，結束")
            break

    return inserted, total


def main() -> None:
    parser = argparse.ArgumentParser(description="OpenAlex drone metadata ingest")
    parser.add_argument("--query", default=DEFAULT_QUERY)
    parser.add_argument("--year-from", type=int, default=DEFAULT_YEAR_FROM)
    parser.add_argument("--year-to", type=int, default=DEFAULT_YEAR_TO)
    parser.add_argument("--max-pages", type=int, default=DEFAULT_MAX_PAGES)
    args = parser.parse_args()

    print("=" * 60)
    print("drone_data/03 — 從 OpenAlex API 擷取 drone 論文")
    print("=" * 60)
    print(f"  project_id : {PROJECT_ID}")
    print(f"  query      : {args.query!r}")
    print(f"  year_range : {args.year_from}-{args.year_to}")
    print(f"  max_pages  : {args.max_pages}（每頁 {DEFAULT_PER_PAGE} 筆）")
    print(f"  mailto     : {OPENALEX_MAILTO or '(unset — anonymous pool)'}")
    print()

    source = seed_source()
    print(f"[OK] source 已 upsert：{source['id']}")
    print()

    inserted, total = ingest(
        source_id=source["id"],
        query=args.query,
        year_from=args.year_from,
        year_to=args.year_to,
        max_pages=args.max_pages,
    )

    print()
    print("─" * 60)
    print(f"完成：抓取 {total} 筆 → upsert {inserted} 筆 articles")
    print(f"完成時間：{now_iso()}")
    print()
    print("下一步：")
    print("  python ch09-rag-bridge/04_end_to_end_demo.py")


if __name__ == "__main__":
    main()

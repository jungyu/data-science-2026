"""drone_data/04 — 從 IEEE Xplore Metadata Search API 擷取 drone 論文。

這是合規版本：使用 IEEE 官方提供的 Metadata Search API，而非爬取
ieeexplore.ieee.org/search 搜尋頁（後者違反 ToS）。

申請流程：
    1. 至 https://developer.ieee.org/getting_started 註冊
    2. 取得 24 字元 API key
    3. status=waiting 期間呼叫會 401/403，通常 1-2 工作天 activate
    4. 在 .env 填入：IEEE_XPLORE_API_KEY=...

API 文件：
    https://developer.ieee.org/docs/read/Metadata_API_responses
    免費額度通常為每日 200 requests / 每次最多 200 筆 / start_record 分頁

執行方式：
    python examples/drone_data/04_ingest_ieee_xplore.py
    python examples/drone_data/04_ingest_ieee_xplore.py --query "swarm robotics"
    python examples/drone_data/04_ingest_ieee_xplore.py --max-pages 2 --per-page 50

與 03_ingest_openalex.py 的差異：
    - 03 OpenAlex：免費、無 key、覆蓋所有出版社（含 IEEE）
    - 04 IEEE Xplore：官方權威來源、author affiliation 較準、可拿到 PDF link
    兩者可互補：03 抓全面，04 補 IEEE 高精度欄位
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
from urllib.error import HTTPError

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
IEEE_API_KEY = os.getenv("IEEE_XPLORE_API_KEY", "")

API_ROOT = "https://ieeexploreapi.ieee.org/api/v1/search/articles"
DEFAULT_QUERY = "drone"
DEFAULT_YEAR_FROM = 2020
DEFAULT_YEAR_TO = 2026
DEFAULT_PER_PAGE = 25  # IEEE API max 200，預設保守值
DEFAULT_MAX_PAGES = 4

# ── source 設定 ───────────────────────────────────────────────────

IEEE_XPLORE_SOURCE = SourceInsert(
    project_id=PROJECT_ID,
    code="ieee-xplore-drone",
    name="IEEE Xplore — Drone Research",
    description="IEEE Xplore Metadata Search API 擷取 drone 主題 2020-2026 論文",
    base_url="https://ieeexplore.ieee.org",
    domain="ieeexploreapi.ieee.org",
    crawler_url=f"{API_ROOT}?querytext={DEFAULT_QUERY}",
    config=SourceConfig(),
    is_enabled=True,
    created_by="seed-script:drone_data",
)


# ── IEEE Xplore 工具 ──────────────────────────────────────────────

def _build_url(
    query: str,
    year_from: int,
    year_to: int,
    per_page: int,
    start_record: int,
) -> str:
    """組裝 IEEE Xplore /search/articles 查詢 URL。"""
    params = {
        "apikey": IEEE_API_KEY,
        "format": "json",
        "querytext": query,
        "start_year": str(year_from),
        "end_year": str(year_to),
        "max_records": str(per_page),
        "start_record": str(start_record),
    }
    return f"{API_ROOT}?{urllib.parse.urlencode(params)}"


def _fetch_page(url: str) -> dict[str, Any]:
    """以 stdlib 對 IEEE Xplore 發 GET；回傳 JSON。

    Raises:
        SystemExit: 401/403（API key 未生效）/ 429（rate limit）等狀態碼，
                    給出明確錯誤訊息後退出。
    """
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "project-playwright/drone_data (educational)"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:300]
        if e.code in (401, 403):
            sys.exit(
                f"\n[401/403] IEEE API 拒絕（{e.reason}）。\n"
                f"  常見原因：\n"
                f"    1. API key 仍為 'waiting' 狀態，未 activate\n"
                f"    2. 每日 quota 用盡\n"
                f"    3. .env 中 IEEE_XPLORE_API_KEY 未設定\n"
                f"  回應：{body}"
            )
        if e.code == 429:
            sys.exit(f"\n[429] Rate limit 觸發，請稍後重試。回應：{body}")
        raise


def _normalize_authors(authors: dict[str, Any] | None) -> tuple[str | None, list[str]]:
    """IEEE API 的 authors 結構：{ "authors": [ { "full_name": "..." }, ... ] }

    回傳 (first_author, all_author_list)。
    """
    if not authors:
        return None, []
    items = authors.get("authors") or []
    names = [a.get("full_name", "").strip() for a in items if a.get("full_name")]
    first = names[0] if names else None
    return first, names


def _article_to_insert(art: dict[str, Any], source_id: str) -> ArticleInsert:
    """將 IEEE Xplore article record 轉成 ArticleInsert。"""
    title = (art.get("title") or "").strip() or "(untitled)"
    doi = art.get("doi")
    article_number = art.get("article_number")

    # IEEE 提供穩定的 abstract URL；若無則 fallback 到 DOI / API id
    source_url = (
        art.get("abstract_url")
        or (f"https://doi.org/{doi}" if doi else "")
        or (f"https://ieeexplore.ieee.org/document/{article_number}" if article_number else "")
        or ""
    )

    first_author, all_authors = _normalize_authors(art.get("authors"))

    # IEEE 提供 publication_year / publication_date 兩種；optional
    published_at = art.get("publication_date") or (
        f"{art['publication_year']}-01-01"
        if art.get("publication_year")
        else None
    )

    content_hash = hashlib.sha256(
        f"{article_number or ''}|{title}|{art.get('insert_date', '')}".encode()
    ).hexdigest()

    index_terms = art.get("index_terms") or {}
    ieee_terms = (index_terms.get("ieee_terms") or {}).get("terms") or []
    author_terms = (index_terms.get("author_terms") or {}).get("terms") or []

    return ArticleInsert(
        project_id=PROJECT_ID,
        source_id=source_id,
        title=title[:500],
        source_url=source_url,
        external_id=str(article_number) if article_number else None,
        author_name=first_author,
        abstract=art.get("abstract") or None,
        published_at=published_at,
        canonical_url=doi,
        lang="en",  # IEEE 文獻幾乎都是英文
        meta=ArticleMeta(
            categories=ieee_terms[:5],
            tags=author_terms[:10],
            section=art.get("publication_title"),  # 期刊 / 會議名稱
            byline_raw=", ".join(all_authors[:5]) if all_authors else None,
            source_labels=["IEEE"],
            extra={
                "content_type": art.get("content_type"),  # Conferences / Journals 等
                "publisher": art.get("publisher"),
                "is_number": art.get("is_number"),
                "citing_paper_count": art.get("citing_paper_count"),
                "pdf_url": art.get("pdf_url"),
            },
        ),
        is_published=True,
        is_available=bool(source_url),
        content_hash=content_hash,
    )


# ── pipeline 主體 ─────────────────────────────────────────────────

def seed_source() -> dict:
    payload = to_insert_dict(IEEE_XPLORE_SOURCE)
    result = (
        get_crawler_table("sources")
        .upsert(payload, on_conflict="project_id,code")
        .execute()
    )
    return result.data[0]


def ingest(
    source_id: str,
    query: str,
    year_from: int,
    year_to: int,
    per_page: int,
    max_pages: int,
) -> tuple[int, int]:
    """逐頁拉 IEEE Xplore；每頁 upsert articles，回傳 (inserted, total_fetched)。"""
    inserted = 0
    total = 0
    start_record = 1  # IEEE 使用 1-based pagination

    for page_idx in range(1, max_pages + 1):
        url = _build_url(query, year_from, year_to, per_page, start_record)
        # 印出 URL 時遮蔽 apikey，避免被誤貼到日誌
        safe_url = url.replace(IEEE_API_KEY, "***") if IEEE_API_KEY else url
        print(f"[fetch] page {page_idx} (start_record={start_record}): {safe_url}")

        body = _fetch_page(url)
        articles = body.get("articles") or []
        total_records = body.get("total_records", 0)
        if not articles:
            print("  → 無更多結果，提前結束")
            break
        total += len(articles)

        rows = [
            to_insert_dict(_article_to_insert(a, source_id)) for a in articles
        ]
        result = (
            get_crawler_table("articles")
            .upsert(rows, on_conflict="source_id,source_url")
            .execute()
        )
        inserted += len(result.data or [])
        print(
            f"  → upsert {len(result.data or [])} 筆"
            f"（API 回報 total_records={total_records}）"
        )

        start_record += per_page
        if start_record > total_records:
            print("  → 已抓完 total_records 範圍")
            break

    return inserted, total


def main() -> None:
    parser = argparse.ArgumentParser(description="IEEE Xplore drone metadata ingest")
    parser.add_argument("--query", default=DEFAULT_QUERY)
    parser.add_argument("--year-from", type=int, default=DEFAULT_YEAR_FROM)
    parser.add_argument("--year-to", type=int, default=DEFAULT_YEAR_TO)
    parser.add_argument("--per-page", type=int, default=DEFAULT_PER_PAGE,
                        help="每頁筆數，IEEE 上限 200")
    parser.add_argument("--max-pages", type=int, default=DEFAULT_MAX_PAGES)
    args = parser.parse_args()

    if not IEEE_API_KEY:
        sys.exit(
            "[ERR] 環境變數 IEEE_XPLORE_API_KEY 未設定。\n"
            "      請至 https://developer.ieee.org/getting_started 申請後填入 .env"
        )

    print("=" * 60)
    print("drone_data/04 — 從 IEEE Xplore API 擷取 drone 論文")
    print("=" * 60)
    print(f"  project_id : {PROJECT_ID}")
    print(f"  query      : {args.query!r}")
    print(f"  year_range : {args.year_from}-{args.year_to}")
    print(f"  per_page   : {args.per_page}")
    print(f"  max_pages  : {args.max_pages}")
    print(f"  api_key    : ***{IEEE_API_KEY[-4:]}（後 4 碼）")
    print()

    source = seed_source()
    print(f"[OK] source 已 upsert：{source['id']}")
    print()

    inserted, total = ingest(
        source_id=source["id"],
        query=args.query,
        year_from=args.year_from,
        year_to=args.year_to,
        per_page=args.per_page,
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

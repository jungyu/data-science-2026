"""drone_data/02 — 將 IEEE Robotics & Automation Society (IEEE RAS) 接入 pipeline。

IEEE RAS（https://www.ieee-ras.org/）是 IEEE 機器人與自動化學會的官方網站，
公開頁面以新聞 / 出版 / 活動為主。本範例聚焦 publications/conferences 列表
與單篇活動頁。

合規備註：
    本腳本僅爬取「對所有訪客公開」的頁面（不需登入），User-Agent 標示為
    Mozilla/5.0 真實瀏覽器；如要在生產環境長期運行，請額外檢查站點
    robots.txt 與 ToS。

已知限制（2025-05 實測）：
    IEEE RAS 站點受 Cloudflare 保護，常見反爬機制：
      - 對自動化 User-Agent 直接回 challenge 頁面（cf-cookie-error）
      - 對短時間多次請求啟動 JS challenge
    Playwright 真實瀏覽器有機會通過 challenge，但**首次連線常被擋**，
    導致 `Schema-based list extracted 0 URLs`。若你看到此狀況：
      1. 把 User-Agent 換成更接近真實瀏覽器（含 sec-ch-ua headers）
      2. 用 ch06 學到的 stealth mode（utils/worker/browser_pool 加 init_script）
      3. 或者放棄這站，改用 PX4 / OpenAlex 等友善來源
    這正是 ch10 想教的「真實爬蟲一半時間在跟反爬鬥」的教學重點。

執行方式：
    python examples/drone_data/02_seed_ieee_ras.py

下一步：
    python -m utils.worker.main
    python ch09-rag-bridge/04_end_to_end_demo.py --category robotics
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from utils.crawl_queue import insert_new_pending_jobs
from utils.db_types import (
    ArticleExtractorSchema,
    CrawlPageType,
    CrawlQueueInsert,
    CrawlQueuePayload,
    ExtractorSchema,
    FieldMapping,
    ListExtractorSchema,
    SourceConfig,
    SourceInsert,
    to_insert_dict,
)
from utils.supabase_client import get_crawler_table

PROJECT_ID = os.getenv("PROJECT_ID", "demo-project")


# ── IEEE RAS source 設定 ──────────────────────────────────────────
#
# 站點是傳統的 WordPress / 靜態 HTML 混合架構：
#   - 列表頁通常用 .post-list / .news-list / <article> 包覆每筆
#   - 內文容器多半在 .entry-content / article main
#   - 學會本身內容更新頻率不高，schedule 設每週一次
#
IEEE_RAS_SOURCE = SourceInsert(
    project_id=PROJECT_ID,
    code="ieee-ras",
    name="IEEE Robotics & Automation Society",
    description="IEEE 機器人與自動化學會官方網站，公告與會議資訊",
    base_url="https://www.ieee-ras.org",
    domain="www.ieee-ras.org",
    crawler_url="https://www.ieee-ras.org/publications",
    config=SourceConfig(
        user_agent=(
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        wait_until="domcontentloaded",
        timeout_ms=20_000,
        block_resources=["image", "font", "media", "stylesheet"],
    ),
    extractor_schema=ExtractorSchema(
        list=ListExtractorSchema(
            # WordPress 常見的內容區包覆元素
            item_selector="article, .post, .views-row",
            link_selector="h2 a, h3 a, .field-content > a",
            title_selector="h2 a, h3 a",
        ),
        article=ArticleExtractorSchema(
            title_selector="h1.entry-title, h1.page-title, article h1",
            author_selector=".byline .author, .entry-author",
            published_at_selector="time[datetime], .entry-date",
            content_selector=".entry-content, article .content, main article",
            remove_selectors=[
                ".sharedaddy",       # 社群分享按鈕
                ".jp-relatedposts",  # 相關文章區塊
                ".comments-area",
                "nav",
                "footer",
            ],
        ),
    ),
    field_mapping=FieldMapping(
        title="title",
        author_name="author_name",
        published_at="published_at",
        content_text="content_text",
    ),
    is_enabled=True,
    schedule_cron="0 6 * * 1",  # 每週一 06:00 UTC
    created_by="seed-script:drone_data",
)


SEED_URLS: list[dict] = [
    {
        "url": "https://www.ieee-ras.org/publications",
        "page_type": CrawlPageType.LIST,
        "priority": 200,
        "payload": CrawlQueuePayload(discovered_from="seed", depth=0),
    },
    {
        "url": "https://www.ieee-ras.org/conferences-workshops",
        "page_type": CrawlPageType.LIST,
        "priority": 180,
        "payload": CrawlQueuePayload(discovered_from="seed", depth=0),
    },
    {
        "url": "https://www.ieee-ras.org/educational-resources-outreach",
        "page_type": CrawlPageType.LIST,
        "priority": 150,
        "payload": CrawlQueuePayload(discovered_from="seed", depth=0),
    },
]


def seed_source() -> dict:
    payload = to_insert_dict(IEEE_RAS_SOURCE)
    result = (
        get_crawler_table("sources")
        .upsert(payload, on_conflict="project_id,code")
        .execute()
    )
    return result.data[0]


def enqueue_seeds(source_id: str) -> tuple[int, int]:
    payloads = [
        to_insert_dict(
            CrawlQueueInsert(
                project_id=PROJECT_ID,
                source_id=source_id,
                url=item["url"],
                page_type=item["page_type"],
                priority=item["priority"],
                payload=item["payload"],
            )
        )
        for item in SEED_URLS
    ]
    return insert_new_pending_jobs(source_id, payloads)


def main() -> None:
    print("=" * 60)
    print("drone_data/02 — 將 IEEE RAS 接入 crawler pipeline")
    print("=" * 60)
    print(f"  project_id : {PROJECT_ID}")
    print(f"  code       : {IEEE_RAS_SOURCE.code}")
    print(f"  crawler_url: {IEEE_RAS_SOURCE.crawler_url}")
    print()

    source = seed_source()
    print(f"[OK] source 已 upsert：{source['id']}")

    enqueued, skipped = enqueue_seeds(source["id"])
    print(f"[OK] crawl_queue：新增 {enqueued} 筆，已存在略過 {skipped} 筆")
    print()
    print("─" * 60)
    print("下一步：")
    print("  1. python -m utils.worker.main          # 啟動爬蟲 worker")
    print("  2. python ch09-rag-bridge/04_end_to_end_demo.py")


if __name__ == "__main__":
    main()

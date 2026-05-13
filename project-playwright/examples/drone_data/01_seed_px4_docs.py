"""drone_data/01 — 將 PX4 開源無人機文件站接入 crawler pipeline。

PX4（https://docs.px4.io/main/en/）是開源無人機自駕儀的官方文件站，
採 Docusaurus 架構、CC-BY 授權，適合作為「結構穩定、可放心爬取」的
教學樣本。

本腳本做兩件事：
    1. 在 crawler.sources 寫入（upsert）PX4 source 設定，
       extractor_schema 採用 schema-driven 設定（無需自訂 Python）
    2. 在 crawler.crawl_queue 排入首頁 + 3 個入門頁面作為種子 URL

執行方式：
    python examples/drone_data/01_seed_px4_docs.py

下一步：
    python -m utils.worker.main          # 啟動 async worker 開始爬取
    python ch09-rag-bridge/04_end_to_end_demo.py  # 驗收 articles 是否寫入
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

# ── PX4 source 設定 ────────────────────────────────────────────────
#
# Docusaurus 結構特徵：
#   - 左側 sidebar 連結用 .menu__link，整站導覽都靠它
#   - 內文容器是 <article class="markdown">
#   - 沒有傳統的「下一頁」分頁，靠 sidebar 結構發現所有頁面
#
PX4_SOURCE = SourceInsert(
    project_id=PROJECT_ID,
    code="px4-docs",
    name="PX4 Autopilot Docs",
    description="開源無人機自駕儀 PX4 的官方文件站（Docusaurus、CC-BY 授權）",
    base_url="https://docs.px4.io",
    domain="docs.px4.io",
    crawler_url="https://docs.px4.io/main/en/",
    config=SourceConfig(
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        wait_until="domcontentloaded",
        timeout_ms=20_000,
        block_resources=["image", "font", "media"],
    ),
    extractor_schema=ExtractorSchema(
        list=ListExtractorSchema(
            # Docusaurus 側欄每個導覽連結
            item_selector="li.theme-doc-sidebar-item-link",
            link_selector="a.menu__link",
            title_selector="a.menu__link",
        ),
        article=ArticleExtractorSchema(
            title_selector="h1",
            content_selector="article.markdown",
            # 移除「上一頁/下一頁」、TOC、編輯連結等噪音
            remove_selectors=[
                ".theme-edit-this-page",
                ".theme-doc-toc-mobile",
                ".pagination-nav",
                ".theme-doc-footer",
            ],
        ),
    ),
    field_mapping=FieldMapping(
        title="title",
        content_text="content_text",
    ),
    is_enabled=True,
    schedule_cron="0 4 * * 0",  # 每週日 04:00 UTC 全量更新
    created_by="seed-script:drone_data",
)

# 種子 URL：首頁 + 幾個重點章節
SEED_URLS: list[dict] = [
    {
        "url": "https://docs.px4.io/main/en/",
        "page_type": CrawlPageType.LIST,
        "priority": 200,
        "payload": CrawlQueuePayload(discovered_from="seed", depth=0),
    },
    {
        "url": "https://docs.px4.io/main/en/getting_started/",
        "page_type": CrawlPageType.LIST,
        "priority": 180,
        "payload": CrawlQueuePayload(discovered_from="seed", depth=0),
    },
    {
        "url": "https://docs.px4.io/main/en/flight_modes/",
        "page_type": CrawlPageType.LIST,
        "priority": 180,
        "payload": CrawlQueuePayload(discovered_from="seed", depth=0),
    },
    {
        "url": "https://docs.px4.io/main/en/airframes/",
        "page_type": CrawlPageType.LIST,
        "priority": 180,
        "payload": CrawlQueuePayload(discovered_from="seed", depth=0),
    },
]


def seed_source() -> dict:
    """Upsert PX4 source 設定，依 (project_id, code) 去重。"""
    payload = to_insert_dict(PX4_SOURCE)
    result = (
        get_crawler_table("sources")
        .upsert(payload, on_conflict="project_id,code")
        .execute()
    )
    return result.data[0]


def enqueue_seeds(source_id: str) -> tuple[int, int]:
    """將 SEED_URLS 插入 crawl_queue；已 pending 的會被略過。"""
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
    print("drone_data/01 — 將 PX4 docs 接入 crawler pipeline")
    print("=" * 60)
    print(f"  project_id : {PROJECT_ID}")
    print(f"  code       : {PX4_SOURCE.code}")
    print(f"  crawler_url: {PX4_SOURCE.crawler_url}")
    print()

    source = seed_source()
    print(f"[OK] source 已 upsert：{source['id']}")

    enqueued, skipped = enqueue_seeds(source["id"])
    print(f"[OK] crawl_queue：新增 {enqueued} 筆，已存在略過 {skipped} 筆")
    print()
    print("─" * 60)
    print("下一步：")
    print("  1. python -m utils.worker.main          # 啟動爬蟲 worker")
    print("  2. python ch09-rag-bridge/04_end_to_end_demo.py  # 驗收落地")


if __name__ == "__main__":
    main()

"""
Ch08-03 — 將種子 URL 塞入 crawler.crawl_queue。

crawl_queue 是整個 pipeline 的任務調度核心：
  - Worker 透過 lease_next_crawl_job() 從這裡「搶單」
  - Partial unique index 確保同一 source+url 不重複排入（pending 狀態下）
  - priority 欄位控制執行順序（高優先先跑）

執行方式：
    python ch08-supabase/03_enqueue_urls.py

    # 或指定 source code（需已在 sources 表中存在）
    python ch08-supabase/03_enqueue_urls.py --source hacker-news
"""

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.crawl_queue import insert_new_pending_jobs
from utils.db_types import (
    CrawlPageType,
    CrawlQueueInsert,
    CrawlQueuePayload,
    to_insert_dict,
)
from utils.supabase_client import get_crawler_table

PROJECT_ID = os.getenv("PROJECT_ID", "demo-project")

# ── Hacker News 種子 URL ──────────────────────────────────────────

HN_SEED_URLS = [
    {
        "url": "https://news.ycombinator.com/",
        "page_type": CrawlPageType.LIST,
        "priority": 200,          # 列表頁優先度最高
        "payload": CrawlQueuePayload(
            discovered_from="seed",
            topic="homepage",
            depth=0,
        ),
    },
    {
        "url": "https://news.ycombinator.com/?p=2",
        "page_type": CrawlPageType.LIST,
        "priority": 150,
        "payload": CrawlQueuePayload(
            discovered_from="seed",
            topic="homepage",
            depth=1,
        ),
    },
]


def get_source_id(source_code: str) -> str:
    """從 crawler.sources 取得 source_id。"""
    result = (
        get_crawler_table("sources")
        .select("id, name")
        .eq("project_id", PROJECT_ID)
        .eq("code", source_code)
        .single()
        .execute()
    )
    if not result.data:
        raise ValueError(
            f"找不到 source code='{source_code}'（project_id='{PROJECT_ID}'）\n"
            "請先執行 02_seed_source.py 建立來源設定。"
        )
    return result.data["id"], result.data["name"]


def enqueue_urls(source_id: str, seed_jobs: list[dict]) -> tuple[int, int]:
    """將種子 URL 批次寫入 crawl_queue。

    使用 ignoreDuplicates=True 搭配 partial unique index：
        uq_crawl_queue_pending_source_url（source_id, url WHERE status='pending'）
    相同的 source+url 在 pending 狀態下只會存在一筆，重複執行不會產生重複任務。

    Returns:
        (enqueued_count, skipped_count)
    """
    payloads = [
        to_insert_dict(
            CrawlQueueInsert(
                project_id=PROJECT_ID,
                source_id=source_id,
                url=job["url"],
                page_type=job["page_type"],
                priority=job.get("priority", 100),
                payload=job.get("payload", CrawlQueuePayload()),
            )
        )
        for job in seed_jobs
    ]
    return insert_new_pending_jobs(source_id, payloads)


def show_queue_stats(source_id: str) -> None:
    """印出目前佇列各狀態的數量。"""
    result = (
        get_crawler_table("crawl_queue")
        .select("status", count="exact")
        .eq("source_id", source_id)
        .execute()
    )

    # 用 group 計算各狀態數量
    from collections import Counter
    all_rows = (
        get_crawler_table("crawl_queue")
        .select("status")
        .eq("source_id", source_id)
        .execute()
    )
    counts = Counter(row["status"] for row in (all_rows.data or []))

    print("\n  [佇列狀態]")
    for status in ["pending", "leased", "running", "done", "failed", "dead", "skipped"]:
        n = counts.get(status, 0)
        if n > 0:
            print(f"    {status:<10} {n} 筆")
    if not counts:
        print("    （空佇列）")


def main():
    parser = argparse.ArgumentParser(description="將種子 URL 塞入 crawl_queue")
    parser.add_argument("--source", default="hacker-news", help="source code（預設：hacker-news）")
    args = parser.parse_args()

    print("=" * 50)
    print("Ch08-03 — 塞入種子 URL")
    print("=" * 50)

    try:
        source_id, source_name = get_source_id(args.source)
    except ValueError as e:
        print(f"[NG] {e}")
        sys.exit(1)

    print(f"  source : {source_name}（{args.source}）")
    print(f"  id     : {source_id}")
    print(f"  URLs   : {len(HN_SEED_URLS)} 筆種子 URL")

    try:
        enqueued, skipped = enqueue_urls(source_id, HN_SEED_URLS)
        print(f"\n[OK] 寫入完成：新增 {enqueued} 筆，跳過重複 {skipped} 筆")
    except Exception as e:
        print(f"\n[NG] 寫入失敗：{e}")
        raise

    show_queue_stats(source_id)
    print("\n  -> 下一步：執行 04_single_job_worker.py 消費佇列任務")


if __name__ == "__main__":
    main()

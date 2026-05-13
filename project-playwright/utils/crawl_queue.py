"""crawl_queue 共用操作。

避免 ch08 各腳本內重複「先 select 看哪些 pending、再過濾後 insert」的模式。

設計備註：
    理想上應使用 ``upsert(..., on_conflict="source_id,url", ignore_duplicates=True)``，
    但 crawl_queue 的 unique 索引是 **partial unique index**
    （``uq_crawl_queue_pending_source_url WHERE status='pending'``），
    PostgREST 的 ON CONFLICT 無法指定 WHERE 條件，會在 server 端報
    "no unique or exclusion constraint matching the ON CONFLICT specification"。
    因此採用 select → 過濾 → insert 的兩段式做法。
"""

from __future__ import annotations

from utils.supabase_client import get_crawler_table


def insert_new_pending_jobs(
    source_id: str, payloads: list[dict]
) -> tuple[int, int]:
    """只插入此 source 目前 pending 佇列尚未存在的 URL。

    Args:
        source_id: crawler.sources.id
        payloads: 已序列化（to_insert_dict）的 crawl_queue 列字典，需含 "url"

    Returns:
        (inserted, skipped) — 實際插入筆數與被略過的重複筆數
    """
    if not payloads:
        return 0, 0

    existing = (
        get_crawler_table("crawl_queue")
        .select("url")
        .eq("source_id", source_id)
        .eq("status", "pending")
        .execute()
    )
    existing_urls = {row["url"] for row in (existing.data or [])}
    new_payloads = [p for p in payloads if p["url"] not in existing_urls]

    if new_payloads:
        get_crawler_table("crawl_queue").insert(new_payloads).execute()

    return len(new_payloads), len(payloads) - len(new_payloads)

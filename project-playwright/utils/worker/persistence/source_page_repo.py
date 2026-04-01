"""
SupabaseSourcePageRepo — SourcePageRepository Protocol 的 Supabase 實作。

職責：封裝 crawler.source_pages 表的 upsert 操作。
Upsert key：(source_id, url)，同一 URL 重抓時更新而非新增。
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from supabase import AsyncClient

from utils.db_types import CrawlPageType, SourcePageRow
from utils.worker.service_inputs import SaveFetchedPageInput

logger = logging.getLogger(__name__)


class SupabaseSourcePageRepo:
    """實作 SourcePageRepository protocol，對接 Supabase crawler.source_pages。"""

    def __init__(self, client: AsyncClient) -> None:
        self._client = client

    def _table(self):
        return self._client.schema("crawler").table("source_pages")

    async def upsert_page(self, input: SaveFetchedPageInput) -> SourcePageRow | None:
        """Upsert 頁面快照，回傳 SourcePageRow（含 DB 生成的 id）。

        Upsert key：source_id + url（見 crawler schema 的 unique constraint）。
        重複抓取相同 URL 時，更新 raw_html、fetched_at，不重複插入。
        """
        now = datetime.now(timezone.utc).isoformat()
        data: dict[str, Any] = {
            "project_id": input.project_id,
            "source_id": input.source_id,
            "url": input.url,
            "page_type": input.page_type.value,
            "title": input.title,
            "raw_html": input.raw_html,
            "http_status": input.http_status,
            "fetched_at": input.fetched_at or now,
            "last_seen_at": now,
        }
        if input.crawl_run_id:
            data["crawl_run_id"] = input.crawl_run_id
        if input.canonical_url:
            data["canonical_url"] = input.canonical_url
        if input.snapshot_json:
            from utils.db_types import to_insert_dict
            data["snapshot_json"] = to_insert_dict(input.snapshot_json)

        result = await self._table().upsert(
            data, on_conflict="source_id,url"
        ).execute()
        rows = result.data
        if not rows:
            return None

        row = rows[0]
        # 回傳 dict（PageRunner 只需要 row["id"]）
        return row  # type: ignore[return-value]

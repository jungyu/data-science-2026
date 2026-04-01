"""
SupabaseSourceRepo — SourceRepository Protocol 的 Supabase 實作。

職責：封裝 crawler.sources 表的讀取操作。
PageRunner 透過 find_by_id() 取得 source 設定（extractor_schema、config 等）。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from supabase import AsyncClient

from utils.db_types import SourceRow

logger = logging.getLogger(__name__)


class SupabaseSourceRepo:
    """實作 SourceRepository protocol，對接 Supabase crawler.sources。"""

    def __init__(self, client: AsyncClient) -> None:
        self._client = client

    def _table(self):
        return self._client.schema("crawler").table("sources")

    async def find_by_id(self, source_id: str) -> SourceRow | None:
        """依 id 查詢 source，找不到回傳 None。"""
        result = await self._table().select("*").eq("id", source_id).execute()
        rows = result.data
        if not rows:
            return None
        return _row_to_source(rows[0])

    async def find_by_code(self, code: str) -> SourceRow | None:
        """依 source code 查詢，找不到回傳 None。"""
        result = await self._table().select("*").eq("code", code).execute()
        rows = result.data
        if not rows:
            return None
        return _row_to_source(rows[0])

    async def list_enabled(self) -> list[SourceRow]:
        """取得所有 is_enabled=true 的 source。"""
        result = await self._table().select("*").eq("is_enabled", True).execute()
        return [_row_to_source(r) for r in (result.data or [])]


def _row_to_source(row: dict[str, Any]) -> SourceRow:
    """將 Supabase 回傳的 dict 轉換成 SourceRow dataclass。"""
    return SourceRow(
        id=row["id"],
        project_id=row["project_id"],
        code=row["code"],
        name=row["name"],
        description=row.get("description"),
        base_url=row.get("base_url"),
        domain=row.get("domain"),
        crawler_url=row.get("crawler_url"),
        config=row.get("config") or {},
        extractor_schema=row.get("extractor_schema") or {},
        field_mapping=row.get("field_mapping") or {},
        is_enabled=row.get("is_enabled", True),
        schedule_cron=row.get("schedule_cron"),
        last_run_at=row.get("last_run_at"),
        created_by=row.get("created_by"),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )

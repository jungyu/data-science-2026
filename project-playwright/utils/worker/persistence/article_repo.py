"""
SupabaseArticleRepo — ArticleRepository Protocol 的 Supabase 實作。

職責：封裝 crawler.articles 的 upsert 操作，包含兩道去重：
  1. Upsert key (source_id, source_url)：URL 相同就更新，不重複插入
  2. content_hash：hash 未變則跳過寫入（節省 DB 寫入）
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any

from supabase import AsyncClient

from utils.db_types import ArticleRow
from utils.worker.service_inputs import UpsertArticleInput

logger = logging.getLogger(__name__)


class SupabaseArticleRepo:
    """實作 ArticleRepository protocol，對接 Supabase crawler.articles。"""

    def __init__(self, client: AsyncClient) -> None:
        self._client = client

    def _table(self):
        return self._client.schema("crawler").table("articles")

    async def upsert_article(self, input: UpsertArticleInput) -> ArticleRow | None:
        """Upsert 文章，回傳更新後的 ArticleRow（dict 型式）。

        content_hash 去重：
          - 若呼叫端已提供 content_hash，直接使用
          - 否則以 content_text 計算 SHA-256
          - hash 與 DB 現有值相同時跳過寫入，回傳 None
        """
        draft = input.draft
        content_text = draft.content_text or ""

        # 決定 content_hash
        new_hash = input.content_hash or _sha256(content_text)

        # 查詢現有記錄（用於 hash 比對）
        existing = await self._table().select("id, content_hash").eq(
            "source_id", input.source_id
        ).eq("source_url", input.source_url).execute()

        if existing.data and existing.data[0].get("content_hash") == new_hash:
            logger.debug("Article unchanged (hash match): %s", input.source_url)
            return None  # 內容未變，跳過

        data: dict[str, Any] = {
            "project_id": input.project_id,
            "source_id": input.source_id,
            "source_url": input.source_url,
            "title": draft.title or input.source_url,
            "content_hash": new_hash,
            "is_published": True,
            "is_available": True,
            "source_type": "web",
            "category": (draft.categories or [None])[0],
        }
        if input.source_page_id:
            data["source_page_id"] = input.source_page_id
        if draft.author_name:
            data["author_name"] = draft.author_name
        if draft.published_at:
            data["published_at"] = draft.published_at
        if draft.content_html:
            data["content_html"] = draft.content_html
        if content_text:
            data["content_text"] = content_text
        if draft.canonical_url:
            data["canonical_url"] = draft.canonical_url
        if draft.lang:
            data["lang"] = draft.lang

        # meta jsonb：合併 tags/categories/extra
        meta: dict[str, Any] = {}
        if draft.tags:
            meta["tags"] = draft.tags
        if draft.categories:
            meta["categories"] = draft.categories
        if draft.meta:
            meta.update(draft.meta)
        if meta:
            data["meta"] = meta

        # extraction_data jsonb
        if draft.extraction_data:
            data["extraction_data"] = draft.extraction_data

        result = await self._table().upsert(
            data, on_conflict="source_id,source_url"
        ).execute()
        rows = result.data
        return rows[0] if rows else None  # type: ignore[return-value]

    async def get_aggregate_by_id(self, article_id: str):
        """取得文章及其關聯資產、標籤（Phase 3 佔位，目前只回傳文章本體）。"""
        result = await self._table().select("*").eq("id", article_id).execute()
        rows = result.data
        if not rows:
            return None
        from utils.worker.service_inputs import ArticleAggregate
        from utils.db_types import ArticleRow as AR
        # 簡化：不 join assets/tags，只回傳骨架
        return {"article": rows[0], "assets": [], "tags": []}


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()

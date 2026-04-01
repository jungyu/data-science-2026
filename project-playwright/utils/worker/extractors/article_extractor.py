"""
ArticleExtractor — 從文章頁擷取正文內容。

對應 docs/supabase/04_crawler/10_worker-interfaces-python.md 的 PageExtractor.extract_article。

設計原則：
  通用最小版 extractor：title + meta description + 正文前 2000 字。
  外部站點結構差異極大，生產環境需為各站撰寫專屬擷取邏輯。
  這份實作展示「通用骨架」，足以讓學生觀察 article → content_text 的完整流程。
"""

from __future__ import annotations

import logging
from typing import Any

from utils.db_types import SourceRow
from utils.worker.types import ExtractedArticleDraft

logger = logging.getLogger(__name__)

# 正文候選 selector，依優先度嘗試
_CONTENT_SELECTORS = ["article", "main", "[role='main']", "body"]

# 正文截取上限（字元）
_CONTENT_LIMIT = 2000


class ArticleExtractor:
    """通用文章頁擷取器。

    呼叫方式：
        draft = await extractor.extract_article(page, source)
        # draft.title        → 頁面標題
        # draft.content_text → 正文前段
        # draft.canonical_url → og:url（若有）
    """

    async def extract_article(self, page: Any, source: SourceRow) -> ExtractedArticleDraft:
        """從已載入的 page 擷取文章內容，回傳 ExtractedArticleDraft。"""
        title = await page.title() or ""

        # meta description
        abstract = await self._get_meta(page, "description")

        # og:url（正規 URL）
        canonical_url = await self._get_og(page, "url") or None

        # lang（html lang 屬性）
        lang = await self._get_html_lang(page)

        # 正文：優先 <article> > <main> > body
        content_text = await self._extract_body_text(page)

        logger.debug(
            "Article extracted: title=%r content_len=%d",
            title[:40], len(content_text),
        )

        return ExtractedArticleDraft(
            title=title,
            content_text=content_text or None,
            canonical_url=canonical_url,
            lang=lang,
            meta={"abstract": abstract} if abstract else {},
        )

    # ── 內部工具 ──────────────────────────────────────────────────

    async def _get_meta(self, page: Any, name: str) -> str:
        el = page.locator(f'meta[name="{name}"]')
        if await el.count() > 0:
            return await el.first.get_attribute("content") or ""
        return ""

    async def _get_og(self, page: Any, property: str) -> str:
        el = page.locator(f'meta[property="og:{property}"]')
        if await el.count() > 0:
            return await el.first.get_attribute("content") or ""
        return ""

    async def _get_html_lang(self, page: Any) -> str | None:
        try:
            lang = await page.eval_on_selector("html", "el => el.lang")
            return lang or None
        except Exception:
            return None

    async def _extract_body_text(self, page: Any) -> str:
        for selector in _CONTENT_SELECTORS:
            try:
                el = page.locator(selector)
                if await el.count() > 0:
                    text = await el.first.inner_text()
                    text = text.strip()
                    if text:
                        return text[:_CONTENT_LIMIT]
            except Exception:
                continue
        return ""

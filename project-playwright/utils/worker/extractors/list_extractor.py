"""
ListExtractor — 從列表頁擷取文章 URL。

對應 docs/supabase/04_crawler/10_worker-interfaces-python.md 的 PageExtractor.extract_list。

設計原則：
  - 優先使用 source.extractor_schema.list 的選擇器設定（通用）
  - 若 source code 是 "hacker-news"，套用 HN 專屬邏輯（示範）
  - 產品環境每個站點會有自己的 extractor；這裡展示兩種模式並存的結構
"""

from __future__ import annotations

import logging
from typing import Any

from utils.db_types import SourceRow
from utils.worker.types import ListExtractionResult, SourcePageSnapshot

logger = logging.getLogger(__name__)


class ListExtractor:
    """列表頁擷取器。

    呼叫方式：
        result = await extractor.extract_list(page, source)
        # result.discovered_urls  → 下一步要爬的文章 URL
        # result.next_page_url    → 翻頁 URL（若有）
    """

    async def extract_list(self, page: Any, source: SourceRow) -> ListExtractionResult:
        """依 source.code 或 extractor_schema 擷取文章 URL 列表。"""
        if source.code == "hacker-news":
            return await self._extract_hn_list(page, source)
        return await self._extract_schema_based(page, source)

    # ── Hacker News 專屬擷取 ──────────────────────────────────────

    async def _extract_hn_list(self, page: Any, source: SourceRow) -> ListExtractionResult:
        """HN 首頁的文章列表擷取。

        對應 ch08-supabase/04_single_job_worker.py 的 extract_hn_articles()，
        改寫為 async Playwright API。
        """
        urls: list[str] = []
        rows = page.locator("tr.athing")
        count = await rows.count()

        for i in range(count):
            row = rows.nth(i)
            title_el = row.locator("td.title span.titleline > a")
            if await title_el.count() == 0:
                continue

            url = await title_el.first.get_attribute("href") or ""
            if not url:
                continue

            # 補全相對路徑
            if not url.startswith("http"):
                url = f"https://news.ycombinator.com/{url.lstrip('/')}"

            urls.append(url)

        logger.info("HN list extracted %d URLs from %s", len(urls), await page.url())
        return ListExtractionResult(
            title=await page.title(),
            discovered_urls=urls,
        )

    # ── 通用 schema-based 擷取 ────────────────────────────────────

    async def _extract_schema_based(self, page: Any, source: SourceRow) -> ListExtractionResult:
        """依 source.extractor_schema.list 設定擷取。

        source.extractor_schema（jsonb）預期格式：
          {
            "list": {
              "item_selector": "tr.athing",
              "link_selector": "td.title span.titleline > a",
              "next_page_selector": "a.morelink"   // 可選
            }
          }
        """
        schema = source.extractor_schema or {}
        list_cfg = schema.get("list") or {}
        item_sel: str = list_cfg.get("item_selector", "a")
        link_sel: str = list_cfg.get("link_selector", "")
        next_page_sel: str | None = list_cfg.get("next_page_selector")

        urls: list[str] = []
        items = page.locator(item_sel)
        count = await items.count()

        for i in range(count):
            item = items.nth(i)
            link_el = item.locator(link_sel) if link_sel else item
            if await link_el.count() == 0:
                continue
            href = await link_el.first.get_attribute("href") or ""
            if href and href.startswith("http"):
                urls.append(href)

        next_page_url: str | None = None
        if next_page_sel:
            next_el = page.locator(next_page_sel)
            if await next_el.count() > 0:
                next_page_url = await next_el.first.get_attribute("href")

        logger.info(
            "Schema-based list extracted %d URLs from %s", len(urls), await page.url()
        )
        return ListExtractionResult(
            title=await page.title(),
            discovered_urls=urls,
            next_page_url=next_page_url,
        )

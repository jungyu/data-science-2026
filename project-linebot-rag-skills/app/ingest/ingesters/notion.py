"""Notion ingester（reference / TODO 框架）。

對應 spec-25 / task-25 步驟 6。本實作為框架版，學生填入 Notion API 細節。
真用需 `pip install -e ".[notion]"` + `NOTION_API_KEY`。

完整 spec：
- 列出 database / page 子節點 → 每個 page 一份 Document
- heading block 結構 → section_path
- last_edited_time vs Document.fetched_at → 增量更新（對應 store.delete_by_source）
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import AsyncIterator

from app.ingest.document import Document, DocumentSection


class NotionIngester:
    name = "notion"

    def __init__(
        self,
        *,
        api_key: str,
        database_id: str | None = None,
        page_id: str | None = None,
        category: str,
    ) -> None:
        self._api_key = api_key
        self._database_id = database_id
        self._page_id = page_id
        self._category = category

    def required_settings(self) -> list[str]:
        return ["NOTION_API_KEY"]

    async def yield_documents(self) -> AsyncIterator[Document]:
        # TODO: 學生填入：
        # 1. notion-client AsyncClient(auth=self._api_key)
        # 2. 列出 database 子 page 或單一 page_id
        # 3. 每個 page → walk blocks，組 section_path（heading blocks）
        # 4. extract text per section → DocumentSection
        # 5. content_hash 用 last_edited_time + page_id；變動才 yield
        raise NotImplementedError(
            "NotionIngester 是 spec-25 的框架；學生填入 Notion API 細節。"
            "完整實作不在教學主線範圍——可參考 spec-25 §「NotionIngester 設計」段。"
        )
        # 為讓 Python 識別這是 async generator：
        if False:  # pragma: no cover
            yield Document(
                source_id="", source_type="notion", title="",
                sections=[], fetched_at=datetime.now(timezone.utc),
                content_hash="", category=self._category,
            )

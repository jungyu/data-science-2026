# task-25：Multi-format Ingestion

> 規格詳見 [spec-25](../specs/spec-25-multi-format-ingestion.md)
>
> **✅ 已完成（commit `44b630d`）** — 實作記錄與驗收測試見 spec-25 頂部「實作狀態」段。
---

引入統一 `Document` 中介格式 + `Ingester` Protocol；提供 Web / PDF / Notion / CSV 四個範例 ingester。spec-18 Playwright 重新定位為其中一個 ingester。

## 前置

- 建議 task-18 + task-24 已完成（前者提供 web crawler，後者提供 store adapter）
- 若先做 task-25：暫時保留現有 `ingest_markdown.py` 路徑

## 前置安裝

`pyproject.toml`：

```toml
dependencies = [
  ...
  "pypdf>=4.0",
  "pdfplumber>=0.11",
]

[project.optional-dependencies]
notion = ["notion-client>=2.0"]
ocr = ["pytesseract>=0.3", "pillow>=10.0"]
```

## 步驟 1：Document schema

新增 `app/ingest/__init__.py`、`app/ingest/document.py`：

```python
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class DocumentSection(BaseModel):
    text: str
    section_path: list[str] = Field(default_factory=list)
    page_number: int | None = None
    metadata: dict = Field(default_factory=dict)


class Document(BaseModel):
    source_id: str
    source_type: Literal["web", "pdf", "notion", "csv", "docx", "manual"]
    source_url: str | None = None
    title: str
    sections: list[DocumentSection]
    fetched_at: datetime
    content_hash: str
    category: str
    tags: list[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)
```

## 步驟 2：Ingester Protocol

新增 `app/ingest/base.py`：

```python
from __future__ import annotations

from typing import AsyncIterator, Protocol

from app.ingest.document import Document


class Ingester(Protocol):
    name: str

    async def yield_documents(self) -> AsyncIterator[Document]: ...

    def required_settings(self) -> list[str]: ...
```

## 步驟 3：Ingestion Pipeline

新增 `app/ingest/pipeline.py`：

```python
from __future__ import annotations

import hashlib
from dataclasses import dataclass

from app.ingest.base import Ingester
from app.rag.chunker import Chunker
from app.rag.embedder import EmbeddingProvider
from app.storage.knowledge_store import KnowledgeChunkInsert, KnowledgeStore


@dataclass
class IngestStats:
    docs: int = 0
    chunks: int = 0


class IngestionPipeline:
    def __init__(
        self, *, chunker: Chunker, embedder: EmbeddingProvider, store: KnowledgeStore
    ) -> None:
        self._chunker = chunker
        self._embedder = embedder
        self._store = store

    async def run(self, ingester: Ingester) -> IngestStats:
        stats = IngestStats()
        async for doc in ingester.yield_documents():
            inserts: list[KnowledgeChunkInsert] = []
            for section in doc.sections:
                for idx, chunk in enumerate(self._chunker.chunk(section.text), start=1):
                    embedding = await self._embedder.embed_query(chunk)
                    content_hash = hashlib.sha256(chunk.encode("utf-8")).hexdigest()
                    inserts.append(
                        KnowledgeChunkInsert(
                            id=f"{doc.source_id}#{section.page_number or 'x'}#{idx}",
                            content=chunk,
                            category=doc.category,
                            tags=doc.tags,
                            embedding=embedding,
                            content_hash=content_hash,
                            source_id=doc.source_id,
                            source_type=doc.source_type,
                            metadata={
                                **doc.metadata,
                                **section.metadata,
                                "source_url": doc.source_url,
                                "section_path": section.section_path,
                                "page_number": section.page_number,
                                "title": doc.title,
                            },
                        )
                    )
            if inserts:
                await self._store.upsert(inserts)
                stats.docs += 1
                stats.chunks += len(inserts)
        return stats
```

## 步驟 4：WebIngester（spec-18 重新封裝）

新增 `app/ingest/ingesters/web.py`：把 `scripts/crawl_to_markdown.py` 的爬蟲邏輯移成 `WebIngester.yield_documents`。原 markdown 中介檔仍可選擇產出，但 pipeline 內部直接 `yield Document`。

## 步驟 5：PdfIngester

新增 `app/ingest/ingesters/pdf.py`：

```python
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncIterator

import pdfplumber

from app.ingest.base import Ingester
from app.ingest.document import Document, DocumentSection


class PdfIngester:
    name = "pdf"

    def __init__(self, paths: list[Path], *, category: str, use_ocr: bool = False) -> None:
        self._paths = paths
        self._category = category
        self._use_ocr = use_ocr

    def required_settings(self) -> list[str]:
        return []

    async def yield_documents(self) -> AsyncIterator[Document]:
        for path in self._paths:
            doc = await self._build_document(path)
            if doc:
                yield doc

    async def _build_document(self, path: Path) -> Document | None:
        sections: list[DocumentSection] = []
        with pdfplumber.open(path) as pdf:
            outline = self._extract_outline(pdf)
            for page_num, page in enumerate(pdf.pages, start=1):
                text = page.extract_text() or ""
                if not text.strip() and self._use_ocr:
                    text = self._ocr_page(page)
                if not text.strip():
                    continue
                sections.append(
                    DocumentSection(
                        text=text,
                        section_path=outline.get(page_num, []),
                        page_number=page_num,
                    )
                )

        if not sections:
            return None

        full_text = "\n".join(s.text for s in sections)
        content_hash = hashlib.sha256(full_text.encode("utf-8")).hexdigest()[:16]
        return Document(
            source_id=str(path),
            source_type="pdf",
            source_url=f"file://{path.absolute()}",
            title=path.stem,
            sections=sections,
            fetched_at=datetime.now(timezone.utc),
            content_hash=content_hash,
            category=self._category,
            tags=[path.stem],
        )

    def _extract_outline(self, pdf) -> dict[int, list[str]]:
        # 用 PDF outline (bookmarks) 對應 page → section_path
        # 簡化版：直接回空 dict，學生需要時擴充
        return {}

    def _ocr_page(self, page) -> str:
        try:
            import pytesseract
            from PIL import Image
            img = page.to_image().original
            return pytesseract.image_to_string(img)
        except Exception:
            return ""
```

## 步驟 6：NotionIngester

新增 `app/ingest/ingesters/notion.py`：

```python
class NotionIngester:
    name = "notion"

    def __init__(self, *, api_key: str, database_id: str | None = None,
                 page_id: str | None = None, category: str) -> None:
        from notion_client import AsyncClient
        self._client = AsyncClient(auth=api_key)
        self._database_id = database_id
        self._page_id = page_id
        self._category = category

    def required_settings(self) -> list[str]:
        return ["NOTION_API_KEY"]

    async def yield_documents(self):
        # 列出 database / page 子節點 → 每個 page 一份 Document
        # heading block 結構 → section_path
        # last_edited_time vs Document.fetched_at → 增量更新
        ...
```

## 步驟 7：CsvIngester

新增 `app/ingest/ingesters/csv.py`：

```python
from dataclasses import dataclass
from typing import Literal


@dataclass
class CsvIngesterConfig:
    path: str
    mode: Literal["row_per_doc", "table_as_doc"]
    text_columns: list[str]
    metadata_columns: list[str]
    title_template: str = "{topic}"


class CsvIngester:
    name = "csv"

    def __init__(self, config: CsvIngesterConfig, *, category: str) -> None:
        self._cfg = config
        self._category = category

    def required_settings(self):
        return []

    async def yield_documents(self):
        import csv

        with open(self._cfg.path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        if self._cfg.mode == "row_per_doc":
            for i, row in enumerate(rows):
                yield self._row_to_doc(row, idx=i)
        else:
            yield self._table_to_doc(rows)
        # ...實作 _row_to_doc / _table_to_doc
```

## 步驟 8：Per-source chunkers

修改 `app/rag/chunker.py`：抽出 `Chunker` Protocol 與多種實作：

```python
class Chunker(Protocol):
    def chunk(self, text: str) -> list[str]: ...


class MarkdownHeadingChunker:
    """既有 chunk_markdown 改名。"""
    def chunk(self, text: str) -> list[str]: ...


class PageBoundaryChunker:
    """PDF 用：以 page 為自然邊界 + size cap 二次切。"""


class NoOpChunker:
    """CSV 一列即一 chunk，不切。"""
    def chunk(self, text: str) -> list[str]:
        return [text]
```

`app/ingest/chunkers.py`：

```python
DEFAULT_CHUNKERS = {
    "markdown": MarkdownHeadingChunker,
    "web": MarkdownHeadingChunker,
    "pdf": PageBoundaryChunker,
    "notion": MarkdownHeadingChunker,
    "csv": NoOpChunker,
}
```

## 步驟 9：統一 CLI

新增 `scripts/ingest.py`：

```python
"""統一 ingestion CLI。

用法：
    python scripts/ingest.py web --urls urls.txt --category nextjs
    python scripts/ingest.py pdf --paths "docs/RAG/source/*.pdf" --category regulations
    python scripts/ingest.py notion --database-id xxx --category company-wiki
    python scripts/ingest.py csv --path data/faq.csv --mode row_per_doc \
        --text-columns question,answer --category faq
"""

import argparse
import asyncio
from pathlib import Path

from app.dependencies import get_knowledge_store
from app.ingest.pipeline import IngestionPipeline
from app.ingest.ingesters import csv as csv_module, notion, pdf, web
from app.ingest.chunkers import DEFAULT_CHUNKERS
# ...建構 pipeline + 解析 sub-commands + 執行
```

舊 `scripts/ingest_markdown.py` 保留為 thin wrapper：

```python
# scripts/ingest_markdown.py
import sys
sys.argv[1:1] = ["markdown"]
from scripts.ingest import main
asyncio.run(main())
```

## 步驟 10：spec-18 重新定位

修改 `scripts/crawl_to_markdown.py`：底層改用 `WebIngester`，但保留「寫 markdown 中介檔」行為作向後相容。或直接 deprecate 並指向 `scripts/ingest.py web`。

## 步驟 11：測試

新增 `tests/test_ingest_pipeline.py`：

```python
@pytest.mark.asyncio
async def test_pipeline_chunks_and_embeds(stub_chunker, stub_embedder, stub_store):
    pipeline = IngestionPipeline(chunker=stub_chunker, embedder=stub_embedder, store=stub_store)

    class StubIngester:
        async def yield_documents(self):
            yield Document(
                source_id="s1", source_type="manual", title="t",
                sections=[DocumentSection(text="hello world")],
                fetched_at=datetime.now(timezone.utc),
                content_hash="h", category="general",
            )

    stats = await pipeline.run(StubIngester())
    assert stats.docs == 1
    assert stats.chunks >= 1
```

`tests/test_pdf_ingester.py`、`tests/test_csv_ingester.py`：用 fixture PDF / CSV 檔。

## 步驟 12：教學配套

新增三份 walkthrough：

- `docs/ai-agent/examples/ingest-pdf-walkthrough.md`：抓 1 份 ≥30 頁 PDF
- `docs/ai-agent/examples/ingest-notion-walkthrough.md`：Notion database 增量
- `docs/ai-agent/examples/ingest-csv-walkthrough.md`：FAQ 100 列

## 步驟 13：Citation 顯示 page_number

task-16 的 `AnswerContractBuilder._citations` 已從 `metadata.source_url` 取 source；本 task 加：

```python
def _source_from_chunk(c):
    meta = c.metadata or {}
    parts = [meta.get("source_url") or c.title or "knowledge_base"]
    if meta.get("page_number"):
        parts.append(f"p.{meta['page_number']}")
    if meta.get("section_path"):
        parts.append(" > ".join(meta["section_path"]))
    return " (".join(parts) + (")" if len(parts) > 1 else "")
```

讓 narrative 中的 `[來源 1]` 對應 `https://...nextjs.org/docs (p.42, 第 3.2 節)`。

## 請輸出

1. `app/ingest/`（document, base, pipeline, chunkers + ingesters/ × 4）
2. 修改後的 `app/rag/chunker.py`
3. 修改後的 `app/generator/contract.py`（`_source_from_chunk` 帶 page_number）
4. `scripts/ingest.py`（統一 CLI）；`scripts/ingest_markdown.py` 改 thin wrapper
5. `tests/test_ingest_pipeline.py`、PDF/CSV 各一個測試
6. 三份 walkthrough 文件
7. 修改後的 `pyproject.toml`、README

## 驗收指令

```bash
python -m pip install -e ".[dev]"

# 4 種 ingester 各跑一次
python scripts/ingest.py web --urls urls/test.txt --category nextjs
python scripts/ingest.py pdf --paths "tests/fixtures/sample.pdf" --category regulations
python scripts/ingest.py notion --database-id $NOTION_DB --category company-wiki
python scripts/ingest.py csv --path tests/fixtures/faq.csv --mode row_per_doc \
    --text-columns question,answer --category faq

# Supabase 端驗證 metadata
psql $SUPABASE_DB_URL -c \
    "select metadata->>'source_url', metadata->>'page_number' from private_knowledge limit 5;"

# LINE / web 端問 PDF 內容 → citation 顯示 (p.42)
```

驗收通過條件：

- 4 個 ingester 都能跑通並 upsert 正確 metadata
- PDF citation 在 narrative 中顯示 page_number
- 既有 markdown 路徑向後相容（`scripts/ingest_markdown.py docs/RAG/*.md` 仍可用）
- 同一 Notion page 跑兩次 ingest 第二次「unchanged, skipped」
- `app/rag/chunker.py` 抽 Protocol 後既有 markdown 切段邏輯不退步

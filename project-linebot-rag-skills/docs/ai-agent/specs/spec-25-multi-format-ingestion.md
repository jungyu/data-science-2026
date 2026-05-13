# Spec-25：Multi-format Ingestion

> **✅ Notion ingester 已實作（commit `44b630d`）；PDF outline / tables 仍為已知 gap**
>
> - `app/ingest/ingesters/notion.py::NotionIngester.yield_documents` 從 `raise NotImplementedError` 重寫為真實作
> - 支援 `database_id` / `page_id` 兩種模式（後者走 `pages.retrieve`）
> - 自動 walk blocks：heading_1~3 切 `section_path`，paragraph / list / quote / code 流入內容
> - `content_hash = sha256(page_id + last_edited_time)`：未編輯的 page 由 IngestionPipeline 跳過（增量更新）
> - 建構時接受 `client` 注入，便於單測（不打真 Notion API）
> - 驗收測試：`tests/test_notion_ingester.py`（6 cases 含 heading 結構、`content_hash` 穩定、empty page skip）
> - **仍缺**：PDF outline → `section_path`、`pdfplumber.extract_tables()` 表格抽取（屬於後續優化）

## 背景

spec-18 只示範 Web crawler（Playwright），但學生實際做專業 RAG 服務面對的資料來源更多：

| 來源 | 學生情境 | 目前覆蓋 |
|---|---|---|
| Web | 技術文件、blog | ✅ spec-18 |
| **PDF** | 法規、論文、產品手冊 | ❌ |
| Notion | 公司知識庫 | 🟡 P5 spec-07 提及未實作 |
| Word / PowerPoint | 內訓教材 | ❌ |
| Confluence / Google Docs | 企業 wiki | ❌ |
| **CSV / Excel** | FAQ 表、SKU 表 | ❌ |
| 內部 API / DB dump | CRM、客服 ticket | ❌ |

對「專業 RAG 服務」，**PDF + 結構化文件**幾乎是必選，目前完全沒有。本 spec 引入統一的 `Document` 中介格式 + `Ingester` Protocol，把 spec-18 重新定位為其中一個 ingester，並補上 PDF / Notion / CSV 三個常用格式作為範例。

借鑑：[`docs/RAG/ch02-etl-chunking.md`](../../RAG/ch02-etl-chunking.md) 的 ETL 思路、LangChain 的 `Document` 抽象（簡化版）。

## 設計

### Document 中介格式

新增 `app/ingest/document.py`：

```python
class DocumentSection(BaseModel):
    """一份 document 的一個邏輯單位（章節 / page / table row）。
    chunker 會把這個單位再切成 chunks。"""

    text: str
    section_path: list[str] = []       # ["第 3 章", "3.2 節"]
    page_number: int | None = None
    metadata: dict = {}                # 額外欄位


class Document(BaseModel):
    source_id: str                     # 唯一 id（URL / 檔案 hash / Notion page id）
    source_type: Literal["web", "pdf", "notion", "csv", "docx", "manual"]
    source_url: str | None = None
    title: str
    sections: list[DocumentSection]
    fetched_at: datetime
    content_hash: str                  # 整體去重
    category: str
    tags: list[str] = []
    metadata: dict = {}                # 來源 specific（PDF 作者 / Notion icon ...）
```

`Document` 是 ingester → chunker → embedder → store 的契約。Chunker 拿到的單位是 `DocumentSection.text`，但會把 `section_path` / `page_number` 帶進每個 chunk 的 metadata。

### Ingester Protocol

新增 `app/ingest/base.py`：

```python
class Ingester(Protocol):
    """從某個來源 yield 出 Document 流。"""

    name: str  # "web" | "pdf" | "notion" | ...

    async def yield_documents(self) -> AsyncIterator[Document]: ...

    def required_settings(self) -> list[str]:
        """聲明需要哪些 env / config（例 ["NOTION_API_KEY"]）。
        DI 階段檢查，缺的話直接拋有用的錯誤。"""
        ...
```

**獨立於 store**：ingester 只產 Document；要存到哪個 store（Supabase / sqlite_vec / Pinecone）由 spec-24 的 store 決定。

### 三個範例 ingester

| Ingester | 用途 | 主要依賴 |
|---|---|---|
| `WebIngester` | spec-18 Playwright crawler 重新封裝 | playwright, readability-lxml, markdownify |
| `PdfIngester` | PDF（含掃描 / OCR fallback）| pypdf, pdfplumber, optional: tesseract |
| `NotionIngester` | Notion API export | notion-client |
| `CsvIngester` | 結構化表（每列一份 doc）| pandas / 純 stdlib |

`DocxIngester` / `ConfluenceIngester` 不在本 spec 範圍——介面有了學生自己加。

### PDF 處理特殊考量

PDF 是 RAG 教學中最棘手的格式：

- **文字抽取策略**：`pdfplumber`（保留 layout）優先，失敗 fallback `pypdf`（純文字）
- **頁碼保留**：每個 `DocumentSection` 對應 1 個 page；`section_path` 用 PDF outline（書籤）填
- **表格**：`pdfplumber.extract_tables()` 抽出後轉 markdown 表格
- **掃描 PDF**：偵測「無法抽出文字」時，可選 OCR fallback（`pytesseract`）；本 spec 預設關閉，學生主動開
- **圖片**：本 spec 不處理（multi-modal RAG 屬另一主題）

提供 `scripts/ingest_pdf.py`：

```bash
python scripts/ingest_pdf.py docs/RAG/source/*.pdf \
  --category regulations \
  --use-ocr false
```

### Notion ingester 設計

最少配置：

```bash
NOTION_API_KEY=secret_xxx
NOTION_DATABASE_ID=...   # 或 NOTION_PAGE_ID
```

行為：

1. 列出 database / page 子節點
2. 每個 page → 一份 Document
3. Page 的 heading 結構 → `section_path`
4. Page property（標籤、分類）→ `tags` / `category`
5. 增量更新：用 `last_edited_time` 比對 `Document.fetched_at` 跳過未變更

### CSV ingester 設計

每列一份 Document（適用 FAQ 表）或全表一份 Document（適用 SKU 規格表）—— 由 config 決定：

```python
@dataclass
class CsvIngesterConfig:
    path: str
    mode: Literal["row_per_doc", "table_as_doc"]
    text_columns: list[str]            # 哪些欄位串成 text
    metadata_columns: list[str]        # 哪些欄位寫進 metadata
    title_template: str = "{topic}"    # f-string 用 row 欄位
```

### 統一 Ingestion Pipeline

新增 `app/ingest/pipeline.py`：

```python
class IngestionPipeline:
    def __init__(
        self, *, chunker: Chunker, embedder: Embedder, store: KnowledgeStore
    ) -> None: ...

    async def run(self, ingester: Ingester) -> IngestStats:
        async for doc in ingester.yield_documents():
            for section in doc.sections:
                for chunk in self.chunker.chunk(section.text):
                    embedding = await self.embedder.embed_query(chunk)
                    await self.store.upsert([_to_chunk_record(doc, section, chunk, embedding)])
```

`scripts/ingest_markdown.py` 改寫成 `scripts/ingest.py`，吃任意 ingester：

```bash
python scripts/ingest.py web --urls urls.txt --category nextjs
python scripts/ingest.py pdf --paths "docs/RAG/source/*.pdf" --category regulations
python scripts/ingest.py notion --database-id xxx --category company-wiki
python scripts/ingest.py csv --path data/faq.csv --mode row_per_doc \
  --text-columns question,answer --category faq
```

舊 `scripts/ingest_markdown.py` 保留作 thin wrapper（對應 `MarkdownIngester` 子集），向後相容。

### Chunking 策略可擴充

`app/rag/chunker.py` 既有的 `chunk_markdown` 仍在；本 spec 不重寫 chunking——但 `Chunker` 抽成 Protocol 讓不同來源用不同策略：

| 來源 | 推薦 chunker |
|---|---|
| Markdown | by heading + size cap |
| PDF | by page boundaries + size cap |
| CSV row | 不切（一列即一 chunk）|
| Notion | by toggle / heading block |

### 與 spec-18 / spec-24 的關係

- spec-18 → **重定位為 spec-25 的 WebIngester 實作**；`scripts/crawl_to_markdown.py` 仍在但底層改用 `WebIngester` + 寫 markdown frontmatter（行為向後相容）
- spec-24 store 不變；本 spec 只在「資料**進**store」端動

### 不做什麼

- 不做 multi-modal（圖片、音檔、影片）
- 不做即時同步（webhook 觸發增量 ingest）
- 不做版本控制 / time-travel query（屬 P5 spec-06）
- 不做 ETL workflow scheduler（cron / Airflow）
- 不做 OCR 全套（提供 hook，學生要 OCR 自己接 tesseract）

## 介面契約

**新增**：

| 檔案 | 用途 |
|---|---|
| `app/ingest/__init__.py` | registry |
| `app/ingest/document.py` | `Document` / `DocumentSection` schema |
| `app/ingest/base.py` | `Ingester` Protocol |
| `app/ingest/pipeline.py` | `IngestionPipeline` |
| `app/ingest/ingesters/web.py` | spec-18 重新封裝 |
| `app/ingest/ingesters/pdf.py` | PDF 處理 |
| `app/ingest/ingesters/notion.py` | Notion API |
| `app/ingest/ingesters/csv.py` | CSV / Excel |
| `app/ingest/chunkers.py` | per-source chunker 註冊表 |
| `scripts/ingest.py` | 統一 CLI |

**修改**：

- `app/rag/chunker.py`：抽出 `Chunker` Protocol，既有 `chunk_markdown` 改為 `MarkdownHeadingChunker.chunk()`
- `scripts/ingest_markdown.py`：保留作 thin wrapper（呼叫 `scripts/ingest.py markdown`）
- `scripts/crawl_to_markdown.py`：保留；但底層改用 `WebIngester` 共用內容抽取邏輯

**新增 dependency**：

```toml
"pypdf>=4.0",
"pdfplumber>=0.11",

[project.optional-dependencies]
notion = ["notion-client>=2.0"]
ocr = ["pytesseract>=0.3", "pillow>=10.0"]
```

**新增範例**：

| 檔案 | 用途 |
|---|---|
| `docs/ai-agent/examples/ingest-pdf-walkthrough.md` | PDF 案例（抓 1 份法規 PDF → ingest → 查詢）|
| `docs/ai-agent/examples/ingest-notion-walkthrough.md` | Notion 案例 |
| `docs/ai-agent/examples/ingest-csv-walkthrough.md` | CSV FAQ 案例 |
| `docs/ai-agent/examples/document-schema.md` | `Document` schema 設計理由 |

## 驗收標準

- `python scripts/ingest.py {web,pdf,notion,csv}` 四種子命令都能跑通
- PDF 範例：抓 1 份 ≥30 頁的 PDF，ingest 後在 LINE / web 上問頁面內容能命中，回覆 citations 含 `page_number`
- Notion 範例：同一個 page 跑兩次 ingest，第二次顯示「unchanged, skipped」
- CSV 範例：FAQ 表 100 列 → 100 個 chunk（每列一份），category filter 能精確查到
- WebIngester 行為與 spec-18 等價（既有 nextjs 範例 metric 不退步）
- `Document` schema 通過 pydantic 驗證；missing required field 會 raise 有用錯誤
- `tests/test_ingest_pipeline.py`：用 `StubIngester` 驗證 pipeline 串起 chunk → embed → upsert 三步
- 三個範例 walkthrough 文件都有實際可貼用的指令與預期 log 輸出
- 既有 markdown ingest 路徑向後相容：`scripts/ingest_markdown.py docs/RAG/*.md` 仍可跑
- `Document.metadata` 流到最終 `KnowledgeChunk.metadata`，retriever 拿到的 chunk 含 `page_number` / `section_path`，spec-16 Citation 在 narrative 中可顯示「(p.42, 第 3.2 節)」

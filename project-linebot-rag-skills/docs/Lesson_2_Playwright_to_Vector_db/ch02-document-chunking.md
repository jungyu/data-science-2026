# Ch 02：Document 格式 + Chunking 策略

> 核心檔案：[`app/ingest/document.py`](../../app/ingest/document.py)、
> [`app/ingest/chunkers.py`](../../app/ingest/chunkers.py)、
> [`app/rag/chunker.py`](../../app/rag/chunker.py)

---

## 2-1  為什麼不直接把整頁文字存成一個向量？

假設你抓了一頁 10,000 字的文件，全部壓成一個 1536 維向量。

```
使用者問：「getStaticProps 怎麼用？」

這個 10,000 字向量裡包含：
- App Router 介紹
- getStaticProps 說明  ← 使用者要的
- getServerSideProps 說明
- Middleware 介紹
- ...

向量是所有內容的平均 → "getStaticProps" 這個方向被其他主題稀釋了
→ 搜尋結果不準確
```

**解法：切成小塊（chunk），每塊各自 embed**。

---

## 2-2  `Document`：所有格式的共同語言

[`app/ingest/document.py`](../../app/ingest/document.py) 定義了統一的中介格式：

```python
class DocumentSection(BaseModel):
    text:         str
    page_number:  int | None = None    # PDF 才有
    section_path: str | None = None    # "第三章 > 第二節"
    metadata:     dict = {}

class Document(BaseModel):
    source_id:    str                  # URL 或檔案路徑（去重 key）
    source_type:  str                  # "web" | "pdf" | "csv" | "markdown"
    source_url:   str | None = None
    title:        str
    sections:     list[DocumentSection]  # 一份文件 = 多個 section
    category:     str
    content_hash: str                  # 整份文件的 hash（增量更新用）
    tags:         list[str] = []
    metadata:     dict = {}
```

每種 Ingester（WebIngester / PdfIngester / CsvIngester）都把資料轉成 `Document`，
後面的 `IngestionPipeline` 不需要知道來源格式。

---

## 2-3  三種 Chunker：根據來源選

[`app/ingest/chunkers.py`](../../app/ingest/chunkers.py)：

### `MarkdownHeadingChunker`（web / markdown / notion 用）

```python
class MarkdownHeadingChunker:
    def __init__(self, *, max_chars: int = 1200, overlap: int = 120):
        ...
    def chunk(self, text: str) -> list[str]:
        return chunk_markdown(text, max_chars=self._max, overlap=self._overlap)
```

底層邏輯（[`app/rag/chunker.py`](../../app/rag/chunker.py)）：

```python
def chunk_markdown(text, *, max_chars=1200, overlap=120) -> list[str]:
    # 超過 max_chars 就切，相鄰 chunk 保留 overlap 個字元的重疊
    chunks = []
    start = 0
    while start < len(text):
        end = min(len(text), start + max_chars)
        chunks.append(text[start:end].strip())
        start = max(0, end - overlap)   # ← 這就是 overlap
    return chunks
```

**Overlap 的效果**：

```
原始文字（假設 max_chars=20, overlap=5）：
"ABCDEFGHIJKLMNOPQRSTUVWXYZ"

chunk 1：ABCDEFGHIJKLMNOPQRST   （第 1–20 字）
chunk 2：PQRSTUVWXYZ            （第 16–26 字，前 5 字和 chunk 1 重疊）
              ↑↑↑↑↑ 重疊

好處：跨越切點的語意不會被硬切斷
```

---

### `PageBoundaryChunker`（PDF 用）

```python
class PageBoundaryChunker:
    def __init__(self, *, max_chars: int = 2400, overlap: int = 120):
        ...
    def chunk(self, text: str) -> list[str]:
        if len(text) <= self._max:
            return [text.strip()]   # 一頁夠短 → 整頁一個 chunk
        return chunk_markdown(...)  # 太長再切，保留頁碼資訊
```

**為什麼 max_chars=2400（比 Markdown 的 1200 大）？**

PDF 的一頁通常是一個完整的邏輯單位（一條法規、一個藥品說明）。
切太細會破壞上下文。

---

### `NoOpChunker`（CSV 用）

```python
class NoOpChunker:
    def chunk(self, text: str) -> list[str]:
        return [text.strip()] if text.strip() else []
```

CSV 每一列已經是最小單位（一筆藥物交互作用記錄、一條客服問答），不需要再切。

---

## 2-4  `DEFAULT_CHUNKERS`：自動對應

```python
# app/ingest/chunkers.py 第 57–65 行
DEFAULT_CHUNKERS: dict[str, Chunker] = {
    "markdown": MarkdownHeadingChunker(),
    "web":      MarkdownHeadingChunker(),
    "notion":   MarkdownHeadingChunker(),
    "pdf":      PageBoundaryChunker(),
    "csv":      NoOpChunker(),
    "docx":     MarkdownHeadingChunker(),
    "manual":   MarkdownHeadingChunker(),
}
```

`IngestionPipeline` 根據 `Document.source_type` 自動選對應的 chunker。
你不需要手動指定。

---

## 2-5  親眼看 Chunking 效果

```python
# 在 Python REPL 跑
from app.ingest.chunkers import MarkdownHeadingChunker, PageBoundaryChunker, NoOpChunker

text = """
# App Router

Next.js 14 引入了 App Router。它基於 React Server Components，
讓你可以在伺服器端直接 fetch 資料，不需要 getServerSideProps。

## 路由定義

在 app/ 目錄建立 page.tsx 檔案即可定義路由。
每個資料夾對應一個 URL segment。

## Layouts

layout.tsx 用來定義跨頁面共用的 UI（例如 navigation bar）。
"""

chunker = MarkdownHeadingChunker(max_chars=200, overlap=30)
chunks = chunker.chunk(text)

for i, c in enumerate(chunks, 1):
    print(f"\n── chunk {i} ({len(c)} chars) ──")
    print(c)
```

預期輸出：
```
── chunk 1 (198 chars) ──
# App Router

Next.js 14 引入了 App Router。它基於 React Server Components，
讓你可以在伺服器端直接 fetch 資料，不需要 getServerSideProps。

## 路由定義

在 app/ 目錄建立 page.tsx 檔案即

── chunk 2 (142 chars) ──
案即可定義路由。      ← 注意：前面 30 字和 chunk 1 重疊
每個資料夾對應一個 URL segment。

## Layouts

layout.tsx 用來定義跨頁面共用的 UI...
```

---

## 2-6  Chunk size 怎麼選？

```
╔═══════════════════════════════════════════════════════╗
║  太小（< 200 chars）→ 上下文不足，LLM 無法理解       ║
║  太大（> 2000 chars）→ 語意被稀釋，搜尋結果不準       ║
║  甜蜜點：600–1200 chars（約 1–3 段文字）              ║
╚═══════════════════════════════════════════════════════╝
```

本專案預設 `max_chars=1200, overlap=120`，適合大多數情境。
你的領域如果是法條（每條通常 200–400 字），可以改小：

```python
# 在 IngestionPipeline 覆蓋預設 chunker
pipeline = IngestionPipeline(
    embedder=embedder,
    store=store,
    chunker=MarkdownHeadingChunker(max_chars=600, overlap=60),  # 法條專用
)
```

---

## ✏️ 本章任務

1. 對 Ch01 抓下來的 Markdown 檔，親眼跑 `MarkdownHeadingChunker`，看 chunk 怎麼被切
2. 數一下：一篇文章大概切出幾個 chunk？chunk 的平均長度？
3. 如果你的領域有 PDF，試試 `PageBoundaryChunker`，比較和 `MarkdownHeadingChunker` 的差異

下一章 → [Ch 03：IngestionPipeline 全流程](ch03-ingest-pipeline.md)

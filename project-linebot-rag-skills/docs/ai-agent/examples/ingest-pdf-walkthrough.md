# 範例：抓 PDF 進知識庫

> 對應 [task-25](../tasks/task-25-multi-format-ingestion.md) §「PDF 處理特殊考量」。

## 1. 準備

```bash
python -m pip install -e ".[dev]"     # 已含 pdfplumber + pypdf
# 把 PDF 放到任意位置，例如：
mkdir -p docs/sources/regulations
cp ~/Downloads/labor_law.pdf docs/sources/regulations/
```

## 2. Ingest

```bash
KNOWLEDGE_STORE_BACKEND=sqlite_vec \
python scripts/ingest.py pdf \
  --paths "docs/sources/regulations/*.pdf" \
  --category regulations
```

預期輸出：

```
[pdf] docs=1 chunks=42 skipped=0
```

每個 PDF page → 一個 chunk（page 過長會二次切，由 `PageBoundaryChunker` 處理）。

## 3. 驗證 metadata 流通

```python
from app.dependencies import get_knowledge_store
store = get_knowledge_store()
results = await store.search(query_embedding=[...], top_k=3)
for c in results:
    print(c.id, c.metadata.get("page_number"), c.metadata.get("source_url"))
```

預期：每個 chunk 帶 `page_number` 與 `source_url=file:///path/to/labor_law.pdf`。

## 4. LINE / Web 上提問

問 PDF 涵蓋的問題（例：「勞基法 §32 怎麼規定加班？」）：

- selfrag / reflection variant 的 `[來源 1]` 格式變成：
  ```
  file:///path/to/labor_law.pdf (p.42)
  ```
- 學生看 narrative 即可追溯到具體 page

## 5. 掃描 PDF（OCR fallback）

抽不到文字的 page（掃描影像）預設會被 skip。要 OCR：

```bash
python -m pip install -e ".[ocr]"
brew install tesseract                # macOS

python scripts/ingest.py pdf --paths "..." --category x --use-ocr
```

OCR 較慢且品質取決於原圖。本專案不對 OCR 結果做額外清洗。

## 6. 進階：擴充 outline → section_path

`PdfIngester._build_document` 內 `section_path` 目前留空。學生要把 PDF
bookmarks 拉進 metadata 可改用 `pypdf.PdfReader(...).outline`，把 outline tree
與 page 對應後填入 `DocumentSection.section_path`。完成後 narrative 引用會變：

```
file:///path/to/labor_law.pdf (p.42, 第 3 章 > 3.2 工時)
```

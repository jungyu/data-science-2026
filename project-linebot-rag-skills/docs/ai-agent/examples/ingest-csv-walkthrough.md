# 範例：FAQ CSV 進知識庫

> 對應 [task-25](../tasks/task-25-multi-format-ingestion.md) §「CSV ingester 設計」。

## 適用情境

- FAQ 表（每列一問一答）
- SKU 規格表（每列一個產品）
- 客服 ticket dump

## 1. 準備 CSV

`data/faq.csv`：

```csv
question,answer,topic
什麼是 RAG？,RAG 是檢索增強生成，讓 LLM 在生成前先查外部知識,intro
向量檢索與全文檢索差異？,向量檢索比相似度，全文檢索比關鍵字命中,vector
LangGraph 為何要用？,需要條件分支、迴圈、可中斷的流程時，LangGraph 比函式串接更合適,langgraph
```

## 2. Ingest（row_per_doc 模式）

```bash
KNOWLEDGE_STORE_BACKEND=sqlite_vec \
python scripts/ingest.py csv \
  --path data/faq.csv \
  --mode row_per_doc \
  --text-columns question,answer \
  --metadata-columns topic \
  --title-column question \
  --category faq
```

預期輸出：

```
[csv] docs=3 chunks=3 skipped=0
```

> 每列一份 Document → 一個 chunk（NoOpChunker，不切）。

## 3. 驗證

```python
results = await store.search(query_embedding=embedder.embed_query("RAG"), top_k=3)
for c in results:
    print(c.id, c.metadata.get("topic"), c.content[:80])
```

預期：第一筆 `topic=intro`，content 含 question + answer。

## 4. table_as_doc 模式（小型參考表）

當 CSV 是「整體當作一份知識」而非「每列一個 FAQ」：

```bash
python scripts/ingest.py csv \
  --path data/sku_lookup.csv \
  --mode table_as_doc \
  --text-columns sku,name,price \
  --category catalog
```

整張表 → 一個 chunk（適合 ≤ 100 列的小表；大表用 row_per_doc）。

## 5. 學生轉題目要動什麼

只動 CLI 參數：
- `--text-columns`：哪些欄位串成 chunk 文字（embedding 比對的對象）
- `--metadata-columns`：哪些欄位寫進 metadata（不進 embedding，但 retrieval 後可讀）
- `--title-column`：列哪個欄位作 Document title
- `--mode`：FAQ 用 row_per_doc，小表用 table_as_doc
- `--category`：路由 / 過濾用

不動程式碼。

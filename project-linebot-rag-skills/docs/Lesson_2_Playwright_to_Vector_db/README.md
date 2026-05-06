# Lesson 2：Playwright → Vector DB

> **先修**：完成 Lesson 1（能跑 `store.search()`）
> **時間**：約 4–5 小時

---

```
╔══════════════════════════════════════════════════════╗
║  你會做到：                                          ║
║  ✅ 用 Playwright 抓一個真實網頁，存成 Markdown      ║
║  ✅ 知道 3 種 Chunking 策略各自適合什麼情境          ║
║  ✅ 用 IngestionPipeline 一行指令讓資料進 Supabase   ║
╚══════════════════════════════════════════════════════╝
```

## 章節地圖

| 章 | 主題 | 核心程式 |
|----|------|---------|
| [Ch 01](ch01-crawl.md) | 爬網頁 → Markdown | `scripts/site_rules.py`、`app/ingest/ingesters/web.py` |
| [Ch 02](ch02-document-chunking.md) | Document 格式 + Chunking | `app/ingest/document.py`、`app/ingest/chunkers.py` |
| [Ch 03](ch03-ingest-pipeline.md) | IngestionPipeline 全流程 | `app/ingest/pipeline.py`、`scripts/ingest.py` |
| [Ch 04](ch04-verify.md) | 驗證資料：看見你的 chunk | `store.search()` + Supabase Dashboard |

完成後進 [Lesson 3](../Lesson_3_LangGraph_RAG/README.md)。

---

## 驗收：pytest

```bash
# 跑 ingest / chunker 相關測試
pytest tests/test_retriever.py tests/ -k "ingest or chunk or pipeline" -v

# 如果沒有符合 pattern 的測試，直接跑全部
pytest -v --tb=short

# 全綠 ✅ 才進 Lesson 3
```

> 💡 Playwright 相關測試（爬蟲）需要 `playwright install chromium` 且能連外網。
> 純 chunker / pipeline 測試不需要 browser，可以在離線環境跑。

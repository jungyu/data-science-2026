# Lesson 1：Supabase Vector DB

> **先修**：會 Python async/await、會基本 SQL SELECT/INSERT
> **時間**：約 3–4 小時

---

```
╔══════════════════════════════════════╗
║  你會做到：                          ║
║  ✅ 10 行 Python 查出語意最近的 chunk ║
║  ✅ 看懂 schema.sql 每一行在做什麼   ║
║  ✅ 能解釋向量搜尋和 SQL LIKE 的差異 ║
╚══════════════════════════════════════╝
```

## 章節地圖

| 章 | 主題 | 核心程式 |
|----|------|---------|
| [Ch 01](ch01-what-is-vector.md) | 什麼是向量搜尋 | 概念 |
| [Ch 02](ch02-schema-deep-dive.md) | `schema.sql` 解剖 | `supabase/schema.sql` |
| [Ch 03](ch03-embed-and-store.md) | Embed + 存入 | `app/rag/embedder.py`、`app/storage/stores/supabase_store.py` |
| [Ch 04](ch04-first-search.md) | 第一次語意查詢 | `supabase/functions.sql` |

學完 Lesson 1，你就有了「會存、會查」的 vector DB 基礎，
再進 [Lesson 2](../Lesson_2_Playwright_to_Vector_db/README.md) 學怎麼把真實資料灌進去。

---

## 驗收：pytest

每章末的「里程碑」完成後，用以下指令驗證：

```bash
# 跑 Supabase / storage 相關測試
pytest tests/test_retriever.py -v

# 如果出現 SKIPPED，確認 .env 填好了 SUPABASE_URL 和 SUPABASE_SERVICE_ROLE_KEY
# 如果全綠 ✅，代表 Lesson 1 環境設定正確
```

> ⚠️ 測試需要真實的 Supabase 連線。網路或 key 有問題時會出現 `ConnectionRefusedError`，
> 不是程式碼問題，是 `.env` 設定問題——對照 [.env.GUIDE.md](../.env.GUIDE.md) 排查。

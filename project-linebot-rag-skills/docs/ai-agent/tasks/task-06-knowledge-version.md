# task-06：Knowledge Version 追蹤

> 規格詳見 [spec-06](../specs/spec-06-knowledge-version.md)

---

請修改 `scripts/ingest_markdown.py`，讓每次成功匯入時自動遞增知識庫版本號。

## 修改 `scripts/ingest_markdown.py`

在 upsert 前取得目前最大版本號，新 chunk 的 `knowledge_version` 設為 `current_version + 1`：

```python
async def get_current_version(supabase) -> int:
    result = (
        await supabase.table("private_knowledge")
        .select("knowledge_version")
        .order("knowledge_version", desc=True)
        .limit(1)
        .execute()
    )
    return result.data[0]["knowledge_version"] if result.data else 0

# 在 ingest 主流程：
current_version = await get_current_version(supabase)
new_version = current_version + 1

# upsert 時帶入 knowledge_version=new_version
payload = {
    ...,
    "knowledge_version": new_version,
}
```

結束時印出：
```
Ingested N chunks (knowledge_version: {new_version})
```

## 不需要修改 schema

`private_knowledge.knowledge_version` 欄位已存在（`integer DEFAULT 1`），只需讓 ingest 腳本正確寫入。

## 請輸出

1. 修改後的完整 `scripts/ingest_markdown.py`
2. 測試：`assert get_current_version()` 空表回傳 0

## 驗收指令

```bash
.venv/bin/python scripts/ingest_markdown.py docs/RAG/ch01-why-rag.md --category rag
# 輸出應包含：Ingested N chunks (knowledge_version: X)

# 再次匯入
.venv/bin/python scripts/ingest_markdown.py docs/RAG/ch02-etl-chunking.md --category rag
# knowledge_version 應為 X+1
```

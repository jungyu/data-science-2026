# Spec-06：Knowledge Version 追蹤

> **✅ 已實作**
>
> - `IngestionPipeline.run()` 開頭呼叫 `store.next_knowledge_version()`（若實作）
>   取得本次匯入用版本號（`max + 1`）；該 run 所有 chunk 共用此版本
> - `SupabaseStore.next_knowledge_version()` 走 `SELECT max(knowledge_version)`
> - `KnowledgeChunkInsert.knowledge_version: int | None` 為 optional 欄位；
>   sqlite_vec / pinecone 等沒有對應欄位的 store 直接忽略（pipeline 拿到 None
>   也照樣跑，chunk 走 schema 預設值）
> - 與 [spec-05](./spec-05-prompt-cache.md) prompt cache 連動：版本變動自動讓
>   舊 cache_key 失配 → 不需手動清表
> - 驗收測試：`tests/test_ingest/test_pipeline.py::test_pipeline_stamps_knowledge_version_when_store_supports_it`
>   + 2 個 fallback / 失敗路徑測試

## 背景

`private_knowledge.knowledge_version` 欄位存在，但 `ingest_markdown.py` 不更新它，`prompt_cache` 也無法依此失效。目前快取失效的唯一方式是手動清空 `prompt_cache` 資料表。

## 目標

建立一個全域知識庫版本號，每次成功匯入知識庫後自動遞增，讓 prompt cache 能依此失效。

## 設計

### 版本號儲存位置

使用 Supabase 一筆固定的 metadata 記錄（不新增資料表）：

```sql
-- 在 seed.sql 加入
INSERT INTO prompt_cache (cache_key, user_input, response_text, knowledge_version)
VALUES ('__meta__:knowledge_version', '', '', 1)
ON CONFLICT (cache_key) DO NOTHING;
```

或：在 `private_knowledge` 取 `max(knowledge_version)`，每次 ingest 時把所有新增 chunk 的 `knowledge_version` 設為 `current_max + 1`。

**選擇方案 B（max knowledge_version）**：不需要額外資料表或 metadata 記錄，直接查 `SELECT MAX(knowledge_version) FROM private_knowledge`。

## 介面契約

**修改**：`scripts/ingest_markdown.py`

```python
async def get_current_version(supabase) -> int:
    result = await supabase.table("private_knowledge").select("knowledge_version").order("knowledge_version", desc=True).limit(1).execute()
    return result.data[0]["knowledge_version"] if result.data else 0

# ingest 時，新 chunk 的 knowledge_version = current_version + 1
```

**修改**：`app/storage/knowledge_repo.py`

```python
async def get_knowledge_version(self) -> int:
    # SELECT MAX(knowledge_version) FROM private_knowledge
    # 回傳整數，空表回傳 0
```

**修改**：`app/dependencies.py`
- `RuntimeServices` 加入 `cache_repo: CacheRepository`
- Generator 收到 `cache_repo` 時使用 knowledge_version

## Cache 失效邏輯

查詢快取時比對 `cache_key`（已包含 knowledge_version）：

```python
cache_key = sha256(f"{skill_id}:{knowledge_version}:{normalized_input}").hexdigest()
```

知識庫版本更新後，舊的 `cache_key` 永遠不會被命中（因為版本號不同），舊記錄自然被冷落，不需要主動刪除（節省一次 DELETE 操作）。

## 不做什麼

- 不新增 metadata 資料表
- 不在每次查詢時更新 version（只在 ingest 時更新）
- 不強制清空 prompt_cache（讓舊記錄自然失效）

## 驗收標準

- 執行 `ingest_markdown.py` 後，`MAX(knowledge_version)` 遞增
- 匯入後再次詢問同一個問題，不命中舊快取（確認走 LLM 而非快取）
- 空知識庫時 `get_knowledge_version()` 回傳 0，不拋錯

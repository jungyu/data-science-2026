# Spec-05：Prompt Cache

> **✅ 已實作（commit `44b630d`）**
>
> - 新增 `app/storage/cache_repo.py::CacheRepository`（含 `get` / `set` / `get_knowledge_version`）
> - `ResponseGenerator` 加 `cache_repo: CacheRepository | None`：hit 跳過 LLM、miss 寫入
> - 落實 spec §「快取條件」：只有 `is_rag_required=True` 且 `rag_chunks` 非空才快取
> - cache_key 依 `knowledge_version` 變動自動失配（不需手動清表）
> - 由 `app/dependencies.py::get_cache_repo` 自動注入 generator
> - 驗收測試：`tests/test_prompt_cache.py`（7 cases 含 normalized key、version 失效）

## 背景

`supabase/schema.sql` 已定義 `prompt_cache` 資料表，但整個應用完全沒有程式碼讀寫這張表。對於重複性高的問題（如「什麼是 RAG？」），每次都重新呼叫 LLM 既浪費 token 也增加延遲。

## 目標

在 `ResponseGenerator` 前後加入 cache 查詢與寫入邏輯，相同問題在知識庫版本未變的情況下直接回傳快取回覆。

## Cache Key 設計

```python
cache_key = sha256(
    f"{skill_id}:{knowledge_version}:{normalized_user_input}"
).hexdigest()
```

- `normalized_user_input`：去除頭尾空白、轉小寫
- `knowledge_version`：從 `private_knowledge` 中取最大 `knowledge_version`（或全域版本號）

## 資料流

```
generate_response() 被呼叫
        ↓
cache_repo.get(cache_key)
        ↓
命中 → 直接回傳 cached response_text（跳過 LLM 呼叫）
        ↓
未命中 → LLM 生成 → cache_repo.set(cache_key, response_text, knowledge_version)
        → 回傳回覆
```

## 介面契約

**新增**：`app/storage/cache_repo.py`

```python
class CacheRepository:
    async def get(self, cache_key: str) -> str | None:
        # SELECT response_text FROM prompt_cache WHERE cache_key = ?
        # 回傳 response_text 或 None

    async def set(
        self,
        cache_key: str,
        user_input: str,
        skill_id: str,
        knowledge_version: int,
        response_text: str,
    ) -> None:
        # UPSERT INTO prompt_cache ON CONFLICT(cache_key) DO UPDATE
```

**修改**：`app/generator/responder.py` 的 `ResponseGenerator`
- 新增可選的 `cache_repo: CacheRepository | None = None`
- `generate_response()` 中：先查快取，命中則跳過 LLM，未命中則生成後寫快取

**快取條件**：只有 `is_rag_required=True` 且 `rag_chunks` 非空時才快取（避免快取「知識庫不足」的回覆）

## Knowledge Version 來源

短期：`private_knowledge` 的 `max(knowledge_version)` 值。  
每次 `ingest_markdown.py` 成功匯入後，更新版本號（見 spec-06）。

## 不做什麼

- 不設定 TTL（依知識庫版本失效，不依時間）
- 不快取 `is_rag_required=False` 的回覆（一般聊天不重複性高）
- 不引入 Redis（Supabase 已足夠）

## 驗收標準

- 同一個問題問兩次，第二次 uvicorn log 顯示「cache hit」
- 執行 `ingest_markdown.py` 後，舊快取被新版本失效（需查詢驗證）
- `prompt_cache` 資料表有記錄
- Cohere 或 LLM 呼叫次數在重複問題下明顯減少（可從 OpenAI Dashboard 觀察）

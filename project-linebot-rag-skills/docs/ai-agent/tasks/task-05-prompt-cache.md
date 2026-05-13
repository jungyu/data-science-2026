# task-05：實作 Prompt Cache

> 規格詳見 [spec-05](../specs/spec-05-prompt-cache.md)
>
> **✅ 已完成（commit `44b630d`）** — 實作記錄與驗收測試見 spec-05 頂部「實作狀態」段。
---

請新增 `app/storage/cache_repo.py` 並整合到 `ResponseGenerator`。

## 步驟 1：新增 `app/storage/cache_repo.py`

```python
from __future__ import annotations
import hashlib
from dataclasses import dataclass
from supabase import AsyncClient


def make_cache_key(skill_id: str, knowledge_version: int, user_input: str) -> str:
    normalized = user_input.strip().lower()
    raw = f"{skill_id}:{knowledge_version}:{normalized}"
    return hashlib.sha256(raw.encode()).hexdigest()


@dataclass
class CacheRepository:
    client: AsyncClient

    async def get(self, cache_key: str) -> str | None:
        result = (
            await self.client.table("prompt_cache")
            .select("response_text")
            .eq("cache_key", cache_key)
            .limit(1)
            .execute()
        )
        if result.data:
            return result.data[0]["response_text"]
        return None

    async def set(
        self,
        cache_key: str,
        user_input: str,
        skill_id: str,
        knowledge_version: int,
        response_text: str,
    ) -> None:
        await self.client.table("prompt_cache").upsert(
            {
                "cache_key": cache_key,
                "user_input": user_input,
                "skill_id": skill_id,
                "knowledge_version": knowledge_version,
                "response_text": response_text,
            },
            on_conflict="cache_key",
        ).execute()
```

## 步驟 2：修改 `app/storage/knowledge_repo.py`

新增：
```python
async def get_knowledge_version(self) -> int:
    result = (
        await self.client.table("private_knowledge")
        .select("knowledge_version")
        .order("knowledge_version", desc=True)
        .limit(1)
        .execute()
    )
    return result.data[0]["knowledge_version"] if result.data else 0
```

## 步驟 3：修改 `app/generator/responder.py`

```python
@dataclass
class ResponseGenerator:
    llm: GeneratorLLM | None = None
    line_max_message_chars: int = 4500
    cache_repo: "CacheRepository | None" = None    # 新增

    async def generate_response(self, *, user_input, router_result, skill, rag_chunks, rag_context, recent_history, knowledge_version: int = 0) -> list[str]:
        # 只對 is_rag_required=True 且 rag_chunks 非空時使用快取
        if self.cache_repo and router_result.is_rag_required and rag_chunks:
            cache_key = make_cache_key(router_result.target_skill, knowledge_version, user_input)
            cached = await self.cache_repo.get(cache_key)
            if cached:
                logger.info("cache hit: %s", cache_key[:8])
                return split_for_line(cached, max_chars=self.line_max_message_chars)

        # ... 現有生成邏輯 ...

        # 生成後寫快取
        if self.cache_repo and router_result.is_rag_required and rag_chunks:
            await self.cache_repo.set(cache_key, user_input, router_result.target_skill, knowledge_version, response_text)

        return split_for_line(response_text, ...)
```

## 步驟 4：修改 `app/dependencies.py`

```python
cache_repo = CacheRepository(client=supabase_client)
responder = ResponseGenerator(llm=..., cache_repo=cache_repo)
```

並在 `process_text_event` 中，retrieve 後取得 `knowledge_version` 傳入 `generate_response`。

## 請輸出

1. `app/storage/cache_repo.py` 完整程式碼
2. 修改後的 `app/storage/knowledge_repo.py`（加入 `get_knowledge_version`）
3. 修改後的 `app/generator/responder.py`
4. 修改後的 `app/dependencies.py`
5. 修改後的 `app/line/webhook.py`（`process_text_event` 取得並傳遞 `knowledge_version`）
6. 測試：cache hit / miss / 寫入的完整測試

## 驗收指令

```bash
pytest tests/ -v
# 問同一個問題兩次，第二次 log 顯示 "cache hit"
```

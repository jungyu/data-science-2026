# Ch 03：Embed + 存入

> 核心檔案：[`app/rag/embedder.py`](../../app/rag/embedder.py)、
> [`app/ai/providers/openai_provider.py`](../../app/ai/providers/openai_provider.py)、
> [`app/storage/stores/supabase_store.py`](../../app/storage/stores/supabase_store.py)

---

## 3-1  Embedder：文字 → 向量

專案定義了一個 Protocol（[`app/rag/embedder.py`](../../app/rag/embedder.py)）：

```python
class EmbeddingProvider(Protocol):
    async def embed_query(self, text: str) -> list[float]:
        ...
```

只有一個方法：輸入文字，輸出 1536 個浮點數的清單。

**真實實作** 在 [`app/ai/providers/openai_provider.py` 第 78–103 行](../../app/ai/providers/openai_provider.py)：

```python
class OpenAIEmbedder:
    async def embed_query(self, text: str) -> list[float]:
        response = await self._client.embeddings.create(
            model=self._model,         # "text-embedding-3-small"
            input=text.strip(),
        )
        return list(response.data[0].embedding)   # 1536 個 float
```

---

## 3-2  親眼看一次向量

用 Python 直接跑（不需要啟動 server）：

```python
# 在專案根目錄執行：python -c "..."
import asyncio
from app.config import Settings
from app.ai.providers.openai_provider import OpenAIEmbedder

async def main():
    embedder = OpenAIEmbedder(Settings())
    vec = await embedder.embed_query("Next.js hydration error")
    print(f"維度：{len(vec)}")          # 1536
    print(f"前 5 個值：{vec[:5]}")
    print(f"最大值：{max(vec):.4f}")
    print(f"最小值：{min(vec):.4f}")

asyncio.run(main())
```

預期輸出：
```
維度：1536
前 5 個值：[0.0213, -0.0451, 0.1034, -0.0782, 0.0561]
最大值：0.1523
最小值：-0.1201
```

> 每次呼叫相同文字，輸出向量**完全一樣**（embedding 是確定性的）。

---

## 3-3  KnowledgeChunkInsert：存入前要準備什麼

[`app/storage/knowledge_store.py` 第 25–44 行](../../app/storage/knowledge_store.py)：

```python
class KnowledgeChunkInsert(BaseModel):
    id:           str         # deterministic ID，格式："{source_id}#p{page}#c{chunk_idx}"
    content:      str         # chunk 的原始文字
    category:     str         # 必須和 skill 的 rag_categories 一致
    embedding:    list[float] # embed_query 的輸出
    title:        str | None
    tags:         list[str]
    metadata:     dict        # page_number / source_url 等
    content_hash: str         # SHA-256 前 16 碼，去重用
    source_id:    str | None
    source_type:  str         # "markdown" | "pdf" | "csv" | "web"
```

---

## 3-4  手動寫入一個 chunk（完整範例）

```python
# scripts/demo_manual_upsert.py（你可以自己建這個檔案試試）
import asyncio, hashlib
from app.config import Settings
from app.ai.providers.openai_provider import OpenAIEmbedder
from app.storage.supabase_client import get_supabase_client, SupabaseRestClient
from app.storage.knowledge_repo import KnowledgeRepository
from app.storage.stores.supabase_store import SupabaseStore
from app.storage.knowledge_store import KnowledgeChunkInsert

async def main():
    settings = Settings()
    embedder = OpenAIEmbedder(settings)
    client   = SupabaseRestClient(settings)
    repo     = KnowledgeRepository(client)
    store    = SupabaseStore(client=client, repo=repo)

    text = "Next.js App Router 的 hydration error 通常發生在 Server Component 和 Client Component 的邊界。"

    # Step 1：把文字變成向量
    vec = await embedder.embed_query(text)

    # Step 2：準備寫入資料
    content_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
    chunk = KnowledgeChunkInsert(
        id           = f"demo#p1#c1",
        content      = text,
        category     = "nextjs",       # 對應 skills/ 裡的 rag_categories
        embedding    = vec,
        title        = "手動示範",
        tags         = ["nextjs", "hydration"],
        metadata     = {"source_url": "https://example.com", "page_number": 1},
        content_hash = content_hash,
        source_id    = "demo",
        source_type  = "markdown",
    )

    # Step 3：存入 Supabase
    count = await store.upsert([chunk])
    print(f"✅ 存入 {count} 個 chunk")

asyncio.run(main())
```

---

## 3-5  確認已存入

存完後，在 Supabase Dashboard 跑這個 SQL：

```sql
SELECT id, title, category, length(content) AS chars,
       metadata->>'source_url' AS source_url
FROM private_knowledge
WHERE category = 'nextjs'
ORDER BY created_at DESC
LIMIT 5;
```

或用 Python 查：

```python
rows = await client.select("private_knowledge", {
    "category": "eq.nextjs",
    "order": "created_at.desc",
    "limit": "5",
    "select": "id,title,category,created_at",
})
for r in rows:
    print(r)
```

---

## 🎯 本章里程碑

```bash
python -c "
import asyncio
from app.config import Settings
from app.ai.providers.openai_provider import OpenAIEmbedder
async def main():
    vec = await OpenAIEmbedder(Settings()).embed_query('test')
    print(f'OK: {len(vec)} dims')
asyncio.run(main())
"
# 輸出：OK: 1536 dims
```

下一章 → [Ch 04：第一次語意查詢](ch04-first-search.md)

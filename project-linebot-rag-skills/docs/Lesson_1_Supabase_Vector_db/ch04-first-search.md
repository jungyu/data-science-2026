# Ch 04：第一次語意查詢

> 核心檔案：[`supabase/functions.sql`](../../supabase/functions.sql)、
> [`app/storage/stores/supabase_store.py`](../../app/storage/stores/supabase_store.py)

---

## 4-1  `match_private_knowledge`：不只是向量搜尋

[`supabase/functions.sql`](../../supabase/functions.sql) 定義的這個 RPC 函式，同時跑兩條搜尋再合併：

```sql
-- 第 19–27 行：向量搜尋（找語意接近的）
with vector_matches as (
  select pk.id,
         1 - (pk.embedding <=> query_embedding) as vector_score,
         row_number() over (order by pk.embedding <=> query_embedding) as vector_rank
  from private_knowledge pk
  where pk.embedding is not null
    and (category_filter is null or pk.category = any(category_filter))
  ...
),

-- 第 29–39 行：關鍵字搜尋（找字面符合的）
keyword_matches as (
  select pk.id,
         ts_rank(pk.search_vector, plainto_tsquery('simple', query_text)) as keyword_score,
         row_number() over (...) as keyword_rank
  from private_knowledge pk
  where pk.search_vector @@ plainto_tsquery('simple', query_text)
  ...
),

-- 第 41–57 行：RRF 融合（排名比分數更穩定）
fused as (
  select ...,
         (
           coalesce(1.0 / (60 + vm.vector_rank), 0) +   -- 向量排名貢獻
           coalesce(1.0 / (60 + km.keyword_rank), 0)    -- 關鍵字排名貢獻
         ) as combined_score
  ...
)
```

**為什麼不只用向量分數直接排序？**

```
純向量分數的問題：
  文件 A：vector_score = 0.87（某段和 query 很像）
  文件 B：vector_score = 0.85（另一段和 query 很像）

  但文件 B 同時也在關鍵字搜尋裡排第 2
  → B 更值得信任（兩種方法都認為它好）

RRF 的做法：
  文件 B：1/(60+2) + 1/(60+2) = 0.0323   ← 兩邊都命中，加分
  文件 A：1/(60+1) + 0        = 0.0164   ← 只有向量命中
  → B 排前面
```

---

## 4-2  Python 裸查詢：10 行看到結果

```python
# 直接在 REPL 或腳本執行，不需要啟動 server
import asyncio
from app.config import Settings
from app.ai.providers.openai_provider import OpenAIEmbedder
from app.storage.supabase_client import SupabaseRestClient
from app.storage.knowledge_repo import KnowledgeRepository
from app.storage.stores.supabase_store import SupabaseStore
from app.storage.knowledge_store import SearchFilters

async def search(query: str, category: str, top_k: int = 5):
    settings = Settings()
    embedder = OpenAIEmbedder(settings)
    client   = SupabaseRestClient(settings)
    store    = SupabaseStore(client=client, repo=KnowledgeRepository(client))

    vec    = await embedder.embed_query(query)
    chunks = await store.search(
        query_embedding = vec,
        query_text      = query,
        filters         = SearchFilters(categories=[category]),
        top_k           = top_k,
    )

    for i, c in enumerate(chunks, 1):
        print(f"\n[{i}] score={c.combined_score:.4f}  id={c.id}")
        print(f"    {c.content[:120]}...")

asyncio.run(search("hydration error 怎麼修", "nextjs"))
```

預期輸出（知識庫有相關 chunk 的情況）：
```
[1] score=0.0328  id=nextjs.org__docs__app#p1#c3
    App Router 的 Client Component 在初次渲染時若 server/client HTML 不一致
    會觸發 hydration mismatch。常見原因：useEffect 裡讀了 window/document...

[2] score=0.0241  id=nextjs.org__docs__app#p2#c1
    Next.js 14 引入 Server Components 後，hydration 的邊界由 "use client"
    指令決定。沒有標記的 component 預設為 server-side...
```

---

## 4-3  `category` 很重要：搜錯了什麼都找不到

```python
# 這樣找不到任何東西（category 不對）
chunks = await store.search(
    query_embedding = vec,
    query_text      = "hydration",
    filters         = SearchFilters(categories=["javascript"]),   # ← 錯了
    top_k           = 5,
)
print(len(chunks))   # 0

# 要用 skill 裡設定的同一個 category
filters = SearchFilters(categories=["nextjs"])   # ← 對應 skills/ YAML 裡的 rag_categories
```

**確認你的知識庫用哪個 category**：

```bash
python -c "
import asyncio
from app.config import Settings
from app.storage.supabase_client import SupabaseRestClient

async def main():
    client = SupabaseRestClient(Settings())
    rows = await client.select('private_knowledge', {
        'select': 'category',
    })
    cats = sorted({r['category'] for r in rows})
    for c in cats:
        print(c)
asyncio.run(main())
"
```

---

## 4-4  對比：向量搜尋 vs SQL LIKE

同一個問題，兩種方式：

```python
# 方式 A：SQL LIKE（在 Supabase Dashboard 跑）
SELECT id, content
FROM private_knowledge
WHERE content LIKE '%hydration%'
  AND category = 'nextjs'
LIMIT 5;

# 方式 B：向量搜尋（Python）
chunks = await store.search(
    query_embedding=await embedder.embed_query("hydration 初次渲染失敗"),
    query_text="hydration 初次渲染失敗",
    filters=SearchFilters(categories=["nextjs"]),
    top_k=5,
)
```

**問題改成中文，或換個說法試試**：

```python
# 這些查詢的語意相同，向量搜尋都找得到，LIKE 只找到有字面符合的
queries = [
    "hydration error 怎麼修",
    "水合錯誤",                          # LIKE 找不到，向量搜尋找得到
    "初次渲染 HTML 不一致",              # LIKE 找不到，向量搜尋找得到
    "Client Server Component mismatch",  # 換個說法
]
```

---

## 🎯 本章里程碑

```
問三個語意相似但字面不同的問題：
  - 英文版
  - 中文版
  - 換個說法的版本

三個都能找到相同的 top chunk。
把結果記在筆記裡，這是你第一次看到語意搜尋的效果。
```

---

上一章 → [Ch 03：Embed + 存入](ch03-embed-and-store.md)

完成 Lesson 1 → 進入 [Lesson 2：Playwright 到 Vector DB](../Lesson_2_Playwright_to_Vector_db/README.md)

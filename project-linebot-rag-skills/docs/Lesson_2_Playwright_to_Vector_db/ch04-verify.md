# Ch 04：驗證資料——看見你的 chunk

> 在進入 LangGraph 之前，先確認「資料進去了，而且能找到」。

---

## 4-1  快速確認：chunk 數量

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
    from collections import Counter
    for cat, count in Counter(r['category'] for r in rows).most_common():
        print(f'  {cat}: {count} chunks')
asyncio.run(main())
"
```

預期輸出：
```
  nextjs: 19 chunks
  react: 8 chunks
```

---

## 4-2  實際查詢：連 LangGraph 都不用

這是 Lesson 1 Ch04 的查詢腳本，在這裡用真實資料跑：

```python
import asyncio
from app.config import Settings
from app.ai.providers.openai_provider import OpenAIEmbedder
from app.storage.supabase_client import SupabaseRestClient
from app.storage.knowledge_repo import KnowledgeRepository
from app.storage.stores.supabase_store import SupabaseStore
from app.storage.knowledge_store import SearchFilters

async def search(query: str, category: str, top_k: int = 3):
    settings = Settings()
    store    = SupabaseStore(
        client=SupabaseRestClient(settings),
        repo=KnowledgeRepository(SupabaseRestClient(settings)),
    )
    vec    = await OpenAIEmbedder(settings).embed_query(query)
    chunks = await store.search(
        query_embedding=vec,
        query_text=query,
        filters=SearchFilters(categories=[category]),
        top_k=top_k,
    )
    for i, c in enumerate(chunks, 1):
        print(f"\n[{i}] score={c.combined_score:.4f}")
        print(f"    id:      {c.id}")
        print(f"    title:   {c.title}")
        print(f"    preview: {c.content[:100]}...")

asyncio.run(search("App Router 怎麼定義路由？", "nextjs"))
```

---

## 4-3  三個驗證問題

用這三個問題確認你的知識庫品質：

**問題 1：知識庫涵蓋的標準問題**
```python
asyncio.run(search("你的領域的標準 FAQ 問題", "your_category"))
# 期望：top-1 chunk 的 content 和答案有關
```

**問題 2：換個說法**
```python
asyncio.run(search("同一件事但換個說法問", "your_category"))
# 期望：找到的 chunk 和問題 1 一樣（驗證語意搜尋有效）
```

**問題 3：知識庫沒有的問題**
```python
asyncio.run(search("你知識庫完全沒有的話題", "your_category"))
# 期望：combined_score 很低（< 0.4），或者 0 個結果
# 這個 score 的門檻會在 Lesson 3 Ch03 用 Sufficiency Check 把關
```

---

## 4-4  讀懂分數

```
combined_score > 0.06   → 兩種搜尋都命中，非常相關
combined_score 0.03–0.06 → 一種搜尋命中，大致相關
combined_score < 0.02   → 只有很弱的命中，可能不相關
```

實際案例：

```
查詢：「App Router 的 Layouts 怎麼用？」

[1] score=0.0841  ← 向量 rank 1 + 關鍵字 rank 1，雙重命中
    id: nextjs.org__docs__app#px#c4
    preview: layout.tsx 用來定義跨頁面共用的 UI...

[2] score=0.0328  ← 向量 rank 2，關鍵字沒有命中
    id: nextjs.org__docs__routing#px#c2
    preview: 每個資料夾對應一個 URL segment...

[3] score=0.0161  ← 只有關鍵字命中（"layout" 出現過）
    id: nextjs.org__docs__rendering#px#c1
    preview: Server Components 在初次 render 時...
```

---

## 4-5  常見問題排查

**Q：chunks = 0，什麼都找不到**

```bash
# 先確認 category 名稱對不對
python -c "
import asyncio
from app.config import Settings
from app.storage.supabase_client import SupabaseRestClient
async def main():
    rows = await SupabaseRestClient(Settings()).select(
        'private_knowledge', {'select': 'category,source_id', 'limit': '5'})
    for r in rows: print(r)
asyncio.run(main())
"
# 看輸出的 category 是什麼，要和你的 search() 裡的 categories 一樣
```

**Q：找到的 chunk content 有很多 nav/footer 的垃圾文字**

```python
# 回去 site_rules.py 加 remove_selectors
"your-site.com": {
    "main_selector": "main",
    "remove_selectors": ["nav", "footer", ".sidebar", "#cookie-banner"],
    ...
}
# 然後重新爬 + 重新 ingest
```

**Q：combined_score 都很低（< 0.02），即使是應該相關的問題**

可能原因：
1. Chunk 太長，語意被稀釋 → 把 `max_chars` 從 1200 降到 600
2. 知識庫的語言和查詢語言不同（知識庫英文，查詢中文）→ 設 `SUFFICIENCY_MIN_FEATURE_OVERLAP=0`（Lesson 3 會說）
3. `category` filter 太嚴格 → 先試試不加 filter（`filters=None`）確認向量有進去

---

## 🎯 Lesson 2 里程碑

```
python -c "
import asyncio
from app.config import Settings
...（你的 search 腳本）
asyncio.run(search('你的領域最常見的問題', 'your_category'))
"

top-1 chunk 的 content 和你的問題相關。
```

恭喜，你的知識庫有效了。
進入 [Lesson 3](../Lesson_3_LangGraph_RAG/README.md)，學怎麼把這個搜尋接進 AI bot。

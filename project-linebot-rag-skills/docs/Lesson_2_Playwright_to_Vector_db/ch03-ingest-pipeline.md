# Ch 03：IngestionPipeline 全流程

> 核心檔案：[`app/ingest/pipeline.py`](../../app/ingest/pipeline.py)、
> [`scripts/ingest.py`](../../scripts/ingest.py)

---

## 3-1  Pipeline 做什麼

```
Ingester.yield_documents()
    ↓ Document（含 sections）
for each section:
    Chunker.chunk(section.text)
        ↓ list[str]
    for each chunk:
        embedder.embed_query(chunk)
            ↓ list[float]（1536 維）
        KnowledgeChunkInsert（組好的物件）
store.upsert(batch)
    ↓
Supabase private_knowledge 表
```

四個步驟，一個 `pipeline.run(ingester)` 呼叫全部搞定。

---

## 3-2  `IngestionPipeline.run()` 原始碼對照

[`app/ingest/pipeline.py` 第 77–98 行](../../app/ingest/pipeline.py)：

```python
async def run(self, ingester: Ingester) -> IngestStats:
    stats = IngestStats()
    async for doc in ingester.yield_documents():          # ← 每個 Document

        # 增量更新：hash 沒變就跳過（不重新 embed）
        if doc.content_hash:
            stored = await self._store.source_hash(doc.source_id)
            if stored == doc.content_hash:
                stats.unchanged += 1
                continue

        chunker = self._chunker_for(doc)                  # ← 依 source_type 自動選
        inserts = []
        chunk_idx = 0
        for section in doc.sections:
            for chunk in chunker.chunk(section.text):     # ← 切 chunk
                chunk_idx += 1
                embedding = await self._embedder.embed_query(chunk)  # ← embed
                inserts.append(
                    self._build_chunk_insert(doc, section, chunk, chunk_idx, embedding)
                )

        if inserts:
            await self._store.upsert(inserts)             # ← 批量存入
            stats.docs += 1
            stats.chunks += len(inserts)
```

**chunk ID 的格式**（[`pipeline.py` 第 53–55 行](../../app/ingest/pipeline.py)）：

```python
page_part = section.page_number if section.page_number is not None else "x"
chunk_id  = f"{doc.source_id}#p{page_part}#c{chunk_index}"
```

例如：
```
"https://nextjs.org/docs/app#px#c3"   ← 網頁第 3 個 chunk
"drug-manual.pdf#p12#c2"              ← PDF 第 12 頁第 2 個 chunk
"drugs.csv#px#c45"                    ← CSV 第 45 列
```

---

## 3-3  CLI 指令：`scripts/ingest.py`

最常用的幾個情境：

```bash
# Markdown 目錄（Ch01 兩階段模式的第二步）
python scripts/ingest.py \
  --source docs/RAG/crawled/nextjs/ \
  --type   markdown \
  --category nextjs

# 單一 PDF
python scripts/ingest.py \
  --source docs/RAG/drug-manual.pdf \
  --type   pdf \
  --category drug_info

# CSV（需要指定哪些欄是 text）
python scripts/ingest.py \
  --source docs/RAG/drug-interactions.csv \
  --type   csv \
  --category drug_interaction \
  --text-columns "drug_a,drug_b,interaction_description"

# 直接從 URL 爬（一步到位）
python scripts/ingest.py \
  --source https://nextjs.org/docs/app \
  --type   web \
  --category nextjs
```

執行中的輸出：
```
[ingest] source=docs/RAG/crawled/nextjs/  type=markdown  category=nextjs
[1/5] nextjs_docs_app.md → 3 chunks  (embed: 3 calls)
[2/5] nextjs_docs_routing.md → 5 chunks  (embed: 5 calls)
[3/5] nextjs_docs_data_fetching.md → 4 chunks  (embed: 4 calls)
[4/5] nextjs_docs_rendering.md → 4 chunks  (embed: 4 calls)
[5/5] nextjs_docs_caching.md → 3 chunks  (embed: 3 calls)
✅ Done: 5 docs, 19 chunks, 0 skipped, 0 unchanged
   Cost: ~$0.0004 (19 × text-embedding-3-small)
```

---

## 3-4  增量更新：不重複 embed

重新跑 ingest 時，`pipeline.py` 會先查 Supabase 這個 source 的 `content_hash`（[第 81–85 行](../../app/ingest/pipeline.py)）：

```python
stored = await self._store.source_hash(doc.source_id)
if stored == doc.content_hash:
    stats.unchanged += 1
    continue   # ← 跳過，不重新 embed
```

實際效果：
```
第一次 ingest（5 個文件）：
  ✅ Done: 5 docs, 19 chunks, 0 skipped, 0 unchanged
  Cost: ~$0.0004

第二次 ingest（文件沒有改變）：
  ✅ Done: 0 docs, 0 chunks, 0 skipped, 5 unchanged
  Cost: $0.0000   ← 完全不花錢

第三次 ingest（其中 1 個文件更新了）：
  ✅ Done: 1 docs, 4 chunks, 0 skipped, 4 unchanged
  Cost: ~$0.00008   ← 只 embed 改變的那份
```

---

## 3-5  完整 Python 範例（不用 CLI）

如果你想在自己的腳本裡直接控制 pipeline：

```python
import asyncio
from app.config import Settings
from app.ai.providers.openai_provider import OpenAIEmbedder
from app.storage.supabase_client import SupabaseRestClient
from app.storage.knowledge_repo import KnowledgeRepository
from app.storage.stores.supabase_store import SupabaseStore
from app.ingest.pipeline import IngestionPipeline
from app.ingest.ingesters.web import WebIngester
from scripts.site_rules import rule_for

async def main():
    settings = Settings()
    embedder = OpenAIEmbedder(settings)
    client   = SupabaseRestClient(settings)
    store    = SupabaseStore(client=client, repo=KnowledgeRepository(client))

    pipeline = IngestionPipeline(embedder=embedder, store=store)

    ingester = WebIngester(
        urls=[
            "https://nextjs.org/docs/app",
            "https://nextjs.org/docs/app/building-your-application/routing",
        ],
        category="nextjs",
        get_rule=rule_for,      # 套用 site_rules.py
        concurrency=2,          # 同時最多 2 個 browser context
        delay=1.0,              # 每頁爬完等 1 秒（遵守禮儀）
    )

    stats = await pipeline.run(ingester)
    print(f"docs={stats.docs}  chunks={stats.chunks}  unchanged={stats.unchanged}")

asyncio.run(main())
```

---

## ✏️ 本章任務

1. 對 Ch01 爬到的 Markdown 目錄跑 `scripts/ingest.py --type markdown`
2. 確認輸出有 `chunks > 0`
3. 改動其中一個 `.md` 檔（加一行文字），重新跑 ingest，確認只有這一份重新 embed

下一章 → [Ch 04：驗證資料](ch04-verify.md)

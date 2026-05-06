# task-24：Knowledge Store Adapter

> 規格詳見 [spec-24](../specs/spec-24-knowledge-store-adapter.md)

---

把 vector store 抽成 Protocol；提供 Supabase + sqlite-vec + Pinecone 三實作。學生不需要 Supabase 帳號就能跑通三變體。

## 前置

- task-12 ~ task-19 完成
- 與 task-23 互相獨立（兩個都做時建議先完成 task-23 再做 task-24）

## 前置安裝

`pyproject.toml`：

```toml
dependencies = [
  ...
  "sqlite-vec>=0.1",
]

[project.optional-dependencies]
pinecone = ["pinecone-client>=4.0"]
```

## 步驟 1：定義 Protocol

新增 `app/storage/knowledge_store.py`：

```python
from __future__ import annotations

from datetime import datetime
from typing import Protocol

from pydantic import BaseModel

from app.rag.schemas import KnowledgeChunk


class SearchFilters(BaseModel):
    categories: list[str] | None = None
    tags: list[str] | None = None
    after: datetime | None = None
    metadata_match: dict | None = None
    tenant_id: str | None = None


class KnowledgeChunkInsert(BaseModel):
    id: str
    content: str
    category: str
    embedding: list[float]
    title: str | None = None
    tags: list[str] = []
    metadata: dict = {}
    content_hash: str
    source_id: str | None = None
    source_type: str = "markdown"


class KnowledgeStore(Protocol):
    async def search(
        self,
        *,
        query_embedding: list[float],
        query_text: str | None = None,
        filters: SearchFilters | None = None,
        top_k: int = 8,
    ) -> list[KnowledgeChunk]: ...

    async def upsert(self, chunks: list[KnowledgeChunkInsert]) -> int: ...

    async def delete_by_source(self, source_id: str) -> int: ...

    async def health_check(self) -> bool: ...
```

## 步驟 2：SupabaseStore（既有路徑包裝）

新增 `app/storage/stores/__init__.py`、`app/storage/stores/supabase_store.py`：

```python
from __future__ import annotations

from app.storage.knowledge_repo import KnowledgeRepository
from app.storage.knowledge_store import KnowledgeChunkInsert, KnowledgeStore, SearchFilters
from app.storage.supabase_client import SupabaseRestClient
from app.rag.schemas import KnowledgeChunk


class SupabaseStore:
    name = "supabase"

    def __init__(self, client: SupabaseRestClient, repo: KnowledgeRepository) -> None:
        self._client = client
        self._repo = repo

    async def search(
        self, *, query_embedding, query_text=None, filters=None, top_k=8
    ) -> list[KnowledgeChunk]:
        filters = filters or SearchFilters()
        return await self._repo.match_private_knowledge(
            query_embedding=query_embedding,
            query_text=query_text or "",
            categories=filters.categories,
            top_k=top_k,
        )

    async def upsert(self, chunks: list[KnowledgeChunkInsert]) -> int:
        rows = [c.model_dump() for c in chunks]
        await self._client.upsert("private_knowledge", rows, on_conflict="content_hash")
        return len(rows)

    async def delete_by_source(self, source_id: str) -> int:
        # 用 client.delete; 若 SupabaseRestClient 沒有 delete API 用 PostgREST patch
        ...

    async def health_check(self) -> bool:
        # 跑一個 select 1
        ...
```

## 步驟 3：SqliteVecStore

新增 `app/storage/stores/sqlite_vec_store.py`：

```python
from __future__ import annotations

import json
import sqlite3

import sqlite_vec

from app.storage.knowledge_store import KnowledgeChunkInsert, SearchFilters
from app.rag.schemas import KnowledgeChunk


class SqliteVecStore:
    name = "sqlite_vec"

    def __init__(self, path: str) -> None:
        self._conn = sqlite3.connect(path)
        self._conn.enable_load_extension(True)
        sqlite_vec.load(self._conn)
        self._init_schema()

    def _init_schema(self):
        self._conn.executescript("""
            create virtual table if not exists private_knowledge using vec0(
              id text primary key,
              embedding float[1536]
            );
            create table if not exists private_knowledge_meta (
              id text primary key,
              content text,
              category text,
              tags text,
              metadata text
            );
        """)

    async def search(
        self, *, query_embedding, query_text=None, filters=None, top_k=8
    ) -> list[KnowledgeChunk]:
        # 純向量 K-NN（不支援 hybrid）
        rows = self._conn.execute("""
            select pk.id, m.content, m.category, m.tags, m.metadata, distance
            from private_knowledge pk
            left join private_knowledge_meta m on m.id = pk.id
            where pk.embedding match ?
            order by distance
            limit ?
        """, (json.dumps(query_embedding), top_k)).fetchall()

        out = []
        for r in rows:
            out.append(KnowledgeChunk(
                id=r[0], content=r[1] or "", category=r[2] or "",
                tags=json.loads(r[3] or "[]"),
                metadata=json.loads(r[4] or "{}"),
                vector_score=1.0 - r[5],
                keyword_score=0.0,
                combined_score=1.0 - r[5],
            ))
        # category filter（純向量 store 在 client 端 filter）
        if filters and filters.categories:
            out = [c for c in out if c.category in filters.categories]
        return out

    async def upsert(self, chunks: list[KnowledgeChunkInsert]) -> int:
        for c in chunks:
            self._conn.execute(
                "insert or replace into private_knowledge (id, embedding) values (?, ?)",
                (c.id, json.dumps(c.embedding))
            )
            self._conn.execute(
                "insert or replace into private_knowledge_meta (id, content, category, tags, metadata) "
                "values (?, ?, ?, ?, ?)",
                (c.id, c.content, c.category, json.dumps(c.tags), json.dumps(c.metadata))
            )
        self._conn.commit()
        return len(chunks)

    async def delete_by_source(self, source_id: str) -> int:
        # 教學版簡化：不實作（學生需要再加）
        return 0

    async def health_check(self) -> bool:
        try:
            self._conn.execute("select 1").fetchone()
            return True
        except Exception:
            return False
```

## 步驟 4：PineconeStore（reference）

新增 `app/storage/stores/pinecone_store.py`：

```python
from __future__ import annotations


class PineconeStore:
    name = "pinecone"

    def __init__(self, api_key: str, index_name: str) -> None:
        from pinecone import Pinecone
        self._client = Pinecone(api_key=api_key)
        self._index = self._client.Index(index_name)

    async def search(
        self, *, query_embedding, query_text=None, filters=None, top_k=8
    ):
        from app.rag.schemas import KnowledgeChunk

        flt = {}
        if filters and filters.categories:
            flt["category"] = {"$in": filters.categories}

        resp = self._index.query(
            vector=query_embedding,
            top_k=top_k,
            include_metadata=True,
            filter=flt or None,
        )
        return [
            KnowledgeChunk(
                id=m.id,
                content=m.metadata.get("content", ""),
                category=m.metadata.get("category", ""),
                metadata=m.metadata,
                vector_score=m.score,
                keyword_score=0.0,
                combined_score=m.score,
            )
            for m in resp.matches
        ]

    async def upsert(self, chunks):
        vectors = [
            {"id": c.id, "values": c.embedding, "metadata": {**c.metadata, "content": c.content, "category": c.category}}
            for c in chunks
        ]
        self._index.upsert(vectors=vectors)
        return len(vectors)

    async def delete_by_source(self, source_id: str):
        self._index.delete(filter={"source_id": source_id})
        return 0  # Pinecone 不回 affected count

    async def health_check(self):
        try:
            self._index.describe_index_stats()
            return True
        except Exception:
            return False
```

## 步驟 5：Store registry + factory

`app/storage/stores/__init__.py`：

```python
from app.config import Settings
from app.storage.knowledge_store import KnowledgeStore


def build_store(settings: Settings) -> KnowledgeStore:
    backend = settings.knowledge_store_backend
    if backend == "supabase":
        from app.storage.stores.supabase_store import SupabaseStore
        from app.dependencies import get_supabase_client, get_knowledge_repo
        return SupabaseStore(get_supabase_client(), get_knowledge_repo())
    if backend == "sqlite_vec":
        from app.storage.stores.sqlite_vec_store import SqliteVecStore
        return SqliteVecStore(settings.sqlite_vec_path)
    if backend == "pinecone":
        from app.storage.stores.pinecone_store import PineconeStore
        return PineconeStore(settings.pinecone_api_key, settings.pinecone_index)
    raise ValueError(f"unknown knowledge_store_backend: {backend}")
```

## 步驟 6：retriever 改吃 Protocol

修改 `app/rag/retriever.py`：

```python
from app.storage.knowledge_store import KnowledgeStore, SearchFilters

@dataclass
class RAGRetriever:
    embedder: EmbeddingProvider
    store: KnowledgeStore                 # 改吃 Protocol
    logs_repo: LogsRepository
    final_context_k: int = 4

    async def retrieve_for_seed(self, seed, *, categories=None, top_k=8):
        try:
            embedding = await self.embedder.embed_query(seed)
            return await self.store.search(
                query_embedding=embedding,
                query_text=seed,
                filters=SearchFilters(categories=categories),
                top_k=top_k,
            )
        except Exception:
            return []

    # retrieve / log_fused_retrieval / build_context 不變
```

## 步驟 7：Settings + DI

修改 `app/config.py`：

```python
knowledge_store_backend: str = "supabase"
sqlite_vec_path: str = ".kb/local.db"
pinecone_api_key: str = ""
pinecone_index: str = "rag-lessons"
```

修改 `app/dependencies.py`：

```python
from app.storage.stores import build_store

@lru_cache(maxsize=1)
def get_knowledge_store():
    return build_store(get_settings())

@lru_cache(maxsize=1)
def get_retriever():
    s = get_settings()
    return RAGRetriever(
        embedder=build_embedder(s),
        store=get_knowledge_store(),
        logs_repo=get_logs_repo(),
        final_context_k=s.final_context_k,
    )
```

## 步驟 8：scripts/ingest_markdown.py 改吃 store

```python
store = build_store(settings)
chunks = [KnowledgeChunkInsert(...) for chunk in chunk_markdown(text)]
await store.upsert(chunks)
```

## 步驟 9：測試

新增 `tests/test_stores/test_sqlite_vec.py`、`test_supabase_store.py`（mock client）、`test_pinecone_store.py`（mock client）：

```python
@pytest.mark.asyncio
async def test_sqlite_vec_roundtrip(tmp_path):
    s = SqliteVecStore(str(tmp_path / "test.db"))
    await s.upsert([
        KnowledgeChunkInsert(
            id="x1", content="hello", category="general",
            embedding=[0.1] * 1536, content_hash="h1",
        ),
    ])
    results = await s.search(query_embedding=[0.1] * 1536, top_k=5)
    assert len(results) == 1
    assert results[0].id == "x1"
```

## 步驟 10：教學配套

新增 `docs/ai-agent/examples/swap-store.md`：學生「換 store」step-by-step（從 supabase 切到 sqlite_vec → 重 ingest → 跑 eval）。

## 請輸出

1. `app/storage/knowledge_store.py`
2. `app/storage/stores/{__init__,supabase_store,sqlite_vec_store,pinecone_store}.py`
3. 修改後的 `app/rag/retriever.py`、`app/dependencies.py`、`app/config.py`
4. 修改後的 `scripts/ingest_markdown.py`
5. `tests/test_stores/`
6. `supabase/sqlite_vec_schema.sql`（若需要 sqlite_vec 補初始化 SQL）
7. `docs/ai-agent/examples/swap-store.md`
8. README 加「離線 demo：用 sqlite_vec」段
9. `pyproject.toml` 加 dep

## 驗收指令

```bash
# 教學版（不需 Supabase）
KNOWLEDGE_STORE_BACKEND=sqlite_vec ./scripts/run_local.sh
python scripts/ingest_markdown.py docs/RAG/*.md --category rag
# 在 LINE 上問問題 → 走 sqlite_vec store

# 既有 Supabase 路徑仍 OK
KNOWLEDGE_STORE_BACKEND=supabase ./scripts/run_local.sh
```

驗收通過條件：

- 三 store 各自單元測試通過
- `KNOWLEDGE_STORE_BACKEND=sqlite_vec` 從 zero（無雲端帳號）跑通三變體 + eval
- 切換 backend 不動 graph 程式
- `app/graph/` 與 `app/rag/` 下 grep 不到 "supabase" / "pinecone" 字串（除 type hint）

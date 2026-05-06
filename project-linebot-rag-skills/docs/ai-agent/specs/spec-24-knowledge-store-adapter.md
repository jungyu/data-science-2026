# Spec-24：Knowledge Store Adapter

## 背景

目前 `RAGRetriever` 直接呼叫 `KnowledgeRepository.match_private_knowledge`（Supabase RPC），介面**不是 Protocol**，無法替換。學生想做下列事都會卡：

| 學生情境 | 卡在哪 |
|---|---|
| 用公司既有的 self-hosted Postgres + pgvector | 要手動移植 RPC `match_private_knowledge` SQL function、欄位名硬編 |
| 用 Pinecone / Weaviate / Qdrant | 整個 retriever 重寫；fusion 邏輯散在 retriever 內難複用 |
| 離線教學 demo（沒 Supabase 帳號）| 沒有 sqlite-vec 替代品 |
| 加 metadata filter（時間、權限、tenant）| RPC 簽章固定 |

`docs/RAG/ch03-vectors-embeddings.md` 對「embedding 與 store 解耦」有著墨，但 codebase 沒落實。本 spec 把 vector store 抽成 Protocol，提供三個實作（Supabase / sqlite-vec / Pinecone），讓「換 store」與「換 embedding model」分屬兩個獨立的 swap point。

借鑑：LangChain VectorStore 介面（簡化版）、project-destiny 的 `bazi.match_knowledge_atoms` RPC 簽章設計。

## 設計

### `KnowledgeStore` Protocol

新增 `app/storage/knowledge_store.py`：

```python
from typing import Protocol

from app.rag.schemas import KnowledgeChunk


class SearchFilters(BaseModel):
    categories: list[str] | None = None
    tags: list[str] | None = None
    after: datetime | None = None              # crawled_at filter
    metadata_match: dict | None = None         # arbitrary jsonb match
    tenant_id: str | None = None               # 預留多租戶


class KnowledgeStore(Protocol):
    """純 vector / hybrid 搜尋層。不負責 chunking、embedding、ingestion。"""

    async def search(
        self,
        *,
        query_embedding: list[float],
        query_text: str | None = None,         # 給 hybrid stores 用
        filters: SearchFilters | None = None,
        top_k: int = 8,
    ) -> list[KnowledgeChunk]: ...

    async def upsert(
        self, chunks: list[KnowledgeChunkInsert]
    ) -> int: ...

    async def delete_by_source(self, source_id: str) -> int: ...

    async def health_check(self) -> bool: ...
```

`query_text` 可選，給支援 hybrid（vector + lexical）的 store 用，像 Supabase RPC；純向量 store（Pinecone / Qdrant）忽略此參數。

### 三個實作

| Store | 模組 | 適用場景 |
|---|---|---|
| `SupabaseStore` | `app/storage/stores/supabase_store.py` | 既有 prod 部署（既有 RPC + tsvector hybrid）|
| `SqliteVecStore` | `app/storage/stores/sqlite_vec_store.py` | 離線教學、CI 測試（零外部依賴）|
| `PineconeStore` | `app/storage/stores/pinecone_store.py` | 生產級 reference（學生看到「商業 vector DB 怎麼接」）|

只有 `SupabaseStore` 支援 hybrid（tsvector）；其他兩個是純向量，只用 `query_embedding`。

### Retriever 改吃 Protocol

修改 `app/rag/retriever.py`：

```python
class RAGRetriever:
    def __init__(
        self,
        embedder: Embedder,
        store: KnowledgeStore,         # 改吃 Protocol
        logs_repo: LogsRepository,
        final_context_k: int,
    ) -> None: ...

    async def retrieve_for_seed(
        self, seed: str, *, categories=None, top_k=8, ...
    ) -> list[KnowledgeChunk]:
        embedding = await self.embedder.embed_query(seed)
        filters = SearchFilters(categories=categories)
        return await self.store.search(
            query_embedding=embedding,
            query_text=seed,
            filters=filters,
            top_k=top_k,
        )
```

舊 `KnowledgeRepository` **不刪**，重新定位為 `SupabaseStore` 內部實作細節。

### Ingest pipeline 改吃 store

修改 `scripts/ingest_markdown.py`：

```python
store: KnowledgeStore = build_store(settings)
await store.upsert(chunks)
```

`build_store(settings)` 在 `app/dependencies.py` 依 `KNOWLEDGE_STORE_BACKEND` env var 選實作：

```bash
KNOWLEDGE_STORE_BACKEND=supabase   # supabase | sqlite_vec | pinecone
SQLITE_VEC_PATH=.kb/local.db
PINECONE_API_KEY=...
PINECONE_INDEX=lessons
```

### SqliteVecStore 教學意義

學生做的第一件事通常是：「我能不能不開 Supabase 帳號就跑通？」

`SqliteVecStore` 用 [sqlite-vec](https://github.com/asg017/sqlite-vec) extension（純檔案）：

- 一份 `.kb/local.db` 即可運作
- 不支援 tsvector hybrid，純向量 search
- 可直接被測試 fixture 載入；單元測試零外部依賴

把它做出來等於送學生一個「不需註冊任何雲端服務也能完整跑通三變體」的入門路徑。

### PineconeStore 的角色

不要求學生實際付費；本 spec 只示範**怎麼接**。提供：

- 完整 `app/storage/stores/pinecone_store.py` 實作
- `tests/test_pinecone_store.py` 用 mock client（不打真 API）
- README 章節「想換 Pinecone：改一行 env、看這個檔」

教學重點：學生看到「Protocol-based design 的好處」具體展現。

### 與 spec-19 / spec-22 的整合

- spec-19 三變體不感知 store 種類
- spec-22 trace 加 `store_backend` 欄位，方便 debug 「為什麼 sqlite_vec 跑得比 Supabase 快/慢」
- spec-20 eval runner 預設用 `SqliteVecStore`（CI 不需 Supabase）

### 不做什麼

- 不做 Weaviate / Qdrant / Milvus（介面有了學生自己加）
- 不做跨 store 的資料同步 / 雙寫（屬部署議題）
- 不做 sharding / replication（生產議題）
- 不做混合排序的 score 校準（fusion 仍在 retriever 層做）

## 介面契約

**新增**：

| 檔案 | 用途 |
|---|---|
| `app/storage/knowledge_store.py` | `KnowledgeStore` Protocol、`SearchFilters` schema |
| `app/storage/stores/__init__.py` | registry：`STORES = {"supabase": SupabaseStore, ...}` |
| `app/storage/stores/supabase_store.py` | 既有 RPC 路徑包裝為 Protocol 實作 |
| `app/storage/stores/sqlite_vec_store.py` | 教學零依賴版 |
| `app/storage/stores/pinecone_store.py` | 生產 reference |

**修改**：

- `app/rag/retriever.py`：constructor 改吃 `KnowledgeStore`
- `app/dependencies.py`：`get_knowledge_store()`、`get_retriever()` 串起來
- `scripts/ingest_markdown.py`：用 `store.upsert` 取代直接 `client.upsert`
- `scripts/crawl_to_markdown.py`：不變（output 仍是檔案）
- `app/storage/knowledge_repo.py`：保留作 `SupabaseStore` 內部使用，不對外 export

**新增 dependency**：

```toml
# 教學版 store
"sqlite-vec>=0.1",
# 生產 reference（optional extra）
[project.optional-dependencies]
pinecone = ["pinecone-client>=4.0"]
```

**Settings 新增**：

```python
knowledge_store_backend: Literal["supabase", "sqlite_vec", "pinecone"] = "supabase"
sqlite_vec_path: str = ".kb/local.db"
pinecone_api_key: str | None = None
pinecone_index: str = "rag-lessons"
```

**Schema 新增（選用）**：

`supabase/sqlite_vec_schema.sql`——sqlite-vec 的本機 schema：

```sql
create virtual table if not exists private_knowledge using vec0(
  id text primary key,
  embedding float[1536]
);

create table if not exists private_knowledge_meta (
  id text primary key,
  content text,
  category text,
  tags text,
  metadata text   -- json 字串
);
```

## 驗收標準

- 切換 `KNOWLEDGE_STORE_BACKEND` 不需改 graph 任何程式
- `KNOWLEDGE_STORE_BACKEND=sqlite_vec` 完整跑通三變體 + eval：**從零到能跑只需要 sqlite-vec 一個 pip install**，零雲端依賴
- `KNOWLEDGE_STORE_BACKEND=supabase` 行為與 spec-23 之前完全等價（同一問題、同一回覆）
- `PineconeStore` 用 mock client 通過單元測試；附完整 setup guide
- 三個 store 在同一個 50 案例的 ingest fixture 上跑 eval，metric 差異符合預期：
  - chunk_recall：Supabase ≥ sqlite_vec（hybrid 優勢）
  - latency：sqlite_vec < Supabase < Pinecone（cold network call）
- `scripts/ingest_markdown.py` 一份呼叫支援三種 store
- 多 store 切換的端對端範例文件 `docs/ai-agent/examples/swap-store.md`
- grep 確認：`app/graph/` 與 `app/rag/` 下不出現 `"supabase"` / `"pinecone"` 字串（除 type hint 外）

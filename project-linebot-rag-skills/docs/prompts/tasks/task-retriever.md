# task-retriever · RAG Retriever 實作

> **使用時機**：改善檢索邏輯、新增 category、或從零實作 RAG 模組時使用。

---

請在 `app/rag/` 目錄下實作完整的 RAG 知識庫檢索模組。

## 目標目錄結構

```
app/rag/
├── embedder.py    # EmbeddingProvider protocol + OpenAIEmbedder
├── retriever.py   # RAGRetriever dataclass
├── reranker.py    # select_top_chunks()
├── chunker.py     # Markdown chunker
└── schemas.py     # KnowledgeChunk, RetrievalLogRecord
```

## schemas.py 規格

```python
@dataclass
class KnowledgeChunk:
    id: uuid.UUID
    title: str | None
    content: str
    category: str
    metadata: dict
    vector_score: float
    keyword_score: float
    combined_score: float
```

## embedder.py 規格

```python
class EmbeddingProvider(Protocol):
    async def embed_query(self, text: str) -> list[float]: ...

class OpenAIEmbedder:
    # 使用 client.embeddings.create()（不是 Responses API）
    # model = settings.embedding_model（預設 text-embedding-3-small）
    # 回傳 list[float]，長度 1536
```

## retriever.py 規格

```python
@dataclass
class RAGRetriever:
    embedder: EmbeddingProvider
    knowledge_repo: KnowledgeRepository
    logs_repo: LogsRepository
    final_context_k: int = 4

    async def retrieve(
        self,
        query: str,
        *,
        categories: list[str] | None = None,   # 對應 ingest --category 的值
        top_k: int = 8,                         # 初始候選數，傳入 RPC
        line_user_id: str | None = None,
        skill_id: str | None = None,
    ) -> list[KnowledgeChunk]:
        # 1. embed(query)
        # 2. knowledge_repo.match_private_knowledge(embedding, query, categories, top_k)
        # 3. select_top_chunks(chunks, final_context_k)
        # 4. logs_repo.log_retrieval()
        # 5. 任何步驟失敗 → return []（不拋錯，讓主流程繼續）

    def build_context(self, chunks: list[KnowledgeChunk]) -> str:
        # 格式：[1] 標題\nCategory: xxx\n內容\n\n[2] ...
        # 上限 final_context_k 個 chunks
```

**關鍵設計決策：**

- `top_k`（8）是傳入 Supabase RPC 的候選數，`final_context_k`（4）是最終進入 Generator 的數
- `categories=None` 表示不過濾，搜尋全庫
- `categories` 的值必須與 `ingest_markdown.py --category` 使用的值一致，否則靜默找不到資料

## Supabase RPC 介面（`match_private_knowledge`）

```sql
-- 在 supabase/functions.sql 已定義
-- 接收: query_embedding vector(1536), query_text text, match_count int, category_filter text[]
-- 回傳: id, title, content, category, metadata, vector_score, keyword_score, combined_score
-- RRF 計算: 1/(60+vector_rank) + 1/(60+keyword_rank)
```

Python 呼叫方式：

```python
result = await supabase.rpc("match_private_knowledge", {
    "query_embedding": embedding,
    "query_text": query,
    "match_count": top_k,
    "category_filter": categories,
}).execute()
```

## 請輸出

1. `schemas.py` 完整程式碼
2. `embedder.py` 完整程式碼（含 Protocol + OpenAIEmbedder）
3. `retriever.py` 完整程式碼
4. `reranker.py`：`select_top_chunks(chunks, k)` 按 `combined_score` 降序取前 k 筆
5. `chunker.py`：按 Markdown heading 切割，每個 chunk 保留前一層 heading 作為 title
6. `tests/test_retriever.py` 測試案例，覆蓋：
   - 正常檢索回傳 chunks
   - categories 找不到資料回傳空 list
   - embed 失敗回傳空 list（不拋錯）
   - build_context 格式正確

## 驗收指令

```bash
pytest tests/test_retriever.py -v

# 實際匯入資料驗證
.venv/bin/python scripts/ingest_markdown.py docs/RAG/*.md --category rag
# 期望：Ingested N chunks，無 400 error
```

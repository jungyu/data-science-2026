# task-04：實作 Cross-Encoder Rerank（Cohere）

> 規格詳見 [spec-04](../specs/spec-04-cross-encoder-rerank.md)
>
> **✅ 已完成（commit `2387555`）** — 實作記錄與驗收測試見 spec-04 頂部「實作狀態」段。
---

請修改 `app/rag/reranker.py`，加入 Cohere Rerank API 整合，並讓 `RAGRetriever` 可選用。

## 步驟 1：安裝依賴

在 `pyproject.toml` 的 `[project.dependencies]` 加入：

```toml
"cohere>=5.0",
```

## 步驟 2：修改 `app/config.py`

```python
cohere_api_key: str = ""
cohere_rerank_model: str = "rerank-v3.5"
```

## 步驟 3：修改 `app/rag/reranker.py`

```python
import cohere

class CohereReranker:
    def __init__(self, api_key: str, model: str = "rerank-v3.5") -> None:
        self._client = cohere.AsyncClientV2(api_key)
        self._model = model

    async def rerank(
        self,
        query: str,
        chunks: list[KnowledgeChunk],
        top_k: int,
    ) -> list[KnowledgeChunk]:
        try:
            documents = [chunk.content for chunk in chunks]
            response = await self._client.rerank(
                model=self._model,
                query=query,
                documents=documents,
                top_n=top_k,
            )
            # response.results[i].index 對應原始 chunks 的索引
            reranked = [chunks[r.index] for r in response.results]
            return reranked
        except Exception:
            logger.warning("Cohere rerank failed, falling back to RRF order")
            return sorted(chunks, key=lambda c: c.combined_score, reverse=True)[:top_k]


def select_top_chunks(
    chunks: list[KnowledgeChunk],
    top_k: int,
    reranker: "CohereReranker | None" = None,
    query: str = "",
) -> list[KnowledgeChunk]:
    if reranker is None or not query:
        return sorted(chunks, key=lambda c: c.combined_score, reverse=True)[:top_k]
    # 同步呼叫點注意：caller 需使用 await
    raise RuntimeError("Use async version: await reranker.rerank()")
```

**注意**：`reranker.rerank()` 是 async，需修改 `RAGRetriever.retrieve()` 的呼叫方式。

## 步驟 4：修改 `app/rag/retriever.py`

```python
@dataclass
class RAGRetriever:
    ...
    reranker: CohereReranker | None = None   # 新增

    async def retrieve(self, query, *, categories, top_k, ...) -> list[KnowledgeChunk]:
        ...
        chunks = await self.knowledge_repo.match_private_knowledge(...)
        if self.reranker and query:
            selected = await self.reranker.rerank(query, chunks, self.final_context_k)
        else:
            selected = select_top_chunks(chunks, self.final_context_k)
        ...
```

## 步驟 5：修改 `app/dependencies.py`

```python
if settings.cohere_api_key:
    reranker = CohereReranker(settings.cohere_api_key, settings.cohere_rerank_model)
else:
    reranker = None
retriever = RAGRetriever(..., reranker=reranker)
```

## 請輸出

1. 修改後的 `app/rag/reranker.py`（含 `CohereReranker` 和修改的 `select_top_chunks`）
2. 修改後的 `app/rag/retriever.py`
3. 修改後的 `app/config.py`（加入 cohere 設定）
4. 修改後的 `app/dependencies.py`
5. 修改後的 `pyproject.toml`
6. `.env.example` 新增 `COHERE_API_KEY=`（空值）
7. 測試：`tests/test_retriever.py` 加入 Cohere 失敗時 fallback 到 RRF 的測試

## 驗收指令

```bash
pip install -e ".[dev]"
pytest tests/test_retriever.py -v
# COHERE_API_KEY 未設定時，bot 正常運作
```

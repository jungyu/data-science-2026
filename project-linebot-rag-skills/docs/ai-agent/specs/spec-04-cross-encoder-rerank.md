# Spec-04：Cross-Encoder Rerank

> **✅ 已實作（commit `2387555` 修補 fallback 路徑；rerank 主體在 spec-28）**
>
> - `CohereReranker.rerank()` 包 try/except；API 失敗（超時 / 限流 / 網路）靜默 fallback 回 RRF 排序
> - `make_reranker()` 缺 key 時回 None + warning，**不再 raise**（過去會直接打斷主流程）
> - 驗收測試：`tests/test_reranker.py::test_rerank_api_failure_falls_back_to_rrf` +
>   `test_cohere_missing_api_key_returns_none`

## 背景

`app/rag/reranker.py` 的 `select_top_chunks()` 目前只是依 `combined_score`（RRF 分數）排序取前 k 筆，不是真正的 reranker。RRF 對精確關鍵字召回表現良好，但對於「語意相似但詞彙不同」的問題，排名品質有限。

## 目標

在 RRF 後加入 Cohere Rerank API 作為輕量 cross-encoder，提升 final 4 筆的相關性，**不改變前面的向量/全文檢索邏輯**。

## 架構

```
pgvector 向量搜尋（top 8 * 3 候選）
tsvector 全文搜尋（top 8 * 3 候選）
        ↓
RRF 合併 → top_k=8 候選
        ↓
Cohere Rerank API（query + 8 候選）
        ↓
final_context_k=4 → Generator
```

## 介面契約

**修改**：`app/rag/reranker.py`

```python
class CohereReranker:
    def __init__(self, api_key: str, model: str = "rerank-v3.5") -> None: ...

    async def rerank(
        self,
        query: str,
        chunks: list[KnowledgeChunk],
        top_k: int,
    ) -> list[KnowledgeChunk]:
        # 呼叫 Cohere Rerank API
        # 回傳按 relevance_score 排序的 top_k chunks
        # API 失敗時 fallback 到原 RRF 排序（不拋錯）

def select_top_chunks(
    chunks: list[KnowledgeChunk],
    top_k: int,
    reranker: CohereReranker | None = None,
    query: str = "",
) -> list[KnowledgeChunk]:
    if reranker is None or not query:
        return sorted(chunks, key=lambda c: c.combined_score, reverse=True)[:top_k]
    return await reranker.rerank(query, chunks, top_k)
```

**修改**：`app/rag/retriever.py` 的 `RAGRetriever`
- 接收可選的 `reranker: CohereReranker | None = None`
- 若有 reranker，在 `select_top_chunks` 時傳入 `query`

**新增環境變數**：`COHERE_API_KEY`（可選，未設定則 fallback 到 RRF）

**修改**：`app/config.py`
```python
cohere_api_key: str = ""
cohere_rerank_model: str = "rerank-v3.5"
```

## Fallback 策略

Cohere API 不可用時（無 API key、超時、限流），靜默降回 RRF 排序，不影響主流程，但記入 log。

## 不做什麼

- 不引入本地 cross-encoder 模型（依賴 GPU，不適合輕量部署）
- 不改變 `match_private_knowledge` SQL 函式
- 不改變前段的 embed → RPC 流程

## 驗收標準

- 設定 `COHERE_API_KEY` 後，`retrieval_logs` 中的 chunk 與 query 的相關性主觀提升
- 移除 `COHERE_API_KEY` 或設為空值，bot 仍正常運作（fallback 到 RRF）
- `pytest tests/test_retriever.py` 通過，含 Cohere 失敗的 fallback 測試

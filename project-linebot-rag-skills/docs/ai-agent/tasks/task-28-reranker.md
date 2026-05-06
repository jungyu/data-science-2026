# task-28：Cross-encoder Reranker（Cohere / BGE）

> 規格詳見 [spec-28](../specs/spec-28-reranker.md)

---

本 task 用真正的 cross-encoder 取代現有的 score-sort stub，在 `fuse_node` 後插入 `rerank_node`。

## 前置

- spec-27（hybrid config）已完成
- `rag_chunks` 欄位已存在於 `RAGState`

## 前置安裝

按需安裝（不一定全裝）：

```bash
# Cohere（推薦教學環境）
uv pip install "cohere>=5.0"

# BGE（本地，需 PyTorch）
uv pip install "sentence-transformers>=2.7"
```

`pyproject.toml` 新增 optional dependencies：

```toml
[project.optional-dependencies]
reranker-cohere = ["cohere>=5.0"]
reranker-bge    = ["sentence-transformers>=2.7"]
```

## 步驟 1：Config 新增

`app/config.py`：

```python
RERANKER_ENABLED: bool = Field(default=False, alias="RERANKER_ENABLED")
RERANKER_PROVIDER: Literal["cohere", "bge"] = Field(default="cohere", alias="RERANKER_PROVIDER")
RERANKER_MODEL: str = Field(default="rerank-multilingual-v3.0", alias="RERANKER_MODEL")
RERANKER_TOP_N: int = Field(default=5, alias="RERANKER_TOP_N")
COHERE_API_KEY: str | None = Field(default=None, alias="COHERE_API_KEY")
BGE_RERANKER_MODEL: str = Field(default="BAAI/bge-reranker-base", alias="BGE_RERANKER_MODEL")
```

## 步驟 2：取代 `app/rag/reranker.py`

完整取代現有 stub，實作 `BaseReranker`、`CohereReranker`、`BgeReranker`、`make_reranker()`、`select_top_chunks()`。

詳見 spec-28 § 設計 → 2。

## 步驟 3：新增 `rerank_node`

`app/graph/nodes.py`：

```python
from app.rag.reranker import BaseReranker, select_top_chunks

async def rerank_node(state: RAGState, settings: Settings, reranker: BaseReranker | None) -> dict:
    chunks = state["rag_chunks"]
    query = state["query"]
    top_n = settings.RERANKER_TOP_N

    if reranker is None:
        ranked = select_top_chunks(chunks, top_n)
    else:
        ranked = await reranker.rerank(query, chunks, top_n)

    logger.info("rerank: %d → %d (strategy=%s)",
                len(chunks), len(ranked), "cross-encoder" if reranker else "score-sort")
    return {"rag_chunks": ranked}
```

## 步驟 4：Graph 接線

每個 variant builder：

```python
from app.rag.reranker import make_reranker

reranker = make_reranker(settings)

builder.add_node("rerank", partial(rerank_node, settings=settings, reranker=reranker))

# 修改 edge：fuse → rerank → check_sufficiency
builder.add_edge("fuse", "rerank")
builder.add_edge("rerank", "check_sufficiency")
# 移除原 fuse → check_sufficiency edge
```

## 步驟 5：撰寫測試

新增 `tests/test_reranker.py`：

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.rag.reranker import CohereReranker, BgeReranker, select_top_chunks
from app.rag.schemas import KnowledgeChunk


def make_chunks(n: int) -> list[KnowledgeChunk]:
    return [
        KnowledgeChunk(id=i, content=f"chunk {i}", combined_score=float(i) / n)
        for i in range(n)
    ]


def test_select_top_chunks():
    chunks = make_chunks(10)
    result = select_top_chunks(chunks, 3)
    assert len(result) == 3
    assert result[0].id == 9  # highest score


@pytest.mark.asyncio
async def test_cohere_reranker_mock():
    mock_result = MagicMock()
    mock_result.results = [
        MagicMock(index=2, relevance_score=0.95),
        MagicMock(index=0, relevance_score=0.70),
    ]
    with patch("cohere.AsyncClientV2") as MockCohere:
        instance = MockCohere.return_value
        instance.rerank = AsyncMock(return_value=mock_result)
        reranker = CohereReranker(api_key="test", model="rerank-multilingual-v3.0")
        chunks = make_chunks(5)
        result = await reranker.rerank("test query", chunks, top_n=2)
        assert len(result) == 2
        assert result[0].combined_score == 0.95
```

## 步驟 6：`.env.example` 補充

```dotenv
# Reranker
RERANKER_ENABLED=false
RERANKER_PROVIDER=cohere
RERANKER_MODEL=rerank-multilingual-v3.0
RERANKER_TOP_N=5
COHERE_API_KEY=your_cohere_api_key_here
```

---

## 里程碑 ✅

- [ ] `RERANKER_ENABLED=false`：`rerank_node` 為 score-sort，log 顯示 `strategy=score-sort`
- [ ] `RERANKER_ENABLED=true, RERANKER_PROVIDER=cohere`：log 顯示 `strategy=cross-encoder`
- [ ] Cohere key 未設時啟動拋 `ValueError`
- [ ] `pytest tests/test_reranker.py` 全綠（含 mock test）
- [ ] （可選）`chunk_recall(reranked)` ≥ `chunk_recall(hybrid)` + 3%

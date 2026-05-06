# Spec-28：Cross-encoder Reranker（Cohere / BGE）

## 背景

### 現狀

`app/rag/reranker.py` 的 `select_top_chunks()` 只是對 `combined_score` 做降序排列，不是真正的 cross-encoder reranker。它的問題在於：

- `combined_score` 是向量分數與關鍵字分數的線性加權，**沒有考慮 query 與 chunk 的語意互動**。
- 假命中（看起來像但其實不相關的 chunk）難以被過濾掉。

Cross-encoder reranker 的核心差異：把 `(query, chunk)` 一起送進模型，得到精確的相關度分數。代價是不能 batch embed——必須 query × chunk 配對計算，因此**只用在 Top-K 精排，不用在初始 recall**。

---

## 設計

### 架構位置

```
retrieve_node(s) → fuse_node → [rerank_node] → sufficiency_check / generate
```

`rerank_node` 在 `fuse` 之後、`sufficiency_check` 之前插入。

### 1. Config 新增

`app/config.py`：

```python
RERANKER_ENABLED: bool = Field(default=False, alias="RERANKER_ENABLED")
RERANKER_PROVIDER: Literal["cohere", "bge"] = Field(default="cohere", alias="RERANKER_PROVIDER")
RERANKER_MODEL: str = Field(default="rerank-multilingual-v3.0", alias="RERANKER_MODEL")
RERANKER_TOP_N: int = Field(default=5, alias="RERANKER_TOP_N")
COHERE_API_KEY: str | None = Field(default=None, alias="COHERE_API_KEY")
BGE_RERANKER_MODEL: str = Field(
    default="BAAI/bge-reranker-base", alias="BGE_RERANKER_MODEL"
)
```

### 2. Reranker 類別

新增 `app/rag/reranker.py`（完整取代現有 stub）：

```python
from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod

from app.rag.schemas import KnowledgeChunk


class BaseReranker(ABC):
    @abstractmethod
    async def rerank(self, query: str, chunks: list[KnowledgeChunk], top_n: int) -> list[KnowledgeChunk]:
        """回傳按 rerank 分數降序排列的前 top_n 個 chunk。"""


class CohereReranker(BaseReranker):
    def __init__(self, api_key: str, model: str = "rerank-multilingual-v3.0"):
        import cohere
        self._client = cohere.AsyncClientV2(api_key=api_key)
        self._model = model

    async def rerank(self, query: str, chunks: list[KnowledgeChunk], top_n: int) -> list[KnowledgeChunk]:
        if not chunks:
            return []
        docs = [c.content for c in chunks]
        resp = await self._client.rerank(
            model=self._model,
            query=query,
            documents=docs,
            top_n=min(top_n, len(docs)),
        )
        reranked: list[KnowledgeChunk] = []
        for result in resp.results:
            chunk = chunks[result.index].model_copy()
            chunk.combined_score = result.relevance_score
            reranked.append(chunk)
        return reranked


class BgeReranker(BaseReranker):
    """本地 BGE Reranker（需安裝 sentence-transformers）。"""

    def __init__(self, model_name: str = "BAAI/bge-reranker-base"):
        from sentence_transformers import CrossEncoder
        self._model = CrossEncoder(model_name)

    async def rerank(self, query: str, chunks: list[KnowledgeChunk], top_n: int) -> list[KnowledgeChunk]:
        if not chunks:
            return []
        pairs = [(query, c.content) for c in chunks]
        # CrossEncoder.predict 是同步，用 run_in_executor 避免阻塞事件迴圈
        loop = asyncio.get_event_loop()
        scores: list[float] = await loop.run_in_executor(
            None, self._model.predict, pairs
        )
        ranked = sorted(
            zip(scores, chunks), key=lambda x: x[0], reverse=True
        )
        result = []
        for score, chunk in ranked[:top_n]:
            c = chunk.model_copy()
            c.combined_score = float(score)
            result.append(c)
        return result


def make_reranker(settings) -> BaseReranker | None:
    """Factory：依 config 回傳 reranker 實例，或 None（disabled）。"""
    if not settings.RERANKER_ENABLED:
        return None
    if settings.RERANKER_PROVIDER == "cohere":
        if not settings.COHERE_API_KEY:
            raise ValueError("RERANKER_PROVIDER=cohere 需設定 COHERE_API_KEY")
        return CohereReranker(
            api_key=settings.COHERE_API_KEY,
            model=settings.RERANKER_MODEL,
        )
    if settings.RERANKER_PROVIDER == "bge":
        return BgeReranker(model_name=settings.BGE_RERANKER_MODEL)
    raise ValueError(f"未知 RERANKER_PROVIDER: {settings.RERANKER_PROVIDER}")


# 保留舊函式供向下相容（不開 reranker 時直接用）
def select_top_chunks(chunks: list[KnowledgeChunk], top_n: int) -> list[KnowledgeChunk]:
    return sorted(chunks, key=lambda c: c.combined_score, reverse=True)[:top_n]
```

### 3. `rerank_node` graph node

`app/graph/nodes.py` 新增：

```python
async def rerank_node(state: RAGState, settings: Settings, reranker: BaseReranker | None) -> dict:
    """
    若 reranker 為 None，直接以 combined_score 排序並取 top_n。
    若 reranker 已初始化，呼叫 cross-encoder 精排。
    """
    chunks: list[KnowledgeChunk] = state["rag_chunks"]
    query: str = state["query"]
    top_n: int = settings.RERANKER_TOP_N

    if reranker is None:
        ranked = select_top_chunks(chunks, top_n)
    else:
        ranked = await reranker.rerank(query, chunks, top_n)

    logger.info("rerank: %d → %d chunks (strategy=%s)", len(chunks), len(ranked),
                "cross-encoder" if reranker else "score-sort")
    return {"rag_chunks": ranked}
```

### 4. Graph 接線

在每個 variant builder 中，`fuse_node` 後插入 `rerank_node`：

```python
# 初始化（build 時一次）
reranker = make_reranker(settings)

builder.add_node(
    "rerank",
    partial(rerank_node, settings=settings, reranker=reranker)
)
builder.add_edge("fuse", "rerank")
builder.add_edge("rerank", "check_sufficiency")  # 原本 fuse → check_sufficiency
```

### 5. 依賴安裝

`pyproject.toml`：

```toml
[project.optional-dependencies]
reranker-cohere = ["cohere>=5.0"]
reranker-bge    = ["sentence-transformers>=2.7"]
```

安裝：
```bash
uv pip install ".[reranker-cohere]"   # Cohere
uv pip install ".[reranker-bge]"      # BGE（需 PyTorch）
```

---

## 效能與成本

| Provider | 延遲（估）| 成本 | GPU 需求 |
|----------|---------|------|---------|
| Cohere Rerank API | 200–600ms（網路）| $0.002 / 1K docs | 無 |
| BGE-Reranker-Base | 50–200ms（CPU 本機）| 0（本地）| 無（CPU OK）|
| BGE-Reranker-Large | 100–400ms（CPU 本機）| 0（本地）| 建議 GPU |

教學環境建議用 **Cohere**（零設定、免 GPU），生產若需降低 API cost 可換 **BGE-Base**。

---

## 可換點 / 不可換點

| | 可換 | 不可換 |
|---|---|---|
| Reranker provider | ✅ `RERANKER_PROVIDER` env var | ❌ `rerank()` 介面：`(query, chunks, top_n) → chunks` |
| `RERANKER_TOP_N` | ✅ 可調，建議 3–10 | ❌ 不能大於 `RETRIEVAL_TOP_K`（排序超過候選集沒意義）|
| `RERANKER_ENABLED=false` | ✅ 退化為 score-sort | ❌ graph 結構不變（`rerank_node` 仍在）|

---

## 驗收標準

- `RERANKER_ENABLED=false`：`rerank_node` 直接 score-sort，log 顯示 `strategy=score-sort`
- `RERANKER_ENABLED=true, RERANKER_PROVIDER=cohere`：log 顯示 `strategy=cross-encoder`，輸出 chunk 順序與 score-sort 不同（有精排效果）
- `chunk_recall(reranked)` ≥ `chunk_recall(hybrid)` + 3%（golden set 10 筆以上）
- Cohere API key 未設時啟動拋 `ValueError`（不 silently pass）
- pytest `tests/test_reranker.py`：CohereReranker mock test + BgeReranker unit test 全綠

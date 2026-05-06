# Spec-29：Embedding 模型選型指南

## 背景

知識庫的嵌入品質直接決定向量搜尋的天花板。學生在換領域時常問：「應該繼續用 `text-embedding-ada-002`？還是換成 `text-embedding-3-small`？還是用開源 BGE/E5？」本 spec 提供：

1. **靜態選型矩陣**（定性分析）
2. **Benchmark 腳本**（在自己的知識庫上量化比較）
3. **換模型的操作步驟**（含重新入庫）

---

## 模型比較矩陣

| 模型 | 維度 | 中文支援 | 成本（每 1M tokens）| GPU 需求 | 適用場景 |
|------|------|---------|---------------------|---------|---------|
| `text-embedding-ada-002` | 1536 | 普通 | $0.10 | 無 | 教學預設；英文為主 |
| `text-embedding-3-small` | 1536（可降維）| 良好 | $0.02 | 無 | 換 ada-002 的首選，更便宜更好 |
| `text-embedding-3-large` | 3072 | 良好 | $0.13 | 無 | 高品質英文；成本與 ada-002 接近 |
| `BAAI/bge-m3` | 1024 | 優秀（多語）| $0（本地）| 建議 GPU | 中文為主；多語言知識庫 |
| `intfloat/multilingual-e5-large` | 1024 | 優秀（多語）| $0（本地）| 建議 GPU | 與 BGE-M3 並列，評測各有勝負 |
| `BAAI/bge-small-zh-v1.5` | 512 | 優秀（純中文）| $0（本地）| 無（CPU OK）| 中文輕量化部署 |

### 選型決策樹

```
知識庫語言？
├── 英文為主
│   └── 成本敏感？
│       ├── 是 → text-embedding-3-small（5× 便宜於 ada-002）
│       └── 否 → text-embedding-3-large（品質最高）
└── 中文 / 多語
    └── 有 GPU？
        ├── 是 → bge-m3（多語首選）
        └── 否 → bge-small-zh-v1.5（CPU 可跑）或 text-embedding-3-small
```

---

## 設計

### 1. Config 統一 embedding 設定

`app/config.py`：

```python
EMBEDDING_PROVIDER: Literal["openai", "huggingface"] = Field(
    default="openai", alias="EMBEDDING_PROVIDER"
)
EMBEDDING_MODEL: str = Field(
    default="text-embedding-ada-002", alias="EMBEDDING_MODEL"
)
EMBEDDING_DIMENSIONS: int | None = Field(
    default=None, alias="EMBEDDING_DIMENSIONS"  # None = 模型預設維度
)
```

### 2. Embedding Provider 抽象

新增 `app/rag/embedder.py`：

```python
from __future__ import annotations

from abc import ABC, abstractmethod


class BaseEmbedder(ABC):
    @abstractmethod
    async def embed(self, text: str) -> list[float]: ...

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]: ...


class OpenAIEmbedder(BaseEmbedder):
    def __init__(self, api_key: str, model: str, dimensions: int | None = None):
        from openai import AsyncOpenAI
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model
        self._dimensions = dimensions

    async def embed(self, text: str) -> list[float]:
        kwargs = {"model": self._model, "input": text}
        if self._dimensions:
            kwargs["dimensions"] = self._dimensions
        resp = await self._client.embeddings.create(**kwargs)
        return resp.data[0].embedding

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        kwargs = {"model": self._model, "input": texts}
        if self._dimensions:
            kwargs["dimensions"] = self._dimensions
        resp = await self._client.embeddings.create(**kwargs)
        return [d.embedding for d in resp.data]


class HuggingFaceEmbedder(BaseEmbedder):
    """本地 HuggingFace 模型（sentence-transformers）。"""

    def __init__(self, model_name: str):
        import asyncio
        from sentence_transformers import SentenceTransformer
        self._model = SentenceTransformer(model_name)

    async def embed(self, text: str) -> list[float]:
        import asyncio
        loop = asyncio.get_event_loop()
        vec = await loop.run_in_executor(None, self._model.encode, text)
        return vec.tolist()

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        import asyncio
        loop = asyncio.get_event_loop()
        vecs = await loop.run_in_executor(None, self._model.encode, texts)
        return vecs.tolist()


def make_embedder(settings) -> BaseEmbedder:
    if settings.EMBEDDING_PROVIDER == "openai":
        return OpenAIEmbedder(
            api_key=settings.OPENAI_API_KEY,
            model=settings.EMBEDDING_MODEL,
            dimensions=settings.EMBEDDING_DIMENSIONS,
        )
    if settings.EMBEDDING_PROVIDER == "huggingface":
        return HuggingFaceEmbedder(model_name=settings.EMBEDDING_MODEL)
    raise ValueError(f"未知 EMBEDDING_PROVIDER: {settings.EMBEDDING_PROVIDER}")
```

> `RAGRetriever` 的 `_embed()` 改用 `self._embedder.embed(query)`（注入 `make_embedder(settings)` 實例）。

### 3. Benchmark 腳本

新增 `scripts/benchmark_embedding.py`：

```python
"""
比較不同 embedding 模型在本地知識庫上的 chunk_recall。

用法：
    python scripts/benchmark_embedding.py \
        --cases tests/cases/golden.yaml \
        --models "text-embedding-ada-002,text-embedding-3-small,BAAI/bge-small-zh-v1.5" \
        --top-k 5 \
        --output reports/embedding_benchmark.md
"""
```

腳本流程：
1. 載入 `golden.yaml`（每筆含 `query` 和 `expected_chunk_ids`）
2. 對每個模型重新 embed golden queries
3. 向 Supabase 做向量搜尋（不入庫——用 `pg_vector` 的即時 embed 或暫時 bypass）
4. 計算 `chunk_recall@K` = 命中 expected_chunk_ids 的比例
5. 輸出 markdown 表格

> **注意**：若要完整跑此 benchmark，需先用各模型重新 ingest 知識庫；教學版可只 benchmark embedding 相似度計算（不需重入庫）。

### 4. 換模型操作步驟

當決定換模型時：

```bash
# 1. 更新 .env
EMBEDDING_MODEL=text-embedding-3-small

# 2. 清空現有 embedding（必做，不同維度不相容）
# Supabase Console → Table Editor → private_knowledge → 清空 embedding 欄位
# 或：
python scripts/clear_embeddings.py

# 3. 重新入庫
python scripts/ingest_markdown.py --reembed

# 4. 驗收
pytest tests/ -k "retriever" -v
```

---

## 可換點 / 不可換點

| | 可換 | 不可換 |
|---|---|---|
| Embedding 模型 | ✅ env var 換 | ❌ 換模型必須重新入庫（不同模型向量不可混用）|
| Embedding 維度 | ✅ `text-embedding-3-*` 支援降維 | ❌ Supabase `vector(N)` 欄位維度需一致（建 table 時決定）|
| Provider | ✅ openai / huggingface | ❌ `embed()` 介面：`str → list[float]` |

---

## 驗收標準

- `EMBEDDING_PROVIDER=openai, EMBEDDING_MODEL=text-embedding-3-small`：功能等價（能正常搜尋）
- `EMBEDDING_PROVIDER=huggingface, EMBEDDING_MODEL=BAAI/bge-small-zh-v1.5`：中文查詢能命中正確 chunk
- `scripts/benchmark_embedding.py` 跑完輸出含 `chunk_recall@5` 的 markdown 表格
- pytest `tests/test_embedder.py`：OpenAIEmbedder mock test + HuggingFaceEmbedder unit test 全綠

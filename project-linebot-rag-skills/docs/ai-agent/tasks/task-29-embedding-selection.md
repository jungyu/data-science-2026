# task-29：Embedding 模型選型指南

> 規格詳見 [spec-29](../specs/spec-29-embedding-selection.md)

---

本 task 引入 `BaseEmbedder` 抽象，讓 embedding 模型可透過 config 切換，並提供 benchmark 腳本供學生在自己的知識庫上量化比較。

## 前置

- spec-20（evaluation framework）建議先完成（`golden.yaml` 和 `chunk_recall` metric）
- 現有 `RAGRetriever._embed()` 直接呼叫 OpenAI SDK

## 前置安裝

```bash
# OpenAI（已有）
# HuggingFace（可選）
uv pip install "sentence-transformers>=2.7"
```

`pyproject.toml`：

```toml
[project.optional-dependencies]
hf-embed = ["sentence-transformers>=2.7"]
```

## 步驟 1：Config 新增

`app/config.py`：

```python
EMBEDDING_PROVIDER: Literal["openai", "huggingface"] = Field(
    default="openai", alias="EMBEDDING_PROVIDER"
)
EMBEDDING_MODEL: str = Field(
    default="text-embedding-ada-002", alias="EMBEDDING_MODEL"
)
EMBEDDING_DIMENSIONS: int | None = Field(
    default=None, alias="EMBEDDING_DIMENSIONS"
)
```

## 步驟 2：新增 `app/rag/embedder.py`

實作 `BaseEmbedder`、`OpenAIEmbedder`、`HuggingFaceEmbedder`、`make_embedder(settings)`。

詳見 spec-29 § 設計 → 2。

## 步驟 3：`RAGRetriever` 注入 embedder

`app/rag/retriever.py`：

```python
from app.rag.embedder import BaseEmbedder, make_embedder

class RAGRetriever:
    def __init__(self, settings: Settings, client, embedder: BaseEmbedder | None = None):
        self._settings = settings
        self._client = client
        self._embedder = embedder or make_embedder(settings)

    async def _embed(self, text: str) -> list[float]:
        return await self._embedder.embed(text)
```

## 步驟 4：新增 benchmark 腳本

新增 `scripts/benchmark_embedding.py`：

```python
"""
比較不同 embedding 模型的 chunk_recall。

用法：
    python scripts/benchmark_embedding.py \
        --cases tests/cases/golden.yaml \
        --models "text-embedding-ada-002,text-embedding-3-small" \
        --top-k 5 \
        --output reports/embedding_benchmark.md
"""
import argparse
import asyncio
import yaml
from pathlib import Path


async def benchmark_model(model_name: str, cases: list[dict], top_k: int) -> float:
    """計算 chunk_recall@top_k for a given model."""
    # ...實作參照 spec-29 腳本流程...
    pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", required=True)
    parser.add_argument("--models", required=True)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--output", default="reports/embedding_benchmark.md")
    args = parser.parse_args()

    cases = yaml.safe_load(Path(args.cases).read_text())
    models = [m.strip() for m in args.models.split(",")]

    results = {}
    for model in models:
        recall = asyncio.run(benchmark_model(model, cases, args.top_k))
        results[model] = recall

    # 輸出 markdown 表格
    lines = ["# Embedding Benchmark\n", "| 模型 | chunk_recall@{} |".format(args.top_k), "|------|---------|"]
    for model, recall in results.items():
        lines.append(f"| {model} | {recall:.3f} |")

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text("\n".join(lines))
    print(f"報告已輸出：{args.output}")


if __name__ == "__main__":
    main()
```

## 步驟 5：補充換模型操作文件

在 `.env.GUIDE.md` 或 README 中新增「換 Embedding 模型」段落：

```markdown
## 換 Embedding 模型

⚠️ 換模型後**必須重新入庫**（不同模型的向量不相容）。

1. 更新 `.env`：`EMBEDDING_MODEL=text-embedding-3-small`
2. 清空舊 embedding：[Supabase Console] → Table Editor → private_knowledge → 清空 `embedding` 欄
3. 重新入庫：`python scripts/ingest_markdown.py`
4. 驗收：`pytest tests/ -k retriever`
```

## 步驟 6：撰寫測試

`tests/test_embedder.py`：

```python
import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_openai_embedder_mock():
    from app.rag.embedder import OpenAIEmbedder
    with patch("openai.AsyncOpenAI") as MockOpenAI:
        instance = MockOpenAI.return_value
        instance.embeddings.create = AsyncMock(
            return_value=MagicMock(data=[MagicMock(embedding=[0.1] * 1536)])
        )
        embedder = OpenAIEmbedder(api_key="test", model="text-embedding-ada-002")
        vec = await embedder.embed("hello")
        assert len(vec) == 1536


@pytest.mark.asyncio
async def test_huggingface_embedder():
    pytest.importorskip("sentence_transformers")
    from app.rag.embedder import HuggingFaceEmbedder
    embedder = HuggingFaceEmbedder("BAAI/bge-small-zh-v1.5")
    vec = await embedder.embed("你好")
    assert len(vec) > 0
```

## 步驟 7：`.env.example` 補充

```dotenv
# Embedding 模型
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-ada-002
# EMBEDDING_DIMENSIONS=  # 留空 = 模型預設維度
```

---

## 里程碑 ✅

- [ ] `EMBEDDING_PROVIDER=openai` 行為與原本完全相同
- [ ] `EMBEDDING_PROVIDER=huggingface, EMBEDDING_MODEL=BAAI/bge-small-zh-v1.5`：中文查詢能正常 embed
- [ ] `scripts/benchmark_embedding.py` 跑完輸出 markdown 表格
- [ ] `pytest tests/test_embedder.py` 全綠

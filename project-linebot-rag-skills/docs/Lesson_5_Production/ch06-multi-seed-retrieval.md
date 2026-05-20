# Ch 06：Multi-seed Retrieval + Fusion + Rerank

> 核心檔案：[`app/graph/seed_expander.py`](../../app/graph/seed_expander.py)、[`app/rag/retriever.py`](../../app/rag/retriever.py)、[`app/rag/fusion.py`](../../app/rag/fusion.py)、[`app/rag/reranker.py`](../../app/rag/reranker.py)
>
> Variant 適用性：**selfrag / reflection 必要** — basic variant 走單 seed 簡化路徑

---

## 本章節奏

| Step | 你會做 |
|------|--------|
| 1 | 看 `DefaultSeedExpander`：features → 多條 seed 的規則 |
| 2 | 看 `RAGRetriever`：單 seed retrieve / 完整 retrieve / fused log 三介面 |
| 3 | 看 fan-out 怎麼在 graph 上並行 |
| 4 | 看 fusion 三策略（max / mean / rrf）細節 |
| 5 | 讀懂 `Cohere/BgeReranker`：兩種 reranker + graceful degrade |
| 6 | ✏️ 調 fusion 策略看排序差異 |
| 7 | ✏️ 寫自己的 SeedExpander（多語言範例） |
| 8 | ✏️ 切到 BGE local reranker（不打 Cohere） |

---

## Step 1：`DefaultSeedExpander` — features → 多條 seed

打開 [`app/graph/seed_expander.py`](../../app/graph/seed_expander.py)：

```python
class DefaultSeedExpander:
    """通用展開規則：
    1. primary_topic 單獨成一條
    2. primary_topic + 各 qualifier
    3. 第一個 entity 串接 primary_topic
    4. raw_query 保底
    去重 + 截斷至 max_seeds。
    """

    def expand(self, features: ExtractedFeatures, *, max_seeds: int = 5) -> list[str]:
        seeds: list[str] = []

        if features.primary_topic:
            seeds.append(features.primary_topic)

        for q in features.qualifiers[:3]:
            combined = f"{features.primary_topic} {q}".strip()
            if combined:
                seeds.append(combined)

        if features.entities:
            entity_seed = f"{features.entities[0]} {features.primary_topic}".strip()
            if entity_seed:
                seeds.append(entity_seed)

        if features.raw_query:
            seeds.append(features.raw_query)

        # 去重 + 截斷
        seen, unique = set(), []
        for s in seeds:
            cleaned = s.strip()
            if cleaned and cleaned not in seen:
                seen.add(cleaned)
                unique.append(cleaned)
        return unique[:max_seeds]
```

### 1-1 範例：一個 query 展成幾條 seed

輸入：「Supabase HNSW 怎麼調 lists 參數？」

[Ch 05](ch05-query-understanding.md) 的 `feature_extractor` 抽出：

```python
ExtractedFeatures(
    primary_topic="HNSW lists 參數",
    qualifiers=["supabase", "向量檢索"],
    intent="how_to",
    entities=["Supabase", "HNSW"],
    raw_query="Supabase HNSW 怎麼調 lists 參數？",
)
```

`DefaultSeedExpander` 展開（去重後）：

```
1. "HNSW lists 參數"                   ← primary_topic 單獨
2. "HNSW lists 參數 supabase"          ← + qualifier 1
3. "HNSW lists 參數 向量檢索"          ← + qualifier 2
4. "Supabase HNSW lists 參數"          ← entity[0] + primary
5. "Supabase HNSW 怎麼調 lists 參數？"  ← raw_query 保底
```

### 1-2 為什麼要這樣展開？

- **primary_topic 單獨**：純概念檢索，撈到 HNSW 的本質介紹
- **加 qualifier**：撈 Supabase 上的具體場景
- **加 entity**：撈該套件的官方/社群文件
- **raw_query**：避免抽錯時什麼都撈不到

5 條 seed 並行去 vector store 撈，每條撈 top-k，後面用 fusion 合併——比單一 query 的覆蓋率高很多。

### 1-3 ✏️ 改成你的需求：增 max_seeds 上限

預設 5 條太多會打爆 LLM token，太少又不夠廣。從 `.env` 拉：

```python
# app/dependencies.py
seed_expander = DefaultSeedExpander()
# 呼叫端：
seeds = seed_expander.expand(features, max_seeds=settings.max_seeds)
```

```bash
# .env
MAX_SEEDS=8   # 預設 5
```

---

## Step 2：`RAGRetriever` — 三個介面各自的用途

打開 [`app/rag/retriever.py`](../../app/rag/retriever.py)。`RAGRetriever` 有三個 async 方法：

### 2-1 `retrieve_for_seed`：單 seed retrieve（給 multi-seed graph 用）

```python
async def retrieve_for_seed(self, seed, *, categories=None, top_k=8) -> list[KnowledgeChunk]:
    try:
        embedding = await self.embedder.embed_query(seed)
        # hybrid 權重從 settings 拉
        s = self.settings
        if s is not None and getattr(s, "hybrid_enabled", False):
            vector_weight = s.hybrid_vector_weight
            keyword_weight = s.hybrid_keyword_weight
        else:
            vector_weight, keyword_weight = 1.0, 0.0
        return await self.store.search(
            query_embedding=embedding,
            query_text=seed,
            filters=SearchFilters(
                categories=categories,
                vector_weight=vector_weight,
                keyword_weight=keyword_weight,
            ),
            top_k=top_k,
        )
    except Exception:
        return []
```

特性：

- **不 rerank**（fusion 之後才 rerank）
- **不 log**（fan-out 多條 seed 各自 log 太吵，最後 `log_fused_retrieval` 統一）
- **失敗回空 list**——一條 seed 失敗不打斷其他 seed

### 2-2 `retrieve`：單 seed 完整 pipeline（給 CLI / test 用）

```python
async def retrieve(self, query, *, categories=None, top_k=8, external_user_id=None, skill_id=None):
    """Single-seed full pipeline（embed → match → rerank → log）。
    保留作為非 graph 路徑的對外 API。"""
    try:
        chunks = await self.retrieve_for_seed(query, categories=categories, top_k=top_k)
        selected = select_top_chunks(chunks, self.final_context_k)
        await self.logs_repo.log_retrieval(RetrievalLogRecord(...))
        return selected
    except Exception:
        return []
```

CLI、測試 fixture、debug script 用這個（一條 query 就完整跑完）。

### 2-3 `log_fused_retrieval`：multi-seed 統一 log

```python
async def log_fused_retrieval(self, *, query, chunks, categories=None, ...):
    """Multi-seed 路徑專用：fusion 完成後的最終結果統一 log。"""
    try:
        await self.logs_repo.log_retrieval(
            RetrievalLogRecord(
                line_user_id=external_user_id,
                query=query,
                skill_id=skill_id,
                category_filter=categories or [],
                retrieved_ids=[chunk.id for chunk in chunks],
                scores={chunk.id: {...} for chunk in chunks},
            )
        )
    except Exception:
        pass
```

multi-seed graph 跑：

1. fan-out N 條 `retrieve_for_seed`（不 log）
2. fusion 合併
3. **一次** `log_fused_retrieval` 寫進 `retrieval_logs`

不然 trace 會被淹沒在每條 seed 的 log 裡。

### 2-4 `build_context`：把 chunks 組成 prompt 段落

```python
def build_context(self, chunks: list[KnowledgeChunk]) -> str:
    if not chunks:
        return "No retrieved context."
    blocks: list[str] = []
    for index, chunk in enumerate(chunks[: self.final_context_k], start=1):
        title = chunk.title or f"Chunk {index}"
        blocks.append(f"[{index}] {title}\nCategory: {chunk.category}\n{chunk.content}")
    return "\n\n".join(blocks)
```

格式：

```
[1] HNSW 索引介紹
Category: engineering
HNSW 是基於圖的近似最近鄰索引...

[2] Supabase 向量檢索教學
Category: engineering
在 Supabase 上使用 pgvector 時...
```

數字 `[1]` `[2]` 是給 LLM 引用用的——[Ch 07](ch07-sufficiency-generation.md) 的 contract builder 會把這些編號對應到 citations。

---

## Step 3：fan-out 怎麼在 graph 上並行

[`app/graph/nodes.py`](../../app/graph/nodes.py) 的 `expand_seeds_node` + `retrieve_one_node`：

```python
async def expand_seeds_node(state: RAGState, services: Any) -> dict:
    """把 features 展開成 seeds，準備 fan-out。"""
    features = state.get("features")
    transformed = state.get("transformed_queries") or []

    seed_set = set()

    # query_transform 的 seeds 優先
    for q in transformed:
        seed_set.add(q.strip())

    # features 展開的 seeds
    if features:
        for s in services.seed_expander.expand(features, max_seeds=services.settings.max_seeds):
            seed_set.add(s.strip())

    seeds = [s for s in seed_set if s][: services.settings.max_seeds]
    return {"seeds": seeds}


async def retrieve_one_node(state: dict, services: Any) -> dict:
    """單一 seed 的 retrieve（fan-out 後每條 seed 一個此節點 instance）。

    每個 state 是 LangGraph Send() 出來的 sub-state，含一個 seed。
    """
    seed = state["seed"]
    categories = state.get("rag_categories") or None
    chunks = await services.retriever.retrieve_for_seed(seed, categories=categories, top_k=8)
    return {"hits_per_seed": [chunks]}   # 合併時用 list-append reducer
```

### 3-1 LangGraph 的 fan-out：`Send` API

```python
# selfrag.py 或 reflection.py
from langgraph.types import Send

def fan_out_to_retrieve(state: RAGState) -> list[Send]:
    seeds = state.get("seeds") or []
    return [
        Send("retrieve_one", {"seed": s, "rag_categories": state.get("router_result").rag_categories})
        for s in seeds
    ]

g.add_conditional_edges("expand_seeds", fan_out_to_retrieve, ["retrieve_one"])
```

`Send` 是 LangGraph 的並行原語——回 list of `Send` 會**並行**啟動多個目標節點。每個 sub-state 走 `retrieve_one_node` 一輪，結果用 reducer 合併。reducer 在 [`app/graph/state.py`](../../app/graph/state.py) 用 `Annotated[..., add]` 標註：

```python
# app/graph/state.py:29
from operator import add
from typing import Annotated

class RAGState(TypedDict):
    hits_per_seed: Annotated[list[list[KnowledgeChunk]], add]   # ← list-append reducer
```

`Annotated[..., add]` 告訴 LangGraph：多個 node 都回傳 `hits_per_seed` 時，用 `add`（也就是 `list1 + list2`）合併，**不是覆蓋**。所以每條 `retrieve_one_node` 回 `{"hits_per_seed": [chunks]}`，最後 fuse_scores 拿到的會是 `[[...], [...], [...]]`（外層 list 對應每條 seed）。

### 3-2 ✏️ 改成你的需求：控制並行度

過多 seeds 並行會打爆 OpenAI / Cohere rate limit。可以加 semaphore 控制：

```python
# app/dependencies.py
import asyncio
retrieve_semaphore = asyncio.Semaphore(settings.max_concurrent_retrieves)   # 預設 5

# 包裝 retrieve_for_seed
async def limited_retrieve(seed, **kwargs):
    async with retrieve_semaphore:
        return await retriever.retrieve_for_seed(seed, **kwargs)
```

或在 LangGraph 層面用 `Send`+遞迴限制。完整見 spec-14。

---

## Step 4：fusion 三策略

打開 [`app/rag/fusion.py`](../../app/rag/fusion.py)，88 行三策略：

### 4-1 `fuse_max`：取最高分（最寬鬆）

```python
def fuse_max(hits_per_seed: list[list[KnowledgeChunk]]) -> list[KnowledgeChunk]:
    best: dict[str, KnowledgeChunk] = {}
    for hits in hits_per_seed:
        for c in hits:
            cid = _by_id(c)
            if cid not in best or c.combined_score > best[cid].combined_score:
                best[cid] = c
    return sorted(best.values(), key=lambda c: c.combined_score, reverse=True)
```

「**任一 seed 撈到分數高就保留**」。優點：召回率最高。缺點：可能保留只在一條 seed 偏高、其實不通用的 chunk。

### 4-2 `fuse_mean`：平均分（偏好多路共識）

```python
def fuse_mean(hits_per_seed: list[list[KnowledgeChunk]]) -> list[KnowledgeChunk]:
    n_seeds = len(hits_per_seed)
    by_id, rep = defaultdict(list), {}

    for hits in hits_per_seed:
        for c in hits:
            cid = _by_id(c)
            by_id[cid].append(c.combined_score)
            if cid not in rep or c.combined_score > rep[cid].combined_score:
                rep[cid] = c

    out = []
    for cid, scores in by_id.items():
        avg = sum(scores) / n_seeds   # ← 缺席的 seed 視為 0
        out.append(rep[cid].model_copy(update={"combined_score": avg}))
    return sorted(out, key=lambda c: c.combined_score, reverse=True)
```

「**只在一條 seed 命中的 chunk 會被平均分稀釋**」。偏好「多條 seed 都撈到 = 真正相關」的 chunk。

### 4-3 `fuse_rrf`：Reciprocal Rank Fusion（最穩定）

```python
def fuse_rrf(hits_per_seed: list[list[KnowledgeChunk]], *, k: int = 60) -> list[KnowledgeChunk]:
    rrf_score: dict[str, float] = defaultdict(float)
    rep: dict[str, KnowledgeChunk] = {}

    for hits in hits_per_seed:
        for rank, c in enumerate(hits):
            cid = _by_id(c)
            rrf_score[cid] += 1.0 / (k + rank + 1)
            if cid not in rep or c.combined_score > rep[cid].combined_score:
                rep[cid] = c

    out = [rep[cid].model_copy(update={"combined_score": score})
           for cid, score in rrf_score.items()]
    return sorted(out, key=lambda c: c.combined_score, reverse=True)
```

「**用 rank 而非 score 累加**」。`1/(60+rank)` 公式跟 [Ch 01 §5-2](ch01-supabase-schema.md#5-2-看-rpc-在做什麼) 的 SQL 端一樣，但這次是在 Python 層做跨 seed 的 RRF。

**為什麼 RRF 是預設？** 不同 seed 撈到的 chunk 量綱可能不同（一條 seed 全是高分 chunk、另一條全是低分）。RRF 用 rank 抹平量綱，最穩定。

### 4-4 策略對照

| 策略 | 偏好 | 適合 |
|------|------|------|
| `max` | 任一命中即保留 | 召回優先 |
| `mean` | 多 seed 共識 | 精準優先 |
| `rrf` | rank-based 抹平 | 預設、平衡 |

`.env`：

```bash
FUSION_STRATEGY=rrf   # max | mean | rrf
```

### 4-5 `get_fuser` 工廠

```python
FUSION_STRATEGIES = {"max": fuse_max, "mean": fuse_mean, "rrf": fuse_rrf}

def get_fuser(strategy: str):
    fuser = FUSION_STRATEGIES.get(strategy)
    if fuser is None:
        raise ValueError(f"unknown fusion strategy: {strategy!r}. Available: {sorted(FUSION_STRATEGIES.keys())}")
    return fuser
```

策略不認識直接 raise——這跟其他地方的 graceful degrade 不同，因為 config 寫錯應該明顯失敗。

---

## Step 5：`CohereReranker` / `BgeReranker` — 兩種 reranker

打開 [`app/rag/reranker.py`](../../app/rag/reranker.py)。

### 5-1 `BaseReranker` 抽象

```python
class BaseReranker(ABC):
    @abstractmethod
    async def rerank(self, query: str, chunks: list[KnowledgeChunk], top_n: int) -> list[KnowledgeChunk]:
        """Return chunks reranked by cross-encoder score, capped at top_n."""
```

### 5-2 `CohereReranker`：API 服務

```python
class CohereReranker(BaseReranker):
    def __init__(self, api_key: str, model: str = "rerank-multilingual-v3.0"):
        import cohere
        self._client = cohere.AsyncClientV2(api_key=api_key)
        self._model = model

    async def rerank(self, query, chunks, top_n):
        if not chunks:
            return []
        docs = [c.content for c in chunks]
        try:
            resp = await self._client.rerank(
                model=self._model, query=query, documents=docs,
                top_n=min(top_n, len(docs)),
            )
        except Exception as exc:
            # spec-04 §Fallback：API 失敗（超時/限流/網路）靜默降回 RRF 排序
            logger.warning("Cohere rerank failed (%s); falling back to RRF score sort", exc)
            return sorted(chunks, key=lambda c: c.combined_score, reverse=True)[:top_n]
        reranked = []
        for result in resp.results:
            chunk = chunks[result.index].model_copy()
            chunk.combined_score = result.relevance_score
            reranked.append(chunk)
        return reranked
```

**關鍵 fallback**：API 失敗時不阻斷，回 RRF 排序前 top_n。

### 5-3 `BgeReranker`：本機 cross-encoder

```python
class BgeReranker(BaseReranker):
    def __init__(self, model_name: str = "BAAI/bge-reranker-base"):
        from sentence_transformers import CrossEncoder
        self._model = CrossEncoder(model_name)

    async def rerank(self, query, chunks, top_n):
        if not chunks:
            return []
        pairs = [(query, c.content) for c in chunks]
        # CrossEncoder.predict 是同步的，丟進 thread pool 不要阻塞 event loop
        loop = asyncio.get_event_loop()
        scores = await loop.run_in_executor(None, self._model.predict, pairs)
        ranked = sorted(zip(scores, chunks), key=lambda x: x[0], reverse=True)
        ...
```

特性：

- 零 API 成本，跑在自己機器上
- 第一次載入模型約 30 秒
- CPU 跑 < 100 chunks 約 1-2 秒

### 5-4 `make_reranker` factory

```python
def make_reranker(settings) -> BaseReranker | None:
    if not getattr(settings, "reranker_enabled", False):
        return None
    provider = getattr(settings, "reranker_provider", "cohere")
    if provider == "cohere":
        api_key = getattr(settings, "cohere_api_key", "")
        if not api_key:
            # spec-04 §Fallback：缺 key 時靜默降回 RRF
            logger.warning("reranker_provider=cohere but COHERE_API_KEY is empty; falling back")
            return None
        return CohereReranker(api_key=api_key, ...)
    if provider == "bge":
        return BgeReranker(...)
    raise ValueError(f"Unknown reranker_provider: {provider!r}")
```

兩層降級：

1. `reranker_enabled=false` → 不 rerank
2. `provider=cohere` 但沒 key → 不 rerank（log warning）

`make_reranker` 回 `None` 時，呼叫端走 `select_top_chunks`（純 score 排序）：

```python
def select_top_chunks(chunks: list[KnowledgeChunk], limit: int) -> list[KnowledgeChunk]:
    """Fallback sort-based selection when reranker is disabled."""
    return sorted(chunks, key=lambda chunk: chunk.combined_score, reverse=True)[:limit]
```

---

## Step 6：✏️ 切 fusion 策略看排序差異

寫個 script 比三策略結果：

```python
# scripts/compare_fusion.py
import asyncio, os
from app.config import Settings
from app.dependencies import build_runtime_services
from app.rag.fusion import get_fuser

async def main():
    services = await build_runtime_services(Settings())
    seeds = [
        "HNSW lists 參數",
        "Supabase pgvector 索引",
        "向量檢索 IVFFlat 比較",
    ]

    # 並行撈 3 條 seed 的 hits
    hits_per_seed = await asyncio.gather(*[
        services.retriever.retrieve_for_seed(s, top_k=10)
        for s in seeds
    ])

    for strategy in ["max", "mean", "rrf"]:
        fuser = get_fuser(strategy)
        fused = fuser(hits_per_seed)[:5]
        print(f"\n=== {strategy} ===")
        for i, c in enumerate(fused, 1):
            print(f"  {i}. {(c.title or '<no title>')[:50]} (score={c.combined_score:.4f})")

asyncio.run(main())
```

```bash
poetry run python scripts/compare_fusion.py
```

預期：三種策略前 5 名重疊但順序不同。決定哪個策略對你的 KB 最合適。

---

## Step 7：✏️ 寫自己的 SeedExpander（多語言範例）

假設你的 KB 是中英混合，想讓每條 seed 都有兩個語言版本：

```python
# app/graph/seed_expander.py 加
class BilingualSeedExpander:
    """中英文 seed 並行（需要 query_transform 已產生英文版）。"""

    def __init__(self, base: DefaultSeedExpander, translator):
        self._base = base
        self._translator = translator   # 同步 dict 或 LLM-based

    def expand(self, features: ExtractedFeatures, *, max_seeds: int = 5) -> list[str]:
        zh_seeds = self._base.expand(features, max_seeds=max_seeds // 2)
        en_seeds = [self._translator(s) for s in zh_seeds]

        all_seeds = []
        for zh, en in zip(zh_seeds, en_seeds):
            all_seeds.append(zh)
            if en and en != zh:
                all_seeds.append(en)
        return all_seeds[:max_seeds]
```

註冊：

```python
# app/dependencies.py
expander = BilingualSeedExpander(
    base=DefaultSeedExpander(),
    translator=my_translator_fn,
)
```

graph 完全不知道你換了——只要實作 `SeedExpander` Protocol 即可。

---

## Step 8：✏️ 切到 BGE local reranker

如果你不想依賴 Cohere（成本 / 隱私 / 離線需求）：

### 8-1 安裝依賴

```bash
poetry add sentence-transformers
```

### 8-2 切 settings

```bash
# .env
RERANKER_ENABLED=true
RERANKER_PROVIDER=bge
BGE_RERANKER_MODEL=BAAI/bge-reranker-base   # 預設；想更好換 base → large
```

### 8-3 第一次啟動會 download 模型

```bash
poetry run uvicorn app.main:app
# 等約 30 秒 download BGE model
```

### 8-4 驗收

```bash
poetry run python -c '
import asyncio
from app.config import Settings
from app.rag.reranker import make_reranker
from app.rag.schemas import KnowledgeChunk

async def main():
    r = make_reranker(Settings())
    print("reranker:", type(r).__name__)

    chunks = [
        KnowledgeChunk(id="1", title="HNSW", content="HNSW is graph-based ANN",
                       category="eng", combined_score=0.5,
                       vector_score=0.5, keyword_score=0),
        KnowledgeChunk(id="2", title="Random", content="Cats love fish",
                       category="eng", combined_score=0.9,
                       vector_score=0.9, keyword_score=0),
    ]
    out = await r.rerank("HNSW vector index", chunks, top_n=2)
    for c in out:
        print(f"  {c.title}: {c.combined_score:.4f}")

asyncio.run(main())
'
```

預期：HNSW chunk 排第一（即使 combined_score 較低，cross-encoder 看內容知道它相關）。

---

## 🎯 本章驗收

### Step 1：seed_expander 展開

```bash
poetry run python -c '
from app.graph.feature_extractor import ExtractedFeatures
from app.graph.seed_expander import DefaultSeedExpander

features = ExtractedFeatures(
    primary_topic="HNSW lists 參數",
    qualifiers=["supabase", "向量檢索"],
    intent="how_to",
    entities=["Supabase", "HNSW"],
    raw_query="Supabase HNSW 怎麼調 lists 參數？",
)
seeds = DefaultSeedExpander().expand(features, max_seeds=10)
for i, s in enumerate(seeds, 1):
    print(f"{i}. {s}")
'
```

預期：4-5 條去重後的 seed。

### Step 2：retrieve_for_seed 單條

```bash
poetry run python -c '
import asyncio
from app.config import Settings
from app.dependencies import build_runtime_services

async def main():
    services = await build_runtime_services(Settings())
    chunks = await services.retriever.retrieve_for_seed("Supabase HNSW", top_k=5)
    for c in chunks:
        print(f"  {(c.title or \"<no title>\")[:50]} (score={c.combined_score:.3f})")

asyncio.run(main())
'
```

預期：5 筆 chunks 且分數 monotonic decreasing。

### Step 3：fusion 三策略不同

跑 [Step 6](#step-6-切-fusion-策略看排序差異) 的 `compare_fusion.py`。

### Step 4：reranker 切換

```bash
# Cohere mode（要有 COHERE_API_KEY）
RERANKER_ENABLED=true RERANKER_PROVIDER=cohere poetry run python -c '
from app.rag.reranker import make_reranker
from app.config import Settings
print(type(make_reranker(Settings())).__name__)
'

# BGE local mode
RERANKER_ENABLED=true RERANKER_PROVIDER=bge poetry run python -c '
from app.rag.reranker import make_reranker
from app.config import Settings
print(type(make_reranker(Settings())).__name__)
'

# Disabled mode
RERANKER_ENABLED=false poetry run python -c '
from app.rag.reranker import make_reranker
from app.config import Settings
print(make_reranker(Settings()))
'
```

預期分別印 `CohereReranker` / `BgeReranker` / `None`。

### Step 5：完整 multi-seed graph 跑通

```bash
poetry run python -c '
import asyncio
from app.config import Settings
from app.dependencies import build_runtime_services
from app.channels.base import ChannelInput
from app.line.webhook import process_channel_input

async def main():
    services = await build_runtime_services(Settings())
    inp = ChannelInput(channel="stub", external_user_id="U_demo_retrieve",
                       external_message_id="msg_1",
                       raw_text="Supabase HNSW 怎麼調 lists 參數？")
    await process_channel_input(inp, services)
    print(services.channels["stub"].pushed)

asyncio.run(main())
'
```

預期：stub 收到一則訊息，內含對 HNSW 的解釋。Trace（[Ch 09](ch09-observability-security.md)）裡能看到 2-5 條並行 retrieve。

---

## 下一章

[Ch 07：Sufficiency + Clarifier + 兩階段生成](ch07-sufficiency-generation.md) — 撈完 chunks 後，怎麼判斷夠不夠？不夠就追問，夠了就走兩階段（contract 純程式 + narrative 受限 LLM）生成最終答案。

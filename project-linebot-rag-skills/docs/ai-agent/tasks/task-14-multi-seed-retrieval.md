# task-14：Multi-seed 並行檢索 + Score Fusion

> 規格詳見 [spec-14](../specs/spec-14-multi-seed-retrieval.md)

---

把 task-13 產出的 `ExtractedFeatures` 展開為多條 seed → 並行 retrieve → fusion 合併。這是 LangGraph fan-out / fan-in 的教學重點。

## 前置

- task-13 完成（`features` 已在 state）
- `RAGRetriever` 已存在；本 task 會新增 `retrieve_for_seed()` 方法但不破壞既有 `retrieve()`

## 步驟 1：實作 SeedExpander

新增 `app/graph/seed_expander.py`：

```python
from __future__ import annotations

from typing import Protocol

from app.graph.feature_extractor import ExtractedFeatures


class SeedExpander(Protocol):
    def expand(self, features: ExtractedFeatures, *, max_seeds: int = 5) -> list[str]: ...


class DefaultSeedExpander:
    """通用展開規則：適用大多數題目，學生轉題目時可子類化覆寫。"""

    def expand(self, features: ExtractedFeatures, *, max_seeds: int = 5) -> list[str]:
        seeds: list[str] = []

        # 規則 1：primary_topic 單獨成一條
        seeds.append(features.primary_topic)

        # 規則 2：primary_topic + 各 qualifier
        for q in features.qualifiers[:3]:
            seeds.append(f"{features.primary_topic} {q}")

        # 規則 3：第一個 entity 串接 primary_topic
        if features.entities:
            seeds.append(f"{features.entities[0]} {features.primary_topic}")

        # 規則 4：raw_query 保底（避免抽取過度）
        if features.raw_query and features.raw_query not in seeds:
            seeds.append(features.raw_query)

        # 去重 + 截斷
        seen = set()
        unique = []
        for s in seeds:
            s_clean = s.strip()
            if s_clean and s_clean not in seen:
                seen.add(s_clean)
                unique.append(s_clean)
        return unique[:max_seeds]
```

## 步驟 2：實作 fusion 三策略

新增 `app/rag/fusion.py`：

```python
from __future__ import annotations

from collections import defaultdict
from typing import Callable

from app.rag.schemas import KnowledgeChunk


def _by_id(chunk: KnowledgeChunk) -> str:
    return chunk.id  # 或 chunk.chunk_id，依實際 schema


def fuse_max(hits_per_seed: list[list[KnowledgeChunk]]) -> list[KnowledgeChunk]:
    best: dict[str, KnowledgeChunk] = {}
    for hits in hits_per_seed:
        for c in hits:
            cid = _by_id(c)
            if cid not in best or c.score > best[cid].score:
                best[cid] = c
    return sorted(best.values(), key=lambda c: c.score, reverse=True)


def fuse_mean(hits_per_seed: list[list[KnowledgeChunk]]) -> list[KnowledgeChunk]:
    by_id: dict[str, list[KnowledgeChunk]] = defaultdict(list)
    n_seeds = len(hits_per_seed)
    for hits in hits_per_seed:
        for c in hits:
            by_id[_by_id(c)].append(c)
    out = []
    for cid, group in by_id.items():
        # 缺席的 seed 計 0
        avg = sum(c.score for c in group) / n_seeds
        rep = max(group, key=lambda c: c.score)
        rep = rep.model_copy(update={"score": avg})  # pydantic v2
        out.append(rep)
    return sorted(out, key=lambda c: c.score, reverse=True)


def fuse_rrf(
    hits_per_seed: list[list[KnowledgeChunk]], *, k: int = 60
) -> list[KnowledgeChunk]:
    rrf_score: dict[str, float] = defaultdict(float)
    rep: dict[str, KnowledgeChunk] = {}
    for hits in hits_per_seed:
        for rank, c in enumerate(hits):
            cid = _by_id(c)
            rrf_score[cid] += 1.0 / (k + rank + 1)
            if cid not in rep or c.score > rep[cid].score:
                rep[cid] = c
    out = [rep[cid].model_copy(update={"score": s}) for cid, s in rrf_score.items()]
    return sorted(out, key=lambda c: c.score, reverse=True)


FUSION_STRATEGIES: dict[str, Callable] = {
    "max": fuse_max,
    "mean": fuse_mean,
    "rrf": fuse_rrf,
}
```

> ⚠️ `_by_id` 與 `model_copy` 的實際 attribute 名稱請對齊 `app/rag/schemas.py::KnowledgeChunk`。若 schema 用 `dataclass` 而非 pydantic，請改用 `dataclasses.replace`。

## 步驟 3：擴充 retriever

修改 `app/rag/retriever.py`：

```python
class RAGRetriever:
    # ...既有方法

    async def retrieve_for_seed(
        self,
        seed: str,
        *,
        categories: list[str] | None = None,
        top_k: int = 8,
        line_user_id: str | None = None,
        skill_id: str | None = None,
    ) -> list[KnowledgeChunk]:
        """單條 seed 的檢索。retrieve() 在 multi-seed 時改為呼叫多次本方法 + fusion。"""
        # 從既有 retrieve() 抽出單次 embedding + RPC + 初步 rerank 的邏輯
        ...

    async def retrieve(self, query: str, **kwargs) -> list[KnowledgeChunk]:
        """單 seed 對外 API（保留給非 graph 路徑使用）。"""
        return await self.retrieve_for_seed(query, **kwargs)
```

## 步驟 4：擴充 RAGState

修改 `app/graph/state.py`：

```python
from typing import Annotated
from operator import add

class RAGState(TypedDict, total=False):
    # ...既有欄位
    seeds: list[str]
    hits_per_seed: Annotated[list[list[KnowledgeChunk]], add]  # reducer 累積
    fusion_strategy: str  # "max" | "mean" | "rrf"
```

`Annotated[..., add]` 是 LangGraph reducer，並行 node 寫入時會 append 而非覆寫。

## 步驟 5：實作 fan-out / fan-in node

修改 `app/graph/nodes.py`：

```python
from langgraph.types import Send
from app.rag.fusion import FUSION_STRATEGIES


async def expand_seeds_node(state: RAGState, services: RuntimeServices):
    seeds = services.seed_expander.expand(state["features"])
    return {"seeds": seeds}


def fan_out_to_retrieve(state: RAGState):
    """conditional edge function：每條 seed 派一個 retrieve_one 任務。"""
    return [Send("retrieve_one", {"seed": s, "_index": i, "_state": state})
            for i, s in enumerate(state["seeds"])]


async def retrieve_one_node(payload: dict, services: RuntimeServices):
    """並行 sub-task；payload 是 fan_out 給的單條 seed。"""
    state = payload["_state"]
    router_result = state["router_result"]
    chunks = await services.retriever.retrieve_for_seed(
        payload["seed"],
        categories=router_result.rag_categories,
        top_k=services.settings.knowledge_top_k,
        line_user_id=state["line_user_id"],
        skill_id=router_result.target_skill,
    )
    # 用 reducer append
    return {"hits_per_seed": [chunks]}


async def fuse_scores_node(state: RAGState, services: RuntimeServices):
    strategy = state.get("fusion_strategy", services.settings.fusion_strategy)
    fuser = FUSION_STRATEGIES[strategy]
    fused = fuser(state["hits_per_seed"])
    final = fused[: services.settings.final_context_k]
    context = services.retriever.build_context(final)
    return {"rag_chunks": final, "rag_context": context}
```

## 步驟 6：改寫 graph

修改 `app/graph/rag_graph.py`：

```python
g.add_node("expand_seeds", partial(expand_seeds_node, services=services))
g.add_node("retrieve_one", partial(retrieve_one_node, services=services))
g.add_node("fuse_scores", partial(fuse_scores_node, services=services))

g.add_edge("extract_features", "expand_seeds")
g.add_conditional_edges("expand_seeds", fan_out_to_retrieve, ["retrieve_one"])
g.add_edge("retrieve_one", "fuse_scores")
g.add_edge("fuse_scores", "generate")
# 移除舊的 retrieve node 與 extract_features → retrieve / retrieve → generate edge
```

> LangGraph 的 fan-in 預設等所有 `retrieve_one` 完成才觸發下游。確認 langgraph 版本 ≥ 0.2 支援 `Send` API。

## 步驟 7：config + DI

修改 `app/config.py`：

```python
class Settings(BaseSettings):
    # ...
    fusion_strategy: Literal["max", "mean", "rrf"] = "max"
    max_seeds: int = 5
```

修改 `app/dependencies.py`：

```python
from app.graph.seed_expander import DefaultSeedExpander

@dataclass(frozen=True)
class RuntimeServices:
    # ...
    seed_expander: Any = None

@lru_cache(maxsize=1)
def get_seed_expander():
    return DefaultSeedExpander()
```

## 步驟 8：測試

新增 `tests/test_seed_expander.py`：

```python
def test_default_expander_produces_unique_seeds():
    from app.graph.feature_extractor import ExtractedFeatures
    from app.graph.seed_expander import DefaultSeedExpander
    f = ExtractedFeatures(
        primary_topic="hydration mismatch",
        qualifiers=["Next.js 14", "SSR"],
        intent="debug",
        entities=["Next.js"],
        raw_query="Next.js 14 SSR hydration",
    )
    seeds = DefaultSeedExpander().expand(f)
    assert len(seeds) == len(set(seeds))
    assert "hydration mismatch" in seeds
    assert any("Next.js 14" in s for s in seeds)
```

新增 `tests/test_fusion.py`：

```python
def test_fuse_max_takes_highest():
    # 用 mock chunks 驗證三策略
    ...

def test_fuse_rrf_handles_missing_seeds():
    ...
```

## 請輸出

1. `app/graph/seed_expander.py`
2. `app/rag/fusion.py`
3. 修改後的 `app/rag/retriever.py`（新增 `retrieve_for_seed`，`retrieve` 改為包裝）
4. 修改後的 `app/graph/state.py`、`nodes.py`、`rag_graph.py`、`dependencies.py`、`config.py`
5. `tests/test_seed_expander.py`、`tests/test_fusion.py`、整合測試 case
6. README 加「Multi-seed 與 Fusion 策略」段（含三策略適用場景表）

## 驗收指令

```bash
pytest tests/test_seed_expander.py tests/test_fusion.py -v
pytest

# 切換策略不需重 build
FUSION_STRATEGY=rrf ./scripts/run_local.sh
# 比對相同問題在 max / mean / rrf 下的 top-K 差異

# log 應顯示
# expanded_seeds=4
# hits_per_seed=[3,2,3,1]
# fusion=max → final_chunks=4
```

驗收通過條件：

- 三策略單元測試全綠
- 多條件問題能展開出 ≥3 條 seed（log 確認）
- 並行檢索的總耗時 ≤ 串行的 1.5 倍（粗略觀察 log 時戳）
- 切換 `FUSION_STRATEGY` 環境變數無需改 graph

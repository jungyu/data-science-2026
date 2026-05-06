# Spec-14：Multi-seed 檢索 + Score Fusion（P2）

## 背景

單一 query embedding 對多條件並置的問題會稀釋語意。Spec-13 的 Feature Extractor 已把輸入拆成 `primary_topic` + `qualifiers` + `entities`；本 spec 把這些特徵**展開為多條獨立 seed，並行檢索後做分數融合**。

借鑑：project-destiny ADR-009（multi-seed retrieval and agentic boundary）。本 spec 採用其 D1 決策，但簡化為 LangGraph 教學情境。

## 設計

### Graph 位置

```
extract_features → expand_seeds → [retrieve_seed_1, retrieve_seed_2, ...]（並行）→ fuse_scores → ...
```

### Seed 展開規則（預設版）

從 `ExtractedFeatures` 產出 2–5 條 seed：

| 規則 | 範例輸入 | 範例 seed |
|------|---------|----------|
| primary_topic 單獨成一條 | `primary_topic="hydration mismatch"` | `"hydration mismatch"` |
| primary_topic + 主要 qualifier | `qualifiers=["Next.js 14", "SSR"]` | `"hydration mismatch Next.js 14"`, `"hydration mismatch SSR"` |
| entities 串接 primary_topic | `entities=["Next.js"]` | `"Next.js hydration mismatch"` |
| raw_query fallback | — | 原句作為保底 seed |

**展開上限預設 5 條**（避免成本爆炸），可由 config 調整。

### 並行檢索

每條 seed 獨立 embedding、獨立呼叫 `RAGRetriever.retrieve_for_seed()`，回傳 `list[KnowledgeChunk]`（含 `seed_index` 標記來源）。

LangGraph 並行寫法用 `Send` API 或 `add_node` 的多次 invoke：

```python
# 在 expand_seeds_node 內回傳
return [Send("retrieve", {"seed": s, "seed_index": i}) for i, s in enumerate(seeds)]
```

### Score Fusion 三策略

| 策略 | 公式 | 適用場景 |
|------|------|---------|
| `max`（預設）| `final = max(score_per_seed)` | 任一 seed 強命中即排前 |
| `mean` | `final = mean(score_per_seed, missing=0)` | 偏好多路共識 |
| `rrf` | `final = Σ 1/(k + rank_per_seed)`，k=60 | 鈍化極端分數，最穩 |

切換策略只改 config，不改 graph 結構。

### State 新增 / 修改欄位

```python
class RAGState(TypedDict, total=False):
    ...
    seeds: list[str]                          # expand_seeds 產出
    hits_per_seed: list[list[KnowledgeChunk]] # 並行 retrieve 累積
    rag_chunks: list[KnowledgeChunk]          # fuse 後的最終排序（取代原欄位）
    fusion_strategy: Literal["max", "mean", "rrf"]
```

`hits_per_seed` 用 reducer（list append）累積並行結果。

### 觀測性

每個 chunk 紀錄：
- `hit_seed_count`：被多少條 seed 命中
- `top_seed_index`：最高分來自哪條 seed

寫入 log，方便 debug 「為什麼這個 chunk 排前 / 為什麼沒命中」。

## 介面契約

**新增**：`app/graph/seed_expander.py`

```python
class SeedExpander(Protocol):
    def expand(self, features: ExtractedFeatures, *, max_seeds: int = 5) -> list[str]: ...
```

**新增**：`app/rag/fusion.py`

```python
def fuse_max(hits_per_seed: list[list[KnowledgeChunk]]) -> list[KnowledgeChunk]: ...
def fuse_mean(hits_per_seed: list[list[KnowledgeChunk]]) -> list[KnowledgeChunk]: ...
def fuse_rrf(hits_per_seed: list[list[KnowledgeChunk]], *, k: int = 60) -> list[KnowledgeChunk]: ...

FUSION_STRATEGIES = {"max": fuse_max, "mean": fuse_mean, "rrf": fuse_rrf}
```

**修改**：
- `app/rag/retriever.py`：新增 `retrieve_for_seed(seed: str, ...) -> list[KnowledgeChunk]`，**保留** `retrieve()` 作為內部包裝
- `app/graph/nodes.py`：新增 `expand_seeds_node`、`fuse_scores_node`，`retrieve_node` 改為單 seed 版
- `app/graph/rag_graph.py`：把 retrieve node 改為 fan-out / fan-in 結構

**Config 新增**：`FUSION_STRATEGY` 環境變數，預設 `max`。

## 驗收標準

- 多條件問題能展開為 ≥3 條 seed，log 顯示每條 seed 的 top-K 命中
- 三種 fusion 策略可以由環境變數切換，graph 不需要重 build
- 並行檢索的總耗時 ≤ 單 seed × 1.5（驗證並行有效）
- 切回單 seed 的 fallback 路徑可用（當 seeds 只有 1 條時，跳過 fusion）
- 既有 `destiny query` 風格的單 seed 直查 API 仍可用（保留 `retrieve()` 公開介面）

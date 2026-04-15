# ADR-009: Multi-seed 檢索與 Rule-first Agentic 邊界

- Status: Accepted
- Date: 2026-04-15
- Deciders: System Architect, NLP Engineer
- Supersedes: 無（補強 ADR-001、ADR-005）
- Tags: retrieval, query-expansion, agentic, score-fusion

## Context

Phase 1 完成後對 [`docs/architecture/bazi-rag-system-plan.md`](../architecture/bazi-rag-system-plan.md)
進行架構審計（比對 `docs/RAG/` 教學材料），發現兩項需明確化的決策：

### 落差 1：單 seed 檢索會稀釋多條件語意

Rule Engine 產出 `retrieval_query_seeds`（通常 3–5 條，涵蓋日主+月令、格局、調候、沖合
等不同維度），但原實作 [`retrieval.retrieve()`](../../src/destiny/retrieval.py) 以
`" / ".join(seeds)` 合成單一字串再做一次 embedding。

八字查詢的典型結構是「甲木 + 申月 + 正官格 + 調候火」這類**多條件並置**，各條件的語意
訊號在單一 embedding 中會相互稀釋，導致：

- 高度相關的單條件 atom（例如只講「甲木冬生調候」的 `ziping-seasonal-jia-winter-001`）被排到中段
- 表面相似但條件不全對的 atom 反而擠入 Top-K
- 難以在檢索日誌中定位「哪條 seed 實際貢獻了命中」

### 落差 2：架構文件未聲明 agentic 邊界

教材 `ch05-agentic-rag.md` 主張「LLM 自主決定是否檢索、如何檢索、是否重試」的通用模式。
若未在架構文件明示本系統的取捨邊界，未來維運者容易誤以為應將 Rule Engine / Bazi Engine
變成 LLM 可呼叫的 tools。這會破壞 ADR-003（確定性排盤）與 ADR-005（規則先行）的根本前提。

## Decision

### D1：採用 Multi-seed 並行檢索 + Score Fusion

修改 Retrieval Orchestrator，使 Rule Engine 的每條 seed **獨立向量化後獨立檢索**，最後
以可選的 fusion 策略合併：

- **max**（預設）：取 atom 在所有 seed 中的最高 `final_score`
- **mean**：對未命中的 seed 計 0，偏好多路共識的 atom
- **rrf**：Reciprocal Rank Fusion，`Σ 1/(k + rank_i)`，鈍化極端分數

API：`retrieval.retrieve_multi_seed(seeds: list[str], fusion="max", ...)`

觀測性：Hit 紀錄 `hit_seed_count` 與 `top_seed`，供除錯。

舊的 `retrieve()` 保留作單 seed 相容 API（如 `destiny query` 指令）。

### D2：明確聲明 Rule-first + 受限 Agentic

架構計畫 §4.5 新增「Retrieval 策略的 Agentic 邊界」章節，明示：

**採用**的受限 agentic 成分：
- Query Expansion（Rule Engine 產多 seed）
- Score Fusion
- Grounded Constraint（只能引 passed-in atom_code）
- Layer D 自審（LLM-as-judge）

**不採用**：
- LLM 自主決策是否/如何檢索
- LLM 呼叫 Bazi Engine / Rule Engine 作為 tools
- 動態重新計劃 pipeline 順序

**未來可評估**：
- 不確定性回溯檢索（由規則觸發，非 LLM 決策）
- Graph Retrieval 二階展開（ADR-001 Phase 2）

## Alternatives Considered

### Option A：維持單 seed concatenation（原實作）
優點：實作最簡單、embedding API 成本最低（一次呼叫）。
缺點：多條件語意稀釋；Top-K 對單條件 atom 偏弱；無可觀測性。

### Option B：多 seed + MMR（Maximal Marginal Relevance）
優點：降低 Top-K 冗餘。
缺點：MMR 需在 Python 端計算 atom 間相似度矩陣，脫離 SQL rerank 管線；與
`bazi.match_knowledge_atoms` 的 weight 結構不相容。**若未來觀察到結果冗餘嚴重，再考慮**。

### Option C：交給 LLM 決定多次檢索（agentic loop）
優點：極端彈性。
缺點：違反 ADR-005；難以評估；延遲與成本不可控。

### Option D：全文 BM25 + 向量混合（教材 ch02 建議）
優點：對古文術語命中友善。
缺點：pgvector 本身不提供 BM25；需引入 `pg_trgm` 或 tsvector 維護成本；且本系統已有
`normalized_tags` + `day_master_tags` 等結構化欄位作為 symbolic filter，BM25 邊際收益有限。
**列為 Phase 3 候選，不列入目前路線圖**。

## Consequences

### Positive
- 多條件查詢 Top-K 精度預期提升（需 Phase 2 評估集量化）
- 檢索日誌可追溯「哪條 seed 命中了哪個 atom」，除錯成本下降
- 架構邊界明確，未來維運者不易誤入 agentic 歧途

### Negative
- 每次 `destiny analyze` 的 embedding API 呼叫從 1 次增至 N 次（N = seed 數）。以預設
  3–5 條 seed、`embed_many` 批次、`text-embedding-3-small` 單價計算，實際成本增幅可忽略
- SQL function 呼叫從 1 次增至 N 次；HNSW 索引下單次查詢 <10ms，預計對使用者感知無影響
- 測試範圍需擴充：fusion 邏輯已加 4 個 unit test（`tests/test_retrieval_fusion.py`）

## Implementation Notes

- 相關檔案：
  - [`src/destiny/retrieval.py`](../../src/destiny/retrieval.py) — 新增 `retrieve_multi_seed()`
  - [`src/destiny/cli.py`](../../src/destiny/cli.py) — `analyze` / `explain` 改用 `_retrieve_for_chart()`
  - [`src/destiny/evaluation.py`](../../src/destiny/evaluation.py) — eval runner 改用 multi-seed
  - [`tests/test_retrieval_fusion.py`](../../tests/test_retrieval_fusion.py) — max / mean / rrf / empty 四項
  - [`docs/architecture/bazi-rag-system-plan.md`](../architecture/bazi-rag-system-plan.md) §3、§4.5

- `per_seed_limit` 預設 20，`top_k` 預設 12，`candidate_limit` 取 `max(50, per_seed_limit * 2)`；
  若 seed 數多（如 ≥8），建議降低 `per_seed_limit` 至 10 以控成本。

- fusion 策略選用指引：
  - 預設 `max`：語意強信號優先
  - 需要多路共識時用 `mean`
  - 分數尺度差異大時用 `rrf`

## Decision Drivers

- 八字查詢本質是**多條件並置**，不是單一語意意圖
- 檢索品質的天花板通常不在 embedding 模型，而在 rerank 與 fusion 策略
- 架構邊界的明確化比演算法複雜度更能影響長期可維運性

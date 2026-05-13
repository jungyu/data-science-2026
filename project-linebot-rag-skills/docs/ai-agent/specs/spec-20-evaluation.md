# Spec-20：Evaluation Framework

> **✅ 已實作；修補 runner 兩個誤判（commit `2387555`）**
>
> - hallucination 案例（`expected_chunks=[]`）走 clarify 不再誤標 `unexpected clarify`
>   — 這類案例本意是測 `forbidden_phrase`，不是測 clarify 路由
> - basic variant 無 answer_contract，不再對 `must_cite_sources` 誤標 failure
> - 驗收測試：`tests/test_eval_runner.py::test_hallucination_case_allows_clarify` +
>   `test_basic_variant_skips_must_cite_failure`

## 背景

本專案教學設計的核心是「**完成基礎後讓學生轉到自己題目**」（[roadmap.md §給學生](../plan/roadmap.md)）。沒有 evaluation，學生在替換 skills、知識庫、Feature Extractor 後**無從驗證自己的 RAG 是不是真的在工作**——只能憑感覺看「回覆好像可以」。這對教學是致命缺陷。

[`docs/RAG/ch06`](../../RAG/ch06-evaluation.md) 整章在講 RAG evaluation；project-destiny `src/destiny/evaluation.py`（ADR-008）與 project-diagnosis [spec-009](../../../../project-diagnosis/docs/specs/spec-009-evaluation-framework.md) 都把 evaluation 視為骨幹。本 spec 把這套思維引進教學專案，並做成**跨三變體可比較**的形式，呼應 spec-19 的對比 demo。

借鑑：destiny evaluation 三項 metric（chart / pattern / atom recall）→ 通用化為 `chunk_recall` / `citation_accuracy` / `judge_pass_rate`；diagnosis spec-009 的 case 結構。

## 設計

### Golden Case Set 結構

存在 `tests/cases/golden.yaml`：

```yaml
- id: case-001
  query: "什麼是 RAG？"
  category: nextjs   # optional：限定 retriever 的 category filter
  expected_chunks:    # 至少要有的 chunk_id 命中（recall 衡量）
    - "kb-rag-overview-001"
    - "kb-rag-pipeline-002"
  must_cite_sources:  # 回覆中必須引用的 source_url 之一
    - "https://nextjs.org/docs/app"
  forbidden_phrases:  # 回覆中禁止出現（防止 hallucination）
    - "我聽說"
    - "可能是因為"
  notes: "FAQ 級基本問題；basic / selfrag / reflection 都該答對"

- id: case-002
  query: "Next.js 14 SSR hydration mismatch 怎麼處理？"
  expected_chunks: [...]
  must_cite_sources: [...]
  notes: "複合條件問題；selfrag 的 multi-seed 應比 basic 命中更多"

- id: case-003
  query: "怎麼用 LangGraph 接 Kubernetes Operator？"
  expected_chunks: []   # 知識庫沒有
  expect_clarification: true   # selfrag / reflection 應走 clarify 分支
  notes: "知識庫沒涵蓋；basic 會強行生成，selfrag 應追問"
```

初版至少 10 個 case，分布：

| 類型 | 數量 |
|---|---|
| FAQ 充分覆蓋（三變體應都通過）| 3 |
| 複合條件（multi-seed 才開始受益）| 3 |
| 知識庫沒涵蓋（測試 sufficiency 分支）| 2 |
| 易誘發 hallucination（測試 grounding）| 2 |

### Metric 定義

| Metric | 公式 | 適用變體 |
|---|---|---|
| `chunk_recall@k` | `len(expected ∩ retrieved_top_k) / len(expected)` | 全部 |
| `citation_accuracy` | 回覆中引用的 source 是否都來自 `retrieved_top_k`（無杜撰）| selfrag / reflection（basic 沒做 grounded citation）|
| `forbidden_phrase_rate` | 回覆含 `forbidden_phrases` 的比率（越低越好）| 全部 |
| `clarification_rate` | `expect_clarification=true` 的 case 是否走 clarify 分支 | selfrag / reflection |
| `judge_pass_rate` | reflection variant 的 judge 通過率（不重 retry）| reflection only |
| `latency_ms` | 端到端 graph invocation 時間 | 全部 |

不做：BLEU / ROUGE / LLM-as-judge for end-to-end 比對——前者對 RAG 不適用，後者把 spec-17 的 judge 重複造輪。

### 跨變體比較表

`scripts/eval.py` 預設輸出：

```
Cases: 10 | Variants: basic, selfrag, reflection

| metric                  | basic | selfrag | reflection |
|-------------------------|-------|---------|------------|
| chunk_recall@k          |  0.62 |   0.81  |    0.81    |
| citation_accuracy       |   n/a |   0.95  |    0.97    |
| forbidden_phrase_rate   |  0.20 |   0.05  |    0.00    |
| clarification_rate      |   n/a |   1.00  |    1.00    |
| judge_pass_rate         |   n/a |    n/a  |    0.85    |
| latency_ms (median)     |  3200 |   5100  |    7400    |

Failed cases:
  basic:      [case-003 hallucinated, case-007 missed expected chunks]
  selfrag:    [case-009 missed citation]
  reflection: [case-009 missed citation]
```

清楚展示「複雜度 vs 品質」trade-off，呼應 ch06「該用哪個」三問題。

### 不做什麼

- 不自動 fail CI（純 reporting；學生自己決定門檻）
- 不做 dataset versioning / DVC（教學版）
- 不做 LLM-as-judge 整體評分（已有 spec-17 4 軸 judge）
- 不做 A/B 線上實驗（屬於 production 議題）

## 介面契約

**新增**：`tests/cases/golden.yaml`、`tests/cases/golden_schema.py`（pydantic 驗證）

```python
class GoldenCase(BaseModel):
    id: str
    query: str
    category: str | None = None
    expected_chunks: list[str] = []
    must_cite_sources: list[str] = []
    forbidden_phrases: list[str] = []
    expect_clarification: bool = False
    notes: str = ""

class GoldenCaseSet(BaseModel):
    cases: list[GoldenCase]
```

**新增**：`app/eval/__init__.py`、`app/eval/metrics.py`、`app/eval/runner.py`

```python
class EvalResult(BaseModel):
    case_id: str
    variant: str
    chunk_recall: float | None
    citation_accuracy: float | None
    forbidden_phrase_hit: bool
    went_to_clarify: bool
    judge_passed: bool | None
    latency_ms: int
    response_excerpt: str
    failure_reasons: list[str]   # 人類可讀，例如 "missed expected chunk: kb-001"


class EvalRunner:
    def __init__(self, services: RuntimeServices) -> None: ...
    async def run(
        self, *, cases: list[GoldenCase], variants: list[str]
    ) -> list[EvalResult]: ...
    def aggregate(self, results: list[EvalResult]) -> dict: ...
```

**新增**：`scripts/eval.py`

```bash
# 三變體全跑
python scripts/eval.py --cases tests/cases/golden.yaml --variants basic,selfrag,reflection

# 只跑特定變體 + 特定 case
python scripts/eval.py --variants reflection --case-id case-001,case-002

# 輸出 JSON 給 CI / 後續分析
python scripts/eval.py --output results.json --format json
```

**整合 push_node**：runner 用 `U_eval_*` 的 `line_user_id` 跳過 LINE push（同 demo_compare_variants 的 mock 模式）。

**整合 spec-17 judge**：reflection variant 的 `judge_passed` 直接從 final state `judge_score` + retry count 推得（pass = `judge.passes()` 且 `retry == 0`）。

## 驗收標準

- `tests/cases/golden.yaml` 至少 10 案例，覆蓋上表四種類型
- `scripts/eval.py` 一鍵跑出三變體的 metric 對比表
- Markdown 對比表能直接複製貼進 `docs/ai-agent/examples/eval-baseline.md`
- 跑同一份 case set 兩次，metric 數字差異 < 5%（embedding / LLM 抖動可接受範圍）
- 學生轉題目後，**改 `golden.yaml` 即可量化驗證**——不需動程式
- 三變體的 metric 對比結果**符合 ch06 的預期**（reflection > selfrag > basic on quality；latency 反向）；不符合時須在 commit 訊息或 PR 描述中說明原因
- 整合測試：在 CI 跑 `scripts/eval.py --quick`（取 3 個 case 的子集），輸出可解析的 JSON

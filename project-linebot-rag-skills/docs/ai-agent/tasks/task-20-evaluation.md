# task-20：Evaluation Framework

> 規格詳見 [spec-20](../specs/spec-20-evaluation.md)
>
> **✅ 已完成（commit `2387555`）** — 實作記錄與驗收測試見 spec-20 頂部「實作狀態」段。
---

實作 golden case set + 6 項 metric + 跨變體比較表。完成後學生能用一行指令量化驗證 RAG 是否在工作。

## 前置

- task-12 ~ task-19 完成（三變體已可切換）
- 需要 `python-yaml` 載 case set（既有 `pyyaml>=6.0` 已有）

## 步驟 1：定義 case schema

新增 `tests/cases/golden_schema.py`：

```python
from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field


class GoldenCase(BaseModel):
    id: str
    query: str
    category: str | None = None
    expected_chunks: list[str] = Field(default_factory=list, description="chunk_id 應命中清單")
    must_cite_sources: list[str] = Field(default_factory=list, description="回覆必須引用的 source")
    forbidden_phrases: list[str] = Field(default_factory=list, description="回覆禁止出現的字串")
    expect_clarification: bool = False
    notes: str = ""


class GoldenCaseSet(BaseModel):
    cases: list[GoldenCase]

    @classmethod
    def load(cls, path: Path) -> "GoldenCaseSet":
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            data = {"cases": data}
        return cls(**data)
```

## 步驟 2：建立 golden case 範本

新增 `tests/cases/golden.yaml`，至少 10 個 case 分四類：

```yaml
cases:
  # FAQ 充分覆蓋（三變體應都通過）
  - id: faq-001
    query: "什麼是 RAG？"
    expected_chunks: ["kb-rag-overview-001"]
    notes: "FAQ 級基本問題"
  - id: faq-002
    query: "RAG 的三個主要步驟是什麼？"
    expected_chunks: ["kb-rag-pipeline-002"]
  - id: faq-003
    query: "向量檢索與全文檢索的差異？"
    expected_chunks: ["kb-vector-vs-fulltext-001"]

  # 複合條件（multi-seed 才開始受益）
  - id: multi-001
    query: "Next.js 14 App Router 的 SSR 怎麼做？"
    expected_chunks: ["kb-nextjs-app-router-ssr-001", "kb-nextjs-rsc-002"]
  - id: multi-002
    query: "pgvector 與 Pinecone 在維度上限的差異？"
    expected_chunks: ["kb-pgvector-limits-001", "kb-pinecone-limits-001"]
  - id: multi-003
    query: "用 Claude 做 RAG 需要哪些 SDK 與 API key？"
    expected_chunks: ["kb-claude-sdk-001"]

  # 知識庫沒涵蓋（測試 sufficiency 分支）
  - id: gap-001
    query: "怎麼用 LangGraph 接 Kubernetes Operator？"
    expected_chunks: []
    expect_clarification: true
  - id: gap-002
    query: "MCP server 與 OpenAI plugin 的差別？"
    expected_chunks: []
    expect_clarification: true

  # 易誘發 hallucination（測試 grounding）
  - id: ground-001
    query: "請列出 RAG 系統的所有評估指標"
    forbidden_phrases: ["所有", "完全", "無一例外"]
    notes: "知識庫只有部分；不可宣稱完整"
  - id: ground-002
    query: "Anthropic 是哪一年提供 embedding API 的？"
    forbidden_phrases: ["2023 年", "2024 年", "已提供"]
    notes: "Anthropic 並無原生 embedding API"
```

> ⚠️ `expected_chunks` 的 chunk_id 取決於實際 ingest 進來的資料。學生轉題目時這份 case set 完全替換。

## 步驟 3：實作 metrics

新增 `app/eval/__init__.py`（空）與 `app/eval/metrics.py`：

```python
from __future__ import annotations

from app.rag.schemas import KnowledgeChunk
from tests.cases.golden_schema import GoldenCase


def chunk_recall_at_k(case: GoldenCase, retrieved: list[KnowledgeChunk]) -> float | None:
    if not case.expected_chunks:
        return None
    retrieved_ids = {c.id for c in retrieved}
    hit = sum(1 for eid in case.expected_chunks if eid in retrieved_ids)
    return hit / len(case.expected_chunks)


def citation_accuracy(retrieved: list[KnowledgeChunk], cited_chunk_ids: list[str]) -> float | None:
    """回覆中引用的 chunk_id 是否都在 retrieved 集合內（無杜撰）。"""
    if not cited_chunk_ids:
        return None
    retrieved_ids = {c.id for c in retrieved}
    valid = sum(1 for cid in cited_chunk_ids if cid in retrieved_ids)
    return valid / len(cited_chunk_ids)


def forbidden_phrase_hit(case: GoldenCase, response_text: str) -> bool:
    return any(p in response_text for p in case.forbidden_phrases)


def must_cite_satisfied(case: GoldenCase, cited_sources: list[str]) -> bool | None:
    if not case.must_cite_sources:
        return None
    return any(any(req in src for src in cited_sources) for req in case.must_cite_sources)
```

## 步驟 4：實作 EvalRunner

新增 `app/eval/runner.py`：

```python
from __future__ import annotations

import time
from dataclasses import dataclass

from pydantic import BaseModel

from app.dependencies import RuntimeServices
from app.eval.metrics import (
    chunk_recall_at_k,
    citation_accuracy,
    forbidden_phrase_hit,
    must_cite_satisfied,
)
from app.graph.variants import VARIANT_BUILDERS
from tests.cases.golden_schema import GoldenCase


class EvalResult(BaseModel):
    case_id: str
    variant: str
    chunk_recall: float | None = None
    citation_accuracy: float | None = None
    forbidden_phrase_hit: bool = False
    went_to_clarify: bool = False
    judge_passed: bool | None = None
    latency_ms: int = 0
    response_excerpt: str = ""
    failure_reasons: list[str] = []


class EvalRunner:
    def __init__(self, services: RuntimeServices) -> None:
        self._services = services

    async def run_case(self, case: GoldenCase, variant: str) -> EvalResult:
        builder = VARIANT_BUILDERS[variant]
        graph = builder(self._services)

        t0 = time.time()
        final = await graph.ainvoke(
            {
                "user_input": case.query,
                "line_user_id": f"U_eval_{case.id}",  # U_eval 前綴跳過 push
                "recent_history": "",
            }
        )
        latency_ms = int((time.time() - t0) * 1000)

        retrieved = final.get("rag_chunks") or []
        responses = final.get("responses") or []
        response_text = "\n".join(responses)
        contract = final.get("answer_contract")
        cited_chunk_ids = (
            [cit.chunk_id for cit in contract.citations] if contract else []
        )
        cited_sources = (
            [cit.source for cit in contract.citations] if contract else []
        )

        went_to_clarify = bool(final.get("clarification_questions"))
        score = final.get("judge_score")
        judge_passed = (
            score.passes(
                min_axis=self._services.settings.judge_min_axis,
                min_mean=self._services.settings.judge_min_mean,
            )
            if score is not None
            else None
        )

        failures: list[str] = []
        if case.expect_clarification and not went_to_clarify:
            failures.append("expected clarify but went to generate")
        if forbidden_phrase_hit(case, response_text):
            failures.append(f"hit forbidden phrase: {case.forbidden_phrases}")
        if must_cite_satisfied(case, cited_sources) is False:
            failures.append(f"missing required citation: {case.must_cite_sources}")

        return EvalResult(
            case_id=case.id,
            variant=variant,
            chunk_recall=chunk_recall_at_k(case, retrieved),
            citation_accuracy=citation_accuracy(retrieved, cited_chunk_ids),
            forbidden_phrase_hit=forbidden_phrase_hit(case, response_text),
            went_to_clarify=went_to_clarify,
            judge_passed=judge_passed,
            latency_ms=latency_ms,
            response_excerpt=response_text[:300],
            failure_reasons=failures,
        )

    async def run(
        self, *, cases: list[GoldenCase], variants: list[str]
    ) -> list[EvalResult]:
        results: list[EvalResult] = []
        for variant in variants:
            for case in cases:
                results.append(await self.run_case(case, variant))
        return results

    @staticmethod
    def aggregate(results: list[EvalResult]) -> dict:
        by_variant: dict[str, list[EvalResult]] = {}
        for r in results:
            by_variant.setdefault(r.variant, []).append(r)

        def _avg(xs):
            xs = [x for x in xs if x is not None]
            return sum(xs) / len(xs) if xs else None

        out = {}
        for variant, rs in by_variant.items():
            out[variant] = {
                "n": len(rs),
                "chunk_recall_avg": _avg(r.chunk_recall for r in rs),
                "citation_accuracy_avg": _avg(r.citation_accuracy for r in rs),
                "forbidden_phrase_rate": sum(r.forbidden_phrase_hit for r in rs) / len(rs),
                "clarification_rate": sum(r.went_to_clarify for r in rs) / len(rs),
                "judge_pass_rate": _avg([1.0 if r.judge_passed else 0.0 for r in rs if r.judge_passed is not None]),
                "latency_ms_median": sorted(r.latency_ms for r in rs)[len(rs) // 2],
                "failed": [r.case_id for r in rs if r.failure_reasons],
            }
        return out
```

## 步驟 5：擴充 push_node 跳過 U_eval 前綴

修改 `app/graph/nodes.py::push_node`（task-19 已加 U_demo skip，本步驟擴充）：

```python
async def push_node(state: RAGState, services: Any) -> dict[str, Any]:
    user_id = state.get("line_user_id", "")
    if user_id.startswith(("U_demo", "U_eval")):
        logger.info("(non-prod mode) skip LINE push: %s", user_id)
        return {}
    await services.line_client.push_text(user_id, state["responses"])
    return {}
```

## 步驟 6：CLI

新增 `scripts/eval.py`：

```python
"""跑 golden case set，輸出三變體 metric 對比表。

用法：
    python scripts/eval.py --cases tests/cases/golden.yaml
    python scripts/eval.py --variants reflection --case-id faq-001,gap-001
    python scripts/eval.py --output results.json --format json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.dependencies import get_runtime_services
from app.eval.runner import EvalRunner
from tests.cases.golden_schema import GoldenCaseSet


def render_table(agg: dict) -> str:
    headers = ["metric", *agg.keys()]
    rows = [
        ("chunk_recall_avg", *(f"{agg[v]['chunk_recall_avg']:.2f}" if agg[v]['chunk_recall_avg'] else "n/a" for v in agg)),
        ("citation_accuracy_avg", *(f"{agg[v]['citation_accuracy_avg']:.2f}" if agg[v]['citation_accuracy_avg'] else "n/a" for v in agg)),
        ("forbidden_phrase_rate", *(f"{agg[v]['forbidden_phrase_rate']:.2f}" for v in agg)),
        ("clarification_rate", *(f"{agg[v]['clarification_rate']:.2f}" for v in agg)),
        ("judge_pass_rate", *(f"{agg[v]['judge_pass_rate']:.2f}" if agg[v]['judge_pass_rate'] else "n/a" for v in agg)),
        ("latency_ms_median", *(str(agg[v]['latency_ms_median']) for v in agg)),
    ]
    out = ["| " + " | ".join(headers) + " |"]
    out.append("|" + "|".join(["-" * 4] * len(headers)) + "|")
    for row in rows:
        out.append("| " + " | ".join(str(c) for c in row) + " |")
    return "\n".join(out)


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", default="tests/cases/golden.yaml")
    parser.add_argument("--variants", default="basic,selfrag,reflection")
    parser.add_argument("--case-id", default=None)
    parser.add_argument("--output", default=None)
    parser.add_argument("--format", choices=["table", "json"], default="table")
    parser.add_argument("--quick", action="store_true", help="只跑前 3 個 case")
    args = parser.parse_args()

    case_set = GoldenCaseSet.load(Path(args.cases))
    cases = case_set.cases
    if args.case_id:
        ids = set(args.case_id.split(","))
        cases = [c for c in cases if c.id in ids]
    if args.quick:
        cases = cases[:3]

    variants = args.variants.split(",")
    services = get_runtime_services()
    runner = EvalRunner(services)

    print(f"Cases: {len(cases)} | Variants: {', '.join(variants)}")
    results = await runner.run(cases=cases, variants=variants)
    agg = runner.aggregate(results)

    if args.format == "json":
        payload = {"results": [r.model_dump() for r in results], "aggregate": agg}
        text = json.dumps(payload, ensure_ascii=False, indent=2)
    else:
        text = render_table(agg) + "\n\nFailed cases:\n"
        for v, info in agg.items():
            text += f"  {v}: {info['failed'] or '(none)'}\n"

    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        print("\n" + text)


if __name__ == "__main__":
    asyncio.run(main())
```

## 步驟 7：測試

新增 `tests/test_eval_metrics.py`：

```python
from app.eval.metrics import (
    chunk_recall_at_k,
    citation_accuracy,
    forbidden_phrase_hit,
)
from tests.cases.golden_schema import GoldenCase


def test_chunk_recall_full():
    case = GoldenCase(id="x", query="x", expected_chunks=["a", "b"])
    retrieved = [_chunk("a"), _chunk("b"), _chunk("c")]
    assert chunk_recall_at_k(case, retrieved) == 1.0


def test_chunk_recall_partial():
    case = GoldenCase(id="x", query="x", expected_chunks=["a", "b"])
    retrieved = [_chunk("a"), _chunk("c")]
    assert chunk_recall_at_k(case, retrieved) == 0.5


def test_citation_accuracy_no_hallucination():
    retrieved = [_chunk("a"), _chunk("b")]
    assert citation_accuracy(retrieved, ["a", "b"]) == 1.0


def test_citation_accuracy_detects_fabrication():
    retrieved = [_chunk("a")]
    assert citation_accuracy(retrieved, ["a", "fabricated"]) == 0.5


def test_forbidden_phrase_hit():
    case = GoldenCase(id="x", query="x", forbidden_phrases=["所有", "完全"])
    assert forbidden_phrase_hit(case, "這涵蓋所有情況")
    assert not forbidden_phrase_hit(case, "這涵蓋大部分情況")


def _chunk(id):
    from app.rag.schemas import KnowledgeChunk
    return KnowledgeChunk(id=id, content=id, category="general")
```

新增 `tests/test_eval_runner.py`：

```python
import pytest

from app.eval.runner import EvalRunner
from tests.cases.golden_schema import GoldenCase


@pytest.mark.asyncio
async def test_runner_against_stub(stub_services):
    runner = EvalRunner(stub_services)
    cases = [
        GoldenCase(id="x1", query="什麼是 RAG？", expected_chunks=["chunk-1"]),
    ]
    results = await runner.run(cases=cases, variants=["basic", "selfrag", "reflection"])
    assert len(results) == 3
    by_variant = {r.variant: r for r in results}
    # stub chunks 含 chunk-1 → recall 應 ≥ 0
    assert by_variant["selfrag"].chunk_recall is not None


@pytest.mark.asyncio
async def test_aggregate_shape(stub_services):
    runner = EvalRunner(stub_services)
    results = await runner.run(
        cases=[GoldenCase(id="x", query="?")],
        variants=["basic"],
    )
    agg = runner.aggregate(results)
    assert "basic" in agg
    assert "n" in agg["basic"]
```

## 步驟 8：教學配套

新增 `docs/ai-agent/examples/eval-baseline.md`：學生轉題目後 T1 結束時要交的「baseline metric」範本（用真實跑過的數字填）。模板示意：

```markdown
# Eval Baseline — <領域名稱>

跑於 <date>，case set: tests/cases/golden.yaml（N=10）

| metric | basic | selfrag | reflection |
|--------|-------|---------|------------|
| chunk_recall_avg | 0.62 | 0.81 | 0.81 |
| citation_accuracy_avg | n/a | 0.95 | 0.97 |
| forbidden_phrase_rate | 0.20 | 0.05 | 0.00 |
| clarification_rate | n/a | 0.20 | 0.20 |
| judge_pass_rate | n/a | n/a | 0.85 |
| latency_ms_median | 3200 | 5100 | 7400 |

Failed cases:
- basic: [gap-001 hallucinated, ground-001 hit forbidden]
- selfrag: [...]
- reflection: [...]

觀察：
- multi-seed 在 multi-001/002 上 recall 相對 basic 提升 30%
- judge 在 ground-001/002 上抓出 reflection 才會通過的杜撰
```

## 請輸出

1. `tests/cases/golden_schema.py`、`tests/cases/golden.yaml`
2. `app/eval/__init__.py`、`app/eval/metrics.py`、`app/eval/runner.py`
3. 修改後的 `app/graph/nodes.py::push_node`（U_eval 前綴跳過）
4. `scripts/eval.py`
5. `tests/test_eval_metrics.py`、`tests/test_eval_runner.py`
6. `docs/ai-agent/examples/eval-baseline.md`
7. README 加「跑 evaluation」段

## 驗收指令

```bash
pytest tests/test_eval_metrics.py tests/test_eval_runner.py -v
pytest

# 跑 quick 模式（CI / 開發用）
CHECKPOINT_BACKEND=none python scripts/eval.py --quick

# 完整跑（需要 .env 配好的 LLM + Supabase / sqlite-vec）
CHECKPOINT_BACKEND=none python scripts/eval.py

# 輸出 JSON 給後續分析
CHECKPOINT_BACKEND=none python scripts/eval.py --output baseline.json --format json
```

> ⚠️ **`CHECKPOINT_BACKEND=none` 必設**（[W2-W8 e2e 驗收](../examples/w2-w8-e2e-verification.md)
> §「對 lesson plan 的累積 feedback」 6 發現）
>
> 預設 `checkpoint_backend=memory` 時，reflection variant compile 帶 checkpointer，
> langgraph 會要求 `config={"configurable": {"thread_id": ...}}`；但 `EvalRunner.run_case`
> 內部 `graph.ainvoke(state)` 沒帶 config → raise `ValueError: Checkpointer requires
> ... thread_id`。
>
> 解法：跑 eval 時禁用 checkpointer（眼下不需要 HITL / persistence）。長期應該在
> runner 內自動生 `thread_id=f"eval-{case.id}-{variant}"`，但教學版優先讓學生看到指令成功。

驗收通過條件：

- 新增的 8 個單元測試全綠
- `python scripts/eval.py --quick` 在無真實 LLM 配置下也能跑（fallback 模式）
- 對同一 case set 跑兩次，metric 差異 < 5%
- 三變體的 metric 對比結果**符合 ch06 預期**：reflection ≥ selfrag ≥ basic on quality；latency 反向

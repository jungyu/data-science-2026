"""Evaluation runner (Spec-009) — 從 bazi.evaluation_cases 拉案例跑 Phase 0 指標。

Phase 0 支援：
- Layer A：排盤欄位比對（day_master / month_commander / season）
- Layer B：規則候選格局命中率
- Layer C：atom_code 召回命中率（top-k 是否包含 expected_atom_codes）

Layer D（生成品質）需人工或 LLM-as-judge，本版暫不自動化。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

import psycopg
from psycopg.rows import dict_row

from destiny.bazi_engine import compute_chart
from destiny.config import Settings
from destiny.embeddings import EmbeddingClient
from destiny.retrieval import retrieve_multi_seed
from destiny.rule_engine import run_rules


@dataclass
class CaseResult:
    case_code: str
    chart_match: dict[str, bool] = field(default_factory=dict)
    pattern_hit: bool | None = None
    atom_hits: list[str] = field(default_factory=list)
    atom_recall: float | None = None
    notes: str = ""

    @property
    def passed_chart(self) -> bool:
        return all(self.chart_match.values()) if self.chart_match else True


@dataclass
class EvaluationSummary:
    total: int
    chart_pass: int
    pattern_pass: int
    atom_recall_mean: float
    results: list[CaseResult]


def _load_cases(conn: psycopg.Connection) -> list[dict]:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            """
            SELECT case_code, input_payload, expected_chart,
                   expected_features, expected_atom_codes, expected_source_books
            FROM bazi.evaluation_cases
            WHERE status = 'active'
            ORDER BY case_code
            """
        )
        return cur.fetchall()


def _compare_chart(expected: dict | None, actual_dump: dict) -> dict[str, bool]:
    if not expected:
        return {}
    checks: dict[str, bool] = {}
    for key in ("day_master", "month_commander", "season"):
        if key in expected:
            checks[key] = expected[key] == actual_dump.get(key)
    return checks


def _pattern_hit(expected_features: dict | None, candidate_patterns: list[str]) -> bool | None:
    if not expected_features or "candidate_patterns" not in expected_features:
        return None
    expected_patterns = expected_features["candidate_patterns"]
    return any(p in candidate_patterns for p in expected_patterns)


def run_evaluation(
    settings: Settings,
    conn: psycopg.Connection,
    embedder: EmbeddingClient,
    top_k: int = 8,
) -> EvaluationSummary:
    cases = _load_cases(conn)
    results: list[CaseResult] = []

    for case in cases:
        code = case["case_code"]
        inp = case["input_payload"]
        result = CaseResult(case_code=code)

        try:
            chart = compute_chart(
                birth_datetime=inp["birth_datetime"],
                timezone=inp.get("timezone", "Asia/Taipei"),
                longitude=inp.get("longitude"),
                use_true_solar_time=inp.get("use_true_solar_time", False),
            )
        except Exception as e:
            result.notes = f"排盤失敗: {e}"
            results.append(result)
            continue

        actual = chart.model_dump()
        actual["month_commander"] = chart.month_commander
        result.chart_match = _compare_chart(case.get("expected_chart"), actual)

        rules = run_rules(chart)
        result.pattern_hit = _pattern_hit(
            case.get("expected_features"),
            [p.pattern for p in rules.candidate_patterns],
        )

        expected_atoms = case.get("expected_atom_codes") or []
        if isinstance(expected_atoms, str):
            expected_atoms = json.loads(expected_atoms)

        if expected_atoms and rules.retrieval_query_seeds:
            hits = retrieve_multi_seed(
                conn, embedder,
                seeds=rules.retrieval_query_seeds,
                day_master_tags=[chart.day_master],
                month_branch_tags=[chart.month_commander],
                pattern_tags=[p.pattern for p in rules.candidate_patterns],
                seasonal_tags=[chart.season, *rules.seasonal_adjustment_needed],
                top_k=top_k,
            )
            hit_codes = {h.atom_code for h in hits}
            result.atom_hits = sorted(hit_codes & set(expected_atoms))
            result.atom_recall = len(result.atom_hits) / len(expected_atoms)

        results.append(result)

    chart_pass = sum(1 for r in results if r.passed_chart)
    pattern_checked = [r for r in results if r.pattern_hit is not None]
    pattern_pass = sum(1 for r in pattern_checked if r.pattern_hit)
    recall_values = [r.atom_recall for r in results if r.atom_recall is not None]
    recall_mean = sum(recall_values) / len(recall_values) if recall_values else 0.0

    return EvaluationSummary(
        total=len(results),
        chart_pass=chart_pass,
        pattern_pass=pattern_pass,
        atom_recall_mean=recall_mean,
        results=results,
    )

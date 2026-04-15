#!/usr/bin/env python3
"""
Evaluation harness for the TCM diagnostic RAG MVP.

Reads tests/cases.yaml, runs each query through the same pipeline as
answer_query.py, and checks the assertions declared per case.

Exit code:
  0 — all cases pass
  1 — at least one case failed
  2 — configuration / environment error

Environment variables:
  DATABASE_URL               - required
  OPENAI_API_KEY             - optional (enables vector route)
  OPENAI_EMBEDDING_MODEL     - optional (default: text-embedding-3-small)
  EVAL_CASES_FILE            - optional (default: tests/cases.yaml)
  EVAL_TOP_K                 - optional (default: 5)
  EVAL_VERBOSE               - optional (default: false) dump full answer on failure
"""

from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import psycopg
import yaml

from answer_query import (
    detect_missing,
    embed_query,
    extract_features,
    load_feature_dictionary,
    rank_patterns,
    resolve_atom_names,
)
from apply_rules import apply_rules, load_active_rules


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("eval_queries")

REPO_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------
# Config
# ---------------------------------------------------------

@dataclass(frozen=True)
class Settings:
    database_url: str
    openai_api_key: str | None
    embedding_model: str
    cases_file: Path
    top_k: int
    verbose: bool


def load_settings() -> Settings:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        raise ValueError("Missing required environment variable: DATABASE_URL")

    cases_file = Path(os.getenv("EVAL_CASES_FILE", str(REPO_ROOT / "tests" / "cases.yaml")))

    return Settings(
        database_url=database_url,
        openai_api_key=(os.getenv("OPENAI_API_KEY") or "").strip() or None,
        embedding_model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small").strip(),
        cases_file=cases_file,
        top_k=int(os.getenv("EVAL_TOP_K", "5")),
        verbose=os.getenv("EVAL_VERBOSE", "").strip().lower() in {"1", "true", "yes", "on"},
    )


# ---------------------------------------------------------
# Pipeline execution (shared with answer_query)
# ---------------------------------------------------------

@dataclass
class PipelineResult:
    symptoms: list[str]
    signs: list[str]
    tongue: list[str]
    pulse: list[str]
    missing: list[str]
    candidates: list[dict[str, Any]]
    rule_outcomes: list[dict[str, Any]]
    ambiguity_flags: list[str]
    suggested_questions: list[str]


def run_pipeline(
    conn: psycopg.Connection,
    settings: Settings,
    query_text: str,
    dictionary,
) -> PipelineResult:
    features = extract_features(query_text, dictionary)
    missing = detect_missing(features, query_text)

    query_embedding = None
    if settings.openai_api_key:
        try:
            query_embedding = embed_query(
                settings.openai_api_key,
                settings.embedding_model,
                query_text,
            )
        except Exception as exc:
            logger.warning("Embedding failed, continuing without vector: %s", exc)

    candidates = rank_patterns(
        conn=conn,
        feature_atom_ids=[f.atom_id for f in features],
        query_embedding=query_embedding,
        query_fts=query_text,
        top_k=settings.top_k,
    )

    rules = load_active_rules(conn)
    rule_result = apply_rules(
        rules=rules,
        features=features,
        candidates=candidates,
        missing_categories=missing,
    )

    return PipelineResult(
        symptoms=[f.canonical_name for f in features if f.atom_type == "symptom"],
        signs=[f.canonical_name for f in features if f.atom_type == "sign"],
        tongue=[f.canonical_name for f in features if f.atom_type == "tongue_feature"],
        pulse=[f.canonical_name for f in features if f.atom_type == "pulse_feature"],
        missing=missing,
        candidates=[
            {
                "pattern_id": c.pattern_id,
                "pattern_name": c.pattern_name,
                "score": c.final_score,
            }
            for c in rule_result.adjusted_candidates
        ],
        rule_outcomes=[
            {"rule_code": o.rule_code, "matched": o.matched, "scope": o.scope}
            for o in rule_result.outcomes
        ],
        ambiguity_flags=rule_result.ambiguity_flags,
        suggested_questions=rule_result.suggested_questions,
    )


# ---------------------------------------------------------
# Assertions
# ---------------------------------------------------------

@dataclass
class AssertionResult:
    name: str
    passed: bool
    detail: str


def check_case(expect: dict[str, Any], result: PipelineResult) -> list[AssertionResult]:
    checks: list[AssertionResult] = []
    top_names = [c["pattern_name"] for c in result.candidates]
    matched_rules = [o["rule_code"] for o in result.rule_outcomes if o["matched"]]

    if "extracted_symptoms_any_of" in expect:
        want = set(expect["extracted_symptoms_any_of"])
        hit = want.intersection(result.symptoms)
        checks.append(AssertionResult(
            name="extracted_symptoms_any_of",
            passed=bool(hit),
            detail=f"want any of {sorted(want)}, got {result.symptoms}",
        ))

    if "extracted_tongue_includes" in expect:
        want = set(expect["extracted_tongue_includes"])
        missing = want - set(result.tongue)
        checks.append(AssertionResult(
            name="extracted_tongue_includes",
            passed=not missing,
            detail=f"missing {sorted(missing)} (got {result.tongue})",
        ))

    if "missing_includes" in expect:
        want = set(expect["missing_includes"])
        missing = want - set(result.missing)
        checks.append(AssertionResult(
            name="missing_includes",
            passed=not missing,
            detail=f"missing {sorted(missing)} from {result.missing}",
        ))

    if "top_pattern" in expect:
        want = expect["top_pattern"]
        got = top_names[0] if top_names else None
        checks.append(AssertionResult(
            name="top_pattern",
            passed=got == want,
            detail=f"want '{want}', got '{got}'",
        ))

    if "top3_includes_any_of" in expect:
        want = set(expect["top3_includes_any_of"])
        hit = want.intersection(top_names[:3])
        checks.append(AssertionResult(
            name="top3_includes_any_of",
            passed=bool(hit),
            detail=f"want any of {sorted(want)}, top3={top_names[:3]}",
        ))

    if "rule_codes_triggered_any_of" in expect:
        want = set(expect["rule_codes_triggered_any_of"])
        hit = want.intersection(matched_rules)
        checks.append(AssertionResult(
            name="rule_codes_triggered_any_of",
            passed=bool(hit),
            detail=f"want any of {sorted(want)}, triggered={matched_rules}",
        ))

    if "has_ambiguity_flag" in expect:
        want = bool(expect["has_ambiguity_flag"])
        got = bool(result.ambiguity_flags)
        checks.append(AssertionResult(
            name="has_ambiguity_flag",
            passed=want == got,
            detail=f"want {want}, flags={result.ambiguity_flags}",
        ))

    if "has_suggested_question" in expect:
        want = bool(expect["has_suggested_question"])
        got = bool(result.suggested_questions)
        checks.append(AssertionResult(
            name="has_suggested_question",
            passed=want == got,
            detail=f"want {want}, questions={result.suggested_questions}",
        ))

    if "yin_heat_rank_min" in expect:
        want_min_rank = int(expect["yin_heat_rank_min"])  # 1-based; rank_min=3 means must be rank 3 or later
        rank = None
        for i, name in enumerate(top_names, start=1):
            if name == "陰虛內熱":
                rank = i
                break
        passed = (rank is None) or (rank >= want_min_rank)
        checks.append(AssertionResult(
            name="yin_heat_rank_min",
            passed=passed,
            detail=f"want rank>={want_min_rank}, got rank={rank} (top_names={top_names[:3]})",
        ))

    return checks


# ---------------------------------------------------------
# Reporting
# ---------------------------------------------------------

def print_case_report(
    case: dict[str, Any],
    result: PipelineResult,
    checks: list[AssertionResult],
    verbose: bool,
) -> bool:
    case_passed = all(c.passed for c in checks)
    status = "PASS" if case_passed else "FAIL"
    print(f"[{status}] {case.get('id')} — {case.get('description', '')}")

    for c in checks:
        icon = "  ✓" if c.passed else "  ✗"
        print(f"{icon} {c.name}: {c.detail}")

    if not case_passed or verbose:
        print("  --- pipeline snapshot ---")
        print(f"  symptoms={result.symptoms}")
        print(f"  tongue={result.tongue}  pulse={result.pulse}")
        print(f"  missing={result.missing}")
        print(f"  top={[(c['pattern_name'], round(c['score'], 3)) for c in result.candidates[:5]]}")
        print(f"  matched_rules={[o['rule_code'] for o in result.rule_outcomes if o['matched']]}")
        print(f"  flags={result.ambiguity_flags}")
        print(f"  questions={result.suggested_questions}")
        print()

    return case_passed


# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

def run() -> int:
    try:
        settings = load_settings()
    except ValueError as exc:
        logger.error("Failed to load settings: %s", exc)
        return 2

    if not settings.cases_file.exists():
        logger.error("Cases file not found: %s", settings.cases_file)
        return 2

    with settings.cases_file.open(encoding="utf-8") as f:
        spec = yaml.safe_load(f)

    cases = spec.get("cases", [])
    if not cases:
        logger.error("No cases declared in %s", settings.cases_file)
        return 2

    try:
        with psycopg.connect(settings.database_url) as conn:
            dictionary = load_feature_dictionary(conn)
            logger.info("Loaded %s dictionary entries.", len(dictionary))
            logger.info("Running %s cases...\n", len(cases))

            total_passed = 0
            total_failed = 0

            for case in cases:
                try:
                    result = run_pipeline(conn, settings, case["query"], dictionary)
                    checks = check_case(case.get("expect", {}), result)
                    case_passed = print_case_report(case, result, checks, settings.verbose)
                    if case_passed:
                        total_passed += 1
                    else:
                        total_failed += 1
                except Exception as exc:
                    logger.error("Case %s crashed: %s", case.get("id"), exc)
                    total_failed += 1

    except psycopg.OperationalError as exc:
        logger.error("Database connection error: %s", exc)
        return 2

    print(f"\nResults: {total_passed} passed, {total_failed} failed, {len(cases)} total.")
    return 0 if total_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(run())

#!/usr/bin/env python3
"""
Diagnostic rules evaluator.

Applies active rows in public.diagnostic_rules to a candidate pattern
ranking result, producing:
  - score adjustments (boost / penalty)
  - ambiguity flags
  - suggested follow-up questions

Rule JSONB shape (see seed.sql and spec §9):

  conditions:
    {
      "all_of":    [{"type": "symptom", "value": "盜汗"}],
      "any_of":    [{"type": "tongue_feature", "value": "舌紅少苔"}],
      "none_of":   [{"type": "sign", "value": "畏寒"}],
      "missing":   ["pulse_feature"],
      "any_candidate_patterns": ["陰虛內熱"]
    }

  actions:
    {
      "action": "boost_pattern" | "flag_ambiguous" | "suggest_question",
      "pattern_id": "...",
      "boost": 0.40,
      "message": "...",
      "suggest_question": "..."
    }

This module is pure: it takes dicts in, returns dicts out.
I/O is the caller's responsibility.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable


# ---------------------------------------------------------
# Input / output types
# ---------------------------------------------------------

@dataclass
class FeatureHit:
    atom_id: str
    atom_type: str          # symptom | sign | tongue_feature | pulse_feature
    canonical_name: str


@dataclass
class PatternCandidate:
    pattern_id: str
    pattern_name: str
    pattern_family: str | None
    final_score: float
    supporting_feature_ids: list[str] = field(default_factory=list)
    conflicting_feature_ids: list[str] = field(default_factory=list)


@dataclass
class RuleRow:
    rule_code: str
    rule_name: str
    rule_scope: str         # pattern_ranking | differential_diagnosis | question_suggestion | contraindication
    priority: int
    conditions: dict[str, Any]
    actions: dict[str, Any]
    explanation: str | None


@dataclass
class RuleOutcome:
    rule_code: str
    rule_name: str
    scope: str
    matched: bool
    score_delta: float = 0.0
    affected_pattern_id: str | None = None
    flag_message: str | None = None
    suggested_question: str | None = None


@dataclass
class RulesResult:
    adjusted_candidates: list[PatternCandidate]
    outcomes: list[RuleOutcome]
    suggested_questions: list[str]
    ambiguity_flags: list[str]


# ---------------------------------------------------------
# Condition matcher
# ---------------------------------------------------------

def _features_by_key(features: Iterable[FeatureHit]) -> set[tuple[str, str]]:
    return {(f.atom_type, f.canonical_name) for f in features}


def _feature_clause_matches(
    clause: dict[str, Any],
    feature_keys: set[tuple[str, str]],
) -> bool:
    atom_type = clause.get("type")
    value = clause.get("value")
    if not atom_type or not value:
        return False
    return (atom_type, value) in feature_keys


def _conditions_match(
    conditions: dict[str, Any],
    features: list[FeatureHit],
    candidate_pattern_names: set[str],
    missing_categories: set[str],
) -> bool:
    feature_keys = _features_by_key(features)

    all_of = conditions.get("all_of") or []
    if all_of and not all(_feature_clause_matches(c, feature_keys) for c in all_of):
        return False

    any_of = conditions.get("any_of") or []
    if any_of and not any(_feature_clause_matches(c, feature_keys) for c in any_of):
        return False

    none_of = conditions.get("none_of") or []
    if none_of and any(_feature_clause_matches(c, feature_keys) for c in none_of):
        return False

    missing = conditions.get("missing") or []
    if missing and not all(cat in missing_categories for cat in missing):
        return False

    any_candidate = conditions.get("any_candidate_patterns") or []
    if any_candidate and not any(name in candidate_pattern_names for name in any_candidate):
        return False

    return True


# ---------------------------------------------------------
# Action applier
# ---------------------------------------------------------

def _apply_action(
    rule: RuleRow,
    candidates_by_id: dict[str, PatternCandidate],
) -> RuleOutcome:
    action = rule.actions.get("action")
    outcome = RuleOutcome(
        rule_code=rule.rule_code,
        rule_name=rule.rule_name,
        scope=rule.rule_scope,
        matched=True,
    )

    if action == "boost_pattern":
        pattern_id = rule.actions.get("pattern_id")
        boost = float(rule.actions.get("boost", 0.0))
        if pattern_id and pattern_id in candidates_by_id:
            candidates_by_id[pattern_id].final_score += boost
            outcome.score_delta = boost
            outcome.affected_pattern_id = pattern_id

    elif action == "flag_ambiguous":
        outcome.flag_message = rule.actions.get("message")
        outcome.suggested_question = rule.actions.get("suggest_question")

    elif action == "suggest_question":
        outcome.suggested_question = rule.actions.get("message") or rule.actions.get(
            "suggest_question"
        )

    return outcome


# ---------------------------------------------------------
# Entry point
# ---------------------------------------------------------

def apply_rules(
    rules: list[RuleRow],
    features: list[FeatureHit],
    candidates: list[PatternCandidate],
    missing_categories: list[str] | None = None,
) -> RulesResult:
    missing_set = set(missing_categories or [])
    candidate_names = {c.pattern_name for c in candidates}
    candidates_by_id = {c.pattern_id: c for c in candidates}

    outcomes: list[RuleOutcome] = []

    sorted_rules = sorted(rules, key=lambda r: r.priority)

    for rule in sorted_rules:
        if not _conditions_match(
            conditions=rule.conditions or {},
            features=features,
            candidate_pattern_names=candidate_names,
            missing_categories=missing_set,
        ):
            outcomes.append(
                RuleOutcome(
                    rule_code=rule.rule_code,
                    rule_name=rule.rule_name,
                    scope=rule.rule_scope,
                    matched=False,
                )
            )
            continue

        outcomes.append(_apply_action(rule, candidates_by_id))

    adjusted = sorted(
        candidates_by_id.values(),
        key=lambda c: c.final_score,
        reverse=True,
    )

    suggested_questions = [
        o.suggested_question for o in outcomes if o.matched and o.suggested_question
    ]
    ambiguity_flags = [
        o.flag_message for o in outcomes if o.matched and o.flag_message
    ]

    return RulesResult(
        adjusted_candidates=adjusted,
        outcomes=outcomes,
        suggested_questions=suggested_questions,
        ambiguity_flags=ambiguity_flags,
    )


# ---------------------------------------------------------
# DB loader (optional convenience)
# ---------------------------------------------------------

def load_active_rules(conn) -> list[RuleRow]:
    """Load all active diagnostic rules from PostgreSQL."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT rule_code, rule_name, rule_scope, priority,
                   conditions, actions, explanation
            FROM public.diagnostic_rules
            WHERE status = 'active'
            ORDER BY priority ASC
            """
        )
        rows = cur.fetchall()

    return [
        RuleRow(
            rule_code=row[0],
            rule_name=row[1],
            rule_scope=row[2],
            priority=int(row[3]),
            conditions=row[4] or {},
            actions=row[5] or {},
            explanation=row[6],
        )
        for row in rows
    ]

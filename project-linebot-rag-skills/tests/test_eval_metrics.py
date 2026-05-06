"""Eval metrics 純單元測試。對應 task-20 步驟 7。"""

from __future__ import annotations

import pytest

from app.eval.metrics import (
    chunk_recall_at_k,
    citation_accuracy,
    forbidden_phrase_hit,
    must_cite_satisfied,
)
from app.eval.schema import GoldenCase
from app.rag.schemas import KnowledgeChunk


def _chunk(id: str) -> KnowledgeChunk:
    return KnowledgeChunk(id=id, content=id, category="general")


# ---- chunk_recall ----------------------------------------------------------


def test_recall_full():
    case = GoldenCase(id="x", query="x", expected_chunks=["a", "b"])
    assert chunk_recall_at_k(case, [_chunk("a"), _chunk("b"), _chunk("c")]) == 1.0


def test_recall_partial():
    case = GoldenCase(id="x", query="x", expected_chunks=["a", "b"])
    assert chunk_recall_at_k(case, [_chunk("a"), _chunk("c")]) == 0.5


def test_recall_zero():
    case = GoldenCase(id="x", query="x", expected_chunks=["a", "b"])
    assert chunk_recall_at_k(case, [_chunk("c"), _chunk("d")]) == 0.0


def test_recall_none_when_no_expected():
    case = GoldenCase(id="x", query="x")
    assert chunk_recall_at_k(case, [_chunk("a")]) is None


# ---- citation_accuracy ----------------------------------------------------


def test_citation_accuracy_no_hallucination():
    assert citation_accuracy([_chunk("a"), _chunk("b")], ["a", "b"]) == 1.0


def test_citation_accuracy_detects_fabrication():
    assert citation_accuracy([_chunk("a")], ["a", "fabricated"]) == 0.5


def test_citation_accuracy_none_when_no_citations():
    assert citation_accuracy([_chunk("a")], []) is None


# ---- forbidden_phrase ------------------------------------------------------


def test_forbidden_phrase_hit_detects():
    case = GoldenCase(id="x", query="x", forbidden_phrases=["所有", "完全"])
    assert forbidden_phrase_hit(case, "這涵蓋所有情況")
    assert forbidden_phrase_hit(case, "完全沒問題")


def test_forbidden_phrase_miss():
    case = GoldenCase(id="x", query="x", forbidden_phrases=["所有"])
    assert not forbidden_phrase_hit(case, "這涵蓋大部分情況")


def test_forbidden_phrase_empty_case():
    case = GoldenCase(id="x", query="x")
    assert not forbidden_phrase_hit(case, "anything")


# ---- must_cite_satisfied --------------------------------------------------


def test_must_cite_substring_match():
    case = GoldenCase(
        id="x", query="x", must_cite_sources=["nextjs.org"]
    )
    assert must_cite_satisfied(case, ["https://nextjs.org/docs/x"]) is True


def test_must_cite_missing():
    case = GoldenCase(
        id="x", query="x", must_cite_sources=["nextjs.org"]
    )
    assert must_cite_satisfied(case, ["other.com"]) is False


def test_must_cite_none_when_unspecified():
    case = GoldenCase(id="x", query="x")
    assert must_cite_satisfied(case, ["any"]) is None


# ---- schema loading ------------------------------------------------------


def test_load_golden_yaml(tmp_path):
    from app.eval.schema import GoldenCaseSet

    p = tmp_path / "g.yaml"
    p.write_text(
        "cases:\n"
        "  - id: x1\n    query: q\n    expected_chunks: [a]\n",
        encoding="utf-8",
    )
    cs = GoldenCaseSet.load(p)
    assert len(cs.cases) == 1
    assert cs.cases[0].id == "x1"


def test_load_real_golden_set():
    """產品級 golden.yaml 應通過 schema validation。"""
    from pathlib import Path

    from app.eval.schema import GoldenCaseSet

    root = Path(__file__).resolve().parents[1]
    cs = GoldenCaseSet.load(root / "tests" / "cases" / "golden.yaml")
    assert len(cs.cases) >= 10
    # 四類都該存在
    ids = [c.id for c in cs.cases]
    assert any(i.startswith("faq-") for i in ids)
    assert any(i.startswith("multi-") for i in ids)
    assert any(i.startswith("gap-") for i in ids)
    assert any(i.startswith("ground-") for i in ids)

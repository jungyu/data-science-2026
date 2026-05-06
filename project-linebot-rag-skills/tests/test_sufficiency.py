"""SufficiencyChecker 單元測試。對應 spec-15 / task-15 step 7。"""

from __future__ import annotations

from app.graph.feature_extractor import ExtractedFeatures
from app.graph.sufficiency import SufficiencyChecker, SufficiencyConfig
from app.rag.schemas import KnowledgeChunk


def _chunk(id: str, content: str, score: float = 0.7) -> KnowledgeChunk:
    return KnowledgeChunk(
        id=id,
        title=id,
        content=content,
        category="general",
        vector_score=score,
        keyword_score=score,
        combined_score=score,
    )


def _features(primary: str = "rag", qualifiers: list[str] | None = None) -> ExtractedFeatures:
    return ExtractedFeatures(
        primary_topic=primary,
        qualifiers=qualifiers or [],
        intent="concept",
        entities=[],
        raw_query=primary,
    )


def _checker(**overrides) -> SufficiencyChecker:
    cfg = SufficiencyConfig(
        min_chunks=overrides.get("min_chunks", 2),
        min_top_score=overrides.get("min_top_score", 0.4),
        min_feature_overlap=overrides.get("min_feature_overlap", 1),
    )
    return SufficiencyChecker(cfg)


def test_sufficient_when_all_pass():
    chunks = [
        _chunk("c1", "rag is retrieval augmented generation", 0.8),
        _chunk("c2", "more rag content", 0.6),
    ]
    decision, reasons = _checker().check(chunks=chunks, features=_features())
    assert decision == "sufficient"
    assert reasons == []


def test_insufficient_when_too_few_chunks():
    chunks = [_chunk("c1", "rag", 0.8)]
    decision, reasons = _checker().check(chunks=chunks, features=_features())
    assert decision == "insufficient"
    assert any("min_chunks" in r for r in reasons)


def test_insufficient_when_top_score_low():
    chunks = [_chunk("c1", "rag", 0.2), _chunk("c2", "rag", 0.1)]
    decision, reasons = _checker().check(chunks=chunks, features=_features())
    assert decision == "insufficient"
    assert any("top_score" in r for r in reasons)


def test_insufficient_when_no_overlap():
    chunks = [
        _chunk("c1", "completely unrelated text", 0.8),
        _chunk("c2", "more unrelated", 0.6),
    ]
    decision, reasons = _checker().check(chunks=chunks, features=_features("rag"))
    assert decision == "insufficient"
    assert any("feature_overlap" in r for r in reasons)


def test_insufficient_with_empty_chunks():
    decision, reasons = _checker().check(chunks=[], features=_features())
    assert decision == "insufficient"
    # 三項規則應全部失敗
    assert len(reasons) == 3


def test_qualifier_overlap_counts():
    """primary_topic 不在 chunks 但 qualifier 在，仍算 overlap。"""
    chunks = [
        _chunk("c1", "this content mentions Next.js 14 specifically", 0.8),
        _chunk("c2", "more content with Next.js 14 again", 0.6),
    ]
    f = _features(primary="hydration", qualifiers=["Next.js 14"])
    decision, _ = _checker().check(chunks=chunks, features=f)
    assert decision == "sufficient"


def test_case_insensitive_overlap():
    chunks = [
        _chunk("c1", "RAG is great", 0.8),
        _chunk("c2", "About RAG systems", 0.6),
    ]
    f = _features(primary="rag")
    decision, _ = _checker().check(chunks=chunks, features=f)
    assert decision == "sufficient"


def test_threshold_overrides():
    """門檻全降到 0 → 永遠 sufficient（即使 chunks 為空）。"""
    decision, _ = _checker(min_chunks=0, min_top_score=0.0, min_feature_overlap=0).check(
        chunks=[], features=_features()
    )
    assert decision == "sufficient"

"""Seed expander 單元測試。對應 spec-14 / task-14 step 8。"""

from __future__ import annotations

from app.graph.feature_extractor import ExtractedFeatures
from app.graph.seed_expander import DefaultSeedExpander


def _features(**overrides) -> ExtractedFeatures:
    base = dict(
        primary_topic="hydration mismatch",
        qualifiers=["Next.js 14", "SSR"],
        intent="debug",
        entities=["Next.js"],
        raw_query="Next.js 14 SSR hydration",
    )
    base.update(overrides)
    return ExtractedFeatures(**base)


def test_default_expander_produces_unique_seeds():
    seeds = DefaultSeedExpander().expand(_features())
    assert len(seeds) == len(set(seeds)), "seeds must be unique"
    assert "hydration mismatch" in seeds


def test_combines_topic_with_qualifiers():
    seeds = DefaultSeedExpander().expand(_features())
    assert any("Next.js 14" in s for s in seeds)
    assert any("SSR" in s for s in seeds)


def test_includes_entity_combination():
    seeds = DefaultSeedExpander().expand(_features())
    # 第一個 entity 串接 primary_topic
    assert any(s.startswith("Next.js ") for s in seeds)


def test_raw_query_kept_as_fallback():
    seeds = DefaultSeedExpander().expand(_features())
    assert "Next.js 14 SSR hydration" in seeds


def test_truncates_to_max_seeds():
    f = _features(qualifiers=["a", "b", "c", "d", "e", "f"])
    seeds = DefaultSeedExpander().expand(f, max_seeds=3)
    assert len(seeds) == 3


def test_handles_empty_qualifiers_and_entities():
    f = _features(qualifiers=[], entities=[])
    seeds = DefaultSeedExpander().expand(f)
    assert seeds[0] == "hydration mismatch"
    # 至少有 primary_topic 與 raw_query
    assert len(seeds) >= 1


def test_handles_empty_primary_topic():
    f = _features(primary_topic="", qualifiers=[], entities=[], raw_query="hi")
    seeds = DefaultSeedExpander().expand(f)
    # 仍應產出 raw_query 保底
    assert "hi" in seeds

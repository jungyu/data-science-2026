"""Score fusion 三策略單元測試。對應 spec-14 / task-14 step 8。"""

from __future__ import annotations

import pytest

from app.rag.fusion import fuse_max, fuse_mean, fuse_rrf, get_fuser
from app.rag.schemas import KnowledgeChunk


def _c(id: str, score: float) -> KnowledgeChunk:
    return KnowledgeChunk(
        id=id,
        title=id,
        content=f"content of {id}",
        category="general",
        vector_score=score,
        keyword_score=score,
        combined_score=score,
    )


def test_fuse_max_takes_highest():
    """同一 chunk 在多 seed 命中時，取所有 seed 中最高分。"""
    hits = [
        [_c("a", 0.5), _c("b", 0.3)],
        [_c("a", 0.8), _c("c", 0.6)],
    ]
    out = fuse_max(hits)
    by_id = {c.id: c.combined_score for c in out}
    assert by_id["a"] == 0.8  # max(0.5, 0.8)
    assert by_id["b"] == 0.3
    assert by_id["c"] == 0.6
    # 排序：a > c > b
    assert [c.id for c in out] == ["a", "c", "b"]


def test_fuse_mean_treats_missing_as_zero():
    """未命中的 seed 視為 0；偏好多路共識。"""
    hits = [
        [_c("a", 0.6), _c("b", 0.4)],
        [_c("a", 0.8)],  # b 沒命中
    ]
    out = fuse_mean(hits)
    by_id = {c.id: c.combined_score for c in out}
    # a: (0.6+0.8)/2 = 0.7；b: (0.4+0)/2 = 0.2
    assert by_id["a"] == pytest.approx(0.7)
    assert by_id["b"] == pytest.approx(0.2)
    assert [c.id for c in out] == ["a", "b"]


def test_fuse_rrf_combines_ranks():
    """RRF：Σ 1/(k+rank)，與絕對分數無關。"""
    hits = [
        [_c("a", 0.99), _c("b", 0.01)],
        [_c("b", 0.99), _c("a", 0.01)],
    ]
    out = fuse_rrf(hits, k=60)
    # 兩個 chunk 在兩個 seed 都出現過、rank 1 與 2 互換 → 分數應相同
    assert len(out) == 2
    scores = sorted({round(c.combined_score, 6) for c in out})
    # 兩 chunk 拿到相同 RRF：1/(60+1)+1/(60+2)
    expected = 1 / 61 + 1 / 62
    assert all(c.combined_score == pytest.approx(expected) for c in out)


def test_fuse_rrf_rewards_consensus():
    """在多個 seed 都排前的 chunk，RRF 應比只在一處出現的高。"""
    hits = [
        [_c("a", 0.5), _c("b", 0.3)],
        [_c("a", 0.5), _c("c", 0.3)],
        [_c("a", 0.5)],
    ]
    out = fuse_rrf(hits)
    by_id = {c.id: c.combined_score for c in out}
    assert by_id["a"] > by_id["b"]
    assert by_id["a"] > by_id["c"]
    # 排序：a 最前
    assert out[0].id == "a"


def test_fusion_handles_empty_seeds():
    assert fuse_max([]) == []
    assert fuse_mean([]) == []
    assert fuse_rrf([]) == []


def test_fusion_skips_empty_seed_within_list():
    """某些 seed 沒命中（空 list），不應 crash。"""
    hits = [
        [_c("a", 0.7)],
        [],
        [_c("b", 0.5)],
    ]
    out = fuse_max(hits)
    ids = {c.id for c in out}
    assert ids == {"a", "b"}


def test_get_fuser_returns_expected():
    assert get_fuser("max") is fuse_max
    assert get_fuser("mean") is fuse_mean
    assert get_fuser("rrf") is fuse_rrf


def test_get_fuser_rejects_unknown():
    with pytest.raises(ValueError, match="unknown fusion strategy"):
        get_fuser("nonsense")

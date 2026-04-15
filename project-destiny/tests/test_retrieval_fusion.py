"""驗證 retrieve_multi_seed 的融合邏輯（不需要實際 DB / embedding API）。

策略：mock _run_sql 與 EmbeddingClient.embed_many，直接餵不同 seed 的 SQL 回傳結果。
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from destiny import retrieval
from destiny.retrieval import retrieve_multi_seed


class _FakeEmbedder:
    def embed_many(self, texts):
        return [[0.0] * 4 for _ in list(texts)]


def _row(code: str, score: float, pri: int = 1) -> dict:
    return {
        "atom_id": hash(code) & 0xFFFF,
        "atom_code": code,
        "source_book": "子平真詮",
        "source_priority": pri,
        "title": None,
        "original_text": f"原文-{code}",
        "modern_interpretation": None,
        "vector_score": score,
        "source_priority_score": 1.0,
        "symbolic_match_score": 1.0,
        "metadata_overlap_score": 1.0,
        "final_score": score,
    }


def test_max_fusion_picks_highest_score_across_seeds() -> None:
    seed_results = {
        "seed_A": [_row("atom_X", 0.60), _row("atom_Y", 0.55)],
        "seed_B": [_row("atom_X", 0.90), _row("atom_Z", 0.50)],
    }
    calls = iter(["seed_A", "seed_B"])

    def fake_run(conn, emb, q):
        return seed_results[next(calls)]

    with patch.object(retrieval, "_run_sql", side_effect=fake_run):
        hits = retrieve_multi_seed(
            conn=None, embedder=_FakeEmbedder(),  # type: ignore[arg-type]
            seeds=["seed_A", "seed_B"], fusion="max",
        )

    by_code = {h.atom_code: h for h in hits}
    # atom_X 取兩 seed 中較高 0.90
    assert by_code["atom_X"].final_score == pytest.approx(0.90)
    assert by_code["atom_X"].hit_seed_count == 2
    assert by_code["atom_X"].top_seed == "seed_B"
    # atom_Y 只被 seed_A 命中
    assert by_code["atom_Y"].hit_seed_count == 1
    # 排序：X > Y > Z
    assert [h.atom_code for h in hits][:3] == ["atom_X", "atom_Y", "atom_Z"]


def test_mean_fusion_penalises_single_seed_hits() -> None:
    """mean 模式：未命中的 seed 計 0，因此多路命中的 atom 會勝出。"""
    seed_results = {
        "A": [_row("both", 0.60), _row("only_a", 0.90)],
        "B": [_row("both", 0.60)],
    }
    calls = iter(["A", "B"])

    with patch.object(retrieval, "_run_sql", side_effect=lambda *_: seed_results[next(calls)]):
        hits = retrieve_multi_seed(
            conn=None, embedder=_FakeEmbedder(),  # type: ignore[arg-type]
            seeds=["A", "B"], fusion="mean",
        )

    by_code = {h.atom_code: h for h in hits}
    # both: (0.60 + 0.60) / 2 = 0.60
    assert by_code["both"].final_score == pytest.approx(0.60)
    # only_a: (0.90 + 0) / 2 = 0.45
    assert by_code["only_a"].final_score == pytest.approx(0.45)
    assert hits[0].atom_code == "both"


def test_empty_seeds_returns_empty() -> None:
    hits = retrieve_multi_seed(
        conn=None, embedder=_FakeEmbedder(), seeds=[],  # type: ignore[arg-type]
    )
    assert hits == []


def test_rrf_fusion_rank_based() -> None:
    """RRF：兩 seed 都排第一的 atom 應勝過只被單 seed 排第一的 atom。"""
    seed_results = {
        "A": [_row("double_top", 0.1), _row("single_top_a", 0.99)],
        "B": [_row("double_top", 0.1), _row("single_top_b", 0.99)],
    }
    calls = iter(["A", "B"])

    with patch.object(retrieval, "_run_sql", side_effect=lambda *_: seed_results[next(calls)]):
        hits = retrieve_multi_seed(
            conn=None, embedder=_FakeEmbedder(),  # type: ignore[arg-type]
            seeds=["A", "B"], fusion="rrf",
        )

    assert hits[0].atom_code == "double_top"

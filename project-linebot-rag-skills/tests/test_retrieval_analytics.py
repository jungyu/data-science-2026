"""spec-09 retrieval_logs 分析驗收。

純函式測試（不打 Supabase）；CLI wrapper 只負責 IO，所以核心邏輯在此覆蓋。
"""

from __future__ import annotations

from app.eval.retrieval_analytics import (
    aggregate_category_stats,
    aggregate_empty_hits,
    aggregate_low_score,
    filter_query_records,
    render_table,
)


def _row(
    query: str,
    retrieved_ids: list[str],
    scores: dict | None = None,
    category_filter: list[str] | None = None,
    created_at: str = "2026-05-01T00:00:00Z",
    skill_id: str | None = None,
) -> dict:
    return {
        "query": query,
        "retrieved_ids": retrieved_ids,
        "scores": scores or {},
        "category_filter": category_filter or [],
        "created_at": created_at,
        "skill_id": skill_id,
    }


# ── empty hits ───────────────────────────────────────────────────────────────


def test_empty_hits_counts_zero_retrieval_queries():
    rows = [
        _row("a", []),
        _row("a", []),
        _row("b", ["c1"]),
        _row("c", []),
    ]
    out = aggregate_empty_hits(rows)
    assert out == [
        {"query": "a", "count": 2},
        {"query": "c", "count": 1},
    ]


def test_empty_hits_handles_no_records():
    assert aggregate_empty_hits([]) == []


def test_empty_hits_skips_blank_query():
    rows = [_row("", []), _row("   ", []), _row("real", [])]
    assert aggregate_empty_hits(rows) == [{"query": "real", "count": 1}]


# ── low score ────────────────────────────────────────────────────────────────


def test_low_score_filters_by_max_combined():
    rows = [
        _row("hi", ["c1"], {"c1": {"combined": 0.9}}),    # 不該選
        _row("lo1", ["c1"], {"c1": {"combined": 0.2}}),   # 選
        _row("lo2", ["c1"], {"c1": {"combined": 0.1}}),   # 選
        _row("no", []),                                    # empty_hits 的範疇，跳過
    ]
    out = aggregate_low_score(rows, threshold=0.3)
    assert [r["query"] for r in out] == ["lo2", "lo1"]  # 升序
    assert out[0]["max_combined"] == 0.1


def test_low_score_tolerates_flat_score_dict():
    """歷史版本可能只記 {chunk_id: combined_float}（非 nested dict），仍要能讀。"""
    rows = [_row("q", ["c1"], {"c1": 0.15})]
    out = aggregate_low_score(rows, threshold=0.3)
    assert len(out) == 1
    assert out[0]["max_combined"] == 0.15


def test_low_score_skips_records_without_scores():
    rows = [_row("q", ["c1"], {})]
    assert aggregate_low_score(rows, threshold=0.3) == []


def test_low_score_excludes_zero_combined_scores():
    """combined=0 視為沒實際命中，不該被誤算成「分數低於 threshold 的有效低分」。"""
    rows = [_row("q", ["c1"], {"c1": {"combined": 0.0}})]
    # 沒有 > 0 的分數 → _max_combined 回 None → 被 aggregate 跳過
    assert aggregate_low_score(rows, threshold=0.3) == []


def test_category_stats_skips_zero_in_avg():
    """category 平均分計算也排除 0（保持與 _max_combined 一致）。"""
    rows = [
        _row("a", ["c1"], {"c1": {"combined": 0.8}}, category_filter=["rag"]),
        _row("b", ["c1"], {"c1": {"combined": 0.0}}, category_filter=["rag"]),  # 不算進平均
    ]
    out = aggregate_category_stats(rows)
    by_cat = {r["category"]: r for r in out}
    assert by_cat["rag"]["count"] == 2  # count 還是算
    assert by_cat["rag"]["avg_max_score"] == 0.8  # avg 只有 0.8


# ── category stats ──────────────────────────────────────────────────────────


def test_category_stats_counts_and_avg():
    rows = [
        _row("a", ["c1"], {"c1": {"combined": 0.8}}, category_filter=["rag"]),
        _row("b", ["c1"], {"c1": {"combined": 0.6}}, category_filter=["rag"]),
        _row("c", ["c1"], {"c1": {"combined": 0.9}}, category_filter=["philosophy"]),
        _row("d", ["c1"], {"c1": {"combined": 0.3}}, category_filter=["rag", "notes"]),
    ]
    out = aggregate_category_stats(rows)
    by_cat = {r["category"]: r for r in out}
    assert by_cat["rag"]["count"] == 3
    assert by_cat["rag"]["avg_max_score"] == round((0.8 + 0.6 + 0.3) / 3, 4)
    assert by_cat["philosophy"]["count"] == 1
    assert by_cat["notes"]["count"] == 1


def test_category_stats_no_filter_bucket():
    rows = [_row("a", ["c1"], {"c1": {"combined": 0.5}}, category_filter=[])]
    out = aggregate_category_stats(rows)
    assert out == [{"category": "(no filter)", "count": 1, "avg_max_score": 0.5}]


# ── filter by query text ─────────────────────────────────────────────────────


def test_filter_query_case_insensitive_partial_match():
    rows = [
        _row("LangGraph 是什麼", ["c1"], skill_id="x", created_at="2026-05-02T00:00:00Z"),
        _row("RAG 簡介", ["c2"], skill_id="y", created_at="2026-05-01T00:00:00Z"),
        _row("langgraph 入門", ["c3"], skill_id="z", created_at="2026-05-03T00:00:00Z"),
    ]
    out = filter_query_records(rows, "langgraph")
    # 倒序 by created_at
    assert [r["query"] for r in out] == ["langgraph 入門", "LangGraph 是什麼"]


def test_filter_query_empty_returns_empty():
    rows = [_row("anything", ["c1"])]
    assert filter_query_records(rows, "") == []


# ── render_table ─────────────────────────────────────────────────────────────


def test_render_table_pads_columns():
    out = render_table(
        [{"a": "x", "b": 1}, {"a": "yy", "b": 22}],
        headers=["a", "b"],
    )
    # header + separator + 2 rows
    assert out.count("\n") == 3
    assert "a " in out and "b" in out


def test_render_table_no_records_message():
    assert render_table([], headers=["a"]) == "（無記錄）"

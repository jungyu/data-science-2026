"""Eval runner 整合測試（用 stub services，不打真 LLM）。對應 task-20 步驟 7。"""

from __future__ import annotations

import pytest

from app.eval.runner import EvalRunner
from app.eval.schema import GoldenCase


@pytest.mark.asyncio
async def test_runner_against_stub(stub_services):
    runner = EvalRunner(stub_services)
    cases = [
        # _StubRetriever 的 default chunks 含 chunk-1 / chunk-2
        GoldenCase(id="x1", query="什麼是 RAG？", expected_chunks=["chunk-1"]),
    ]
    results = await runner.run(
        cases=cases, variants=["basic", "selfrag", "reflection"]
    )
    assert len(results) == 3
    by_variant = {r.variant: r for r in results}

    # 三變體都該命中（recall=1）
    assert by_variant["basic"].chunk_recall == 1.0
    assert by_variant["selfrag"].chunk_recall == 1.0
    assert by_variant["reflection"].chunk_recall == 1.0


@pytest.mark.asyncio
async def test_runner_records_clarification(stub_services_insufficient):
    """gap case：retriever 回空 → selfrag/reflection 走 clarify → went_to_clarify=True。"""
    runner = EvalRunner(stub_services_insufficient)
    cases = [
        GoldenCase(
            id="g1", query="知識庫沒涵蓋", expected_chunks=[],
            expect_clarification=True,
        ),
    ]
    results = await runner.run(cases=cases, variants=["selfrag"])
    assert results[0].went_to_clarify is True
    assert results[0].failure_reasons == []


@pytest.mark.asyncio
async def test_runner_flags_unexpected_clarify_when_chunks_expected(
    stub_services_insufficient,
):
    """expected_chunks 非空但 graph 走了 clarify → 標 failure。
    （hallucination case 即 expected_chunks=[] 是測 forbidden_phrase，
    走 clarify 不算 failure，另一個測試覆蓋。）"""
    runner = EvalRunner(stub_services_insufficient)
    cases = [
        GoldenCase(
            id="x",
            query="?",
            expected_chunks=["chunk-1"],
            expect_clarification=False,
        )
    ]
    results = await runner.run(cases=cases, variants=["selfrag"])
    assert any("unexpected clarify" in r for r in results[0].failure_reasons)


@pytest.mark.asyncio
async def test_hallucination_case_allows_clarify(stub_services_insufficient):
    """spec-20：expected_chunks=[] 的 hallucination 案例走 clarify 不算 failure。"""
    runner = EvalRunner(stub_services_insufficient)
    cases = [
        GoldenCase(
            id="ground-001",
            query="知識庫沒有的查詢",
            expected_chunks=[],
            expect_clarification=False,
            forbidden_phrases=["亂編的事實"],
        )
    ]
    results = await runner.run(cases=cases, variants=["selfrag"])
    assert all("unexpected clarify" not in r for r in results[0].failure_reasons)


@pytest.mark.asyncio
async def test_basic_variant_skips_must_cite_failure(stub_services):
    """spec-20 §Metric：basic variant 不產 answer_contract，must_cite 不該列 failure。"""
    runner = EvalRunner(stub_services)
    cases = [
        GoldenCase(
            id="x",
            query="?",
            expected_chunks=["chunk-1"],
            must_cite_sources=["some-source.md"],
        )
    ]
    results = await runner.run(cases=cases, variants=["basic"])
    assert all(
        "missing required citation" not in r for r in results[0].failure_reasons
    )


@pytest.mark.asyncio
async def test_aggregate_shape(stub_services):
    runner = EvalRunner(stub_services)
    results = await runner.run(
        cases=[GoldenCase(id="x", query="?")], variants=["basic"]
    )
    agg = runner.aggregate(results)
    assert "basic" in agg
    assert agg["basic"]["n"] == 1
    assert "latency_ms_median" in agg["basic"]


@pytest.mark.asyncio
async def test_judge_pass_recorded_for_reflection(stub_services_judge_pass):
    """reflection variant 跑 judge_pass 路徑 → judge_passed=True。"""
    runner = EvalRunner(stub_services_judge_pass)
    cases = [GoldenCase(id="x", query="?", expected_chunks=["chunk-1"])]
    results = await runner.run(cases=cases, variants=["reflection"])
    assert results[0].judge_passed is True


@pytest.mark.asyncio
async def test_eval_does_not_push_to_line(stub_services):
    """U_eval 前綴 → push_node 跳過實際 LINE 推送。"""
    runner = EvalRunner(stub_services)
    cases = [GoldenCase(id="x", query="?", expected_chunks=["chunk-1"])]
    await runner.run(cases=cases, variants=["basic"])
    assert stub_services.line_client.pushed == []

"""GroundednessJudge + JudgeScore 單元測試。對應 spec-17 / task-17 step 6。"""

from __future__ import annotations

import json

import pytest

from app.generator.contract import AnswerContract, Citation, KeyFinding
from app.judge.scorer import GroundednessJudge, JudgeScore


def _contract() -> AnswerContract:
    return AnswerContract(
        summary="關於 RAG 的概念。",
        key_findings=[KeyFinding(point="RAG 是檢索增強生成。", citations=["c1"])],
        caveats=["以下內容依當前知識庫整理。"],
        citations=[Citation(chunk_id="c1", source="https://example.com/1", snippet="...")],
    )


# ---- JudgeScore ----------------------------------------------------------


def test_score_passes_when_all_axes_high():
    s = JudgeScore(
        groundedness=8, citation_fidelity=8, format_completeness=8, uncertainty_honesty=8, issues=[]
    )
    assert s.passes()
    assert s.mean == 8.0


def test_score_fails_when_one_axis_low():
    s = JudgeScore(
        groundedness=5, citation_fidelity=8, format_completeness=8, uncertainty_honesty=8,
        issues=["x"]
    )
    assert not s.passes()


def test_score_fails_when_mean_below_threshold():
    """所有軸都剛好過 min_axis 但平均低於 min_mean。"""
    s = JudgeScore(
        groundedness=6, citation_fidelity=6, format_completeness=6, uncertainty_honesty=6, issues=[]
    )
    # min_axis=6 通過，但 mean=6 < min_mean=7
    assert not s.passes(min_axis=6, min_mean=7.0)


def test_score_thresholds_customizable():
    s = JudgeScore(
        groundedness=4, citation_fidelity=4, format_completeness=4, uncertainty_honesty=4, issues=[]
    )
    assert s.passes(min_axis=4, min_mean=4.0)
    assert not s.passes(min_axis=5, min_mean=4.0)


# ---- GroundednessJudge --------------------------------------------------


class _OkJudgeLLM:
    async def complete(self, prompt: str) -> str:
        return json.dumps(
            {
                "groundedness": 9,
                "citation_fidelity": 8,
                "format_completeness": 8,
                "uncertainty_honesty": 7,
                "issues": [],
            }
        )


class _FencedJudgeLLM:
    async def complete(self, prompt: str) -> str:
        return (
            "```json\n"
            '{"groundedness":7,"citation_fidelity":6,"format_completeness":5,'
            '"uncertainty_honesty":6,"issues":["caveat 沒呈現"]}\n```'
        )


class _RaisingJudgeLLM:
    async def complete(self, prompt: str) -> str:
        raise RuntimeError("boom")


class _MalformedJudgeLLM:
    async def complete(self, prompt: str) -> str:
        return "not json"


@pytest.mark.asyncio
async def test_judge_returns_score():
    j = GroundednessJudge(llm=_OkJudgeLLM())
    score = await j.judge(narrative="x", contract=_contract(), response_mode="brief")
    assert score is not None
    assert score.groundedness == 9
    assert score.passes()


@pytest.mark.asyncio
async def test_judge_strips_fence():
    j = GroundednessJudge(llm=_FencedJudgeLLM())
    score = await j.judge(narrative="x", contract=_contract(), response_mode="brief")
    assert score is not None
    assert "caveat 沒呈現" in score.issues
    assert not score.passes()  # format=5 < 6


@pytest.mark.asyncio
async def test_judge_returns_none_on_llm_failure():
    j = GroundednessJudge(llm=_RaisingJudgeLLM())
    score = await j.judge(narrative="x", contract=_contract(), response_mode="brief")
    assert score is None  # graceful degrade → 視為 pass


@pytest.mark.asyncio
async def test_judge_returns_none_on_malformed_json():
    j = GroundednessJudge(llm=_MalformedJudgeLLM())
    score = await j.judge(narrative="x", contract=_contract(), response_mode="brief")
    assert score is None


@pytest.mark.asyncio
async def test_judge_returns_none_when_llm_is_none():
    j = GroundednessJudge(llm=None)
    score = await j.judge(narrative="x", contract=_contract(), response_mode="brief")
    assert score is None


@pytest.mark.asyncio
async def test_judge_truncates_issues():
    """LLM 若回 100 個 issues，scorer 應截到 5 條。"""

    class _BloatLLM:
        async def complete(self, prompt: str) -> str:
            return json.dumps(
                {
                    "groundedness": 5,
                    "citation_fidelity": 5,
                    "format_completeness": 5,
                    "uncertainty_honesty": 5,
                    "issues": [f"issue {i}" for i in range(20)],
                }
            )

    j = GroundednessJudge(llm=_BloatLLM())
    score = await j.judge(narrative="x", contract=_contract(), response_mode="brief")
    assert score is not None
    assert len(score.issues) == 5

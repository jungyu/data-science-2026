"""Clarifier 單元測試。對應 spec-15 / task-15 step 7。"""

from __future__ import annotations

import json

import pytest

from app.graph.clarifier import LLMClarifier, format_clarification
from app.graph.feature_extractor import ExtractedFeatures
from app.rag.schemas import KnowledgeChunk


def _features() -> ExtractedFeatures:
    return ExtractedFeatures(
        primary_topic="hydration mismatch",
        qualifiers=[],
        intent="debug",
        entities=[],
        raw_query="hydration mismatch",
    )


def _chunk() -> KnowledgeChunk:
    return KnowledgeChunk(
        id="c1",
        title="t",
        content="some content",
        category="general",
        combined_score=0.3,
    )


class _ValidJsonLLM:
    async def complete(self, prompt: str) -> str:
        return json.dumps(
            {"questions": ["你用的是哪個版本？", "在哪個環境跑？", "錯誤訊息是什麼？"]}
        )


class _FencedJsonLLM:
    async def complete(self, prompt: str) -> str:
        return '```json\n{"questions": ["q1?", "q2?"]}\n```'


class _RaisingLLM:
    async def complete(self, prompt: str) -> str:
        raise RuntimeError("boom")


class _MalformedLLM:
    async def complete(self, prompt: str) -> str:
        return "not json"


@pytest.mark.asyncio
async def test_returns_llm_questions():
    c = LLMClarifier(llm=_ValidJsonLLM())
    qs = await c.generate_questions(
        user_input="x", features=_features(), chunks=[_chunk()]
    )
    assert qs == ["你用的是哪個版本？", "在哪個環境跑？", "錯誤訊息是什麼？"]


@pytest.mark.asyncio
async def test_strips_fence():
    c = LLMClarifier(llm=_FencedJsonLLM())
    qs = await c.generate_questions(user_input="x", features=_features(), chunks=[])
    assert qs == ["q1?", "q2?"]


@pytest.mark.asyncio
async def test_falls_back_on_failure():
    c = LLMClarifier(llm=_RaisingLLM())
    qs = await c.generate_questions(user_input="x", features=_features(), chunks=[])
    assert len(qs) == 2
    # fallback 不該是空字串
    assert all(q.strip() for q in qs)


@pytest.mark.asyncio
async def test_falls_back_on_malformed_json():
    c = LLMClarifier(llm=_MalformedLLM())
    qs = await c.generate_questions(user_input="x", features=_features(), chunks=[])
    assert len(qs) == 2  # fallback


@pytest.mark.asyncio
async def test_falls_back_when_llm_is_none():
    c = LLMClarifier(llm=None)
    qs = await c.generate_questions(user_input="x", features=_features(), chunks=[])
    assert len(qs) == 2


@pytest.mark.asyncio
async def test_truncates_to_three_questions():
    class _ManyLLM:
        async def complete(self, prompt: str) -> str:
            return json.dumps({"questions": [f"q{i}" for i in range(10)]})

    qs = await LLMClarifier(llm=_ManyLLM()).generate_questions(
        user_input="x", features=_features(), chunks=[]
    )
    assert len(qs) == 3


def test_format_clarification_renders_template():
    text = format_clarification(["問題 A", "問題 B"])
    assert text.startswith("我需要再確認幾件事：")
    assert "1. 問題 A" in text
    assert "2. 問題 B" in text
    assert text.endswith("回覆後我再幫你分析。")


def test_format_clarification_with_empty_falls_back():
    text = format_clarification([])
    assert "1." in text  # fallback questions present

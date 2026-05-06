"""Feature Extractor 單元測試與整合測試。

對應 spec-13 / task-13 step 7。
"""

from __future__ import annotations

import json

import pytest

from app.graph.feature_extractor import ExtractedFeatures, LLMFeatureExtractor


class _ValidJsonLLM:
    async def complete(self, prompt: str) -> str:
        return json.dumps(
            {
                "primary_topic": "hydration mismatch",
                "qualifiers": ["Next.js 14", "SSR"],
                "intent": "debug",
                "entities": ["Next.js"],
            }
        )


class _FencedJsonLLM:
    """LLM 把 JSON 包進 markdown fence——常見場景，要正確解析。"""

    async def complete(self, prompt: str) -> str:
        return (
            "```json\n"
            '{"primary_topic":"RAG","qualifiers":[],"intent":"concept",'
            '"entities":["pgvector"]}\n'
            "```"
        )


class _RaisingLLM:
    async def complete(self, prompt: str) -> str:
        raise RuntimeError("simulated LLM failure")


class _MalformedLLM:
    async def complete(self, prompt: str) -> str:
        return "not json at all"


@pytest.mark.asyncio
async def test_extracts_valid_json():
    extractor = LLMFeatureExtractor(llm=_ValidJsonLLM())
    f = await extractor.extract(user_input="Next.js 14 SSR hydration error")
    assert f.primary_topic == "hydration mismatch"
    assert f.qualifiers == ["Next.js 14", "SSR"]
    assert f.intent == "debug"
    assert f.entities == ["Next.js"]
    assert f.raw_query == "Next.js 14 SSR hydration error"


@pytest.mark.asyncio
async def test_strips_markdown_fence():
    extractor = LLMFeatureExtractor(llm=_FencedJsonLLM())
    f = await extractor.extract(user_input="什麼是 RAG？")
    assert f.primary_topic == "RAG"
    assert f.intent == "concept"
    assert f.entities == ["pgvector"]


@pytest.mark.asyncio
async def test_falls_back_on_llm_failure():
    extractor = LLMFeatureExtractor(llm=_RaisingLLM())
    f = await extractor.extract(user_input="壞掉的問題")
    assert f.primary_topic == "壞掉的問題"
    assert f.intent == "other"
    assert f.qualifiers == []


@pytest.mark.asyncio
async def test_falls_back_on_malformed_json():
    extractor = LLMFeatureExtractor(llm=_MalformedLLM())
    f = await extractor.extract(user_input="another bad input")
    assert f.primary_topic == "another bad input"
    assert f.intent == "other"


@pytest.mark.asyncio
async def test_falls_back_when_llm_is_none():
    extractor = LLMFeatureExtractor(llm=None)
    f = await extractor.extract(user_input="no llm configured")
    assert f.primary_topic == "no llm configured"
    assert f.intent == "other"


@pytest.mark.asyncio
async def test_truncates_overlong_lists():
    """LLM 若回 100 個 entity，extractor 應截到 8 個避免 prompt 注入。"""

    class _BloatLLM:
        async def complete(self, prompt: str) -> str:
            return json.dumps(
                {
                    "primary_topic": "x",
                    "qualifiers": [f"q{i}" for i in range(20)],
                    "intent": "other",
                    "entities": [f"e{i}" for i in range(50)],
                }
            )

    extractor = LLMFeatureExtractor(llm=_BloatLLM())
    f = await extractor.extract(user_input="bloat")
    assert len(f.qualifiers) == 5
    assert len(f.entities) == 8


@pytest.mark.asyncio
async def test_graph_populates_features(stub_services):
    """整合測試：graph 跑完後 state 含 features（用 conftest 的 _StubFeatureExtractor）。"""
    final = await stub_services.rag_graph.ainvoke(
        {
            "user_input": "什麼是 RAG？",
            "external_user_id": "U_test",
            "recent_history": "",
        }
    )
    assert isinstance(final["features"], ExtractedFeatures)
    # _StubFeatureExtractor 用常數 primary_topic="topic"（與 stub chunks 對齊）
    assert final["features"].primary_topic == "topic"
    assert final["features"].raw_query == "什麼是 RAG？"

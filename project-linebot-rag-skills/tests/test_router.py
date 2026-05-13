import asyncio

import pytest

from app.router.categories import VALID_RAG_CATEGORIES
from app.router.intent_router import IntentRouter


class FakeRouterLLM:
    def __init__(self, output: str) -> None:
        self._output = output

    async def complete(self, prompt: str) -> str:
        return self._output


def test_router_parses_technical_response() -> None:
    router = IntentRouter(
        llm=FakeRouterLLM(
            """
            {
              "target_skill": "tech_architect",
              "is_rag_required": true,
              "rag_query": "supabase webhook architecture",
              "rag_categories": ["engineering"],
              "emotion_state": "neutral",
              "response_mode": "structured",
              "confidence": 0.91
            }
            """
        )
    )

    result = asyncio.run(
        router.route_message("Supabase webhook 怎麼設計？", "No recent conversation.")
    )
    assert result.target_skill == "tech_architect"
    assert result.is_rag_required is True


def test_router_parses_business_response() -> None:
    router = IntentRouter(
        llm=FakeRouterLLM(
            """
            {
              "target_skill": "business_strategist",
              "is_rag_required": false,
              "rag_query": "pricing strategy",
              "rag_categories": [],
              "emotion_state": "curious",
              "response_mode": "decision_support",
              "confidence": 0.88
            }
            """
        )
    )

    result = asyncio.run(router.route_message("這產品要怎麼定價？", "No recent conversation."))
    assert result.target_skill == "business_strategist"
    assert result.response_mode == "decision_support"


def test_router_marks_anxious_message() -> None:
    router = IntentRouter(llm=None)

    result = asyncio.run(
        router.route_message("我很焦慮，擔心這個作品根本沒人用。", "No recent conversation.")
    )
    assert result.emotion_state == "anxious"
    assert result.target_skill == "emotional_calibration"


def test_router_falls_back_when_json_is_invalid() -> None:
    router = IntentRouter(llm=FakeRouterLLM("not-json"))

    result = asyncio.run(router.route_message("哈囉", "No recent conversation."))
    assert result.target_skill == "general_chat"


def test_router_low_confidence_falls_back_to_tech_for_technical_query() -> None:
    router = IntentRouter(
        llm=FakeRouterLLM(
            """
            {
              "target_skill": "general_chat",
              "is_rag_required": false,
              "rag_query": "",
              "rag_categories": [],
              "emotion_state": "neutral",
              "response_mode": "brief",
              "confidence": 0.12
            }
            """
        )
    )

    result = asyncio.run(
        router.route_message("FastAPI webhook schema 怎麼設計？", "No recent conversation.")
    )
    assert result.target_skill == "tech_architect"


def test_heuristic_categories_are_all_valid() -> None:
    """spec-03 驗收：所有 heuristic 路徑產出的 rag_categories ⊂ VALID_RAG_CATEGORIES。"""
    router = IntentRouter(llm=None)
    queries = [
        # 觸發各 heuristic 分支
        "supabase webhook 怎麼設計",                # tech
        "ab test 指標怎麼看",                        # data
        "我的產品定位該怎麼調整",                    # business
        "存在的意義是什麼",                          # philosophy
        "今天天氣不錯",                              # general_chat
    ]
    for q in queries:
        result = asyncio.run(router.route_message(q, ""))
        invalid = set(result.rag_categories) - VALID_RAG_CATEGORIES
        assert not invalid, f"query={q!r} produced invalid categories: {invalid}"


def test_llm_output_invalid_categories_are_filtered() -> None:
    """spec-03 驗收：LLM 若回非法 category，normalize 後會被過濾。"""
    router = IntentRouter(
        llm=FakeRouterLLM(
            """
            {
              "target_skill": "philosophical_dialectic",
              "is_rag_required": true,
              "rag_query": "意義與自由",
              "rag_categories": ["philosophy", "reflection", "made_up"],
              "emotion_state": "reflective",
              "response_mode": "reflection",
              "confidence": 0.9
            }
            """
        )
    )
    result = asyncio.run(router.route_message("自由意志是真的嗎？", ""))
    assert set(result.rag_categories) <= VALID_RAG_CATEGORIES
    assert "reflection" not in result.rag_categories
    assert "made_up" not in result.rag_categories

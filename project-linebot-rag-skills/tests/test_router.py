import asyncio

import pytest

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

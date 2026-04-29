import asyncio

import pytest

from app.generator.formatter import split_for_line
from app.generator.responder import ResponseGenerator
from app.router.schemas import RouterResult
from app.skills.loader import SkillDefinition


class FakeGeneratorLLM:
    def __init__(self, output: str) -> None:
        self._output = output

    async def complete(self, prompt: str) -> str:
        return self._output


def test_responder_adds_knowledge_gap_notice_when_rag_required() -> None:
    responder = ResponseGenerator(llm=FakeGeneratorLLM("這是一般回答。"), line_max_message_chars=1000)
    skill = SkillDefinition(
        skill_id="tech_architect",
        name="技術架構師",
        description="desc",
        category="engineering",
        system_prompt="prompt",
    )
    router_result = RouterResult(
        target_skill="tech_architect",
        is_rag_required=True,
        rag_query="query",
        rag_categories=["engineering"],
        emotion_state="neutral",
        response_mode="structured",
        confidence=0.9,
    )

    messages = asyncio.run(
        responder.generate_response(
            user_input="請看專案 ADR",
            router_result=router_result,
            skill=skill,
            rag_chunks=[],
            rag_context="No retrieved context.",
            recent_history="No recent conversation.",
        )
    )

    assert "目前知識庫沒有足夠資料" in messages[0]


def test_split_for_line_splits_long_text() -> None:
    text = ("A" * 20) + "\n\n" + ("B" * 20)
    chunks = split_for_line(text, max_chars=25)
    assert len(chunks) >= 2

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.generator.formatter import split_for_line
from app.generator.prompts import render_synthesis_prompt
from app.rag.schemas import KnowledgeChunk
from app.router.schemas import RouterResult
from app.skills.loader import SkillDefinition


class GeneratorLLM(Protocol):
    async def complete(self, prompt: str) -> str:
        ...


@dataclass
class ResponseGenerator:
    llm: GeneratorLLM | None = None
    line_max_message_chars: int = 4500

    async def generate_response(
        self,
        *,
        user_input: str,
        router_result: RouterResult,
        skill: SkillDefinition,
        rag_chunks: list[KnowledgeChunk],
        rag_context: str,
        recent_history: str,
    ) -> list[str]:
        if self.llm is None:
            return self._fallback_response(router_result, rag_chunks)

        prompt = render_synthesis_prompt(
            skill_name=skill.name,
            skill_system_prompt=skill.system_prompt,
            user_input=user_input,
            recent_history=recent_history,
            emotion_state=router_result.emotion_state,
            response_mode=router_result.response_mode,
            rag_context=rag_context,
        )
        response_text = await self.llm.complete(prompt)

        if router_result.is_rag_required and not rag_chunks:
            response_text = f"目前知識庫沒有足夠資料。\n\n{response_text}".strip()

        return split_for_line(response_text, max_chars=self.line_max_message_chars)

    def _fallback_response(
        self,
        router_result: RouterResult,
        rag_chunks: list[KnowledgeChunk],
    ) -> list[str]:
        if router_result.is_rag_required and not rag_chunks:
            text = "目前知識庫沒有足夠資料。先提供保守回應，若需要可補充更多背景。"
        else:
            text = "已收到訊息，系統會依目前 skill 與上下文回覆。"
        return split_for_line(text, max_chars=self.line_max_message_chars)

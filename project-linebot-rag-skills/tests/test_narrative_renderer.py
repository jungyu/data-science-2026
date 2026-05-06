"""NarrativeRenderer 單元測試。對應 spec-16 / task-16 step 9。

驗證受限 LLM render + LLM=None / 失敗時的 fallback 模板。
"""

from __future__ import annotations

import pytest

from app.generator.contract import AnswerContract, Citation, KeyFinding
from app.generator.narrative import NarrativeRenderer
from app.skills.loader import SkillDefinition


def _skill() -> SkillDefinition:
    return SkillDefinition(
        skill_id="general_chat",
        name="一般對話",
        description="d",
        category="general",
        system_prompt="你是助理。",
    )


def _contract() -> AnswerContract:
    return AnswerContract(
        summary="關於 RAG 的概念。",
        key_findings=[
            KeyFinding(point="RAG 是檢索增強生成。", citations=["c1"]),
            KeyFinding(point="向量檢索是基礎。", citations=["c2"]),
        ],
        caveats=["以下內容依當前知識庫整理。"],
        next_steps=["可進一步閱讀官方 docs"],
        citations=[
            Citation(chunk_id="c1", source="https://example.com/1", snippet="..."),
            Citation(chunk_id="c2", source="https://example.com/2", snippet="..."),
        ],
    )


class _OkLLM:
    async def complete(self, prompt: str) -> str:
        return "**摘要**\nRAG 是檢索增強生成 [來源 1]。"


class _RaisingLLM:
    async def complete(self, prompt: str) -> str:
        raise RuntimeError("boom")


@pytest.mark.asyncio
async def test_renders_via_llm():
    r = NarrativeRenderer(llm=_OkLLM())
    out = await r.render(contract=_contract(), skill=_skill(), response_mode="brief")
    assert out == ["**摘要**\nRAG 是檢索增強生成 [來源 1]。"]


@pytest.mark.asyncio
async def test_falls_back_when_llm_is_none():
    r = NarrativeRenderer(llm=None)
    out = await r.render(contract=_contract(), skill=_skill(), response_mode="brief")
    text = "\n".join(out)
    # 模板必含關鍵段落
    assert "**摘要**" in text
    assert "**重點**" in text
    assert "**注意事項**" in text
    assert "**來源**" in text
    # 明確標註降級
    assert "（降級輸出）" in text


@pytest.mark.asyncio
async def test_falls_back_on_llm_failure():
    r = NarrativeRenderer(llm=_RaisingLLM())
    out = await r.render(contract=_contract(), skill=_skill(), response_mode="brief")
    text = "\n".join(out)
    assert "（降級輸出）" in text


@pytest.mark.asyncio
async def test_fallback_includes_citation_markers():
    r = NarrativeRenderer(llm=None)
    out = await r.render(contract=_contract(), skill=_skill(), response_mode="brief")
    text = "\n".join(out)
    assert "[來源 1]" in text  # contract 有 citations，模板要帶上


@pytest.mark.asyncio
async def test_feedback_appended_to_prompt():
    """retry 時 feedback 應插入 prompt（給 P4 reflection 用）。"""
    captured = {}

    class _CapturingLLM:
        async def complete(self, prompt: str) -> str:
            captured["prompt"] = prompt
            return "ok"

    r = NarrativeRenderer(llm=_CapturingLLM())
    await r.render(
        contract=_contract(),
        skill=_skill(),
        response_mode="brief",
        feedback=["citation 沒對齊", "段落漏了 caveat"],
    )
    assert "（前一次的問題，請改善）" in captured["prompt"]
    assert "citation 沒對齊" in captured["prompt"]


@pytest.mark.asyncio
async def test_long_response_split_for_line():
    long_text = "段" * 6000  # 超過 default 4500

    class _LongLLM:
        async def complete(self, prompt: str) -> str:
            return long_text

    r = NarrativeRenderer(llm=_LongLLM(), line_max_message_chars=4500)
    out = await r.render(contract=_contract(), skill=_skill(), response_mode="brief")
    # 切段後每段都 ≤ max
    assert all(len(seg) <= 4500 for seg in out)
    # 且不丟字
    assert sum(len(seg) for seg in out) >= len(long_text)

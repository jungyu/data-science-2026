"""spec-05 Prompt Cache 驗收：

- 第二次呼叫同樣的 (skill, knowledge_version, user_input) 命中快取、跳過 LLM
- knowledge_version 改變後舊 key 自然失配 → 重新呼叫 LLM
- is_rag_required=False 不快取
- rag_chunks 為空（hallucination case）不快取
- cache_repo 內部 Supabase 錯誤不打斷主流程
"""

from __future__ import annotations

import asyncio

import pytest

from app.generator.responder import ResponseGenerator
from app.rag.schemas import KnowledgeChunk
from app.router.schemas import RouterResult
from app.skills.loader import SkillDefinition
from app.storage.cache_repo import build_cache_key


# ── Fakes ────────────────────────────────────────────────────────────────────


class _FakeLLM:
    def __init__(self, output: str = "LLM 真實回答") -> None:
        self.output = output
        self.calls = 0

    async def complete(self, prompt: str) -> str:
        self.calls += 1
        return self.output


class _InMemoryCacheRepo:
    """模擬 CacheRepository 的最小行為。"""

    def __init__(self, *, knowledge_version: int = 1) -> None:
        self.store: dict[str, str] = {}
        self.version = knowledge_version
        self.gets: list[str] = []
        self.sets: list[tuple[str, str]] = []

    async def get(self, cache_key: str) -> str | None:
        self.gets.append(cache_key)
        return self.store.get(cache_key)

    async def set(
        self,
        *,
        cache_key: str,
        user_input: str,
        skill_id: str,
        knowledge_version: int,
        response_text: str,
    ) -> None:
        self.store[cache_key] = response_text
        self.sets.append((cache_key, response_text))

    async def get_knowledge_version(self) -> int:
        return self.version


def _skill(skill_id: str = "tech_architect") -> SkillDefinition:
    return SkillDefinition(
        skill_id=skill_id,
        name=skill_id,
        description="desc",
        category="general",
        system_prompt="prompt",
    )


def _router(
    *, is_rag_required: bool = True, target_skill: str = "tech_architect"
) -> RouterResult:
    return RouterResult(
        target_skill=target_skill,
        is_rag_required=is_rag_required,
        rag_query="q",
        rag_categories=[],
        emotion_state="neutral",
        response_mode="structured",
        confidence=0.9,
    )


def _chunks(n: int = 1) -> list[KnowledgeChunk]:
    return [
        KnowledgeChunk(id=f"c-{i}", content=f"chunk {i}", category="general")
        for i in range(n)
    ]


def _run(coro):
    return asyncio.run(coro)


# ── 命中 / 未命中 ────────────────────────────────────────────────────────────


def test_second_call_hits_cache_and_skips_llm():
    llm = _FakeLLM(output="第一次回答")
    cache = _InMemoryCacheRepo(knowledge_version=1)
    gen = ResponseGenerator(llm=llm, cache_repo=cache, line_max_message_chars=1000)

    skill = _skill()
    router = _router()
    chunks = _chunks(2)

    # 第一次：miss → 寫入
    out1 = _run(
        gen.generate_response(
            user_input="什麼是 RAG？",
            router_result=router,
            skill=skill,
            rag_chunks=chunks,
            rag_context="some ctx",
            recent_history="",
        )
    )
    assert llm.calls == 1
    assert len(cache.sets) == 1
    assert "第一次回答" in out1[0]

    # 第二次：相同 inputs → cache hit，LLM 不再被呼叫
    out2 = _run(
        gen.generate_response(
            user_input="什麼是 RAG？",
            router_result=router,
            skill=skill,
            rag_chunks=chunks,
            rag_context="some ctx",
            recent_history="",
        )
    )
    assert llm.calls == 1  # 沒有新增
    assert "第一次回答" in out2[0]


def test_normalized_input_treats_case_and_whitespace_equally():
    """spec-05 §「Cache Key 設計」：normalized_user_input = strip + lower。"""
    llm = _FakeLLM()
    cache = _InMemoryCacheRepo(knowledge_version=1)
    gen = ResponseGenerator(llm=llm, cache_repo=cache, line_max_message_chars=1000)

    _run(
        gen.generate_response(
            user_input="What is RAG?",
            router_result=_router(),
            skill=_skill(),
            rag_chunks=_chunks(),
            rag_context="ctx",
            recent_history="",
        )
    )
    _run(
        gen.generate_response(
            user_input="  WHAT IS rag?  ",
            router_result=_router(),
            skill=_skill(),
            rag_chunks=_chunks(),
            rag_context="ctx",
            recent_history="",
        )
    )
    # 兩次應命中同一 cache key → LLM 只被叫一次
    assert llm.calls == 1


def test_knowledge_version_bump_invalidates_cache():
    """spec-05 §「Knowledge Version 來源」：version 變動 → 舊 key 失配 → 重新生成。"""
    llm = _FakeLLM(output="v1 答案")
    cache = _InMemoryCacheRepo(knowledge_version=1)
    gen = ResponseGenerator(llm=llm, cache_repo=cache, line_max_message_chars=1000)

    _run(
        gen.generate_response(
            user_input="同樣問題",
            router_result=_router(),
            skill=_skill(),
            rag_chunks=_chunks(),
            rag_context="ctx",
            recent_history="",
        )
    )
    assert llm.calls == 1

    # 升版本（模擬 ingest 後）+ 換 LLM 輸出
    cache.version = 2
    llm.output = "v2 答案"
    out = _run(
        gen.generate_response(
            user_input="同樣問題",
            router_result=_router(),
            skill=_skill(),
            rag_chunks=_chunks(),
            rag_context="ctx",
            recent_history="",
        )
    )
    assert llm.calls == 2
    assert "v2" in out[0]


# ── 不快取的 case ────────────────────────────────────────────────────────────


def test_no_cache_when_is_rag_required_false():
    """spec-05 §「不快取 is_rag_required=False 的回覆」。"""
    llm = _FakeLLM()
    cache = _InMemoryCacheRepo()
    gen = ResponseGenerator(llm=llm, cache_repo=cache, line_max_message_chars=1000)

    _run(
        gen.generate_response(
            user_input="嗨",
            router_result=_router(is_rag_required=False, target_skill="general_chat"),
            skill=_skill("general_chat"),
            rag_chunks=[],
            rag_context="",
            recent_history="",
        )
    )
    assert cache.gets == []
    assert cache.sets == []


def test_no_cache_when_rag_chunks_empty():
    """spec-05 §「快取條件」：rag_chunks 為空（避免快取知識庫不足回覆）→ 不快取。"""
    llm = _FakeLLM()
    cache = _InMemoryCacheRepo()
    gen = ResponseGenerator(llm=llm, cache_repo=cache, line_max_message_chars=1000)

    _run(
        gen.generate_response(
            user_input="未涵蓋的問題",
            router_result=_router(is_rag_required=True),
            skill=_skill(),
            rag_chunks=[],
            rag_context="",
            recent_history="",
        )
    )
    assert cache.gets == []
    assert cache.sets == []


def test_works_without_cache_repo():
    """cache_repo=None 時行為與舊版完全一致。"""
    llm = _FakeLLM()
    gen = ResponseGenerator(llm=llm, cache_repo=None, line_max_message_chars=1000)
    out = _run(
        gen.generate_response(
            user_input="q",
            router_result=_router(),
            skill=_skill(),
            rag_chunks=_chunks(),
            rag_context="ctx",
            recent_history="",
        )
    )
    assert llm.calls == 1
    assert out  # 有回應


# ── build_cache_key 純函式 ──────────────────────────────────────────────────


def test_build_cache_key_deterministic():
    k1 = build_cache_key(skill_id="x", knowledge_version=3, user_input=" Foo ")
    k2 = build_cache_key(skill_id="x", knowledge_version=3, user_input="foo")
    k3 = build_cache_key(skill_id="x", knowledge_version=4, user_input="foo")
    k4 = build_cache_key(skill_id="y", knowledge_version=3, user_input="foo")
    assert k1 == k2
    assert k1 != k3
    assert k1 != k4
    assert len(k1) == 64  # sha256 hex

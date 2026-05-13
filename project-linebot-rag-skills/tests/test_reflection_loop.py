"""Judge + Reflection 迴圈整合測試。對應 spec-17 / task-17 step 6 + 驗收標準。"""

from __future__ import annotations

import pytest

from app.skills.loader import SkillDefinition


@pytest.mark.asyncio
async def test_judge_pass_skips_retry(stub_services_judge_pass):
    """Judge 高分 → pass → 不重 render。reflection_retry 應為 0。"""
    final = await stub_services_judge_pass.rag_graph.ainvoke(
        {
            "user_input": "什麼是 RAG？",
            "external_user_id": "U_test",
            "recent_history": "",
        }
    )
    assert final["judge_score"] is not None
    assert final["judge_score"].groundedness == 9
    assert final.get("reflection_retry", 0) == 0
    assert not final.get("judge_warning_prefix", False)
    assert final["responses"] == ["假回覆"]


@pytest.mark.asyncio
async def test_judge_fail_triggers_one_retry_then_pass(stub_services_judge_fail_then_pass):
    """第一次 judge fail → retry → 第二次 pass。"""
    final = await stub_services_judge_fail_then_pass.rag_graph.ainvoke(
        {
            "user_input": "需要重 render 的問題",
            "external_user_id": "U_test",
            "recent_history": "",
        }
    )
    assert final["reflection_retry"] == 1
    assert not final.get("judge_warning_prefix", False)
    # 最終 score 是第二次 judge 的高分
    assert final["judge_score"].groundedness == 9


@pytest.mark.asyncio
async def test_retry_limit_forces_push_with_warning(stub_services_judge_always_fail):
    """Judge 永遠 fail → retry 達上限後 force_push、加 ⚠️ 品質警告，永不無限迴圈。"""
    final = await stub_services_judge_always_fail.rag_graph.ainvoke(
        {
            "user_input": "永遠失敗的問題",
            "external_user_id": "U_test",
            "recent_history": "",
        }
    )
    assert final["judge_warning_prefix"] is True
    assert final["responses"][0].startswith("⚠️ 品質警告")
    # max_reflection_retries=1 → retry 計數 1 後 force_push
    assert final["reflection_retry"] == 1
    # push 仍發生（一次）
    assert len(stub_services_judge_always_fail.line_client.pushed) == 1


@pytest.mark.asyncio
async def test_judge_skipped_for_no_rag(stub_services_no_rag):
    """is_rag_required=False → judge_node 視為 pass，judge_score=None。"""
    final = await stub_services_no_rag.rag_graph.ainvoke(
        {
            "user_input": "你好",
            "external_user_id": "U_test",
            "recent_history": "",
        }
    )
    assert final.get("judge_score") is None
    assert final["responses"] == ["假回覆"]


@pytest.mark.asyncio
async def test_judge_skipped_for_general_chat_skill(stub_services_judge_always_fail):
    """spec-17：skill=general_chat → judge 跳過。即使 ScriptedJudge 永遠 fail 也不會
    被呼叫到，不該觸發品質警告。

    （前版誤用 "small_talk" 比對，但 SkillId 沒有 "small_talk"——閒聊真實的
    skill_id 是 "general_chat"，導致生產環境 general_chat 永遠被 judge 評分。）
    """
    services = stub_services_judge_always_fail
    general_chat_skill = SkillDefinition(
        skill_id="general_chat",
        name="閒聊",
        description="d",
        category="general",
        system_prompt="prompt",
    )
    services.skill_registry._skill = general_chat_skill  # noqa: SLF001（測試用）

    final = await services.rag_graph.ainvoke(
        {
            "user_input": "嗨",
            "external_user_id": "U_test",
            "recent_history": "",
        }
    )
    assert final.get("judge_score") is None
    assert not final.get("judge_warning_prefix", False)
    # 不該觸發品質警告
    assert not final["responses"][0].startswith("⚠️")

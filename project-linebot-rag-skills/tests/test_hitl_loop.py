"""HITL interrupt + resume 整合測試。對應 task-21 步驟 9。"""

from __future__ import annotations

import pytest


_THREAD_CFG = {"configurable": {"thread_id": "test-thread-1"}}
_INITIAL_STATE = {
    "user_input": "永遠失敗的問題",
    "external_user_id": "U_test",
    "channel": "line",
    "external_message_id": "msg-1",
    "recent_history": "",
}


@pytest.mark.asyncio
async def test_hitl_interrupts_before_human_review(stub_services_hitl_always_fail):
    """Judge 永遠 fail → retry 用盡 → human_review 前 interrupt → push 不發生。"""
    services = stub_services_hitl_always_fail
    await services.rag_graph.ainvoke(_INITIAL_STATE, config=_THREAD_CFG)

    snapshot = services.rag_graph.get_state(_THREAD_CFG)
    # next 指向 human_review（尚未執行）
    assert "human_review" in snapshot.next
    # push 還沒跑 → line_client.pushed 為空
    assert services.line_client.pushed == []
    # judge fail 已記錄
    assert snapshot.values["judge_score"] is not None
    assert not snapshot.values["judge_score"].passes()


@pytest.mark.asyncio
async def test_hitl_approve_resumes_with_original(stub_services_hitl_always_fail):
    """approve → resume → push 推原 narrative。"""
    services = stub_services_hitl_always_fail
    await services.rag_graph.ainvoke(_INITIAL_STATE, config=_THREAD_CFG)
    services.rag_graph.update_state(
        _THREAD_CFG, {"reviewer_decision": "approve"}
    )
    await services.rag_graph.ainvoke(None, config=_THREAD_CFG)

    assert services.line_client.pushed == [("U_test", ["假回覆"])]


@pytest.mark.asyncio
async def test_hitl_revise_pushes_revised_text(stub_services_hitl_always_fail):
    """revise → resume 後 push 用 reviewer_revised_text 而非原 responses。"""
    services = stub_services_hitl_always_fail
    await services.rag_graph.ainvoke(_INITIAL_STATE, config=_THREAD_CFG)
    services.rag_graph.update_state(
        _THREAD_CFG,
        {
            "reviewer_decision": "revise",
            "reviewer_revised_text": "（人工修正後內容）",
        },
    )
    await services.rag_graph.ainvoke(None, config=_THREAD_CFG)

    assert services.line_client.pushed == [("U_test", ["（人工修正後內容）"])]


@pytest.mark.asyncio
async def test_hitl_drop_skips_push(stub_services_hitl_always_fail):
    """drop → resume 後 push 完全不發生。"""
    services = stub_services_hitl_always_fail
    await services.rag_graph.ainvoke(_INITIAL_STATE, config=_THREAD_CFG)
    services.rag_graph.update_state(_THREAD_CFG, {"reviewer_decision": "drop"})
    await services.rag_graph.ainvoke(None, config=_THREAD_CFG)

    assert services.line_client.pushed == []


@pytest.mark.asyncio
async def test_hitl_disabled_keeps_force_push_path(stub_services_judge_always_fail):
    """hitl_enabled=False（既有 fixture）→ 走 mark_warning 路徑、無 interrupt。"""
    services = stub_services_judge_always_fail
    final = await services.rag_graph.ainvoke(_INITIAL_STATE)
    # 無 interrupt → 直接 push 完成
    assert final.get("judge_warning_prefix") is True
    assert services.line_client.pushed != []


@pytest.mark.asyncio
async def test_hitl_judge_pass_doesnt_interrupt(stub_services_judge_pass):
    """Judge pass → 不走 human_review → 即使 hitl_enabled 也不該 interrupt。"""
    from langgraph.checkpoint.memory import InMemorySaver

    services = stub_services_judge_pass
    services.settings.hitl_enabled = True
    services.checkpointer = InMemorySaver()
    from app.graph.variants.reflection import build_reflection_graph
    services.rag_graph = build_reflection_graph(services)

    final = await services.rag_graph.ainvoke(_INITIAL_STATE, config=_THREAD_CFG)
    # 完整跑完，無 interrupt
    assert final.get("responses") == ["假回覆"]
    snapshot = services.rag_graph.get_state(_THREAD_CFG)
    assert not snapshot.next  # 已到 END
    assert services.line_client.pushed != []


@pytest.mark.asyncio
async def test_hitl_basic_variant_unaffected(stub_services):
    """basic variant 不受 hitl_enabled 影響（HITL 只配 reflection）。"""
    stub_services.settings.hitl_enabled = True
    from app.graph.variants.basic import build_basic_graph
    g = build_basic_graph(stub_services)
    final = await g.ainvoke(_INITIAL_STATE)
    # basic 無 judge / human_review → 直接走完
    assert stub_services.line_client.pushed != []


@pytest.mark.asyncio
async def test_hitl_enabled_without_checkpointer_raises():
    """sanity guard：hitl_enabled=True 但無 checkpointer → build 時 raise。"""
    import pytest as _pytest

    from app.graph.variants.reflection import build_reflection_graph

    class _Services:
        class settings:
            hitl_enabled = True
            max_reflection_retries = 1
        checkpointer = None
        # ... reflection variant build 不會用到其他 services（partial 在 ainvoke 時才呼叫）
        def __getattr__(self, name):
            return None

    with _pytest.raises(RuntimeError, match="hitl_enabled=True"):
        build_reflection_graph(_Services())

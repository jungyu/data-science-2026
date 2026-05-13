"""P1 等價重構驗證：graph 與重構前線性 pipeline 行為一致。

對應 spec-12 / task-12 step 8。
"""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_graph_runs_linearly(stub_services):
    """4 個 node 依序跑完，state 累積完整。"""
    final = await stub_services.rag_graph.ainvoke(
        {
            "user_input": "什麼是 RAG？",
            "external_user_id": "U_test",
            "recent_history": "",
        }
    )
    assert final["router_result"] is not None
    # conftest _StubRouter 預設 target_skill=tech_architect（為了讓 judge 流程
    # 的測試有作用——general_chat 在 SKIP_JUDGE_SKILLS 中）。
    assert final["router_result"].target_skill == "tech_architect"
    assert final["skill"].skill_id == "tech_architect"
    assert final["responses"] == ["假回覆"]
    # push_node 已經呼叫 line_client
    assert stub_services.line_client.pushed == [("U_test", ["假回覆"])]


@pytest.mark.asyncio
async def test_renderer_failure_returns_fallback(stub_services_failing_renderer):
    """Stage 2 renderer 失敗 → render_narrative_node 回固定錯誤訊息，push 仍發生。

    取代 P1 階段的 responder failure test：兩階段 generator 落地後，graph 走的
    是 narrative_renderer 而非 responder。
    """
    final = await stub_services_failing_renderer.rag_graph.ainvoke(
        {
            "user_input": "壞掉的問題",
            "external_user_id": "U_test",
            "recent_history": "",
        }
    )
    assert final["responses"] == ["系統暫時無法完成此請求，請稍後再試。"]
    assert stub_services_failing_renderer.line_client.pushed == [
        ("U_test", ["系統暫時無法完成此請求，請稍後再試。"])
    ]


@pytest.mark.asyncio
async def test_no_rag_required_skips_retrieve(stub_services_no_rag):
    """router 回 is_rag_required=False 時，rag_chunks 為空，rag_context 是預設字串。"""
    final = await stub_services_no_rag.rag_graph.ainvoke(
        {
            "user_input": "你好",
            "external_user_id": "U_test",
            "recent_history": "",
        }
    )
    assert final["rag_chunks"] == []
    assert final["rag_context"] == "No retrieved context."
    assert final["responses"] == ["假回覆"]


@pytest.mark.asyncio
async def test_multi_seed_fan_out_collects_hits(stub_services):
    """RAG 路徑：seeds 展開後 retrieve_one 並行命中，hits_per_seed 累積、fuse 取頂。"""
    final = await stub_services.rag_graph.ainvoke(
        {
            "user_input": "什麼是 RAG？",
            "external_user_id": "U_test",
            "recent_history": "",
        }
    )
    # DefaultSeedExpander 至少給出 1 條 seed（primary_topic = user_input[:50]）
    assert len(final["seeds"]) >= 1
    # 每條 seed 都該有 1 筆 hit（_StubRetriever 回傳固定一筆）
    assert len(final["hits_per_seed"]) == len(final["seeds"])
    # fuse 後 rag_chunks 仍有內容（dedupe by id 後仍 ≥ 1）
    assert len(final["rag_chunks"]) >= 1
    assert "topic content" in final["rag_context"]


@pytest.mark.asyncio
async def test_no_rag_skips_fan_out_entirely(stub_services_no_rag):
    """is_rag_required=False 時 seeds 為空，fan-out 直接跳到 fuse_scores。"""
    final = await stub_services_no_rag.rag_graph.ainvoke(
        {
            "user_input": "你好",
            "external_user_id": "U_test",
            "recent_history": "",
        }
    )
    assert final.get("seeds") == []
    assert final.get("hits_per_seed") == []
    assert final["rag_chunks"] == []
    # 不需 RAG 也應視為 sufficient → 走 generate 分支（不該 clarify）
    assert final["sufficiency"] == "sufficient"
    assert final["responses"] == ["假回覆"]


@pytest.mark.asyncio
async def test_sufficient_branch_goes_to_generate(stub_services):
    """RAG 路徑 + 充足 chunks → sufficient → generate → 回正常 response。"""
    final = await stub_services.rag_graph.ainvoke(
        {
            "user_input": "什麼是 RAG？",
            "external_user_id": "U_test",
            "recent_history": "",
        }
    )
    assert final["sufficiency"] == "sufficient"
    assert final["sufficiency_reasons"] == []
    assert final["responses"] == ["假回覆"]


@pytest.mark.asyncio
async def test_two_stage_generator_produces_contract(stub_services):
    """sufficient 路徑：build_answer_contract 先寫 contract，render_narrative 再產 responses。"""
    from app.generator.contract import AnswerContract

    final = await stub_services.rag_graph.ainvoke(
        {
            "user_input": "什麼是 RAG？",
            "external_user_id": "U_test",
            "recent_history": "",
        }
    )
    # Stage 1 產出 contract
    assert isinstance(final["answer_contract"], AnswerContract)
    contract = final["answer_contract"]
    assert contract.summary
    # 有 chunks → 應有 key_findings
    assert len(contract.key_findings) >= 1
    assert len(contract.citations) >= 1
    # Stage 2 產出 responses（_StubNarrativeRenderer 回常數）
    assert final["responses"] == ["假回覆"]


@pytest.mark.asyncio
async def test_insufficient_branch_goes_to_clarify(stub_services_insufficient):
    """RAG 路徑 + 空 chunks → insufficient → clarify → push 追問。"""
    final = await stub_services_insufficient.rag_graph.ainvoke(
        {
            "user_input": "知識庫沒有的問題",
            "external_user_id": "U_test",
            "recent_history": "",
        }
    )
    assert final["sufficiency"] == "insufficient"
    assert len(final["sufficiency_reasons"]) >= 1
    assert "clarification_questions" in final
    assert len(final["clarification_questions"]) >= 1
    # responses 是 clarify 文字（不是 _StubResponder 的 "假回覆"）
    assert final["responses"][0].startswith("我需要再確認幾件事：")
    # push 仍會發生
    assert stub_services_insufficient.line_client.pushed[0][0] == "U_test"

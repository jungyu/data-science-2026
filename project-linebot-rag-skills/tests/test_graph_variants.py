"""三變體並陳測試。對應 spec-19 / task-19 step 8。"""

from __future__ import annotations

import pytest

from app.graph.variants import (
    VARIANT_BUILDERS,
    build_basic_graph,
    build_reflection_graph,
    build_selfrag_graph,
)


def test_variant_registry_has_three():
    assert set(VARIANT_BUILDERS.keys()) == {"basic", "selfrag", "reflection"}


def test_each_variant_compiles(stub_services):
    """三 variant 都能用同一份 services build 出可執行 graph。"""
    for name, builder in VARIANT_BUILDERS.items():
        graph = builder(stub_services)
        assert graph is not None, f"variant {name} did not compile"


def test_basic_topology_is_minimal(stub_services):
    """basic variant 不含 multi-seed / sufficiency / judge 的 node。"""
    g = build_basic_graph(stub_services)
    nodes = set(g.get_graph().nodes.keys())
    # basic 有的：route, retrieve, generate, push（+ start/end auto-added）
    assert {"route", "retrieve", "generate", "push"}.issubset(nodes)
    # basic 不該有的：multi-seed 與 P3/P4 的 node
    forbidden = {"extract_features", "expand_seeds", "retrieve_one", "fuse_scores",
                 "check_sufficiency", "clarify", "build_answer_contract",
                 "render_narrative", "judge", "increment_retry", "mark_warning"}
    assert nodes & forbidden == set(), f"basic should not contain {nodes & forbidden}"


def test_selfrag_topology_no_judge(stub_services):
    """selfrag 含 P2/P3 但不含 P4 judge。"""
    g = build_selfrag_graph(stub_services)
    nodes = set(g.get_graph().nodes.keys())
    assert {"extract_features", "expand_seeds", "fuse_scores",
            "check_sufficiency", "clarify",
            "build_answer_contract", "render_narrative"}.issubset(nodes)
    assert "judge" not in nodes
    assert "increment_retry" not in nodes
    assert "mark_warning" not in nodes


def test_reflection_topology_full(stub_services):
    """reflection 含全部 phase。"""
    g = build_reflection_graph(stub_services)
    nodes = set(g.get_graph().nodes.keys())
    assert {"extract_features", "expand_seeds", "fuse_scores",
            "check_sufficiency", "clarify",
            "build_answer_contract", "render_narrative",
            "judge", "increment_retry", "mark_warning"}.issubset(nodes)


@pytest.mark.asyncio
async def test_basic_variant_runs_end_to_end(stub_services):
    """basic variant：route → retrieve → generate → push，回傳 _StubResponder 的 "假回覆"。"""
    g = build_basic_graph(stub_services)
    final = await g.ainvoke(
        {
            "user_input": "什麼是 RAG？",
            "external_user_id": "U_test",
            "recent_history": "",
        }
    )
    # 走的是 generate_basic_node → services.responder.generate_response
    assert final["responses"] == ["假回覆"]
    # 不應有 P3/P4 欄位
    assert final.get("answer_contract") is None
    assert final.get("judge_score") is None


@pytest.mark.asyncio
async def test_selfrag_variant_runs_end_to_end(stub_services):
    g = build_selfrag_graph(stub_services)
    final = await g.ainvoke(
        {
            "user_input": "什麼是 RAG？",
            "external_user_id": "U_test",
            "recent_history": "",
        }
    )
    # 走的是 build_answer_contract + render_narrative
    assert final["answer_contract"] is not None
    assert final["sufficiency"] == "sufficient"
    # 沒經過 judge
    assert final.get("judge_score") is None
    assert final["responses"] == ["假回覆"]


@pytest.mark.asyncio
async def test_reflection_variant_runs_end_to_end(stub_services_judge_pass):
    g = build_reflection_graph(stub_services_judge_pass)
    final = await g.ainvoke(
        {
            "user_input": "什麼是 RAG？",
            "external_user_id": "U_test",
            "recent_history": "",
        }
    )
    assert final["answer_contract"] is not None
    assert final["judge_score"] is not None
    assert final["judge_score"].groundedness == 9


@pytest.mark.asyncio
async def test_demo_user_id_skips_push(stub_services):
    """U_demo 前綴 → push_node 略過實際呼叫 LINE，便於離線比較 demo。"""
    g = build_basic_graph(stub_services)
    final = await g.ainvoke(
        {
            "user_input": "什麼是 RAG？",
            "external_user_id": "U_demo_test",
            "recent_history": "",
            "dry_run": True,
        }
    )
    # responses 仍產出，但 line_client 不被呼叫
    assert final["responses"] == ["假回覆"]
    assert stub_services.line_client.pushed == []


@pytest.mark.asyncio
async def test_settings_variant_dispatches(stub_services):
    """build_rag_graph 依 settings.graph_variant 切換 variant。"""
    from app.graph.rag_graph import build_rag_graph

    stub_services.settings.graph_variant = "basic"
    g = build_rag_graph(stub_services)
    assert "judge" not in set(g.get_graph().nodes.keys())

    stub_services.settings.graph_variant = "selfrag"
    g = build_rag_graph(stub_services)
    nodes = set(g.get_graph().nodes.keys())
    assert "build_answer_contract" in nodes
    assert "judge" not in nodes

    stub_services.settings.graph_variant = "reflection"
    g = build_rag_graph(stub_services)
    assert "judge" in set(g.get_graph().nodes.keys())


def test_unknown_variant_raises(stub_services):
    from app.graph.rag_graph import build_rag_graph

    stub_services.settings.graph_variant = "nonsense"
    with pytest.raises(ValueError, match="unknown graph_variant"):
        build_rag_graph(stub_services)

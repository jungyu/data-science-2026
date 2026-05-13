"""GraphTracer + TracerRegistry + @traced 測試。對應 task-22 步驟 10。"""

from __future__ import annotations

import json

import pytest

from app.observability.pricing import PRICING_USD_PER_1M, estimate_cost_usd
from app.observability.tracer import (
    GraphTracer,
    TracerRegistry,
    get_current_tracer,
    record_llm_call_if_traced,
    reset_current_tracer,
    set_current_tracer,
    traced,
)


# ---- pricing ---------------------------------------------------------------


def test_estimate_cost_known_model():
    p = PRICING_USD_PER_1M["gpt-4.1-mini"]
    expected = (1000 * p["input"] + 500 * p["output"]) / 1_000_000
    assert (
        estimate_cost_usd(model="gpt-4.1-mini", input_tokens=1000, output_tokens=500)
        == pytest.approx(expected)
    )


def test_estimate_cost_unknown_returns_zero():
    assert (
        estimate_cost_usd(model="nonexistent", input_tokens=1000, output_tokens=500)
        == 0.0
    )


# ---- GraphTracer ---------------------------------------------------------


def test_span_records_enter_and_exit():
    t = GraphTracer(thread_id="x", variant="basic")
    with t.span(node="route"):
        pass
    phases = [e["phase"] for e in t.events if e["node"] == "route"]
    assert phases == ["node_enter", "node_exit"]


def test_span_extra_kwargs_carried():
    t = GraphTracer(thread_id="x", variant="reflection")
    with t.span(node="render_narrative", retry=2):
        pass
    enter = [e for e in t.events if e["phase"] == "node_enter"][0]
    assert enter["retry"] == 2


def test_llm_call_accumulates_tokens_and_cost():
    t = GraphTracer(thread_id="x", variant="basic")
    t.record_llm_call(
        node="x", model="gpt-4.1-mini", provider="openai",
        input_tokens=100, output_tokens=50, duration_ms=200,
    )
    t.record_llm_call(
        node="y", model="gpt-4.1-mini", provider="openai",
        input_tokens=200, output_tokens=100, duration_ms=300,
    )
    assert t.total_input_tokens == 300
    assert t.total_output_tokens == 150
    assert t.total_cost_usd > 0


def test_finalize_returns_payload():
    t = GraphTracer(thread_id="x", variant="basic")
    with t.span(node="route"):
        pass
    payload = t.finalize()
    assert payload["variant"] == "basic"
    assert payload["thread_id"] == "x"
    assert payload["total_duration_ms"] >= 0
    assert any(nt["node"] == "route" for nt in payload["node_timings"])


# ---- TracerRegistry write -----------------------------------------------


def test_write_trace_creates_file(tmp_path):
    reg = TracerRegistry(trace_dir=tmp_path)
    tracer = reg.start(thread_id="line-U1-msg1", variant="basic")
    with tracer.span(node="route"):
        pass
    out = reg.write_trace(tracer)
    assert out.exists()
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["thread_id"] == "line-U1-msg1"


def test_write_trace_sanitizes_filename(tmp_path):
    reg = TracerRegistry(trace_dir=tmp_path)
    tracer = reg.start(thread_id="line/U1/msg1", variant="basic")
    out = reg.write_trace(tracer)
    # 檔名替換掉 "/"
    assert "/" not in out.name
    assert out.exists()


# ---- persist=True 路徑（spec-22 §Supabase Schema）----------------------------


class _StubTracesRepo:
    def __init__(self) -> None:
        self.inserts: list[dict] = []

    async def insert(self, payload: dict) -> None:
        self.inserts.append(payload)


@pytest.mark.asyncio
async def test_async_write_trace_persists_when_enabled(tmp_path):
    """spec-22 驗收：OBSERVABILITY_PERSIST=true 時 async_write_trace 會把
    finalize() payload 寫進 traces_repo。"""
    repo = _StubTracesRepo()
    reg = TracerRegistry(trace_dir=tmp_path, persist=True, traces_repo=repo)
    tracer = reg.start(thread_id="line-U1-msg1", variant="reflection")
    with tracer.span(node="route"):
        pass

    out = await reg.async_write_trace(tracer)
    assert out.exists()
    assert len(repo.inserts) == 1
    assert repo.inserts[0]["thread_id"] == "line-U1-msg1"
    assert repo.inserts[0]["variant"] == "reflection"


@pytest.mark.asyncio
async def test_async_write_trace_skips_supabase_when_persist_false(tmp_path):
    """persist=False 時不該呼叫 traces_repo（即使有注入）。"""
    repo = _StubTracesRepo()
    reg = TracerRegistry(trace_dir=tmp_path, persist=False, traces_repo=repo)
    tracer = reg.start(thread_id="x", variant="basic")
    await reg.async_write_trace(tracer)
    assert repo.inserts == []


@pytest.mark.asyncio
async def test_async_write_trace_warns_when_persist_without_repo(tmp_path, caplog):
    """persist=True 但 traces_repo=None 時 log 警告但不該 raise。"""
    import logging

    reg = TracerRegistry(trace_dir=tmp_path, persist=True, traces_repo=None)
    tracer = reg.start(thread_id="x", variant="basic")
    with caplog.at_level(logging.WARNING, logger="observability"):
        await reg.async_write_trace(tracer)
    assert any("traces_repo is None" in rec.message for rec in caplog.records)


# ---- ContextVar dispatch -------------------------------------------------


def test_set_and_reset_current_tracer():
    assert get_current_tracer() is None
    t = GraphTracer(thread_id="x", variant="basic")
    token = set_current_tracer(t)
    try:
        assert get_current_tracer() is t
    finally:
        reset_current_tracer(token)
    assert get_current_tracer() is None


def test_record_llm_call_no_op_when_no_tracer():
    """無 tracer context → record_llm_call_if_traced 不應 raise。"""
    record_llm_call_if_traced(
        model="gpt-4.1", provider="openai",
        input_tokens=100, output_tokens=50, duration_ms=200,
    )


def test_record_llm_call_writes_when_traced():
    t = GraphTracer(thread_id="x", variant="basic")
    token = set_current_tracer(t)
    try:
        record_llm_call_if_traced(
            model="gpt-4.1-mini", provider="openai",
            input_tokens=100, output_tokens=50, duration_ms=200,
        )
    finally:
        reset_current_tracer(token)
    assert t.total_input_tokens == 100


# ---- @traced decorator --------------------------------------------------


@pytest.mark.asyncio
async def test_traced_decorator_creates_span():
    @traced("test_node")
    async def fn(state, services):
        return {"ok": True}

    t = GraphTracer(thread_id="x", variant="basic")
    token = set_current_tracer(t)
    try:
        result = await fn({"reflection_retry": 0}, None)
    finally:
        reset_current_tracer(token)
    assert result == {"ok": True}
    assert any(e["node"] == "test_node" for e in t.events)


@pytest.mark.asyncio
async def test_traced_decorator_no_op_when_no_tracer():
    @traced("test_node")
    async def fn(state, services):
        return {"ok": True}

    result = await fn({}, None)
    assert result == {"ok": True}


# ---- 端對端：graph 跑完後產生 trace -------------------------------------


@pytest.mark.asyncio
async def test_graph_with_tracer_produces_trace(stub_services):
    """跑完 graph 後 tracer 的 events 含每個 node 的 enter/exit。"""
    t = GraphTracer(thread_id="test", variant="reflection")
    token = set_current_tracer(t)
    try:
        await stub_services.rag_graph.ainvoke(
            {
                "user_input": "什麼是 RAG？",
                "external_user_id": "U_test",
                "recent_history": "",
            }
        )
    finally:
        reset_current_tracer(token)

    nodes_seen = {e["node"] for e in t.events if e["phase"] == "node_exit"}
    # 至少這幾個 node 應該都被經過
    assert "route" in nodes_seen
    assert "extract_features" in nodes_seen
    assert "push" in nodes_seen

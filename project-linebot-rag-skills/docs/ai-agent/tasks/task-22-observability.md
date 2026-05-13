# task-22：Observability + Cost Tracking

> 規格詳見 [spec-22](../specs/spec-22-observability.md)
>
> **✅ 已完成（commit `2387555`）** — 實作記錄與驗收測試見 spec-22 頂部「實作狀態」段。
---

加結構化 log + per-invocation trace JSON + cost 估算 + summary CLI。spec-19 demo / spec-20 eval / spec-21 HITL 都共用這個觀測底座。

## 前置

- task-12 ~ task-19 完成（觀測 instrument 散落在每個 node）
- 不阻塞其他 task：可獨立完成

## 前置安裝

`pyproject.toml` 加：

```toml
"python-json-logger>=2.0",
```

## 步驟 1：Settings

修改 `app/config.py`：

```python
observability_enabled: bool = True
observability_persist: bool = False     # 寫 Supabase graph_traces table
trace_dir: str = ".traces"
```

## 步驟 2：定價表

新增 `app/observability/__init__.py`、`app/observability/pricing.py`：

```python
"""Per-million-token pricing (USD)。學生若要用其他 model 自行擴充。"""

PRICING_USD_PER_1M: dict[str, dict[str, float]] = {
    "gpt-4.1": {"input": 2.50, "output": 10.00},
    "gpt-4.1-mini": {"input": 0.15, "output": 0.60},
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00},
    "claude-haiku-4-5-20251001": {"input": 0.80, "output": 4.00},
    "gemini-2.5-flash": {"input": 0.075, "output": 0.30},
    "gemini-2.5-pro": {"input": 1.25, "output": 5.00},
}


def estimate_cost_usd(*, model: str, input_tokens: int, output_tokens: int) -> float:
    p = PRICING_USD_PER_1M.get(model)
    if p is None:
        return 0.0
    return (input_tokens * p["input"] + output_tokens * p["output"]) / 1_000_000
```

## 步驟 3：Tracer

新增 `app/observability/tracer.py`：

```python
from __future__ import annotations

import json
import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

from app.observability.pricing import estimate_cost_usd

logger = logging.getLogger("observability")


@dataclass
class Span:
    node: str
    started_at: float
    ended_at: float | None = None
    extra: dict = field(default_factory=dict)

    @property
    def duration_ms(self) -> int:
        end = self.ended_at or time.time()
        return int((end - self.started_at) * 1000)


@dataclass
class GraphTracer:
    thread_id: str
    variant: str
    started_at: float = field(default_factory=time.time)
    events: list[dict] = field(default_factory=list)
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cost_usd: float = 0.0
    finished_at: float | None = None

    @contextmanager
    def span(self, *, node: str, **extra) -> Iterator[Span]:
        s = Span(node=node, started_at=time.time(), extra=extra)
        self.events.append({"phase": "node_enter", "node": node, "ts": s.started_at, **extra})
        try:
            yield s
        finally:
            s.ended_at = time.time()
            self.events.append({
                "phase": "node_exit",
                "node": node,
                "duration_ms": s.duration_ms,
                "ts": s.ended_at,
                **extra,
            })

    def record_llm_call(
        self, *, node: str, model: str, provider: str,
        input_tokens: int, output_tokens: int,
        cached_tokens: int = 0, duration_ms: int,
    ) -> None:
        cost = estimate_cost_usd(model=model, input_tokens=input_tokens, output_tokens=output_tokens)
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_cost_usd += cost
        self.events.append({
            "phase": "llm_call",
            "node": node,
            "model": model,
            "provider": provider,
            "tokens": {"input": input_tokens, "output": output_tokens, "cached": cached_tokens},
            "duration_ms": duration_ms,
            "estimated_cost_usd": cost,
            "ts": time.time(),
        })

    def finalize(self) -> dict:
        self.finished_at = time.time()
        node_timings: list[dict] = []
        # 配對 node_enter / node_exit
        in_progress: dict[str, float] = {}
        for ev in self.events:
            if ev["phase"] == "node_enter":
                in_progress[ev["node"]] = ev["ts"]
            elif ev["phase"] == "node_exit":
                started = in_progress.pop(ev["node"], ev["ts"])
                node_timings.append({"node": ev["node"], "duration_ms": ev["duration_ms"]})
        return {
            "thread_id": self.thread_id,
            "variant": self.variant,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "total_duration_ms": int((self.finished_at - self.started_at) * 1000),
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_cost_usd": round(self.total_cost_usd, 6),
            "node_timings": node_timings,
            "events": self.events,
        }


class TracerRegistry:
    """每個 thread_id 對應一個 GraphTracer；node 透過 services.tracer.for_thread(state)。"""

    def __init__(self, *, trace_dir: str = ".traces", persist: bool = False) -> None:
        self._tracers: dict[str, GraphTracer] = {}
        self._dir = Path(trace_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._persist = persist

    def for_thread(self, state: dict) -> GraphTracer:
        thread_id = state.get("line_user_id", "unknown") + "-" + str(id(state))
        if thread_id not in self._tracers:
            variant = state.get("_variant", "unknown")
            self._tracers[thread_id] = GraphTracer(thread_id=thread_id, variant=variant)
        return self._tracers[thread_id]

    def write_trace(self, tracer: GraphTracer) -> Path:
        payload = tracer.finalize()
        path = self._dir / f"{tracer.thread_id}.json"
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path
```

> 教學版簡化：tracer 鍵直接用 thread_id；正式版會用 langgraph 的 thread_id。每次 graph 完整跑完後手動呼叫 `write_trace`。

## 步驟 4：把 trace 接進 nodes

修改 `app/graph/nodes.py`（每個 node 包 `with tracer.span(...)`）。範例：

```python
async def render_narrative_node(state: RAGState, services: Any) -> dict[str, Any]:
    tracer = services.tracer.for_thread(state) if services.tracer else None

    async def _do():
        # ... 原邏輯
        ...

    if tracer is None:
        return await _do()
    with tracer.span(node="render_narrative", retry=state.get("reflection_retry", 0)):
        return await _do()
```

> 為避免每個 node 都重複這 if 樣板，可寫一個 `@traced("node_name")` decorator 包起來。

## 步驟 5：擴充 LLM provider 回 usage

修改 `app/ai/providers/openai_provider.py` 等：`complete()` 回傳 `(text, usage)` tuple，或在 provider 內部呼叫 `services.tracer.record_llm_call(...)`。

最小破壞性做法：provider 維持原 `complete(prompt) -> str`，**內部**呼叫 tracer：

```python
class OpenAILLM:
    def __init__(self, settings, model, *, tracer=None):
        self._tracer = tracer
        # ...

    async def complete(self, prompt: str) -> str:
        t0 = time.time()
        resp = await self._client.responses.create(...)
        if self._tracer:
            usage = resp.usage  # OpenAI / Claude / Gemini 各家欄位名不同
            self._tracer.record_llm_call(
                node="<unknown>",  # 由 caller 補；可改用 contextvar
                model=self._model,
                provider="openai",
                input_tokens=usage.input_tokens,
                output_tokens=usage.output_tokens,
                duration_ms=int((time.time() - t0) * 1000),
            )
        return resp.output_text
```

> 「node 名稱」如何傳給 provider 是個小設計問題。最簡單：用 contextvar 在 node entry 設、provider 讀。教學版可暫時記 `node="(llm_call)"`，學生若要精確 attribute 再升級。

## 步驟 6：包進 webhook

修改 `app/line/webhook.py`：

```python
final_state = await services.rag_graph.ainvoke(initial_state)

if services.tracer_registry:
    tracer = services.tracer_registry.for_thread(initial_state)
    services.tracer_registry.write_trace(tracer)
```

## 步驟 7：DI

修改 `app/dependencies.py`：

```python
@lru_cache(maxsize=1)
def get_tracer_registry():
    s = get_settings()
    if not s.observability_enabled:
        return None
    return TracerRegistry(trace_dir=s.trace_dir, persist=s.observability_persist)
```

`RuntimeServices` 加 `tracer_registry`。

## 步驟 8：CLI

新增 `scripts/trace.py`：

```python
"""Trace CLI。

用法：
    python scripts/trace.py show <thread_id>
    python scripts/trace.py summary --last 50
    python scripts/trace.py top --by duration --limit 5
    python scripts/trace.py top --by cost --limit 5
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def _load_traces(trace_dir: Path) -> list[dict]:
    return [json.loads(p.read_text(encoding="utf-8")) for p in trace_dir.glob("*.json")]


def cmd_show(thread_id: str, trace_dir: Path):
    p = trace_dir / f"{thread_id}.json"
    if not p.exists():
        print(f"no trace for {thread_id}")
        return
    data = json.loads(p.read_text(encoding="utf-8"))
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_summary(last: int, trace_dir: Path):
    traces = sorted(_load_traces(trace_dir), key=lambda t: t["started_at"], reverse=True)[:last]
    by_variant: dict[str, list[dict]] = {}
    for t in traces:
        by_variant.setdefault(t["variant"], []).append(t)

    print(f"{'variant':12} | {'n':>3} | {'p50_ms':>7} | {'p95_ms':>7} | {'avg_cost':>10}")
    for variant, ts in by_variant.items():
        durations = sorted(t["total_duration_ms"] for t in ts)
        n = len(durations)
        p50 = durations[n // 2]
        p95 = durations[int(n * 0.95)] if n >= 20 else durations[-1]
        avg_cost = sum(t["total_cost_usd"] for t in ts) / n
        print(f"{variant:12} | {n:>3} | {p50:>7} | {p95:>7} | ${avg_cost:>8.4f}")


def cmd_top(by: str, limit: int, trace_dir: Path):
    traces = _load_traces(trace_dir)
    key = "total_duration_ms" if by == "duration" else "total_cost_usd"
    top = sorted(traces, key=lambda t: t[key], reverse=True)[:limit]
    for t in top:
        print(f"{t['thread_id']:50} {t['variant']:12} {t[key]}")


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("show"); p.add_argument("thread_id")
    p = sub.add_parser("summary"); p.add_argument("--last", type=int, default=50)
    p = sub.add_parser("top"); p.add_argument("--by", choices=["duration", "cost"], default="duration")
    p.add_argument("--limit", type=int, default=5)
    parser.add_argument("--trace-dir", default=".traces")
    args = parser.parse_args()

    trace_dir = Path(args.trace_dir)
    if args.cmd == "show": cmd_show(args.thread_id, trace_dir)
    elif args.cmd == "summary": cmd_summary(args.last, trace_dir)
    elif args.cmd == "top": cmd_top(args.by, args.limit, trace_dir)


if __name__ == "__main__":
    main()
```

## 步驟 9：Supabase schema（opt-in）

新增 `supabase/observability_schema.sql`：

```sql
create table if not exists graph_traces (
  id uuid primary key default gen_random_uuid(),
  thread_id text not null,
  variant text not null,
  started_at timestamptz not null,
  finished_at timestamptz not null,
  total_duration_ms int not null,
  total_input_tokens int default 0,
  total_output_tokens int default 0,
  total_cost_usd numeric(10, 6) default 0,
  payload jsonb not null,
  created_at timestamptz default now()
);

create index on graph_traces (variant, started_at desc);
create index on graph_traces (thread_id);
```

`scripts/apply_supabase_traces.sh`：簡單 psql 套用。

## 步驟 10：測試

新增 `tests/test_tracer.py`：

```python
import pytest

from app.observability.tracer import GraphTracer
from app.observability.pricing import estimate_cost_usd


def test_span_records_duration():
    t = GraphTracer(thread_id="x", variant="basic")
    with t.span(node="route"):
        pass
    assert any(e["phase"] == "node_exit" and e["node"] == "route" for e in t.events)


def test_llm_call_accumulates_tokens():
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


def test_finalize_returns_payload():
    t = GraphTracer(thread_id="x", variant="basic")
    with t.span(node="route"):
        pass
    payload = t.finalize()
    assert payload["variant"] == "basic"
    assert payload["thread_id"] == "x"
    assert "node_timings" in payload


def test_cost_estimation():
    cost = estimate_cost_usd(
        model="gpt-4.1-mini", input_tokens=1000, output_tokens=500
    )
    assert 0 < cost < 0.01  # ~$0.00045


def test_unknown_model_returns_zero():
    assert estimate_cost_usd(model="unknown-model", input_tokens=1000, output_tokens=500) == 0.0
```

## 請輸出

1. 修改後的 `app/config.py`、`pyproject.toml`
2. `app/observability/__init__.py`、`pricing.py`、`tracer.py`、`logger.py`
3. 修改後的 `app/graph/nodes.py`（用 tracer.span 包 node）
4. 修改後的 `app/ai/providers/*.py`（記 LLM 呼叫 usage）
5. 修改後的 `app/dependencies.py`、`app/line/webhook.py`
6. `scripts/trace.py`
7. `supabase/observability_schema.sql`、`scripts/apply_supabase_traces.sh`
8. `tests/test_tracer.py`
9. README 加「觀測 / cost tracking」段（含 LangSmith opt-in 提示）

## 驗收指令

```bash
pytest tests/test_tracer.py -v
pytest

./scripts/run_local.sh
# 跑幾則訊息後：
ls .traces/
python scripts/trace.py show <thread_id>
python scripts/trace.py summary --last 10
python scripts/trace.py top --by cost --limit 3
```

驗收通過條件：

- 5 個 tracer 測試全綠
- `.traces/{thread_id}.json` 出現含完整 node timing + token usage
- summary CLI 對最近 10 次 invocation 跑出三變體對比表
- LLM 失敗時 cost 不會錯算（不產生 phantom token）
- `OBSERVABILITY_ENABLED=false` 時 `.traces/` 不產生任何檔
- 觀測層 overhead < 50ms / invocation

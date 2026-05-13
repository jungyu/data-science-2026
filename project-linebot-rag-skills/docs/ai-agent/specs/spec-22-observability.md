# Spec-22：Observability + Cost Tracking

> **✅ 已實作；修補 persist 寫入路徑 + 補完介面契約檔（commit `2387555`）**
>
> - `OBSERVABILITY_PERSIST=true` 過去不會真寫 Supabase；現在 `TracerRegistry` 接受
>   `traces_repo` 參數，`async_write_trace` 在本機 JSON 之外同步寫 `graph_traces`
> - 新建 `app/storage/traces_repo.py::TracesRepository`（`insert` / `recent`）
> - 新建 `app/observability/logger.py::configure_observability`（JSON formatter，
>   `python-json-logger` 為 opt-in dep `[observability-json]`）
> - 新建 `scripts/apply_supabase_traces.sh`（套用 opt-in schema）
> - `app/dependencies.py::get_tracer_registry` 在 `persist=True` 時自動注入 traces_repo
> - 驗收測試：`tests/test_tracer.py::test_async_write_trace_persists_when_enabled` +
>   `test_async_write_trace_skips_supabase_when_persist_false` +
>   `test_async_write_trace_warns_when_persist_without_repo`

## 背景

[`docs/RAG/LangGraph/ch10`](../../RAG/LangGraph/ch10-production.md) 的核心痛點：學生實作完三變體後，最常問「**為什麼這個變慢/變貴了？**」沒有觀察工具就只能猜——尤其 reflection variant 的 judge + retry 迴圈，cost 與 latency 的放大效應很難憑感覺判斷。

教學完整性上，這份 spec 的角色是讓 spec-19 的「三變體比較」與 spec-20 的「evaluation」**有共通的觀測底座**：每次 graph 跑完都能 dump 出一份結構化 trace，學生看得到每個 node 花了多少時間、用了多少 token、命中多少 chunk。

不做 LangSmith / LangFuse 整合（屬於商業服務 / self-host 議題）——本 spec 只做**自帶的最小觀測層**，學生想接 LangSmith 把 env var 打開即可（LangGraph 原生支援）。

## 設計

### 三層觀測

| 層級 | 工具 | 出口 |
|---|---|---|
| **結構化 log** | stdlib `logging` + JSON formatter | stdout / Supabase `query_logs` |
| **Trace dump** | 每次 invocation 一份 JSON 檔 | `.traces/{thread_id}.json` |
| **聚合統計** | CLI 從 trace 檔算出 | terminal table |

LangSmith / LangFuse 不在本 spec 的實作範圍，但設計時保留它們的 hook（`LANGCHAIN_TRACING_V2=true` 即可上線）。

### 結構化 log

每個 node 進出都記一筆 JSON log：

```json
{
  "ts": "2026-05-05T10:00:01.234Z",
  "thread_id": "line-U_xxx-evt_001",
  "variant": "reflection",
  "phase": "node_enter",
  "node": "retrieve_one",
  "seed_index": 2
}
```

```json
{
  "ts": "2026-05-05T10:00:01.812Z",
  "thread_id": "line-U_xxx-evt_001",
  "variant": "reflection",
  "phase": "node_exit",
  "node": "retrieve_one",
  "seed_index": 2,
  "duration_ms": 578,
  "metrics": {
    "chunks_retrieved": 5,
    "embedding_tokens": 12
  }
}
```

統一 logger：`app/observability/logger.py::trace_logger`，所有 node 用 `with trace_span(node="x", thread_id=..., **extra)` 包起來。

### Token / Cost 計數

每次 LLM 呼叫後記錄：

```json
{
  "phase": "llm_call",
  "node": "render_narrative",
  "model": "gpt-4.1",
  "provider": "openai",
  "tokens": {"input": 1234, "output": 456, "cached": 200},
  "duration_ms": 2310,
  "estimated_cost_usd": 0.0123
}
```

定價表硬編在 `app/observability/pricing.py`（學生可改）：

```python
PRICING_USD_PER_1M = {
    "gpt-4.1": {"input": 2.50, "output": 10.00},
    "gpt-4.1-mini": {"input": 0.15, "output": 0.60},
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00},
    "claude-haiku-4-5-20251001": {"input": 0.80, "output": 4.00},
    "gemini-2.5-flash": {"input": 0.075, "output": 0.30},
    # ...
}
```

不做即時匯率轉換、不做計費門檻警告——這些是 production 議題。

### Trace Dump

每次 graph invocation 結束後，把所有 log entry 整理成單一 JSON：

```json
{
  "thread_id": "line-U_xxx-evt_001",
  "variant": "reflection",
  "started_at": "...",
  "finished_at": "...",
  "total_duration_ms": 7340,
  "total_tokens": {"input": 4521, "output": 1208},
  "total_cost_usd": 0.0421,
  "node_timings": [
    {"node": "route", "duration_ms": 230},
    {"node": "extract_features", "duration_ms": 580},
    {"node": "retrieve_one[0]", "duration_ms": 410},
    {"node": "retrieve_one[1]", "duration_ms": 445},
    {"node": "retrieve_one[2]", "duration_ms": 502, "ran_in_parallel_with": [0, 1]},
    {"node": "fuse_scores", "duration_ms": 5},
    {"node": "render_narrative", "duration_ms": 2310, "tokens": 1690},
    {"node": "judge", "duration_ms": 890, "tokens": 540},
    {"node": "render_narrative[retry=1]", "duration_ms": 1980, "tokens": 1430}
  ],
  "events": [...]   // 完整原始 log
}
```

寫到 `.traces/{thread_id}.json`，可選：同步寫進 Supabase `graph_traces` table（DDL 在本 spec §schema 段）。

### CLI 聚合

```bash
# 看單次 trace
python scripts/trace.py show line-U_xxx-evt_001

# 看最近 N 次的聚合
python scripts/trace.py summary --last 50
# 輸出：
# variant      | n  | p50_ms | p95_ms | avg_cost
# basic        | 12 |  3100  |  4500  |  $0.003
# selfrag      | 18 |  5050  |  7200  |  $0.012
# reflection   | 20 |  7300  | 12800  |  $0.028 (含平均 0.4 次 retry)

# 找最慢的 N 次
python scripts/trace.py top --by duration --limit 5

# 找最貴的 N 次
python scripts/trace.py top --by cost --limit 5
```

### Supabase Schema（可選）

如果學生想跨 session 累積分析，提供 optional table：

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

**寫入是 opt-in**：env `OBSERVABILITY_PERSIST=true` 才寫 DB（避免測試 / eval 時把 DB 灌爆）。

### 與 spec-20 / spec-21 的整合

- spec-20 evaluation runner 預設**寫 trace 但不寫 DB**（避免污染 production trace）
- spec-21 HITL：interrupt 點寫一筆 `phase: "interrupted"` log；resume 後接續寫 `phase: "resumed"`
- spec-19 demo_compare_variants 直接讀 trace JSON 印對比，不需另寫 timing 邏輯

### 不做什麼

- 不做 metrics endpoint（Prometheus 等）—— production 議題
- 不做即時 dashboard
- 不做警報（cost 超標通知等）
- 不做 distributed tracing（OpenTelemetry）—— 單機教學專案不需要
- 不做 PII redaction（學生需要自己評估，但本 spec 不強制）

## 介面契約

**新增**：`app/observability/__init__.py`、`logger.py`、`tracer.py`、`pricing.py`

```python
# tracer.py
class GraphTracer:
    """收集單次 graph invocation 的所有 event。"""

    def __init__(self, thread_id: str, variant: str) -> None: ...

    @contextmanager
    def span(self, *, node: str, **extra) -> Iterator[Span]: ...

    def record_llm_call(
        self, *, node: str, model: str, provider: str,
        input_tokens: int, output_tokens: int,
        cached_tokens: int = 0, duration_ms: int,
    ) -> None: ...

    def finalize(self) -> dict: ...
```

```python
# logger.py
def get_trace_logger() -> logging.Logger: ...

def configure_observability(settings: Settings) -> None:
    """Setup JSON formatter + log level + LangSmith env vars。"""
```

```python
# pricing.py
def estimate_cost_usd(*, model: str, input_tokens: int, output_tokens: int) -> float: ...
```

**修改**：`app/graph/nodes.py` 每個 node

```python
async def render_narrative_node(state: RAGState, services: RuntimeServices):
    tracer = services.tracer.for_thread(state)
    with tracer.span(node="render_narrative", retry=state.get("reflection_retry", 0)):
        # ...原邏輯
        # LLM 呼叫後：
        tracer.record_llm_call(
            node="render_narrative",
            model=services.settings.generator_model,
            provider=services.settings.ai_provider,
            input_tokens=usage.input,
            output_tokens=usage.output,
            duration_ms=elapsed,
        )
        return {"responses": responses}
```

**修改**：`app/ai/providers/*` 各 provider

每個 provider 的 `complete_text` / `complete_json` 回傳值加 `usage` 欄位（`input_tokens` / `output_tokens` / `cached_tokens`）。OpenAI / Anthropic / Gemini 都原生回傳 usage，只是欄位名不同——provider 內統一成同一個 dataclass。

**新增**：`app/storage/traces_repo.py`（opt-in）

```python
class TracesRepository:
    async def insert(self, trace: dict) -> None: ...
    async def recent(self, *, variant: str | None = None, limit: int = 50) -> list[dict]: ...
```

**新增**：`scripts/trace.py`（CLI 如設計段所述）

**新增 dependency**：

```toml
"python-json-logger>=2.0",
```

LangSmith 不加 dep（學生自選）；提及在 README 加一段「想接 LangSmith 設這幾個 env」即可。

**新增**：`supabase/schema_traces.sql`（opt-in 套用）、`scripts/apply_supabase_traces.sh`

**新增**：`Settings`

```python
observability_enabled: bool = True       # 寫本機 trace 檔
observability_persist: bool = False      # 寫 Supabase graph_traces
trace_dir: str = ".traces"
```

## 驗收標準

- 跑任一 variant 一次，`.traces/{thread_id}.json` 出現，含完整 node timing 與 token usage
- `python scripts/trace.py show <thread_id>` 能 pretty print
- `python scripts/trace.py summary --last 10` 對最近 10 次跑出三變體的對比表
- reflection variant retry 1 次後，trace 中出現兩筆 `render_narrative` 紀錄、第二筆 metadata 標 `retry=1`
- 每筆 LLM 呼叫的 `estimated_cost_usd` 與該 model 的官方定價對得上（誤差 < 5%）
- `OBSERVABILITY_PERSIST=true` 時，Supabase `graph_traces` 表能查到對應記錄
- spec-19 demo_compare_variants 改用 trace dump 出 timing，輸出格式與舊版一致
- spec-20 eval runner 在跑時自動產 trace，CI 中可下載 trace 作 debug 用
- 整體 graph 跑完的 overhead（觀測層 vs 不觀測）增量 < 50ms
- 關掉 observability（`OBSERVABILITY_ENABLED=false`）時，無任何 `.traces/` 檔產生，無 import error

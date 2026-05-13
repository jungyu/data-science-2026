# task-21：Persistence + Human-in-the-Loop

> 規格詳見 [spec-21](../specs/spec-21-persistence-hitl.md)
>
> **✅ 已完成（commit `2387555`）** — 實作記錄與驗收測試見 spec-21 頂部「實作狀態」段。
---

接 LangGraph checkpointer + interrupt_before + review CLI。HITL **只配 reflection variant**（其他兩個 variant 不啟用）。

## 前置

- task-19 完成（三變體已落地）
- 讀過 [`docs/RAG/LangGraph/ch04`](../../RAG/LangGraph/ch04-persistence.md)

## 前置安裝

`pyproject.toml` 加 dependency：

```toml
dependencies = [
  ...
  "langgraph-checkpoint-sqlite>=2.0",
]

[project.optional-dependencies]
postgres = ["langgraph-checkpoint-postgres>=2.0", "psycopg[binary]>=3.2"]
```

```bash
python -m pip install -e ".[dev]"
```

## 步驟 1：Settings

修改 `app/config.py`：

```python
hitl_enabled: bool = False
hitl_always_review_skills: list[str] = []
checkpoint_backend: str = "sqlite"   # sqlite | postgres | memory | none
checkpoint_sqlite_path: str = ".checkpoints/rag.db"
```

## 步驟 2：Checkpointer factory

新增 `app/graph/checkpoint.py`：

```python
from __future__ import annotations

from app.config import Settings


def build_checkpointer(settings: Settings):
    backend = settings.checkpoint_backend
    if backend == "none":
        return None
    if backend == "memory":
        from langgraph.checkpoint.memory import MemorySaver
        return MemorySaver()
    if backend == "sqlite":
        from langgraph.checkpoint.sqlite import SqliteSaver
        from pathlib import Path
        Path(settings.checkpoint_sqlite_path).parent.mkdir(parents=True, exist_ok=True)
        return SqliteSaver.from_conn_string(settings.checkpoint_sqlite_path)
    if backend == "postgres":
        from langgraph.checkpoint.postgres import PostgresSaver
        return PostgresSaver.from_conn_string(settings.supabase_db_url)
    raise ValueError(f"unknown checkpoint backend: {backend}")
```

## 步驟 3：擴充 RAGState 與 nodes

修改 `app/graph/state.py`：

```python
class RAGState(TypedDict, total=False):
    # ...
    reviewer_decision: Literal["approve", "revise", "drop"] | None
    reviewer_revised_text: str | None
    reviewed_at: str | None
    reviewer_id: str | None
```

修改 `app/graph/nodes.py`：

```python
async def human_review_node(state: RAGState, services: Any) -> dict[str, Any]:
    """暫存 contract / narrative / judge 結果。實際 interrupt 由 graph compile 時的
    interrupt_before=["push"] 完成；resume 後本 node 結果不變，push_node 讀
    reviewer_decision 決定推什麼。"""
    return {}


async def push_node(state: RAGState, services: Any) -> dict[str, Any]:
    user_id = state.get("line_user_id", "")
    if user_id.startswith(("U_demo", "U_eval")):
        return {}
    decision = state.get("reviewer_decision")
    if decision == "drop":
        return {}
    if decision == "revise" and state.get("reviewer_revised_text"):
        await services.line_client.push_text(user_id, [state["reviewer_revised_text"]])
        return {}
    # approve 或無 review → push 原 responses
    await services.line_client.push_text(user_id, state["responses"])
    return {}
```

## 步驟 4：reflection variant 加 human_review 路徑

修改 `app/graph/variants/reflection.py`：

```python
def build_reflection_graph(services: Any, *, checkpointer=None):
    g = StateGraph(RAGState)
    # ... 既有 add_node

    g.add_node("human_review", partial(human_review_node, services=services))

    # 把原 force_push → mark_warning 路徑改為 human_review
    g.add_conditional_edges(
        "judge",
        route_after_judge,
        {"pass": "push", "retry": "increment_retry", "human_review": "human_review"},
    )
    g.add_edge("human_review", "push")
    # ...

    interrupt_before = ["push"] if services.settings.hitl_enabled else None
    return g.compile(checkpointer=checkpointer, interrupt_before=interrupt_before)
```

調整 `make_route_after_judge`：retry 用盡時回 `"human_review"` 而非 `"force_push"`。

`mark_warning_node` 仍保留——若 HITL 未啟用但 retry 用盡，graph 走 `mark_warning → push`（向後相容）。實作上：

```python
def make_route_after_judge(max_retries: int, *, hitl_enabled: bool = False):
    HARD_MAX = 2
    effective_max = min(max(max_retries, 0), HARD_MAX)

    def route(state):
        score = state.get("judge_score")
        if score is None or not (state.get("judge_feedback") or []):
            return "pass"
        if state.get("reflection_retry", 0) >= effective_max:
            return "human_review" if hitl_enabled else "force_push"
        return "retry"

    return route
```

reflection.py 加 `force_push → mark_warning → push` 為備援路徑（hitl 未啟用時走的）。

## 步驟 5：thread_id 管理

修改 `app/line/webhook.py`：

```python
config = {"configurable": {"thread_id": f"line-{user_id}-{event.message.id}"}}
final_state = await services.rag_graph.ainvoke(initial_state, config=config)

# 偵測 interrupt：langgraph 1.x 在 interrupt 時 ainvoke 不會拋錯，但 final_state
# 不會包含 push 之後的欄位。可用 graph.get_state(config) 檢查 next 是否為 ("push",)
state_snapshot = services.rag_graph.get_state(config)
if state_snapshot.next and "push" in state_snapshot.next:
    await services.messages_repo.mark_pending_review(thread_id=config["configurable"]["thread_id"])
    return  # 不繼續走 outbound 落庫
```

`messages_repo.mark_pending_review` 是新方法，記一筆 `direction="pending_review"` 訊息或一個獨立 table。

## 步驟 6：Review CLI

新增 `scripts/review_queue.py`：

```python
"""HITL review queue CLI。

用法：
    python scripts/review_queue.py list
    python scripts/review_queue.py show <thread_id>
    python scripts/review_queue.py approve <thread_id>
    python scripts/review_queue.py revise <thread_id> --text "改後內容"
    python scripts/review_queue.py drop <thread_id>
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app.dependencies import get_runtime_services
from langgraph.types import Command


def _cfg(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


async def cmd_list(services):
    rows = await services.messages_repo.list_pending_review()
    for r in rows:
        print(f"{r['thread_id']}\t{r['line_user_id']}\t{r['query'][:50]}")


async def cmd_show(services, thread_id):
    snapshot = services.rag_graph.get_state(_cfg(thread_id))
    state = snapshot.values
    print(f"query:    {state.get('user_input')}")
    print(f"contract: {state.get('answer_contract')}")
    print(f"score:    {state.get('judge_score')}")
    print(f"narrative:")
    for r in state.get("responses") or []:
        print("  " + r.replace("\n", "\n  "))


async def _resume_with(services, thread_id, decision, **extra):
    config = _cfg(thread_id)
    update = {"reviewer_decision": decision, **extra}
    services.rag_graph.update_state(config, update)
    await services.rag_graph.ainvoke(None, config=config)
    await services.messages_repo.clear_pending_review(thread_id=thread_id)


async def cmd_approve(services, thread_id):
    await _resume_with(services, thread_id, "approve")


async def cmd_revise(services, thread_id, text):
    await _resume_with(services, thread_id, "revise", reviewer_revised_text=text)


async def cmd_drop(services, thread_id):
    await _resume_with(services, thread_id, "drop")


async def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    p = sub.add_parser("show"); p.add_argument("thread_id")
    p = sub.add_parser("approve"); p.add_argument("thread_id")
    p = sub.add_parser("revise"); p.add_argument("thread_id"); p.add_argument("--text", required=True)
    p = sub.add_parser("drop"); p.add_argument("thread_id")
    args = parser.parse_args()

    services = get_runtime_services()
    cmd = args.cmd
    if cmd == "list": await cmd_list(services)
    elif cmd == "show": await cmd_show(services, args.thread_id)
    elif cmd == "approve": await cmd_approve(services, args.thread_id)
    elif cmd == "revise": await cmd_revise(services, args.thread_id, args.text)
    elif cmd == "drop": await cmd_drop(services, args.thread_id)


if __name__ == "__main__":
    asyncio.run(main())
```

## 步驟 7：DI

修改 `app/dependencies.py`：

```python
from app.graph.checkpoint import build_checkpointer

@lru_cache(maxsize=1)
def get_runtime_services() -> RuntimeServices:
    settings = get_settings()
    services = RuntimeServices(...)
    checkpointer = build_checkpointer(settings)
    services.checkpointer = checkpointer  # 新欄位
    services.rag_graph = build_rag_graph(services)  # builder 內讀 checkpointer
    return services
```

`build_rag_graph` 與 variant builders 簽章加 `checkpointer` 參數，傳給 `g.compile()`。

## 步驟 8：messages_repo 擴充

修改 `app/storage/messages_repo.py`：

```python
async def mark_pending_review(self, *, thread_id: str): ...
async def list_pending_review(self) -> list[dict]: ...
async def clear_pending_review(self, *, thread_id: str): ...
```

可以用獨立 table `pending_reviews` 或在現有 messages 加 `status` 欄位。教學版用獨立 table 簡單：

```sql
create table if not exists pending_reviews (
  thread_id text primary key,
  line_user_id text not null,
  query text not null,
  created_at timestamptz default now(),
  resolved_at timestamptz
);
```

## 步驟 9：測試

新增 `tests/test_persistence.py`：

```python
import pytest

from app.graph.checkpoint import build_checkpointer


def test_memory_checkpointer():
    from app.config import Settings
    s = Settings(checkpoint_backend="memory")
    cp = build_checkpointer(s)
    assert cp is not None


def test_none_backend_returns_none():
    from app.config import Settings
    s = Settings(checkpoint_backend="none")
    assert build_checkpointer(s) is None
```

新增 `tests/test_hitl_loop.py`（用 MemorySaver + scripted_judge always-fail）：

```python
@pytest.mark.asyncio
async def test_hitl_interrupt_before_push(stub_services_judge_always_fail):
    """HITL 啟用 + judge 永遠 fail → graph 在 push 前 interrupt。"""
    services = stub_services_judge_always_fail
    services.settings.hitl_enabled = True
    # rebuild graph with checkpointer
    from langgraph.checkpoint.memory import MemorySaver
    from app.graph.variants.reflection import build_reflection_graph
    services.rag_graph = build_reflection_graph(services, checkpointer=MemorySaver())

    config = {"configurable": {"thread_id": "test-1"}}
    await services.rag_graph.ainvoke(
        {"user_input": "x", "line_user_id": "U_test", "recent_history": ""},
        config=config,
    )
    # interrupt 後 push 尚未執行
    snapshot = services.rag_graph.get_state(config)
    assert snapshot.next and "push" in snapshot.next
    assert services.line_client.pushed == []


@pytest.mark.asyncio
async def test_hitl_approve_resumes_push(stub_services_judge_always_fail):
    """approve → resume → push 原 responses。"""
    # ... 同上 setup，然後：
    services.rag_graph.update_state(config, {"reviewer_decision": "approve"})
    await services.rag_graph.ainvoke(None, config=config)
    assert len(services.line_client.pushed) == 1


@pytest.mark.asyncio
async def test_hitl_revise_pushes_revised(stub_services_judge_always_fail):
    # ... revise with text → push 用 reviewer_revised_text
    services.rag_graph.update_state(
        config, {"reviewer_decision": "revise", "reviewer_revised_text": "改後 X"}
    )
    await services.rag_graph.ainvoke(None, config=config)
    assert services.line_client.pushed == [("U_test", ["改後 X"])]


@pytest.mark.asyncio
async def test_hitl_drop_skips_push(stub_services_judge_always_fail):
    services.rag_graph.update_state(config, {"reviewer_decision": "drop"})
    await services.rag_graph.ainvoke(None, config=config)
    assert services.line_client.pushed == []


@pytest.mark.asyncio
async def test_basic_variant_unaffected_by_hitl(stub_services):
    """basic / selfrag 不受 hitl_enabled 影響。"""
    stub_services.settings.hitl_enabled = True
    from app.graph.variants.basic import build_basic_graph
    g = build_basic_graph(stub_services)
    final = await g.ainvoke({"user_input": "x", "line_user_id": "U_test", "recent_history": ""})
    assert stub_services.line_client.pushed != []
```

## 步驟 10：教學配套

新增 `docs/ai-agent/examples/hitl-walkthrough.md`：完整走一個 case：低分 → CLI 列出 → revise → resume → push。每步驟附 expected log。

## 請輸出

1. 修改後的 `app/config.py`
2. `app/graph/checkpoint.py`
3. 修改後的 `app/graph/state.py`、`nodes.py`、`variants/reflection.py`
4. 修改後的 `app/dependencies.py`、`app/line/webhook.py`
5. 修改後的 `app/storage/messages_repo.py` + DDL `supabase/pending_reviews.sql`
6. `scripts/review_queue.py`
7. `tests/test_persistence.py`、`tests/test_hitl_loop.py`
8. `docs/ai-agent/examples/hitl-walkthrough.md`
9. README 加「啟用 HITL」段、`pyproject.toml` 加 dep

## 驗收指令

```bash
pytest tests/test_persistence.py tests/test_hitl_loop.py -v
pytest

# 端對端
HITL_ENABLED=true CHECKPOINT_BACKEND=sqlite ./scripts/run_local.sh
# 1. LINE 傳一個會觸發低分的問題 → bot 不回（interrupt）
# 2. python scripts/review_queue.py list → 看到 pending
# 3. python scripts/review_queue.py revise <id> --text "改後內容" → LINE 收到改後內容

# basic / selfrag 不受影響
GRAPH_VARIANT=basic HITL_ENABLED=true ./scripts/run_local.sh
# LINE 仍正常收到回覆
```

驗收通過條件：

- 5 個 HITL 測試全綠（pass-through / approve / revise / drop / basic 不受影響）
- `.checkpoints/rag.db` 在 sqlite 模式下出現
- review CLI 三動作（approve / revise / drop）都能正確 resume
- retry 上限到達不再無限迴圈（HITL 啟用 → human_review；HITL 未啟用 → mark_warning + push）

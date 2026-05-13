# Spec-21：Persistence + Human-in-the-Loop

> **✅ 已實作；修補 production 入口 thread_id 缺失（commit `2387555`）**
>
> - webhook / chat / stream 三條 production 入口都改為帶
>   `config={"configurable": {"thread_id": ...}}` 呼叫 `graph.ainvoke`
>   — 過去未帶 config，checkpointer + interrupt 在 production 形同沒接
> - webhook 新增 `_is_interrupted` helper + 偵測中斷後改呼叫 `mark_pending_review`，不送 outbound
> - `app/storage/messages_repo.py` 加 `mark_pending_review` / `list_pending_reviews` / `resolve_pending_review`
> - `supabase/schema.sql` 加 `hitl_pending_reviews` opt-in 表（schema 未套用時靜默退化）
> - `app/graph/checkpoint.py` 加 `build_postgres_saver_async`（回 `(saver, cm)` tuple，
>   lifespan 在 shutdown 需 `await cm.__aexit__`，避免連線洩漏）；
>   `config.py` 加 `supabase_db_url`
> - `pyproject.toml` 加 `hitl-postgres` extra（`langgraph-checkpoint-postgres` + `psycopg[binary]`）
> - `scripts/review_queue.py` 在 resume 後同步呼叫 `resolve_pending_review`，
>   並新增 `list-db` 子命令從 Supabase 視圖列待審——讓 `hitl_pending_reviews` 表
>   不只是 webhook 寫入沒人讀的 dead code
> - 驗收測試：`tests/test_line_webhook.py::test_line_webhook_passes_thread_id_config_to_graph`
>
> **⚠️ Thread granularity 設計選擇**：`build_thread_id(inp)` 用
> `line-{user_id}-{message_id}` 是**單訊息粒度**，每則訊息一條獨立 thread；
> checkpointer 不會跨訊息保留 state，多輪對話的歷史靠 `recent_history`（從
> `line_messages` 表組）。若需要「user 級別的多輪 thread」（讓 LangGraph 在
> 訊息間持續累積 state），請改 `app/channels/line.py::build_thread_id` 為
> `f"line-{user_id}"` —— 但要同步注意 reflection retry 計數需手動重置。

## 背景

[`docs/RAG/LangGraph/ch04`](../../RAG/LangGraph/ch04-persistence.md) **整章**在講 checkpoint / interrupt / resume——目前所有 spec 一字未提。`ch06 §3` 明確指出：**高風險領域 Reflection Agent 必須有 human_review 路徑**。學生讀完 ch04 / ch06 來看 spec/task，會找不到對應實作。

更實務的問題：spec-17 的 reflection 迴圈在 retry 達上限後選擇「強制 push 加品質警告」——對教學 demo 沒問題，但對任何認真的生產情境都不夠。Human-in-the-loop 是 LangGraph 相對其他 framework 的核心優勢，**不示範等於沒教 LangGraph**。

借鑑：
- LangGraph 官方 `SqliteSaver` / `PostgresSaver` checkpointer
- [`docs/RAG/LangGraph/ch04`](../../RAG/LangGraph/ch04-persistence.md) 的設計哲學
- [`ch09-langgraph-in-action.md`](../../RAG/LangGraph/ch09-langgraph-in-action.md) 已示範 checkpointer 接法
- ch06 §3 的「[Rewrite/Retrieve] / [Human] / [Citation Builder]」三向設計

## 設計

### 兩個獨立但相關的能力

| 能力 | 教學要點 | 何時用 |
|---|---|---|
| **Persistence**（checkpoint）| 每個 node 完成後自動 snapshot；可 resume 重跑 | 任何長流程、任何要 debug 的場景 |
| **Human-in-the-Loop**（HITL）| 在指定 node 前 `interrupt`；外部審核後 `resume` | reflection retry 用盡、敏感領域 |

兩者技術上獨立（HITL 不一定需要 persistence，但有 persistence HITL 才實用），教學上一起講最自然——**checkpoint 是 HITL 的前提**。

### Persistence 設計

**Checkpointer 選擇**：

| 環境 | Checkpointer | 理由 |
|---|---|---|
| 教學 / 本機 | `SqliteSaver` | 零依賴、可看檔案 |
| 生產 / Supabase | `PostgresSaver`（langgraph-checkpoint-postgres）| 與既有 Supabase 共用 connection |

兩者切換由 env var：

```bash
CHECKPOINT_BACKEND=sqlite  # sqlite | postgres
CHECKPOINT_SQLITE_PATH=.checkpoints/rag.db
```

**整合到 builder**：

```python
def build_reflection_graph(services: RuntimeServices, *, checkpointer=None):
    g = StateGraph(RAGState)
    # ... add_node / add_edge
    return g.compile(
        checkpointer=checkpointer,
        interrupt_before=["push"] if services.settings.hitl_enabled else None,
    )
```

每個 invocation 帶 `thread_id`：

```python
config = {"configurable": {"thread_id": f"line-{line_user_id}-{event_id}"}}
await graph.ainvoke(initial_state, config=config)
```

### HITL 設計

**觸發條件**（在 reflection variant 內）：

| 條件 | 動作 |
|---|---|
| Judge retry 用盡仍 fail | interrupt before push（不直接強推 + 警告）|
| `Settings.hitl_always_review_skills` 列入的 skill | interrupt before push（無條件）|
| 其它 | 直接 push（不 interrupt）|

調整 spec-17 的 `route_after_judge`：

```python
def route_after_judge(state: RAGState) -> str:
    score = state.get("judge_score")
    if score is None or not state.get("judge_feedback"):
        return "pass"
    if state.get("reflection_retry", 0) >= 1:
        return "human_review"   # 取代原 force_push
    return "retry"
```

新增 `human_review` 路徑：

```
judge → human_review → [interrupt before push] → push
                                ↑
                       外部 resume(state with reviewer_decision)
```

### Human Review Queue（簡化教學版）

不引入完整 dashboard，提供 CLI：

```bash
# 列出待審項目
python scripts/review_queue.py list
# 輸出：thread_id | line_user_id | query | judge_mean | created_at

# 看詳細
python scripts/review_queue.py show <thread_id>
# 輸出：query / contract / narrative / judge feedback

# 批准（直接 push 原 narrative）
python scripts/review_queue.py approve <thread_id>

# 改寫後 push
python scripts/review_queue.py revise <thread_id> --text "改後內容"

# 撤回（不送任何訊息）
python scripts/review_queue.py drop <thread_id>
```

CLI 內部呼叫 `graph.ainvoke(None, config=..., resume=Command(...))`。

### State 新增欄位

```python
class RAGState(TypedDict, total=False):
    # ...
    reviewer_decision: Literal["approve", "revise", "drop"] | None
    reviewer_revised_text: str | None
    reviewed_at: str | None
    reviewer_id: str | None
```

push_node 在 resume 後讀 `reviewer_decision`：

- `approve` → push 原 `responses`
- `revise` → push `reviewer_revised_text`
- `drop` → 不 push，記 log

### 不做什麼

- 不做 web dashboard（屬產品功能；teaching 階段 CLI 夠用）
- 不做 reviewer 認證 / 多人審核流程
- 不做 SLA / 逾期自動處理（屬 production 議題）
- 不對 basic / selfrag variant 啟用 HITL（這兩個變體理論上沒有「該找人看」的場景；HITL 只配 reflection）

## 介面契約

**新增 dependency**：

```toml
"langgraph-checkpoint-sqlite>=2.0",
# 生產用
"langgraph-checkpoint-postgres>=2.0",
"psycopg[binary]>=3.2",
```

**新增**：`app/graph/checkpoint.py`

```python
from typing import Literal

CheckpointBackend = Literal["sqlite", "postgres", "memory", "none"]


def build_checkpointer(settings: Settings):
    """Returns langgraph checkpointer or None。"""
    backend = settings.checkpoint_backend
    if backend == "none":
        return None
    if backend == "memory":
        from langgraph.checkpoint.memory import MemorySaver
        return MemorySaver()
    if backend == "sqlite":
        from langgraph.checkpoint.sqlite import SqliteSaver
        return SqliteSaver.from_conn_string(settings.checkpoint_sqlite_path)
    if backend == "postgres":
        from langgraph.checkpoint.postgres import PostgresSaver
        return PostgresSaver.from_conn_string(settings.supabase_db_url)
    raise ValueError(f"unknown backend: {backend}")
```

**修改**：`app/graph/variants/reflection.py`

```python
def build_reflection_graph(services: RuntimeServices, *, checkpointer=None):
    g = StateGraph(RAGState)
    # ... 現有 nodes / edges
    g.add_node("human_review", partial(human_review_node, services=services))
    # 把 force_push 路徑改為 human_review
    g.add_conditional_edges("judge", route_after_judge, {
        "pass": "push",
        "retry": "increment_retry",
        "human_review": "human_review",
    })
    g.add_edge("human_review", "push")  # interrupt 在 push 前

    return g.compile(
        checkpointer=checkpointer,
        interrupt_before=["push"] if services.settings.hitl_enabled else None,
    )
```

**修改**：`app/dependencies.py`

```python
@lru_cache(maxsize=1)
def get_runtime_services() -> RuntimeServices:
    settings = get_settings()
    services = RuntimeServices(...)
    checkpointer = build_checkpointer(settings)
    builder = VARIANT_BUILDERS[settings.graph_variant]
    object.__setattr__(services, "rag_graph", builder(services, checkpointer=checkpointer))
    object.__setattr__(services, "checkpointer", checkpointer)
    return services
```

`basic` / `selfrag` builder 接受 `checkpointer=None` 但不使用 `interrupt_before`（HITL 只配 reflection）。

**修改**：`app/line/webhook.py`

```python
config = {"configurable": {"thread_id": f"line-{user_id}-{event.message.id}"}}
final = await services.rag_graph.ainvoke(initial_state, config=config)

# 若 final 是 None / 偵測到 interrupt，僅落庫 inbound + 標記 pending review，不 push outbound
if _is_interrupted(final):
    await services.messages_repo.mark_pending_review(thread_id=config["configurable"]["thread_id"])
    return
```

**新增**：`scripts/review_queue.py`（CLI 如上）

**新增**：`Settings`

```python
hitl_enabled: bool = False  # 預設 off，學生主動開
hitl_always_review_skills: list[str] = []
checkpoint_backend: CheckpointBackend = "sqlite"
checkpoint_sqlite_path: str = ".checkpoints/rag.db"
```

**新增**：`docs/ai-agent/examples/hitl-walkthrough.md`——完整走一個 case：低分觸發 → CLI 列出 → 人工 revise → resume → push。

## 驗收標準

- `CHECKPOINT_BACKEND=sqlite` 跑 reflection variant，`.checkpoints/rag.db` 出現且每個 node 都有 snapshot
- `HITL_ENABLED=true` + 觸發低分 case → graph 在 push 前 interrupt，**LINE 不收到任何訊息**
- `python scripts/review_queue.py list` 能看到 pending thread_id
- `review_queue.py approve` 後，LINE 收到原始 narrative
- `review_queue.py revise --text "..."` 後，LINE 收到改後文字
- `review_queue.py drop` 後，LINE 不收到任何訊息，DB 標記 dropped
- `basic` / `selfrag` variant 不受 HITL 影響（即使 `HITL_ENABLED=true` 也照常 push）
- Resume 後 graph state 完整（contract / chunks 都還在），不需重跑 retrieval
- `tests/test_persistence.py`：mock checkpointer 驗證 invoke 兩次後 thread_id 同一個能 resume；`tests/test_hitl_loop.py`：模擬 approve / revise / drop 三條路徑

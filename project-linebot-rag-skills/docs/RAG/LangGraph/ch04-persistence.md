# 第 4 章：Persistence — Agent 的存檔機制

> 「沒有 persistence 的 agent，像沒存檔的 RPG。」

## 開場故事

你的 agent 跑到一半：

- 已經做了 5 次檢索
- 呼叫了 3 個外部 API
- 等使用者按「同意」
- ⚡ 突然斷線

如果沒有 persistence，這整條工作 GG，從頭再來。每次重跑都要花錢、花時間，使用者也會抓狂。

## Checkpointer 是什麼？

把它想成 **流程的自動存檔器**。每跑完一個節點，自動快照：

- 現在停在哪個 node
- 那一刻的 state 長怎樣
- 這一步輸出了什麼

```
[START] → [Rewrite] → 💾 → [Retrieve] → 💾 → [Generate] → 💾 → [Reflect] → 💾
```

而整條軌跡會綁到一個 **Thread ID**——把它想成「**存檔檔名**」。同一個 thread_id 就是同一份遊戲進度，可以反覆讀檔、續玩；不同 thread_id 之間完全隔離。

## 你能做哪些事？

| 能力 | 用途 | 對應 API |
|------|------|---------|
| **Resume** | 從 checkpoint 繼續 | `graph.invoke(None, config)` |
| **Interrupt Resume** | 回應 `interrupt()` 並繼續 | `graph.invoke(Command(resume=...), config)` |
| **Inspect** | 查看任一時刻的 state | `graph.get_state(config)` |
| **Replay** | 列出整條軌跡每一步的 state | `graph.get_state_history(config)` |
| **Fork** | 從某個 checkpoint 改 state 後分叉 | `graph.update_state(...)` + 從該 checkpoint 繼續 |

### 為什麼 Resume 只要傳 `None`？

`graph.invoke(None, config=config)` 看起來很魔法。其實邏輯很簡單：

- `config` 裡帶了 `thread_id` → LangGraph 知道要去哪份存檔找最後的 state
- 第一個參數傳 `None` → 告訴它「**不要給我新 input，從 checkpoint 接著跑**」
- 如果傳 dict → 那是新的 input，會疊到既有 state 上

> ⚠️ 沒設 `thread_id` 就沒辦法 resume——因為它不知道你要接哪份存檔。

這裡講的是「一般 checkpoint resume」。如果流程是停在 `interrupt()`，就不能只傳 `None`，而是要用 `Command(resume=...)` 把人類或外部系統的回覆送回那個 interrupt 點；下面的 HITL 段會示範。

### Time-Travel：把 state 倒帶到任何一步

ch01 預告過的 🎮 **Time-Travel** 就是 Replay + Fork 組合技。每個 checkpoint 都有 `checkpoint_id`，可以拿它把流程倒帶：

```python
# 1. 列出這個 thread 跑過的所有快照（最新的在前）
history = list(graph.get_state_history(config))
# [現在, Reflect 後, Generate 後, Retrieve 後, Rewrite 後, ...]

# 2. 挑你想倒帶到的那一刻（例如 Retrieve 之後）
target = history[3]

# 3. 在那個快照上手動改 state——例如修掉爛的檢索結果
graph.update_state(
    target.config,
    {"retrieval": {"docs": [...人類修正過的文件...]}}
)

# 4. 從那一點繼續跑。原本的歷史不會被覆蓋，這是「新分支」
result = graph.invoke(None, config=target.config)
```

> 🎮 **就像存檔點玩 RPG**：你可以從第 5 章打到一半的存檔分叉出去試另一條路，原本那條存檔還在。

**為什麼這在 RAG 開發很重要？**
複雜 reflection agent 跑 30 秒就燒掉一塊錢。沒 time-travel 時改完 prompt 只能從頭重跑；有了它你可以鎖定「Reflect 那一步決策爛」，回到該點手動修 reflection 結果、只重跑後半段。除錯效率天差地遠。

## 對話：persistence vs memory

> **新手**：我已經有 conversation memory 了，這不就是 persistence？
>
> **老手**：不一樣。Memory 只記**對話內容**。Persistence 記的是**整個流程的執行狀態**——包含 attempt_count、route_history、retrieval_history、reflection 結果。
>
> **新手**：差別有那麼大嗎？
>
> **老手**：差在「能不能還原」。Memory 還原不了「我上次跑到第 4 個 node 的第 2 次重試」。

## Interrupt：暫停等人類

LangGraph 給了**兩種**暫停方式，學生常會搞混：

### 方式 1：靜態暫停 `interrupt_before` / `interrupt_after`

最簡單。**編譯圖時就宣告**「跑到這個節點之前/之後一定暫停」：

```python
graph = builder.compile(
    checkpointer=checkpointer,
    interrupt_before=["delete_database_node"],
)
```

適合「**這個節點永遠都要人類審核**」的場景——刪資料、扣款、發信、執行不可逆 SQL。

### 方式 2：動態暫停 `interrupt()`

寫在節點函式裡，**執行時才決定**要不要暫停：

```python
def human_review(state):
    review = interrupt({
        "draft_answer": state["draft_answer"],
        "reflection": state["reflection"],
    })
    return {
        "reflection": {
            **state["reflection"],
            "decision": review.get("decision", "finalize"),
        }
    }
```

適合「**有條件才暫停**」——金額超過 10 萬才人工核可、信心分數低於 0.6 才丟給人、AI 自己覺得不確定才求救。

### 暫停期間到底發生什麼？

這是最多人誤解的地方。**不是 process 卡在那邊空等**，而是：

1. State 序列化進資料庫
2. **計算資源完全釋放**（Python process 可以去服務別人，伺服器不會被佔著）
3. 等外部呼叫恢復——可以是隔 10 秒、隔 3 小時、甚至隔天

### 人類不只是按「同意」，可以直接改 state

這是 LangGraph HITL 真正的殺手鐧。等待期間，後台介面可以**任意修改 state 內容**：

```python
# 例：人類覺得 AI 找的檢索結果很爛，幫它換掉
graph.update_state(
    config,
    {"retrieval": {"docs": [...人類找的好文件...]}}
)
```

然後用 `Command(resume=...)` 把人類的決策塞回 `interrupt()` 的回傳值，繼續跑：

```python
from langgraph.types import Command

result = graph.invoke(
    Command(resume={"decision": "finalize"}),
    config=config,
)
# interrupt() 那行會收到 {"decision": "finalize"} 當回傳值
```

> 💡 **比較**：傳統 chain 要實現「暫停 + 改 state + 恢復」，工程師要自己寫外部 DB 鎖、webhook、等待狀態機。LangGraph 把這整套包進框架——這就是 ch01 講的「**第一公民級的 HITL**」。

> ⚠️ **沒有 checkpointer 就沒有 interrupt。** 兩者綁在一起——因為「暫停」的本質就是「存檔等人」。

## 應用場景

不是只有「斷線重連」才需要 persistence：

- **長流程研究 agent**：跑 30 分鐘、跨多次 LLM call
- **人工審核**：合約條款、診斷建議、查詢方向
- **多輪對話任務**：使用者隔天回來繼續
- **昂貴工具調用**：不想重跑 GPT-4 + Web Search
- **不穩定環境**：行動裝置、邊緣節點

## 一張圖：含持久化的架構

```
[START]
  ↓
[Init State]
  ↓
[Rewrite Query] → 💾
  ↓
[Retrieve] → 💾
  ↓
[Generate Draft] → 💾
  ↓
[Reflect] → 💾
  │
  ├─ rewrite_query ────→ [Rewrite Query]
  ├─ retrieve_again ───→ [Retrieve]
  ├─ human_review ─ ─ ┐
  │                   ↓
  │              [[Interrupt]]
  │                   ↓ resume
  │              [Reflect 重評]
  │
  └─ finalize ────────→ [Finalize] → 💾 → [END]
```

## 簡單上手

```python
from langgraph.checkpoint.sqlite import SqliteSaver

checkpointer = SqliteSaver.from_conn_string("checkpoints.db")

graph = builder.compile(checkpointer=checkpointer)

# 跑流程，綁 thread_id
config = {"configurable": {"thread_id": "user-123-session-1"}}
result = graph.invoke({"user_query": "..."}, config=config)

# 中斷後恢復
result = graph.invoke(None, config=config)  # 從上次 checkpoint 接續
```

## ⚠️ Production 注意

1. **不要用 in-memory checkpointer 上 production**：重啟就沒了
2. **生產用 PostgreSQL / Redis backend**：容錯 + 多 instance 共享
3. **Thread ID 設計要想清楚**：通常 = `user_id + session_id`
4. **Checkpoint 會佔空間**：要設過期策略

## 🔧 真實實作對照：[`app/graph/checkpoint.py`](../../../app/graph/checkpoint.py)

本書範例專案把 checkpoint backend 選擇做成 factory，三種 backend 一字排開——`memory`（教學）、`sqlite`（單機生產）、`postgres`（多 instance 生產）。學生可以直接看真實 production 怎麼處理：

```python
# app/graph/checkpoint.py:21-46（節錄）
def build_checkpointer(settings: Settings) -> Any | None:
    backend = settings.checkpoint_backend
    if backend in ("none", ""):
        return None
    if backend == "memory":
        from langgraph.checkpoint.memory import InMemorySaver
        return InMemorySaver()
    if backend == "sqlite":
        # async setup needed → 走 build_sqlite_saver_async() 在 startup hook 內
        return None
    if backend == "postgres":
        # 與既有 Supabase 共用 connection（spec-21）
        return None
    raise ValueError(f"unknown checkpoint_backend: {backend!r}")
```

幾個生產系統才會踩到的細節：

- **`memory` 是同步建構，能直接用**；`sqlite` / `postgres` 都需要 `await saver.setup()`，所以同步函式回 `None`，真正的建構移到 FastAPI lifespan hook 裡（見同檔 `build_sqlite_saver_async` / `build_postgres_saver_async`）
- **PostgresSaver 的 cleanup 不能省**：`await cm.__aexit__(None, None, None)` 必須在 shutdown 跑，否則 connection 洩漏。這是「checkpoint backend 不只是 import 一個 class」的現實
- **`backend = "none"` 是合法選項**——關掉 persistence + HITL，純跑無狀態 RAG 用

### HITL 不能沒有 checkpointer：真實守門 code

ch01 強調「沒 checkpointer 就沒 interrupt」，這在範例專案是一段會直接 fail-fast 的程式碼：

```python
# app/graph/variants/reflection.py:111-118
if hitl_enabled:
    if checkpointer is None:
        raise RuntimeError(
            "hitl_enabled=True 但 services.checkpointer 為 None。"
            " HITL 需要 checkpointer 才能 interrupt + resume；"
            " 設 CHECKPOINT_BACKEND=memory（教學）或 sqlite（生產）。"
        )
    compile_kwargs["interrupt_before"] = ["human_review"]
```

啟動時就崩，比 runtime 跑到一半才發現「interrupt 沒生效」省事一萬倍。**生產系統設計準則：能在 boot 抓的錯不要留到 request time**。

### 靜態 interrupt 的真實寫法

注意上面 line 118：`interrupt_before=["human_review"]`。這就是本章「方式 1：靜態暫停」的真實用法——`human_review` 節點被自動暫停，不需要在節點函式內呼叫 `interrupt()`：

```python
# app/graph/nodes.py:367-377
async def human_review_node(state: RAGState, services: Any) -> dict[str, Any]:
    """HITL 中繼 node。實際 interrupt 由 graph compile 時的 interrupt_before 完成。
    Resume 後本 node 不做事；push_node 會讀 reviewer_decision 決定推什麼。"""
    logger.info(
        "human_review entered: thread=%s reviewer_decision=%s",
        state.get("external_message_id"),
        state.get("reviewer_decision"),
    )
    return {}
```

節點本身近乎空殼——所有暫停 / 恢復語意都在 compile 時宣告。

> 💡 **Brain Power**
> 如果同一個使用者在兩個分頁同時跑 agent，thread_id 該怎麼設計？

<details>
<summary>解答</summary>

不能只用 `user_id`。要加上 session 或 tab 的識別，例如 `user_id + browser_tab_uuid`。否則兩個分頁會互相覆蓋對方的 state。
</details>

## 一句話收斂

> Persistence 把長流程從「賭運氣」變成「可工程化」。

---

**下一章**：[Agent Loop：思考、行動、觀察、重複](ch05-agent-loop.md)

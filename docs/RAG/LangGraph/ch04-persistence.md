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

把它想成 **流程的自動存檔器**。

每走完一個節點，就記下：
- 現在在哪個 node
- State 長怎樣
- 這一步輸出是什麼
- Thread ID 是什麼

```
[START] → [Rewrite] → 💾 → [Retrieve] → 💾 → [Generate] → 💾 → [Reflect] → 💾
```

## 你能做哪些事？

| 能力 | 用途 |
|------|------|
| **Resume** | 從中斷點繼續 |
| **Inspect** | 查看當時 state |
| **Replay** | 重播後續步驟（debug 神器）|
| **Fork** | 從某個 checkpoint 分叉試另一條路 |

## 對話：persistence vs memory

> **新手**：我已經有 conversation memory 了，這不就是 persistence？
>
> **老手**：不一樣。Memory 只記**對話內容**。Persistence 記的是**整個流程的執行狀態**——包含 attempt_count、route_history、retrieval_history、reflection 結果。
>
> **新手**：差別有那麼大嗎？
>
> **老手**：差在「能不能還原」。Memory 還原不了「我上次跑到第 4 個 node 的第 2 次重試」。

## Interrupt：暫停等人類

LangGraph 有個超實用的 feature：**Interrupts**。

```python
def human_review(state):
    review = interrupt({
        "draft_answer": state["draft_answer"],
        "reflection": state["reflection"]
    })
    return {
        "reflection": {
            **state["reflection"],
            "decision": review.get("decision", "finalize")
        }
    }
```

當 `interrupt()` 觸發：
1. 系統把當前 state **存到 checkpoint**
2. 流程**暫停**
3. 等外部呼叫 `resume()`
4. 從中斷處繼續

> ⚠️ **沒有 checkpointer 就沒有 interrupt。** 兩者綁在一起。

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

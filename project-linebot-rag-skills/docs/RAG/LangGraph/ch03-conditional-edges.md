# 第 3 章：Conditional Edges — 路口的號誌系統

> 「如果流程只能直走，那它就不是 Agent，是 pipeline。」

## 高速公路交流道的比喻

想像你在高速公路。
直線 chain 是這樣：每台車只能一直直走。

```
入口 → A → B → C → 出口
```

但真實世界的 Agent 像交流道：

```
                ┌─→ 重新檢索
入口 → 反思 ────┼─→ 改寫查詢
                ├─→ 人工審核
                └─→ 結束
```

決定走哪條路的，就是 **Conditional Edge**。

## 它到底在做什麼？

一個普通 edge：

```python
builder.add_edge("retrieve", "generate")  # 永遠 retrieve → generate
```

一個 conditional edge：

```python
builder.add_conditional_edges(
    "reflect",
    route_after_reflect,   # ← 這個函式決定去哪
    {
        "rewrite_query": "rewrite",
        "retrieve_again": "retrieve",
        "human_review": "human_review",
        "finalize": "finalize",
    }
)
```

> ⚠️ **Edge 不只是連線，是決策邏輯的出口。**

## `add_conditional_edges` 解剖

很多人第一次看到上面那段會卡住：「那三個參數到底各自負責什麼？」

```python
builder.add_conditional_edges(
    "reflect",                # ① 從哪個 node 出發
    route_after_reflect,      # ② 決策函式
    {                         # ③ 決策結果 → 目標 node 的對照表
        "rewrite_query": "rewrite",
        "retrieve_again": "retrieve",
        "human_review": "human_review",
        "finalize": "finalize",
    }
)
```

關鍵在第 ② 個參數，**routing function** 有固定簽名：

```python
def route_after_reflect(state: AgentState) -> str:
    # 讀 state → 回傳一個字串
    return "rewrite_query"
```

- **輸入**：當前 state（跟 node 一樣）
- **輸出**：一個字串（這個字串會去查第 ③ 個 dict 找對應的 node）

第 ③ 個 dict 其實是「翻譯表」：把語意化的決策名稱（`"rewrite_query"`）翻譯成 graph 裡真實的 node 名稱（`"rewrite"`）。這層翻譯讓你的決策名稱不需要跟 node 名稱綁死，refactor 時很有用。

> 💡 **小技巧**
> 如果你的決策名稱就是 node 名稱，可以省略第 ③ 個 dict，LangGraph 會直接拿回傳值當 node 名（後面「記 history」那段會用到這種寫法）。

## 對話：為什麼不直接叫模型決定？

> **新手**：我直接在 prompt 裡寫「請決定下一步要做什麼」不就好了？
>
> **老手**：然後模型有時回 `"rewrite"`，有時回 `"我覺得可以再改寫一下"`，有時回 `"Let's try retrieval again"`。你的 router 怎麼接？
>
> **新手**：我加 regex parse？
>
> **老手**：那如果模型今天回 `"rewrite_query"`，明天回 `"REWRITE"`？
>
> **新手**：……
>
> **老手**：所以**模型只負責產生結構化判斷，graph 才負責決策**。控制權要從「模型自由發揮」轉成「系統顯式治理」。

什麼叫「結構化判斷」？對比一下就懂：

| 非結構化判斷 | 結構化判斷 |
|--------------|------------|
| `"我覺得這份資料還可以再找找"` | `{"decision": "retrieve_again"}` |
| `"建議重寫查詢喔"` | `{"decision": "rewrite_query"}` |
| 自由文字、語意飄移 | 預定義欄位、值域封閉 |

結構化判斷的好處：router 拿到 `state["reflection"]["decision"]`，比對一個固定 enum 就能分支，**完全不需要再解析自然語言**。

## 正確的拆法

### Step 1：Reflect node 只更新 state

```python
def reflect(state):
    return {
        "reflection": {
            "grounded": False,
            "sufficient": False,
            "decision": "rewrite_query"   # ← 封閉集合
        }
    }
```

### Step 2：Routing function 才決定去哪

```python
def route_after_reflect(state):
    if state["attempt_count"] >= state["max_attempts"]:
        return "finalize"   # 硬性煞車

    decision = state["reflection"]["decision"]
    if decision == "rewrite_query":
        return "rewrite_query"
    elif decision == "retrieve_again":
        return "retrieve"
    elif decision == "human_review":
        return "human_review"
    else:
        return "finalize"
```

> 💡 **Brain Power**
> 為什麼要把 `attempt_count >= max_attempts` 放在 routing function，而不是放在 reflect node？
>
> （這是個生產系統會踩的坑。）

<details>
<summary>解答</summary>

因為 reflect node 的職責是「評估答案品質」，而 attempt 上限是「流程治理」。把流程治理放進 reflect node 會讓它越長越大，責任不清。**判斷與決策分離**是長期可維護的關鍵。
</details>

## 設計原則：decision 必須是封閉集合

「封閉集合」指的是：**所有可能的取值都已經被預先列舉完畢，不會臨時冒出新的**。在工程上，它對應的就是 enum、`Literal` 型別、或一個固定的字串集合。

❌ 錯（開放集合，自由文字）：

```python
"decision": "我覺得可以再找看看"
"decision": "try_again"
"decision": "maybe rewrite"
```

✅ 對（封閉集合，用 `Literal` 鎖死）：

```python
from typing import Literal

Decision = Literal["rewrite_query", "retrieve_again", "finalize", "human_review"]

class Reflection(TypedDict):
    grounded: bool
    sufficient: bool
    decision: Decision   # ← 型別檢查器會在編譯期擋掉非法值
```

`typing.Literal` 不會在 runtime 強制檢查，但它做了兩件重要的事：

1. **靜態檢查**：mypy / pyright / IDE 會在你寫 `decision = "REWRITE"` 時直接標紅
2. **文件化**：未來看這段程式碼的人立刻知道「這個欄位只有這四種值」

> 🔗 **呼應 [ch02](ch02-stategraph.md) 的 FSM 思想**
> 還記得狀態機的第一條規則嗎？「**所有狀態必須有限可列舉**」。封閉集合就是這條規則延伸到「決策值」上的具體實踐——決策也必須有限、必須可列舉、必須不能臨時長出新分支。

封閉集合 = router 永遠知道怎麼接。

## 條件路由的真正價值

| 沒有條件路由 | 有條件路由 |
|--------------|------------|
| 失敗就整條重跑 | 失敗變成可處理的分支 |
| 模型亂回控制不住 | 系統用結構強制 |
| 不能 audit 為什麼走那條路 | 每次 routing 可記錄 |
| 一次性 RAG | 真正的 Agent |

## 進階：路由也可以記 history

把每次路由決策都存進 state，之後審計、debug、優化 prompt 都用得上。

完整作法分三步：

**Step 1：State 加一個 `route_history` 欄位**

```python
from datetime import datetime, timezone
from typing import TypedDict, List

class RouteRecord(TypedDict):
    from_node: str
    to_node: str
    reason: str
    at: str   # ISO timestamp

class AgentState(TypedDict):
    # ... 其他欄位
    route_history: List[RouteRecord]
```

**Step 2：reflect node 寫入 decision 時，順手 append 一筆紀錄**

```python
def reflect(state):
    decision = "rewrite_query"   # 假設 LLM 判斷結果
    reason = "retrieved docs lack pricing info"

    new_record: RouteRecord = {
        "from_node": "reflect",
        "to_node": decision,
        "reason": reason,
        "at": datetime.now(timezone.utc).isoformat(),
    }

    return {
        "reflection": {"grounded": False, "sufficient": False, "decision": decision},
        "route_history": state["route_history"] + [new_record],   # ← 累積
    }
```

**Step 3：routing function 維持純讀取**

```python
def route_after_reflect(state) -> str:
    if state["attempt_count"] >= state["max_attempts"]:
        return "finalize"
    return state["reflection"]["decision"]   # 直接回字串當 node 名
```

> 注意 Step 3 沒有用 `add_conditional_edges` 的第三個 dict 參數——因為 `decision` 字串本身就是 node 名，所以可以省略翻譯表。

這樣 `state["route_history"]` 就會累積一條完整的決策軌跡，跑完之後 dump 出來就是一份天然的 audit log。

## 🔧 真實實作對照：三種複雜度的路由函式

本書範例專案 [`app/graph/`](../../../app/graph/) 裡有三個真實的路由函式，剛好對應從「最簡」到「生產級」的複雜度梯度。

### 最簡：純讀欄位

```python
# app/graph/nodes.py:200-201
def route_by_sufficiency(state: RAGState) -> str:
    return state.get("sufficiency", "sufficient")
```

兩行。`check_sufficiency_node` 已經把判斷結果寫進 `state["sufficiency"]`，路由函式只是把它讀出來——這是「**判斷與決策分離**」教科書級的最小範例。

### 中等：帶守門 + 翻譯表

```python
# app/graph/variants/selfrag.py:76-80
g.add_conditional_edges(
    "check_sufficiency",
    route_by_sufficiency,
    {"sufficient": "build_answer_contract", "insufficient": "clarify"},
)
```

決策值 `"sufficient" / "insufficient"` 翻譯成兩個不同 node id。

### 生產級：closure + 硬上限保險

```python
# app/graph/nodes.py:344-363
def make_route_after_judge(max_retries: int, *, hitl_enabled: bool = False):
    HARD_MAX = 2                                          # ① 硬上限：再不信任 settings
    effective_max = min(max(max_retries, 0), HARD_MAX)

    def route_after_judge(state: RAGState) -> str:
        score = state.get("judge_score")
        feedback = state.get("judge_feedback") or []
        if score is None or not feedback:                 # ② judge 失敗 → 視為 pass（degrade）
            return "pass"
        retry = state.get("reflection_retry", 0)
        if retry >= effective_max:                        # ③ 超過 retry 上限 → 升級到 HITL / 警告推送
            return "human_review" if hitl_enabled else "force_push"
        return "retry"

    return route_after_judge
```

對應本章三個重點：
- **① HARD_MAX = 2**：呼應「**沒有 max_attempts 煞車**」反模式。這裡甚至加了「再不信任 settings」的雙重保險——避免有人把 `max_reflection_retries` 設成 100
- **② Graceful degradation**：judge 失敗時不阻塞輸出，視為 pass（這是 production 系統與教學版的差別）
- **③ 動態分支**：`hitl_enabled` 決定 retry 用盡時是送 `human_review` 還是 `force_push` + 警告前綴。對應的 `add_conditional_edges` branches dict 是動態組裝的（見 [`reflection.py:94-99`](../../../app/graph/variants/reflection.py)）：

```python
# app/graph/variants/reflection.py:94-99
branches: dict[str, str] = {"pass": "push", "retry": "increment_retry"}
if hitl_enabled:
    branches["human_review"] = "human_review"
else:
    branches["force_push"] = "mark_warning"
g.add_conditional_edges("judge", route_after_judge, branches)
```

> 🎯 **三層複雜度梯度**：純讀欄位 → 翻譯表 → closure 注入參數 + 動態分支。從教學版升級到 production 通常就是沿這條路徑進化。

## ⚠️ 常見錯誤

1. **routing function 裡呼叫 LLM**
   每跑一次 graph 就多一次 inference 成本，而且 routing 結果會隨機飄移——同樣的 state 今天走 A、明天走 B，整個流程變得不可重現、不可測試。Routing 應該是純函式：相同 state → 相同決策。

2. **decision 用自由文字**
   `"我覺得可以再找看看"` 這種回答沒辦法被 router 的 dict 對應到，於是你開始寫 regex、寫 fuzzy match、寫 fallback……最後 router 比 reflect node 還複雜。源頭就用 `Literal` 鎖死。

3. **沒有 max_attempts 煞車**
   只要 reflect 一直回 `"retrieve_again"`，graph 就會永遠跑下去，token 帳單會用很驚人的方式教你這件事。`attempt_count >= max_attempts` 必須是 routing function 的第一道判斷。

4. **routing 邏輯藏在 reflect node**
   讓 reflect 直接決定下一步 node（例如 `state["next"] = "rewrite"`），表面看起來很方便，但 reflect 從此同時做「品質評估」和「流程治理」兩件事，職責不清。改一邊就會動到另一邊。判斷與決策必須分離。

## 一句話收斂

> **判斷與決策分離**：模型負責判斷，graph 負責決策。

---

**下一章**：[Persistence：Agent 的存檔機制](ch04-persistence.md)

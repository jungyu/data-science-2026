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

❌ 錯：

```python
"decision": "我覺得可以再找看看"
"decision": "try_again"
"decision": "maybe rewrite"
```

✅ 對：

```python
DECISIONS = Literal["rewrite_query", "retrieve_again", "finalize", "human_review"]
```

封閉集合 = router 永遠知道怎麼接。

## 條件路由的真正價值

| 沒有條件路由 | 有條件路由 |
|--------------|------------|
| 失敗就整條重跑 | 失敗變成可處理的分支 |
| 模型亂回控制不住 | 系統用結構強制 |
| 不能 audit 為什麼走那條路 | 每次 routing 可記錄 |
| 一次性 RAG | 真正的 Agent |

## 進階：路由也可以記 history

把路由決策也存進 state，之後審計超有用：

```python
def route_after_reflect(state):
    decision = state["reflection"]["decision"]

    # 記錄路由理由（在 reflect node 寫 state 時做）
    return decision  # 字串對應 edge 名稱
```

State 裡可以加：

```python
route_history: List[{
    "from": str,
    "to": str,
    "reason": str,
    "at": str,
}]
```

## ⚠️ 常見錯誤

1. **routing function 裡呼叫 LLM**：每次 routing 都付錢，且不穩定
2. **decision 用自由文字**：router 會崩
3. **沒有 max_attempts 煞車**：無限迴圈警報
4. **routing 邏輯藏在 reflect node**：責任不清

## 一句話收斂

> **判斷與決策分離**：模型負責判斷，graph 負責決策。

---

**下一章**：[Persistence：Agent 的存檔機制](ch04-persistence.md)

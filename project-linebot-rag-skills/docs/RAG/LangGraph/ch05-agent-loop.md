# 第 5 章：Agent Loop — 思考、行動、觀察、重複

> 「Agent 不是『會用工具的 LLM』，而是『會自己修正方向的流程』。」

## 經典抽象 vs 真實系統

教科書的 Agent loop（來自 2022 年 Yao et al. 提出的 **ReAct paradigm**）：

```
Think → Act → Observe → Repeat
```

聽起來很有道理。但 ReAct 原版只跑這三步：模型想一下、做一個動作、看結果、再想一下。它沒有「評估上一步做得好不好」的環節，所以一旦走偏，就只能繼續走偏。

**Reflection Agent = ReAct + 一個評估環節**。多出來的 Reflect 階段專門負責「停下來檢查」，這也是後面所有路由決策的依據。

在 LangGraph 裡，這不是抽象概念，而是**真的 graph 上的節點與邊**：

| 階段 | 對應 Node | 來源 |
|------|-----------|------|
| Think | `rewrite_query` | ReAct |
| Act | `retrieve` | ReAct |
| Observe | `generate` | ReAct |
| Reflect | `reflect` | Reflection 新增 |
| Repeat | conditional routing 回到上面 | ReAct |

## 一個典型的 RAG Agent Loop

```
        ┌──────────────────────────────────┐
        ↓                                  │
 [Rewrite Query] → [Retrieve] → [Generate] → [Reflect]
                                              │
                                              ├─→ rewrite (回去改寫)
                                              ├─→ retrieve_again (再查一次)
                                              ├─→ human_review (找人)
                                              └─→ finalize (出答案)
```

關鍵：**Reflect 提供路由判斷，不是答案產生器。** 真正決定下一步去哪的，仍然是 ch03 講過的 conditional edge / routing function。

## 一個具體例子

使用者問：

> 「這個病人的脈象看起來偏浮而數，要怎麼辨證？」

### Step 1: Rewrite Query（Think）

把口語問題改寫成適合檢索的形式：

- `浮數脈 主病 病機 辨證`
- `浮脈 數脈 合併 解釋`
- `外感熱證 浮數脈 關聯`

### Step 2: Retrieve（Act）

用改寫後的 query 去檢索，回傳「**證據候選集**」（不是答案）：

```
[Doc 1] 浮脈主表，數脈主熱...
[Doc 2] 外感風熱證的脈象表現...
```

> 為什麼刻意叫「候選集」而不是「文件」或「結果」？
> 因為這個階段的職責只是**準備材料**，要不要採信、採信哪幾份、採信到什麼程度，是後面 generate 和 reflect 的事。命名上把「檢索 ≠ 證據確認」這件事先框出來，後面 reflect 才有空間說「召回了但不夠用」。

### Step 3: Generate Draft（Observe）

根據證據生成 **草稿**（不是最終答案）：

> 浮數脈通常代表表證+熱證，常見於外感風熱...

### Step 4: Reflect（評估）

老師改作文模式：

- 答案有沒有真的被文件支持？
- 有沒有漏掉關鍵面向？
- 有沒有過度推論？
- 文件不足，還是查詢不好？

輸出結構化判斷：

```json
{
  "grounded": true,
  "sufficient": false,
  "missing_topics": ["病機說明不足"],
  "decision": "retrieve_again"
}
```

兩個關鍵欄位的差別必須分清楚——它們是 RAG 品質的兩個獨立維度：

| 欄位 | 在問什麼 | 為 false 代表 | 對應修正方向 |
|------|---------|--------------|-------------|
| `grounded` | 草稿裡每一句話，**有沒有出處支撐**？ | 答案在幻覺、自由發揮 | regenerate（重寫但限制只能引用證據） |
| `sufficient` | 證據量**夠不夠完整回答問題**？ | 答案可能對，但漏掉重要面向 | retrieve_again / rewrite_query（找更多證據） |

> 💡 上面這個例子 `grounded=true, sufficient=false`——意思是：「我說的都有依據，但依據還不夠完整」。所以 decision 是 `retrieve_again`，去補更多證據。
>
> 反過來如果 `grounded=false, sufficient=true`——文件夠多但答案在亂編，那就是 generate 步驟出問題，不是 retrieve 的問題。

### Step 5: Conditional Route

根據 decision 跳：

- `rewrite` → 查詢方向錯了
- `retrieve_again` → 方向對但證據不夠
- `finalize` → 可以了

> 💡 **Brain Power**
> 為什麼第 3 步叫「Draft」而不是「Answer」？這個命名差別有什麼意義？

<details>
<summary>解答</summary>

命名暗示「這還會被改」。如果叫 `answer`，很多開發者會直接把它輸出給使用者，跳過 reflect。命名是設計的一部分——它在傳達意圖。
</details>

## 對話：為什麼這樣設計能避免「一次失敗就崩」？

> **新手**：不就是多查幾次嗎？
>
> **老手**：差別在「能不能診斷失敗原因」。一次性 RAG 把檢索結果直接灌給 LLM，LLM 不知道資料夠不夠，只能硬掰。
>
> **新手**：那 Self-RAG 加個「再查一次」不就好了？
>
> **老手**：如果是 query 寫壞，再查只會在錯方向上越查越多。Reflection Agent 會分辨：「是 query 不對？還是召回太少？還是排序不好？」然後跳到對的節點修正。
>
> **新手**：所以失敗變成可診斷的？
>
> **老手**：對。失敗從「終局」變成「中間步驟」。

## 傳統 RAG 的問題（換個角度看）

```
Query → Retrieve → Generate → Output
```

如果 Retrieve 沒抓到關鍵文件：

- 瞎猜
- 過度泛化
- 自信但錯誤

而且**你不知道哪一步壞了**。

## Reflection Agent 把失敗變診斷題

它會問：

- 是 query 不夠精確？→ **rewrite_query**（換個說法重新檢索，例如把口語問題換成領域術語）
- 是召回太少？→ **retrieve_again**（同一個 query 但調高 `top_k`，或換 index）
- 是排序不好？→ **rerank**（進階：召回的文件夠多，但真正相關的被排在後面，用 cross-encoder 之類的模型重新排序）
- 是生成時忽略證據？→ **regenerate**（進階：證據足夠但草稿沒引用，用更嚴格的 prompt 重新生成，常配合 `grounded=false` 觸發）
- 是證據本身不足？→ **human_review**（資料庫裡就沒有，硬跑也只是幻覺）

每個失敗都有對應的修正路徑。

## 防止無限迴圈：Production 必備

```python
def route_after_reflect(state):
    if state["attempt_count"] >= state["max_attempts"]:
        return "finalize_with_limits"   # 硬煞車

    decision = state["reflection"]["decision"]
    ...
```

### 為什麼是 `finalize_with_limits` 而不是 `finalize`？

注意這裡刻意用了不同的 node 名稱。兩者的差別是：

- `finalize`：reflect 自己判斷品質夠了，正常結束 → 輸出乾淨答案
- `finalize_with_limits`：被 `max_attempts` 強制中斷 → 輸出答案時要**附帶 caveat**（例如：「本回答經 3 次檢索後仍存在資訊缺口，請審慎參考」）

混在一起寫看似省事，但會讓使用者拿到不可信的答案卻不知情，等於把品質訊號吃掉。Production 系統一定要把這兩條出口分開。

### State 裡至少要有

- `attempt_count`
- `max_attempts`
- `retrieval_history`：記錄已經查過的 query，避免在錯誤方向上反覆撞牆
- `route_history`：審計用，見 [ch03](ch03-conditional-edges.md#進階路由也可以記-history)

`retrieval_history` 的用法很簡單——retrieve node 開頭先檢查一下：

```python
def retrieve(state):
    query = state["rewritten_query"]
    if query in state["retrieval_history"]:
        # 這個 query 查過了，要嘛換 top_k、要嘛強制 rewrite
        return {"reflection": {"decision": "rewrite_query",
                               "reason": "duplicate query detected"}}

    docs = vector_store.search(query, top_k=state["top_k"])
    return {
        "retrieved_docs": docs,
        "retrieval_history": state["retrieval_history"] + [query],
    }
```

## 一張總圖

```
[Init] → [Rewrite] ─┐
                    ↓
              [Retrieve] ←─┐
                    ↓       │
              [Generate]    │
                    ↓       │
              [Reflect] ────┤  retrieve_again
                    │       │
                    ├──── rewrite_query → [Rewrite]
                    │
                    ├──── human_review → [Interrupt] → resume
                    │
                    └──── finalize → [Finalize] → [END]
```

## 🔧 真實實作對照：reflection variant 的 judge 迴圈

本書範例專案 [`app/graph/variants/reflection.py`](../../../app/graph/variants/reflection.py) 把本章的 Agent Loop 蓋成真實可跑的 graph。核心三條邊就是「reflect 迴圈」的實體：

```python
# app/graph/variants/reflection.py（節錄關鍵三邊）
g.add_edge("render_narrative", "judge")                       # Observe → Reflect
g.add_conditional_edges("judge", route_after_judge, branches) # Reflect → 路由
g.add_edge("increment_retry", "render_narrative")             # Repeat（回到生成）
```

`route_after_judge` 三向分流見 [ch03 §真實實作對照](ch03-conditional-edges.md#-真實實作對照三種複雜度的路由函式)——`pass` / `retry` / `human_review|force_push`。

### Retry 時帶著 feedback 重生成

本章說「失敗變成可診斷的中間步驟」——真實版的 `increment_retry_node` 連 feedback 都不需要自己搬運，因為它已經在 state 裡：

```python
# app/graph/nodes.py:381-386
async def increment_retry_node(state: RAGState, services: Any) -> dict[str, Any]:
    """retry 路徑：累加 reflection_retry 計數，下一輪 render_narrative 會帶 feedback。"""
    current = state.get("reflection_retry", 0)
    next_count = current + 1
    logger.info("reflection retry → %d (max=%d)", next_count, services.settings.max_reflection_retries)
    return {"reflection_retry": next_count}
```

下一輪 `render_narrative_node` 進來時會看到 `state["judge_feedback"]`（上一輪 judge 的具體 issue list），把它塞進生成 prompt——這就是「**判斷結果回填到下一輪 prompt**」的工程實現，把抽象 Reflection 變成具體訊號流。

### 跟「教學版」差在哪？

| 教學版 | 真實版 |
|--------|--------|
| `attempt_count >= max_attempts` 全寫在 routing function | 加一道 **HARD_MAX = 2** 守門（不信任 settings 配錯）|
| reflect 失敗 → 視為 `human_review` | judge 失敗 → 視為 `pass`（graceful degrade，不阻塞輸出）|
| 一個 finalize 出口 | 兩個出口：`finalize`（正常）vs `mark_warning`（被強制收斂，加 ⚠️ 前綴）|

第三個差異對應本章「**`finalize_with_limits`** vs `finalize`」的設計原則——真實系統用 `mark_warning_node` 在訊息開頭加品質警告：

```python
# app/graph/nodes.py:390-395
async def mark_warning_node(state: RAGState, services: Any) -> dict[str, Any]:
    """force_push 前在訊息開頭加品質警告。"""
    responses = list(state.get("responses") or [])
    if responses:
        responses[0] = "⚠️ 品質警告：本次回覆未通過自審\n\n" + responses[0]
    return {"responses": responses, "judge_warning_prefix": True}
```

把品質訊號暴露給使用者，不要靜悄悄把不可信答案推出去——本章設計原則的真實落地。

## 番外：Interrupt / Resume 是什麼？

上圖右側 `human_review → [Interrupt] → resume` 是 LangGraph 的招牌功能之一，值得單獨提一下。

傳統 pipeline 一旦執行下去就只能跑到底，要嘛成功、要嘛失敗。LangGraph 允許 graph **在指定節點主動暫停**，把當下的 state 完整保留下來，等外部（通常是人類）做完決策、把結果寫回 state，再從**同一個位置**繼續往下跑。

```python
# 大致長這樣
graph = builder.compile(checkpointer=checkpointer, interrupt_before=["human_review"])

# 跑到 human_review 之前會停下來，state 被保存
# 人類在 UI 上看到目前的 draft + reflection，決定怎麼修
# 把人類的決策寫回 state，呼叫 graph.invoke(None, config) 繼續

```

這個機制讓 Agent 跟人類可以**共用同一份 state**，而不是各跑各的。底層靠的是 [ch04 的 checkpoint 機制](ch04-persistence.md)——state 必須能存、能還原，interrupt 才有意義。

> 關鍵心智模型：interrupt 不是「程式當掉」，而是「graph 主動把控制權讓給外部」。

## 一句話收斂

> Agent Loop 不是讓 AI 更聰明，是讓系統允許 AI 慢慢接近正確答案。

---

**下一章**：[三種 RAG 對照](ch06-rag-vs-selfrag-vs-reflection.md)

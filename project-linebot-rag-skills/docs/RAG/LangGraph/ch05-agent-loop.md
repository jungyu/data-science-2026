# 第 5 章：Agent Loop — 思考、行動、觀察、重複

> 「Agent 不是『會用工具的 LLM』，而是『會自己修正方向的流程』。」

## 經典抽象 vs 真實系統

教科書的 Agent loop：

```
Think → Act → Observe → Repeat
```

聽起來很有道理。但在 LangGraph 裡，這不是抽象概念，而是**真的 graph 上的節點與邊**：

| 階段 | 對應 Node |
|------|-----------|
| Think | `rewrite_query` |
| Act | `retrieve` |
| Observe | `generate` |
| Reflect | `reflect` |
| Repeat | conditional routing 回到上面 |

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

關鍵：**Reflect 是路由器，不是答案產生器。**

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

- 是 query 不夠精確？→ rewrite_query
- 是召回太少？→ retrieve_again
- 是排序不好？→ rerank（進階）
- 是生成時忽略證據？→ regenerate（進階）
- 是證據本身不足？→ human_review

每個失敗都有對應的修正路徑。

## 防止無限迴圈：Production 必備

```python
def route_after_reflect(state):
    if state["attempt_count"] >= state["max_attempts"]:
        return "finalize_with_limits"   # 硬煞車

    decision = state["reflection"]["decision"]
    ...
```

State 裡至少要有：

- `attempt_count`
- `max_attempts`
- `retrieval_history`（避免重複查同樣的 query）
- `route_history`（審計用）

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

## 一句話收斂

> Agent Loop 不是讓 AI 更聰明，是讓系統允許 AI 慢慢接近正確答案。

---

**下一章**：[三種 RAG 對照](ch06-rag-vs-selfrag-vs-reflection.md)

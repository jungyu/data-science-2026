# 第 1 章：為什麼需要 LangGraph？

> 「我的 RAG 上線了，怎麼還是常常胡說？」—— 每一個做過 RAG demo 的人

## 場景：你寫了一個 RAG，然後它崩了

你蓋了一個經典 RAG：

```
使用者問題 → 檢索 → 生成 → 回答
```

Demo 很順。客戶很爽。上線兩週後 Slack 開始響：

- 「它說的東西文件裡根本沒有。」
- 「同一個問題答兩次答案不同。」
- 「為什麼這個明明很簡單的問題它答得這麼爛？」

你打開 log，發現 retrieval 那一步根本沒抓到關鍵文件。但是 LLM **還是把答案掰出來了**。

> 💡 **Brain Power**
> 如果你只能改一個地方來修這個系統，你會改哪裡？
> （提示：不是 prompt，也不是換更大的模型。）

## 真實的推理流程，不長那樣

線性流程（你寫的）：

```
A → B → C → 結束
```

人類專家做研究的真實流程：

```
理解問題 → 改寫查詢 → 檢索 → 生成草稿 → 反思
   ↑                                        ↓
   ←─────────  不夠好？回頭再來  ─────────────
```

注意關鍵字：**迴圈**、**分支**、**反思**、**回頭**。

這四個字，傳統 chain 一個都做不到。

## 對話：兩個工程師

> **A**：那我加個 if/else 不就好了？
>
> **B**：然後反思結果用 prompt 叫模型自己決定要不要再查？
>
> **A**：對啊。
>
> **B**：你要怎麼確定模型每次都回 `"retrieve_again"` 而不是 `"我覺得可以再找看看"`？
>
> **A**：……
>
> **B**：然後流程跑到一半斷線，要從頭重跑嗎？人工要審核時，整條 pipeline 就卡死嗎？
>
> **A**：所以你的意思是？
>
> **B**：我們需要的不是「更聰明的 prompt」，是「更會管流程的系統」。

## LangGraph 是什麼？

把它想成一個 **狀態驅動的流程控制板**。它原生支援：

- ✅ **State**：流程裡所有節點共用的工作筆記 —— 不用再把資料硬塞進 prompt 傳來傳去
- ✅ **Nodes**：對 state 做事的函式 —— 一個節點＝一件可單獨測試的事
- ✅ **Edges**：決定下一步去哪的連線（包括條件分支）—— 路由邏輯顯式寫在圖裡，不是藏在 prompt
- ✅ **Loops**：可以回頭、可以迭代 —— 反思失敗就重來，這是 chain 做不到的
- ✅ **Persistence**：每一步自動存檔，可中斷可恢復 —— 第 4 步掛了從第 4 步繼續，不用重跑前 3 步
- ✅ **Interrupts**：人工審核可以無縫接入 —— 流程暫停在資料庫裡，等人類點同意才繼續

> ⚠️ **重點不是「畫流程圖」**
> LangGraph 的圖不是文件，是**真的執行模型本身**。你畫的圖就是系統跑的東西。

## 三個容易被忽略的甜頭

新手讀到這裡常會說：「ok 不就是流程引擎嗎？Airflow / Temporal 也行啊？」差別在三個你 demo 階段感覺不到、但上線後天天救你的設計：

### 甜頭 1：第 4 步崩了，從第 4 步繼續

傳統 chain 跑到一半斷線，整條從頭重來。RAG 流程裡前幾步通常是檢索 + LLM 生成草稿——重跑一次就是燒一次錢。LangGraph 每跑完一個節點就把 state 自動寫進 checkpoint，崩潰後**從崩的那一步往下接**，不是從頭來。

順帶送你一個外掛功能叫 **Time-Travel**：可以把 state 回滾到 10 分鐘前的某個節點，改裡面的變數，再從那一步分支重跑——就像 Git 那樣。除錯複雜 RAG 時這招會讓你少掉一半的頭髮。

> 完整玩法在 [第 4 章：Persistence](ch04-persistence.md)。

### 甜頭 2：人類審核不再「凍結整條 pipeline」

「AI 決定要刪掉這張資料表前，先讓人類確認」——這需求做過企業案子的都遇過。傳統做法是自己寫一堆外部 DB 鎖、webhook、等待狀態，痛苦。

LangGraph 的解法是一行設定：

```python
graph.compile(checkpointer=..., interrupt_before=["delete_node"])
```

圖會在 `delete_node` 之前自動暫停，把 state 序列化存進資料庫並**釋放計算資源**。等人類在後台介面點完同意（甚至**直接改 state 內容**——例如修正 AI 找錯的關鍵字），再恢復執行。

> 細節在 [第 4 章](ch04-persistence.md) 與 [第 10 章：Production](ch10-production.md)。

### 甜頭 3：上線後看得見發生了什麼

最痛的不是 bug，是「客戶說它答錯了，你卻不知道它在哪一步答錯」。LangGraph 內建跟 **LangSmith** 整合：設好環境變數，每一次執行都會自動渲染成一張動態圖，每個節點花了多少 token、走了哪條 conditional edge、state 在每一步的 diff，全部攤開給你看。

> 不是「事後加 log」，是「圖本身就是 trace」。

> 💡 **Brain Power**
> 上面三個甜頭，哪一個是傳統 chain（LangChain LCEL、純函式 pipeline）「再多寫一點程式」就能補上的？哪一個是**架構上根本做不到**的？
> （提示：跟「狀態要不要被外部儲存」有關。）

## 一張圖看懂差異

```
[傳統 RAG]                    [LangGraph Agent]

Query                         Query
  ↓                             ↓
Retrieve  ← 失敗就 GG         Rewrite Query ← ─┐
  ↓                             ↓             │
Generate                      Retrieve  ─ ─ ─ ┤
  ↓                             ↓             │
Answer                        Generate Draft  │
                                ↓             │
                              Reflect ───────┘
                                ↓
                              Finalize
```

## 🔧 本書範例專案的對照

這份指南不只是紙上談兵——本 repo 的 [`project-linebot-rag-skills/app/`](../../../app/) 就是一個正在生產跑的 LangGraph RAG 系統。三章後談到的「三種 RAG 漸進演化」實際上在 code 裡是三個可切換的 variant：

| 演化階段 | 對應檔案 | 行數 | 特色 |
|---------|---------|------|------|
| 基本 RAG | [`app/graph/variants/basic.py`](../../../app/graph/variants/basic.py) | 49 | 線性 5 節點，最簡能跑 |
| Self-RAG | [`app/graph/variants/selfrag.py`](../../../app/graph/variants/selfrag.py) | 87 | 多 seed fan-out、sufficiency 分支 |
| Reflection Agent | [`app/graph/variants/reflection.py`](../../../app/graph/variants/reflection.py) | 120 | 4 軸 LLM-as-Judge + retry 迴圈 + HITL |

切換是一個環境變數的事（`GRAPH_VARIANT=basic|selfrag|reflection`，見 [`app/graph/rag_graph.py`](../../../app/graph/rag_graph.py)）。本書每個概念都會回頭指向這三個檔案的對應段落，讓你看「教學版」和「真實版」並排。

而本章開頭講的「Persistence 與 Interrupts 綁在一起」也不是抽象主張——`reflection.py` 末尾有一段守門 code：

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

這 8 行 code 就是本章「沒有 checkpointer 就沒有 interrupt」最直接的工程證據。

## 設計哲學的轉移

| 傳統 RAG | LangGraph Agent |
|---------|-----------------|
| 一次成敗 | 允許逐步逼近 |
| 模型自由發揮 | 系統顯式治理 |
| 失敗就重跑 | 失敗可診斷可修正 |
| 流程藏在 prompt | 流程提升成系統結構 |
| 黑盒子 | 可審計可觀測 |

## 一句話收斂

> LLM 負責「想內容」，Graph 負責「管流程」。

把這句話刻在腦子裡。後面九章都在解釋這句話的細節。

---

**下一章**：[StateGraph：流程的中樞神經](ch02-stategraph.md)

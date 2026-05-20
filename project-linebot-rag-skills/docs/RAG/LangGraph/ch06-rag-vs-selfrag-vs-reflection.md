# 第 6 章：三種 RAG 對照

> 同一條主線上，三種不同程度的「自我修正能力」。

## 一句話差異

- **RAG**：查一次，答一次
- **Self-RAG**：查完後，判斷夠不夠，必要時再查
- **Reflection Agent**：判斷答案品質、判斷查詢方向、決定改寫/重檢索/人工/結束

> 📌 **命名說明**：學術界對這幾個名詞有更精確的定義——Self-RAG 原始論文用四個 reflection tokens；另有 **CRAG**（Corrective RAG，加入「檢索品質評分→不夠好就轉 Web Search」）、**Reflexion**、**Self-Refine** 等近親變體。骨架都一樣，差在路由策略與 reflection prompt 設計。本章用工程上的寬鬆口語幫你建立直覺，遇到論文時再回來對照細節即可。

## 1. 基本 RAG

```
Query → Retrieve → Generate → Output
```

**特性**
- 線性
- 無反思
- 無修正

**適合**
- 簡單 FAQ
- 知識點明確、語言固定的任務

**問題**
- Retrieve 偏掉，整條歪掉

> 🔧 **真實對應**：[`app/graph/variants/basic.py`](../../../app/graph/variants/basic.py)（49 行）。設 `GRAPH_VARIANT=basic` 就會跑這份。

## 2. Self-RAG

```
Query → Retrieve → Generate Draft → Sufficient?
                                      │
                                      ├─ No → Retrieve Again ↑
                                      └─ Yes → Final Answer
```

**特性**
- 開始有迴圈
- 會問「資料夠不夠」
- 但通常不細分原因

**像什麼？**
> 學生交作業前看一下：「資料好像找太少了，再補兩篇再寫。」

**優點**
- 簡單，好實作
- MVP 夠用

**缺點**
- 無法分辨「查詢寫壞」vs「資料真的缺」

> 🔧 **真實對應**：[`app/graph/variants/selfrag.py`](../../../app/graph/variants/selfrag.py)（87 行）。多了 multi-seed fan-out（`expand_seeds → retrieve_one × N → fuse_scores`）+ rule-based [`SufficiencyChecker`](../../../app/graph/sufficiency.py)，資料不夠時走 `clarify` 誠實追問。設 `GRAPH_VARIANT=selfrag` 啟用。

## 3. Reflection Agent

```
Query → Rewrite → Retrieve → Generate → Reflect
                                          │
                                          ├─ rewrite_query
                                          ├─ retrieve_again
                                          ├─ human_review
                                          └─ finalize
```

**特性**
- 顯式反思節點
- 多分支條件路由
- 多維度評估（grounding / sufficient / hallucination）
- 可接 human-in-the-loop

**像什麼？**
> 研究員寫論文：「這段論證夠不夠？引用對不對？要不要再查一輪？要不要找指導教授看一下？」

> 🔧 **真實對應**：[`app/graph/variants/reflection.py`](../../../app/graph/variants/reflection.py)（120 行）。selfrag 之上加 4 軸 LLM-as-Judge（[`app/judge/scorer.py`](../../../app/judge/scorer.py)）+ retry 迴圈 + HITL 三向分流。設 `GRAPH_VARIANT=reflection` 啟用，再開 `HITL_ENABLED=true` 才會掛 `human_review` 出口。

## 對照表

| 項目 | RAG | Self-RAG | Reflection Agent |
|------|-----|----------|------------------|
| 流程結構 | 線性 | 單一迴圈 | 多分支迴圈 |
| 反思機制 | 無 | 「夠不夠」 | 多維度評估 |
| 路由 | 無 | 單一路徑 | 條件分支 |
| 失敗處理 | 整條重跑 | 多查一次 | 診斷+對應修正 |
| 複雜度 | 低 | 中 | 高 |
| 治理性 | 低 | 中 | 高 |
| 適用場景 | FAQ、簡單問答 | 知識庫查詢 | 醫療、法規、命理、高風險 |

## 三種反思檢查維度（Reflection 在檢什麼？）

對照表寫了 Reflection Agent「多維度評估（grounding / sufficient / hallucination）」——這三個詞各自在檢什麼？

### Grounding（接地度）

> **答案的每一句話，是否真的來自被檢索到的文件？**

做法：把生成的答案逐句和檢索結果比對，看每一句是否有對應出處。
失敗例：文件只提到「附子有毒性」，答案卻寫「附子可治高血壓」——明顯超出文件範圍。
路由：grounding 低 → 通常導向 `rewrite_query` 或 `retrieve_again`。

### Sufficient（資料充足度）

> **現有的檢索結果，夠不夠回答這個問題？**

做法：拿原始問題 vs 檢索結果，問 LLM「資訊是否足以回答」。
失敗例：問「八字癸水日主在丑月怎麼解？」結果只查到「癸水基本性質」——資料缺角。
路由：不夠 → `retrieve_again`（換策略再查）；換了還是不夠 → `human_review`。

### Hallucination（幻覺）

> **有沒有編造文件裡沒有的東西？**

和 grounding 是一體兩面——grounding 看「有沒有出處」，hallucination 看「有沒有無中生有」。實作上通常同一個 prompt 一起檢，但分開記分。
路由：高幻覺 + 高風險領域 → 直接 `human_review`，不要試圖自動修。

> 🔗 三種 check 的 prompt 設計、如何回填到 state、條件路由怎麼接——完整實戰在 [第 8 章：Reflection Node 深潛](ch08-reflection-node.md)。

## 對話：該用哪個？

> **新手**：那我直接上 Reflection Agent 不就好？
>
> **老手**：複雜度有代價。需要更嚴格的 schema、prompt、測試。Reflection 沒寫好，比 Self-RAG 還差。
>
> **新手**：那我怎麼選？
>
> **老手**：三個問題。
> 1. 答錯有沒有後果？沒後果用 RAG。
> 2. 知識庫詞彙跟使用者語言落差大嗎？大，用 Self-RAG 起跳。
> 3. 是高風險領域（醫療/法規/財務）嗎？是，直接 Reflection Agent + human_review。

## 升級路徑

不要一次蓋 Reflection Agent。建議：

```
Phase 1: RAG (1 週)
   ↓ 觀察「答錯」的模式
Phase 2: Self-RAG (2 週)
   ↓ 發現「再查也沒用」的 case
Phase 3: Reflection Agent (1-2 個月)
   ↓ 接 human review、加 grounding check
Phase 4: Production (持續迭代)
```

每個 phase 都先讓系統真的跑、收集真實 case，再升級。

> 💡 **Brain Power**
> 你目前的系統如果有「使用者抱怨」，最常見的抱怨類型是哪一種？這直接暗示你該升到哪一個 phase。

一旦你決定要升級到 Self-RAG 或 Reflection Agent，下一個問題就不是「要不要多一個 node」，而是：**state 裡要多哪些欄位，才能讓這些 node 正確協作？** 這就是下一章要處理的事。

## 高風險領域的特殊建議

如果你做的是：

- 中醫診斷
- 八字解盤
- 法規判讀
- 財務建議

**強烈建議**：

1. ✅ **Reflection Agent 起跳**（不要從 RAG 開始）—— 答錯成本太高，不能靠「上線後再迭代」
2. ✅ **一定要有 `human_review` 路徑** —— 高風險決策由人類最終確認；技術細節（靜態/動態 interrupt、暫停期間改 state）見 [ch04 Interrupt 段](ch04-persistence.md#interrupt暫停等人類)
3. ✅ **一定要有獨立 `grounding_check` node** —— 用獨立 LLM call 驗證答案每句話都有出處。**不要相信生成模型自己說「我有根據」**——它就是寫那答案的人，自評會偏袒
4. ✅ **一定要有 `citation_builder`**（最終答案附引用）—— 強制每段話標 `[doc_id:段落]`，把可驗證性還給使用者
5. ✅ **Finalize 前加 `safety_gate`** —— 規則引擎（不是 LLM）攔截禁區，例如：八字回應禁談醫療診斷、命理禁談未來具體日期、財務建議禁談個股名稱。規則寫在 code，不靠 prompt 約束

架構長這樣：

```
[Rewrite] → [Retrieve] → [Generate] → [Grounding Check] → [Reflect]
                                                            │
                                            ┌───────────────┼────────────┐
                                            ↓               ↓            ↓
                                       [Citation Builder] [Human]   [Rewrite/Retrieve]
                                            ↓
                                       [Safety Gate]
                                            ↓
                                       [Finalize]
```

## 一句話收斂

> 不是越複雜越好。是「失敗的後果」決定你需要哪一級。

---

**下一章**：[State Schema 設計](ch07-state-schema.md)

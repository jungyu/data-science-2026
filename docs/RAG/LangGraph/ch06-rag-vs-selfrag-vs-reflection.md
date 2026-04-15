# 第 6 章：三種 RAG 對照

> 同一條主線上，三種不同程度的「自我修正能力」。

## 一句話差異

- **RAG**：查一次，答一次
- **Self-RAG**：查完後，判斷夠不夠，必要時再查
- **Reflection Agent**：判斷答案品質、判斷查詢方向、決定改寫/重檢索/人工/結束

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

## 高風險領域的特殊建議

如果你做的是：

- 中醫診斷
- 八字解盤
- 法規判讀
- 財務建議

**強烈建議**：

1. ✅ Reflection Agent 起跳（不要從 RAG 開始）
2. ✅ 一定要有 `human_review` 路徑
3. ✅ 一定要有獨立 `grounding_check` node
4. ✅ 一定要有 `citation_builder`（最終答案附引用）
5. ✅ Finalize 前加 `safety_gate`

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

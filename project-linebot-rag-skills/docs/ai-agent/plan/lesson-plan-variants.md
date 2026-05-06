# Lesson Plan 變體 — 1 週密集 / 16 週半學期 / 自學版

> 補完 [主 lesson-plan.md](./lesson-plan.md)（8 週版 + 6 週壓縮 + 10 週寬鬆）為**極端時程**：
> - **1 週密集 Workshop**：5 個工作日 × 8 小時 = 40 小時，給資深工程師 / hackathon 參賽者
> - **16 週半學期**：每週 3–4 小時，給大學部 / 研究所選修課
> - **自學版**：無時程，依 module 完成度推進，給個人學習者
>
> 三變體共用 [capstone 規格](./capstone-spec.md)，但對應規模調整。

---

# V1：1 週密集 Workshop（40 小時）

## 適用對象

- 資深工程師（已熟 Python async + LLM API）
- Hackathon / 黑客松參賽者
- 公司內訓 5 天集訓

## 前置硬要求

學員必須在開課前**自學**：

- [ ] Python async / await 流暢使用
- [ ] 至少跑過一次 OpenAI / Claude / Gemini API（任一）
- [ ] 讀完 [docs/RAG/LangGraph/ch01–ch03](../../RAG/LangGraph/)
- [ ] `.env` + `pytest` 都跑得起來

未達條件者，請走主 8 週版。

## 時程

每天 8 小時：4 小時實作 + 2 小時討論 + 2 小時 milestone artifact。

| Day | 主題 | 對應 task | 必交 |
|-----|------|----------|------|
| **D1** | 環境 + 資料 + Graph | task-18, 12, 13, 14 | 自己領域知識庫 ≥ 30 chunks + selfrag 跑通 |
| **D2** | Sufficiency + Two-stage + Reflection | task-15, 16, 17, 19 | 三變體並陳；至少看到一個 retry |
| **D3** | Eval + Observability | task-20, 22 | `docs/eval-baseline.md` 三變體 metric 表 |
| **D4** | 進階 Tier（擇一）| task-23 / 24 / 25 / 21 | 對應 Tier 的 artifact |
| **D5** | Capstone mini + 群體 demo | — | ≤ 5 min demo + ≤ 800 字 README |

## D5 Capstone Mini 規格

時間限制下用 **簡化版** [capstone-spec.md](./capstone-spec.md)：

| 段 | 主規格分數 | Workshop 分數 | 簡化原因 |
|---|---|---|---|
| A. T1 baseline | 30 | **20** | 知識庫降到 30 chunks（時間限制） |
| B. Tier 進階 | 25 | **15** | D4 一天工時，深度減 |
| C. Eval 分析 | 25 | **15** | 5 case 即可、reference baseline 對比 |
| D. Communication | 20 | **10** | demo 3 分鐘、README ≤ 500 字 |
| **小計** | **100** | **60** | |

過 60 = pass。Workshop 不發 Distinction / Merit。

## 必砍項目

| 項目 | 為什麼砍 |
|------|---------|
| HITL 完整 demo（3 路徑各一案例）| D4 時間不夠；至少 demo approve 一條即可 |
| 多格式 ingest（PDF + Notion + CSV）| 取一格式 demo 即可；其他學員自學 |
| 完整 10 case golden.yaml | 5 case 即可，覆蓋 3 類型 |
| paper reading | 完全跳過 |
| 多 channel 整合（LINE + web 同 graph）| 只走一條 channel |

## 成本估算（每位學員）

| 階段 | LLM cost |
|------|---------|
| D1–D2 多次 e2e 跑通 | ~$1.0 |
| D3 eval baseline（5 case × 3 variant）| ~$0.5 |
| D4 進階 demo | ~$0.3 |
| D5 capstone demo + 練習 | ~$0.5 |
| **合計** | **~$2.3** |

> 公司內訓建議統一發 OpenAI key 額度 $5/人（含 buffer）。

## 講師備課清單

D 前一週：
- [ ] 預先 fork 專案到課程組織帳號
- [ ] 備好 .env 範本（含 placeholder）
- [ ] 列出 5 個學員可選領域 reference（醫療 / 法規 / 程式 / 客服 / 內容）
- [ ] 提前 ingest nextjs 知識庫到共用 sqlite-vec（學員可用作對照 baseline）
- [ ] 確認教室 wifi 能連 OpenAI API

D 期間：
- [ ] D1 上午 90 分鐘 ch01–ch06 概念 review（學員前置可能消化不全）
- [ ] D3 下午加碼 30 分鐘「降本三法」迷你 session（學員見到 cost 數字會關心）
- [ ] D5 demo 每位 3 分鐘、評審 90 分鐘、團體 retro 30 分鐘

---

# V2：16 週半學期（每週 3–4 小時）

## 適用對象

- 大學部 CS / 資管 RAG 主題選修
- Master's coursework 模組之一
- 想深入研究 RAG 系統設計的自學者（願意花半學期）

## 前置

- 修過或正修「機器學習導論」或等價課
- 看過至少 1 篇 transformer / attention paper
- 不要求 LangGraph 經驗（從零教）

## 時程結構

每週固定三段：

| 段 | 時長 | 內容 |
|---|---|---|
| 講授 | 1 小時 | 概念 + paper / 章節重點 |
| 實作 | 2 小時 | 對應 task |
| Reflection | 0.5–1 小時 | 寫週記（300 字）+ peer review |

## 16 週進度

### Phase 1：基礎（W1–W4）

| W | 主題 | 對應 task | Paper / Ref（必讀）|
|---|------|----------|---|
| 1 | Why RAG / 環境 / 資料 ETL | task-18, ch01-02 | _Lewis et al. 2020_ Original RAG paper |
| 2 | Embedding / Vector retrieval / Chunking 理論 | task-24（store）+ ch03 | _Karpukhin et al. 2020_ DPR |
| 3 | LangGraph 基礎：state / node / edge | task-12 + ch02–03 | LangGraph 官方 cookbook |
| 4 | Feature extraction / Query rewriting | task-13 | _Gao et al. 2023_ Query2Doc |

**M1 milestone（W4 末）**：自己領域知識庫 + selfrag 等價 graph 跑通。

### Phase 2：深化（W5–W8）

| W | 主題 | Paper |
|---|------|---|
| 5 | Multi-seed / Hybrid retrieval / Score fusion | task-14 + _Chen et al. 2017_ DrQA |
| 6 | Sufficiency / Refusal as feature | task-15 + _Asai et al. 2023_ Self-RAG |
| 7 | Grounded generation / Citation systems | task-16 + _Menick et al. 2022_ Teaching language models to support |
| 8 | LLM-as-Judge / Self-correction | task-17 + _Madaan et al. 2023_ Self-Refine |

**M2 milestone（W8 末，期中報告）**：三變體並陳 + 一個 paper reading review。

### Phase 3：實踐（W9–W12）

| W | 主題 | Paper / Practice |
|---|------|---|
| 9 | Evaluation methodology | task-20 + _Es et al. 2023_ RAGAS |
| 10 | Observability / Cost / Tracing | task-22 + Production case study |
| 11 | Channel adapter / API design | task-23 + 軟體工程：Hexagonal Architecture |
| 12 | Multi-format ingestion / OCR / Layout-aware parsing | task-25 + _Wang et al. 2023_ DocLLM |

**M3 milestone（W12 末）**：自己領域 eval baseline + 觀測 + 多 channel demo。

### Phase 4：上線 + Capstone（W13–W16）

| W | 主題 | Paper |
|---|------|---|
| 13 | HITL / Persistence / Resume | task-21 + _Wu et al. 2022_ AI Chains |
| 14 | Production patterns / Failure modes / Scaling | ch10 + reading case |
| 15 | **Capstone 完整版** 第 1 週 | — |
| 16 | **Capstone presentation + peer review** | — |

**Final milestone（W16）**：[capstone-spec.md](./capstone-spec.md) 完整 100 分制。

## 加碼研究活動

### Paper rotation

每位學員週 N 領 1 篇 paper（從 W2 開始），W N+2 上台 5 分鐘 review。

paper reading queue 範本（共 14 篇配對 14 個非 capstone 週）：

```
W2 RAG          → Lewis 2020
W3 retrieval    → Karpukhin 2020 (DPR)
W4 query rewrite → Gao 2023 (Query2Doc) / Ma 2023 (Generative QR)
W5 hybrid       → Chen 2017 (DrQA) / Lin 2021 (Pyserini)
W6 self-rag     → Asai 2023 / Wang 2023 (Toolformer)
W7 grounded     → Menick 2022 / Bohnet 2022 (LaMDA citations)
W8 self-correct → Madaan 2023 (Self-Refine) / Pan 2023 (Critique)
W9 eval         → Es 2023 (RAGAS) / Saad-Falcon 2023 (ARES)
W10 cost        → Patel 2024 cost analysis case
W11 architecture → Hexagonal / DDD chapters
W12 multimodal  → Wang 2023 (DocLLM) / Liu 2024 (LayoutLM)
W13 hitl        → Wu 2022 (AI Chains) / Lee 2023 (CoAuthor)
W14 production  → Real cases (Replit, Linear, etc.)
```

### Peer review 機制

W4, W8, W12 各一次 peer review session：

- 每位學員交「過去 4 週 commits + WEEKn.md 紀錄」
- 配對 review（雙盲），各方寫 ≤ 500 字 feedback
- 被 review 學員寫 ≤ 200 字 response

### Reflection journal

每週交 300 字週記，連續 16 週 = 4800 字（capstone report 的素材庫）。

## 成本估算

| 階段 | per student LLM cost |
|------|---------|
| W1–W8 學習 + 實驗 | ~$3 |
| W9–W12 eval baseline + 多次跑 | ~$5 |
| W13–W14 HITL + production demo | ~$3 |
| W15–W16 capstone 完整 | ~$5 |
| **合計** | **~$16** |

> 學校建議：course budget 編 $25/student（buffer 1.5x）。

## 期末評量分配

| 項目 | 百分比 |
|------|--------|
| 週記 / paper review（W1–W14）| 30% |
| M1 / M2 / M3 milestones | 30% |
| Capstone（[capstone-spec.md](./capstone-spec.md) 100 分）| 35% |
| Peer review 參與 | 5% |

---

# V3：自學版（無時程，module-based）

## 適用對象

- 個人學習者（無強制 deadline）
- 在職工作者，每週能投入時間不固定
- 已有部分 RAG 經驗，想針對性補完

## 設計哲學

不是「按週推進」，而是「**每完成一個 module，過一個自驗收，再進下一個**」。

學員可：
- 跳過已熟悉的 module（須通過該 module 的 self-check）
- 在某 module 停留任意久（直到自驗收過為止）
- 用任何工具輔助（GPT / Claude 直接問都可以；本來就是教 RAG）

## Module 拓撲

```
M0  環境
M1  資料：crawler + frontmatter（task-18）
M2  Graph 起步（task-12）
M3  Feature extraction（task-13）
M4  Multi-seed + Fusion（task-14）           [需 M3]
M5  Sufficiency + Clarify（task-15）         [需 M4]
M6  Two-stage Generator（task-16）           [需 M5]
M7  Judge + Reflection（task-17）            [需 M6]
M8  三變體並陳（task-19）                     [需 M7]
M9  Eval（task-20）                          [需 M8]
M10 Observability（task-22）                 [可獨立或 M2 後]
M11 Channel adapter（task-23）               [可獨立或 M2 後]
M12 Store adapter（task-24）                 [可獨立或 M1 後]
M13 Multi-format（task-25）                  [需 M12]
M14 HITL（task-21）                          [需 M7]
M15 Capstone（[capstone-spec.md](./capstone-spec.md)）
```

依賴鏈：M1→M2→M3→M4→M5→M6→M7→M8→M9→M15。M10–M14 可平行、隨時插入。

## 每個 Module 的標配

| 元件 | 內容 |
|---|---|
| **Why** | 為什麼這 module 重要（30–60 字）|
| **Read** | 必讀 spec / task / walkthrough（≤ 30 min）|
| **Build** | 動手做（依 task 步驟）|
| **Self-check** | 5 條自驗收（pass/fail）|
| **Reflection prompt** | 1–2 個延伸思辨題 |
| **Done criteria** | 寫 ≤ 300 字 module-N.md 紀錄 |

## Self-check 範本

每個 module 都有 5 條 yes/no 自驗收。範例 — M4 Multi-seed：

```markdown
## M4 Self-check
1. [ ] 我能解釋 fan-out / fan-in 為什麼用 Send + reducer
2. [ ] 我能切換 fusion strategy（max / mean / rrf）並看到 metric 差異
3. [ ] 我能在 trace JSON 中看到 5 個 seeds 各自命中幾個 chunks
4. [ ] 我能解釋為什麼 multi-seed 在「複合條件問題」上比 basic 好
5. [ ] 我跑出 selfrag variant 比 basic 多命中 ≥ 30% 的證據
```

5 條全 yes → 進 M5；任何 no → 回頭做。

## Capstone（M15）

[capstone-spec.md](./capstone-spec.md) 完整 100 分制；自學者自評 + 社群 review。

社群 review 機制（建議）：在 GitHub Discussions / Discord 開個「capstone showcase」，自學者自願送 fork 連結，其他學員 / mentor review，**評語不評分**。

## 進度追蹤

學員自己維護 `LEARNING_LOG.md`：

```markdown
# Learning Log

| Module | Status | Started | Completed | Self-check pass | Reflection link |
|--------|--------|---------|-----------|-----------------|-----------------|
| M0 | ✅ | 2026-01-10 | 2026-01-10 | 5/5 | reflections/m0.md |
| M1 | ✅ | 2026-01-15 | 2026-01-22 | 5/5 | reflections/m1.md |
| M2 | 🔄 | 2026-02-01 | — | 3/5 | reflections/m2-draft.md |
| ... | ⏸️ | — | — | — | — |
```

## 卡關時的 fallback

每個 module 都附 **「卡關 30 min 怎麼辦」** 段：

1. 重看對應 spec
2. 跑 unit test 看哪邊不對
3. 把 task 內的範例直接 copy-paste 跑一次
4. 對照 [W1 e2e 驗收](../examples/w1-e2e-verification.md) / [W2-W8 e2e 驗收](../examples/w2-w8-e2e-verification.md) 比較自己的 log
5. 仍卡 → 開 GitHub Discussion 問

> ⚠️ 自學版**沒有授課者**。「能自己解決卡關」本身就是 module 的隱藏 self-check。

## 預估完成時間

| 學員背景 | 預估完成時間 |
|---|---|
| 已熟 LangGraph / async Python | 3–4 週（投入 ~10 hr/week）|
| 熟 Python + LLM API，新接觸 LangGraph | 6–8 週 |
| Python 進階，無 LLM 經驗 | 12–16 週 |
| Python 入門 | 不建議單獨自學，請走主 8 週 + 群組 |

## 自學版常見坑

| 坑 | 解 |
|---|---|
| 拖延卡 M2 不前進 | 設「14 天 hard limit」，超過就跳到 M10/M11 換口味 |
| Self-check 自我感覺良好但其實沒過 | M3, M6, M9, M15 各拉一個 mentor / 同好 review |
| 沒有 deadline 缺壓力 | 加入 GitHub Discussions 公告自己「將在 X 日前過 M N」|
| 改進專案而非完成 module | 用 todo list 區分「我想做的優化」與「module 必交 artifact」|

---

# 三變體選擇樹

```
我有多少時間？
├─ 5 天集中（hackathon / 公司內訓）
│   └─ V1：1 週密集 Workshop（前提：資深工程師）
├─ 8 週左右
│   └─ 主 lesson-plan.md（多數情境的 default）
├─ 半學期 16 週
│   └─ V2：學術半學期（含 paper reading + peer review）
└─ 沒有固定時程
    └─ V3：自學版（module-based，依依賴鏈走）
```

## 三變體共通元素

無論走哪個變體，都共用：

- **同一份 spec / task**（14 spec + 12 task）
- **同一份 [capstone-spec.md](./capstone-spec.md) 評分標準**（V1 用簡化版 60 分制；V2/V3 用完整 100 分制）
- **同一份 [doc-01](../guides/doc-01-transferability-guide.md)** 轉換指南
- **同一份 [swap-diff-three-domains.md](../guides/swap-diff-three-domains.md)** 領域 reference
- **同一套 W1 / W2-W8 e2e 驗收紀錄**（V2/V3 學員看「真實跑過長什麼樣」對照）

差異只在於**時程結構與必交 milestone 的密度**。

---

## 給授課者選變體的建議

| 情境 | 建議變體 |
|---|---|
| 公司新人入職 onboarding | 主 8 週（內部 mentor 帶）|
| 公司年度 hackathon / 黑客松 | V1 1 週密集 |
| 大學部選修課（3 學分）| V2 16 週半學期 |
| 研究所討論課（2 學分） | 主 8 週 + paper rotation（V2 抽部分）|
| 開放給線上學員 self-paced | V3 自學版 |
| 個人學習（兼職投入） | V3，估 6-12 週 |
| 訓練營 / bootcamp 8 週課程 | 主 8 週 |
| 短期 workshop 試水溫（2 天）| 主 8 週的 W1 + W4 抽精華（不發 capstone）|

---

*三變體共用 [capstone-spec.md](./capstone-spec.md)；只有 V1 用簡化 60 分制，V2/V3 用完整 100 分制。*

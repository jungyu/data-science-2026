# W8 Capstone Project 規格書

> 對應 [lesson-plan W8](./lesson-plan.md#week-8端對端整合--自選領域-demo)。本檔給**授課者打分** + **學生明確知道評分依據**。
>
> 一份合格的 capstone 證明學生：
> 1. 完成 [doc-01](../guides/doc-01-transferability-guide.md) 至少 T1（換領域）+ 一個進階 Tier
> 2. 能用[三領域 reference](../guides/swap-diff-three-domains.md) 之一作為起點
> 3. 能用 eval 量化自己的 baseline，並解釋與 W1 nextjs baseline 的差異

## 提交格式

每位學生交付一份 fork：

```
my-rag-bot/
├── README.md                    # 領域定位 + 設計決策（capstone summary）
├── docs/
│   ├── eval-baseline.md         # T1 必交（W5 produced）
│   ├── swap-store-decision.md   # T3 必交（W6）
│   ├── safety-cases.md          # T4 必交（高風險領域才需）
│   └── capstone-report.md       # 本檔的 self-assessment
├── tests/cases/golden.yaml      # ≥10 個自己領域 case
├── skills/                      # 自己領域的 SKILL.md × N
├── scripts/site_rules.py        # 自己領域目標站 selector
└── ...（其餘專案結構不動）
```

## 評分總表（100 分）

| 段 | 權重 | 主題 | 量化判準 |
|---|---|---|---|
| **A** | 30 | T1 Baseline replication | 4 處改動完整 + W1 等級 metric |
| **B** | 25 | Tier 進階（T2 / T3 / T4 擇一）| 對應 artifact 完整 |
| **C** | 25 | Eval baseline 分析 | 與 W1 / 對應 reference baseline 對比解釋 |
| **D** | 20 | Communication（demo + README）| 5 分鐘 demo + ≤1500 字 README |
| **必過門檻** | — | 工程基本面 | 不過直接 Fail |

---

## 必過門檻（任一不過 = Fail）

學生提交前自查、評審第一輪掃這 6 條：

| # | 條件 | 驗證指令 |
|---|---|---|
| 1 | `pytest` 全綠（含學生新增測試）| `pytest` |
| 2 | `python scripts/eval.py --quick` 跑得起來 | run + check exit code |
| 3 | `golden.yaml` ≥ 10 個 case，分布涵蓋 ≥ 3 類型 | 檢查 `tests/cases/golden.yaml` |
| 4 | 三變體（basic/selfrag/reflection）都能 build 出 graph | `scripts/dump_graph_mermaid.py` |
| 5 | 至少一條 channel 端對端 demo 過（LINE 或 `/api/chat`）| 看 README 截圖 / 影片 |
| 6 | `docs/eval-baseline.md` 有真實 metric 數字（非空模板）| 抓 `chunk_recall_avg` 等欄位非 n/a |

任一不過：直接 Fail。後續 A–D 不計分。

---

## A. T1 Baseline Replication（30 分）

學生必須**完整替換 4 處**並提供證據：

### A-1. `skills/` 替換（5 分）

| 分數 | 標準 |
|---|---|
| 5 | 至少 2 個自定 skill；rag_categories 與知識庫 chunk category 對齊；`use_when` / `avoid_when` 寫得清楚 |
| 3 | 有 1 個自定 skill；rag_categories 對齊 |
| 1 | 改了 SKILL.md 字串但結構沿用 nextjs |
| 0 | 沒改 |

### A-2. 知識庫 ≥ 50 chunks（10 分）

| 分數 | 標準 |
|---|---|
| 10 | ≥ 50 chunks；自己跑 crawler 或 PDF / Notion 多源；metadata 完整含 source_url + page_number（若 PDF）|
| 7 | ≥ 50 chunks；單一資料源 |
| 4 | < 50 chunks 但 ≥ 20 |
| 0 | 沿用 nextjs / 沒 ingest |

驗證：`select count(*) from private_knowledge` 或 `select count(*) from private_knowledge_meta`。

### A-3. Feature Extractor 客製（10 分）

| 分數 | 標準 |
|---|---|
| 10 | 子類化 `ExtractedFeatures` 加 ≥ 2 個領域欄位；rule-based 或 hybrid（rule + LLM fallback）|
| 7 | 加 ≥ 1 個領域欄位 |
| 4 | 改 prompt 但 schema 不變 |
| 0 | 沒改 |

驗證：`grep -r "class.*Features" app/graph/feature_extractors/`。

### A-4. golden.yaml 自製（5 分）

| 分數 | 標準 |
|---|---|
| 5 | ≥ 10 個自己領域 case，4 類分布完整（faq / multi / gap / ground）；至少 3 個含 `must_cite_sources`、3 個含 `forbidden_phrases` |
| 3 | ≥ 10 個 case，3 類分布 |
| 1 | < 10 個 case |
| 0 | 沿用 nextjs cases |

---

## B. Tier 進階（25 分，三選一）

學生必須選擇 T2 / T3 / T4 至少一條走完。多走加分（每條額外 +5，最多三條總 35 分但段內仍上限 25）。

### B-T2：加 web UI / API（25 分）

| 分數 | 標準 |
|---|---|
| 25 | `/api/chat` 可用；附簡單前端（HTML + JS）；LINE 與 web 同 query 一致性測試通過 |
| 18 | `/api/chat` 可用，無前端 |
| 10 | 部分實作但兩 channel 行為不一致 |
| 0 | 沒做 |

### B-T3：換 store / 加多格式（25 分）

| 分數 | 標準 |
|---|---|
| 25 | 用 sqlite-vec 或 Pinecone 跑通；至少 1 個非 web 來源（PDF / Notion / CSV）ingest 進去；citation 帶 page_number |
| 18 | 換 store 但只 markdown |
| 10 | 加 PDF 但沒換 store |
| 0 | 沒做 |

### B-T4：上線生產（HITL + observability + eval baseline）（25 分）

| 分數 | 標準 |
|---|---|
| 25 | HITL 啟用，走過 ≥ 3 個 review 案例（approve / revise / drop 各一）；trace 至少 50 筆；`docs/safety-cases.md` 含完整故事 |
| 18 | HITL 啟用，3 路徑跑過但案例 < 3 個 |
| 10 | 只啟 observability，無 HITL |
| 0 | 沒做 |

> **領域引導**：醫療 / 法規類**強烈建議**走 T4。低風險領域（程式教學）走 T2 即可。三領域 reference 見 [swap-diff-three-domains.md](../guides/swap-diff-three-domains.md)。

---

## C. Eval Baseline 分析（25 分）

學生必須交 `docs/eval-baseline.md`，含**真實跑出的 metric** + **與參考 baseline 的對比解釋**。

### C-1. Metric 表完整度（10 分）

| 分數 | 標準 |
|---|---|
| 10 | 三變體 × 6 metric 全部跑出（chunk_recall / citation_accuracy / forbidden / clarification / judge_pass / latency）；無 `n/a` 除非該 metric 不適用 |
| 7 | 缺 1–2 個 metric |
| 4 | 只跑單一 variant |
| 0 | 沒跑 |

### C-2. 與 Reference Baseline 對比（10 分）

學生選定一個 [swap-diff reference](../guides/swap-diff-three-domains.md)（醫療 / 法規 / 程式教學），對照「**預期 metric**」段。

| 分數 | 標準 |
|---|---|
| 10 | 每個 metric 都和 reference 預期值對比；不符的部分有可信解釋 |
| 7 | 大多數 metric 對比；少數無解釋 |
| 4 | 只列數字不解釋 |
| 0 | 沒對比 |

### C-3. 失敗案例分析（5 分）

| 分數 | 標準 |
|---|---|
| 5 | 每個 failed case 都有 root cause 分析 + 改進方向 |
| 3 | 列出 failed case 但分析淺 |
| 0 | 沒分析 |

---

## D. Communication（20 分）

### D-1. README（10 分）

≤ 1500 字（中文）或 ≤ 800 words（英文）。必含：

1. 領域定位（你的 RAG 做什麼 / 不做什麼）
2. 設計決策（為什麼選這個 swap-diff reference / 為什麼這些參數）
3. 已知限制（你的系統哪裡會壞）
4. 下一步要改什麼

| 分數 | 標準 |
|---|---|
| 10 | 4 段都明確；用具體例子說明設計決策 |
| 7 | 4 段齊全但部分抽象 |
| 4 | 缺 1–2 段 |
| 0 | README 是空的或只有專案名 |

### D-2. Demo（10 分）

5 分鐘 demo（影片或 live 簡報），參考 [W1 demo 腳本](../examples/w1-demo-script.md) 結構：

1. 領域與資料源
2. 一個典型 query 跑通（看 retrieval / contract / narrative / cost）
3. 一個邊界 case（clarify 或 HITL 或 judge fail）
4. eval 結果摘要
5. 限制 + 下一步

| 分數 | 標準 |
|---|---|
| 10 | 5 點全到；現場跑通；含 cost 數字 |
| 7 | 5 點全到但其中一個 hand-wave |
| 4 | < 5 點 |
| 0 | 沒交 |

---

## 加分項（最多 +10）

| 加分 | 條件 |
|---|---|
| +3 | 自寫一個新 Ingester（除 markdown / pdf / csv / notion 之外，例：Confluence / Google Docs / DB dump）|
| +3 | 自加一個 LangGraph 節點（除 task-12～25 既有 13 個）並文件化 |
| +3 | 自寫 channel adapter（例：Slack / Discord / Telegram）並通過整合測試 |
| +5 | Real-world deployment（學校 / 公司 / 開源社群實際使用），含 ≥ 30 days 觀測資料 |

> 加分總上限 +10。Capstone 滿分 100 + 10 = 110。

---

## 自評檢查單（學生交件前自查）

```markdown
## 必過門檻
- [ ] pytest 全綠
- [ ] scripts/eval.py --quick 跑得起來
- [ ] tests/cases/golden.yaml ≥ 10 個 case
- [ ] 三變體 build 通過
- [ ] LINE 或 /api/chat 至少一條端對端 demo 過
- [ ] docs/eval-baseline.md 有真實 metric

## A. T1（30）
- [ ] skills/ 替換，rag_categories 對齊（5）
- [ ] 知識庫 ≥ 50 chunks（10）
- [ ] Feature Extractor 加 ≥ 2 領域欄位（10）
- [ ] golden.yaml 自製，4 類分布（5）

## B. Tier 進階（25，三選一）
- [ ] T2 web UI / [ ] T3 store + 多格式 / [ ] T4 HITL + 上線

## C. Eval 分析（25）
- [ ] 三變體 × 6 metric 表完整（10）
- [ ] 與 reference baseline 對比解釋（10）
- [ ] failed case root cause 分析（5）

## D. Communication（20）
- [ ] README 4 段（領域 / 決策 / 限制 / 下一步）（10）
- [ ] 5 分鐘 demo 5 點都到（10）

## 加分（≤ +10）
- [ ] 新 Ingester / [ ] 新 graph node / [ ] 新 channel / [ ] real deployment
```

---

## 評分等級

| 總分 | 等級 | 含義 |
|---|---|---|
| 90+ | **Distinction** | 教學承諾全部兌現；可以做為 W9 助教範例 |
| 75–89 | **Merit** | T1 完整 + 一個進階 Tier；可作為下屆學生 fork 的起點 |
| 60–74 | **Pass** | T1 完整；分析或 communication 可加強 |
| < 60 | **Fail** | 必過門檻不符或 T1 未完成 |

> **不同 lesson plan 變體對應的 capstone 規模**：
> - 主 8 週 / 6 週壓縮 / 10 週寬鬆 / 16 週半學期 → **完整 100 分制**（本檔）
> - 1 週密集 workshop → **簡化 60 分制**（見 [lesson-plan-variants.md V1 §「D5 Capstone Mini 規格」](./lesson-plan-variants.md#d5-capstone-mini-規格)）
> - 自學版 → **完整 100 分制**，但社群 review 取代授課者打分

---

## 給授課者的評分流程建議

每份 capstone 預估 30–45 分鐘評分時間。建議流程：

1. **5 min** — clone fork、跑必過門檻 6 項自動化檢查
   ```bash
   git clone <student-fork>
   cd <fork> && python -m pip install -e ".[dev,crawler]" --quiet
   pytest --quiet 2>&1 | tail -3
   CHECKPOINT_BACKEND=none python scripts/eval.py --quick
   python scripts/dump_graph_mermaid.py
   wc -l tests/cases/golden.yaml
   ```
2. **10 min** — 看 `docs/eval-baseline.md` + `README.md`
3. **5 min** — 看 demo 影片（≤ 5 min）
4. **10 min** — 抽 2–3 個 commit 看 code quality（不評分但給意見）
5. **5 min** — 填評分單

完整評分單範本：

```markdown
# Capstone 評分 — <student name> / <domain>

## 必過門檻
1. pytest: ✅ / ❌
2. eval --quick: ✅ / ❌
3. golden ≥ 10: ✅ / ❌  (count: __)
4. 三變體 build: ✅ / ❌
5. channel demo: ✅ / ❌
6. eval-baseline real numbers: ✅ / ❌

如有 ❌ → Fail，停止

## A. T1 (30)
- A-1 skills (5): __
- A-2 KB (10): __  (chunks: __)
- A-3 feature extractor (10): __
- A-4 golden.yaml (5): __

## B. Tier 進階 (25)
- 選擇: T2 / T3 / T4
- 分數: __

## C. Eval 分析 (25)
- C-1 metric 表 (10): __
- C-2 對比解釋 (10): __
- C-3 failed case (5): __

## D. Communication (20)
- D-1 README (10): __
- D-2 Demo (10): __

## 加分 (≤ +10): __

## 總分: ___ / 110
## 等級: Distinction / Merit / Pass / Fail
## Comments: ___
```

---

## 與三領域 reference 的對齊

| 學生領域 | 推薦 reference | T 階梯 |
|---|---|---|
| 醫療 / 健康 / 心理 | [醫療助理 reference](../guides/swap-diff-three-domains.md#領域-1醫療助理高風險示範) | **T4 必走** |
| 法律 / 合規 / 財務 | [法規問答 reference](../guides/swap-diff-three-domains.md#領域-2法規問答中高風險) | **T4 強烈建議** |
| 程式 / 技術 / 教育 | [程式教學 reference](../guides/swap-diff-three-domains.md#領域-3程式教學低-中風險最像-w1-nextjs) | T2 / T3 即可 |
| 客服 / 商務 / 內容 | 程式教學 reference 為起點，視風險加 HITL | T2 起跳 |

學生在 README 必須**明示自己選哪個 reference + 為什麼**。

---

## 對 lesson-plan 的回頭補充

W8 結束時，學生交 capstone 流程：

```
W8 第一天： 跑 doc-01 T1–T4 checklist 自查
W8 中段：   填本檔的「自評檢查單」
W8 最後一天：交 fork URL + demo 影片
W9 第一週： 授課者依本檔評分流程批改、回饋
```

---

## 與既有教學文件的對應

| 文件 | 用途 |
|---|---|
| [roadmap.md](./roadmap.md) | 設計藍圖（按 phase）|
| [lesson-plan.md](./lesson-plan.md) | 學習進度（按週）|
| [doc-01](../guides/doc-01-transferability-guide.md) | 轉換指南（4 Tier）|
| [swap-diff-three-domains.md](../guides/swap-diff-three-domains.md) | 三領域 reference |
| **本檔（capstone-spec.md）** | **W8 評量標準** |

四份文件相互引用，不重複內容；學生從 lesson plan 進入，依 doc-01 + swap-diff 動手做，最後依本檔交 capstone。

---

*本檔對應 lesson-plan W8 的「終測」評量標準。授課者可直接複製評分單；學生可直接套自評檢查單。*

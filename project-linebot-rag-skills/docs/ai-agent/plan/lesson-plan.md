# 8 週 Lesson Plan — RAG + LangGraph 教學進度表

> 對應 [roadmap.md](./roadmap.md) 的 12 個 task（P0 + P1–P4 + 跨切面 + 可移植層）。
> 假設每週 5–8 小時學習時間。進度快可壓縮到 6 週（合併 W6+W7、W7+W8）。
> 每週收束於一個可審計的 milestone artifact。

## 整體節奏

| Week | 主題 | 對應 task | 對應 doc-01 Tier | Milestone |
|------|------|----------|----------------|-----------|
| W1 | 環境就緒 + Graph 起步 | task-18, task-12 | T1 起步 | 自己的知識庫 + 線性 graph 跑通 |
| W2 | Multi-seed 檢索 | task-13, task-14 | T1 | 複合條件問題能展開多 seed 並命中 |
| W3 | Sufficiency + Grounded Generation | task-15, task-16 | T1 | 沒資料會誠實追問、有資料能 grounded 生成 |
| W4 | Self-Correction 迴圈 | task-17, task-19 | T1 完成 | 三變體並陳，judge + retry 看得到 |
| W5 | 量化驗證 + 觀測 | task-20, task-22 | T1 baseline 交付 | eval-baseline.md + trace summary |
| W6 | 多 channel + 多 store | task-23, task-24 | T2 + T3 | LINE + Web 雙 channel；sqlite-vec 離線跑通 |
| W7 | 多格式資料 + HITL | task-25, task-21 | T3 + T4 | PDF citation 帶 page_number；HITL approve/revise/drop 走通 |
| W8 | 端對端整合 + 自選領域 | 全部回顧 | T1–T4 全套 | 學生自選領域的可審計 baseline + demo |

---

## Week 1：環境就緒 + Graph 起步

**主題**：把開發環境弄好、做出有自己資料的可跑系統。

**學習目標**

- 理解 LangGraph 的 `StateGraph` / TypedDict / node / edge 四個基本概念
- 看到「線性函式 → graph」的等價重構過程
- 會用 Playwright crawler 把外部網頁抓進知識庫
- 認識 frontmatter 是「資料進到系統的契約」

**主要任務**

| 任務 | 對應 | 預期工時 |
|------|------|---------|
| 設定 .env、跑通 `pytest` | — | 1 小時 |
| 讀 [task-18 walkthrough](../examples/crawl-recipe-nextjs.md) 並執行 | task-18 | 2 小時 |
| 讀 [task-12 spec](../specs/spec-12-graph-refactor.md) + 理解 graph 等價重構 | task-12 | 2 小時 |
| 跑通 LINE webhook → graph → push 一條訊息 | — | 2 小時 |

**必交 artifact**

- [ ] `docs/RAG/crawled/<my-domain>/` 至少 5 個 markdown 檔，frontmatter 完整
- [ ] **graph 端對端跑通**——選一條：
  - LINE webhook + ngrok（學生有 LINE Developer 帳號時）
  - **`/api/chat` endpoint**（無 LINE 帳號時的備援；task-23 提供）
  - **`scripts/demo_compare_variants.py`**（最簡單，不需 web server）
- [ ] commit 一份 `WEEK1.md` 紀錄你問了什麼、graph 跑了多久

**Milestone**：問一個你抓進來的 docs 涵蓋的問題，回覆內容**至少有一處與你抓的內容相關**。

> ⚠️ **W1 容易撞到的坑**（[W1 e2e 驗收報告](../examples/w1-e2e-verification.md) 已紀錄完整 4 個摩擦點）：
> - **frontmatter `category`** vs skill `rag_categories` 不對齊 → 0 hits（解法：crawl `--category` 對齊 skill）
> - **跨語言 query**：中文 query + 英文 chunks → sufficiency 卡 lexical overlap=0（解法：`SUFFICIENCY_MIN_FEATURE_OVERLAP=0`）
> - **router 非確定性**：同 query 不同跑次 routing 結果不同（解法：低 temperature；長期靠 task-20 eval majority vote）
> - **上游 docs URL alias**：少數站不同 URL 指向同一頁；學生抓站要看 sitemap

**Brain Power**

> 為什麼 task-12 要堅持「行為等價重構」？如果一開始就把 multi-seed 寫進去，會撞到什麼問題？

---

## Week 2：Multi-seed 檢索

**主題**：把使用者輸入結構化抽取，展開為多條 seed 並行檢索，再 fusion 合併。

**學習目標**

- 結構化 query 比 raw embedding 更精準
- LangGraph 怎麼做 fan-out / fan-in（`Send` API + `Annotated[list, add]` reducer）
- Score fusion 三策略（max / mean / RRF）的差異與適用情境

**主要任務**

| 任務 | 對應 | 預期工時 |
|------|------|---------|
| 讀 [task-13 spec](../specs/spec-13-feature-extractor.md) + 理解 LLM-based extractor | task-13 | 2 小時 |
| 讀 [task-14 spec](../specs/spec-14-multi-seed-retrieval.md) + 看 fan-out 拓撲 | task-14 | 2 小時 |
| 跑 `python scripts/demo_compare_variants.py` 對複合條件問題比較 basic / selfrag | — | 1 小時 |
| 切換 `FUSION_STRATEGY=max|mean|rrf` 各跑一次同問題 | — | 1 小時 |

**必交 artifact**

- [ ] 一份 `WEEK2.md` 紀錄：對你領域的某個複合條件問題（例：「Next.js 14 + SSR + hydration」）
  - basic variant 命中幾個 chunks
  - selfrag variant 展開幾條 seed、命中幾個 chunks
  - max / mean / rrf 三策略的 top-K 差異
- [ ] 三策略至少有一條觀察到「跟另一條結果不同」

**Milestone**：能向別人解釋「為什麼複合條件問題上 selfrag > basic」。

**Brain Power**

> 你的領域更適合哪種 fusion 策略？為什麼？（提示：依「絕對分數可信度」 vs 「多路共識」決定）

---

## Week 3：Sufficiency + Grounded Generation

**主題**：graph 學會誠實——資料不夠時不強行生成、資料夠時用程式組骨架 + 受限 LLM 寫敘事。

**學習目標**

- LangGraph 的 conditional edge（`add_conditional_edges` + dict mapping）
- 「Answer Contract」設計：為什麼 Stage 1 不交給 LLM
- Grounded constraint 在 prompt 中怎麼寫
- Citation 從 chunk metadata 流到 narrative `[來源 N]`

**主要任務**

| 任務 | 對應 | 預期工時 |
|------|------|---------|
| 讀 [task-15 spec](../specs/spec-15-sufficiency-clarify.md) + 三項 sufficiency 規則 | task-15 | 2 小時 |
| 讀 [task-16 spec](../specs/spec-16-two-stage-generator.md) + AnswerContract schema | task-16 | 2 小時 |
| 用 [`scripts/demo_compare_variants.py`](../../../scripts/demo_compare_variants.py) 問三類問題：充分 / 複合 / 沒涵蓋 | — | 1 小時 |
| 看 narrative 中的 `[來源 N]` 是否真的對應 retrieved chunks | — | 1 小時 |

**必交 artifact**

- [ ] `WEEK3.md` 紀錄三類問題在 selfrag variant 下的行為：
  - 充分案例：sufficiency 結果 + Answer Contract dump
  - 沒涵蓋案例：clarify 產出的 2-3 條追問
- [ ] 找一個 Answer Contract dump 出來貼進文件（驗證「結構是程式組的」）

**Milestone**：對「我系統什麼時候會誠實追問、什麼時候會生成」有清楚答案。

**Brain Power**

> 如果你的領域 sufficiency 偽陽性（明明該追問卻生成）很常見，你會調哪個門檻？  
> （`sufficiency_min_chunks` / `min_top_score` / `min_feature_overlap`）

---

## Week 4：Self-Correction 迴圈

**主題**：reflection variant 落地——4 軸 judge 自評 + retry 迴圈 + 三變體並陳。

**學習目標**

- LangGraph 三向 conditional edge（pass / retry / force_push）
- Retry 上限保險的設計（HARD_MAX = 2）
- 為什麼 4 軸而非單一分數
- 三變體並陳（basic / selfrag / reflection）的對照意義

**主要任務**

| 任務 | 對應 | 預期工時 |
|------|------|---------|
| 讀 [task-17 spec](../specs/spec-17-judge-reflection.md) | task-17 | 2 小時 |
| 讀 [task-19 spec](../specs/spec-19-graph-variants.md) + 三變體拓撲 | task-19 | 1 小時 |
| 跑 `scripts/dump_graph_mermaid.py` 看三變體 mermaid 圖 | — | 0.5 小時 |
| 故意問「易誘發 hallucination 的問題」看 reflection 是否會 retry | — | 1.5 小時 |

**必交 artifact**

- [ ] `WEEK4.md` 紀錄至少一個案例的 retry 軌跡（trace JSON 或 log）：
  - 第一次 judge 分數
  - 第二次 render 後 judge 分數
  - 是否 pass 或進 force_push
- [ ] 三變體 mermaid 圖貼進 `WEEK4.md`

**Milestone**：能解釋 ch06 「該用哪個」三問題在你領域的答案。

**Brain Power**

> 你的領域如果 retry 永遠到上限（force_push），代表 judge 太嚴格還是 generator 太弱？怎麼判斷？

---

## Week 5：量化驗證 + 觀測

**主題**：把感覺變數字——eval baseline + trace + cost 三件套上線。

**學習目標**

- Golden case set 設計：四類分布（faq / multi / gap / ground）
- 6 項 metric 的意義與適用變體
- LangGraph 的 trace 與 cost tracking 模式（ContextVar dispatch）

**主要任務**

| 任務 | 對應 | 預期工時 |
|------|------|---------|
| 讀 [task-20 spec](../specs/spec-20-evaluation.md) | task-20 | 1 小時 |
| 把 [`tests/cases/golden.yaml`](../../../tests/cases/golden.yaml) 換成 ≥10 個自己領域案例 | — | 3 小時 |
| 跑 `python scripts/eval.py --output baseline.json --format json` | — | 0.5 小時 |
| 讀 [task-22 spec](../specs/spec-22-observability.md) | task-22 | 1 小時 |
| 跑 `python scripts/trace.py summary --last 50` | — | 0.5 小時 |
| 填寫 [eval-baseline.md 範本](../examples/eval-baseline.md) 為自己領域的 baseline | — | 2 小時 |

**必交 artifact**

- [ ] `tests/cases/golden.yaml`（≥10 案例，四類分布完整）
- [ ] **`docs/eval-baseline.md`**（doc-01 T1 必交 artifact，**Milestone 之核心**）：三變體 metric 對比表 + 失敗案例分析 + 結論建議
- [ ] 至少 3 條 trace 的 cost 估算紀錄

**Milestone**：T1 baseline 交付。能回答「我系統現在 chunk_recall / forbidden_phrase_rate / latency 是多少」。

**Brain Power**

> 跑同一份 case set 兩次 metric 差異有多大？如果差異 > 5% 代表什麼問題？

---

## Week 6：多 channel + 多 store

**主題**：把 LINE 解耦、加 web UI；換 store backend（離線 sqlite-vec / 商業 Pinecone）。

**學習目標**

- Adapter pattern：channel / store 兩層 Protocol
- Channel-agnostic state schema（`external_user_id` 取代 `line_user_id`）
- 為什麼 sqlite-vec 是「教學零依賴」殺手鐧

**主要任務**

| 任務 | 對應 | 預期工時 |
|------|------|---------|
| 讀 [task-23 spec](../specs/spec-23-channel-adapter.md) | task-23 | 1.5 小時 |
| 跑 `curl POST /api/chat`，比對 LINE 與 Web 同 query 回覆語意一致 | — | 1 小時 |
| 讀 [task-24 spec](../specs/spec-24-knowledge-store-adapter.md) | task-24 | 1.5 小時 |
| `KNOWLEDGE_STORE_BACKEND=sqlite_vec` 重 ingest 自己領域 + 重跑 eval | — | 2 小時 |
| 比對 sqlite-vec vs Supabase 的 metric 差異 | — | 1 小時 |

**必交 artifact**

- [ ] `WEEK6.md`：
  - LINE 與 Web 同 query 截圖 / 文字對照
  - sqlite-vec vs Supabase 的 metric 對比表
  - 結論：你的領域更適合哪個 store
- [ ] （選）一個簡單的 web 前端（HTML + fetch /api/chat）

**Milestone**：T2（多 channel）+ T3 一半（換 store）兌現。

**Brain Power**

> 換到 Pinecone 在你領域的 trade-off 是什麼？什麼時候值得付費？

---

## Week 7：多格式資料 + HITL

**主題**：把 PDF / CSV 接進來、為高風險路徑加人工審查。

**學習目標**

- Document 中介格式 + Ingester Protocol
- PDF 的 page_number / section_path 怎麼流到 Citation
- LangGraph interrupt_before + checkpointer + update_state 三件套
- 何時該啟用 HITL（看領域風險）

**主要任務**

| 任務 | 對應 | 預期工時 |
|------|------|---------|
| 讀 [task-25 spec](../specs/spec-25-multi-format-ingestion.md) | task-25 | 1.5 小時 |
| 抓自己領域的 1 份 ≥30 頁 PDF + ingest | — | 2 小時 |
| 問 PDF 內容、確認 narrative `[來源 N]` 帶 `(p.42)` | — | 0.5 小時 |
| 讀 [task-21 spec](../specs/spec-21-persistence-hitl.md) + [hitl-walkthrough](../examples/hitl-walkthrough.md) | task-21 | 1.5 小時 |
| 啟用 HITL，故意觸發低分案例，走完 list / show / approve / revise / drop 三條路徑 | — | 2 小時 |

**必交 artifact**

- [ ] PDF citation 帶 `(p.N)` 的截圖 / log
- [ ] `WEEK7.md` HITL 案例集：3 條路徑各一個案例（approve / revise / drop）
- [ ] （高風險領域才需）`docs/safety-cases.md`（doc-01 T4 artifact）

**Milestone**：T3 完成（多格式）+ T4 一半（HITL）兌現。

**Brain Power**

> 你的領域哪些 skill / intent 應該無條件走 HITL？（提示：對照 ch06 §3「高風險領域」)

---

## Week 8：端對端整合 + 自選領域 demo

> **評量規格詳見 [capstone-spec.md](./capstone-spec.md)**：100 分制（30 T1 + 25 Tier 進階 + 25 eval 分析 + 20 communication）+ 6 個必過門檻 + 自評檢查單。

**主題**：把所有 12 個 task 學到的東西打包成一份可向別人介紹的 baseline。

**學習目標**

- 全套整合：自己領域的 RAG 服務從 zero 跑到上線就緒
- 文件能力：把過去 7 週的 artifact 整合成一份 README + 簡報

**主要任務**

| 任務 | 工時 |
|------|------|
| 跑一遍 [doc-01 Transferability Guide](../guides/doc-01-transferability-guide.md) 的 T1–T4 checklist | 2 小時 |
| 補完 docs/eval-baseline.md（W5）、docs/swap-store-decision.md（W6）、docs/safety-cases.md（W7） | 2 小時 |
| 寫一份 `README.md` 給自己領域的版本（領域 / 設計決策 / metric / 限制）| 2 小時 |
| 錄一段 ≤ 5 分鐘 demo 影片或寫一份簡報 | 2 小時 |

**必交 artifact**（doc-01 T1–T4 checklist 完整勾完）

- [ ] T1.1 替換 `skills/` ✓
- [ ] T1.2 知識庫已 ingest ≥50 chunks ✓
- [ ] T1.3 Feature Extractor 已客製 ✓
- [ ] T1.4 `golden.yaml` ≥10 案例 ✓
- [ ] T1.5 `docs/eval-baseline.md`：三變體 metric 表 ✓
- [ ] T2.1 `/api/chat` 可用 ✓
- [ ] T2.2 LINE + web 雙 channel 同 query 一致性測試通過 ✓
- [ ] T3.1 ≥1 個非 web 來源已 ingest（PDF）✓
- [ ] T3.2 重跑 eval，metric 不退步 ✓
- [ ] T4.1 HITL 啟用 + 走過 ≥3 個 review 案例 ✓
- [ ] T4.2 每日 trace summary 已可看 ✓

**Milestone — Final**：能 5 分鐘介紹「我做了什麼領域的 RAG，三變體 metric 是 X / Y / Z，最大限制是什麼，下一步要改什麼」。

**Brain Power**

> 過 8 週你最沒想到的事是什麼？學到最多的一個技術概念是什麼？

---

## 給授課者的時程彈性

> **更極端的時程變體**（1 週密集 / 16 週半學期 / 自學版）見 [lesson-plan-variants.md](./lesson-plan-variants.md)。本檔保留 6 / 8 / 10 週三組常見時程。

### 6 週壓縮版

合併 W1+W2、W6+W7：

| Week | 範圍 |
|------|------|
| W1 | 環境 + Graph + Multi-seed（task-18 + 12 + 13 + 14）|
| W2 | Sufficiency + Two-stage（task-15 + 16）|
| W3 | Reflection + 三變體（task-17 + 19）|
| W4 | Eval + Observability（task-20 + 22）|
| W5 | Channel + Store + 多格式 + HITL（task-23 + 24 + 25 + 21）|
| W6 | 整合 + demo |

> 適用：學員已熟 Python async + 有 LangChain / LangGraph 經驗。

### 10 週寬鬆版

- W1 環境
- W2 task-18（單獨一週深入爬蟲）
- W3 task-12
- W4 task-13 + 14
- W5 task-15 + 16
- W6 task-17 + 19
- W7 task-20 + 22
- W8 task-23 + 24
- W9 task-25 + 21
- W10 整合

> 適用：學員第一次接觸 LLM / RAG / async Python；需要更多消化時間。

---

## 共通操作守則

每週固定動作：

1. **週初**：讀對應 spec，**跑一次** `pytest`（確保環境正常）
2. **週中**：實作 / 跑 demo / 記錄觀察到 `WEEKn.md`
3. **週末**：提交本週 artifact（commit + PR），對照 milestone 檢查

評量建議（授課者）：

- 60% 主要 milestone artifact 完整度
- 20% 對 spec 設計決策的理解（小型口試或書面題）
- 20% 自選領域 final demo

> ⚠️ 不建議用「程式碼行數」或「測試覆蓋率」評分——本專案已提供完整骨架，學生主要工作是**理解 + 換領域 + 量化驗證**，不是寫新程式。

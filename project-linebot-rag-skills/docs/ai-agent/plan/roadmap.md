# 開發藍圖（教學導向 · LangGraph 主線）

> **教學進度排程**：見 [lesson-plan.md](./lesson-plan.md)（8 週版 + 6 週壓縮版 + 10 週寬鬆版）。
> **Capstone 評量規格**：見 [capstone-spec.md](./capstone-spec.md)（100 分制 + 必過門檻）。
> Roadmap 是設計藍圖、按 phase 組織；lesson plan 是學習進度、按週組織；capstone 是 W8 終測。

## 定位

本專案是「**RAG + LangGraph 教學範例**」。目標是讓學生：

1. 從一個能跑的線性 pipeline 出發，逐步學會把它重構成 LangGraph
2. 在 graph 上加入通用 RAG 增強模式（multi-seed 檢索、sufficiency 檢查、grounded 生成、self-judge 重生成）
3. **完成基礎後，能把領域層（skills、知識庫、feature extractor）替換為自己的題目**，骨架不變

因此每個 phase 都遵守兩條原則：

- **通用優先**：node 的設計不綁定特定領域；領域邏輯隔離在可替換點
- **行為等價先於功能擴充**：先重構（不改行為）→ 再加功能（改行為），學生可清楚分辨「結構變化」與「功能變化」

## 原則

1. 不破壞現有可運作的 bot：每個 phase 結束後 bot 仍能正常收發訊息
2. 每個 phase 獨立可驗收：不依賴下一個 phase 的功能
3. **每個 node 標明「可換點」與「不可換點」**，幫學生轉換題目
4. **每個 phase 標明「教學要點」**：這個 phase 教會學生哪個 LangGraph / RAG 概念
5. MCP Server 不在此藍圖內（ADR-006）

---

## Phase 概覽

| Phase | 名稱 | 教學要點 | 預估工時 | 依賴 |
|-------|------|----------|---------|------|
| **P0（前置）** | 資料準備（Playwright 支線）| Web crawling、frontmatter 設計、`source_url` 追溯 | 1–2 天 | 無 |
| **P1** | 線性 → LangGraph 等價重構 | StateGraph、TypedDict state、線性 node 串接 | 2–3 天 | 無 |
| **P2** | Feature Extractor + Multi-seed 檢索 | Fan-out / fan-in、score fusion、查詢結構化 | 3–5 天 | P1 |
| **P3** | Sufficiency Check + Two-stage Generator | 條件 edge、Clarification 分支、Answer Contract（確定性 JSON + 受限敘事）| 3–5 天 | P2 |
| **P4** | LLM-as-Judge + Reflection 迴圈 | Self-correction loop、結構化評分、迴圈上限控制 | 3–5 天 | P3 |
| **教學完整性層（跨切面）** | Eval / Persistence+HITL / Observability | 對應 docs/RAG ch06、ch04、ch10——讓學生能驗證、能審核、能觀察 | 5–7 天 | 對應主 phase 完成 |
| **轉換可移植層（跨切面）** | Channel / Store / Multi-format Ingestion + Transferability Guide | 解決「換到專業 RAG 服務」的 3 個結構性斷點 | 5–7 天 | P0–P4 完成 |
| **P5（選修）** | 工程補完 | 不屬於 graph 主線的工程議題（rerank、cache、emotion、Notion 匯入等）| 視需求 | 任意 |

> **P0 與 P1–P4 是平行支線**：學生若已有 markdown 素材可跳過 P0；想做完整端對端範例則先做 P0 把知識庫填滿再進 P1。

### 三變體並陳（對應 ch06）

P1 / P3 / P4 完成時，graph 形態剛好對應 [docs/RAG/LangGraph/ch06](../../RAG/LangGraph/ch06-rag-vs-selfrag-vs-reflection.md) 的三種 RAG 模式。本專案**保留所有三個變體並存**（不互相覆寫），由 [spec-19](../specs/spec-19-graph-variants.md) / [task-19](../tasks/task-19-graph-variants.md) 統一收尾：

| 變體 | builder | 對應 phase | ch06 模式 |
|---|---|---|---|
| `basic` | `build_basic_graph()` | P1 完成 | §1 基本 RAG |
| `selfrag` | `build_selfrag_graph()` | P3 完成 | §2 Self-RAG |
| `reflection` | `build_reflection_graph()` | P4 完成 | §3 Reflection Agent |

學生用 `GRAPH_VARIANT=basic|selfrag|reflection` 切換，並可用 `scripts/demo_compare_variants.py` 在同一輸入上比較三者差異。

### Phase 與變體輸出對應

| Phase | 完成後新增 / 強化的變體 |
|---|---|
| P1（spec-12）| 新增 `build_basic_graph()` |
| P2（spec-14）| 強化 selfrag 內部結構（multi-seed），不單獨成變體 |
| P3（spec-15 / 16）| 新增 `build_selfrag_graph()` |
| P4（spec-17）| 新增 `build_reflection_graph()` |
| **整合（spec-19）**| 三 builder 並陳 + 切換機制 + 比較 demo |

> **學生轉題目時**：完成 P1–P4 後，把 [`skills/`](../../../skills/)、知識庫、Feature Extractor 三處替換成自己的領域，graph 結構不需動。

---

## Phase 0（前置）：資料準備（Playwright 支線）

**目標**：讓學生親手把網頁抓下來、整理成 markdown、入 Supabase。**完成 P0 後知識庫已填滿，後續 P1–P4 才有東西檢索**。

**為什麼放 P0**：教學上「資料從哪裡來」是學生最常忽略也最容易卡關的環節。把 Playwright 整合進來既補完整端對端，又示範一條獨立於 graph 主線的工程實踐。

### 規格與任務

| 項目 | 規格 | 任務 | 借鑑 |
|------|------|------|------|
| Playwright 抓頁 → markdown → ingest | [spec-18](../specs/spec-18-playwright-ingestion.md) | [task-18](../tasks/task-18-playwright-ingestion.md) | [project-playwright/ch05](../../../../project-playwright/ch05-data-extraction/) + [ch08](../../../../project-playwright/ch08-supabase/) |

### 教學要點

- 兩階段解耦：**crawl 一次 → markdown 中介 → ingest 多次**
- frontmatter 攜帶 `source_url` / `content_hash` / `category`，讓 chunk 在資料庫中可追溯來源
- Playwright × readability × markdownify 組合的內容抽取模式
- robots.txt 與節流的工程倫理（教學內建檢查）
- 與 [project-playwright/ch08](../../../../project-playwright/ch08-supabase/) 的 lease-based queue 架構區分：本 phase 是教學版，ch08 是生產級進階版

### 可換點 / 不可換點

| | 可換 | 不可換 |
|---|---|---|
| `site_rules.py` 的抽取規則 | ✅ **學生轉題目時主要替換點**（每個站的 selector 不同）| ❌ frontmatter 必含 `source_url` / `content_hash` |
| URL 來源 | ✅ 純文字檔、CSV、Notion export 皆可 | ❌ ingest 端統一吃 markdown + frontmatter |
| 去重策略 | ✅ 教學版用 `content_hash` 簡化；進階可學 ch08 partial unique index | — |

### 驗收標準

- 跑一次 crawler 產出 N 份 markdown，frontmatter 完整
- 跑第二次幾乎全部 `unchanged, skipped`（hash 去重生效）
- robots.txt disallow 的 URL **不抓**且 log 明示
- ingest 後 Supabase `private_knowledge.metadata` 有 `source_url`
- 在 LINE 上問該知識庫涵蓋的問題，回覆中的 citations 帶 URL（搭配 P3 的 task-16 Citation 改動）

---

## Phase 1：線性 → LangGraph 等價重構

**目標**：把現有的 `route → retrieve → generate → push` 線性流程重構為 LangGraph，**行為完全一樣**。

**為什麼先做這個**：學生需要先在「他熟悉的、跑得起來的」程式碼上看到 graph 的等價形式，才能理解 state、node、edge 是什麼。直接跳到 Self-RAG 會讓「graph 抽象」與「新功能」混在一起，學習曲線陡。

### 規格與任務

| 項目 | 規格 | 任務 |
|------|------|------|
| Graph 等價重構 | [spec-12](../specs/spec-12-graph-refactor.md) | [task-12](../tasks/task-12-graph-refactor.md) |

### 教學要點

- `StateGraph` / `TypedDict` state schema 的設計
- node 函式簽章（`state → state`）
- 線性 edge 的串接、`START` / `END` 的角色
- 如何把現有服務（`IntentRouter`、`RAGRetriever`、`ResponseGenerator`）包成 node 而**不改它們的介面**

### 可換點 / 不可換點

| | 可換 | 不可換 |
|---|---|---|
| node 函式 | ✅ 內部實作可換廠商 / 模型 | ❌ node 的 input/output state 欄位 |
| state schema | ✅ 可加領域欄位 | ❌ 既有欄位語意 |

### 驗收標準

- 同一則訊息，重構前後的回覆內容一致（diff 為空或僅格式差異）
- 新增 `app/graph/rag_graph.py`，`webhook.py` 改呼叫 `graph.ainvoke(state)`
- 移除原線性串接函式（避免兩套並存）

---

## Phase 2：Feature Extractor + Multi-seed 檢索

**目標**：教學生「在進 retrieval 之前先把使用者輸入結構化」，然後用結構化結果**展開為多條 seed 並行檢索 + 分數融合**。

**為什麼**：單一 query embedding 對「多條件並置」的問題會稀釋語意（參考 destiny ADR-009）。Multi-seed 是 LangGraph fan-out / fan-in 的最佳教學案例，且**所有領域都用得上**。

### 規格與任務

| 項目 | 規格 | 任務 | 借鑑 |
|------|------|------|------|
| Feature Extractor node | [spec-13](../specs/spec-13-feature-extractor.md) | [task-13](../tasks/task-13-feature-extractor.md) | project-diagnosis spec-002 |
| Multi-seed 展開 + 並行檢索 | [spec-14](../specs/spec-14-multi-seed-retrieval.md) | [task-14](../tasks/task-14-multi-seed-retrieval.md) | project-destiny ADR-009 |
| Score Fusion（max / mean / RRF）| [spec-14](../specs/spec-14-multi-seed-retrieval.md) | [task-14](../tasks/task-14-multi-seed-retrieval.md) | project-destiny ADR-009 §D1 |

### Graph 變化

```
[route] → [extract_features] → [expand_seeds] → [retrieve × N (並行)] → [fuse_scores] → [generate] → [push]
```

### 教學要點

- 為什麼結構化 query 比直接拿原句去 embedding 更準
- LangGraph 怎麼做 fan-out（多 node 並行）與 fan-in（合併結果）
- Score Fusion 三種策略的差異與適用場景：
  - `max`：多 seed 任一命中即排前
  - `mean`：偏好多路共識
  - `rrf`：鈍化極端分數，最穩

### 可換點 / 不可換點

| | 可換 | 不可換 |
|---|---|---|
| Feature Extractor 規則 | ✅ **學生轉題目時主要替換點**（例如把「提取 skill 線索」換成「提取症狀詞」） | ❌ 輸出仍要是 `list[str]` 形式的 seed |
| Fusion 策略 | ✅ 預設 `max`，可切換 | ❌ 介面 `fuse(hits_per_seed) → ranked_hits` |

### 驗收標準

- 一個多條件問題（例：「我用 React 18 搭 Next.js，SSR 時遇到 hydration error 怎麼辦？」）能展開為 3+ 條 seed
- log 顯示每條 seed 各自命中的 atom 與 fusion 後的最終排序
- 切換 fusion 策略無需改 graph 結構

---

## Phase 3：Sufficiency Check + Two-stage Generator

**目標**：教學生兩件事：

1. **條件 edge**：retrieval 結果不夠時，分支去 Clarification node 而不是硬生成
2. **Answer Contract**：Generator 不要全交給 LLM 自由發揮 —— 先用程式組 JSON 骨架（確定性）→ 再用受限 prompt 寫成自然語言

### 規格與任務

| 項目 | 規格 | 任務 | 借鑑 |
|------|------|------|------|
| Sufficiency Check + Clarification | [spec-15](../specs/spec-15-sufficiency-clarify.md) | [task-15](../tasks/task-15-sufficiency-clarify.md) | project-diagnosis spec-005 / 007（suggested_questions、ambiguity_flags）|
| Two-stage Generator（Answer Contract）| [spec-16](../specs/spec-16-two-stage-generator.md) | [task-16](../tasks/task-16-two-stage-generator.md) | project-diagnosis spec-007 |

### Graph 變化

```
[fuse_scores] → [check_sufficiency]
                    ├─ 不足 → [clarify]（產出引導追問）→ [push]
                    └─ 充足 → [build_answer_contract] → [render_narrative] → [push]
```

### 教學要點

- LangGraph 的 conditional edge 寫法（`add_conditional_edges` + 回傳 string key）
- 「資訊不足就誠實追問」比「強行生成」對使用者更有價值
- 兩階段生成的好處：JSON 骨架可被測試、可被審查；LLM 只負責語言表達
- 受限 prompt 的關鍵約束：「只能引用 contract 內列出的事實」

### 可換點 / 不可換點

| | 可換 | 不可換 |
|---|---|---|
| Sufficiency 判定門檻 | ✅ 例如最低 score、最少命中數 | ❌ 回傳 `"sufficient"` / `"insufficient"` 兩個 key |
| Answer Contract 段落 | ✅ 段落名稱與順序依領域調整 | ❌ 必須有 `citations` 欄位指向 retrieval atom |
| Clarification 風格 | ✅ 提問語氣、數量 | ❌ 必須產生「具體可回答的問題」而非空泛詢問 |

### 驗收標準

- 問一個知識庫沒有的問題 → 走 clarify 分支，回覆是「我需要再確認...」這類具體追問
- 問一個知識庫有的問題 → 回覆有清楚的段落結構，且每段都能對應到某個檢索到的 chunk
- Answer Contract 的 JSON 可獨立 dump 出來檢視（debug mode）

---

## Phase 4：LLM-as-Judge + Reflection 迴圈

**目標**：教學生 **self-correction loop**：模型對自己的回覆做結構化評分，分數不足時帶著評語重新生成。

### 規格與任務

| 項目 | 規格 | 任務 | 借鑑 |
|------|------|------|------|
| 4 軸結構化 Judge | [spec-17](../specs/spec-17-judge-reflection.md)（取代 spec-11）| [task-17](../tasks/task-17-judge-reflection.md) | project-destiny `src/destiny/judge.py` |
| Reflection 重生成迴圈 | [spec-17](../specs/spec-17-judge-reflection.md) | [task-17](../tasks/task-17-judge-reflection.md) | project-destiny ADR-008 |

### Graph 變化

```
[render_narrative] → [judge]
                       ├─ pass → [push]
                       └─ fail → [render_narrative]（帶 judge feedback，retry_count+1）
                                   （retry_count >= 1 強制 push）
```

### 教學要點

- 為什麼用「多軸結構化評分」優於「單一 0~1 分數」（borrowed from destiny）：
  - `groundedness` — 結論是否都有依據
  - `citation_fidelity` — 引用是否與來源一致
  - `format_completeness` — 段落是否齊全
  - `uncertainty_honesty` — 不確定處是否誠實標示
- LangGraph 的迴圈寫法（`add_conditional_edges` 回到上游 node）
- 為什麼**必須有 retry 上限**（避免無限迴圈、成本爆炸）

### 可換點 / 不可換點

| | 可換 | 不可換 |
|---|---|---|
| Judge 軸數與名稱 | ✅ 領域可加軸（例：醫療領域加 `safety`）| ❌ 必須回傳結構化 JSON |
| 通過門檻 | ✅ 各軸獨立或加權 | ❌ retry 上限必須 ≤ 2 |
| Judge 的 model | ✅ 可與 Generator 不同廠商（建議）| — |

### 驗收標準

- 強制觸發低分（例：刻意餵不足資料）→ log 顯示 `judge fail → retry`
- 正常品質回覆 → log 顯示 `judge pass`，不重生成
- judge LLM 失敗時 → fallback 直接送出原回覆，不 crash
- retry 上限到達後強制 push（永不無限迴圈）

---

## 教學完整性層（跨切面）

這三個 spec **不屬於 graph 主線**，但對應 `docs/RAG` 與 `docs/RAG/LangGraph` 既有教學章節，缺了等於沒講完。實作順序建議在對應主 phase 完成後立刻接上。

| 項目 | 規格 | 任務 | 對應教學章節 | 對應主 phase |
|------|------|------|-------------|-------------|
| Evaluation Framework | [spec-20](../specs/spec-20-evaluation.md) | [task-20](../tasks/task-20-evaluation.md) | `docs/RAG/ch06-evaluation.md` | P4 之後（需 reflection variant 才能跑 judge_pass_rate）|
| Persistence + Human-in-the-Loop | [spec-21](../specs/spec-21-persistence-hitl.md) | [task-21](../tasks/task-21-persistence-hitl.md) | `LangGraph/ch04-persistence.md`、`ch06 §3` | P4 之後（HITL 配 reflection）|
| Observability + Cost | [spec-22](../specs/spec-22-observability.md) | [task-22](../tasks/task-22-observability.md) | `LangGraph/ch10-production.md` | P1 之後即可開始；P3 / P4 完成後價值最高 |

### 為什麼這三個必補

| Spec | 沒它會發生什麼 |
|---|---|
| spec-20 evaluation | 學生轉題目後**無從驗證自己的 RAG 是否在工作**——教學最大缺口 |
| spec-21 persistence + HITL | LangGraph 三大殺手鐧之一（checkpoint / interrupt / resume）一字未提；ch04 整章承諾沒兌現 |
| spec-22 observability | 三變體 cost / latency 差異無法量化展示，「該用哪個」變成口頭主張 |

---

## 轉換可移植層（跨切面）

教學完整性層讓學生**能驗證**自己的 RAG，但若要把這個 bot 改造成「真正的專業 RAG 服務」（web UI / Slack / API、換 vector store、處理 PDF），會撞到 3 個結構性斷點。本層補上對應的 Adapter 介面與多格式 ingestion，並提供完整 transferability guide。

| 項目 | 規格 / 文件 | 任務 | 解的斷點 |
|------|------|------|------|
| Channel Adapter Layer | [spec-23](../specs/spec-23-channel-adapter.md) | [task-23](../tasks/task-23-channel-adapter.md) | LINE coupling 滲透 graph state |
| Knowledge Store Adapter | [spec-24](../specs/spec-24-knowledge-store-adapter.md) | [task-24](../tasks/task-24-knowledge-store-adapter.md) | Supabase RPC 寫死 |
| Multi-format Ingestion | [spec-25](../specs/spec-25-multi-format-ingestion.md) | [task-25](../tasks/task-25-multi-format-ingestion.md) | 只支援 Web crawler，缺 PDF / Notion / CSV |
| **Transferability Guide** | [doc-01](../guides/doc-01-transferability-guide.md) | —（doc，非 task）| 兌現「轉換 promise」的人類可讀證據 |

### 為什麼這層必補

| Spec | 沒它會發生什麼 |
|---|---|
| spec-23 | 學生想做 web RAG / Slack bot，要改 graph state、push、history、formatter 四處——roadmap 說「動 4 處」其實是 LINE-bound 假設 |
| spec-24 | 學生公司用自家 Postgres / Pinecone，retriever 整個重寫；離線教學 demo 必須開 Supabase 帳號 |
| spec-25 | PDF 是專業 RAG 必選（法規 / 醫療 / 學術），目前完全沒有 |
| doc-01 | spec 講「能不能換」，guide 講「實際怎麼換」——對學生最直接 |

---

## Phase 5（選修）：工程補完

完成 P1–P4 後 graph 主線就齊了。Phase 5 分兩梯次：

### 第一梯次（原有）

| 項目 | 規格 | 屬性 |
|------|------|------|
| Response Mode 差異化 | [spec-01](../specs/spec-01-response-mode.md) | Generator prompt 工程 |
| Emotion 應對策略 | [spec-02](../specs/spec-02-emotion-handling.md) | Router 後處理 |
| Heuristic Categories 同步 | [spec-03](../specs/spec-03-heuristic-sync.md) | 資料一致性 |
| Cross-encoder Rerank | [spec-04](../specs/spec-04-cross-encoder-rerank.md) | 檢索品質 |
| Prompt Cache | [spec-05](../specs/spec-05-prompt-cache.md) | 成本優化 |
| Knowledge Version 追蹤 | [spec-06](../specs/spec-06-knowledge-version.md) | 資料治理 |
| Notion Ingestion | [spec-07](../specs/spec-07-notion-ingestion.md) | 資料來源擴充 |
| Skill 熱更新 | [spec-08](../specs/spec-08-skill-hot-reload.md) | 維運便利 |
| Retrieval Log 分析 | [spec-09](../specs/spec-09-retrieval-analytics.md) | 觀測性 |

> ⚠️ 既有的 [spec-10 Self-RAG](../specs/spec-10-selfrag.md) 與 [spec-11 Reflection](../specs/spec-11-reflection.md) 已被取代並標記為 superseded：spec-10 → [spec-15 Sufficiency + Clarify](../specs/spec-15-sufficiency-clarify.md)（Self-RAG 的「query 改寫重試」改為偵測不足時向使用者澄清，避免幻覺）；spec-11 → [spec-17 Judge Reflection](../specs/spec-17-judge-reflection.md)（單一 reflection_score 升級為 4 軸結構化 Judge）。spec-10 / spec-11 文件保留作為設計演進記錄。

### 第二梯次：Advanced RAG 強化（spec-26–31）

**計畫總覽**：[advanced-rag-plan.md](./advanced-rag-plan.md)

本梯次補完六個 RAG 核心品質與生產安全性議題，不改變 graph 骨架，透過 env var 切換是否啟用：

| 項目 | 規格 | 任務 | 依賴 | 屬性 |
|------|------|------|------|------|
| 查詢轉換（HyDE / Step-Back / Decompose）| [spec-26](../specs/spec-26-query-transform.md) | [task-26](../tasks/task-26-query-transform.md) | P2 | 檢索品質 |
| 混合檢索曝光（BM25 + vector config）| [spec-27](../specs/spec-27-hybrid-retrieval.md) | [task-27](../tasks/task-27-hybrid-retrieval.md) | P1 | 檢索品質 |
| Cross-encoder Reranker（Cohere / BGE）| [spec-28](../specs/spec-28-reranker.md) | [task-28](../tasks/task-28-reranker.md) | spec-27 | 精排品質 |
| Embedding 模型選型 | [spec-29](../specs/spec-29-embedding-selection.md) | [task-29](../tasks/task-29-embedding-selection.md) | spec-20 | 基礎設施 |
| 安全性防禦（Injection / Poisoning / 洩漏）| [spec-30](../specs/spec-30-security.md) | [task-30](../tasks/task-30-security.md) | P3 | 生產安全 |
| 串流回應（HTTP SSE / LINE 占位訊息）| [spec-31](../specs/spec-31-streaming.md) | [task-31](../tasks/task-31-streaming.md) | P4 | 使用者體驗 |

建議施做順序：`spec-27 → spec-28 → spec-26 → spec-30 → spec-31 → spec-29`

---

## 給學生：轉換到自己的題目

完成 P0–P4 後，要把這個 bot 改成自己的題目，依目標分四個 Tier，詳見 **[doc-01 Transferability Guide](../guides/doc-01-transferability-guide.md)**：

| Tier | 換什麼 | 動的地方 | 預期工時 |
|---|---|---|---|
| **T1** | 換領域，留 LINE + Supabase | 4 處（skills / site_rules / 知識庫 / Feature Extractor）| 1–2 天 |
| **T2** | 加 web UI / API（多 channel） | + Channel Adapter（spec-23） | 1–2 天 |
| **T3** | 換 vector store / 加 PDF 與 Notion | + Store Adapter（spec-24）+ Multi-format（spec-25） | 2–3 天 |
| **T4** | 上線生產（HITL + observability + eval baseline） | + spec-20 / 21 / 22 | 3–5 天 |

> ⚠️ **誠實版承諾**：原版 roadmap 「只動 4 處」**只在 T1 成立**（LINE-bound + Supabase-bound 假設）。T2–T4 各需要一層 adapter spec 才能兌現。本專案 spec 已備齊，但學生需依目標選擇推進到哪個 Tier。

graph 骨架（route / multi-seed / fuse / sufficiency / two-stage / judge）**完全不動**。這是本專案教學設計的核心目的。

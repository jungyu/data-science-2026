# AI Agent 教學資源索引（Index）

> **第一次 fork 這個 repo？從這裡開始。**
>
> 本頁把 `docs/ai-agent/` 下的所有教學文件整理成一份導覽地圖。
> 按學習階段排列；每份文件後面有一句話說明「什麼時候該讀它」。

---

## 快速入口（3 步）

| 步驟 | 動作 | 讀這個 |
|---|---|---|
| 1 | 理解整體計畫 | [lesson-plan.md](plan/lesson-plan.md) |
| 2 | 開始 W1 | [crawl-recipe-nextjs.md](examples/crawl-recipe-nextjs.md) |
| 3 | 要交 W8 capstone | [capstone-spec.md](plan/capstone-spec.md) + [capstone-medical-distinction.md](examples/capstone-medical-distinction.md) |

---

## 1. 計畫文件（`plan/`）

這四份文件定義「你要去哪裡」——先讀 lesson-plan，其他按需查閱。

| 文件 | 一句話說明 |
|---|---|
| [lesson-plan.md](plan/lesson-plan.md) | 8 週進度表，每週任務、工時估算、Milestone artifact。**先讀這個。** |
| [capstone-spec.md](plan/capstone-spec.md) | W8 評分標準（100 分制）、必過門檻、自評檢查單。W8 前必讀。 |
| [lesson-plan-variants.md](plan/lesson-plan-variants.md) | 時程變體：1 週密集 / 16 週半學期 / 自學版。時間不是 8 週時讀。 |
| [roadmap.md](plan/roadmap.md) | 技術 phase 藍圖（P0–P4 + 跨切面）。想了解「為什麼這樣設計」時讀。 |

---

## 2. 可移植性指南（`guides/`）

這兩份文件是「換領域」的操作手冊。

| 文件 | 一句話說明 |
|---|---|
| [doc-01-transferability-guide.md](guides/doc-01-transferability-guide.md) | 換領域的 4-Tier 轉換矩陣，說明每 Tier 要動哪些檔、如何驗證。W1 完成後讀。 |
| [swap-diff-three-domains.md](guides/swap-diff-three-domains.md) | 醫療 / 法規 / 程式教學三領域完整 swap diff——含 SKILL.md、golden.yaml、參數表、預期 metric。換領域時直接複製貼用。 |

---

## 3. Specs + Tasks 對照表（W1–W7 核心任務）

> **Spec** = 設計文件（why + how）；**Task** = 驗收單（具體步驟 + 必交 artifact）。
> 每週先讀 Spec 理解設計，再按 Task 執行。

### Week 1：環境 + Graph 起步

| Spec | Task | 主題 |
|---|---|---|
| [spec-18](specs/spec-18-playwright-ingestion.md) | [task-18](tasks/task-18-playwright-ingestion.md) | Playwright 爬蟲抓 markdown，frontmatter 為入庫契約 |
| [spec-12](specs/spec-12-graph-refactor.md) | [task-12](tasks/task-12-graph-refactor.md) | 線性函式 → LangGraph 等價重構 |

### Week 2：Multi-seed 檢索

| Spec | Task | 主題 |
|---|---|---|
| [spec-13](specs/spec-13-feature-extractor.md) | [task-13](tasks/task-13-feature-extractor.md) | Feature Extractor：結構化 query 抽取 |
| [spec-14](specs/spec-14-multi-seed-retrieval.md) | [task-14](tasks/task-14-multi-seed-retrieval.md) | Multi-seed fan-out + RRF fusion |

### Week 3：Sufficiency + Grounded Generation

| Spec | Task | 主題 |
|---|---|---|
| [spec-15](specs/spec-15-sufficiency-clarify.md) | [task-15](tasks/task-15-sufficiency-clarify.md) | Sufficiency 三規則：沒資料時誠實追問 |
| [spec-16](specs/spec-16-two-stage-generator.md) | [task-16](tasks/task-16-two-stage-generator.md) | Two-stage generator：Contract（程式）+ Narrative（LLM）|

### Week 4：Self-Correction 迴圈

| Spec | Task | 主題 |
|---|---|---|
| [spec-17](specs/spec-17-judge-reflection.md) | [task-17](tasks/task-17-judge-reflection.md) | 4 軸 Judge + retry 迴圈（reflection variant）|
| [spec-19](specs/spec-19-graph-variants.md) | [task-19](tasks/task-19-graph-variants.md) | 三變體並陳（basic / selfrag / reflection）|

### Week 5：量化驗證 + 觀測

| Spec | Task | 主題 |
|---|---|---|
| [spec-20](specs/spec-20-evaluation.md) | [task-20](tasks/task-20-evaluation.md) | Golden case set + 6 metric eval pipeline |
| [spec-22](specs/spec-22-observability.md) | [task-22](tasks/task-22-observability.md) | Trace + cost 觀測，ContextVar dispatch |

### Week 6：多 Channel + 多 Store

| Spec | Task | 主題 |
|---|---|---|
| [spec-23](specs/spec-23-channel-adapter.md) | [task-23](tasks/task-23-channel-adapter.md) | Channel Adapter Protocol（LINE / Web / Stub）|
| [spec-24](specs/spec-24-knowledge-store-adapter.md) | [task-24](tasks/task-24-knowledge-store-adapter.md) | Store Adapter（Supabase / sqlite-vec / Pinecone）|

### Week 7：多格式資料 + HITL

| Spec | Task | 主題 |
|---|---|---|
| [spec-25](specs/spec-25-multi-format-ingestion.md) | [task-25](tasks/task-25-multi-format-ingestion.md) | PDF / CSV / Notion 多格式 ingestion + page_number citation |
| [spec-21](specs/spec-21-persistence-hitl.md) | [task-21](tasks/task-21-persistence-hitl.md) | LangGraph interrupt / checkpointer / HITL review queue |

### 既有 specs（P0–P1 基礎層，不在週進度中）

> 這些是架構基礎，不屬於週任務但可按需查閱：

| Spec / Task | 主題 |
|---|---|
| spec/task 01–03 | 回覆模式、情緒處理、啟發式同步 |
| spec/task 04–06 | 跨編碼器 rerank、prompt cache、知識版本 |
| spec/task 07–09 | Notion ingestion、skill hot-reload、retrieval analytics |
| spec/task 10–11 | Self-RAG（精簡版）、初版 reflection |

### Advanced RAG 強化梯次（W1–W7 完成後選修）

> 計畫總覽：[advanced-rag-plan.md](plan/advanced-rag-plan.md)。
> 全部以 env var 切換是否啟用，預設 OFF；行為與 W7 完成後完全一致。

| Spec | Task | 主題 |
|---|---|---|
| [spec-26](specs/spec-26-query-transform.md) | [task-26](tasks/task-26-query-transform.md) | 查詢轉換（HyDE / Step-Back / Decompose）|
| [spec-27](specs/spec-27-hybrid-retrieval.md) | [task-27](tasks/task-27-hybrid-retrieval.md) | 混合檢索曝光（BM25 + vector 權重 config）|
| [spec-28](specs/spec-28-reranker.md) | [task-28](tasks/task-28-reranker.md) | Cross-encoder Reranker（Cohere / BGE）|
| [spec-29](specs/spec-29-embedding-selection.md) | [task-29](tasks/task-29-embedding-selection.md) | Embedding 模型選型（含 HuggingFace 本地嵌入）|
| [spec-30](specs/spec-30-security.md) | [task-30](tasks/task-30-security.md) | 安全防禦（Prompt Injection / RAG Poisoning / PII redact）|
| [spec-31](specs/spec-31-streaming.md) | [task-31](tasks/task-31-streaming.md) | 串流回應（HTTP SSE 真 token streaming + LINE 占位訊息）|

---

## 4. 範例與走查（`examples/`）

按使用情境分類：

### 上手示範

| 文件 | 使用時機 |
|---|---|
| [crawl-recipe-nextjs.md](examples/crawl-recipe-nextjs.md) | W1：照做一遍 Playwright 爬蟲 + ingest 流程 |
| [w1-demo-script.md](examples/w1-demo-script.md) | W1 結束時的 demo 腳本；格式是 W8 demo 的基礎 |
| [w1-e2e-verification.md](examples/w1-e2e-verification.md) | W1 驗收：四個常見摩擦點（category 對齊、跨語言、router 非確定、URL alias）|

### 系統行為驗收

| 文件 | 使用時機 |
|---|---|
| [w2-w8-e2e-verification.md](examples/w2-w8-e2e-verification.md) | W2–W8 整合驗收腳本（含所有主要功能的 smoke test）|
| [variants-comparison.md](examples/variants-comparison.md) | 三變體（basic / selfrag / reflection）在不同問題上的實際輸出對比 |

### 圖形結構參考

| 文件 | 使用時機 |
|---|---|
| [graph-basic.mermaid](examples/graph-basic.mermaid) | basic variant 的 LangGraph 拓撲 |
| [graph-selfrag.mermaid](examples/graph-selfrag.mermaid) | selfrag variant（含 fan-out / sufficiency）|
| [graph-reflection.mermaid](examples/graph-reflection.mermaid) | reflection variant（含 judge / retry / human_review）|

### Ingestion 走查

| 文件 | 使用時機 |
|---|---|
| [ingest-pdf-walkthrough.md](examples/ingest-pdf-walkthrough.md) | W7：PDF 帶 page_number 流到 narrative citation 的完整流程 |
| [ingest-csv-walkthrough.md](examples/ingest-csv-walkthrough.md) | W7：CSV 逐列 ingest，metadata filter 對齊 skill |

### 領域移植

| 文件 | 使用時機 |
|---|---|
| [feature-extractor-medical.md](examples/feature-extractor-medical.md) | 醫療領域 rule-based + hybrid feature extractor 完整實作骨架 |
| [hitl-walkthrough.md](examples/hitl-walkthrough.md) | HITL approve / revise / drop 三條路徑 step-by-step |

### 評量範本

| 文件 | 使用時機 |
|---|---|
| [eval-baseline.md](examples/eval-baseline.md) | W5 必交 artifact 的格式範本（含空白欄位，學生填入真實數字）|
| **[capstone-medical-distinction.md](examples/capstone-medical-distinction.md)** | **W8 Distinction tier 示範——完整跑完的醫療領域 capstone（107/110）** |

---

## 5. 架構決策記錄（`../../adr/`）

| 文件 | 決策摘要 |
|---|---|
| [ADR-001](../adr/ADR-001-line-bot-interface.md) | 為什麼選 LINE Bot 作為主要 interface |
| [ADR-002](../adr/ADR-002-supabase-pgvector-rag.md) | 為什麼選 Supabase pgvector 作為預設 KB |
| [ADR-003](../adr/ADR-003-skill-based-router.md) | Skill-based router 的設計理由 |
| [ADR-004](../adr/ADR-004-hybrid-search-and-rrf.md) | 混合搜索 + RRF fusion 的取捨 |
| [ADR-005](../adr/ADR-005-stateless-role-switching.md) | 無狀態 role switching 設計 |
| [ADR-006](../adr/ADR-006-no-mcp-server-for-mvp.md) | MVP 不做 MCP server 的理由 |

---

## 6. RAG 理論課（`../../RAG/`）

> 這些是「課本」，不是操作文件。卡住時或想理解「為什麼」時翻閱。

### RAG 基礎（`docs/RAG/`）

| 文件 | 主題 |
|---|---|
| [ch01-why-rag.md](../RAG/ch01-why-rag.md) | RAG 動機：為什麼不直接 fine-tune |
| [ch02-etl-chunking.md](../RAG/ch02-etl-chunking.md) | ETL pipeline + chunking 策略 |
| [ch03-vectors-embeddings.md](../RAG/ch03-vectors-embeddings.md) | 向量 + embedding 工作原理 |
| [ch04-llamaindex.md](../RAG/ch04-llamaindex.md) | LlamaIndex 對照參考 |
| [ch05-agentic-rag.md](../RAG/ch05-agentic-rag.md) | Agentic RAG：為什麼需要 graph |
| [ch06-evaluation.md](../RAG/ch06-evaluation.md) | RAG 評估指標全覽 |
| [module-pre-a-crawler.md](../RAG/module-pre-a-crawler.md) | Playwright crawler 原理 |
| [module-a-mcp-server.md](../RAG/module-a-mcp-server.md) | 選修：MCP server 整合 |
| [module-b-dashboard.md](../RAG/module-b-dashboard.md) | 選修：觀測 dashboard |

### LangGraph 深入（`docs/RAG/LangGraph/`）

| 文件 | 主題 |
|---|---|
| [ch01-why-langgraph.md](../RAG/LangGraph/ch01-why-langgraph.md) | 為什麼需要 LangGraph（vs 線性 chain）|
| [ch02-stategraph.md](../RAG/LangGraph/ch02-stategraph.md) | StateGraph / TypedDict / node / edge 四基本 |
| [ch03-conditional-edges.md](../RAG/LangGraph/ch03-conditional-edges.md) | Conditional edges（三向路由）|
| [ch04-persistence.md](../RAG/LangGraph/ch04-persistence.md) | checkpointer 持久化 + thread_id |
| [ch05-agent-loop.md](../RAG/LangGraph/ch05-agent-loop.md) | Agent loop 設計（含 retry 上限保險）|
| [ch06-rag-vs-selfrag-vs-reflection.md](../RAG/LangGraph/ch06-rag-vs-selfrag-vs-reflection.md) | **三變體選擇指南**（哪個場景用哪個）|
| [ch07-state-schema.md](../RAG/LangGraph/ch07-state-schema.md) | State schema 設計原則 |
| [ch08-reflection-node.md](../RAG/LangGraph/ch08-reflection-node.md) | Reflection node 實作細節 |
| [ch09-langgraph-in-action.md](../RAG/LangGraph/ch09-langgraph-in-action.md) | 端對端整合範例 |
| [ch10-production.md](../RAG/LangGraph/ch10-production.md) | 生產就緒 checklist |

---

## 7. 其他操作文件

| 文件 | 說明 |
|---|---|
| [docs/setup.md](../setup.md) | 環境設定（env / DB / ngrok）|
| [docs/tunnel.md](../tunnel.md) | LINE webhook + ngrok 通道設定 |
| [docs/user-manual.md](../user-manual.md) | 使用者操作手冊（可直接給 end user）|
| [docs/QA.md](../QA.md) | 常見問題 Q&A |
| [AGENTS.md](../../AGENTS.md) | 給 AI Agent（Claude Code 等）的協作指引 |

---

## 資源總覽快速計數

| 類型 | 數量 | 位置 |
|---|---|---|
| 計畫文件 | 4 | `plan/` |
| 可移植性指南 | 2 | `guides/` |
| Spec 文件 | 31 | `specs/` |
| Task 文件 | 31 | `tasks/` |
| 範例 / 走查 | 14 | `examples/` |
| ADR | 6 | `../../adr/` |
| RAG 理論 | 19 | `../../RAG/` |
| 操作文件 | 5 | `../../` |
| **合計** | **112** | |

---

*本索引在每次新增文件後應同步更新。Pull request 新增 `docs/ai-agent/` 文件時，請同步在對應分類加一行。*

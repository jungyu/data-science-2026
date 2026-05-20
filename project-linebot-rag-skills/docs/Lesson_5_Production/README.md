# Lesson 5：Production 化 — 從 Reflection Agent 跑成 24/7 服務

> **時間**：約 12–16 小時（含本地跑通與部署設定）

## 先修：Lesson 1–4 + RAG/LangGraph 概念章

| 前置條件 | 說明 |
|----------|------|
| ✅ Supabase 已能跑、示範 KB 已入庫 | [Lesson 1](../Lesson_1_Supabase_Vector_db/README.md) |
| ✅ 自己領域的 KB 與 skill 已上線 | [Lesson 4](../Lesson_4_Build_Yours/README.md) |
| ✅ 讀完 LangGraph 概念 10 章 | [docs/RAG/LangGraph/](../RAG/LangGraph/README.md) |
| ✅ `selfrag` 與 `reflection` variant 跑通 | [Lesson 3](../Lesson_3_LangGraph_RAG/README.md) |

Lesson 5 假設你已理解 graph 概念與基礎實作；本課只談「從 demo 到 production」需要補的工程細節，**全部以 [`app/`](../../app/) 真實程式為例**。

---

```
╔══════════════════════════════════════════════════════════╗
║  你會做到：                                              ║
║  ✅ Supabase schema、HNSW 索引、Hybrid RPC 全部親手套用 ║
║  ✅ 從 channel webhook 一路追到 LLM provider 的每一節點 ║
║  ✅ Judge 失敗、LLM timeout、cache miss 都有降級路徑     ║
║  ✅ 觀測 / 安全 / 成本三道防線各自獨立、可獨立 disable  ║
║  ✅ 部署前 smoke test 清單跑完才上線                     ║
╚══════════════════════════════════════════════════════════╝
```

## 本課與 Lesson 4 的差別

| 維度 | Lesson 4 | Lesson 5 |
|------|----------|----------|
| 目的 | 換領域（KB / skill / channel） | 上 production |
| 改動範圍 | 4 個替換點 | 跨資料層、graph、observability、安全、部署 |
| 主軸 | 「你的領域 bot 能跑」 | 「失敗時系統能自救、能稽核、能算成本」 |
| 工具 | site_rules、skills、feature_extractor | psql、Supabase CLI、tracer、judge、checkpoint |

---

## 章節地圖

每章對應 [`app/`](../../app/) 一個（或一組）模組，讀完整章你的系統會多一層 production 能力：

| 章 | 主題 | 讀完能做到 | 對應 app/ 模組 |
|----|------|-----------|----------------|
| [Ch 01](ch01-supabase-schema.md) | **Supabase Schema 與向量索引** | 親手套用 schema.sql / functions.sql / observability_schema.sql / seed.sql；理解 HNSW 與 hybrid RPC | `storage/supabase_client.py` + [`supabase/*.sql`](../../supabase/) |
| [Ch 02](ch02-repo-pattern.md) | **Repo Pattern 與 DB 實務操作** | 用 Repo 層讀寫；knowledge_version 失效流程；migration 策略 | [`app/storage/*_repo.py`](../../app/storage/) |
| [Ch 03](ch03-channel-webhook.md) | **Channel 抽象與 LINE Webhook** | 接 LINE / HTTP / Stub 三入口共用同一個 graph | [`app/channels/`](../../app/channels/) + [`app/line/`](../../app/line/) |
| [Ch 04](ch04-router-skills.md) | **Intent Router 與 Skills 註冊** | LLM 分流 + heuristic fallback + DB-driven skills | [`app/router/`](../../app/router/) + [`app/skills/`](../../app/skills/) + [`app/ai/factory.py`](../../app/ai/factory.py) |
| [Ch 05](ch05-query-understanding.md) | **Query 理解：Feature Extraction + Query Transform** | 把 user_input 拆成結構化 features，HyDE / Step-back / Decompose 三策略 | [`app/graph/feature_extractor.py`](../../app/graph/feature_extractor.py) + [`query_transform.py`](../../app/graph/query_transform.py) |
| [Ch 06](ch06-multi-seed-retrieval.md) | **Multi-seed Retrieval + Fusion + Rerank** | 並行 fan-out 檢索；max/mean/RRF fusion；reranker graceful degrade | [`app/graph/seed_expander.py`](../../app/graph/seed_expander.py) + [`app/rag/`](../../app/rag/) |
| [Ch 07](ch07-sufficiency-generation.md) | **Sufficiency + Clarifier + 兩階段生成** | 不夠就追問；contract 純程式組、narrative 受限 LLM | [`app/graph/sufficiency.py`](../../app/graph/sufficiency.py) + [`clarifier.py`](../../app/graph/clarifier.py) + [`app/generator/`](../../app/generator/) |
| [Ch 08](ch08-judge-hitl.md) | **Judge + Reflection 迴圈 + HITL** | 4 軸評分 + retry 上限 + 人工審核 interrupt | [`app/judge/`](../../app/judge/) + [`app/graph/variants/reflection.py`](../../app/graph/variants/reflection.py) |
| [Ch 09](ch09-observability-security.md) | **觀測（Tracer + Logger + Pricing）+ 安全 Guards** | ContextVar tracer、JSON log、token cost、injection 防禦 | [`app/observability/`](../../app/observability/) + [`app/security/`](../../app/security/) |
| [Ch 10](ch10-deployment-pitfalls.md) | **Checkpoint / Cache / 成本 / 部署清單 / 地雷集** | 三後端 checkpoint、prompt cache 失效、budget 斷路、12 條地雷 | [`app/graph/checkpoint.py`](../../app/graph/checkpoint.py) + [`app/storage/cache_repo.py`](../../app/storage/cache_repo.py) |

---

## 三條學習軌跡

不一定要從 Ch 01 線性讀。依你目前要解決的問題挑：

### 軌跡 A：資料層改造（Ch 01 → Ch 02 → Ch 10 §cache）
你已經有 graph 在跑，但想把資料層升級成 HNSW + hybrid + cache。

### 軌跡 B：pipeline 升級（Ch 05 → Ch 06 → Ch 07 → Ch 08）
你的 basic variant 跑得起來，要升級到 selfrag → reflection。

### 軌跡 C：上線前最後一哩（Ch 09 → Ch 10）
功能都齊了，要補觀測、安全、cost、checkpoint、deployment。

---

## 三個 Graph Variant：你目前在哪一層？

本課所有章節都會標註「**這節對哪個 variant 必要**」：

| 章節 | basic | selfrag | reflection |
|------|:-----:|:-------:|:----------:|
| Ch 01-02（資料層）| ✅ | ✅ | ✅ |
| Ch 03-04（channel + router）| ✅ | ✅ | ✅ |
| Ch 05（feature + transform）| — | ✅ | ✅ |
| Ch 06（multi-seed retrieval）| 部份 | ✅ | ✅ |
| Ch 07（sufficiency + 兩階段生成）| — | ✅ | ✅ |
| Ch 08（judge + HITL）| — | — | ✅ |
| Ch 09（觀測 + 安全）| ✅ | ✅ | ✅ |
| Ch 10（checkpoint / cache / 部署）| ✅ | ✅ | ✅ |

切換靠環境變數 `GRAPH_VARIANT=basic|selfrag|reflection`，三個 variant **共用同一份 state、checkpointer、retriever**——這也是 LangGraph 在工程上很值錢的設計：升級 variant 不用重寫資料層，你可以從本課任何一章開始切入。

---

## 驗收：Production smoke test

每章末尾都有 **🎯 本章驗收** 區塊，類似 Lesson 4 的 eval gate，但形式更偏「smoke test」——例如：

- **Ch 01 驗收**：`psql -f schema.sql` 套用後，能用 `match_private_knowledge` RPC 撈回至少一筆 chunk
- **Ch 06 驗收**：multi-seed retrieve trace 中能看到 ≥ 2 個 seed 並行，fusion 後分數 monotonic
- **Ch 08 驗收**：故意餵一個 ungrounded 草稿，judge 能正確走 retry → mark_warning 路徑

跑完 10 章驗收，你的系統就具備 production 該有的 self-healing、observability、cost-awareness。

---

## 進階閱讀

- [docs/specs/](../specs/README.md)：本專案各 spec 的設計決策（spec-05 cache、spec-17 reflection、spec-22 telemetry、spec-26 query transform、spec-27 hybrid、spec-30 guards、spec-31 streaming）
- [docs/adr/](../adr/README.md)：架構決策紀錄
- [docs/RAG/LangGraph/](../RAG/LangGraph/README.md)：LangGraph 概念 10 章（如果忘了某個原理）

> 「If your agent can't tell you why it failed, it's not production.」

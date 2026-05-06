# Doc-01：轉換到自己領域的 RAG 服務（Transferability Guide）

> 給已完成 P0–P4 + spec-23 / 24 / 25 的學生：把這個 LINE bot 改造成「自己領域的專業 RAG 服務」，逐步、可驗證、有比較基準。

## 背景

[`roadmap.md §給學生`](../plan/roadmap.md) 承諾「轉換只動 4 處」，但**前提**是學生留在 LINE + Supabase 軌道、只換領域。一旦要做專業服務（web UI / Slack / API、換 vector store、處理 PDF），需要動的地方更多。

本 guide 把轉換過程拆成 **4 個 Tier**，每 Tier 對應不同的「斷點等級」，學生依自己需求逐 tier 推進，不必一次全做。每 tier 都帶 3 個具體領域範例（**醫療助理 / 法規問答 / 程式教學**），可當作模板。

借鑑：本 guide 設計風格參考 [`docs/RAG/LangGraph/ch10-production.md`](../../RAG/LangGraph/ch10-production.md) 的 production checklist 思路；範例選擇對齊 [`ch06-rag-vs-selfrag-vs-reflection.md`](../../RAG/LangGraph/ch06-rag-vs-selfrag-vs-reflection.md) 對「高風險領域」的建議。

## 設計

### 4 Tier 轉換矩陣

| Tier | 換什麼 | 必動的檔 | 預期工時 | 對應 spec |
|---|---|---|---|---|
| **T1** | 換領域，留 LINE + Supabase | 4 處 | 1–2 天 | 既有 P0–P4 |
| **T2** | 加 web UI / API（多 channel） | + Channel Adapter | 1–2 天 | spec-23 |
| **T3** | 換 vector store / 加 PDF 與 Notion | + Store Adapter + Multi-format Ingestion | 2–3 天 | spec-24, spec-25 |
| **T4** | 上線生產（HITL、observability、eval baseline） | + Persistence、Trace、Eval | 3–5 天 | spec-20, spec-21, spec-22 |

T1 是必經之路；T2–T4 看學生最終目標選用。

### Tier 1：換領域（留 LINE + Supabase）

**動 4 處**：

1. **`skills/`** — 替換領域特定 SKILL.md
2. **`scripts/site_rules.py`** — 加上自己領域目標站的 selector（若用 Web 來源）
3. **知識庫** — `scripts/crawl_to_markdown.py` + `scripts/ingest.py` 入庫
4. **Feature Extractor** — 子類化 `LLMFeatureExtractor` 或實作 `RuleBasedFeatureExtractor`

**驗證手段**：spec-20 的 `tests/cases/golden.yaml` 換成自己領域案例，跑 `scripts/eval.py` 看三變體 metric。

**三領域範例 swap diff**：完整可貼用 reference（含 SKILL.md 模板、golden.yaml 範例、參數調整表、Judge 加軸建議、HITL 觸發條件）見 [swap-diff-three-domains.md](./swap-diff-three-domains.md)。

| 改動 | 醫療助理 | 法規問答 | 程式教學 |
|---|---|---|---|
| skills 加 | `triage`, `med_qa`, `reassurance` | `regulation_lookup`, `precedent_search` | `code_review`, `concept_explain`, `debug_help` |
| Feature Extractor primary_topic 範例 | `"夜間咳嗽"` | `"勞動基準法 §32"` | `"hydration mismatch"` |
| Feature Extractor entities 範例 | 藥名、症狀 | 條號、判決字號 | 套件名、版本 |
| Judge 必加軸 | `safety`（避免診斷）| `legal_accuracy` | （無；4 軸足夠）|
| Sufficiency `min_top_score` | 0.55（高風險，寧缺勿濫）| 0.50 | 0.40 |

### Tier 2：加 web UI / API

**前置**：完成 spec-23 channel adapter

**動的檔**：

1. `app/channels/` 加新 adapter（或直接用既有 `HttpChannel`）
2. 寫前端（不在本專案範圍，但 `/api/chat` 已經是標準 endpoint）

**驗證手段**：
- 同一個 query 在 LINE 與 web 兩 channel 跑，回覆語意一致
- spec-22 trace JSON 兩 channel 都有紀錄

**三領域範例**：

| 領域 | Web UI 重點 |
|---|---|
| 醫療助理 | 多輪追問展開（追問 → 補充 → 再問），需要 spec-27 multi-turn session |
| 法規問答 | 引用條文需可點擊，`Citation.source` 在前端 render 為超連結 |
| 程式教學 | code block 用 syntax highlighting，markdown 完整顯示（不切段）|

### Tier 3：換 store / 處理 PDF + Notion

**前置**：完成 spec-24 store adapter、spec-25 multi-format ingestion

**動的檔**：

1. `KNOWLEDGE_STORE_BACKEND` env var 切換
2. `python scripts/ingest.py pdf|notion|csv` 取代或補充 web ingester
3. （選）為新格式擴充 `app/ingest/chunkers.py`

**驗證手段**：spec-20 eval 在新 store / 新格式上重跑，metric 落點符合預期：

| 改動 | 預期 metric 變化 |
|---|---|
| Supabase → sqlite_vec | chunk_recall 略降（無 hybrid）；latency 大降 |
| 加 PDF 內容 | chunk 總數增加；新 query 在 PDF 案例上 recall 應 > 0.6 |
| 加 Notion 內容 | metadata 帶 Notion `page_id`，可追溯 |

**三領域範例**：

| 領域 | 主資料來源 |
|---|---|
| 醫療助理 | 衛福部公告 PDF + 藥廠仿單（PDF）+ 內部 SOP（Notion）|
| 法規問答 | 法規資料庫 PDF + 大法官判決書 PDF + FAQ CSV |
| 程式教學 | 官方 docs（Web）+ 內部 best practices（Notion）+ 常見錯誤表（CSV）|

### Tier 4：上線生產

**前置**：完成 spec-20 / 21 / 22

**最低標準**：

- [ ] **eval baseline** 已確立（`tests/cases/golden.yaml` ≥30 案例，三變體 metric 紀錄）
- [ ] **HITL 路徑** 啟用（`HITL_ENABLED=true`），高風險領域必開
- [ ] **observability** 啟用（trace JSON + 結構化 log）
- [ ] **persistence** 啟用 PostgresSaver（共用 Supabase）
- [ ] **safety gate**（reflection variant 強制；judge 軸含領域 safety axis）
- [ ] **rate limiting**（per user_id / per minute；本專案不提供，需自加 middleware）
- [ ] **cost dashboard**（spec-22 的 trace summary 跑 cron 每日）

**三領域範例**：

| 領域 | 必加的 HITL 觸發條件 |
|---|---|
| 醫療助理 | `judge.safety < 7` 或 `intent == "decide"`（涉及就醫決策）|
| 法規問答 | `intent == "decide"`（涉及訴訟 / 訂約建議）|
| 程式教學 | （非必要；`reflection_retry >= 1` 即可）|

## 介面契約（學生產出物）

完成轉換時，學生**至少**應產出以下檔案 / artifacts：

| Artifact | 內容 | Tier |
|---|---|---|
| `skills/<domain>/*.md` | 自己領域的 skill 定義 | T1 |
| `scripts/site_rules.py` 或 `app/ingest/site_rules.py` | 領域目標站 selector | T1 |
| `app/graph/feature_extractors/<domain>.py` | 子類化或新實作 | T1 |
| `tests/cases/golden.yaml`（替換）| 領域 golden case ≥10 | T1 必交 |
| `docs/eval-baseline.md` | T1 結束時三變體 metric 表 | T1 必交 |
| `docs/swap-store-decision.md`（若 T3）| 為何選某個 store + benchmark | T3 |
| `docs/safety-cases.md`（若領域屬高風險）| HITL 觸發案例集 | T4 |
| `docs/cost-budget.md`（若進 T4）| 每月預算估算 + 監控規劃 | T4 |

每個 Tier 結束時，這些 artifact 都應在 PR / commit 中可見，作為「promise 兌現」的可審計證據。

### 學生 fork 時的最小 checklist

```markdown
- [ ] T1.1 替換 skills/
- [ ] T1.2 知識庫已 ingest（≥50 chunks）
- [ ] T1.3 Feature Extractor 已客製
- [ ] T1.4 golden.yaml ≥10 案例
- [ ] T1.5 eval-baseline.md：三變體 metric 表
（如要 web）
- [ ] T2.1 /api/chat 可用
- [ ] T2.2 LINE + web 雙 channel 同 query 一致性測試通過
（如要 PDF / Notion）
- [ ] T3.1 ≥1 個非 web 來源已 ingest
- [ ] T3.2 重跑 eval，metric 不退步
（如要上線）
- [ ] T4.1 HITL 啟用 + 走過 ≥3 個 review 案例
- [ ] T4.2 每日 trace summary 已可看
```

## 驗收（兌現「promise 成立」的判準）

- 一個學生**只跟著本 guide 推 T1**，能在 1–2 天內：拿到自己領域 ≥10 個 golden case 的 baseline metric，並能在 PR 中展示「比 mainline 領域 metric 退步多少 / 進步多少」
- 一個學生**完成 T1 + T2**，能在 1 週內把 bot 部署成有 web UI 的 demo（LINE 仍可用）
- 一個學生**完成 T1 + T3**，能在 1 週內把 ≥1 個 PDF 來源納入知識庫，並對 PDF 內容的問題給出帶 `page_number` 的 citation
- 一個學生**完成全部 T1 + T2 + T3 + T4**，能在 2 週內交出「可上線的小型專業 RAG」，含 eval baseline、observability 截圖、HITL 走過的案例集
- 三個範例領域（醫療 / 法規 / 程式）的 T1 swap diff 表都能被學生**直接複製作為自己領域的起點**
- guide 中所有指令都對應**真實存在的 spec / script**——讀到的學生不會撞到「找不到那個檔」的死路（用 grep 驗證連結有效）

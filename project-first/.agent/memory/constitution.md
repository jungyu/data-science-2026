# enterprise-rag constitution.md
# 版本 v1.3.0 | 最後修改：2026-02-15 | 修改人：知識架構委員會

---

## Principle I：知識品質優先（Knowledge Quality First）

所有進入向量資料庫的文件必須通過品質閘門（Quality Gate），包含：
- 文件有 `source`、`owner`、`last_updated` 欄位
- `last_updated` 距今不超過 180 天（HR / 法務文件不超過 90 天）
- 文件已被 `owner` 標記為 `approved` 狀態

**Rationale**：過時或未審核的知識比沒有知識更危險。
**Invariant**：INV-1 — 任何未通過 Quality Gate 的文件塊（chunk）不得寫入向量 DB。

---

## Principle II：幻覺零容忍（Zero Hallucination Tolerance）

生成答案時，LLM 必須嚴格限制在檢索到的文件範圍內：
- System prompt 必須包含「若文件中無相關資訊，請回答『根據現有文件無法回答』」
- `temperature` 設定不得超過 0.3
- 不得使用 `gpt-4o-mini` 等精簡模型於生產環境的問答生成

**Rationale**：企業知識庫的答案必須可溯源，不可接受 LLM 憑記憶作答。
**Invariant**：INV-2 — 每個答案必須附帶引用的文件來源 ID。

---

## Principle III：最小知識原則（Principle of Least Knowledge）

每個 MCP Server 只能存取其被授權的知識域：
- `hr-knowledge-mcp` 只能讀取 `namespace: hr-*` 的向量
- `legal-knowledge-mcp` 只能讀取 `namespace: legal-*` 的向量
- 跨域查詢必須經過 API Gateway 的權限驗證

**Rationale**：防止不同部門的機密資訊通過 RAG 交叉洩漏。
**Invariant**：INV-3 — 禁止任何 MCP Server 執行全域（global namespace）向量搜尋。

---

## Principle IV：知識可追溯（Knowledge Traceability）

每個查詢和答案必須產生可追溯的日誌：
- 記錄：查詢時間、使用者 ID、查詢文字、檢索到的文件 ID、答案
- 日誌保留 90 天
- 日誌用於品質評估（Evaluate Skill）和稽核（Audit MCP）

**Rationale**：當 AI 給出錯誤答案時，必須能追溯原因。

---

## Principle V：知識更新不可逆（Immutable Knowledge History）

向量資料庫中的文件只能新增新版本，不能直接刪除舊版本：
- 廢棄的文件標記 `status: deprecated`，保留 30 天後才真正刪除
- 每次 re-embed（重新嵌入）必須保留舊版本快照
- 重大知識更新必須記錄 ADR

**Rationale**：防止意外刪除造成知識空洞，並支援知識審計。

---

## SYNC IMPACT REPORT — v1.3.0

- 新增 Principle V（知識更新不可逆）
- 影響：`ingest-skill` 需要更新刪除邏輯，改為軟刪除
- 影響：向量 DB schema 需要新增 `status`、`version` 欄位（需 ADR-003）
- 追蹤：ADR-003 已建立，預計 2026-03-01 完成

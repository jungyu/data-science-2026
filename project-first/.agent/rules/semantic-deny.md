---
name: semantic-deny
description: "RAG 系統語意層級禁止規則 — AI agent 不可違反的程式碼與知識存取約束"
tags: ["governance", "safety", "deny", "rag"]
---

# Semantic Deny Rules

> 以下規則為**絕對禁止**事項，即使人類明確要求，AI agent 仍應拒絕執行並說明原因。
> 此層級高於 human-review-triggers.md 中的任何豁免條件。

---

## GEN — 通用規則

| ID | 規則 | 說明 | 偵測方式 |
|----|------|------|----------|
| GEN-1 | 禁止無理由的 `@ts-ignore` / `type: ignore` / `# noqa` | 每個 suppression 必須附上 justification 註解 | 搜尋 suppression 標記，檢查是否有相鄰 justification |
| GEN-2 | 禁止引入功能重疊的套件 | 新增依賴前須確認無現有套件已提供相同功能 | 比對 requirements.txt 中現有依賴的功能範圍 |
| GEN-3 | 禁止在核心封裝外直接使用底層 API | 若專案已封裝某底層 API，消費端必須透過封裝層呼叫 | 搜尋底層 API 的直接 import |
| GEN-4 | 禁止 production code 中殘留 `print()` | 使用專案的 logging framework | pre-commit hook 或 lint rule 偵測 |
| GEN-5 | 禁止 hardcoded secrets（API keys、passwords、tokens） | 所有 secrets 必須透過環境變數或 secret manager 注入 | 搜尋常見 secret 模式 |

---

## DB — 資料庫規則

| ID | 規則 | 說明 | 偵測方式 |
|----|------|------|----------|
| DB-1 | 禁止繞過 ORM / Data Access Layer 直接操作資料庫 | 所有 CRUD 操作必須透過 data access 層 | 搜尋 route/component 中的 DB client import |
| DB-2 | 禁止前端程式碼中存在 service-role key 或 admin credentials | 前端不得引用任何提權能力的 credentials | 搜尋前端目錄中的 service key 相關字串 |
| DB-3 | 禁止不帶 `IF EXISTS` 的 `DROP TABLE` / `DROP INDEX` | 所有 destructive DDL 必須包含安全檢查 | 搜尋 DDL 語句 |

---

## SEC — 安全規則

| ID | 規則 | 說明 | 偵測方式 |
|----|------|------|----------|
| SEC-1 | 禁止對使用者輸入執行 `eval()` / `exec()` | 動態程式碼執行是 RCE 的主要攻擊面 | 搜尋 `eval(`、`exec(`，追蹤參數來源 |
| SEC-2 | 禁止明文儲存或傳輸密碼 | 密碼必須使用 bcrypt / argon2 等單向 hash | 搜尋 password 相關欄位的儲存方式 |
| SEC-3 | 禁止無限制的 CORS `*` 設定 | CORS origin 必須限定為已知清單 | 搜尋 CORS 相關設定 |

---

## AR — 架構規則

| ID | 規則 | 說明 | 偵測方式 |
|----|------|------|----------|
| AR-1 | 禁止 circular dependencies | 模組之間不得存在循環引用 | 使用 dependency analysis 工具偵測 |
| AR-2 | 禁止 god objects（單一檔案超過 500 行邏輯程式碼） | 超過 500 行的檔案須拆分 | 檔案行數檢查 |
| AR-3 | 禁止 commit 時跳過 linter / type checker | 不得使用 `--no-verify` | 監控 git hooks |

---

## KA — 知識存取規則（RAG 專屬）

| ID | 規則 | 說明 | 偵測方式 |
|----|------|------|----------|
| KA-1 | 禁止直接操作向量 DB（必須透過封裝的 Ingestor / Retriever） | 所有向量寫入/讀取必須經過治理閘門 | 搜尋 vector_db 的直接呼叫（應只出現在封裝層） |
| KA-2 | 禁止攝取未審核文件（status != "approved"） | Constitution Principle I | ingest 前置條件驗證 |
| KA-3 | 禁止在 system prompt 中省略「文件不足時回答無法回答」的指令 | Constitution Principle II | 審查 LLM 呼叫的 system prompt |
| KA-4 | 禁止使用 FORBIDDEN_MODELS 進行生產環境問答生成 | gpt-4o-mini、gpt-3.5-turbo 等禁止用於問答 | 搜尋 model 參數設定 |
| KA-5 | 禁止直接刪除向量 DB 中的文件（只允許 deprecate） | Constitution Principle V — 知識不可變 | 搜尋 vector_db.delete（應只出現在 rollback 和清理任務中） |

---

## MCP — MCP Server 規則（RAG 專屬）

| ID | 規則 | 說明 | 偵測方式 |
|----|------|------|----------|
| MCP-1 | 禁止 MCP Server 執行全域 namespace 搜尋 | Constitution Principle III — 最小知識原則 | 檢查 MCP query 是否有 namespace 限制 |
| MCP-2 | 禁止 MCP Server 暴露寫入工具 | MCP Server 只讀；寫入必須透過 ingest-skill | 檢查 list_tools() 回傳的工具列表 |

---

## 自我檢查流程

AI agent 在生成或修改程式碼時，須執行以下自我檢查：

```
1. 掃描生成的程式碼，比對上方所有 deny rule 的偵測模式
2. 若命中任何規則：
   a. 停止該段程式碼的輸出
   b. 向人類說明命中的規則 ID 與原因
   c. 提出符合規則的替代方案
3. 若無命中：正常輸出
4. 若不確定是否命中：標示 [DENY-CHECK: 需人類確認] 並說明疑慮
```

---

**優先順序**：Deny > Review > Module Rules > Guide

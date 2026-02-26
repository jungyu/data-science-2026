---
name: semantic-deny
description: "跨模組語意層級禁止規則彙總 — AI agent 不可違反的程式碼層級約束"
tags: ["governance", "safety", "deny", "cross-cutting"]
---

# Semantic Deny Rules

> 以下規則為**絕對禁止**事項，即使人類明確要求，AI agent 仍應拒絕執行並說明原因。
> 此層級高於 human-review-triggers.md 中的任何豁免條件。

---

## GEN — 通用規則

| ID | 規則 | 說明 | 偵測方式 |
|----|------|------|----------|
| GEN-1 | 禁止無理由的 `@ts-ignore` / `type: ignore` / `# noqa` | 每個 suppression 必須附上 justification 註解，說明為何無法正確修復 | 搜尋 `@ts-ignore`、`type: ignore`、`# noqa`、`eslint-disable` 等，檢查是否有相鄰 justification |
| GEN-2 | 禁止引入功能重疊的套件 | 新增依賴前須確認無現有套件已提供相同功能；若有，須使用現有套件或提出替換計畫 | 比對 package.json / requirements.txt 中現有依賴的功能範圍 |
| GEN-3 | 禁止在核心封裝外直接使用底層 API | 若專案已封裝某底層 API（如 HTTP client、DB client、auth helper），消費端必須透過封裝層呼叫 | 搜尋底層 API 的直接 import，確認是否來自封裝模組外 |
| GEN-4 | 禁止 production code 中殘留 `console.log` / `print()` | 使用專案的 logging framework；開發階段的 debug 輸出須在 commit 前移除 | pre-commit hook 或 lint rule 偵測 |
| GEN-5 | 禁止 hardcoded secrets（API keys、passwords、tokens） | 所有 secrets 必須透過環境變數或 secret manager 注入 | 搜尋常見 secret 模式（`sk-`、`pk_`、`password=`、`Bearer ` 等） |

---

## DB — 資料庫規則

| ID | 規則 | 說明 | 偵測方式 |
|----|------|------|----------|
| DB-1 | 禁止繞過 ORM / Data Access Layer 直接操作資料庫 | 所有 CRUD 操作必須透過專案定義的 data access 層；禁止在 route handler 或 component 中直接寫 SQL / 直接呼叫 DB client | 搜尋 route/component 檔案中的 DB client import |
| DB-2 | 禁止前端程式碼中存在 service-role key 或 admin credentials | 前端（browser-side）程式碼不得引用任何具有提權能力的 credentials | 搜尋前端目錄中的 service key 相關字串 |
| DB-3 | 禁止不帶 `IF EXISTS` 的 `DROP TABLE` / `DROP INDEX` | 所有 destructive DDL 必須包含安全檢查，避免在物件不存在時造成 migration 失敗 | 搜尋 `DROP TABLE`、`DROP INDEX`，檢查是否有 `IF EXISTS` |

---

## SEC — 安全規則

| ID | 規則 | 說明 | 偵測方式 |
|----|------|------|----------|
| SEC-1 | 禁止對使用者輸入執行 `eval()` / `exec()` / `Function()` | 動態程式碼執行是 RCE（Remote Code Execution）的主要攻擊面；若確有需求，須使用 sandbox 並經安全審查 | 搜尋 `eval(`、`exec(`、`new Function(`，追蹤參數來源 |
| SEC-2 | 禁止明文儲存或傳輸密碼 | 密碼必須使用 bcrypt / argon2 等單向 hash；傳輸必須走 HTTPS/TLS | 搜尋 password 相關欄位的儲存方式 |
| SEC-3 | 禁止無限制的 CORS `*` 設定 | CORS 的 `Access-Control-Allow-Origin` 必須限定為已知 origin 清單；開發環境除外 | 搜尋 `Access-Control-Allow-Origin: *` 或 `origin: '*'`，確認環境條件 |

---

## AR — 架構規則

| ID | 規則 | 說明 | 偵測方式 |
|----|------|------|----------|
| AR-1 | 禁止 circular dependencies | 模組之間不得存在循環引用；偵測到時須重構為單向依賴或提取共用模組 | 使用 `madge --circular` 或等效工具偵測 |
| AR-2 | 禁止 god objects（單一檔案超過 500 行邏輯程式碼） | 超過 500 行的檔案須拆分為多個職責明確的模組；行數計算排除 import、type 定義、註解 | 檔案行數檢查（排除 type-only 與 comment 行） |
| AR-3 | 禁止 commit 時跳過 linter / type checker | 不得在 commit 中使用 `--no-verify` 或在 CI 中停用 lint/typecheck 步驟 | 監控 git hooks 與 CI pipeline 設定 |

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

## 如何新增規則

1. 確定規則的分類（GEN / DB / SEC / AR，或新增分類）
2. 分配下一個流水號 ID（如 `GEN-6`、`SEC-4`）
3. 填寫：規則名稱、說明（為何禁止）、偵測方式
4. 在 PR description 中標示 `[semantic-deny: NEW RULE]`
5. 經團隊 review 後合併

**分類擴展建議**：
- `PERF-*`：效能相關禁止規則
- `TEST-*`：測試相關禁止規則
- `UI-*`：前端/介面相關禁止規則

---

## 與其他治理層的關係

| 層級 | 文件 | 強制力 |
|------|------|--------|
| **Deny（本文件）** | `semantic-deny.md` | 絕對禁止，不可豁免 |
| **Review** | `human-review-triggers.md` | 需人類確認，可依條件豁免 |
| **Guide** | `copilot-instructions.md` | 建議遵循，彈性較高 |
| **Module** | `_module-rules-template.md` | 模組層級約束，由模組負責人維護 |

**優先順序**：Deny > Review > Module Rules > Guide

> 若 deny rule 與其他文件衝突，以 deny rule 為準。

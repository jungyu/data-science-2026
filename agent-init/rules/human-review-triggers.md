---
name: human-review-triggers
description: "AI agent 必須暫停並詢問人類確認的操作清單"
tags: ["governance", "safety", "human-in-the-loop"]
---

# Human Review Triggers

> AI agent 在執行下列操作前，**必須**依等級決定是否暫停並取得人類確認。
> 此清單為專案治理的最後一道防線，任何自動化流程皆不得繞過。

---

## LEVEL 1 — MUST STOP（必須停止並等待人類確認）

Agent 偵測到以下意圖時，**必須立即停止**，輸出變更摘要並等待明確核准。

| ID | 類別 | 觸發條件 |
|----|------|----------|
| L1-DB-1 | 資料庫 | 建立或執行 database migration（schema 變更、欄位增刪改） |
| L1-DB-2 | 資料庫 | 包含 `DROP`、`TRUNCATE`、或缺少 `WHERE` 子句的 `DELETE` 語句 |
| L1-AUTH | 認證 | 修改認證/授權流程（login、register、OAuth、token 機制、session 策略） |
| L1-DEPLOY | 部署 | 修改 CI/CD pipeline 設定、deployment config、或 infrastructure-as-code |
| L1-GOV | 治理 | 修改 `.agent-init/` 下任何 constitution 或 governance gate 文件 |
| L1-PAY | 金流 | 修改 payment、billing、pricing、subscription 相關邏輯或設定 |
| L1-DEL-1 | 刪除 | 單次操作刪除超過 5 個檔案 |
| L1-DEL-2 | 刪除 | 刪除核心目錄（`lib/`、`app/`、`components/`、`config/`、或其他 {{CORE_DIRS}}） |
| L1-ENV | 環境 | 修改生產環境變數（`.env.production`、secrets、encryption keys） |

**Agent 行為規則**：
1. 輸出完整的變更意圖摘要（影響範圍、預期結果、風險評估）
2. 列出所有受影響的檔案清單
3. 明確標示 `[LEVEL 1 — 等待人類確認]`
4. **不得**在未收到明確核准前執行任何寫入操作
5. 若人類拒絕，agent 須提出替代方案或終止該操作

---

## LEVEL 2 — SHOULD CONFIRM（應確認，可附帶建議）

Agent 偵測到以下意圖時，**應主動告知人類**並附上建議，等待確認後再執行。
若人類已在同一對話中明確授權同類操作，可在告知後直接執行。

| ID | 類別 | 觸發條件 |
|----|------|----------|
| L2-DEP | 架構 | 新增套件依賴（npm / pip / cargo / go mod 等） |
| L2-API | API | 新增或修改公開 API route（endpoint signature、HTTP method、response schema） |
| L2-TEST-1 | 測試 | 刪除測試案例或將測試標記為 `skip` / `todo` |
| L2-BARREL | 架構 | 修改 barrel export（index.ts / __init__.py 等入口檔案） |
| L2-IFACE | 核心 | 修改共用元件或 library 的公開介面（exported types、function signatures） |
| L2-QUOTA | 品質 | 修改 rate limiting、quota、throttle 相關邏輯 |
| L2-PERF | 效能 | 修改 caching 策略或 query 層級（N+1、batch size、connection pool） |
| L2-DEP-RM | 架構 | 移除現有套件依賴 |

**Agent 行為規則**：
1. 輸出變更摘要與推薦理由
2. 標示 `[LEVEL 2 — 建議確認]`
3. 若人類在同一對話中已授權同類操作（如「可以自行新增需要的套件」），可在告知後直接執行
4. 記錄授權範圍，不得擴大解釋

---

## LEVEL 3 — NOTIFY AFTER（事後通知即可）

Agent 可直接執行，但**必須在完成後立即通知人類**，附上變更摘要。

| ID | 類別 | 觸發條件 |
|----|------|----------|
| L3-AGENT | 文件 | 修改 `.agent-init/` 下的 rules 或 skills 文件（非 constitution） |
| L3-MEM | 文件 | 修改 MEMORY.md、diary.md、或其他 agent 記憶檔案 |
| L3-RENAME | 重構 | 單次操作 rename 超過 3 個檔案 |
| L3-STYLE | 樣式 | 修改全域 CSS、theme 設定、design tokens |

**Agent 行為規則**：
1. 執行完成後立即輸出變更摘要
2. 標示 `[LEVEL 3 — 事後通知]`
3. 列出所有變更的檔案與修改重點

---

## 豁免條件

以下情境可降低審查等級（但不得完全跳過）：

| 條件 | 效果 |
|------|------|
| 人類在同一對話中明確授權 | LEVEL 2 → 告知後直接執行 |
| 變更僅限於測試檔案（`__tests__/`、`*.test.*`、`*.spec.*`） | LEVEL 2 → LEVEL 3 |
| 變更為 revert（還原先前 commit） | LEVEL 1 → LEVEL 2 |
| 人類明確指示「全權處理」 | LEVEL 2 → LEVEL 3，LEVEL 1 維持不變 |

> **注意**：LEVEL 1 中的 L1-GOV（治理文件）與 L1-PAY（金流）**永遠不可豁免**。

---

## 與其他治理層的關係

- **semantic-deny.md**：定義「絕對禁止」的程式碼層級約束 — 即使人類核准，deny 規則仍不可違反
- **copilot-instructions.md**：定義日常開發的編碼規範與慣例
- **_module-rules-template.md**：定義各模組的架構邊界與不變量

本文件的觸發條件與 semantic-deny 互補：deny 規則是「無條件禁止」，本文件是「需人類確認後可執行」。

---
name: human-review-triggers
description: "AI agent 必須暫停並詢問人類確認的操作清單（含 RAG 專屬觸發條件）"
tags: ["governance", "safety", "human-in-the-loop", "rag"]
---

# Human Review Triggers

> AI agent 在執行下列操作前，**必須**依等級決定是否暫停並取得人類確認。

---

## LEVEL 1 — MUST STOP（必須停止並等待人類確認）

| ID | 類別 | 觸發條件 |
|----|------|----------|
| L1-DB-1 | 資料庫 | 建立或執行 database migration |
| L1-DB-2 | 資料庫 | 包含 `DROP`、`TRUNCATE`、或缺少 `WHERE` 的 `DELETE` |
| L1-AUTH | 認證 | 修改認證/授權流程 |
| L1-DEPLOY | 部署 | 修改 CI/CD pipeline 或 deployment config |
| L1-GOV | 治理 | 修改 `.agent/` 下 constitution 或 governance gate 文件 |
| L1-PAY | 金流 | 修改 payment、billing、pricing 相關邏輯 |
| L1-DEL-1 | 刪除 | 單次操作刪除超過 5 個檔案 |
| L1-DEL-2 | 刪除 | 刪除核心目錄（`src/`、`tests/`、`.agent/`） |
| L1-ENV | 環境 | 修改生產環境變數 |
| L1-EMBED | RAG | 更換嵌入模型（影響全系統向量空間） |
| L1-NS-PERM | RAG | 變更 namespace 存取權限（影響資料隔離） |
| L1-CONST | RAG | 修改 Constitution（任何原則的增刪改） |
| L1-BULK-DEL | RAG | 批次刪除/廢棄超過 10 份文件 |

**L1-GOV、L1-PAY、L1-CONST 永遠不可豁免。**

---

## LEVEL 2 — SHOULD CONFIRM（應確認）

| ID | 類別 | 觸發條件 |
|----|------|----------|
| L2-DEP | 架構 | 新增套件依賴 |
| L2-API | API | 新增或修改公開 API route |
| L2-TEST-1 | 測試 | 刪除測試案例或標記 skip |
| L2-BARREL | 架構 | 修改 barrel export / `__init__.py` 入口 |
| L2-IFACE | 核心 | 修改共用元件的公開介面 |
| L2-QUOTA | 品質 | 修改 rate limiting / quota 邏輯 |
| L2-PERF | 效能 | 修改 caching 策略或 query 層級 |
| L2-DEP-RM | 架構 | 移除現有套件依賴 |
| L2-NS-NEW | RAG | 新增 namespace（需要存取控制設計） |
| L2-BATCH | RAG | 批次攝取超過 50 份文件 |
| L2-CHUNK | RAG | 修改 chunking 參數（target_size, overlap） |
| L2-GATE | RAG | 修改 Retrieval Gate 閾值（MIN_SCORE, MAX_AGE_DAYS） |

---

## LEVEL 3 — NOTIFY AFTER（事後通知）

| ID | 類別 | 觸發條件 |
|----|------|----------|
| L3-AGENT | 文件 | 修改 `.agent/` 下的 rules 或 skills 文件（非 constitution） |
| L3-MEM | 文件 | 修改 diary.md 或 agent 記憶檔案 |
| L3-RENAME | 重構 | 單次 rename 超過 3 個檔案 |
| L3-STYLE | 樣式 | 修改全域 CSS、theme 設定 |
| L3-LOG | RAG | 修改 Action Log 格式或保留策略 |
| L3-BUDGET | RAG | 調整 token budget 配額（不影響安全性） |

---

## 豁免條件

| 條件 | 效果 |
|------|------|
| 人類在同一對話中明確授權 | LEVEL 2 → 告知後直接執行 |
| 變更僅限於測試檔案 | LEVEL 2 → LEVEL 3 |
| 變更為 revert（還原先前 commit） | LEVEL 1 → LEVEL 2 |
| 人類明確指示「全權處理」 | LEVEL 2 → LEVEL 3，LEVEL 1 維持不變 |
| Task Pack 已核准此操作 | LEVEL 2 → 告知後直接執行 |
| 緊急修復模式（urgent_fix） | LEVEL 2 → LEVEL 3 |

> **注意**：L1-GOV、L1-PAY、L1-CONST **永遠不可豁免**。

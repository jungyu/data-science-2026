# 02 — Scenario Gate：BDD 場景完整性

> Standard / Full 模式必須通過此閘門。

## 驗證清單

- [ ] Happy path 場景定義（正常操作流程）
- [ ] Error path 場景定義（至少 2 個失敗場景）
- [ ] Edge case 場景定義（空文件、超大文件、重複攝取）
- [ ] 安全場景定義（跨 namespace 存取、未授權操作）

## Gherkin 格式要求

每個場景必須包含：
- **Given**：前置狀態（向量 DB 狀態、文件準備）
- **When**：觸發操作
- **Then**：預期結果（含治理規則驗證）

## 通過條件

至少有 1 個 happy path + 1 個 error path + 1 個安全場景。

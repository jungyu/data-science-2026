---
name: governance
description: "AI 協作治理框架 - 防止技術債與架構漂移的守門員"
tags: ["governance", "architecture", "quality-control"]
---

# AI 協作治理框架

## 宗旨

本框架為 AI Agent 與人類開發者協作時的**治理守門員**。
所有規則皆為專案無關（project-agnostic），透過 `{{PLACEHOLDER}}` 標記專案特定路徑與慣例。

---

## 核心原則

### 1. Contract First（契約優先）

任何涉及 API、型別、Schema 的變更，**必須先更新契約文件**再修改實作。
契約是系統的 single source of truth，實作永遠追隨契約。

### 2. AI Containment（AI 隔離）

AI 產生的程式碼**不得直接進入生產路徑**。
所有 AI 生成物先進隔離區，經人類審查與重構後才可整併。

### 3. Style Consistency（風格一致性）

同一模組內**禁止混用**多種 async pattern、error handling pattern 或 naming convention。
所有新增程式碼必須遵循專案既有的 style canon。

### 4. Decision Recording（決策記錄）

影響架構、部署、核心依賴的變更**必須留下 ADR（Architecture Decision Record）**。
決策不記錄等於決策不存在。

### 5. Evolution Control（演化控制）

系統演化必須沿著 intent map 定義的方向前進。
任何偏離 non-negotiables 的變更必須附帶補救方案。

### 6. Escape Hatch Guarantee（逃生艙保證）

引入平台鎖定格式或供應商特定依賴時，**必須提供逃生艙**（escape hatch），
確保系統不會被單一供應商或格式永久綁定。

---

## 規則清單

| 規則檔案 | 守門範圍 | 說明 |
|----------|---------|------|
| `contract_first_gate.yaml` | 契約與 Schema 變更 | API / 型別 / DB Schema 變更必須同步更新契約文件 |
| `adr_gate.yaml` | 架構決策記錄 | 部署、核心依賴、版本系統變更須留 ADR |
| `ai_quarantine_merge.yaml` | AI 程式碼隔離 | AI 生成物必須先進隔離區再整併 |
| `style_canon_enforcer.yaml` | 風格一致性 | 命名、error handling、logging 必須遵循 style canon |
| `intent_drift_detector.yaml` | 意圖漂移偵測 | 偵測偏離平台核心意圖的變更 |

---

## 使用方式

1. **初次導入**：複製 `.agent-init/` 至專案根目錄
2. **自訂佔位符**：替換所有 `{{PLACEHOLDER}}` 為專案實際路徑與慣例
3. **啟用規則**：AI Agent 在每次程式碼變更前自動比對規則
4. **演化更新**：隨專案成長新增規則或調整閾值

## 佔位符參考

| 佔位符 | 說明 | 範例 |
|--------|------|------|
| `{{SRC_DIR}}` | 主要原始碼目錄 | `src/`, `lib/`, `app/` |
| `{{API_DIR}}` | API 路由目錄 | `app/api/`, `src/routes/` |
| `{{CONTRACT_DIR}}` | 契約文件目錄 | `contracts/`, `schemas/` |
| `{{STYLE_CANON_PATH}}` | 風格規範文件路徑 | `docs/style-canon.md` |
| `{{ERROR_TYPE_MODULE}}` | 統一錯誤型別模組 | `lib/errors.ts` |
| `{{LOGGING_UTILITY}}` | 集中式 logging 工具 | `lib/logger.ts` |
| `{{CSS_MERGE_UTILITY}}` | CSS class 合併工具 | `lib/utils/cn.ts` |
| `{{ADR_DIR}}` | ADR 文件目錄 | `docs/adr/` |
| `{{INTENT_DIR}}` | Intent map 目錄 | `docs/intent/` |

# Scenario Gate Prompt - 情境關

> **目的**: 從 SDD 中萃取「最值錢」的情境，建立 BDD 行為契約。

## 🎯 核心任務

從 SDD 中萃取 **3-7 條**關鍵情境，必須覆蓋：
- ⚡ **權限邊界** - 不同角色的存取控制
- 🔒 **數據一致性** - 並發與交易完整性
- ⚠️ **不可逆操作** - 刪除、發布等高風險動作
- 🛡️ **Fail-safe** - 安全失效機制

## ❌ 禁止行為

- ❌ 追求無意義的測試覆蓋率
- ❌ 為每個欄位寫獨立測試
- ❌ 重複測試相同邏輯

---

## Prompt Template

```markdown
# Role
你是一位 QA 專家，負責撰寫 BDD Gherkin 規格。

# Context
我已完成 `01-spec.md` 的規格定義，現在需要萃取關鍵測試情境。

# Task
請根據 SDD 規格，撰寫 `specs/[feature-name]/02-scenarios.feature`。

## 萃取原則
1. 選擇 3-7 條「最值錢」的情境
2. 優先覆蓋：權限、一致性、不可逆操作、Fail-safe
3. 標註每個 Scenario 的測試層級

## Gherkin Style Guide
- **Given**: 描述初始狀態與前置條件
- **When**: 描述使用者操作
- **Then**: 描述預期結果

## 測試層級標註
使用 Tag 標註：
- `@e2e` - 端對端測試
- `@integration` - 整合測試
- `@unit` - 單元測試

# Output Format

feature
Feature: [功能名稱]
  為了 [商業價值]
  作為 [角色]
  我需要 [功能]

  Background:
    Given 系統已配置...

  @e2e @critical
  Scenario: [Happy Path]
    Given ...
    When ...
    Then ...

  @integration @security
  Scenario: [權限檢查]
    Given 使用者角色為 "viewer"
    When 使用者嘗試執行 [操作]
    Then 系統應回傳 403 錯誤

  @integration @data-integrity
  Scenario: [並發控制]
    Given 兩個使用者同時編輯同一資源
    When 第二個使用者嘗試儲存
    Then 系統應偵測到衝突並提示
```

---

## 產出範例

```gherkin
Feature: 主題複製功能
  為了快速建立類似的主題配置
  作為主題設計師
  我需要複製現有主題

  Background:
    Given 系統已配置測試環境
    And 使用者已登入

  @e2e @critical
  Scenario: 成功複製主題
    Given 我有一個名為 "Dark Theme" 的主題
    When 我點擊複製按鈕
    And 輸入新名稱 "Dark Theme Copy"
    Then 系統應建立新主題記錄
    And 新主題應包含原主題的所有配置

  @integration @security
  Scenario: 無權複製他人主題
    Given 使用者 A 擁有主題 "Private Theme"
    And 該主題設定為私人
    When 使用者 B 嘗試複製該主題
    Then 系統應回傳 403 錯誤
    And 錯誤訊息應為 "您沒有權限複製此主題"

  @unit @validation
  Scenario: 複製名稱重複檢查
    Given 已存在名為 "My Theme" 的主題
    When 我嘗試複製並命名為 "My Theme"
    Then 系統應提示 "該名稱已存在，請使用其他名稱"
```

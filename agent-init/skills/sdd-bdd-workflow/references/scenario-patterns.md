# BDD 情境模式庫 (Scenario Patterns)

> **目的**: 提供可重用的 BDD 情境模板，加速規格撰寫。

---

## 📋 權限相關情境

### Pattern 1: 角色權限檢查

```gherkin
@integration @security
Scenario: [角色] 無權執行 [操作]
  Given 使用者角色為 "[角色名稱]"
  And 存在一個 [資源] "[資源名稱]"
  When 使用者嘗試 [操作] 該 [資源]
  Then 系統應回傳 403 錯誤
  And 錯誤訊息應為 "您沒有權限執行此操作"
```

**變數替換範例**:
- [角色名稱]: viewer, member, guest
- [資源]: 主題, 專案, 文章
- [操作]: 刪除, 編輯, 複製

---

### Pattern 2: 資源擁有者檢查

```gherkin
@integration @security
Scenario: 無法存取他人的 [資源]
  Given 使用者 A 擁有 [資源] "私人資源"
  And 該 [資源] 設定為私人
  When 使用者 B 嘗試存取該 [資源]
  Then 系統應回傳 404 錯誤
  # 注意：回傳 404 而非 403，避免洩漏資源存在資訊
```

---

## 📋 CRUD 情境

### Pattern 3: 成功建立

```gherkin
@e2e @critical
Scenario: 成功建立 [資源]
  Given 使用者已登入
  And 使用者有建立 [資源] 的權限
  When 使用者填寫 [資源] 表單
    | 欄位 | 值 |
    | 名稱 | "新資源" |
    | 描述 | "測試描述" |
  And 使用者點擊儲存按鈕
  Then 系統應建立新的 [資源]
  And 使用者應被導向 [資源] 詳情頁
  And 應顯示成功通知 "[資源] 已建立"
```

---

### Pattern 4: 驗證失敗

```gherkin
@unit @validation
Scenario: [欄位] 驗證失敗
  Given 使用者正在編輯 [資源]
  When 使用者輸入 [無效值] 於 [欄位]
  And 使用者嘗試儲存
  Then 系統應顯示驗證錯誤
  And 錯誤訊息應為 "[錯誤訊息]"
  And [資源] 應不被儲存
```

---

### Pattern 5: 刪除確認 (不可逆操作)

```gherkin
@e2e @critical @irreversible
Scenario: 刪除 [資源] 需要確認
  Given 存在一個 [資源] "待刪除資源"
  When 使用者點擊刪除按鈕
  Then 系統應顯示確認對話框
  And 對話框應警告 "此操作無法復原"
  When 使用者確認刪除
  Then [資源] 應被刪除
  And 使用者應被導向 [資源] 列表頁
```

---

## 📋 並發控制情境

### Pattern 6: 樂觀鎖定衝突

```gherkin
@integration @data-integrity
Scenario: 並發編輯衝突
  Given 使用者 A 開啟 [資源] 編輯頁面
  And 使用者 B 開啟同一個 [資源] 編輯頁面
  When 使用者 A 儲存變更
  And 使用者 B 嘗試儲存變更
  Then 使用者 B 應收到衝突錯誤
  And 錯誤訊息應為 "資源已被其他人修改，請重新載入"
  And 系統應保留使用者 A 的變更
```

---

### Pattern 7: 資源鎖定

```gherkin
@integration @data-integrity
Scenario: 編輯中的資源鎖定
  Given 使用者 A 正在編輯 [資源]
  When 使用者 B 嘗試編輯同一個 [資源]
  Then 使用者 B 應看到唯讀模式
  And 應顯示訊息 "此資源正被 [使用者 A] 編輯中"
```

---

## 📋 系統錯誤情境

### Pattern 8: 外部 API 失敗

```gherkin
@integration @fail-safe
Scenario: 外部服務暫時不可用
  Given 外部 [服務名稱] API 回傳 503 錯誤
  When 使用者嘗試 [操作]
  Then 系統應顯示友善錯誤訊息
  And 錯誤訊息應為 "[服務名稱] 服務暫時無法使用，請稍後再試"
  And 系統應記錄錯誤日誌
  # 注意：不應洩漏技術細節給使用者
```

---

### Pattern 9: 網路逾時

```gherkin
@integration @fail-safe
Scenario: 操作逾時
  Given 執行 [操作] 需要超過 30 秒
  When 使用者觸發該 [操作]
  Then 系統應在 30 秒後顯示逾時訊息
  And 應提供重試按鈕
  And 若為交易操作，應回滾所有變更
```

---

## 📋 邊界條件情境

### Pattern 10: 配額限制

```gherkin
@integration @business-rule
Scenario: 達到 [資源] 數量上限
  Given 使用者已建立 [上限數量] 個 [資源]
  When 使用者嘗試建立新的 [資源]
  Then 系統應拒絕建立
  And 錯誤訊息應為 "已達到 [資源] 數量上限 ([上限數量])"
  And 應提供升級方案連結
```

---

### Pattern 11: 空狀態處理

```gherkin
@unit @ui
Scenario: 無 [資源] 時的空狀態
  Given 使用者沒有任何 [資源]
  When 使用者進入 [資源] 列表頁
  Then 應顯示空狀態插圖
  And 應顯示引導文字 "尚無 [資源]，立即建立第一個"
  And 應提供建立按鈕
```

---

## 🎯 使用方式

### 在 02-scenarios.feature 中使用

1. 從模式庫選擇適用的 Pattern
2. 替換 `[變數]` 為實際值
3. 根據需求調整細節

### 範例：主題複製功能

```gherkin
Feature: 主題複製
  
  # 使用 Pattern 3 變體
  @e2e @critical
  Scenario: 成功複製主題
    Given 使用者已登入
    And 存在一個主題 "Dark Theme"
    When 使用者點擊複製按鈕
    And 輸入新名稱 "Dark Theme Copy"
    Then 系統應建立新主題
    And 新主題應包含原主題的所有配置
  
  # 使用 Pattern 1
  @integration @security
  Scenario: Viewer 無權複製主題
    Given 使用者角色為 "viewer"
    And 存在一個主題 "Protected Theme"
    When 使用者嘗試複製該主題
    Then 系統應回傳 403 錯誤
    And 錯誤訊息應為 "您沒有權限複製此主題"
  
  # 使用 Pattern 4
  @unit @validation
  Scenario: 複製名稱重複檢查
    Given 已存在名為 "My Theme" 的主題
    When 使用者嘗試複製並命名為 "My Theme"
    Then 系統應顯示驗證錯誤
    And 錯誤訊息應為 "該名稱已存在，請使用其他名稱"
```

---

## 📚 相關文件

- [error-taxonomy.md](./error-taxonomy.md) - 錯誤分類參考
- [02-scenario-gate.md](../02-scenario-gate.md) - Scenario Gate Prompt

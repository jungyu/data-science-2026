# Ch3：BDD 行為驅動開發

> **本章目標**：學會用 Gherkin 語法寫驗收測試，確保需求被正確理解。

---

## 🎬 開場：從規格到測試

上一章，你寫了規格。

但規格再清楚，也只是「文字描述」。

**問題：怎麼確保 Agent 真的理解了你的規格？**

答案：**用測試來驗證**。

BDD（行為驅動開發）就是這個橋樑。

---

## 🌉 什麼是 BDD？

### 定義

```
BDD = 用「使用者的語言」寫「驗收測試」

特點：
- 不是程式碼（非程序員也能讀）
- 描述「行為」（系統應該怎麼做）
- 自動化測試（可以跑 check）
- 既是規格，也是測試
```

### BDD 的三個角色

```
你（開發者）
    ↓
寫 BDD 情境
（用 Gherkin 語法）
    ↓
Agent（Claude Code）
    ↓
根據情境寫程式碼
    ↓
自動化測試
    ↓
驗證程式碼符合情境
```

### BDD 的核心思想

```
沒有 BDD：
「規格」← 人工理解 → 「程式碼」
                    ↓
                有可能理解錯誤

有 BDD：
「規格」→「情境（自動化測試）」← 機器驗證 → 「程式碼」
   人類寫          人類檢查              自動執行
                                      ↓
                                   無法理解錯誤
```

---

## 📝 Gherkin 語法入門

Gherkin 是一種特殊的「行為描述語言」，讓非技術人員也能寫測試。

### 基本結構

```gherkin
Feature: [功能名稱]
  [簡短描述]

  Scenario: [場景名稱]
    Given [前置條件]
    When [使用者做什麼]
    Then [系統應該怎樣]
```

### 翻譯成中文

```gherkin
功能: [功能名稱]

  場景: [場景名稱]
    假設 [前置條件]
    當 [使用者做什麼]
    那麼 [系統應該怎樣]
```

### 簡單例子

```gherkin
Feature: 使用者登入

  Scenario: 成功登入
    Given 使用者在登入頁面
    When 使用者輸入 "alice@example.com" 和密碼 "Pass1234"
    And 點擊「登入」按鈕
    Then 系統應該導向首頁
    And 顯示歡迎訊息 "Hi, Alice"
```

### 語法解析

```
Feature: 功能塊的開始
  └─ 表示整個功能

Scenario: 一個具體的場景
  └─ 一個場景 = 一個測試用例

Given: 前置條件
  └─ 測試開始前的狀態

When: 觸發動作
  └─ 使用者或系統的動作

Then: 預期結果
  └─ 系統應該表現如何

And: 連接多個條件
  └─ Given ... And ... And ...
  └─ When ... And ... And ...
  └─ Then ... And ... And ...
```

---

## 🎯 BDD 的三種場景

### Scenario 1：快樂路徑（Happy Path）

使用者做「正確的事」，系統給「正確的回應」。

```gherkin
Scenario: 使用者成功建立帳戶
  Given 使用者在註冊頁面
  When 使用者輸入有效的 email "newuser@example.com"
  And 輸入有效的密碼 "SecurePass123"
  And 點擊「建立帳戶」
  Then 帳戶建立成功
  And 系統發送驗證信到 "newuser@example.com"
  And 導向驗證郵箱頁面
```

**為什麼需要？** 驗證基本功能正常運作

### Scenario 2：錯誤路徑（Error Path）

使用者做「不對的事」，系統給「合理的錯誤提示」。

```gherkin
Scenario: 使用者用無效的 email 註冊
  Given 使用者在註冊頁面
  When 使用者輸入無效的 email "not-an-email"
  And 輸入密碼 "SecurePass123"
  And 點擊「建立帳戶」
  Then 系統顯示錯誤訊息 "請輸入有效的 email"
  And 帳戶沒有被建立

Scenario: 使用者用已存在的 email 註冊
  Given 一個已註冊的使用者 "alice@example.com"
  When 使用者輸入 "alice@example.com"
  And 輸入密碼 "NewPassword123"
  And 點擊「建立帳戶」
  Then 系統顯示錯誤訊息 "此 email 已被使用"
  And 帳戶沒有被新建

Scenario: 使用者輸入過短的密碼
  Given 使用者在註冊頁面
  When 使用者輸入 email "user@example.com"
  And 輸入密碼 "short"
  And 點擊「建立帳戶」
  Then 系統顯示錯誤訊息 "密碼長度至少 8 字元"
```

**為什麼需要？** 驗證邊界情況的處理

### Scenario 3：邊界路徑（Edge Case）

系統在「特殊條件」下的表現。

```gherkin
Scenario: 密碼邊界測試 - 恰好 8 字元
  Given 使用者在註冊頁面
  When 使用者輸入 email "user@example.com"
  And 輸入密碼 "Pass1234" (8 個字元)
  And 點擊「建立帳戶」
  Then 帳戶建立成功

Scenario: 資料庫暫時不可用
  Given 資料庫服務當前不可用
  When 使用者提交註冊表單
  Then 系統顯示錯誤訊息 "系統暫時繁忙，請稍後重試"
  And 顯示「重試」按鈕

Scenario: 同時 1000 人申請註冊
  Given 系統承載 1000 並發請求
  When 所有使用者點擊「建立帳戶」
  Then 所有人都能在 30 秒內得到回應
  And 沒有資料重複或遺漏
```

**為什麼需要？** 驗證系統在壓力下的表現

---

## 📋 完整 BDD 範例：使用者邀請

回到之前的「使用者邀請」例子，看看怎麼用 BDD 寫：

```gherkin
Feature: 使用者邀請系統

  Background:
    Given 系統有一個 admin 使用者 "admin@company.com"
    And 系統有一個普通使用者 "member@company.com"

  # ========== 快樂路徑 ==========

  Scenario: Admin 成功邀請新使用者
    Given Admin 已登入
    When Admin 進入「邀請使用者」頁面
    And 輸入 email "newuser@example.com"
    And 點擊「發送邀請」
    Then 系統顯示成功訊息 "邀請已發送"
    And 一封邀請信被發送到 "newuser@example.com"
    And 邀請記錄顯示狀態為 "pending"

  Scenario: 被邀請者點擊連結完成註冊
    Given 一個有效的邀請連結 (72 小時內建立)
    When 被邀請者點擊連結
    And 輸入密碼 "SecurePass123"
    And 點擊「完成註冊」
    Then 新帳戶建立成功
    And 使用者自動登入
    And 邀請記錄標記為 "used"

  # ========== 錯誤路徑 ==========

  Scenario: 非 admin 使用者試圖邀請
    Given Member 已登入
    When Member 嘗試訪問「邀請使用者」頁面
    Then 系統返回 403 Forbidden
    And 顯示訊息 "你沒有權限執行此操作"

  Scenario: Admin 邀請已註冊的使用者
    Given Admin 已登入
    And "existing@example.com" 已經是註冊使用者
    When Admin 輸入 "existing@example.com"
    And 點擊「發送邀請」
    Then 系統顯示錯誤訊息 "此 email 已經是註冊使用者"
    And 沒有新的邀請被建立

  Scenario: Admin 輸入無效的 email
    Given Admin 已登入
    When Admin 輸入 "not-an-email"
    And 點擊「發送邀請」
    Then 系統顯示錯誤訊息 "請輸入有效的 email"

  Scenario: 邀請連結已過期
    Given 一個 72 小時前建立的邀請連結
    When 被邀請者點擊連結
    Then 系統顯示訊息 "邀請已過期，請聯繫管理員重新邀請"
    And 提供「請求新邀請」按鈕

  Scenario: 被邀請者用錯誤的密碼
    Given 一個有效的邀請連結
    When 被邀請者輸入密碼 "short"
    And 點擊「完成註冊」
    Then 系統顯示錯誤訊息 "密碼長度至少 8 字元"
    And 帳戶沒有被建立

  # ========== 邊界情況 ==========

  Scenario: 同一 email 發送多個邀請
    Given Admin 已登入
    And "user@example.com" 有 1 個 pending 邀請
    When Admin 再次輸入 "user@example.com"
    And 點擊「發送邀請」
    Then 新邀請被建立
    And 舊邀請標記為 "superseded"
    And "user@example.com" 收到新的邀請信

  Scenario: 同一 email 發送超過 3 個邀請
    Given Admin 已登入
    And "user@example.com" 已有 3 個 pending 邀請
    When Admin 試圖發送第 4 個邀請到 "user@example.com"
    And 點擊「發送邀請」
    Then 系統顯示警告 "此 email 已有 3 個待使用邀請，
                        請等待使用者點擊或重新發送"
    And 邀請沒有被建立

  Scenario: Database 連線失敗
    Given Database 當前不可用
    When Admin 點擊「發送邀請」
    Then 系統顯示錯誤 "系統暫時無法處理，請稍後重試"
    And 郵件沒有被發送
```

### 注意事項

```
✅ Background：每個 Scenario 之前都執行
   用來設置公共的前置條件

✅ Given：測試開始前的狀態
   可能包括「資料庫已有…」「使用者已登入…」

✅ When：使用者或系統做什麼動作
   通常只有 1-2 個主要動作

✅ Then：預期的結果
   應該可以被自動驗證（例如檢查 API 回應）

✅ And：連接同一層級的條件
   可以有多個 And
```

---

## 🔄 從規格轉換到 BDD

### Step 1：列出所有「場景」

從規格中，找出所有可能的場景：

```
規格：「使用者可以封鎖其他使用者」

快樂路徑：
  - 成功封鎖一個使用者

錯誤路徑：
  - 試圖封鎖自己
  - 試圖封鎖已封鎖的使用者
  - 非登入使用者試圖封鎖

邊界：
  - 同時封鎖多個使用者
  - 封鎖後可以解封嗎
  - 被封鎖者能知道嗎
```

### Step 2：用 Gherkin 寫出來

```gherkin
Feature: 使用者封鎖

  Scenario: 成功封鎖
    Given User Alice 已登入
    When Alice 訪問 Bob 的檔案
    And 點擊「更多」菜單
    And 選擇「封鎖此使用者」
    Then 系統顯示確認對話
    When Alice 點擊「是的，封鎖」
    Then Alice 的聯絡人列表中不再顯示 Bob
    And Bob 無法看到 Alice 的新貼文

  # 其他 Scenario...
```

### Step 3：讓 Agent 根據 BDD 寫程式碼

```
「這是『使用者封鎖』功能的 BDD 場景。
 請根據這些場景寫實作程式碼，
 讓所有場景都通過測試。」
```

---

## 🛠️ 寫 BDD 的技巧

### 技巧 1：一個 Scenario 只測試一件事

```
❌ 不好
Scenario: 註冊和登入
  Given 使用者在註冊頁面
  When 註冊成功
  Then 自動登入
  And 看到首頁
  And 郵件被發送
  And 使用者偏設置被初始化
  ... (太多事)

✅ 好
Scenario: 成功註冊
  Given 使用者在註冊頁面
  When 輸入有效資訊並提交
  Then 帳戶建立成功

Scenario: 註冊後發送驗證信
  Given 帳戶剛建立
  Then 驗證信被發送
```

### 技巧 2：用具體的例子，不用模糊的表述

```
❌ 模糊
When 使用者輸入一些資訊
Then 系統處理它

✅ 具體
When 使用者輸入 email "alice@example.com" 和密碼 "Pass1234"
Then 系統檢查 email 格式
And 檢查密碼長度 ≥ 8
And 建立帳戶
```

### 技巧 3：從使用者角度，不從系統角度

```
❌ 系統視角
When database.insert() 被呼叫
Then schema 驗證通過

✅ 使用者視角
When 使用者輸入有效的註冊資訊
Then 帳戶建立成功
And 看到確認訊息
```

### 技巧 4：每個 Scenario 應該是獨立的

```
❌ 有依賴
Scenario 1: 建立帳戶
Scenario 2: 登入（依賴 Scenario 1）

✅ 獨立（用 Background 或 Given 設置）
Background:
  Given 已經有一個註冊帳戶

Scenario 1: 建立帳戶
Scenario 2: 登入
```

---

## 📊 BDD 覆蓋度檢查表

寫完 BDD 情境後，檢查：

```
對於每個功能：

快樂路徑：
  □ 最基本的成功情況
  □ 有多個分支時，每個分支都測試

錯誤路徑：
  □ 輸入驗證（格式、範圍）
  □ 權限檢查（who can do what）
  □ 已有資源的處理（重複）
  □ 資源不存在
  □ 系統故障（DB、API）

邊界情況：
  □ 最小值邊界
  □ 最大值邊界
  □ 空的情況
  □ 並發情況（多人同時操作）

完整性：
  □ 覆蓋了規格中所有的驗收條件
  □ 沒有自相矛盾的場景
  □ 場景順序合理
```

---

## 🤝 BDD 和自動化測試的關係

### Framework 1：Gherkin + 測試框架

Gherkin 本身只是「描述語言」，需要搭配測試框架：

#### JavaScript/TypeScript

```javascript
// 使用 Cucumber 或 Jest Gherkin
import { Given, When, Then } from '@cucumber/cucumber';

Given('使用者在登入頁面', () => {
  // 設置前置條件
  cy.visit('/login');
});

When('使用者輸入 email {string} 和密碼 {string}', (email, password) => {
  // 執行動作
  cy.get('input[name=email]').type(email);
  cy.get('input[name=password]').type(password);
  cy.get('button[type=submit]').click();
});

Then('系統應該導向首頁', () => {
  // 驗證結果
  cy.url().should('include', '/home');
});
```

#### Python

```python
from behave import given, when, then

@given('使用者在登入頁面')
def step_user_at_login(context):
    context.browser.get('http://localhost:3000/login')

@when('使用者輸入 {email} 和 {password}')
def step_input_credentials(context, email, password):
    context.browser.find_element('input[name=email]').send_keys(email)
    context.browser.find_element('input[name=password]').send_keys(password)
    context.browser.find_element('button').click()

@then('系統應該導向首頁')
def step_redirect_home(context):
    assert '/home' in context.browser.current_url
```

### 重點

```
Gherkin ≠ 測試程式碼
Gherkin + 自動化映射 = 自動化測試

你寫 Gherkin（描述）
Agent 或你實作 step definitions（自動化邏輯）
自動化工具執行測試
```

---

## 📈 BDD 的三個層級

### Level 1：簡明 BDD

適合簡單功能，只有 1-2 個 Scenario：

```gherkin
Feature: 修改按鈕顏色

  Scenario: 登入按鈕變綠色
    Given 我看到登入按鈕
    When 我檢查按鈕的樣式
    Then 按鈕應該是綠色
```

### Level 2：標準 BDD

適合中等功能，3-5 個 Scenario（快樂路徑 + 3-4 個錯誤/邊界）：

這是我們前面的「使用者邀請」例子。

### Level 3：完整 BDD

適合複雜功能，10+ 個 Scenario，涵蓋所有可能情況：

```gherkin
Feature: 金流整合

  Background:
    Given 系統已連接綠界 API
    And 測試環境的商店代碼已設置

  # 正常流程：10+ Scenario
  # 錯誤流程：5+ Scenario
  # 邊界情況：5+ Scenario
  # 併發場景：3+ Scenario
  
  # 總共 20+ Scenario
```

---

## ❌ 常見陷阱

### 陷阱 1：BDD 和單元測試的混淆

```
❌ 不要用 BDD 測試細節
   Scenario: 密碼 hash 函式
   When password.hash() 被呼叫
   Then 結果應該是 bcrypt hash

✅ 用單元測試
   test('password hash should return bcrypt', () => {
     expect(hashPassword('abc')).toMatch(/^\$2[aby]/)
   })

✅ 用 BDD 測試高層行為
   Scenario: 密碼被安全地儲存
   When 使用者設定密碼
   Then 密碼在資料庫中不是明文
```

### 陷阱 2：Scenario 太多細節

```
❌ 過度
Scenario: 填表單
  Given 表單有 20 個欄位
  When 使用者輸入每個欄位 (20 步 When)
  Then 驗證每個欄位 (20 步 Then)

✅ 適當
Scenario: 提交完整表單
  When 使用者填寫並提交表單
  Then 系統驗證所有欄位
  And 建立記錄
```

### 陷阱 3：規格和 BDD 不同步

```
❌ 規格說「支援 3 種格式」
   BDD 只測了 1 種

✅ 檢查規格中的每個驗收條件
   都對應至少 1 個 BDD Scenario
```

### 陷阱 4：BDD 寫得太「技術」

```
❌ 技術語言
Scenario: API 端點返回正確的 JSON
  When POST /api/users 被呼叫，payload 為 {...}
  Then 回應状態為 201
  And response.body.id 存在

✅ 使用者語言
Scenario: 成功建立新使用者
  When 管理員點擊「新增使用者」
  And 輸入使用者資訊
  And 點擊「保存」
  Then 新使用者出現在清單中
```

---

## 🎓 總結：BDD 的核心

### BDD 是什麼

```
BDD = 用「人類可讀的語言」寫「可自動化的測試」

既是：
  - 規格（描述系統應該怎樣）
  - 測試（驗證系統是否符合規格）
  - 文件（讓新人了解功能如何使用）
```

### BDD 的三個層級

```
Given：前置條件
When：動作
Then：結果
```

### BDD 的三種場景

```
快樂路徑：正常情況
錯誤路徑：各種失敗
邊界路徑：邊界和壓力
```

### BDD 的目標

```
確保：
✅ 需求被清楚地表達
✅ 需求能被自動化驗證
✅ 實作符合需求
✅ 沒有「理解誤差」
```

---

## 🧠 動手做：寫你第一個 BDD

拿出上一章寫的規格。

現在，為它寫 BDD 情境：

```
Feature: [你的功能名稱]

  Scenario: [快樂路徑 - 成功情況]
    Given ...
    When ...
    Then ...

  Scenario: [錯誤情況 1]
    Given ...
    When ...
    Then ...

  Scenario: [錯誤情況 2]
    Given ...
    When ...
    Then ...

  Scenario: [邊界情況]
    Given ...
    When ...
    Then ...
```

要求：
- [ ] 至少 1 個快樂路徑
- [ ] 至少 2 個錯誤路徑
- [ ] 至少 1 個邊界情況
- [ ] 每個 Scenario 用「人類語言」
- [ ] 每個 Scenario 測試一件事
- [ ] 用具體例子（不是模糊表述）

---

## ✅ 本章回顧

```
目標：用 BDD 將規格轉換成可驗證的測試

學到的：
□ Gherkin 語法（Given/When/Then）
□ 三種場景（快樂路徑/錯誤路徑/邊界）
□ 怎麼從規格轉換到 BDD
□ BDD 和單元測試的區別
□ 常見陷阱

準備好了嗎？

下一章，我們要做決定：
根據功能複雜度，選擇合適的工作流
```

---

**下一章 → Ch4：複雜度評估與工作流選擇**

在那裡，你會學到：
- 四問題複雜度評估法
- 如何根據複雜度選擇 Lite / Standard / Full 工作流
- 何時升級工作流級別

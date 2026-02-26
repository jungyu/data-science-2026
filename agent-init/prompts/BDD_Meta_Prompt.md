# BDD Meta-Prompt for Component Integration

> 文件編號: BDD_Meta_Prompt
> 用途: AI 輔助開發的標準化 BDD 提示詞（泛用版）

---

## 🤖 Meta-Prompt: Component BDD Generator

```markdown
# Role
你是一位精通 {{TECH_STACK}} 架構的前端架構師與 QA 專家。你的任務是為指定的 UI 組件撰寫 BDD Gherkin Feature 文件。

# Context: Component Integration Protocol
在撰寫 Gherkin 前，請嚴格遵守以下整合邏輯：

1. **組件分類學 (Taxonomy):**
   - **Type A (Atomic):** 僅使用 Props/Fields 控制外觀與行為。不包含子插槽。
   - **Type B (Container):** 負責佈局，核心包含子元素渲染區域（slot / children）。
   - **Type C (Composite):** 必須拆解為 Parent-Child 結構 (如 ul > li)。Parent 管理方向，Child 管理內容。

2. **渲染邏輯 (Render Logic):**
   - **Slots:** 使用框架提供的插槽機制（React children、Vue slots、Web Component slots）。
   - **Conditional Slots:** 若 Slot 預設為空會影響美觀，必須搭配一個控制屬性來控制渲染。
   - **CSS Variables:** 若元件依賴 CSS 變數，必須在 render 中動態注入 style 物件。

# Task
請針對我指定的 UI 組件，產出一個完整的 Gherkin Feature 檔。
該檔案必須包含：
1. **Feature:** 描述該組件的整合目標。
2. **Scenario:** 涵蓋「屬性映射」、「插槽機制」與「條件渲染」的測試場景。
3. **Scenario Outline (若適用):** 針對不同 Variant (顏色/大小) 的批量測試。

# Gherkin Style Guide
- **Given:** 描述組件的初始設定 (props, defaultValues)。
- **When:** 描述使用者的操作 (如：點擊、切換開關、選擇選項)。
- **Then:** 描述預期的 HTML 結構、CSS Class 變化，以及插槽的存在與否。

---

# Input Task
請針對 **[在此填入您想開發的組件]** 撰寫 BDD 文件。
```

---

## 📝 範例產出: Stat 統計組件

### Feature 文件

```gherkin
Feature: Stat 統計組件整合
  為了讓視覺設計師能在編輯器中建立數據儀表板
  作為開發者
  我需要將 Stat 結構映射為組件配置 (Type C: Composite)

  Background:
    Given 系統已載入 UI 框架與樣式
    And 系統已配置組件編輯環境
    And 定義了 "StatsContainer" (Parent) 與 "Stat" (Child) 兩個組件

  # 測試父容器的佈局控制
  Scenario: 設定 Stats 容器的排列方向
    Given 我在編輯器中新增了 "StatsContainer"
    When 我將 "direction" 屬性設定為 "Vertical"
    Then 渲染出的 HTML 容器應包含 class "stats-vertical"
    And 容器內部應包含一個子元素插槽

  # 測試子組件的基本文字欄位映射
  Scenario: 編輯 Stat 單元的文字內容與顏色
    Given 我在 "StatsContainer" 中新增了一個 "Stat" 組件
    When 我輸入 "title" 為 "總瀏覽量"
    And 我輸入 "value" 為 "89,400"
    And 我選擇 "variant" (顏色) 為 "Secondary"
    Then 渲染出的 HTML 應包含 class "stat"
    And "stat-title" 區域應顯示文字 "總瀏覽量"
    And "stat-value" 區域應顯示文字 "89,400"
    And "stat-value" 區域應包含 class "text-secondary"

  # 關鍵邏輯：測試條件式插槽
  Scenario: 開啟圖示 (Figure) 插槽
    Given "Stat" 組件的 "showFigure" 屬性預設為 False
    When 我將 "showFigure" 切換為 True
    Then 渲染出的 HTML 應包含 div class "stat-figure"
    And 該 div 內部應渲染出一個名為 "figure-slot" 的插槽
    And 該插槽的提示文字應顯示 "Drop Icon Here"

  # 資料驅動測試：批量測試各種變體
  Scenario Outline: 測試所有顏色變體
    Given 我在 "StatsContainer" 中新增了一個 "Stat" 組件
    When 我選擇 "variant" 為 "<variant>"
    Then "stat-value" 應包含 class "text-<variant>"

    Examples:
      | variant   |
      | primary   |
      | secondary |
      | accent    |
      | info      |
      | success   |
      | warning   |
      | error     |
```

---

## 📝 範例產出 2: Timeline 時間軸組件

### Feature 文件

```gherkin
Feature: Timeline (時間軸) 組件整合
  為了讓設計師能夠在編輯器中建立具有時間序的事件列表
  作為開發者
  我需要將 Timeline 結構 (ul > li) 映射為組件配置 (Type C: Composite)

  Background:
    Given 系統已載入 UI 框架與樣式
    And 系統已配置組件編輯環境
    And 定義了 "TimelineContainer" (Parent) 與 "TimelineItem" (Child) 兩個組件

  Scenario: 設定時間軸容器的基本佈局
    Given 我在編輯器中新增了 "TimelineContainer"
    When 我將 "direction" 屬性設定為 "Horizontal" (水平)
    And 我開啟 "compact" (緊湊模式) 開關
    Then 渲染出的 HTML 標籤應為 "ul"
    And 該標籤應包含 class "timeline"
    And 該標籤應包含 class "timeline-horizontal"
    And 該標籤應包含 class "timeline-compact"
    And 容器內部應渲染出一個子元素插槽

  Scenario: 預設狀態下的時間軸單元結構
    Given 我在 "TimelineContainer" 中新增了一個 "TimelineItem"
    And 所有欄位均為預設值
    Then 渲染出的 HTML 標籤應為 "li"
    And 應包含 class "timeline-start" 且內部有起始內容插槽
    And 應包含 class "timeline-middle" 且內部顯示預設圖示 (SVG)
    And 應包含 class "timeline-end" 且內部有結尾內容插槽
    And 列表項目前後應各有一條 <hr> 分隔線

  # 條件式插槽：避免畫面出現空的插槽框線影響預覽體驗
  Scenario: 關閉時間軸左側/上方內容 (Start Content)
    Given "TimelineItem" 的 "hasStartContent" 屬性預設為 True
    When 我將 "hasStartContent" 切換為 False
    Then HTML 中對應 "timeline-start" 的 div 應被隱藏（或不渲染）
    And 編輯器畫面中不應出現起始內容的插槽框線

  Scenario: 限制容器僅接受特定子組件
    Given "TimelineContainer" 的子元素插槽設定
    When 我嘗試將 "Button" 組件拖入該區域
    Then 編輯器應拒絕該操作 (若有設定 accept 屬性)
    And 僅允許 "TimelineItem" 組件被放入
```

---

## 🎯 為何這個 Prompt 有效？

### 1. **鎖定框架版本**
強制 AI 使用正確的 API，避免使用過時的寫法。

### 2. **定義分類學 (Taxonomy)**
AI 會先判斷是 Type A, B 還是 C，這樣它在寫 `Given` 條件時才不會搞錯結構。

### 3. **強調條件渲染 (Conditional Slots)**
這是編輯器使用者體驗最關鍵的一環（避免畫面充滿空的框框）。

### 4. **清晰的 Given/When/Then 映射**
- **Given** = Config 設定
- **When** = 編輯器操作
- **Then** = 最終 HTML 與 Class

---

## 📋 使用流程

### Step 1: 選擇組件
從待實作列表中選擇一個組件（例如：Timeline, Accordion）

### Step 2: 使用 Meta-Prompt
將 Meta-Prompt 提供給 AI，指定組件名稱。

### Step 3: 獲得 Gherkin 規格
AI 產出完整的 Feature 文件，作為開發規格書。

### Step 4: 實作組件
根據 Gherkin 規格實作組件 Config。

### Step 5: 驗收測試
使用 Gherkin Scenario 逐條驗證實作是否正確。

---

## 📁 組件 BDD 文件目錄結構

```
docs/
└── bdd/
    └── components/
        ├── actions/
        │   ├── Button.feature
        │   ├── Dropdown.feature
        │   └── Modal.feature
        ├── data-display/
        │   ├── Accordion.feature
        │   ├── Carousel.feature
        │   ├── Stat.feature
        │   └── Timeline.feature
        ├── layout/
        │   ├── Drawer.feature
        │   └── Footer.feature
        └── README.md
```

---

## 🚀 下一步建議

1. **先測試簡單組件**
   - 使用 Badge 或 Button 測試 Prompt
   - 確認 AI 輸出符合預期

2. **建立 BDD 文件庫**
   - 為每個待實作組件生成 Feature 文件
   - 作為開發與 QA 的共同規格

3. **自動化測試**
   - 考慮使用 Cucumber.js 或 Playwright 將 Gherkin 轉為自動化測試

4. **持續優化 Protocol**
   - 根據實作經驗調整 Meta-Prompt
   - 補充邊緣案例與最佳實踐

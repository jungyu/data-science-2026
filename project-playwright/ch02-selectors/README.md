# Ch02 — 元素選擇器

## 學習目標

- 掌握 Playwright 的 Locator API（推薦方式）
- 了解 CSS、文字、角色等選擇策略
- 學會鏈式選擇（chaining）與篩選（filtering）

## 核心觀念

Playwright 推薦使用 **Locator API**，而非直接操作 `page.query_selector()`：

```python
# ✅ 推薦：Locator API（自動等待 + 重試）
page.locator("button.submit").click()
page.get_by_role("button", name="送出").click()
page.get_by_text("登入").click()

# ❌ 不推薦：舊式 query_selector（不會自動等待）
element = page.query_selector("button.submit")
```

## 選擇器優先順序

| 優先級 | 方法 | 適用場景 |
|--------|------|----------|
| 1 | `get_by_role()` | 按鈕、連結、表單元素 |
| 2 | `get_by_text()` | 可見文字內容 |
| 3 | `get_by_label()` | 表單欄位 |
| 4 | `get_by_placeholder()` | 輸入框 placeholder |
| 5 | `get_by_test_id()` | data-testid 屬性 |
| 6 | `locator("css")` | CSS 選擇器（通用） |

## 範例檔案

| 檔案 | 說明 |
|------|------|
| `01_locator_basics.py` | Locator API 基礎用法 |
| `02_role_and_text.py` | 以角色和文字定位元素 |
| `03_chaining_and_filtering.py` | 鏈式選擇與篩選技巧 |

## 練習

1. 用 `get_by_role()` 找到頁面上所有的連結
2. 嘗試用不同選擇器定位同一個元素，比較哪種最穩定
3. 使用 `locator().filter()` 從清單中篩選特定項目

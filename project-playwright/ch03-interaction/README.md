# Ch03 — 頁面互動

## 學習目標

- 模擬使用者操作：點擊、輸入、選擇
- 表單填寫與送出
- 鍵盤與滑鼠進階操作

## 核心觀念

Playwright 的互動方法都內建**自動等待**（auto-waiting）：
- 等待元素可見（visible）
- 等待元素穩定（stable，不在動畫中）
- 等待元素可接收事件（enabled）

```python
# 這行會自動等到按鈕出現且可點擊才執行
page.get_by_role("button", name="送出").click()
```

## 範例檔案

| 檔案 | 需要網路 | 說明 |
|------|---------|------|
| `01_click_and_type.py` | ✅（DuckDuckGo） | 基本點擊與文字輸入（selector 可能隨網站改版變動） |
| `02_form_operations.py` | ❌（自建 HTML） | 下拉選單、核取方塊、單選鈕（結果穩定） |
| `03_keyboard_mouse.py` | ❌（自建 HTML） | 鍵盤快捷鍵與滑鼠操作（結果穩定） |

## 自我檢核

完成本章後，你應該能回答：

1. 為什麼 `page.locator("button").click()` 不需要自己先等按鈕出現？Playwright 在背後做了什麼？
2. `page.fill()` 和 `page.type()` 都能輸入文字，差異在哪裡？什麼場景下你會選擇 `type()`？
3. `02_form_operations.py` 使用 `page.set_content()` 而非連到真實網站，這個設計有什麼優缺點？

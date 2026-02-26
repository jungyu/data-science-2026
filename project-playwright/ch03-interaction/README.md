# Ch03 — 頁面互動

## 學習目標

- 模擬使用者操作：點擊、輸入、選擇
- 表單填寫與送出
- 鍵盤與滑鼠進階操作
- 檔案上傳

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

| 檔案 | 說明 |
|------|------|
| `01_click_and_type.py` | 基本點擊與文字輸入 |
| `02_form_operations.py` | 下拉選單、核取方塊、單選鈕 |
| `03_keyboard_mouse.py` | 鍵盤快捷鍵與滑鼠操作 |

# Ch05 — 資料擷取

## 學習目標

- 從網頁中提取文字、屬性、HTML 內容
- 爬取表格資料並結構化
- 匯出為 JSON 和 CSV 格式
- 處理分頁和「載入更多」按鈕

## 核心觀念

資料擷取的三步驟：**定位 → 提取 → 結構化**

```python
# 定位
rows = page.locator("table tbody tr")

# 提取
for i in range(rows.count()):
    cells = rows.nth(i).locator("td")
    name = cells.nth(0).text_content()
    value = cells.nth(1).text_content()

# 結構化 → JSON / CSV
```

## 範例檔案

| 檔案 | 說明 |
|------|------|
| `01_text_extraction.py` | 提取文字、屬性、HTML |
| `02_table_scraping.py` | 表格資料爬取與結構化 |
| `03_export_json_csv.py` | 匯出為 JSON 和 CSV |

## 資料科學應用

這一章的技能直接對應資料科學工作流中的「資料收集」階段：
- 無 API 的網站 → 用 Playwright 擷取
- 動態載入的內容（JavaScript 渲染）→ Playwright 可以等待完成
- 需要登入才能看到的資料 → 搭配 ch06 Session 管理

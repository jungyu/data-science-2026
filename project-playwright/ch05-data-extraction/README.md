# Ch05 — 資料擷取

![Ch05 資料擷取](ch05.png)

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

| 檔案 | 需要網路 | 說明 |
|------|---------|------|
| `01_text_extraction.py` | ✅（playwright.dev） | 提取文字、屬性、HTML |
| `02_table_scraping.py` | ❌（自建 HTML） | 表格資料爬取與結構化 |
| `03_export_json_csv.py` | ❌（自建 HTML） | 匯出為 JSON 和 CSV |
| `test_extractor.py` | ❌ | 純函式單元測試（不需要瀏覽器） |

## 資料科學應用

這一章的技能直接對應資料科學工作流中的「資料收集」階段：
- 無 API 的網站 → 用 Playwright 擷取
- 動態載入的內容（JavaScript 渲染）→ Playwright 可以等待完成
- 需要登入才能看到的資料 → 搭配 ch06 Session 管理

## 純函式測試

`02_table_scraping.py` 把「DOM 取值」和「字串→字典轉換」拆成兩個函式：

```
scrape_table(page, selector)   ← 瀏覽器互動層（需要 Chromium）
      ↓ 傳入 headers + raw_rows
rows_to_dicts(headers, raw)    ← 資料轉換層（純 Python，可單元測試）
```

測試轉換層只需要 `pytest`，不需要啟動瀏覽器：

```bash
pytest ch05-data-extraction/test_extractor.py -v
```

## 道德與法律提醒

- 擷取前請確認目標網站的 `robots.txt` 是否允許爬取
- 遵守網站服務條款（Terms of Service）
- 控制請求頻率，避免對伺服器造成過大負擔
- 爬取的資料僅限學術研究和個人使用，勿用於商業目的
- 涉及個人資料時需遵守個資法與隱私保護法規

## 自我檢核

完成本章後，你應該能回答：

1. `text_content()` 和 `inner_text()` 的差別是什麼？哪個結果更接近使用者看到的文字？
2. `02_table_scraping.py` 把邏輯拆成 `scrape_table`（瀏覽器層）和 `rows_to_dicts`（轉換層）。如果不拆，寫測試會遇到什麼困難？
3. 執行 `test_extractor.py`，觀察所有測試的執行時間。比一下 ch07 的 E2E 測試需要多久。

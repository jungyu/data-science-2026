# Ch01 — 初探瀏覽器自動化

## 學習目標

- 理解 Playwright 的 sync API 基本用法
- 啟動瀏覽器、建立頁面、導航至網址
- 擷取頁面截圖與 PDF
- 了解 headless 與 headed 模式的差異

## 核心觀念

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()      # 啟動瀏覽器
    page = browser.new_page()          # 建立新頁面
    page.goto("https://example.com")   # 導航至網址
    page.screenshot(path="shot.png")   # 截圖
    browser.close()                    # 關閉瀏覽器
```

**生命週期**：`Playwright → Browser → BrowserContext → Page`

## 範例檔案

| 檔案 | 說明 |
|------|------|
| `01_open_browser.py` | 最基礎：開啟瀏覽器並印出標題 |
| `02_navigate_and_screenshot.py` | 導航多個頁面並截圖 |
| `03_pdf_export.py` | 將網頁匯出為 PDF（僅 Chromium） |
| `04_browser_context.py` | 使用 BrowserContext 隔離瀏覽狀態 |

## 練習

1. 修改 `01_open_browser.py`，改用 `headed` 模式觀察瀏覽器實際動作
2. 在 `02_navigate_and_screenshot.py` 中加入你常用的網站
3. 嘗試用 `firefox` 取代 `chromium` 看看有什麼差異

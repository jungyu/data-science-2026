# Ch07 — pytest-playwright 測試整合

## 學習目標

- 使用 pytest-playwright 撰寫自動化測試
- 了解 fixture 機制與 page 注入
- 撰寫 E2E 測試流程
- 使用 Trace Viewer 除錯

## 核心觀念

`pytest-playwright` 提供現成的 fixture：
- `page`：自動建立的 Playwright Page（每個測試一個）
- `context`：BrowserContext
- `browser`：Browser 實例

```python
# 只要宣告 page 參數，pytest-playwright 會自動注入
def test_example(page):
    page.goto("https://example.com")
    assert page.title() == "Example Domain"
```

## 執行測試

```bash
# 基本執行
pytest ch07-testing/

# 顯示瀏覽器畫面
pytest ch07-testing/ --headed

# 慢速模式（方便觀察）
pytest ch07-testing/ --headed --slowmo 500

# 指定瀏覽器
pytest ch07-testing/ --browser chromium
pytest ch07-testing/ --browser firefox

# 開啟 Trace（除錯用）
pytest ch07-testing/ --tracing on

# 只執行特定測試
pytest ch07-testing/test_basic.py -k "test_title"
```

## Trace Viewer

當測試失敗時，可以用 Trace Viewer 回放：

```bash
playwright show-trace trace.zip
```

## 範例檔案

| 檔案 | 說明 |
|------|------|
| `test_basic.py` | 基礎測試：導航、標題、元素 |
| `test_e2e_search.py` | E2E 流程：搜尋引擎操作 |

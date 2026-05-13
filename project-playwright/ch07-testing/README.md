# Ch07 — pytest-playwright 測試整合

![Ch07 pytest-playwright 測試整合](ch07.png)

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

測試分兩類：

| 類別 | 標記 | 說明 |
|------|------|------|
| 基礎測試 | 無（預設執行） | `test_basic.py`：example.com / playwright.dev，穩定 |
| E2E 測試 | `@pytest.mark.network` | `test_e2e_search.py`：DuckDuckGo，依賴外站 DOM |

E2E 測試預設跳過，避免學生因外站 DOM 改版或網路問題
誤以為是自己的程式寫錯。

```bash
# 基礎測試（預設，不跑 E2E）
pytest ch07-testing/

# 全部執行，包含 E2E
pytest ch07-testing/ --run-network

# 只跑 E2E
pytest ch07-testing/ -m network --run-network

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

## 自我檢核

完成本章後，你應該能回答：

1. pytest-playwright 的 `page` fixture 是怎麼來的？你在測試函式裡宣告參數名稱，pytest 怎麼知道要注入什麼？
2. 為什麼 `test_e2e_search.py` 預設不執行？如果你把它加入 CI 自動跑，可能會有什麼問題？
3. 用 `playwright show-trace trace.zip` 可以看到什麼？它和一般的 pytest 錯誤訊息相比，多了哪些資訊？

---

## 與 Ch08 的關係

Ch07 示範的是 **pytest-playwright**：把瀏覽器自動化當作「測試框架」，透過 fixture 驅動，適合 E2E 驗收。

Ch08 則把 Playwright 用在「**生產爬蟲 pipeline**」：長時間跑的 worker、Job Queue、資料庫寫入。這類場景不適合 pytest-playwright fixture（每個 job 生命週期不同、需要自行管理 browser 實例），所以 Ch08 的 `BrowserManager` 直接呼叫 `async_playwright()` 而非依賴 fixture。

簡單記法：

| | pytest-playwright | Playwright SDK（直接） |
|---|---|---|
| 使用場景 | E2E 測試、CI 驗收 | 爬蟲 worker、批次任務 |
| 觸發方式 | `pytest` 指令 | 直接執行 Python 腳本 |
| 本課章節 | Ch07 | Ch08 |

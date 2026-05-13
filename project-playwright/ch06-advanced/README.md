# Ch06 — 進階技巧

![Ch06 進階技巧](ch06.png)

## 學習目標

- 使用 Stealth 模式規避反爬蟲偵測
- 管理 Session（Cookie / localStorage）跨次保持登入
- 設定 Proxy 與自訂 User-Agent
- 處理彈窗、Cookie Banner、驗證頁面

> 本章參考 [DataScout/playwright_base](https://github.com/jungyu/DataScout/tree/main/playwright_base) 的設計模式，以現代化做法重新實現。

## 核心觀念

網站的反爬蟲機制通常偵測以下特徵：
1. `navigator.webdriver` 為 `true`（Playwright 預設會設定）
2. 無正常的瀏覽器指紋（plugins、語系、螢幕解析度）
3. 請求頻率異常快速
4. 缺少 Cookie 或 Session

**應對策略**：Stealth JS 注入 + 合理延遲 + Session 重用

## 範例檔案

| 檔案 | 需要網路 | 說明 |
|------|---------|------|
| `01_stealth_mode.py` | ❌（自建 HTML） | Stealth JS 注入，示範部分自動化特徵的改寫方式 |
| `02_session_management.py` | ✅（example.com） | 儲存/載入 Cookie 與 localStorage |
| `03_proxy_and_headers.py` | ❌（本機驗證） | Proxy 設定與自訂 HTTP 標頭 |
| `04_popup_handler.py` | ❌（自建 HTML） | 處理 Cookie Banner 與彈窗 |
| `05_async_preview.py` | ✅（3 個外部站） | Async API 預覽（ch08 的語法準備） |

## 道德與法律提醒

- 遵守目標網站的 robots.txt 和服務條款
- 控制請求頻率，不要對伺服器造成過大負擔
- 爬取的資料僅限於學術研究和個人使用
- 涉及個人資料時需遵守隱私保護法規

## 自我檢核

完成本章後，你應該能回答：

1. Playwright 爬蟲為什麼預設會被部分網站識別？`navigator.webdriver` 的值正常瀏覽器和自動化瀏覽器有什麼不同？
2. Session 管理（儲存 Cookie）能解決什麼問題？什麼情況下 Session 會失效，需要重新登入？
3. 執行 `05_async_preview.py`，比較 sync 和 async 版本的耗時。如果改成同時抓 10 個頁面，差距會更大還是更小？

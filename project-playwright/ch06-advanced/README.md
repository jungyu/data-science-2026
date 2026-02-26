# Ch06 — 進階技巧

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

| 檔案 | 說明 |
|------|------|
| `01_stealth_mode.py` | Stealth JS 注入，隱藏自動化特徵 |
| `02_session_management.py` | 儲存/載入 Cookie 與 localStorage |
| `03_proxy_and_headers.py` | Proxy 設定與自訂 HTTP 標頭 |
| `04_popup_handler.py` | 處理 Cookie Banner 與彈窗 |

## 道德與法律提醒

- 遵守目標網站的 robots.txt 和服務條款
- 控制請求頻率，不要對伺服器造成過大負擔
- 爬取的資料僅限於學術研究和個人使用
- 涉及個人資料時需遵守隱私保護法規

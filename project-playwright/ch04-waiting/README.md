# Ch04 — 等待策略

![Ch04 等待策略](ch04.png)

## 學習目標

- 理解 Playwright 的自動等待機制
- 掌握顯式等待的使用時機
- 監聽網路請求與回應事件
- 處理動態載入的內容（AJAX、SPA）

## 核心觀念

Playwright 的 Locator 動作（click、fill 等）都**內建自動等待**，
但有些場景仍需手動控制等待：

```python
# ✅ 自動等待：大多數情況夠用
page.locator("button").click()

# 🔧 顯式等待：特殊場景
page.wait_for_selector(".loaded")       # 等待元素出現
page.wait_for_load_state("networkidle") # 等待網路靜止
page.wait_for_url("**/dashboard")       # 等待 URL 變更
```

## 範例檔案

| 檔案 | 需要網路 | 說明 |
|------|---------|------|
| `01_auto_waiting.py` | ❌（自建 HTML） | Playwright 自動等待機制 |
| `02_explicit_wait.py` | ✅（playwright.dev） | 顯式等待：selector、URL、load state |
| `03_network_events.py` | ✅（playwright.dev） | 攔截與監聽網路請求 |
| `04_error_and_retry.py` | ✅（example.com） | TimeoutError 捕捉與重試策略 |

## 自我檢核

完成本章後，你應該能回答：

1. 什麼情況下 Playwright 的自動等待「不夠」，必須用 `wait_for_selector()` 或 `wait_for_load_state("networkidle")`？
2. `PlaywrightTimeoutError` 應該在哪一層捕捉？捕捉後應該做什麼（重試、跳過、記錄）？
3. 指數退避（exponential backoff）的原理是什麼？為什麼不用固定間隔重試？

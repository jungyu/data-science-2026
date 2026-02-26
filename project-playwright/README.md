# Playwright 漸進式學習專案

> 從零開始掌握瀏覽器自動化與網頁資料擷取

## 專案目標

提供一個**開箱即用**的 Playwright 學習環境，讓學生：

1. 不再踩坑環境設置，一鍵完成安裝驗證
2. 依章節循序漸進，從基礎到進階
3. 每個範例都可獨立執行，即學即練
4. 掌握資料科學中「網頁資料擷取」的實戰技能

## 前置需求

- Python 3.11+
- pip 或 uv 套件管理工具

## 快速開始

```bash
# 1. 進入專案目錄
cd project-playwright

# 2. 建立虛擬環境
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows

# 3. 安裝依賴
pip install -e ".[all]"

# 4. 安裝 Playwright 瀏覽器
playwright install chromium

# 5. 驗證安裝
python ch00-setup/verify_install.py

# 6. 複製環境設定
cp .env.example .env
```

## 章節導覽

| 章節 | 主題 | 學習重點 |
|------|------|----------|
| **ch00** | 環境設置 | 安裝驗證、專案結構認識 |
| **ch01** | 初探瀏覽器自動化 | 開啟瀏覽器、導航、截圖 |
| **ch02** | 元素選擇器 | CSS / Text / Locator API |
| **ch03** | 頁面互動 | 點擊、輸入、表單、檔案上傳 |
| **ch04** | 等待策略 | 自動等待、顯式等待、網路事件 |
| **ch05** | 資料擷取 | 文字提取、表格爬取、匯出 JSON/CSV |
| **ch06** | 進階技巧 | Stealth 模式、Session 管理、Proxy |
| **ch07** | 測試整合 | pytest-playwright、E2E 測試 |

## 專案結構

```
project-playwright/
├── pyproject.toml          # 套件設定與依賴管理
├── conftest.py             # pytest 全域 fixtures
├── .env.example            # 環境變數範本
├── ch00-setup/             # 環境設置與驗證
├── ch01-first-steps/       # 基礎瀏覽器操作
├── ch02-selectors/         # 元素選擇策略
├── ch03-interaction/       # 頁面互動操作
├── ch04-waiting/           # 等待與同步策略
├── ch05-data-extraction/   # 資料擷取與匯出
├── ch06-advanced/          # 進階：隱匿、Session、代理
├── ch07-testing/           # pytest-playwright 測試
├── utils/                  # 共用工具模組
└── examples/               # 完整實戰範例
```

## 學習建議

1. **依序學習**：ch00 → ch07，每章建立在前一章基礎上
2. **動手執行**：每個 `.py` 檔都可獨立跑，先跑再讀程式碼
3. **修改實驗**：改 selector、改目標網址、觀察不同結果
4. **搭配文件**：善用 [Playwright Python 官方文件](https://playwright.dev/python/)

## 參考來源

本專案參考 [DataScout/playwright_base](https://github.com/jungyu/DataScout/tree/main/playwright_base) 的設計模式，並以現代化實踐重新設計，專注於教學場景。

"""
Ch01-01 — 開啟瀏覽器並印出頁面標題。

這是最基礎的 Playwright 範例，示範完整的瀏覽器生命週期：
啟動 → 建立頁面 → 導航 → 取得資訊 → 關閉

執行方式：
    python ch01-first-steps/01_open_browser.py
"""

from playwright.sync_api import sync_playwright


def main():
    with sync_playwright() as p:
        # 啟動 Chromium（headless=False 可看到瀏覽器畫面）
        browser = p.chromium.launch(headless=True)

        # 建立新分頁
        page = browser.new_page()

        # 導航至目標網址
        page.goto("https://example.com")

        # 取得頁面資訊
        print(f"標題: {page.title()}")
        print(f"網址: {page.url}")

        # 關閉瀏覽器
        browser.close()


if __name__ == "__main__":
    main()

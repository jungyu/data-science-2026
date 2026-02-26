"""
Ch03-01 — 基本點擊與文字輸入。

使用 DuckDuckGo 搜尋引擎示範：
- 定位輸入框並輸入文字
- 按下 Enter 送出搜尋
- 等待搜尋結果出現

執行方式：
    python ch03-interaction/01_click_and_type.py
"""

from playwright.sync_api import sync_playwright


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # 導航至 DuckDuckGo
        page.goto("https://duckduckgo.com")
        print(f"[導航] {page.url}")

        # --- fill()：清除並填入文字 ---
        search_box = page.get_by_role("textbox", name="Search")
        search_box.fill("Playwright Python tutorial")
        print("[輸入] 已填入搜尋關鍵字")

        # --- press()：按下鍵盤按鍵 ---
        search_box.press("Enter")
        print("[按鍵] 按下 Enter")

        # 等待搜尋結果載入
        page.wait_for_load_state("domcontentloaded")
        print(f"[結果] 頁面標題: {page.title()}")

        # --- click()：點擊元素 ---
        results = page.locator("[data-testid='result']")
        result_count = results.count()
        print(f"[結果] 找到 {result_count} 筆搜尋結果")

        # 印出前 3 筆結果標題
        for i in range(min(3, result_count)):
            title = results.nth(i).locator("h2").text_content()
            if title:
                print(f"  {i + 1}. {title.strip()}")

        browser.close()


if __name__ == "__main__":
    main()

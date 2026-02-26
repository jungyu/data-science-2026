"""
Ch02-02 — 以角色（Role）和文字定位元素。

Playwright 的 get_by_role() 對應 ARIA 角色，是最推薦的選擇方式，
因為它最接近「使用者如何感知頁面」。

執行方式：
    python ch02-selectors/02_role_and_text.py
"""

from playwright.sync_api import sync_playwright


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://playwright.dev/python/")

        # --- get_by_role：以 ARIA 角色定位 ---
        # 常用角色：button, link, heading, textbox, checkbox, radio, img
        all_links = page.get_by_role("link")
        print(f"[Role] 頁面連結總數: {all_links.count()}")

        headings = page.get_by_role("heading")
        print(f"[Role] 標題數量: {headings.count()}")

        # 帶 name 參數：比對可見文字或 aria-label
        docs_link = page.get_by_role("link", name="Docs")
        print(f"[Role+Name] 'Docs' 連結: 找到 {docs_link.count()} 個")

        # --- get_by_text：以可見文字定位 ---
        # 預設為部分比對（substring match）
        partial = page.get_by_text("Playwright")
        print(f"\n[Text 部分比對] 含 'Playwright' 的元素: {partial.count()}")

        # exact=True 精確比對
        exact = page.get_by_text("Playwright", exact=True)
        print(f"[Text 精確比對] 剛好是 'Playwright': {exact.count()}")

        # --- 印出所有標題文字 ---
        print("\n頁面標題：")
        for i in range(headings.count()):
            text = headings.nth(i).text_content()
            if text and text.strip():
                print(f"  <h?> {text.strip()}")

        browser.close()


if __name__ == "__main__":
    main()

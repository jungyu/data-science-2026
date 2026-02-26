"""
Ch02-01 — Locator API 基礎用法。

示範 Playwright 推薦的元素定位方式，包括：
- CSS 選擇器
- 文字選擇器
- 屬性選擇器
- 複合選擇器

執行方式：
    python ch02-selectors/01_locator_basics.py
"""

from playwright.sync_api import sync_playwright


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://playwright.dev/python/")

        # --- CSS 選擇器 ---
        nav_links = page.locator("nav a")
        print(f"[CSS] 導覽列連結數量: {nav_links.count()}")

        # --- 文字選擇器（精確比對）---
        docs_link = page.locator("text=Docs")
        print(f"[Text] 'Docs' 連結存在: {docs_link.count() > 0}")

        # --- 組合選擇器：CSS + 文字 ---
        nav_docs = page.locator("nav >> text=Docs")
        print(f"[組合] nav 中的 'Docs': {nav_docs.count() > 0}")

        # --- 屬性選擇器 ---
        links_with_href = page.locator("a[href*='docs']")
        print(f"[屬性] 含 'docs' 的連結數量: {links_with_href.count()}")

        # --- 列出所有導覽連結的文字 ---
        print("\n導覽列連結：")
        for i in range(nav_links.count()):
            text = nav_links.nth(i).text_content()
            if text and text.strip():
                print(f"  - {text.strip()}")

        browser.close()


if __name__ == "__main__":
    main()

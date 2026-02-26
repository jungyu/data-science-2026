"""
Ch05-01 — 提取文字、屬性、HTML 內容。

從頁面中擷取各種類型的資料，是網頁爬蟲最基礎的操作。

執行方式：
    python ch05-data-extraction/01_text_extraction.py
"""

from playwright.sync_api import sync_playwright


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://playwright.dev/python/")

        # --- 1. text_content()：取得元素的文字內容 ---
        title = page.locator("h1").first.text_content()
        print(f"[文字] 主標題: {title.strip()}")

        # --- 2. inner_text()：取得可見文字（排除隱藏元素）---
        # text_content() 包含隱藏文字，inner_text() 只有可見的
        nav_text = page.locator("nav").first.inner_text()
        print(f"[可見文字] 導覽列: {nav_text[:50]}...")

        # --- 3. get_attribute()：取得 HTML 屬性 ---
        links = page.locator("a[href]")
        print(f"\n[屬性] 前 5 個連結的 href：")
        for i in range(min(5, links.count())):
            href = links.nth(i).get_attribute("href")
            text = (links.nth(i).text_content() or "").strip()[:30]
            print(f"  [{text}] → {href}")

        # --- 4. inner_html()：取得元素的 HTML 內容 ---
        main_html = page.locator("main").first.inner_html()
        print(f"\n[HTML] main 區塊 HTML 長度: {len(main_html)} 字元")

        # --- 5. all_text_contents()：一次取得所有匹配元素的文字 ---
        all_headings = page.locator("h1, h2, h3").all_text_contents()
        print(f"\n[全部文字] 頁面標題列表 ({len(all_headings)} 個)：")
        for heading in all_headings[:8]:
            clean = heading.strip()
            if clean:
                print(f"  - {clean}")

        # --- 6. evaluate()：用 JavaScript 取得複雜資料 ---
        meta_info = page.evaluate("""
            () => ({
                title: document.title,
                charset: document.characterSet,
                links_count: document.querySelectorAll('a').length,
                images_count: document.querySelectorAll('img').length,
            })
        """)
        print(f"\n[JS 評估] 頁面資訊：")
        for key, value in meta_info.items():
            print(f"  {key}: {value}")

        browser.close()


if __name__ == "__main__":
    main()

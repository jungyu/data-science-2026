"""
Ch02-03 — 鏈式選擇（Chaining）與篩選（Filtering）。

當頁面元素很多時，可以用鏈式定位縮小範圍，
或用 filter() 從多個匹配結果中篩選出需要的。

執行方式：
    python ch02-selectors/03_chaining_and_filtering.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.console import setup_stdout

from playwright.sync_api import sync_playwright


def main() -> None:
    setup_stdout()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto("https://playwright.dev/python/")

        # --- 鏈式定位（Chaining）---
        # 先定位父容器，再往下找子元素
        nav = page.locator("nav")
        nav_links = nav.get_by_role("link")
        print(f"[鏈式] 導覽列中的連結: {nav_links.count()}")

        # --- 篩選（Filtering）---
        # 從所有連結中篩選出文字含 "API" 的
        all_links = page.get_by_role("link")
        api_links = all_links.filter(has_text="API")
        print(f"[篩選] 含 'API' 文字的連結: {api_links.count()}")

        # --- filter + has：包含特定子元素 ---
        # 找到所有包含 <svg> 圖示的連結
        links_with_icon = all_links.filter(has=page.locator("svg"))
        print(f"[篩選] 含 SVG 圖示的連結: {links_with_icon.count()}")

        # --- nth() 取第 N 個 ---
        if nav_links.count() > 0:
            first_link = nav_links.first
            last_link = nav_links.last
            # text_content() 可能為 None（icon-only link）；退而顯示 href
            def link_label(loc) -> str:
                text = (loc.text_content() or "").strip()
                return text or loc.get_attribute("href") or "<no text>"
            print(f"\n[nth] 第一個導覽連結: {link_label(first_link)}")
            print(f"[nth] 最後一個導覽連結: {link_label(last_link)}")

        # --- 實用模式：逐一處理匹配結果 ---
        print("\n所有導覽連結的 href：")
        for i in range(nav_links.count()):
            link = nav_links.nth(i)
            text = (link.text_content() or "").strip()
            href = link.get_attribute("href") or ""
            if text:
                print(f"  [{text}] → {href}")

        browser.close()


if __name__ == "__main__":
    main()

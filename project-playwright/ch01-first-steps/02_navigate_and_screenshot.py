"""
Ch01-02 — 導航至多個頁面並截圖。

示範：
- 連續導航不同網址
- 截取全頁與指定區域截圖
- 使用 viewport 控制瀏覽器尺寸

執行方式：
    python ch01-first-steps/02_navigate_and_screenshot.py
"""

from pathlib import Path
from playwright.sync_api import sync_playwright

OUTPUT_DIR = Path(__file__).parent.parent / "output" / "screenshots"


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # 建立頁面並指定視窗大小
        page = browser.new_page(viewport={"width": 1280, "height": 720})

        # --- 範例 1：基本截圖 ---
        page.goto("https://example.com")
        page.screenshot(path=str(OUTPUT_DIR / "example_com.png"))
        print(f"[截圖] example.com → {OUTPUT_DIR / 'example_com.png'}")

        # --- 範例 2：全頁截圖（包含捲軸以下的內容）---
        page.goto("https://playwright.dev/python/")
        page.screenshot(
            path=str(OUTPUT_DIR / "playwright_fullpage.png"),
            full_page=True,
        )
        print(f"[截圖] playwright.dev 全頁 → {OUTPUT_DIR / 'playwright_fullpage.png'}")

        # --- 範例 3：指定元素截圖 ---
        hero = page.locator("main .hero")
        if hero.count() > 0:
            hero.first.screenshot(path=str(OUTPUT_DIR / "playwright_hero.png"))
            print(f"[截圖] hero 區塊 → {OUTPUT_DIR / 'playwright_hero.png'}")

        browser.close()
        print("\n✅ 所有截圖完成！請查看 output/screenshots/ 資料夾。")


if __name__ == "__main__":
    main()

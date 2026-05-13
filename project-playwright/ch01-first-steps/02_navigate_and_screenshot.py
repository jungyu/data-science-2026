"""
Ch01-02 — 導航至多個頁面並截圖。

示範：
- 連續導航不同網址
- 截取全頁與指定區域截圖
- 使用 viewport 控制瀏覽器尺寸

執行方式：
    python ch01-first-steps/02_navigate_and_screenshot.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.console import setup_stdout

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

OUTPUT_DIR = Path(__file__).parent.parent / "output" / "screenshots"


def main() -> None:
    setup_stdout()
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

        # --- 範例 3：指定元素截圖（外部網站 DOM 可能隨時更新，允許略過）---
        # 注意：selector 依賴第三方網站結構，若找不到元素會提示略過而非報錯
        try:
            hero = page.locator("h1").first
            if hero.count() > 0:
                hero.screenshot(path=str(OUTPUT_DIR / "playwright_hero.png"))
                print(f"[截圖] h1 標題區塊 → {OUTPUT_DIR / 'playwright_hero.png'}")
            else:
                print("[略過] 找不到 h1 元素，跳過區塊截圖。")
        except PlaywrightTimeoutError:
            print("[略過] 元素截圖逾時，跳過區塊截圖。")
        except PlaywrightError as e:
            # Playwright 內部錯誤（element detached / page navigated 等），不再吞掉其他類型
            print(f"[略過] 元素截圖失敗（{e}），跳過區塊截圖。")

        browser.close()

    print("\n[完成] 所有截圖完成，請查看 output/screenshots/ 資料夾。")


if __name__ == "__main__":
    main()

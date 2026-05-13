"""
Ch03-01 — 基本點擊與文字輸入。

使用 Wikipedia 的「特殊：搜尋」頁面示範：
- 定位搜尋輸入框並輸入文字
- 按下 Enter 送出搜尋
- 等待搜尋結果頁載入

為什麼用 Wikipedia 而不是 Google / DuckDuckGo？
    搜尋引擎會頻繁改版、套用 CAPTCHA、做機器人偵測，
    教學腳本綁到它們會三天兩頭壞掉。
    Wikipedia 的 Special:Search 結構穩定、無反爬機制、繁體支援好。

執行方式：
    python ch03-interaction/01_click_and_type.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.console import setup_stdout

from playwright.sync_api import TimeoutError as PwTimeout, sync_playwright


def main() -> None:
    setup_stdout()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # 導航至 Wikipedia 中文首頁
        page.goto("https://zh.wikipedia.org/", wait_until="domcontentloaded")
        print(f"[導航] {page.url}")

        # --- fill()：清除並填入文字 ---
        # Wikipedia 的搜尋框 name="search"，結構穩定多年未變
        search_box = page.locator("input[name='search']").first
        search_box.wait_for()
        search_box.fill("Playwright 軟體")
        print("[輸入] 已填入搜尋關鍵字")

        # --- press()：按下鍵盤按鍵 ---
        # Wikipedia 對精確比對的關鍵字會直接導到該條目，
        # 對模糊比對則導到搜尋結果頁（兩種情況都會觸發 navigation）
        search_box.press("Enter")
        print("[按鍵] 按下 Enter")

        try:
            # 等到網路安靜，跨「導到條目」與「導到搜尋結果頁」兩種情況
            page.wait_for_load_state("networkidle", timeout=15_000)
        except PwTimeout:
            print("[!] 載入逾時——網路可能較慢")
            browser.close()
            return

        print(f"[結果] 頁面標題: {page.title()}")
        print(f"[結果] 最終 URL : {page.url}")

        # --- click()：示範 click 元素 ---
        # 找頁面內第一個「有文字」的內文連結（跳過 logo / 圖示等空 anchor）
        links = page.locator("#mw-content-text a[href^='/wiki/']")
        for i in range(min(links.count(), 30)):
            link = links.nth(i)
            text = (link.text_content() or "").strip()
            if text:
                print(f"[找到] 第一個有文字的連結：{text!r} → {link.get_attribute('href')}")
                break
        else:
            print("[結果] 頁面內未找到有文字的 /wiki/ 連結")

        browser.close()
        print("\n[完成] ch03-01 基本點擊 / 輸入 / 按鍵示範結束。")


if __name__ == "__main__":
    main()

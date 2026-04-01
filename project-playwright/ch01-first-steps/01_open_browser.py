"""
Ch01-01 — 開啟瀏覽器並印出頁面標題。

這是最基礎的 Playwright 範例，示範完整的瀏覽器生命週期：
啟動 → 建立頁面 → 導航 → 取得資訊 → 關閉

執行方式：
    python ch01-first-steps/01_open_browser.py             # headed 模式，可看到瀏覽器畫面
    python ch01-first-steps/01_open_browser.py --headless  # headless 模式，無視窗執行
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.console import setup_stdout

from playwright.sync_api import sync_playwright


def main() -> None:
    setup_stdout()

    parser = argparse.ArgumentParser(description="Ch01-01: 開啟瀏覽器並印出頁面標題")
    parser.add_argument("--headless", action="store_true", help="以無頭模式執行（不顯示瀏覽器視窗）")
    args = parser.parse_args()

    with sync_playwright() as p:
        # 預設 headless=False，讓初學者能觀察瀏覽器開啟過程
        browser = p.chromium.launch(headless=args.headless)

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

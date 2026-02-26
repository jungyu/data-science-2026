"""
Ch01-04 — 使用 BrowserContext 隔離瀏覽狀態。

BrowserContext 類似「無痕視窗」，每個 Context 有獨立的：
- Cookie
- localStorage / sessionStorage
- 快取

這讓你可以在同一個 Browser 中模擬多個使用者。

執行方式：
    python ch01-first-steps/04_browser_context.py
"""

from playwright.sync_api import sync_playwright


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # --- Context 1：繁體中文使用者 ---
        ctx_tw = browser.new_context(
            locale="zh-TW",
            timezone_id="Asia/Taipei",
            viewport={"width": 1280, "height": 720},
        )
        page_tw = ctx_tw.new_page()
        page_tw.goto("https://example.com")
        print(f"[TW] 標題: {page_tw.title()}")
        print(f"[TW] 語系: zh-TW, 時區: Asia/Taipei")

        # --- Context 2：日文使用者 ---
        ctx_jp = browser.new_context(
            locale="ja-JP",
            timezone_id="Asia/Tokyo",
            viewport={"width": 375, "height": 812},  # iPhone 尺寸
        )
        page_jp = ctx_jp.new_page()
        page_jp.goto("https://example.com")
        print(f"\n[JP] 標題: {page_jp.title()}")
        print(f"[JP] 語系: ja-JP, 時區: Asia/Tokyo")

        # 兩個 Context 的 Cookie 互不影響
        ctx_tw.add_cookies([{
            "name": "user",
            "value": "taiwan_user",
            "domain": "example.com",
            "path": "/",
        }])

        tw_cookies = ctx_tw.cookies()
        jp_cookies = ctx_jp.cookies()
        print(f"\n[TW] Cookie 數量: {len(tw_cookies)}")
        print(f"[JP] Cookie 數量: {len(jp_cookies)}  ← 互不影響")

        # 關閉所有 Context 與瀏覽器
        ctx_tw.close()
        ctx_jp.close()
        browser.close()


if __name__ == "__main__":
    main()

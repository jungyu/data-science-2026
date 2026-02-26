"""
Ch06-03 — Proxy 設定與自訂 HTTP 標頭。

示範：
- 透過 Proxy 發送請求
- 自訂 User-Agent 和其他 HTTP 標頭
- 驗證 IP 和標頭是否正確套用

參考：DataScout/playwright_base/anti_detection/proxy_manager.py

執行方式：
    python ch06-advanced/03_proxy_and_headers.py
"""

import os
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

load_dotenv()


def demo_custom_headers():
    """示範自訂 HTTP 標頭。"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # 在 Context 層級設定 User-Agent 和其他標頭
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            extra_http_headers={
                "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
                "Accept-Encoding": "gzip, deflate, br",
            },
        )

        page = context.new_page()

        # 用 httpbin 驗證實際送出的標頭
        page.goto("https://httpbin.org/headers")
        page.wait_for_load_state("domcontentloaded")

        # 提取回應的 JSON 內容
        content = page.locator("pre").text_content()
        print("=== 自訂 HTTP 標頭 ===")
        print(f"  回應內容（前 500 字元）:\n{content[:500]}")

        context.close()
        browser.close()


def demo_proxy():
    """示範 Proxy 設定（需要有可用的 Proxy）。"""
    proxy_server = os.getenv("PROXY_SERVER")

    if not proxy_server:
        print("\n=== Proxy 設定（未啟用）===")
        print("  PROXY_SERVER 環境變數未設定，跳過 Proxy 示範。")
        print("  設定方式：在 .env 中加入 PROXY_SERVER=http://your-proxy:8080")
        print("\n  Playwright Proxy 設定範例：")
        print("    browser = p.chromium.launch(proxy={")
        print('        "server": "http://proxy.example.com:8080",')
        print('        "username": "user",    # 選填')
        print('        "password": "pass",    # 選填')
        print("    })")
        return

    print(f"\n=== Proxy 設定 ===")
    print(f"  使用 Proxy: {proxy_server}")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            proxy={"server": proxy_server},
        )
        page = browser.new_page()

        try:
            page.goto("https://httpbin.org/ip", timeout=10000)
            content = page.locator("pre").text_content()
            print(f"  Proxy IP: {content.strip()}")
        except Exception as e:
            print(f"  Proxy 連線失敗: {e}")
        finally:
            browser.close()


def main():
    demo_custom_headers()
    demo_proxy()
    print("\n✅ 標頭與 Proxy 設定示範完成。")


if __name__ == "__main__":
    main()

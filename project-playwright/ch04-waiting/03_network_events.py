"""
Ch04-03 — 網路事件攔截與監聽。

Playwright 可以監聽和攔截瀏覽器的網路請求，
這在資料擷取和 API 分析時非常有用。

執行方式：
    python ch04-waiting/03_network_events.py
"""

from playwright.sync_api import sync_playwright


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # --- 1. 監聽所有請求 ---
        requests_log = []

        def on_request(request):
            requests_log.append({
                "method": request.method,
                "url": request.url[:80],
                "type": request.resource_type,
            })

        page.on("request", on_request)

        page.goto("https://example.com")
        print(f"[監聽] 捕獲到 {len(requests_log)} 個請求：")
        for req in requests_log[:5]:
            print(f"  {req['method']} [{req['type']}] {req['url']}")

        # --- 2. 監聽回應 ---
        page.remove_listener("request", on_request)
        responses_log = []

        def on_response(response):
            responses_log.append({
                "status": response.status,
                "url": response.url[:80],
            })

        page.on("response", on_response)

        page.goto("https://playwright.dev/python/")
        print(f"\n[回應] 捕獲到 {len(responses_log)} 個回應：")
        for res in responses_log[:5]:
            print(f"  [{res['status']}] {res['url']}")

        # --- 3. 等待特定請求 ---
        page.remove_listener("response", on_response)

        # wait_for_response：等待符合條件的回應
        with page.expect_response(lambda r: "playwright" in r.url) as response_info:
            page.reload()
        response = response_info.value
        print(f"\n[等待回應] status={response.status}, url={response.url[:60]}")

        # --- 4. 攔截請求（route）---
        # 阻擋所有圖片請求（加速載入）
        blocked_count = 0

        def block_images(route):
            nonlocal blocked_count
            if route.request.resource_type == "image":
                blocked_count += 1
                route.abort()
            else:
                route.continue_()

        page.route("**/*", block_images)
        page.goto("https://playwright.dev/python/")
        print(f"\n[攔截] 已阻擋 {blocked_count} 個圖片請求")

        # --- 5. 修改請求標頭 ---
        page.unroute("**/*")

        def add_custom_header(route):
            headers = {**route.request.headers, "X-Custom": "playwright-demo"}
            route.continue_(headers=headers)

        page.route("**/*", add_custom_header)
        page.goto("https://example.com")
        print("[標頭] 已為所有請求加上自訂 Header")

        browser.close()


if __name__ == "__main__":
    main()

"""
Ch04-01 — Playwright 自動等待機制。

Playwright 的 Locator 動作會自動：
1. 等待元素出現在 DOM 中
2. 等待元素可見（visible）
3. 等待元素穩定（停止動畫）
4. 等待元素可互動（enabled, editable）
5. 重試直到超時（預設 30 秒）

執行方式：
    python ch04-waiting/01_auto_waiting.py
"""

from playwright.sync_api import sync_playwright, TimeoutError


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # 建立一個模擬延遲載入的頁面
        page.set_content("""
        <html><body>
            <h1>自動等待示範</h1>
            <button id="load-btn" onclick="loadContent()">載入內容</button>
            <div id="container"></div>
            <script>
                function loadContent() {
                    document.getElementById('load-btn').disabled = true;
                    document.getElementById('load-btn').textContent = '載入中...';

                    // 模擬 API 延遲 2 秒
                    setTimeout(() => {
                        document.getElementById('container').innerHTML = `
                            <div class="result" style="padding:10px; background:#e8f5e9;">
                                <h2>載入完成！</h2>
                                <p>這是延遲載入的內容。</p>
                                <button id="action-btn">執行動作</button>
                            </div>
                        `;
                    }, 2000);
                }
            </script>
        </body></html>
        """)

        # --- 自動等待：點擊按鈕 ---
        page.locator("#load-btn").click()
        print("[點擊] 已點擊載入按鈕")

        # --- 自動等待：Locator 會等到元素出現才繼續 ---
        # 不需要 sleep 或 wait_for_selector！
        result = page.locator(".result h2")
        text = result.text_content()
        print(f"[自動等待] 內容: {text}")

        # --- 自動等待：新按鈕也能直接操作 ---
        action_btn = page.locator("#action-btn")
        print(f"[自動等待] 按鈕可見: {action_btn.is_visible()}")

        # --- 超時處理 ---
        try:
            # 嘗試找一個不存在的元素（設定短超時）
            page.locator("#nonexistent").click(timeout=2000)
        except TimeoutError:
            print("[超時] 2 秒內找不到 #nonexistent（預期行為）")

        # --- 自訂全域超時 ---
        page_with_timeout = browser.new_page()
        page_with_timeout.set_default_timeout(5000)  # 全域 5 秒超時
        print(f"\n[設定] 已將預設超時改為 5 秒")
        page_with_timeout.close()

        browser.close()


if __name__ == "__main__":
    main()

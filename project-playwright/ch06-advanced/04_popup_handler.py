"""
Ch06-04 — 處理彈窗、Cookie Banner、對話框。

許多網站會彈出 Cookie 同意、廣告、登入提示等，
需要在爬取前自動關閉它們。

參考：DataScout/playwright_base/core/popup_handler.py

執行方式：
    python ch06-advanced/04_popup_handler.py
"""

from playwright.sync_api import sync_playwright, Page

# 常見彈窗的 CSS 選擇器
DEFAULT_POPUP_SELECTORS = {
    "cookie_banners": [
        "[class*='cookie'] button[class*='accept']",
        "[class*='cookie'] button[class*='agree']",
        "[id*='cookie'] button[class*='accept']",
        "[class*='consent'] button[class*='accept']",
        "button[id*='accept-cookies']",
        ".cc-btn.cc-dismiss",
    ],
    "close_buttons": [
        "button[class*='close']",
        "button[aria-label='Close']",
        "button[aria-label='關閉']",
        "[class*='modal'] button[class*='close']",
        ".popup-close",
        "[data-dismiss='modal']",
    ],
    "overlay_dismiss": [
        ".modal-backdrop",
        "[class*='overlay']",
    ],
}


def handle_popups(page: Page, custom_selectors: dict | None = None, timeout: int = 2000):
    """嘗試關閉頁面上的各種彈窗。

    Args:
        page: Playwright 頁面物件
        custom_selectors: 自訂選擇器（會合併到預設選擇器中）
        timeout: 每個選擇器的等待超時（毫秒）
    """
    selectors = {**DEFAULT_POPUP_SELECTORS}
    if custom_selectors:
        for key, values in custom_selectors.items():
            selectors.setdefault(key, []).extend(values)

    closed_count = 0

    for category, selector_list in selectors.items():
        for selector in selector_list:
            try:
                element = page.locator(selector).first
                if element.is_visible(timeout=timeout):
                    element.click(timeout=timeout)
                    closed_count += 1
                    print(f"  [關閉] {category}: {selector}")
            except Exception:
                # 找不到或無法點擊，跳過
                pass

    return closed_count


def handle_dialog(page: Page):
    """自動處理 JavaScript alert / confirm / prompt 對話框。"""
    def on_dialog(dialog):
        print(f"  [對話框] 類型: {dialog.type}, 訊息: {dialog.message}")
        dialog.accept()

    page.on("dialog", on_dialog)


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # --- 1. 示範 JavaScript 對話框處理 ---
        print("=== JavaScript 對話框處理 ===")
        handle_dialog(page)

        page.set_content("""
        <html><body>
            <h1>對話框測試</h1>
            <button onclick="alert('這是一個 alert!')">Alert</button>
            <button onclick="confirm('確定要繼續嗎？')">Confirm</button>
        </body></html>
        """)

        # 觸發 alert
        page.locator("button", has_text="Alert").click()
        # 觸發 confirm
        page.locator("button", has_text="Confirm").click()

        # --- 2. 示範 Cookie Banner 處理 ---
        print("\n=== Cookie Banner 處理（模擬）===")
        page.set_content("""
        <html><body>
            <h1>主要內容</h1>
            <div class="cookie-banner" style="position:fixed; bottom:0; left:0; right:0;
                 background:#333; color:white; padding:20px; z-index:1000;">
                <p>本網站使用 Cookie 以提供最佳體驗。</p>
                <button class="accept-cookies"
                        onclick="this.parentElement.style.display='none'">
                    接受所有 Cookie
                </button>
            </div>
        </body></html>
        """)

        # 檢查 banner 是否存在
        banner = page.locator(".cookie-banner")
        print(f"  Banner 可見: {banner.is_visible()}")

        # 關閉 banner
        closed = handle_popups(page)
        print(f"  已關閉 {closed} 個彈窗")
        print(f"  Banner 可見: {banner.is_visible()}")

        # --- 3. 新開頁面（popup window）處理 ---
        print("\n=== 新開頁面（popup）處理 ===")
        page.set_content("""
        <html><body>
            <a href="https://example.com" target="_blank" id="popup-link">
                開新視窗
            </a>
        </body></html>
        """)

        # 攔截新開的頁面
        with page.context.expect_page() as new_page_info:
            page.locator("#popup-link").click()
        new_page = new_page_info.value
        new_page.wait_for_load_state("domcontentloaded")
        print(f"  新頁面 URL: {new_page.url}")
        print(f"  新頁面標題: {new_page.title()}")
        new_page.close()

        browser.close()
        print("\n✅ 彈窗處理示範完成。")


if __name__ == "__main__":
    main()

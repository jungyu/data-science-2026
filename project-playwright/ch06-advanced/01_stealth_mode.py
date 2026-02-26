"""
Ch06-01 — Stealth 模式：隱藏自動化特徵。

許多網站會偵測 navigator.webdriver 等特徵來判斷是否為機器人。
本範例示範如何注入 JavaScript 來規避基本偵測。

參考：DataScout/playwright_base/core/stealth.py

執行方式：
    python ch06-advanced/01_stealth_mode.py
"""

from playwright.sync_api import sync_playwright

# Stealth JS：隱藏 Playwright 自動化特徵
STEALTH_JS = """
() => {
    // 1. 隱藏 navigator.webdriver
    Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined,
    });

    // 2. 偽造 navigator.plugins（正常瀏覽器至少有幾個 plugin）
    Object.defineProperty(navigator, 'plugins', {
        get: () => [1, 2, 3, 4, 5],
    });

    // 3. 偽造 navigator.languages
    Object.defineProperty(navigator, 'languages', {
        get: () => ['zh-TW', 'zh', 'en-US', 'en'],
    });

    // 4. 修正 Chrome 特有屬性
    window.chrome = {
        runtime: {},
        loadTimes: function() {},
        csi: function() {},
        app: {},
    };

    // 5. 修正 Permissions API
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) => (
        parameters.name === 'notifications'
            ? Promise.resolve({ state: Notification.permission })
            : originalQuery(parameters)
    );

    // 6. 隱藏自動化相關的 console 訊息
    const originalLog = console.log;
    console.log = (...args) => {
        if (args[0]?.toString().includes('cdc_')) return;
        originalLog.apply(console, args);
    };
}
"""


def create_stealth_context(playwright, **kwargs):
    """建立帶有 Stealth 模式的 BrowserContext。

    將 Stealth JS 注入到 BrowserContext 的 init script 中，
    這樣每個新開的頁面都會自動套用。
    """
    browser = playwright.chromium.launch(
        headless=kwargs.pop("headless", True),
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-first-run",
            "--no-default-browser-check",
        ],
    )

    context = browser.new_context(
        viewport=kwargs.pop("viewport", {"width": 1920, "height": 1080}),
        user_agent=kwargs.pop("user_agent", None),
        locale=kwargs.pop("locale", "zh-TW"),
        timezone_id=kwargs.pop("timezone_id", "Asia/Taipei"),
        **kwargs,
    )

    # 注入 Stealth JS 到每個新頁面
    context.add_init_script(STEALTH_JS)

    return browser, context


def main():
    with sync_playwright() as p:
        # --- 比較：一般模式 vs Stealth 模式 ---

        # 一般模式
        browser_normal = p.chromium.launch(headless=True)
        page_normal = browser_normal.new_page()
        page_normal.goto("https://example.com")

        webdriver_normal = page_normal.evaluate("navigator.webdriver")
        plugins_normal = page_normal.evaluate("navigator.plugins.length")
        print("--- 一般模式 ---")
        print(f"  navigator.webdriver: {webdriver_normal}")
        print(f"  navigator.plugins.length: {plugins_normal}")
        browser_normal.close()

        # Stealth 模式
        browser_stealth, ctx_stealth = create_stealth_context(p)
        page_stealth = ctx_stealth.new_page()
        page_stealth.goto("https://example.com")

        webdriver_stealth = page_stealth.evaluate("navigator.webdriver")
        plugins_stealth = page_stealth.evaluate("navigator.plugins.length")
        languages = page_stealth.evaluate("navigator.languages")
        has_chrome = page_stealth.evaluate("!!window.chrome")

        print("\n--- Stealth 模式 ---")
        print(f"  navigator.webdriver: {webdriver_stealth}")
        print(f"  navigator.plugins.length: {plugins_stealth}")
        print(f"  navigator.languages: {languages}")
        print(f"  window.chrome 存在: {has_chrome}")

        ctx_stealth.close()
        browser_stealth.close()

        print("\n✅ Stealth 模式能有效隱藏大部分自動化特徵。")


if __name__ == "__main__":
    main()

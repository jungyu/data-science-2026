"""
瀏覽器管理工具。

提供統一的瀏覽器啟動、Context 建立、Stealth 注入等功能，
讓各章節範例可以共用設定。

使用方式：
    from utils.browser import BrowserManager

    with BrowserManager(headless=False) as bm:
        page = bm.new_page()
        page.goto("https://example.com")
"""

import os
from pathlib import Path
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page
from dotenv import load_dotenv

load_dotenv()

# Stealth JS（從 ch06 提取為共用版本，與 ch06/01_stealth_mode.py 保持一致）
_STEALTH_JS = """
() => {
    // 1. 隱藏 navigator.webdriver
    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

    // 2. 偽造 navigator.plugins
    Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });

    // 3. 偽造 navigator.languages
    Object.defineProperty(navigator, 'languages', {
        get: () => ['zh-TW', 'zh', 'en-US', 'en'],
    });

    // 4. 修正 Chrome 特有屬性
    window.chrome = { runtime: {}, loadTimes: function() {}, csi: function() {}, app: {} };

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


class BrowserManager:
    """統一的瀏覽器管理器，支援 Context Manager 模式。"""

    def __init__(
        self,
        headless: bool | None = None,
        browser_type: str | None = None,
        stealth: bool = False,
        slow_mo: int | None = None,
        viewport: dict | None = None,
        locale: str = "zh-TW",
        timezone_id: str = "Asia/Taipei",
        user_agent: str | None = None,
        proxy: dict | None = None,
        storage_state: str | dict | None = None,
    ):
        # 從環境變數讀取預設值
        self.headless = headless if headless is not None else os.getenv("HEADLESS", "true").lower() == "true"
        self.browser_type = browser_type or os.getenv("BROWSER_TYPE", "chromium")
        self.stealth = stealth
        try:
            self.slow_mo = slow_mo if slow_mo is not None else int(os.getenv("SLOW_MO", "0"))
        except ValueError:
            self.slow_mo = 0
        self.locale = locale
        self.timezone_id = timezone_id
        self.user_agent = user_agent
        self.proxy = proxy
        self.storage_state = storage_state
        self.viewport = viewport or {
            "width": int(os.getenv("VIEWPORT_WIDTH", "1280")),
            "height": int(os.getenv("VIEWPORT_HEIGHT", "720")),
        }

        self._playwright = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._contexts: list[BrowserContext] = []

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def start(self):
        """啟動 Playwright 和瀏覽器。"""
        self._playwright = sync_playwright().start()

        launcher = getattr(self._playwright, self.browser_type)

        launch_args = {
            "headless": self.headless,
            "slow_mo": self.slow_mo,
        }
        if self.stealth:
            launch_args["args"] = ["--disable-blink-features=AutomationControlled"]
        if self.proxy:
            launch_args["proxy"] = self.proxy

        self._browser = launcher.launch(**launch_args)
        return self

    def new_context(self, **kwargs) -> BrowserContext:
        """建立新的 BrowserContext。"""
        context_args = {
            "viewport": self.viewport,
            "locale": self.locale,
            "timezone_id": self.timezone_id,
            "ignore_https_errors": True,
        }
        if self.user_agent:
            context_args["user_agent"] = self.user_agent
        if self.storage_state:
            context_args["storage_state"] = self.storage_state

        context_args.update(kwargs)
        context = self._browser.new_context(**context_args)

        if self.stealth:
            context.add_init_script(_STEALTH_JS)

        self._contexts.append(context)
        self._context = context
        return context

    def new_page(self, **kwargs) -> Page:
        """建立新頁面（自動建立 Context）。"""
        if self._context is None:
            self.new_context()
        return self._context.new_page(**kwargs)

    def save_session(self, path: str | Path):
        """儲存目前 Context 的 Session 狀態。"""
        if self._context:
            filepath = Path(path)
            filepath.parent.mkdir(parents=True, exist_ok=True)
            self._context.storage_state(path=str(filepath))

    def close(self):
        """關閉所有資源。"""
        for ctx in self._contexts:
            ctx.close()
        self._contexts.clear()
        self._context = None
        if self._browser:
            self._browser.close()
            self._browser = None
        if self._playwright:
            self._playwright.stop()
            self._playwright = None

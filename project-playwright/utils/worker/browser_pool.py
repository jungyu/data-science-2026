"""
Async Browser Pool — 瀏覽器生命週期管理。

來源文件：docs/supabase/04_crawler/06_worker-consume-loop-python.md

設計原則：
    - 瀏覽器（Browser）長時間保持存活，跨任務重複使用
    - Context（BrowserContext）每個任務短暫建立，用後立即關閉
    - 每處理 N 個任務後自動重啟瀏覽器，防止記憶體/狀態累積

用法：
    async with async_playwright() as pw:
        pool = BrowserPool(pw)
        await pool.start()
        try:
            ctx = await pool.new_context()
            page = await ctx.new_page()
            ...
            await ctx.close()   # 使用端負責關閉 context
        finally:
            await pool.stop()

注意：
    - 此模組需要 playwright[async] 支援（pip install -e ".[supabase]"）
    - 設計為 async 模式，不相容於 ch01-ch07 的同步 BrowserManager
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from playwright.async_api import Browser, BrowserContext, Playwright

logger = logging.getLogger(__name__)


@dataclass
class BrowserPoolConfig:
    """BrowserPool 設定。"""
    max_browsers: int = 2                    # 同時存活的瀏覽器數（目前實作為 1）
    max_contexts_per_browser: int = 5        # 每瀏覽器最大 context 數（供未來擴充）
    browser_restart_after_jobs: int = 50     # 每 N 個任務後重啟瀏覽器


class BrowserPool:
    """管理 Playwright 瀏覽器生命週期。

    Context 為每個任務短暫建立，由呼叫端負責關閉。
    瀏覽器本體長時間存活，避免反覆啟動的開銷。
    """

    def __init__(
        self,
        pw: Playwright,
        config: BrowserPoolConfig | None = None,
    ) -> None:
        self._pw = pw
        self._config = config or BrowserPoolConfig()
        self._browser: Browser | None = None
        self._jobs_since_restart: int = 0

    async def start(self) -> None:
        """啟動 Chromium 瀏覽器。"""
        self._browser = await self._pw.chromium.launch(headless=True)
        self._jobs_since_restart = 0
        logger.info("Browser launched")

    async def stop(self) -> None:
        """關閉瀏覽器，釋放所有資源。"""
        if self._browser:
            await self._browser.close()
            self._browser = None
            logger.info("Browser closed")

    async def new_context(self, **kwargs) -> BrowserContext:
        """建立新的 BrowserContext。

        呼叫端使用完畢後**必須自行呼叫 ctx.close()**。

        每處理 browser_restart_after_jobs 個任務後自動重啟瀏覽器，
        防止記憶體洩漏與狀態污染。

        Args:
            **kwargs: 傳遞給 browser.new_context() 的參數
                      （例如：user_agent、viewport、locale）

        Returns:
            新建立的 BrowserContext
        """
        if self._browser is None:
            await self.start()

        self._jobs_since_restart += 1
        if self._jobs_since_restart >= self._config.browser_restart_after_jobs:
            logger.info(
                "Restarting browser after %d jobs", self._jobs_since_restart
            )
            await self.stop()
            await self.start()

        assert self._browser is not None
        return await self._browser.new_context(**kwargs)

    @property
    def jobs_since_restart(self) -> int:
        """回傳自上次重啟後已處理的任務數，用於監控。"""
        return self._jobs_since_restart

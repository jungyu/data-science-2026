"""
Ch06-05 — Async API 預覽（ch08 的準備）。

ch01–ch05 全部使用 sync API（`sync_playwright`）：
  - 程式碼直觀，適合入門與互動式除錯
  - 一次只做一件事，等完才繼續

ch08 的生產 Pipeline 改用 async API（`async_playwright`）：
  - 可同時等待多個頁面，提升爬取效率
  - 與 FastAPI、資料庫 async client 自然整合

本範例用「同一個任務」對比兩種寫法，
幫助你在進入 ch08 前熟悉 async/await 語法。

執行方式：
    python ch06-advanced/05_async_preview.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.console import setup_stdout

# ── 任務說明 ────────────────────────────────────────────────────────────────────
# 目標：同時抓取 3 個頁面的標題
# Sync 版本：依序等，總時間 ≈ T1 + T2 + T3
# Async 版本：並發等，總時間 ≈ max(T1, T2, T3)

URLS = [
    "https://example.com",
    "https://playwright.dev/python/",
    "https://docs.python.org/3/",
]


# ══════════════════════════════════════════════════════════════════════════════
# Sync 版本（你已熟悉的寫法）
# ══════════════════════════════════════════════════════════════════════════════

def fetch_titles_sync() -> list[str]:
    from playwright.sync_api import sync_playwright

    titles = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for url in URLS:
            page = browser.new_page()
            page.goto(url, timeout=15_000)
            titles.append(page.title())
            page.close()
        browser.close()
    return titles


# ══════════════════════════════════════════════════════════════════════════════
# Async 版本（ch08 使用的寫法）
# ══════════════════════════════════════════════════════════════════════════════

async def fetch_title(browser, url: str) -> str:
    """抓取單一 URL 的標題（async coroutine）。"""
    page = await browser.new_page()
    try:
        await page.goto(url, timeout=15_000)
        return await page.title()
    finally:
        await page.close()


async def fetch_titles_async() -> list[str]:
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        # asyncio.gather：同時發出所有請求，等全部完成
        titles = await asyncio.gather(
            *[fetch_title(browser, url) for url in URLS]
        )

        await browser.close()
    return list(titles)


# ══════════════════════════════════════════════════════════════════════════════
# 主程式：比較兩種版本
# ══════════════════════════════════════════════════════════════════════════════

async def main():
    import time
    setup_stdout()

    print("══ Sync 版本（依序等待）══")
    t0 = time.perf_counter()
    sync_titles = fetch_titles_sync()
    sync_elapsed = time.perf_counter() - t0
    for url, title in zip(URLS, sync_titles):
        print(f"  {url[:40]:<40} → {title[:50]}")
    print(f"  耗時：{sync_elapsed:.2f}s\n")

    print("══ Async 版本（並發等待）══")
    t0 = time.perf_counter()
    async_titles = await fetch_titles_async()
    async_elapsed = time.perf_counter() - t0
    for url, title in zip(URLS, async_titles):
        print(f"  {url[:40]:<40} → {title[:50]}")
    print(f"  耗時：{async_elapsed:.2f}s\n")

    speedup = sync_elapsed / async_elapsed if async_elapsed > 0 else 1
    print(f"  加速比：{speedup:.1f}x（頁面越多、網路越慢，差距越大）")

    print()
    print("── Sync vs Async 語法對照 ─────────────────────────────────")
    print("  Sync                          │ Async")
    print("  ──────────────────────────────│──────────────────────────────")
    print("  sync_playwright()             │ async_playwright()")
    print("  browser = p.chromium.launch() │ browser = await p.chromium.launch()")
    print("  page = browser.new_page()     │ page = await browser.new_page()")
    print("  page.goto(url)                │ await page.goto(url)")
    print("  page.title()                  │ await page.title()")
    print("  （函式定義無特殊語法）        │ async def fetch(...):  ...")
    print()
    print("  ch08 的 BrowserManager 就是 async 版本的封裝，")
    print("  你在 ch01–ch06 學到的每個概念都可以直接對應過去。")


if __name__ == "__main__":
    asyncio.run(main())

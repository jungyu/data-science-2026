"""
Ch07 — 基礎 pytest-playwright 測試。

pytest-playwright 會自動提供 `page` fixture，
不需要手動建立瀏覽器和頁面。

執行方式：
    pytest ch07-testing/test_basic.py -v
    pytest ch07-testing/test_basic.py -v --headed  # 看到瀏覽器
"""

import re
from playwright.sync_api import Page, expect


def test_example_com_title(page: Page):
    """驗證 example.com 的頁面標題。"""
    page.goto("https://example.com")
    expect(page).to_have_title("Example Domain")


def test_example_com_heading(page: Page):
    """驗證 example.com 的主標題文字。"""
    page.goto("https://example.com")
    heading = page.locator("h1")
    expect(heading).to_have_text("Example Domain")


def test_example_com_has_link(page: Page):
    """驗證 example.com 有「More information」連結。"""
    page.goto("https://example.com")
    link = page.get_by_role("link", name="More information")
    expect(link).to_be_visible()
    expect(link).to_have_attribute("href", "https://www.iana.org/domains/example")


def test_playwright_docs_navigation(page: Page):
    """驗證 Playwright 文件站的基本導航。"""
    page.goto("https://playwright.dev/python/")

    # 頁面應該載入成功
    expect(page).to_have_title(re.compile("Playwright"))

    # 應該有 Docs 連結
    docs_link = page.get_by_role("link", name="Docs")
    expect(docs_link.first).to_be_visible()


def test_page_screenshot(page: Page, output_dir):
    """驗證截圖功能正常運作。"""
    page.goto("https://example.com")
    screenshot_path = output_dir / "test_screenshot.png"
    page.screenshot(path=str(screenshot_path))
    assert screenshot_path.exists(), "截圖檔案應該被建立"
    assert screenshot_path.stat().st_size > 0, "截圖檔案不應該是空的"

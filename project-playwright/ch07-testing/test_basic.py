"""
Ch07 — 基礎 pytest-playwright 測試。

pytest-playwright 會自動提供 `page` fixture，
不需要手動建立瀏覽器和頁面。

執行方式：
    pytest ch07-testing/test_basic.py -v --run-network            # 跑所有
    pytest ch07-testing/test_basic.py -v --run-network --headed   # 看到瀏覽器

注意：本檔所有測試都實際導航到外站，預設會被 ch07-testing/conftest.py
的 ``@pytest.mark.network`` 機制跳過，避免外站 DOM 變動或網路不穩時
誤判為程式碼壞掉。加 ``--run-network`` 才會執行。
"""

import re

import pytest
from playwright.sync_api import Page, expect

# 整檔皆依賴外站 — 統一標記，conftest 預設會跳過，--run-network 才執行
pytestmark = pytest.mark.network


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
    """驗證 example.com 有指向 IANA 的連結（容許 IANA 變更子路徑）。"""
    page.goto("https://example.com")
    link = page.locator("a[href*='iana.org']").first
    expect(link).to_be_visible()


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

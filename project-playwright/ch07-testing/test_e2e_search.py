"""
Ch07 — E2E 搜尋流程測試。

模擬使用者在搜尋引擎執行搜尋的完整流程，
示範 E2E 測試的典型結構。

執行方式：
    pytest ch07-testing/test_e2e_search.py -v
    pytest ch07-testing/test_e2e_search.py -v --headed --slowmo 300
"""

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.network
class TestDuckDuckGoSearch:
    """DuckDuckGo 搜尋 E2E 測試。"""

    def test_homepage_loads(self, page: Page):
        """首頁應該正確載入。"""
        page.goto("https://duckduckgo.com")
        expect(page).to_have_title("DuckDuckGo — Privacy, simplified.")

    def test_search_box_visible(self, page: Page):
        """搜尋框應該可見且可操作。"""
        page.goto("https://duckduckgo.com")
        search_box = page.get_by_role("textbox", name="Search")
        expect(search_box).to_be_visible()
        expect(search_box).to_be_editable()

    def test_search_returns_results(self, page: Page):
        """輸入關鍵字後應該回傳搜尋結果。"""
        page.goto("https://duckduckgo.com")

        # 輸入搜尋關鍵字
        search_box = page.get_by_role("textbox", name="Search")
        search_box.fill("Playwright Python")
        search_box.press("Enter")

        # 等待搜尋結果頁面
        page.wait_for_load_state("domcontentloaded")

        # 驗證有搜尋結果
        results = page.locator("[data-testid='result']")
        expect(results.first).to_be_visible(timeout=10000)
        assert results.count() > 0, "應該至少有一筆搜尋結果"

    def test_search_results_contain_keyword(self, page: Page):
        """搜尋結果應該包含搜尋關鍵字。"""
        page.goto("https://duckduckgo.com")

        search_box = page.get_by_role("textbox", name="Search")
        search_box.fill("Playwright automation")
        search_box.press("Enter")

        page.wait_for_load_state("domcontentloaded")

        # 至少有一個結果的標題包含 "Playwright"（不區分大小寫）
        results = page.locator("[data-testid='result']")
        expect(results.first).to_be_visible(timeout=10000)

        found = False
        for i in range(min(5, results.count())):
            title = results.nth(i).locator("h2").text_content() or ""
            if "playwright" in title.lower():
                found = True
                break

        assert found, "前 5 筆結果中應該至少有一筆標題包含 'Playwright'"

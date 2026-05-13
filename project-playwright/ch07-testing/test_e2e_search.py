"""
Ch07 — E2E 搜尋流程測試。

模擬使用者在搜尋引擎執行搜尋的完整流程，
示範 E2E 測試的典型結構（goto → fill → assert → text content）。

為什麼選 Wikipedia 而不是 Google / DuckDuckGo？
    搜尋引擎會頻繁改版、套用 CAPTCHA、機器人偵測，DOM 結構不穩定。
    教學測試綁定到它們會三天兩頭壞掉，學生看到失敗會誤判為自己寫錯。
    Wikipedia Special:Search 結構穩定多年未變，繁體中文支援完整。

執行方式：
    pytest ch07-testing/test_e2e_search.py -v --run-network
    pytest ch07-testing/test_e2e_search.py -v --run-network --headed --slowmo 300
"""

import re

import pytest
from playwright.sync_api import Page, expect


@pytest.mark.network
class TestWikipediaSearch:
    """Wikipedia 搜尋 E2E 測試。"""

    def test_homepage_loads(self, page: Page):
        """首頁應該正確載入。"""
        page.goto("https://zh.wikipedia.org/")
        expect(page).to_have_title(re.compile(r"维基百科|維基百科|Wikipedia", re.IGNORECASE))

    def test_search_box_visible(self, page: Page):
        """搜尋框應該可見且可操作。"""
        page.goto("https://zh.wikipedia.org/", wait_until="domcontentloaded")
        search_box = page.locator("input[name='search']").first
        expect(search_box).to_be_visible(timeout=5000)
        expect(search_box).to_be_editable()

    def test_search_navigates_to_results(self, page: Page):
        """輸入關鍵字按 Enter 後，應該導到搜尋結果頁或目標條目。"""
        page.goto("https://zh.wikipedia.org/", wait_until="domcontentloaded")

        # 輸入搜尋關鍵字
        search_box = page.locator("input[name='search']").first
        search_box.wait_for()
        search_box.fill("Playwright 軟體")
        search_box.press("Enter")

        # Wikipedia 對精確比對直接導到條目，模糊比對導到搜尋結果頁
        # 兩種情況都會觸發 navigation；networkidle 比 domcontentloaded 可靠
        page.wait_for_load_state("networkidle", timeout=15_000)

        # URL 應該變化（離開首頁）
        assert "wikipedia.org" in page.url
        assert page.url != "https://zh.wikipedia.org/"

        # 內容區應該載入
        content = page.locator("#mw-content-text")
        expect(content).to_be_visible(timeout=10_000)

    def test_search_results_contain_keyword(self, page: Page):
        """搜尋結果頁應該在某處（標題 / 摘要 / 結果列表）出現搜尋關鍵字。

        中文 Wikipedia 搜尋英文關鍵字（如 'Playwright'）時，可能因翻譯關係
        在結果連結文字看不到原英文（例如 'Playwright' → 結果是「劇作家」）。
        所以斷言「整個結果頁內文有出現該字」比「結果連結文字有」更可靠。
        """
        page.goto(
            "https://zh.wikipedia.org/w/index.php?search=Python&title=Special:Search",
            wait_until="networkidle",
            timeout=15_000,
        )

        # 結果頁 #mw-content-text 應可見
        content = page.locator("#mw-content-text")
        expect(content).to_be_visible(timeout=10_000)

        # 整個內容區包含「Python」字串（不分大小寫）
        # Wikipedia 可能：
        #   1. 進入搜尋結果頁（多個候選條目）→ .mw-search-results 列表有「Python」
        #   2. 對精確匹配直接導到條目頁（如 /wiki/Python）→ 條目內文也有「Python」
        # 兩種情況都會通過此 assertion，比「強制找搜尋列表」更穩定
        body_text = (content.text_content() or "").lower()
        assert "python" in body_text, "結果頁內文應該含有搜尋關鍵字 'Python'"

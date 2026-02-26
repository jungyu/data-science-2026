"""
Ch04-02 — 顯式等待策略。

有些場景需要手動等待：
- 等待頁面完全載入（SPA 路由切換）
- 等待特定 URL 出現
- 等待特定元素狀態變化
- 等待網路安靜（所有 AJAX 完成）

執行方式：
    python ch04-waiting/02_explicit_wait.py
"""

from playwright.sync_api import sync_playwright


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # --- wait_for_load_state：等待頁面載入狀態 ---
        page.goto("https://playwright.dev/python/")

        # "domcontentloaded"：DOM 解析完成（最快）
        page.wait_for_load_state("domcontentloaded")
        print("[等待] DOM 解析完成")

        # "load"：所有資源載入完成（圖片、CSS 等）
        page.wait_for_load_state("load")
        print("[等待] 頁面完全載入")

        # "networkidle"：500ms 內沒有網路請求（最慢但最安全）
        page.wait_for_load_state("networkidle")
        print("[等待] 網路已靜止")

        # --- wait_for_url：等待 URL 變化 ---
        print(f"\n[目前 URL] {page.url}")

        # 點擊「Docs」連結並等待 URL 變化
        page.get_by_role("link", name="Docs").first.click()
        page.wait_for_url("**/docs/**")
        print(f"[URL 變化] {page.url}")

        # --- wait_for_selector：等待元素出現/消失 ---
        page.goto("https://playwright.dev/python/docs/intro")

        # 等待文章內容出現
        page.wait_for_selector("article")
        print("\n[元素] article 已出現")

        # --- locator.wait_for：等待 Locator 狀態 ---
        article = page.locator("article")
        article.wait_for(state="visible")
        print("[Locator] article 可見")

        # --- expect（搭配 assertions）---
        from playwright.sync_api import expect

        # 斷言元素可見（會自動重試直到通過或超時）
        expect(page.locator("article")).to_be_visible()
        print("[斷言] article 確認可見 ✓")

        # 斷言頁面標題包含特定文字
        expect(page).to_have_title("Installation | Playwright Python")
        print(f"[斷言] 頁面標題正確 ✓")

        browser.close()


if __name__ == "__main__":
    main()

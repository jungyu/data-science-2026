"""
Ch00 — 驗證 Playwright 安裝是否正確。

執行方式：
    python ch00-setup/verify_install.py
"""

from pathlib import Path


def verify():
    errors = []

    # 1. 檢查套件是否安裝
    try:
        import playwright
        version = playwright.__version__
        print(f"[✓] playwright 套件已安裝 (版本: {version})")
    except ImportError:
        errors.append("playwright 套件未安裝，請執行: pip install playwright")
        print("[✗] playwright 套件未安裝")
        print("\n".join(f"  - {e}" for e in errors))
        return False

    # 2. 嘗試啟動瀏覽器
    from playwright.sync_api import sync_playwright

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            print("[✓] chromium 瀏覽器可用")

            # 3. 導航至測試頁面
            page = browser.new_page()
            page.goto("https://playwright.dev/python/")
            title = page.title()
            print(f"[✓] 成功開啟瀏覽器並導航至測試頁面 ({title})")

            # 4. 截圖驗證
            output_dir = Path(__file__).parent.parent / "output" / "screenshots"
            output_dir.mkdir(parents=True, exist_ok=True)
            screenshot_path = output_dir / "verify_install.png"
            page.screenshot(path=str(screenshot_path))
            print(f"[✓] 截圖已儲存 → {screenshot_path}")

            browser.close()

    except Exception as e:
        errors.append(f"瀏覽器啟動失敗: {e}")
        print(f"[✗] 瀏覽器啟動失敗: {e}")
        print("\n  請執行: playwright install chromium")
        return False

    if errors:
        print("\n以下項目需要修正：")
        for err in errors:
            print(f"  - {err}")
        return False

    print("\n🎉 環境設置完成！可以開始學習了。")
    return True


if __name__ == "__main__":
    verify()

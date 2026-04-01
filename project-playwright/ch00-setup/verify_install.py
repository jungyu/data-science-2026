"""
Ch00 — 驗證 Playwright 安裝是否正確。

「安裝正確」只需要瀏覽器能啟動，不需要對外網路。
本腳本把兩件事分開：

  步驟 1-3：離線驗證（只要 pip install + playwright install 就能過）
  步驟 4（--online）：線上連線測試（可選）

執行方式：
    python ch00-setup/verify_install.py            # 離線驗證
    python ch00-setup/verify_install.py --online   # 加測對外連線
"""

import argparse
import sys
from pathlib import Path


def verify_offline() -> bool:
    """步驟 1-3：確認套件安裝 + 瀏覽器可啟動 + 截圖正常（不需網路）。"""

    # ── 步驟 1：套件是否安裝 ──────────────────────────────────────
    try:
        import playwright
        print(f"[✓] playwright 套件已安裝（版本：{playwright.__version__}）")
    except ImportError:
        print("[✗] playwright 套件未安裝")
        print("    請執行：pip install playwright")
        return False

    # ── 步驟 2：瀏覽器是否可啟動（用 about:blank，不需網路）──────
    from playwright.sync_api import sync_playwright

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            print("[✓] chromium 瀏覽器可啟動")

            page = browser.new_page()
            page.goto("about:blank")   # ← 不需要任何網路連線
            print("[✓] 瀏覽器可開啟頁面（about:blank，離線）")

            # ── 步驟 3：截圖功能是否正常 ──────────────────────────
            output_dir = Path(__file__).parent.parent / "output" / "screenshots"
            output_dir.mkdir(parents=True, exist_ok=True)
            screenshot_path = output_dir / "verify_install.png"
            page.screenshot(path=str(screenshot_path))
            print(f"[✓] 截圖功能正常 → {screenshot_path}")

            browser.close()

    except Exception as e:
        print(f"[✗] 瀏覽器啟動失敗：{e}")
        print()
        print("    常見原因：chromium 尚未安裝")
        print("    請執行：playwright install chromium")
        return False

    return True


def verify_online() -> None:
    """步驟 4（可選）：確認可對外連線。

    失敗不代表安裝有問題，可能是網路環境限制（公司 Proxy、校園防火牆）。
    大多數章節不需要此步驟通過。
    """
    from playwright.sync_api import sync_playwright

    print()
    print("── 步驟 4：線上連線測試（可選）──")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto("https://example.com", timeout=10000)
            title = page.title()
            print(f"[✓] 對外連線正常（載入：{title}）")
            browser.close()
    except Exception as e:
        print(f"[!] 對外連線失敗（安裝本身沒問題，但網路可能受限）：{e}")
        print()
        print("    這不影響離線章節的學習。")
        print("    若需要爬取外部網站，請確認網路設定。")


def main():
    parser = argparse.ArgumentParser(
        description="驗證 Playwright 安裝（步驟 1-3 為離線驗證）"
    )
    parser.add_argument(
        "--online",
        action="store_true",
        help="加測對外網路連線（步驟 4，可選）",
    )
    args = parser.parse_args()

    print("── 離線驗證（步驟 1-3）──")
    ok = verify_offline()
    if not ok:
        sys.exit(1)

    if args.online:
        verify_online()
    else:
        print()
        print("  若要同時測試對外連線，加上 --online 參數：")
        print("  python ch00-setup/verify_install.py --online")

    print()
    print("🎉 環境設置完成！可以開始學習了。")


if __name__ == "__main__":
    main()

"""
Ch06-02 — Session 管理：儲存與載入瀏覽狀態。

Playwright 的 storage_state 可以把 Cookie 和 localStorage
儲存到 JSON 檔案，下次啟動時直接載入，不用重新登入。

參考：DataScout/playwright_base/storage/storage_manager.py

執行方式：
    python ch06-advanced/02_session_management.py
"""

import json
from pathlib import Path
from playwright.sync_api import sync_playwright

STORAGE_DIR = Path(__file__).parent.parent / "output" / "sessions"


def save_session(context, name: str = "default") -> Path:
    """儲存瀏覽器狀態（Cookie + localStorage）到 JSON 檔案。"""
    STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    filepath = STORAGE_DIR / f"{name}_session.json"
    context.storage_state(path=str(filepath))
    return filepath


def load_session(name: str = "default") -> dict | None:
    """載入先前儲存的瀏覽器狀態。"""
    filepath = STORAGE_DIR / f"{name}_session.json"
    if filepath.exists():
        with open(filepath, encoding="utf-8") as f:
            return json.load(f)
    return None


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        # --- 第一次：建立 Session ---
        print("=== 第一次瀏覽（建立 Session）===")
        ctx1 = browser.new_context()
        page1 = ctx1.new_page()
        page1.goto("https://example.com")

        # 模擬網站設定 Cookie（真實場景是登入後自動設定）
        ctx1.add_cookies([
            {
                "name": "session_id",
                "value": "abc123xyz",
                "domain": "example.com",
                "path": "/",
                "httpOnly": True,
                "secure": True,
            },
            {
                "name": "user_pref",
                "value": "dark_mode",
                "domain": "example.com",
                "path": "/",
            },
        ])

        # 儲存 Session
        session_path = save_session(ctx1, "demo")
        cookies = ctx1.cookies()
        print(f"  Cookie 數量: {len(cookies)}")
        print(f"  Session 已儲存 → {session_path}")
        ctx1.close()

        # --- 第二次：載入 Session ---
        print("\n=== 第二次瀏覽（載入 Session）===")
        session_data = load_session("demo")

        if session_data:
            # 用儲存的狀態建立新 Context
            ctx2 = browser.new_context(storage_state=session_data)
            page2 = ctx2.new_page()
            page2.goto("https://example.com")

            cookies = ctx2.cookies()
            print(f"  已載入 Cookie 數量: {len(cookies)}")
            for cookie in cookies:
                print(f"    {cookie['name']}: {cookie['value']}")

            ctx2.close()
        else:
            print("  找不到先前的 Session")

        # --- 查看儲存的 Session 內容 ---
        print(f"\n=== Session 檔案內容 ===")
        with open(STORAGE_DIR / "demo_session.json", encoding="utf-8") as f:
            data = json.load(f)
        print(f"  Cookie 數: {len(data.get('cookies', []))}")
        print(f"  Origins 數: {len(data.get('origins', []))}")

        browser.close()
        print("\n✅ Session 管理完成！重複執行可保持登入狀態。")


if __name__ == "__main__":
    main()

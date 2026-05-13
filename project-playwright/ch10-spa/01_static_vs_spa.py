"""Ch10-01 — 為什麼 SPA 不能用 requests / urllib 爬？

最直接的教學：同一個網址，分別用「直接抓 HTML」和「用 Playwright 渲染」，
比對拿到的內容差異。

對象站點：CBETA Online（中華電子佛典協會）
  https://cbetaonline.dila.edu.tw/zh/B0067_001
  — 經典 SPA：HTML 初次回應只有空殼，內文由 JavaScript 在
    瀏覽器端載入。

執行方式：
    python ch10-spa/01_static_vs_spa.py
"""

from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.console import setup_stdout

from playwright.sync_api import sync_playwright

TARGET_URL = "https://cbetaonline.dila.edu.tw/zh/B0067_001"
CONTENT_KEYWORD = "白話"  # 假設經文內容會出現的中文字，作為「真的拿到內文」的判據


def fetch_static() -> str:
    """模擬 requests/urllib — 只拿 server 第一次回應的 HTML 原始碼。"""
    req = urllib.request.Request(
        TARGET_URL,
        headers={"User-Agent": "Mozilla/5.0 (educational ch10-01)"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def fetch_with_playwright() -> str:
    """用 Playwright 真的開瀏覽器 — JS 執行完後再拿 HTML。"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        # 重點：wait_until="networkidle" 等到網路安靜 500ms 才算載入完成
        page.goto(TARGET_URL, wait_until="networkidle", timeout=30_000)
        html = page.content()
        browser.close()
        return html


def main() -> None:
    setup_stdout()
    print("=" * 60)
    print("Ch10-01 — Static vs SPA")
    print("=" * 60)
    print(f"目標：{TARGET_URL}")
    print()

    # ── A. 靜態抓取 ────────────────────────────────────────────────
    print("[A] 模擬 requests / urllib（不執行 JS）...")
    try:
        static_html = fetch_static()
        static_len = len(static_html)
        has_content_static = CONTENT_KEYWORD in static_html
        print(f"    HTML 長度：{static_len:,} 字元")
        print(f"    含 '{CONTENT_KEYWORD}'：{has_content_static}")
    except Exception as e:
        print(f"    失敗：{e}")
        static_len, has_content_static = 0, False

    print()

    # ── B. Playwright 渲染 ────────────────────────────────────────
    print("[B] Playwright 開瀏覽器執行 JS ...")
    try:
        rendered_html = fetch_with_playwright()
        rendered_len = len(rendered_html)
        has_content_rendered = CONTENT_KEYWORD in rendered_html
        print(f"    HTML 長度：{rendered_len:,} 字元")
        print(f"    含 '{CONTENT_KEYWORD}'：{has_content_rendered}")
    except Exception as e:
        print(f"    失敗：{e}")
        rendered_len, has_content_rendered = 0, False

    print()
    print("─" * 60)
    print("結論")
    print("─" * 60)
    if rendered_len > static_len * 2:
        print(
            f"  Playwright 比靜態抓多 {rendered_len - static_len:,} 字元"
            f"（{rendered_len / max(static_len, 1):.1f}x）"
        )
    if has_content_rendered and not has_content_static:
        print(f"  '{CONTENT_KEYWORD}' 只在 Playwright 版本出現")
        print(f"  → CBETA 是 SPA，requests / urllib 拿不到內文")
    elif has_content_static:
        print(f"  '{CONTENT_KEYWORD}' 在靜態版本就有 → 不是 SPA，省事")
    else:
        print(f"  '{CONTENT_KEYWORD}' 兩邊都沒有 → 換關鍵字試試，或頁面結構變了")

    print()
    print("📌 重點：怎麼判斷一個站點是否為 SPA？")
    print("  1. View Source 看到大量 <div id='app'></div> 但很少內容 → 是 SPA")
    print("  2. DevTools Network 看 XHR / Fetch 大量內容請求 → 是 SPA")
    print("  3. 關 JS 後重新整理頁面是空白 → 是 SPA")


if __name__ == "__main__":
    main()

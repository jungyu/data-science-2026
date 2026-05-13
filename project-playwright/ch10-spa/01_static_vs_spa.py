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

import ssl
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.console import setup_stdout

from playwright.sync_api import sync_playwright

TARGET_URL = "https://cbetaonline.dila.edu.tw/zh/B0067_001"
# 經文內容載入後幾乎必然出現的字，作為「真的拿到內文」的判據
# 「卷」字在每頁標題與導覽都會出現；「經」字在絕大多數佛典中
CONTENT_KEYWORD = "卷"


def fetch_static() -> str:
    """模擬 requests/urllib — 只拿 server 第一次回應的 HTML 原始碼。

    注意 SSL：CBETA 站方的 TLS 憑證缺 Subject Key Identifier 擴充，
    Python 3.12+ 的預設 SSL 驗證會拒絕。為教學示範比較目的（這支腳本
    重點是「JS 渲染前後差異」而非 TLS 安全），這裡用寬鬆 context。
    **真實爬蟲不要這樣做** — 應驗證憑證或聯絡站方修正。
    """
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    req = urllib.request.Request(
        TARGET_URL,
        headers={"User-Agent": "Mozilla/5.0 (educational ch10-01)"},
    )
    with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
        return resp.read().decode("utf-8", errors="replace")


def fetch_with_playwright() -> str:
    """用 Playwright 真的開瀏覽器 — JS 執行完後再拿 HTML。

    為什麼用 wait_until="load" 而不是 "networkidle"？
        CBETA 載入後會持續發 analytics / heartbeat 請求，網路永遠不安靜，
        networkidle 永遠不會觸發 → 30 秒逾時。這正是 ch10/02 要教的
        「不同 wait 策略適用情境」的真實案例。load 已足以等到 JS 渲染完成。
    """
    with sync_playwright() as p:
        # 用 ignore_https_errors 應對 CBETA 證書問題（同 fetch_static 的理由）
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(ignore_https_errors=True)
        page = ctx.new_page()
        page.goto(TARGET_URL, wait_until="load", timeout=30_000)
        # 給 SPA 多 2 秒讓初始 AJAX 渲染完成（教學版的簡單做法；
        # 生產版會用 wait_for_selector 等具體元素）
        page.wait_for_timeout(2_000)
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

    # 主要判據：HTML 長度差
    # 若 Playwright 比 urllib 多出 > 2x 的字元，幾乎必然是 SPA。
    # urllib 拿到的是 server 直送的 HTML 殼；Playwright 拿到的是 JS 執行後的 DOM。
    # 兩邊長度接近 = 內容主要在初始 HTML（不是 SPA）。
    ratio = rendered_len / max(static_len, 1)
    if rendered_len > static_len * 2:
        print(f"  ✅ 是 SPA")
        print(
            f"     Playwright 比 urllib 多 {rendered_len - static_len:,} 字元"
            f"（{ratio:.1f}x）"
        )
        print(f"     → 大量內容由 JS 執行後才填入 DOM")
    elif ratio > 1.2:
        print(f"  ⚠️ 半 SPA（部分內容由 JS 補完）")
        print(f"     Playwright 多 {ratio:.1f}x — 可能是延遲載入區塊或 widget")
    else:
        print(f"  ❌ 不是 SPA")
        print(f"     兩邊長度接近（{ratio:.1f}x），urllib 已足以拿到完整內容")

    # 次要判據：關鍵字比對（提供輔助資訊，不主導結論）
    print()
    print(f"  關鍵字 '{CONTENT_KEYWORD}' 出現情況：")
    print(f"    urllib 版本     ：{'✓' if has_content_static else '✗'}")
    print(f"    Playwright 版本 ：{'✓' if has_content_rendered else '✗'}")
    if has_content_rendered and not has_content_static:
        print(f"    → 關鍵字「只」在 JS 渲染後出現，再次佐證為 SPA")
    elif has_content_static and has_content_rendered:
        print(f"    → 關鍵字兩邊都有（可能是 nav / footer 提及），")
        print(f"      不能單憑這個下定論——以上面的長度差為準")

    print()
    print("📌 重點：怎麼判斷一個站點是否為 SPA？")
    print("  1. View Source 看到大量 <div id='app'></div> 但很少內容 → 是 SPA")
    print("  2. DevTools Network 看 XHR / Fetch 大量內容請求 → 是 SPA")
    print("  3. 關 JS 後重新整理頁面是空白 → 是 SPA")


if __name__ == "__main__":
    main()

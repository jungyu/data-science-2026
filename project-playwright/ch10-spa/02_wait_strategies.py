"""Ch10-02 — SPA 的四種等待策略，哪個最適合你？

Playwright 的 wait_until 有四個選項，加上「等特定元素」這條手動路線。
這支範例對同一個 SPA 用五種策略各跑一次，比對：
  - 載入耗時
  - 拿到的 HTML 是否含目標內容

對象：CBETA B0067_001。實測 SPA 在這四種策略下的差異。

執行方式：
    python ch10-spa/02_wait_strategies.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.console import setup_stdout

from playwright.sync_api import Page, sync_playwright, TimeoutError as PwTimeout

TARGET_URL = "https://cbetaonline.dila.edu.tw/zh/B0067_001"
# 經典 SPA 渲染完成後會出現的內文容器候選；用任一個 selector 偵測
CONTENT_SELECTOR = "article, .juan, .l, [role='main']"

# 各策略註解：
#   commit          ↘  伺服器回應一收到就放行；HTML 通常還沒解析
#   domcontentloaded → DOM 樹建好就放行；JS 還在跑
#   load            → window.onload 觸發；圖片等資源也載完
#   networkidle     → 500ms 內無網路活動；對 SPA 通常最準但最慢
#   wait_for_selector → 手動等到特定元素出現；最精準也最可控

STRATEGIES = ["commit", "domcontentloaded", "load", "networkidle"]


def measure(page: Page, strategy: str) -> dict:
    """用指定策略 goto 並量測耗時、HTML 長度、是否含內容。"""
    t0 = time.monotonic()
    try:
        page.goto(TARGET_URL, wait_until=strategy, timeout=30_000)
        elapsed = (time.monotonic() - t0) * 1000
        html = page.content()
        has_content = page.locator(CONTENT_SELECTOR).count() > 0
        return {
            "strategy": strategy,
            "elapsed_ms": int(elapsed),
            "html_len": len(html),
            "has_content": has_content,
            "error": None,
        }
    except PwTimeout:
        return {
            "strategy": strategy,
            "elapsed_ms": 30_000,
            "html_len": 0,
            "has_content": False,
            "error": "timeout",
        }


def measure_explicit_wait(page: Page) -> dict:
    """手動策略：domcontentloaded + 顯式 wait_for_selector。"""
    t0 = time.monotonic()
    try:
        page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=30_000)
        page.wait_for_selector(CONTENT_SELECTOR, timeout=15_000)
        elapsed = (time.monotonic() - t0) * 1000
        html = page.content()
        return {
            "strategy": "domcontentloaded + wait_for_selector",
            "elapsed_ms": int(elapsed),
            "html_len": len(html),
            "has_content": True,
            "error": None,
        }
    except PwTimeout:
        return {
            "strategy": "domcontentloaded + wait_for_selector",
            "elapsed_ms": int((time.monotonic() - t0) * 1000),
            "html_len": 0,
            "has_content": False,
            "error": "selector timeout",
        }


def print_row(r: dict) -> None:
    ok = "✓" if r["has_content"] else "✗"
    err = f" [{r['error']}]" if r["error"] else ""
    print(
        f"  {r['strategy']:42s} "
        f"{r['elapsed_ms']:>6d} ms  "
        f"HTML {r['html_len']:>7,} 字元  "
        f"內容 {ok}{err}"
    )


def main() -> None:
    setup_stdout()
    print("=" * 80)
    print("Ch10-02 — SPA 五種等待策略對照")
    print("=" * 80)
    print(f"目標：{TARGET_URL}")
    print(f"內容 selector：{CONTENT_SELECTOR}")
    print()

    results: list[dict] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        for strategy in STRATEGIES:
            page = browser.new_page()
            print(f"[測試] wait_until={strategy!r} ...")
            r = measure(page, strategy)
            results.append(r)
            page.close()

        # 第五種：手動 wait_for_selector
        page = browser.new_page()
        print(f"[測試] domcontentloaded + wait_for_selector ...")
        results.append(measure_explicit_wait(page))
        page.close()

        browser.close()

    print()
    print("─" * 80)
    print("綜合比較")
    print("─" * 80)
    for r in results:
        print_row(r)

    print()
    print("📌 怎麼選？")
    print("  • SPA 內容尚未出現 → 別用 commit / domcontentloaded 單獨用")
    print("  • 圖很多很大 → load 會等到圖片載完，多花時間")
    print("  • 預知內容容器 selector → 'domcontentloaded + wait_for_selector'")
    print("    通常是「最快又最準」的組合，生產環境推薦")
    print("  • 完全不知道頁面結構 → networkidle 保底，但有時 SPA 持續輪詢")
    print("    會永遠不安靜，可能逾時")


if __name__ == "__main__":
    main()

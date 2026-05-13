"""
Ch04-04 — 錯誤處理與重試策略。

真實爬蟲一定會遇到：
- TimeoutError：元素沒在期限內出現
- 網路不穩：goto() 失敗或回應很慢
- 選擇器失效：網站改版導致找不到元素

本範例示範三件事：
  1. 捕捉 TimeoutError，不讓爬蟲整個崩潰
  2. 自訂 timeout（毫秒），讓等待時間配合任務需求
  3. 最小化的 retry 模式（指數退避）

執行方式：
    python ch04-waiting/04_error_and_retry.py
"""

import time
import sys
from pathlib import Path
from typing import Callable, TypeVar

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from utils.console import setup_stdout

from playwright.sync_api import Page, sync_playwright, TimeoutError as PlaywrightTimeoutError


# ── 工具函式（純 Python，可獨立單元測試）────────────────────────────────────────

T = TypeVar("T")


def with_retry(
    fn: Callable[[], T],
    *,
    max_attempts: int = 3,
    delay: float = 1.0,
    label: str = "",
) -> T:
    """對 fn() 最多重試 max_attempts 次；每次失敗後等待 delay 秒（指數退避）。

    Args:
        fn: 無參數的 callable，失敗時應拋出 Exception。
        max_attempts: 最大嘗試次數（含第一次）。
        delay: 第一次重試前等待秒數；之後每次翻倍。
        label: 用於日誌輸出的描述字串。
    Returns:
        fn() 成功時的回傳值。
    Raises:
        最後一次失敗的 Exception。
    """
    wait = delay
    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except Exception as e:
            if attempt == max_attempts:
                print(f"  ✗ [{label}] 已達最大重試次數（{max_attempts}），放棄：{e}")
                raise
            print(f"  ⚠ [{label}] 第 {attempt} 次失敗，{wait:.1f}s 後重試…（{e}）")
            time.sleep(wait)
            wait *= 2  # 指數退避


# ── 示範 1：刻意讓 TimeoutError 發生並捕捉 ──────────────────────────────────────

def demo_timeout_error(page: Page) -> None:
    print("\n【示範 1】捕捉 TimeoutError")
    page.set_content("<html><body><p>這個頁面沒有 .never-appears</p></body></html>")

    try:
        # timeout=2000 → 等 2 秒後拋出 TimeoutError
        page.wait_for_selector(".never-appears", timeout=2_000)
        print("  ← 這行不會執行到")
    except PlaywrightTimeoutError:
        print("  ✓ 捕捉到 TimeoutError，爬蟲繼續執行而不崩潰")


# ── 示範 2：自訂 goto() timeout ────────────────────────────────────────────────

def demo_goto_timeout(page: Page) -> None:
    print("\n【示範 2】自訂 goto() timeout")
    print("  預設 timeout = 30,000ms（30 秒）")
    print("  生產環境通常設 10,000–15,000ms，避免卡在慢速頁面")

    # 對 example.com 示範短 timeout（正常網路應該夠用）
    try:
        page.goto("https://example.com", timeout=10_000)
        print(f"  ✓ 載入成功：{page.title()}")
    except PlaywrightTimeoutError:
        print("  ✗ 10 秒內未載入完成（網路可能較慢）")


# ── 示範 3：重試包裝器 ────────────────────────────────────────────────────────

def demo_retry(page: Page) -> None:
    print("\n【示範 3】重試包裝器（模擬不穩定的動態元素）")

    # 建立一個「延遲 3 秒才出現」的元素
    page.set_content("""
    <html><body>
        <p id="status">載入中…</p>
        <script>
            setTimeout(() => {
                document.getElementById('status').textContent = '完成！';
                document.getElementById('status').className = 'ready';
            }, 1500);
        </script>
    </body></html>
    """)

    attempt_count = 0

    def try_get_ready():
        nonlocal attempt_count
        attempt_count += 1
        # 每次只等 800ms，故前 1–2 次可能失敗
        page.wait_for_selector(".ready", timeout=800)
        return page.locator(".ready").text_content()

    try:
        text = with_retry(try_get_ready, max_attempts=4, delay=0.5, label="ready-element")
        print(f"  ✓ 成功取得文字：{text!r}（共嘗試 {attempt_count} 次）")
    except PlaywrightTimeoutError:
        print(f"  ✗ 重試耗盡仍未找到元素（共嘗試 {attempt_count} 次）")


# ── 主程式 ─────────────────────────────────────────────────────────────────────

def main() -> None:
    setup_stdout()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        demo_timeout_error(page)
        demo_goto_timeout(page)
        demo_retry(page)

        browser.close()

    print("\n── 重點整理 ───────────────────────────────────────────")
    print("  • TimeoutError 應用 try/except 捕捉，不要讓整個程式崩潰")
    print("  • goto() / wait_for_selector() 都可以傳 timeout=毫秒數")
    print("  • retry 時加入等待（delay），避免對伺服器造成連續衝擊")
    print("  • 指數退避（delay *= 2）是業界標準做法")


if __name__ == "__main__":
    main()

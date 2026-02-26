"""
Ch03-03 — 鍵盤快捷鍵與滑鼠操作。

示範：
- 鍵盤組合鍵（Ctrl+A, Ctrl+C 等）
- 逐字輸入（模擬真實打字）
- 滑鼠懸停（hover）
- 拖放操作（drag and drop）

執行方式：
    python ch03-interaction/03_keyboard_mouse.py
"""

from playwright.sync_api import sync_playwright


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.set_content("""
        <html><body>
            <h1>鍵盤與滑鼠操作</h1>
            <input type="text" id="input1" value="Hello World" style="width:300px"><br><br>
            <textarea id="textarea1" rows="4" cols="50" placeholder="在這裡打字..."></textarea><br><br>
            <div id="hover-target" style="padding:20px; background:#eee; display:inline-block;">
                滑鼠移到這裡
            </div>
            <div id="hover-result" style="display:none; color:green;">
                ✓ 偵測到 hover！
            </div>
            <script>
                document.getElementById('hover-target').addEventListener('mouseenter', () => {
                    document.getElementById('hover-result').style.display = 'block';
                });
            </script>
        </body></html>
        """)

        # --- 鍵盤：全選 + 刪除 ---
        input_box = page.locator("#input1")
        input_box.click()

        # 全選文字
        modifier = "Meta" if p.chromium.name else "Control"  # macOS 用 Meta
        page.keyboard.press(f"{modifier}+a")
        print("[鍵盤] 全選文字")

        # 刪除並重新輸入
        page.keyboard.press("Backspace")
        print("[鍵盤] 刪除選取內容")

        # --- type()：逐字輸入（模擬真實打字速度）---
        input_box.type("Playwright 很好用", delay=50)
        print(f"[打字] 逐字輸入完成: {input_box.input_value()}")

        # --- 鍵盤：在 textarea 中輸入多行 ---
        textarea = page.locator("#textarea1")
        textarea.click()
        textarea.type("第一行文字")
        page.keyboard.press("Enter")
        textarea.type("第二行文字")
        page.keyboard.press("Enter")
        textarea.type("第三行文字")
        print("[多行] 已在 textarea 輸入三行")

        # --- 滑鼠：hover ---
        hover_target = page.locator("#hover-target")
        hover_target.hover()
        hover_result = page.locator("#hover-result")
        is_visible = hover_result.is_visible()
        print(f"\n[滑鼠] Hover 結果: {'偵測成功 ✓' if is_visible else '未偵測到'}")

        # --- 鍵盤：Tab 在欄位間切換 ---
        input_box.focus()
        page.keyboard.press("Tab")
        active_tag = page.evaluate("document.activeElement.tagName")
        print(f"[Tab] 焦點移至: {active_tag}")

        browser.close()


if __name__ == "__main__":
    main()

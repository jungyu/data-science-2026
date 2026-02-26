"""
Ch03-02 — 表單操作：下拉選單、核取方塊、單選鈕。

使用 Playwright 內建的表單操作方法，
在 httpbin.org 的表單頁面進行示範。

執行方式：
    python ch03-interaction/02_form_operations.py
"""

from playwright.sync_api import sync_playwright


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # 使用一個有表單元素的測試頁面
        # 我們用 Playwright 自己建立一個本地 HTML 測試頁面
        page.set_content("""
        <html><body>
            <h1>表單操作練習</h1>
            <form id="demo-form">
                <!-- 文字輸入 -->
                <label for="name">姓名：</label>
                <input type="text" id="name" name="name" placeholder="請輸入姓名"><br><br>

                <!-- 下拉選單 -->
                <label for="city">城市：</label>
                <select id="city" name="city">
                    <option value="">請選擇</option>
                    <option value="taipei">台北</option>
                    <option value="taichung">台中</option>
                    <option value="kaohsiung">高雄</option>
                </select><br><br>

                <!-- 核取方塊 -->
                <label><input type="checkbox" name="skill" value="python"> Python</label>
                <label><input type="checkbox" name="skill" value="js"> JavaScript</label>
                <label><input type="checkbox" name="skill" value="sql"> SQL</label><br><br>

                <!-- 單選鈕 -->
                <label><input type="radio" name="level" value="beginner"> 初學者</label>
                <label><input type="radio" name="level" value="intermediate"> 中級</label>
                <label><input type="radio" name="level" value="advanced"> 進階</label><br><br>

                <button type="submit">送出</button>
            </form>
        </body></html>
        """)

        # --- fill()：文字輸入 ---
        page.get_by_label("姓名：").fill("王小明")
        print("[文字] 已填入姓名: 王小明")

        # --- select_option()：下拉選單 ---
        page.get_by_label("城市：").select_option("taipei")
        print("[選單] 已選擇城市: 台北")

        # --- check()：核取方塊 ---
        page.get_by_label("Python").check()
        page.get_by_label("SQL").check()
        print("[核取] 已勾選: Python, SQL")

        # 驗證核取狀態
        is_python = page.get_by_label("Python").is_checked()
        is_js = page.get_by_label("JavaScript").is_checked()
        print(f"  Python: {'✓' if is_python else '✗'}, JavaScript: {'✓' if is_js else '✗'}")

        # --- check()：單選鈕 ---
        page.get_by_label("中級").check()
        print("[單選] 已選擇: 中級")

        # --- 取消核取 ---
        page.get_by_label("SQL").uncheck()
        print("[取消] 已取消勾選: SQL")

        # 最終狀態
        print("\n--- 表單最終狀態 ---")
        print(f"  姓名: {page.get_by_label('姓名：').input_value()}")
        print(f"  城市: {page.get_by_label('城市：').input_value()}")
        print(f"  Python: {page.get_by_label('Python').is_checked()}")
        print(f"  SQL: {page.get_by_label('SQL').is_checked()}")
        print(f"  中級: {page.get_by_label('中級').is_checked()}")

        browser.close()


if __name__ == "__main__":
    main()

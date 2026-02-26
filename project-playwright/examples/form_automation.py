"""
完整範例：表單自動化填寫。

綜合運用：
- 元素選擇器（ch02）
- 頁面互動（ch03）
- 等待策略（ch04）
- 截圖存證（ch01）

目標：自動填寫一個多步驟表單並截圖存證。

執行方式：
    python examples/form_automation.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.browser import BrowserManager
from utils.logger import setup_logger

OUTPUT_DIR = Path(__file__).parent.parent / "output" / "screenshots"
logger = setup_logger("form_automation")

# 模擬一個多步驟表單頁面
FORM_HTML = """
<html>
<head>
    <meta charset="utf-8">
    <title>學生資料填寫系統</title>
    <style>
        body { font-family: sans-serif; max-width: 600px; margin: 40px auto; padding: 0 20px; }
        .step { display: none; }
        .step.active { display: block; }
        input, select, textarea { width: 100%; padding: 8px; margin: 8px 0; box-sizing: border-box; }
        button { padding: 10px 20px; margin: 10px 5px 10px 0; cursor: pointer; }
        .btn-primary { background: #4CAF50; color: white; border: none; border-radius: 4px; }
        .btn-secondary { background: #2196F3; color: white; border: none; border-radius: 4px; }
        .progress { background: #eee; border-radius: 4px; margin-bottom: 20px; }
        .progress-bar { background: #4CAF50; height: 8px; border-radius: 4px; transition: width 0.3s; }
        .success { background: #e8f5e9; padding: 20px; border-radius: 8px; text-align: center; }
        h2 { color: #333; }
    </style>
</head>
<body>
    <h1>學生資料填寫系統</h1>
    <div class="progress"><div class="progress-bar" id="progress" style="width:33%"></div></div>

    <!-- Step 1: 基本資料 -->
    <div class="step active" id="step1">
        <h2>步驟 1：基本資料</h2>
        <label for="name">姓名：</label>
        <input type="text" id="name" name="name" placeholder="請輸入姓名">
        <label for="email">Email：</label>
        <input type="email" id="email" name="email" placeholder="請輸入 Email">
        <label for="department">系所：</label>
        <select id="department" name="department">
            <option value="">請選擇</option>
            <option value="cs">資訊工程系</option>
            <option value="im">資訊管理系</option>
            <option value="ee">電機工程系</option>
            <option value="math">數學系</option>
        </select>
        <br>
        <button class="btn-primary" onclick="nextStep(2)">下一步</button>
    </div>

    <!-- Step 2: 技能 -->
    <div class="step" id="step2">
        <h2>步驟 2：技能評估</h2>
        <p>請勾選您具備的技能：</p>
        <label><input type="checkbox" name="skill" value="python"> Python</label><br>
        <label><input type="checkbox" name="skill" value="javascript"> JavaScript</label><br>
        <label><input type="checkbox" name="skill" value="sql"> SQL</label><br>
        <label><input type="checkbox" name="skill" value="ml"> 機器學習</label><br>
        <br>
        <label for="experience">經驗描述：</label>
        <textarea id="experience" name="experience" rows="3" placeholder="簡述您的相關經驗"></textarea>
        <br>
        <button class="btn-secondary" onclick="nextStep(1)">上一步</button>
        <button class="btn-primary" onclick="nextStep(3)">下一步</button>
    </div>

    <!-- Step 3: 確認 -->
    <div class="step" id="step3">
        <h2>步驟 3：確認送出</h2>
        <div id="summary"></div>
        <br>
        <button class="btn-secondary" onclick="nextStep(2)">上一步</button>
        <button class="btn-primary" onclick="submitForm()">確認送出</button>
    </div>

    <!-- 完成 -->
    <div class="step" id="step4">
        <div class="success">
            <h2>送出成功！</h2>
            <p>您的資料已成功提交。</p>
            <p id="timestamp"></p>
        </div>
    </div>

    <script>
        function nextStep(step) {
            document.querySelectorAll('.step').forEach(s => s.classList.remove('active'));
            document.getElementById('step' + step).classList.add('active');
            document.getElementById('progress').style.width = (step * 25) + '%';

            if (step === 3) {
                const name = document.getElementById('name').value;
                const email = document.getElementById('email').value;
                const dept = document.getElementById('department').selectedOptions[0]?.text || '';
                const skills = [...document.querySelectorAll('input[name=skill]:checked')]
                    .map(c => c.parentElement.textContent.trim());
                const exp = document.getElementById('experience').value;

                document.getElementById('summary').innerHTML = `
                    <p><strong>姓名：</strong>${name}</p>
                    <p><strong>Email：</strong>${email}</p>
                    <p><strong>系所：</strong>${dept}</p>
                    <p><strong>技能：</strong>${skills.join('、') || '未選擇'}</p>
                    <p><strong>經驗：</strong>${exp || '未填寫'}</p>
                `;
            }
        }
        function submitForm() {
            document.querySelectorAll('.step').forEach(s => s.classList.remove('active'));
            document.getElementById('step4').classList.add('active');
            document.getElementById('progress').style.width = '100%';
            document.getElementById('timestamp').textContent =
                '提交時間：' + new Date().toLocaleString('zh-TW');
        }
    </script>
</body>
</html>
"""


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("啟動表單自動化...")
    with BrowserManager(headless=True) as bm:
        page = bm.new_page()
        page.set_content(FORM_HTML)

        # === Step 1：填寫基本資料 ===
        logger.info("Step 1: 填寫基本資料")
        page.get_by_label("姓名：").fill("王小明")
        page.get_by_label("Email：").fill("wang@example.com")
        page.get_by_label("系所：").select_option("im")

        page.screenshot(path=str(OUTPUT_DIR / "form_step1.png"))
        logger.info("  截圖: form_step1.png")

        page.get_by_role("button", name="下一步").click()

        # === Step 2：勾選技能 ===
        logger.info("Step 2: 填寫技能評估")
        page.get_by_label("Python").check()
        page.get_by_label("SQL").check()
        page.get_by_label("機器學習").check()
        page.get_by_label("經驗描述：").fill(
            "修習過資料科學導論，熟悉 Python pandas 和 scikit-learn，"
            "曾完成 Kaggle 入門競賽。"
        )

        page.screenshot(path=str(OUTPUT_DIR / "form_step2.png"))
        logger.info("  截圖: form_step2.png")

        page.get_by_role("button", name="下一步").click()

        # === Step 3：確認 ===
        logger.info("Step 3: 確認資料")
        summary = page.locator("#summary").text_content()
        print(f"\n--- 表單摘要 ---\n{summary}")

        page.screenshot(path=str(OUTPUT_DIR / "form_step3.png"))
        logger.info("  截圖: form_step3.png")

        page.get_by_role("button", name="確認送出").click()

        # === Step 4：完成 ===
        success = page.locator(".success h2")
        print(f"\n結果: {success.text_content()}")

        page.screenshot(path=str(OUTPUT_DIR / "form_step4.png"))
        logger.info("  截圖: form_step4.png")

    logger.info(f"所有截圖已儲存至 {OUTPUT_DIR}/")
    print(f"\n✅ 表單自動化完成！截圖存於 {OUTPUT_DIR}/")


if __name__ == "__main__":
    main()

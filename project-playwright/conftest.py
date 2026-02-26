"""
全域 pytest 設定與 Playwright 共用 fixtures。

使用方式：
    pytest ch07-testing/ --headed --slowmo 500
"""

import pytest
from pathlib import Path
from dotenv import load_dotenv

# 載入 .env 環境變數
load_dotenv()

OUTPUT_DIR = Path(__file__).parent / "output"


@pytest.fixture(scope="session")
def output_dir():
    """確保輸出資料夾存在並回傳路徑。"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    return OUTPUT_DIR


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """覆寫 pytest-playwright 預設的 BrowserContext 參數。"""
    return {
        **browser_context_args,
        "viewport": {"width": 1280, "height": 720},
        "ignore_https_errors": True,
        "locale": "zh-TW",
        "timezone_id": "Asia/Taipei",
    }

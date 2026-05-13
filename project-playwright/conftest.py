"""
全域 pytest 設定與 Playwright 共用 fixtures。

使用方式：
    pytest ch07-testing/ --headed --slowmo 500
"""

import pytest
from pathlib import Path
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent
ENV_FILE = ROOT_DIR / ".env"
if not ENV_FILE.exists():
    print(
        f"[conftest] 提示：找不到 {ENV_FILE.name}。"
        f" 如需 Supabase / 其他外部服務，請執行 `cp .env.example .env` 後填入。"
    )
load_dotenv(ENV_FILE)

OUTPUT_DIR = ROOT_DIR / "output"


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

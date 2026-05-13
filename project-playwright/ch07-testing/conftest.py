"""
Ch07 — 測試設定：把「本地安全」和「需要網路」的測試分開。

為什麼要分？
    E2E 測試（如 DuckDuckGo）依賴外站 DOM 結構，網站改版或網路不穩
    都可能讓測試失敗。學生第一次跑測試時，無法分辨「程式寫錯了」
    還是「測試樣本壞了」。

做法：
    - @pytest.mark.network 的測試預設被跳過
    - 加 --run-network 才執行（明確表達「我知道這需要網路且可能脆弱」）

執行範例：
    pytest ch07-testing/                    # 只跑本地安全測試
    pytest ch07-testing/ --run-network      # 全部跑，包含 E2E
    pytest ch07-testing/ -m network --run-network   # 只跑 E2E

與根目錄 conftest.py 的分工：
    根 conftest.py 設定 ``browser_context_args``（viewport / locale /
    timezone 等共用瀏覽器情境），pytest-playwright 會自動套用至此章。
    本檔只負責「網路測試開關」，不重複定義瀏覽器參數。
"""

import pytest


def pytest_addoption(parser):
    parser.addoption(
        "--run-network",
        action="store_true",
        default=False,
        help="執行需要網路連線的測試（@pytest.mark.network）",
    )


def pytest_collection_modifyitems(config, items):
    """預設跳過 @pytest.mark.network 的測試。"""
    if config.getoption("--run-network"):
        return  # 有加 --run-network，全部都跑

    skip_network = pytest.mark.skip(
        reason=(
            "此測試需要網路連線且依賴外站 DOM，預設跳過。"
            " 加 --run-network 才執行：pytest ch07-testing/ --run-network"
        )
    )
    for item in items:
        if item.get_closest_marker("network"):
            item.add_marker(skip_network)

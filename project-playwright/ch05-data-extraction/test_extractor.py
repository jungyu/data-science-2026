"""Ch05 — 純函式單元測試（不需要瀏覽器）。

重點：爬蟲程式裡有兩層邏輯：
  1. 「瀏覽器互動層」—— 操作 DOM、取出原始字串（需要 Chromium）
  2. 「資料轉換層」—— 把字串整理成結構化資料（純 Python，易測試）

本檔案只測第 2 層（transforms.py）。好的爬蟲設計應把這兩層拆開，
讓轉換邏輯可以獨立驗證，不需啟動 Chromium。

vs ch07 的 E2E 測試：
  ch07：pytest-playwright fixture → 需要瀏覽器 + 網路，幾秒才跑完
  本檔：import 純函式           → 只需要 pytest，毫秒內跑完

執行：
    pytest ch05-data-extraction/test_extractor.py -v
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from transforms import rows_to_dicts


# ── 基本功能 ──────────────────────────────────────────────────────────────────

def test_basic_mapping():
    headers = ["城市", "人口（萬）"]
    raw = [["台北市", "251"], ["高雄市", "276"]]
    result = rows_to_dicts(headers, raw)
    assert result == [
        {"城市": "台北市", "人口（萬）": "251"},
        {"城市": "高雄市", "人口（萬）": "276"},
    ]


def test_preserves_column_order():
    headers = ["A", "B", "C"]
    raw = [["1", "2", "3"]]
    result = rows_to_dicts(headers, raw)
    assert list(result[0].keys()) == ["A", "B", "C"]


# ── 邊界情況 ──────────────────────────────────────────────────────────────────

def test_empty_table_returns_empty_list():
    assert rows_to_dicts(["Col"], []) == []


def test_row_longer_than_headers_is_truncated():
    """欄位比表頭多時，超出的部分應被截去（不能 KeyError）。"""
    headers = ["A", "B"]
    raw = [["1", "2", "3", "4"]]
    result = rows_to_dicts(headers, raw)
    assert result == [{"A": "1", "B": "2"}]


def test_row_shorter_than_headers():
    """欄位比表頭少時，只對應有值的部分。"""
    headers = ["A", "B", "C"]
    raw = [["only_one"]]
    result = rows_to_dicts(headers, raw)
    assert result == [{"A": "only_one"}]


def test_empty_row_is_skipped():
    """完全空的列（例如 DOM 裡的空 <tr>）應被跳過。"""
    headers = ["A", "B"]
    raw = [[], ["x", "y"]]
    result = rows_to_dicts(headers, raw)
    assert len(result) == 1
    assert result[0] == {"A": "x", "B": "y"}


def test_multiple_rows():
    headers = ["名稱", "分數"]
    raw = [["Alice", "90"], ["Bob", "85"], ["Carol", "92"]]
    result = rows_to_dicts(headers, raw)
    assert len(result) == 3
    assert result[2]["名稱"] == "Carol"


def test_single_column():
    headers = ["Tag"]
    raw = [["python"], ["playwright"], ["data"]]
    result = rows_to_dicts(headers, raw)
    assert [r["Tag"] for r in result] == ["python", "playwright", "data"]


# ── 資料科學應用：輸出格式可直接轉 DataFrame ─────────────────────────────────

def test_output_compatible_with_pandas():
    """rows_to_dicts 的輸出可以直接丟給 pd.DataFrame()。

    pandas 未安裝或版本不相容（numpy ABI mismatch）時，此測試會 skip。
    """
    import pytest
    try:
        import pandas as pd
    except Exception as e:
        pytest.skip(f"pandas 無法載入，跳過：{e}")

    headers = ["城市", "人口（萬）", "面積（km²）"]
    raw = [
        ["台北市", "251", "271.8"],
        ["新北市", "403", "2052.6"],
    ]
    data = rows_to_dicts(headers, raw)
    df = pd.DataFrame(data)
    assert list(df.columns) == headers
    assert len(df) == 2
    assert df.loc[0, "城市"] == "台北市"

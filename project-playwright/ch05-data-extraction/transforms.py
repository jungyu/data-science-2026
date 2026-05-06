"""Ch05 純函式：資料轉換層（無任何外部依賴）。

爬蟲邏輯分兩層：
  瀏覽器互動層（02_table_scraping.py）→ 取出原始字串
  資料轉換層  （本檔案）              → 字串 → 結構化資料

本檔案無 playwright、無 requests，可以獨立用 pytest 測試。
"""

from __future__ import annotations


def rows_to_dicts(headers: list[str], raw_rows: list[list[str]]) -> list[dict]:
    """(表頭, 字串矩陣) → 字典列表。

    - 欄位比表頭多：超出的部分截去
    - 欄位比表頭少：只對應有值的部分
    - 空列（[]）：跳過
    """
    result = []
    for row in raw_rows:
        row_data = {headers[j]: row[j] for j in range(min(len(row), len(headers)))}
        if row_data:
            result.append(row_data)
    return result

"""
utils.console — 主控台跨平台相容工具。

提供 Windows cp950 環境下的 UTF-8 輸出修正，
確保章節範例腳本在所有平台上都能正常印出中文與特殊字元。
"""

import sys


def setup_stdout() -> None:
    """將 stdout 重設為 UTF-8（僅在支援 reconfigure 的環境生效）。

    在 Windows 預設 cp950 主控台下，print() 含非 ASCII 字元時會拋出
    UnicodeEncodeError。呼叫此函式可在不影響其他平台的情況下修正此問題。

    使用方式：
        from utils.console import setup_stdout
        setup_stdout()   # 在 main() 最頂端呼叫
    """
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

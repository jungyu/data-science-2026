"""
環境驗證腳本。

逐一檢查所有必要套件是否正確安裝，
並測試資料下載與中文字體渲染功能。
"""

from __future__ import annotations

import sys


def check_package(name: str, import_name: str | None = None) -> bool:
    """檢查套件是否可匯入。"""
    mod = import_name or name
    try:
        __import__(mod)
        return True
    except ImportError:
        return False


def main() -> None:
    print("=" * 60)
    print("  時間序列預測專案 — 環境驗證")
    print("=" * 60)
    print(f"\n  Python 版本: {sys.version}")
    print()

    # 必要套件清單
    packages = [
        ("pandas", None, "資料處理"),
        ("numpy", None, "數值運算"),
        ("matplotlib", None, "視覺化"),
        ("seaborn", None, "統計圖表"),
        ("plotly", None, "互動圖表"),
        ("scipy", None, "科學計算"),
        ("statsmodels", None, "統計模型"),
        ("arch", None, "GARCH 模型"),
        ("prophet", None, "Prophet 預測"),
        ("sklearn", "sklearn", "機器學習"),
        ("lightgbm", None, "LightGBM"),
        ("xgboost", None, "XGBoost"),
        ("catboost", None, "CatBoost"),
        ("optuna", None, "超參數優化"),
        ("torch", None, "深度學習"),
        ("sktime", None, "時間序列框架"),
        ("pandas_ta", None, "技術指標"),
        ("yfinance", "yfinance", "股價資料"),
        ("mlflow", None, "實驗追蹤"),
        ("joblib", None, "模型序列化"),
        ("tqdm", None, "進度條"),
        ("dotenv", "dotenv", "環境變數"),
    ]

    passed = 0
    failed = 0
    failed_list = []

    for name, import_name, desc in packages:
        ok = check_package(name, import_name)
        status = "OK" if ok else "MISSING"
        symbol = "+" if ok else "x"
        print(f"  [{symbol}] {name:<20} {desc:<16} {status}")
        if ok:
            passed += 1
        else:
            failed += 1
            failed_list.append(name)

    print(f"\n  結果: {passed} 通過 / {failed} 失敗")

    if failed_list:
        print(f"\n  缺少的套件: {', '.join(failed_list)}")
        print("  請執行: pip install -e '.[all]'")
        print()
        return

    # 測試資料下載
    print("\n" + "-" * 60)
    print("  測試資料下載 (yfinance) ...")
    try:
        import yfinance as yf

        data = yf.download("AAPL", start="2024-01-01", end="2024-01-10", progress=False)
        if len(data) > 0:
            print(f"  [+] 成功下載 AAPL 測試資料 ({len(data)} 筆)")
        else:
            print("  [x] 下載成功但無資料，請檢查網路連線")
    except Exception as e:
        print(f"  [x] 下載失敗: {e}")

    # 測試中文字體
    print("\n  測試中文字體 ...")
    try:
        import matplotlib
        matplotlib.use("Agg")  # 不顯示視窗
        import matplotlib.pyplot as plt
        from matplotlib.font_manager import FontManager

        fm = FontManager()
        available = {f.name for f in fm.ttflist}
        cjk_fonts = [
            "Noto Sans CJK TC", "Noto Sans TC", "Microsoft JhengHei",
            "PingFang TC", "Apple LiGothic", "SimHei",
        ]
        found = [f for f in cjk_fonts if f in available]
        if found:
            print(f"  [+] 找到中文字體: {found[0]}")
        else:
            print("  [!] 未找到中文字體，圖表中文可能亂碼")
            print("      建議安裝 Noto Sans CJK TC")
    except Exception as e:
        print(f"  [x] 字體檢測失敗: {e}")

    print("\n" + "=" * 60)
    if failed == 0:
        print("  環境驗證全部通過！可以開始學習。")
    print("=" * 60)


if __name__ == "__main__":
    main()

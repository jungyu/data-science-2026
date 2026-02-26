"""
Ch01-02: 時間序列分解。

學習重點：
- 加法模型 vs 乘法模型
- 趨勢、季節性、殘差各成分的意義
- STL 分解（Seasonal-Trend decomposition using LOESS）
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.data_loader import download_stock_data
from src.plot_utils import apply_style

import matplotlib.pyplot as plt
from statsmodels.tsa.seasonal import STL, seasonal_decompose


def main() -> None:
    df = download_stock_data(ticker="AAPL", start="2020-01-01")
    close = df["Close"].asfreq("B").ffill()  # 填補非交易日

    apply_style()

    # === 1. 經典分解（乘法模型） ===
    print("=== 經典乘法分解 ===")
    result_mult = seasonal_decompose(close, model="multiplicative", period=252)

    fig = result_mult.plot()
    fig.set_size_inches(14, 10)
    fig.suptitle("經典乘法分解 (period=252 交易日)", fontsize=14, y=1.02)
    plt.tight_layout()
    plt.savefig(
        Path(__file__).resolve().parent.parent / "outputs" / "ch01_decompose_mult.png",
        dpi=150, bbox_inches="tight",
    )
    plt.show()

    # === 2. STL 分解（更穩健） ===
    print("\n=== STL 分解 ===")
    stl = STL(close, period=252, robust=True)
    result_stl = stl.fit()

    fig = result_stl.plot()
    fig.set_size_inches(14, 10)
    fig.suptitle("STL 分解 (robust=True)", fontsize=14, y=1.02)
    plt.tight_layout()
    plt.savefig(
        Path(__file__).resolve().parent.parent / "outputs" / "ch01_decompose_stl.png",
        dpi=150, bbox_inches="tight",
    )
    plt.show()

    # === 3. 比較殘差 ===
    print("\n=== 殘差比較 ===")
    print(f"  經典分解殘差標準差: {result_mult.resid.std():.4f}")
    print(f"  STL 分解殘差標準差:   {result_stl.resid.std():.4f}")
    print("  （STL 殘差通常更小，表示分解更充分）")


if __name__ == "__main__":
    main()

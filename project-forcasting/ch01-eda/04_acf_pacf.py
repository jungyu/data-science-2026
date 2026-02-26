"""
Ch01-04: 自相關分析。

學習重點：
- ACF (Auto-Correlation Function) 的意義
- PACF (Partial ACF) 的意義
- 如何從 ACF/PACF 圖形判斷 ARIMA 的 p, q 階數
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.data_loader import download_stock_data
from src.plot_utils import apply_style

import matplotlib.pyplot as plt
import numpy as np
from statsmodels.graphics.tsaplots import plot_acf, plot_pacf


def main() -> None:
    df = download_stock_data(ticker="AAPL", start="2020-01-01")
    returns = df["Close"].pct_change().dropna()

    apply_style()

    # === 1. 報酬率的 ACF & PACF ===
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    plot_acf(returns, lags=40, ax=axes[0, 0], title="報酬率 ACF")
    plot_pacf(returns, lags=40, ax=axes[0, 1], title="報酬率 PACF", method="ywm")

    # === 2. 報酬率平方的 ACF (波動聚集) ===
    returns_sq = returns**2
    plot_acf(returns_sq, lags=40, ax=axes[1, 0], title="報酬率² ACF（波動聚集）")
    plot_pacf(returns_sq, lags=40, ax=axes[1, 1], title="報酬率² PACF", method="ywm")

    plt.tight_layout()
    plt.savefig(
        Path(__file__).resolve().parent.parent / "outputs" / "ch01_acf_pacf.png",
        dpi=150, bbox_inches="tight",
    )
    plt.show()

    # === 3. 觀察摘要 ===
    print("=" * 60)
    print("  ACF / PACF 判讀指南")
    print("=" * 60)
    print()
    print("  ARIMA(p, d, q) 定階規則：")
    print("  ┌──────────┬─────────────┬─────────────┐")
    print("  │ 模型     │ ACF 特徵    │ PACF 特徵   │")
    print("  ├──────────┼─────────────┼─────────────┤")
    print("  │ AR(p)    │ 拖尾衰減    │ p 階截尾    │")
    print("  │ MA(q)    │ q 階截尾    │ 拖尾衰減    │")
    print("  │ ARMA(p,q)│ 拖尾衰減    │ 拖尾衰減    │")
    print("  └──────────┴─────────────┴─────────────┘")
    print()
    print("  觀察結果：")
    print("  - 報酬率 ACF: 大多在信賴帶內 → 弱自相關")
    print("  - 報酬率² ACF: 明顯正自相關 → 波動聚集效應")
    print("  - 波動聚集 → 可考慮 GARCH 模型捕捉")


if __name__ == "__main__":
    main()

"""
Ch01-03: 定態性檢定。

學習重點：
- ADF (Augmented Dickey-Fuller) 檢定
- KPSS (Kwiatkowski-Phillips-Schmidt-Shin) 檢定
- 差分操作使序列定態化
- 兩種檢定的互補關係
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.data_loader import download_stock_data
from src.plot_utils import apply_style

import matplotlib.pyplot as plt
import numpy as np
from statsmodels.tsa.stattools import adfuller, kpss


def adf_test(series: np.ndarray, name: str = "") -> dict:
    """執行 ADF 檢定並輸出結果。"""
    result = adfuller(series, autolag="AIC")
    stat, pvalue, lags, nobs, critical, icbest = result

    print(f"\n  ADF 檢定 — {name}")
    print(f"    統計量:    {stat:.4f}")
    print(f"    p-value:   {pvalue:.6f}")
    print(f"    使用滯後:  {lags}")
    for key, val in critical.items():
        print(f"    臨界值 {key}: {val:.4f}")

    is_stationary = pvalue < 0.05
    print(f"    結論: {'定態 (拒絕單根)' if is_stationary else '非定態 (無法拒絕單根)'}")
    return {"statistic": stat, "pvalue": pvalue, "stationary": is_stationary}


def kpss_test(series: np.ndarray, name: str = "") -> dict:
    """執行 KPSS 檢定並輸出結果。"""
    # regression='c' 檢定水準定態; 'ct' 檢定趨勢定態
    stat, pvalue, lags, critical = kpss(series, regression="c", nlags="auto")

    print(f"\n  KPSS 檢定 — {name}")
    print(f"    統計量:    {stat:.4f}")
    print(f"    p-value:   {pvalue:.4f}")
    print(f"    使用滯後:  {lags}")
    for key, val in critical.items():
        print(f"    臨界值 {key}: {val:.4f}")

    is_stationary = pvalue > 0.05  # KPSS 的虛無假設是定態
    print(f"    結論: {'定態' if is_stationary else '非定態'}")
    return {"statistic": stat, "pvalue": pvalue, "stationary": is_stationary}


def main() -> None:
    df = download_stock_data(ticker="AAPL", start="2020-01-01")
    close = df["Close"].values
    returns = np.diff(np.log(close))  # 對數報酬率 ≈ 一階差分

    print("=" * 60)
    print("  定態性檢定")
    print("=" * 60)

    # === 1. 收盤價 (預期非定態) ===
    print("\n--- 收盤價 ---")
    adf_test(close, "收盤價")
    kpss_test(close, "收盤價")

    # === 2. 對數報酬率 (預期定態) ===
    print("\n--- 對數報酬率 (一階差分) ---")
    adf_test(returns, "對數報酬率")
    kpss_test(returns, "對數報酬率")

    # === 3. 視覺化比較 ===
    apply_style()
    fig, axes = plt.subplots(2, 1, figsize=(14, 8))

    axes[0].plot(df.index, close, linewidth=1)
    axes[0].set_title("收盤價（非定態）")
    axes[0].set_ylabel("價格")

    axes[1].plot(df.index[1:], returns, linewidth=0.5, alpha=0.8)
    axes[1].axhline(y=0, color="red", linestyle="--", alpha=0.5)
    axes[1].set_title("對數報酬率（定態）")
    axes[1].set_ylabel("報酬率")

    plt.tight_layout()
    plt.savefig(
        Path(__file__).resolve().parent.parent / "outputs" / "ch01_stationarity.png",
        dpi=150, bbox_inches="tight",
    )
    plt.show()

    print("\n" + "=" * 60)
    print("  重點整理")
    print("-" * 60)
    print("  1. ADF: H0=有單根(非定態)。p<0.05 → 拒絕 → 定態")
    print("  2. KPSS: H0=定態。p>0.05 → 不拒絕 → 定態")
    print("  3. 兩個檢定互補使用，結果一致時信心更高")
    print("  4. 股價通常非定態，報酬率通常定態")
    print("=" * 60)


if __name__ == "__main__":
    main()

"""
Ch01-01: 載入資料與基礎視覺化。

學習重點：
- 使用 yfinance 下載股價資料
- 繪製收盤價走勢與成交量
- 觀察基本統計特性
"""

from __future__ import annotations

import sys
from pathlib import Path

# 將專案根目錄加入路徑
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.data_loader import download_stock_data
from src.plot_utils import apply_style, plot_price_history

import matplotlib.pyplot as plt
import pandas as pd


def main() -> None:
    # === 1. 下載資料 ===
    df = download_stock_data(ticker="AAPL", start="2018-01-01")

    # === 2. 基本資訊 ===
    print("\n=== 資料概覽 ===")
    print(f"期間: {df.index[0].date()} ~ {df.index[-1].date()}")
    print(f"筆數: {len(df)}")
    print(f"\n{df.describe().round(2)}")

    # === 3. 走勢圖 ===
    plot_price_history(df, title="AAPL 股價走勢", save_name="ch01_price_history.png")

    # === 4. 報酬率分佈 ===
    apply_style()
    returns = df["Close"].pct_change().dropna()

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # 報酬率時序圖
    axes[0].plot(returns.index, returns, linewidth=0.5, alpha=0.7)
    axes[0].axhline(y=0, color="red", linestyle="--", alpha=0.5)
    axes[0].set_title("日報酬率")
    axes[0].set_ylabel("報酬率")

    # 報酬率直方圖
    axes[1].hist(returns, bins=80, edgecolor="white", alpha=0.7)
    axes[1].axvline(x=returns.mean(), color="red", linestyle="--", label=f"均值={returns.mean():.4f}")
    axes[1].set_title("報酬率分佈")
    axes[1].set_xlabel("報酬率")
    axes[1].legend()

    plt.tight_layout()
    plt.savefig(Path(__file__).resolve().parent.parent / "outputs" / "ch01_return_dist.png", dpi=150)
    plt.show()

    # === 5. 基本統計 ===
    print(f"\n=== 報酬率統計 ===")
    print(f"  均值:   {returns.mean():.6f}")
    print(f"  標準差: {returns.std():.6f}")
    print(f"  偏態:   {returns.skew():.4f}")
    print(f"  峰態:   {returns.kurtosis():.4f}")
    print(f"  （峰態 > 0 表示厚尾分佈，常見於金融資料）")


if __name__ == "__main__":
    main()

"""
Ch04-02: 技術指標特徵。

學習重點：
- 常用技術指標的數學原理
- 使用 pandas_ta 快速計算
- 指標之間的互補性與冗餘性
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import OUTPUT_DIR
from src.data_loader import download_stock_data
from src.feature_engineer import add_price_features, add_technical_indicators
from src.plot_utils import apply_style

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


def main() -> None:
    df = download_stock_data(ticker="AAPL", start="2022-01-01")

    # === 1. 計算技術指標 ===
    print("=== 技術指標計算 ===")
    df = add_price_features(df)
    df = add_technical_indicators(df)
    df = df.dropna()
    print(f"  指標欄位數: {len(df.columns)}")
    print(f"  有效樣本數: {len(df)}")

    # === 2. 指標概覽 ===
    indicator_cols = [c for c in df.columns if any(
        x in c for x in ["RSI", "MACD", "BB", "STOCH", "WILLR", "SMA", "EMA"]
    )]
    print(f"\n  技術指標欄位:")
    for col in indicator_cols:
        print(f"    {col}: {df[col].describe()[['mean', 'std', 'min', 'max']].to_dict()}")

    # === 3. 相關性分析 ===
    apply_style()
    target = (df["Close"].shift(-1) > df["Close"]).astype(int)
    target = target[:-1]  # 移除最後一筆（無未來值）
    df_corr = df.iloc[:-1][indicator_cols].copy()
    df_corr["Target"] = target.values

    corr_with_target = df_corr.corr()["Target"].drop("Target").sort_values()
    print(f"\n=== 與漲跌方向的相關性 ===")
    print(corr_with_target.to_string())

    # === 4. 視覺化 ===
    fig, axes = plt.subplots(2, 2, figsize=(14, 12))

    # RSI
    axes[0, 0].plot(df.index[-252:], df["RSI_14"][-252:])
    axes[0, 0].axhline(y=70, color="red", linestyle="--", alpha=0.5, label="超買 (70)")
    axes[0, 0].axhline(y=30, color="green", linestyle="--", alpha=0.5, label="超賣 (30)")
    axes[0, 0].set_title("RSI (14)")
    axes[0, 0].legend()

    # MACD
    macd_cols = [c for c in df.columns if "MACD" in c]
    if len(macd_cols) >= 2:
        axes[0, 1].plot(df.index[-252:], df[macd_cols[0]][-252:], label="MACD")
        axes[0, 1].plot(df.index[-252:], df[macd_cols[1]][-252:], label="Signal")
        if len(macd_cols) >= 3:
            axes[0, 1].bar(df.index[-252:], df[macd_cols[2]][-252:], alpha=0.3, label="Histogram")
        axes[0, 1].set_title("MACD")
        axes[0, 1].legend()

    # 布林通道
    bb_cols = [c for c in df.columns if "BB" in c and c != "BB_Position"]
    if bb_cols:
        axes[1, 0].plot(df.index[-252:], df["Close"][-252:], label="Close", linewidth=1)
        for col in bb_cols[:3]:
            axes[1, 0].plot(df.index[-252:], df[col][-252:], label=col, alpha=0.7, linestyle="--")
        axes[1, 0].set_title("布林通道")
        axes[1, 0].legend(fontsize=8)

    # 指標相關矩陣
    corr_matrix = df[indicator_cols[:10]].corr()
    sns.heatmap(corr_matrix, annot=True, fmt=".2f", cmap="RdBu_r", ax=axes[1, 1],
                vmin=-1, vmax=1, center=0, xticklabels=True, yticklabels=True)
    axes[1, 1].set_title("指標相關矩陣 (前10個)")
    axes[1, 1].tick_params(axis="x", rotation=45)

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "ch04_technical_indicators.png", dpi=150, bbox_inches="tight")
    plt.show()

    print("\n=== 重點提醒 ===")
    print("  1. 高度相關的指標可能帶來冗餘，不一定要全部使用")
    print("  2. RSI 與 Williams %R 高度負相關（數學上類似）")
    print("  3. 技術指標是從價量衍生的，本質上是特徵變換")


if __name__ == "__main__":
    main()

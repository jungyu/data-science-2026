"""
Ch04-01: 滯後特徵與滾動窗口統計。

學習重點：
- 為什麼需要滯後特徵
- 如何選擇適當的滯後天數
- 滾動窗口統計量（均值、標準差、最大值、最小值）
- 避免資料洩漏的關鍵原則
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import OUTPUT_DIR
from src.data_loader import download_stock_data
from src.plot_utils import apply_style

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.feature_selection import mutual_info_classif


def main() -> None:
    df = download_stock_data(ticker="AAPL", start="2018-01-01")

    # === 1. 基礎滯後特徵 ===
    print("=== 建構滯後特徵 ===")
    df["Return"] = df["Close"].pct_change()

    lags = [1, 2, 3, 5, 10, 20]
    for lag in lags:
        df[f"Close_Lag_{lag}"] = df["Close"].shift(lag)
        df[f"Return_Lag_{lag}"] = df["Return"].shift(lag)
        df[f"Volume_Lag_{lag}"] = df["Volume"].shift(lag)

    # === 2. 滾動窗口統計 ===
    print("=== 滾動窗口統計 ===")
    windows = [5, 10, 20]
    for w in windows:
        df[f"Return_RollMean_{w}"] = df["Return"].rolling(w).mean()
        df[f"Return_RollStd_{w}"] = df["Return"].rolling(w).std()
        df[f"Close_RollMax_{w}"] = df["Close"].rolling(w).max()
        df[f"Close_RollMin_{w}"] = df["Close"].rolling(w).min()
        # 價格在近期高低點的位置
        df[f"Close_Position_{w}"] = (
            (df["Close"] - df[f"Close_RollMin_{w}"])
            / (df[f"Close_RollMax_{w}"] - df[f"Close_RollMin_{w}"])
        )

    # === 3. 目標變數 ===
    df["Target"] = (df["Close"].shift(-1) > df["Close"]).astype(int)
    df = df.dropna()

    print(f"  特徵數: {len(df.columns) - 1}")
    print(f"  樣本數: {len(df)}")

    # === 4. 互資訊分析：找出最有用的特徵 ===
    print("\n=== 互資訊特徵重要性 ===")
    feature_cols = [c for c in df.columns if c not in ["Target", "Open", "High", "Low", "Close", "Volume"]]
    X = df[feature_cols].values
    y = df["Target"].values

    mi_scores = mutual_info_classif(X, y, random_state=42)
    mi_ranking = sorted(zip(feature_cols, mi_scores), key=lambda x: x[1], reverse=True)

    print(f"\n  Top 15 特徵:")
    for name, score in mi_ranking[:15]:
        bar = "#" * int(score * 200)
        print(f"    {name:<25} {score:.4f} {bar}")

    # === 5. 視覺化 ===
    apply_style()
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # 滯後自相關
    correlations = [df["Return"].corr(df[f"Return_Lag_{lag}"]) for lag in lags]
    axes[0, 0].bar([str(l) for l in lags], correlations)
    axes[0, 0].set_title("報酬率 vs 滯後報酬率 (相關係數)")
    axes[0, 0].set_xlabel("滯後天數")

    # 滾動波動率
    axes[0, 1].plot(df.index[-500:], df["Return_RollStd_20"][-500:])
    axes[0, 1].set_title("20 日滾動波動率")

    # 價格位置
    axes[1, 0].plot(df.index[-500:], df["Close_Position_20"][-500:], alpha=0.7)
    axes[1, 0].axhline(y=0.5, color="red", linestyle="--", alpha=0.5)
    axes[1, 0].set_title("20 日價格位置 (0=最低, 1=最高)")

    # 特徵重要性 Top 10
    top10 = mi_ranking[:10]
    axes[1, 1].barh([n for n, _ in top10], [s for _, s in top10])
    axes[1, 1].set_title("互資訊 Top 10 特徵")

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "ch04_lag_features.png", dpi=150, bbox_inches="tight")
    plt.show()

    print("\n=== 重點提醒 ===")
    print("  1. 滯後特徵只使用過去資訊，不會造成資料洩漏")
    print("  2. 滾動窗口大小是超參數，需要交叉驗證選擇")
    print("  3. 過多滯後特徵可能導致過擬合，用互資訊篩選")


if __name__ == "__main__":
    main()

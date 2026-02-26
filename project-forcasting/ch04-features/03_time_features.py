"""
Ch04-03: 時間特徵與週期性編碼。

學習重點：
- 為什麼星期一=0, 星期五=4 不是好的編碼方式
- 正弦/餘弦週期性編碼的原理
- 日曆效應（月末效應、星期效應）的實證
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import OUTPUT_DIR
from src.data_loader import download_stock_data
from src.feature_engineer import add_time_features
from src.plot_utils import apply_style

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def main() -> None:
    df = download_stock_data(ticker="AAPL", start="2018-01-01")
    df["Return"] = df["Close"].pct_change()
    df = add_time_features(df)
    df = df.dropna()

    # === 1. 星期效應 ===
    print("=== 星期效應 ===")
    day_names = ["週一", "週二", "週三", "週四", "週五"]
    day_returns = df.groupby("DayOfWeek")["Return"].agg(["mean", "std", "count"])
    day_returns.index = day_names[:len(day_returns)]
    print(day_returns.round(6))

    # === 2. 月份效應 ===
    print("\n=== 月份效應 ===")
    month_returns = df.groupby("Month")["Return"].agg(["mean", "std", "count"])
    print(month_returns.round(6))

    # === 3. 月末效應 ===
    print("\n=== 月末效應 ===")
    month_end = df.groupby("IsMonthEnd")["Return"].agg(["mean", "std", "count"])
    month_end.index = ["非月末", "月末"]
    print(month_end.round(6))

    # === 4. 週期性編碼說明 ===
    apply_style()
    fig, axes = plt.subplots(2, 3, figsize=(16, 10))

    # 星期效應柱狀圖
    axes[0, 0].bar(day_names[:len(day_returns)], day_returns["mean"] * 100)
    axes[0, 0].set_title("各星期平均日報酬率 (%)")
    axes[0, 0].axhline(y=0, color="red", linestyle="--", alpha=0.5)

    # 月份效應柱狀圖
    axes[0, 1].bar(range(1, 13), month_returns["mean"] * 100)
    axes[0, 1].set_title("各月平均日報酬率 (%)")
    axes[0, 1].set_xticks(range(1, 13))
    axes[0, 1].axhline(y=0, color="red", linestyle="--", alpha=0.5)

    # 整數編碼 vs 週期編碼
    days = np.arange(5)
    axes[0, 2].scatter(days, np.zeros_like(days), s=100)
    for i, name in enumerate(day_names):
        axes[0, 2].annotate(name, (i, 0), textcoords="offset points", xytext=(0, 10), ha='center')
    axes[0, 2].set_title("整數編碼：週五(4)和週一(0)距離=4")
    axes[0, 2].set_ylim(-0.5, 0.5)

    # 正弦/餘弦編碼
    theta = 2 * np.pi * days / 5
    sin_vals = np.sin(theta)
    cos_vals = np.cos(theta)
    axes[1, 0].scatter(sin_vals, cos_vals, s=100)
    for i, name in enumerate(day_names):
        axes[1, 0].annotate(name, (sin_vals[i], cos_vals[i]), textcoords="offset points", xytext=(5, 5))
    axes[1, 0].set_title("週期編碼：週五和週一距離相近")
    axes[1, 0].set_xlabel("sin(2π·day/5)")
    axes[1, 0].set_ylabel("cos(2π·day/5)")
    axes[1, 0].set_aspect("equal")
    axes[1, 0].grid(True)

    # 月份週期編碼
    months = np.arange(1, 13)
    theta_m = 2 * np.pi * months / 12
    axes[1, 1].scatter(np.sin(theta_m), np.cos(theta_m), s=100)
    for m in months:
        t = 2 * np.pi * m / 12
        axes[1, 1].annotate(f"{m}月", (np.sin(t), np.cos(t)), textcoords="offset points", xytext=(5, 5))
    axes[1, 1].set_title("月份週期編碼")
    axes[1, 1].set_xlabel("sin(2π·month/12)")
    axes[1, 1].set_ylabel("cos(2π·month/12)")
    axes[1, 1].set_aspect("equal")
    axes[1, 1].grid(True)

    # Sin/Cos 在時間軸上的值
    x = np.linspace(0, 4 * np.pi, 200)
    axes[1, 2].plot(x, np.sin(x), label="sin")
    axes[1, 2].plot(x, np.cos(x), label="cos")
    axes[1, 2].set_title("sin/cos 編碼：連續且週期性")
    axes[1, 2].legend()
    axes[1, 2].grid(True)

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "ch04_time_features.png", dpi=150, bbox_inches="tight")
    plt.show()

    print("\n=== 重點整理 ===")
    print("  1. 整數編碼會讓模型以為 週五(4)-週一(0)=4 很遠，但實際相鄰")
    print("  2. sin/cos 編碼保留了週期結構，距離正確反映時間接近程度")
    print("  3. 日曆效應在學術上有爭議，但作為特徵仍有實用價值")


if __name__ == "__main__":
    main()

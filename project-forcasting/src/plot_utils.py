"""
視覺化工具模組。

提供統一風格的圖表繪製函式，支援中文字體自動偵測。
"""

from __future__ import annotations

from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.config import CJK_FONT_CANDIDATES, OUTPUT_DIR, PLOT_DPI, PLOT_FIGSIZE, PLOT_STYLE


def setup_chinese_font() -> None:
    """自動偵測並設定中文字體。"""
    from matplotlib.font_manager import FontManager

    fm = FontManager()
    available = {f.name for f in fm.ttflist}

    for font_name in CJK_FONT_CANDIDATES:
        if font_name in available:
            matplotlib.rcParams["font.sans-serif"] = [font_name, "DejaVu Sans"]
            matplotlib.rcParams["axes.unicode_minus"] = False
            print(f"[字體] 使用 {font_name}")
            return

    print("[字體] 未找到中文字體，圖表中文可能無法正確顯示")
    matplotlib.rcParams["axes.unicode_minus"] = False


def apply_style() -> None:
    """套用統一的圖表風格。"""
    try:
        plt.style.use(PLOT_STYLE)
    except OSError:
        plt.style.use("seaborn-v0_8")
    setup_chinese_font()


def plot_price_history(
    df: pd.DataFrame,
    title: str = "股價走勢",
    save_name: str | None = None,
) -> None:
    """繪製收盤價走勢圖。"""
    apply_style()
    fig, axes = plt.subplots(2, 1, figsize=PLOT_FIGSIZE, height_ratios=[3, 1], sharex=True)

    axes[0].plot(df.index, df["Close"], linewidth=1.2)
    axes[0].set_title(title, fontsize=14)
    axes[0].set_ylabel("收盤價")

    axes[1].bar(df.index, df["Volume"], alpha=0.6, width=1)
    axes[1].set_ylabel("成交量")
    axes[1].set_xlabel("日期")

    plt.tight_layout()
    if save_name:
        plt.savefig(OUTPUT_DIR / save_name, dpi=PLOT_DPI, bbox_inches="tight")
    plt.show()


def plot_equity_curve(
    equity_df: pd.DataFrame,
    title: str = "策略淨值 vs 買入持有",
    save_name: str | None = None,
) -> None:
    """繪製回測淨值曲線。"""
    apply_style()
    fig, ax = plt.subplots(figsize=PLOT_FIGSIZE)

    ax.plot(equity_df.index, equity_df["Strategy_Equity"], label="策略", linewidth=1.5)
    ax.plot(equity_df.index, equity_df["BuyHold_Equity"], label="買入持有", linewidth=1.5, alpha=0.7)

    ax.set_title(title, fontsize=14)
    ax.set_ylabel("淨值")
    ax.set_xlabel("日期")
    ax.legend(fontsize=12)

    plt.tight_layout()
    if save_name:
        plt.savefig(OUTPUT_DIR / save_name, dpi=PLOT_DPI, bbox_inches="tight")
    plt.show()


def plot_feature_importance(
    feature_names: list[str],
    importances: np.ndarray,
    top_n: int = 20,
    title: str = "特徵重要性",
    save_name: str | None = None,
) -> None:
    """繪製特徵重要性橫條圖。"""
    apply_style()
    idx = np.argsort(importances)[-top_n:]
    fig, ax = plt.subplots(figsize=(10, max(6, top_n * 0.35)))

    ax.barh(range(len(idx)), importances[idx])
    ax.set_yticks(range(len(idx)))
    ax.set_yticklabels([feature_names[i] for i in idx])
    ax.set_title(title, fontsize=14)
    ax.set_xlabel("重要性")

    plt.tight_layout()
    if save_name:
        plt.savefig(OUTPUT_DIR / save_name, dpi=PLOT_DPI, bbox_inches="tight")
    plt.show()


def plot_confusion_matrix(
    cm: np.ndarray,
    labels: list[str] | None = None,
    title: str = "混淆矩陣",
    save_name: str | None = None,
) -> None:
    """繪製混淆矩陣熱力圖。"""
    import seaborn as sns

    apply_style()
    labels = labels or ["跌 (0)", "漲 (1)"]
    fig, ax = plt.subplots(figsize=(6, 5))

    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues", xticklabels=labels, yticklabels=labels, ax=ax)
    ax.set_title(title, fontsize=14)
    ax.set_ylabel("實際")
    ax.set_xlabel("預測")

    plt.tight_layout()
    if save_name:
        plt.savefig(OUTPUT_DIR / save_name, dpi=PLOT_DPI, bbox_inches="tight")
    plt.show()


def plot_predictions_vs_actual(
    dates: pd.DatetimeIndex,
    actual: np.ndarray,
    predicted: np.ndarray,
    title: str = "預測 vs 實際",
    save_name: str | None = None,
) -> None:
    """繪製預測值與實際值的對比圖（適用於連續值預測）。"""
    apply_style()
    fig, ax = plt.subplots(figsize=PLOT_FIGSIZE)

    ax.plot(dates, actual, label="實際值", linewidth=1.2)
    ax.plot(dates, predicted, label="預測值", linewidth=1.2, alpha=0.8)

    ax.set_title(title, fontsize=14)
    ax.set_ylabel("值")
    ax.set_xlabel("日期")
    ax.legend(fontsize=12)

    plt.tight_layout()
    if save_name:
        plt.savefig(OUTPUT_DIR / save_name, dpi=PLOT_DPI, bbox_inches="tight")
    plt.show()

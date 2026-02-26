"""
模型評估模組。

提供分類模型評估、回測分析、Walk-forward 驗證等功能。
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    roc_auc_score,
)
from sklearn.model_selection import TimeSeriesSplit


def evaluate_classifier(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_prob: np.ndarray | None = None,
) -> dict[str, Any]:
    """
    評估二元分類模型。

    Parameters
    ----------
    y_true : array-like
        真實標籤
    y_pred : array-like
        預測標籤
    y_prob : array-like | None
        預測機率（用於計算 AUC）

    Returns
    -------
    dict
        包含 accuracy, auc, confusion_matrix, report 的字典
    """
    results: dict[str, Any] = {
        "accuracy": accuracy_score(y_true, y_pred),
        "confusion_matrix": confusion_matrix(y_true, y_pred),
        "report": classification_report(y_true, y_pred, output_dict=True),
    }

    if y_prob is not None:
        results["auc"] = roc_auc_score(y_true, y_prob)

    return results


def print_evaluation(results: dict[str, Any]) -> None:
    """格式化輸出評估結果。"""
    print("=" * 50)
    print(f"  準確率 (Accuracy): {results['accuracy']:.4f}")
    if "auc" in results:
        print(f"  AUC-ROC:           {results['auc']:.4f}")
    print(f"\n  混淆矩陣:")
    cm = results["confusion_matrix"]
    print(f"    預測↓ \\ 實際→  跌(0)  漲(1)")
    print(f"    跌(0)         {cm[0][0]:>5}  {cm[0][1]:>5}")
    print(f"    漲(1)         {cm[1][0]:>5}  {cm[1][1]:>5}")

    report = results["report"]
    print(f"\n  精確率 (0/1): {report['0']['precision']:.3f} / {report['1']['precision']:.3f}")
    print(f"  召回率 (0/1): {report['0']['recall']:.3f} / {report['1']['recall']:.3f}")
    print(f"  F1     (0/1): {report['0']['f1-score']:.3f} / {report['1']['f1-score']:.3f}")
    print("=" * 50)


def backtest_strategy(
    df: pd.DataFrame,
    y_pred: np.ndarray,
    initial_capital: float = 100_000.0,
    transaction_cost: float = 0.001,
) -> dict[str, Any]:
    """
    簡易回測：根據預測方向決定持倉。

    Parameters
    ----------
    df : pd.DataFrame
        包含 Close 與 Return 的測試集資料
    y_pred : array-like
        預測方向 (1=做多, 0=空手)
    initial_capital : float
        初始資金
    transaction_cost : float
        單邊交易成本比率（預設 0.1%）

    Returns
    -------
    dict
        回測結果，包含累積報酬、夏普比率、最大回撤等
    """
    test_df = df.iloc[-len(y_pred):].copy()
    test_df["Signal"] = y_pred
    test_df["Signal_Change"] = test_df["Signal"].diff().abs().fillna(0)

    # 策略報酬 = 信號 × 日報酬 - 換手成本
    test_df["Strategy_Return"] = (
        test_df["Signal"] * test_df["Return"]
        - test_df["Signal_Change"] * transaction_cost
    )
    test_df["BuyHold_Return"] = test_df["Return"]

    # 累積淨值
    test_df["Strategy_Equity"] = initial_capital * (1 + test_df["Strategy_Return"]).cumprod()
    test_df["BuyHold_Equity"] = initial_capital * (1 + test_df["BuyHold_Return"]).cumprod()

    # 績效指標
    strategy_total = test_df["Strategy_Equity"].iloc[-1] / initial_capital - 1
    buyhold_total = test_df["BuyHold_Equity"].iloc[-1] / initial_capital - 1

    # 年化夏普比率（假設 252 交易日）
    daily_returns = test_df["Strategy_Return"]
    sharpe = np.sqrt(252) * daily_returns.mean() / daily_returns.std() if daily_returns.std() > 0 else 0.0

    # 最大回撤
    cummax = test_df["Strategy_Equity"].cummax()
    drawdown = (test_df["Strategy_Equity"] - cummax) / cummax
    max_drawdown = drawdown.min()

    # 勝率
    winning_days = (test_df["Strategy_Return"] > 0).sum()
    trading_days = (test_df["Signal"] == 1).sum()
    win_rate = winning_days / trading_days if trading_days > 0 else 0.0

    results = {
        "strategy_return": strategy_total,
        "buyhold_return": buyhold_total,
        "excess_return": strategy_total - buyhold_total,
        "sharpe_ratio": sharpe,
        "max_drawdown": max_drawdown,
        "win_rate": win_rate,
        "trading_days": int(trading_days),
        "total_days": len(test_df),
        "equity_curve": test_df[["Strategy_Equity", "BuyHold_Equity"]],
    }

    return results


def print_backtest(results: dict[str, Any]) -> None:
    """格式化輸出回測結果。"""
    print("=" * 50)
    print("  回測績效摘要")
    print("-" * 50)
    print(f"  策略總報酬:   {results['strategy_return']:>+8.2%}")
    print(f"  買入持有報酬: {results['buyhold_return']:>+8.2%}")
    print(f"  超額報酬:     {results['excess_return']:>+8.2%}")
    print(f"  夏普比率:     {results['sharpe_ratio']:>8.3f}")
    print(f"  最大回撤:     {results['max_drawdown']:>8.2%}")
    print(f"  勝率:         {results['win_rate']:>8.2%}")
    print(f"  交易天數:     {results['trading_days']:>5} / {results['total_days']}")
    print("=" * 50)


def walk_forward_split(
    n_samples: int,
    n_splits: int = 5,
    train_ratio: float = 0.7,
    min_train_size: int | None = None,
) -> list[tuple[np.ndarray, np.ndarray]]:
    """
    Walk-forward 驗證分割（擴展窗口）。

    Parameters
    ----------
    n_samples : int
        總樣本數
    n_splits : int
        分割次數
    train_ratio : float
        初始訓練集佔比
    min_train_size : int | None
        最小訓練集大小

    Returns
    -------
    list[tuple[ndarray, ndarray]]
        每個 fold 的 (train_indices, test_indices)
    """
    if min_train_size is None:
        min_train_size = int(n_samples * train_ratio)

    test_size = (n_samples - min_train_size) // n_splits
    splits = []

    for i in range(n_splits):
        train_end = min_train_size + i * test_size
        test_end = min(train_end + test_size, n_samples)
        if train_end >= n_samples:
            break
        train_idx = np.arange(0, train_end)
        test_idx = np.arange(train_end, test_end)
        splits.append((train_idx, test_idx))

    return splits

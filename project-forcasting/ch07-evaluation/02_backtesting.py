"""
Ch07-02: 進階回測系統。

學習重點：
- 交易成本對績效的影響
- 風險調整報酬指標（夏普、Sortino、Calmar）
- 多策略比較框架
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import DATA_DIR, MODEL_DIR, OUTPUT_DIR, RANDOM_SEED, TRAIN_TEST_SPLIT_DATE
from src.data_loader import download_stock_data, train_test_split_by_date
from src.feature_engineer import build_feature_matrix
from src.plot_utils import apply_style

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def get_feature_target(df):
    exclude = {"Target", "Open", "High", "Low", "Close", "Volume"}
    feature_cols = [c for c in df.columns if c not in exclude]
    return df[feature_cols], df["Target"]


def advanced_backtest(
    df: pd.DataFrame,
    signals: np.ndarray,
    transaction_cost: float = 0.001,
    initial_capital: float = 100_000.0,
) -> dict:
    """進階回測引擎。"""
    test_df = df.iloc[-len(signals):].copy()
    returns = test_df["Close"].pct_change().fillna(0)

    signal_change = np.abs(np.diff(signals, prepend=signals[0]))
    strategy_returns = signals * returns.values - signal_change * transaction_cost

    # 累積淨值
    equity = initial_capital * np.cumprod(1 + strategy_returns)
    buyhold = initial_capital * np.cumprod(1 + returns.values)

    # 夏普比率
    sharpe = np.sqrt(252) * strategy_returns.mean() / strategy_returns.std() if strategy_returns.std() > 0 else 0

    # Sortino 比率（只計算下行波動）
    downside = strategy_returns[strategy_returns < 0]
    sortino = np.sqrt(252) * strategy_returns.mean() / downside.std() if len(downside) > 0 and downside.std() > 0 else 0

    # 最大回撤
    peak = np.maximum.accumulate(equity)
    drawdown = (equity - peak) / peak
    max_drawdown = drawdown.min()

    # Calmar 比率
    annual_return = (equity[-1] / initial_capital) ** (252 / len(equity)) - 1
    calmar = annual_return / abs(max_drawdown) if max_drawdown != 0 else 0

    return {
        "total_return": equity[-1] / initial_capital - 1,
        "buyhold_return": buyhold[-1] / initial_capital - 1,
        "sharpe": sharpe,
        "sortino": sortino,
        "calmar": calmar,
        "max_drawdown": max_drawdown,
        "win_rate": (strategy_returns > 0).sum() / (signals == 1).sum() if (signals == 1).sum() > 0 else 0,
        "equity": equity,
        "buyhold_equity": buyhold,
        "drawdown": drawdown,
        "dates": test_df.index,
    }


def main() -> None:
    print("=== 進階回測系統 ===\n")

    cache_path = DATA_DIR / "feature_matrix_full.parquet"
    if cache_path.exists():
        feature_df = pd.read_parquet(cache_path)
    else:
        df = download_stock_data(ticker="AAPL", start="2018-01-01")
        feature_df = build_feature_matrix(df, target_type="direction")

    train_df, test_df = train_test_split_by_date(feature_df, TRAIN_TEST_SPLIT_DATE)
    X_train, y_train = get_feature_target(train_df)
    X_test, y_test = get_feature_target(test_df)

    # === 1. 載入或訓練模型 ===
    from lightgbm import LGBMClassifier

    model_path = MODEL_DIR / "lightgbm_model.joblib"
    if model_path.exists():
        model = joblib.load(model_path)
        print("[載入] LightGBM 模型")
    else:
        model = LGBMClassifier(n_estimators=300, learning_rate=0.05, random_state=RANDOM_SEED, verbose=-1)
        model.fit(X_train, y_train)
        print("[訓練] LightGBM 模型")

    y_pred = model.predict(X_test)

    # === 2. 不同交易成本的影響 ===
    print("\n=== 交易成本敏感度分析 ===")
    costs = [0.0, 0.0005, 0.001, 0.002, 0.005]
    cost_results = {}

    print(f"{'成本':<8} {'總報酬':>10} {'夏普':>8} {'最大回撤':>10} {'勝率':>8}")
    print("-" * 50)

    for cost in costs:
        res = advanced_backtest(test_df, y_pred, transaction_cost=cost)
        cost_results[cost] = res
        print(f"{cost:<8.4f} {res['total_return']:>+10.2%} {res['sharpe']:>8.3f} {res['max_drawdown']:>10.2%} {res['win_rate']:>8.2%}")

    # === 3. 多策略比較 ===
    print("\n=== 策略比較 ===")
    strategies = {
        "模型預測": y_pred,
        "永遠做多": np.ones(len(y_pred)),
        "永遠空手": np.zeros(len(y_pred)),
        "隨機交易": np.random.RandomState(42).randint(0, 2, len(y_pred)),
    }

    print(f"{'策略':<12} {'總報酬':>10} {'夏普':>8} {'Sortino':>8} {'Calmar':>8} {'最大回撤':>10}")
    print("-" * 62)

    strategy_results = {}
    for name, signals in strategies.items():
        res = advanced_backtest(test_df, signals, transaction_cost=0.001)
        strategy_results[name] = res
        print(f"{name:<12} {res['total_return']:>+10.2%} {res['sharpe']:>8.3f} {res['sortino']:>8.3f} {res['calmar']:>8.3f} {res['max_drawdown']:>10.2%}")

    # === 4. 視覺化 ===
    apply_style()
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # 淨值曲線
    for name, res in strategy_results.items():
        axes[0, 0].plot(res["dates"], res["equity"], label=name, linewidth=1.2)
    axes[0, 0].set_title("策略淨值曲線（含交易成本 0.1%）")
    axes[0, 0].set_ylabel("淨值")
    axes[0, 0].legend()

    # 回撤圖
    model_res = strategy_results["模型預測"]
    axes[0, 1].fill_between(model_res["dates"], model_res["drawdown"] * 100, 0, alpha=0.6, color="red")
    axes[0, 1].set_title("模型策略回撤")
    axes[0, 1].set_ylabel("回撤 (%)")

    # 交易成本影響
    cost_vals = list(cost_results.keys())
    returns_by_cost = [cost_results[c]["total_return"] * 100 for c in cost_vals]
    sharpe_by_cost = [cost_results[c]["sharpe"] for c in cost_vals]

    axes[1, 0].plot([c * 100 for c in cost_vals], returns_by_cost, "o-", color="#2196F3")
    axes[1, 0].set_title("交易成本 vs 總報酬")
    axes[1, 0].set_xlabel("單邊成本 (%)")
    axes[1, 0].set_ylabel("總報酬 (%)")

    axes[1, 1].plot([c * 100 for c in cost_vals], sharpe_by_cost, "s-", color="#FF9800")
    axes[1, 1].set_title("交易成本 vs 夏普比率")
    axes[1, 1].set_xlabel("單邊成本 (%)")
    axes[1, 1].set_ylabel("夏普比率")

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "ch07_backtesting.png", dpi=150, bbox_inches="tight")
    plt.show()


if __name__ == "__main__":
    main()

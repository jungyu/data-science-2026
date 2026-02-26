"""
Ch03-02: Prophet 進階用法。

學習重點：
- 自訂季節性（例如：月度效應）
- 假日效應
- 交叉驗證評估
- 超參數調整
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import OUTPUT_DIR
from src.data_loader import download_stock_data

import matplotlib.pyplot as plt
import pandas as pd
from prophet import Prophet
from prophet.diagnostics import cross_validation, performance_metrics


def create_us_market_holidays() -> pd.DataFrame:
    """建立美股重要假日/事件表。"""
    holidays = pd.DataFrame({
        "holiday": "earnings_season",
        "ds": pd.to_datetime([
            # 財報季開始（大約日期）
            "2020-01-15", "2020-04-15", "2020-07-15", "2020-10-15",
            "2021-01-15", "2021-04-15", "2021-07-15", "2021-10-15",
            "2022-01-15", "2022-04-15", "2022-07-15", "2022-10-15",
            "2023-01-15", "2023-04-15", "2023-07-15", "2023-10-15",
            "2024-01-15", "2024-04-15", "2024-07-15", "2024-10-15",
        ]),
        "lower_window": -2,  # 事件前 2 天
        "upper_window": 5,   # 事件後 5 天
    })
    return holidays


def main() -> None:
    df = download_stock_data(ticker="AAPL", start="2020-01-01")
    prophet_df = df[["Close"]].reset_index()
    prophet_df.columns = ["ds", "y"]

    holidays = create_us_market_holidays()

    # === 1. 進階模型：自訂季節性 + 假日效應 ===
    print("=== Prophet 進階模型 ===")
    model = Prophet(
        daily_seasonality=False,
        weekly_seasonality=True,
        yearly_seasonality=True,
        holidays=holidays,
        changepoint_prior_scale=0.1,
        seasonality_prior_scale=10.0,
        holidays_prior_scale=10.0,
    )

    # 新增月度季節性
    model.add_seasonality(name="monthly", period=30.5, fourier_order=5)
    # 新增季度季節性
    model.add_seasonality(name="quarterly", period=91.25, fourier_order=3)

    model.fit(prophet_df)

    # === 2. 交叉驗證 ===
    print("\n=== 交叉驗證 ===")
    print("  initial=730 天, period=90 天, horizon=60 天")

    df_cv = cross_validation(
        model,
        initial="730 days",    # 最少訓練資料
        period="90 days",      # 每 90 天切一次
        horizon="60 days",     # 預測未來 60 天
    )

    df_perf = performance_metrics(df_cv)
    print(f"\n  不同預測步長的 MAPE:")
    print(df_perf[["horizon", "mape", "mae", "rmse"]].to_string(index=False))

    # === 3. 繪製交叉驗證結果 ===
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # MAPE 隨預測步長變化
    axes[0].plot(df_perf["horizon"].dt.days, df_perf["mape"] * 100)
    axes[0].set_xlabel("Horizon (days)")
    axes[0].set_ylabel("MAPE (%)")
    axes[0].set_title("MAPE vs Forecast Horizon")

    # MAE 隨預測步長變化
    axes[1].plot(df_perf["horizon"].dt.days, df_perf["mae"])
    axes[1].set_xlabel("Horizon (days)")
    axes[1].set_ylabel("MAE")
    axes[1].set_title("MAE vs Forecast Horizon")

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "ch03_prophet_cv.png", dpi=150, bbox_inches="tight")
    plt.show()

    # === 4. 超參數比較 ===
    print("\n=== 超參數敏感度分析 ===")
    scales = [0.01, 0.05, 0.1, 0.5]
    print(f"{'changepoint_prior_scale':<25} {'平均 MAPE':>12}")
    print("-" * 40)

    for scale in scales:
        m = Prophet(
            daily_seasonality=False,
            changepoint_prior_scale=scale,
        )
        m.fit(prophet_df)
        cv = cross_validation(m, initial="730 days", period="180 days", horizon="30 days")
        perf = performance_metrics(cv)
        avg_mape = perf["mape"].mean()
        print(f"{scale:<25} {avg_mape:>12.4%}")

    print("\n  較小的 scale → 趨勢更平滑（欠擬合風險）")
    print("  較大的 scale → 趨勢更彈性（過擬合風險）")


if __name__ == "__main__":
    main()

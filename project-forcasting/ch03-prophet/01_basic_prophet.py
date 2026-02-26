"""
Ch03-01: Prophet 基礎。

學習重點：
- Prophet 的資料格式要求 (ds, y)
- 自動趨勢與季節性分解
- 預測未來與信賴區間
- 成分分解視覺化
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
from sklearn.metrics import mean_absolute_error, mean_absolute_percentage_error


def main() -> None:
    df = download_stock_data(ticker="AAPL", start="2020-01-01")

    # Prophet 需要 ds (日期) 和 y (目標值) 兩欄
    prophet_df = df[["Close"]].reset_index()
    prophet_df.columns = ["ds", "y"]

    # 分割
    split_date = "2024-06-01"
    train = prophet_df[prophet_df["ds"] < split_date]
    test = prophet_df[prophet_df["ds"] >= split_date]

    print(f"=== Prophet 基礎模型 ===")
    print(f"  訓練集: {len(train)} 筆")
    print(f"  測試集: {len(test)} 筆")

    # === 1. 建立與擬合模型 ===
    model = Prophet(
        daily_seasonality=False,   # 日內資料才需要
        weekly_seasonality=True,   # 週效應（週一~五）
        yearly_seasonality=True,   # 年度季節性
        changepoint_prior_scale=0.05,  # 趨勢彈性（越大越彈性）
    )
    model.fit(train)

    # === 2. 預測 ===
    future = model.make_future_dataframe(periods=len(test), freq="B")  # B=營業日
    forecast = model.predict(future)

    # 取出測試期間的預測
    forecast_test = forecast[forecast["ds"].isin(test["ds"])]
    pred = forecast_test["yhat"].values
    actual = test["y"].values[:len(pred)]

    mae = mean_absolute_error(actual, pred)
    mape = mean_absolute_percentage_error(actual, pred)
    print(f"\n  MAE:  {mae:.2f}")
    print(f"  MAPE: {mape:.2%}")

    # === 3. 預測圖 ===
    fig1 = model.plot(forecast)
    fig1.set_size_inches(14, 7)
    plt.title("Prophet 預測（含信賴區間）")
    plt.savefig(OUTPUT_DIR / "ch03_prophet_forecast.png", dpi=150, bbox_inches="tight")
    plt.show()

    # === 4. 成分分解圖 ===
    fig2 = model.plot_components(forecast)
    fig2.set_size_inches(14, 10)
    plt.savefig(OUTPUT_DIR / "ch03_prophet_components.png", dpi=150, bbox_inches="tight")
    plt.show()

    # === 5. 變點偵測 ===
    print(f"\n=== 偵測到的趨勢變點 ===")
    changepoints = model.changepoints
    print(f"  共 {len(changepoints)} 個變點")
    print(f"  最近 5 個: {list(changepoints[-5:].dt.date)}")


if __name__ == "__main__":
    main()

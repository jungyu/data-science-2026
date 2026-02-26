"""
Ch02-01: 指數平滑法 (Exponential Smoothing)。

學習重點：
- 簡單指數平滑 (SES): 僅處理水準
- 雙重指數平滑 (Holt): 水準 + 趨勢
- 三重指數平滑 (Holt-Winters): 水準 + 趨勢 + 季節性
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
from statsmodels.tsa.holtwinters import ExponentialSmoothing, SimpleExpSmoothing


def main() -> None:
    df = download_stock_data(ticker="AAPL", start="2022-01-01")
    close = df["Close"].asfreq("B").ffill()

    # 分割：最後 60 個交易日作為測試集
    train = close[:-60]
    test = close[-60:]
    forecast_steps = len(test)

    apply_style()
    fig, axes = plt.subplots(3, 1, figsize=(14, 15))

    # === 1. 簡單指數平滑 (SES) ===
    print("=== 簡單指數平滑 ===")
    ses = SimpleExpSmoothing(train, initialization_method="estimated")
    ses_fit = ses.fit(optimized=True)
    ses_forecast = ses_fit.forecast(forecast_steps)
    print(f"  最佳 alpha: {ses_fit.params['smoothing_level']:.4f}")

    axes[0].plot(train.index, train, label="訓練集")
    axes[0].plot(test.index, test, label="測試集", color="orange")
    axes[0].plot(test.index, ses_forecast, label="SES 預測", color="red", linestyle="--")
    axes[0].set_title("簡單指數平滑 (SES)")
    axes[0].legend()

    # === 2. Holt 雙重指數平滑 ===
    print("\n=== Holt 雙重指數平滑 ===")
    holt = ExponentialSmoothing(
        train, trend="add", seasonal=None, initialization_method="estimated",
    )
    holt_fit = holt.fit(optimized=True)
    holt_forecast = holt_fit.forecast(forecast_steps)
    print(f"  alpha: {holt_fit.params['smoothing_level']:.4f}")
    print(f"  beta:  {holt_fit.params['smoothing_trend']:.4f}")

    axes[1].plot(train.index, train, label="訓練集")
    axes[1].plot(test.index, test, label="測試集", color="orange")
    axes[1].plot(test.index, holt_forecast, label="Holt 預測", color="red", linestyle="--")
    axes[1].set_title("Holt 雙重指數平滑 (趨勢)")
    axes[1].legend()

    # === 3. Holt-Winters 三重指數平滑 ===
    print("\n=== Holt-Winters 三重指數平滑 ===")
    hw = ExponentialSmoothing(
        train, trend="add", seasonal="add", seasonal_periods=252,
        initialization_method="estimated",
    )
    hw_fit = hw.fit(optimized=True)
    hw_forecast = hw_fit.forecast(forecast_steps)
    print(f"  alpha: {hw_fit.params['smoothing_level']:.4f}")
    print(f"  beta:  {hw_fit.params['smoothing_trend']:.4f}")
    print(f"  gamma: {hw_fit.params['smoothing_seasonal']:.4f}")

    axes[2].plot(train.index, train, label="訓練集")
    axes[2].plot(test.index, test, label="測試集", color="orange")
    axes[2].plot(test.index, hw_forecast, label="Holt-Winters 預測", color="red", linestyle="--")
    axes[2].set_title("Holt-Winters 三重指數平滑 (趨勢 + 季節性)")
    axes[2].legend()

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "ch02_exponential_smoothing.png", dpi=150, bbox_inches="tight")
    plt.show()

    # === 4. 預測誤差比較 ===
    from sklearn.metrics import mean_absolute_error, mean_squared_error

    print("\n=== 預測誤差比較 ===")
    print(f"{'模型':<20} {'MAE':>10} {'RMSE':>10}")
    print("-" * 42)
    for name, forecast in [("SES", ses_forecast), ("Holt", holt_forecast), ("Holt-Winters", hw_forecast)]:
        mae = mean_absolute_error(test, forecast)
        rmse = np.sqrt(mean_squared_error(test, forecast))
        print(f"{name:<20} {mae:>10.2f} {rmse:>10.2f}")


if __name__ == "__main__":
    main()

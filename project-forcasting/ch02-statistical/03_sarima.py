"""
Ch02-03: SARIMA 季節性模型。

學習重點：
- SARIMA(p,d,q)(P,D,Q,s) 的季節參數
- 使用 statsmodels SARIMAX 實作
- 網格搜尋最佳參數組合
"""

from __future__ import annotations

import itertools
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import OUTPUT_DIR
from src.data_loader import download_stock_data
from src.plot_utils import apply_style

import matplotlib.pyplot as plt
import numpy as np
import warnings
from sklearn.metrics import mean_absolute_error, mean_squared_error
from statsmodels.tsa.statespace.sarimax import SARIMAX


def main() -> None:
    df = download_stock_data(ticker="AAPL", start="2020-01-01")
    close = df["Close"].asfreq("B").ffill()

    train = close[:-60]
    test = close[-60:]
    forecast_steps = len(test)

    # === 1. 簡化的網格搜尋 ===
    # 股價的季節性較弱，這裡示範 s=5（週週期）的 SARIMA
    print("=== SARIMA 參數搜尋 ===")
    print("  季節週期 s=5（每週 5 個交易日）")

    p_range = [0, 1, 2]
    d_range = [1]
    q_range = [0, 1]
    P_range = [0, 1]
    D_range = [0, 1]
    Q_range = [0, 1]
    s = 5

    best_aic = np.inf
    best_params = None

    total = len(list(itertools.product(p_range, d_range, q_range, P_range, D_range, Q_range)))
    print(f"  共 {total} 種組合，搜尋中...")

    for p, d, q in itertools.product(p_range, d_range, q_range):
        for P, D, Q in itertools.product(P_range, D_range, Q_range):
            try:
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore")
                    model = SARIMAX(
                        train,
                        order=(p, d, q),
                        seasonal_order=(P, D, Q, s),
                        enforce_stationarity=False,
                        enforce_invertibility=False,
                    )
                    result = model.fit(disp=False, maxiter=100)
                    if result.aic < best_aic:
                        best_aic = result.aic
                        best_params = ((p, d, q), (P, D, Q, s))
            except Exception:
                continue

    print(f"\n  最佳模型: SARIMA{best_params[0]}x{best_params[1]}")
    print(f"  AIC: {best_aic:.1f}")

    # === 2. 用最佳參數預測 ===
    best_model = SARIMAX(
        train,
        order=best_params[0],
        seasonal_order=best_params[1],
        enforce_stationarity=False,
        enforce_invertibility=False,
    )
    best_result = best_model.fit(disp=False)
    forecast = best_result.get_forecast(steps=forecast_steps)
    pred = forecast.predicted_mean
    ci = forecast.conf_int()

    mae = mean_absolute_error(test, pred)
    rmse = np.sqrt(mean_squared_error(test, pred))
    print(f"  MAE: {mae:.2f}")
    print(f"  RMSE: {rmse:.2f}")

    # === 3. 繪圖 ===
    apply_style()
    fig, ax = plt.subplots(figsize=(14, 7))

    ax.plot(train.index[-120:], train[-120:], label="訓練集")
    ax.plot(test.index, test, label="測試集", color="orange")
    ax.plot(test.index, pred, label=f"SARIMA{best_params[0]}x{best_params[1]}", color="red", linestyle="--")
    ax.fill_between(test.index, ci.iloc[:, 0], ci.iloc[:, 1], alpha=0.15, color="red", label="95% CI")
    ax.set_title(f"SARIMA 預測 — AIC={best_aic:.0f}, MAE={mae:.2f}")
    ax.legend()

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "ch02_sarima.png", dpi=150, bbox_inches="tight")
    plt.show()


if __name__ == "__main__":
    main()

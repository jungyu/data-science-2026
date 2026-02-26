"""
Ch02-02: ARIMA 模型。

學習重點：
- ARIMA(p, d, q) 各參數的意義
- 手動定階：ACF/PACF + AIC/BIC
- 自動定階：pmdarima.auto_arima（或 statsmodels 替代）
- 殘差診斷：確認模型充分捕捉結構
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
from sklearn.metrics import mean_absolute_error, mean_squared_error
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.graphics.tsaplots import plot_acf


def fit_arima(train, order, forecast_steps):
    """擬合 ARIMA 並預測。"""
    model = ARIMA(train, order=order)
    result = model.fit()
    forecast = result.get_forecast(steps=forecast_steps)
    return result, forecast


def main() -> None:
    df = download_stock_data(ticker="AAPL", start="2022-01-01")
    close = df["Close"].asfreq("B").ffill()

    train = close[:-60]
    test = close[-60:]
    forecast_steps = len(test)

    # === 1. 嘗試不同 ARIMA 階數 ===
    orders_to_try = [
        (1, 1, 0),  # AR(1) + 差分
        (0, 1, 1),  # MA(1) + 差分
        (1, 1, 1),  # ARMA(1,1) + 差分
        (2, 1, 2),  # ARMA(2,2) + 差分
        (5, 1, 0),  # AR(5) + 差分
    ]

    print("=== ARIMA 模型比較 ===")
    print(f"{'階數 (p,d,q)':<15} {'AIC':>10} {'BIC':>10} {'MAE':>10} {'RMSE':>10}")
    print("-" * 57)

    results = {}
    for order in orders_to_try:
        try:
            result, forecast_obj = fit_arima(train, order, forecast_steps)
            pred = forecast_obj.predicted_mean
            mae = mean_absolute_error(test, pred)
            rmse = np.sqrt(mean_squared_error(test, pred))
            print(f"{str(order):<15} {result.aic:>10.1f} {result.bic:>10.1f} {mae:>10.2f} {rmse:>10.2f}")
            results[order] = {"result": result, "pred": pred, "mae": mae}
        except Exception as e:
            print(f"{str(order):<15} 擬合失敗: {e}")

    # === 2. 選取最佳模型繪圖 ===
    best_order = min(results, key=lambda k: results[k]["mae"])
    best = results[best_order]
    print(f"\n最佳模型: ARIMA{best_order}（MAE 最低）")

    apply_style()
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # 預測圖
    forecast_obj = best["result"].get_forecast(steps=forecast_steps)
    pred = forecast_obj.predicted_mean
    ci = forecast_obj.conf_int()

    axes[0, 0].plot(train.index[-120:], train[-120:], label="訓練集")
    axes[0, 0].plot(test.index, test, label="測試集", color="orange")
    axes[0, 0].plot(test.index, pred, label=f"ARIMA{best_order}", color="red", linestyle="--")
    axes[0, 0].fill_between(test.index, ci.iloc[:, 0], ci.iloc[:, 1], alpha=0.15, color="red")
    axes[0, 0].set_title(f"ARIMA{best_order} 預測（含 95% 信賴區間）")
    axes[0, 0].legend()

    # 殘差圖
    residuals = best["result"].resid
    axes[0, 1].plot(residuals, linewidth=0.5)
    axes[0, 1].axhline(y=0, color="red", linestyle="--")
    axes[0, 1].set_title("殘差時序圖")

    # 殘差分佈
    axes[1, 0].hist(residuals, bins=50, edgecolor="white")
    axes[1, 0].set_title("殘差分佈")

    # 殘差 ACF
    plot_acf(residuals, lags=30, ax=axes[1, 1], title="殘差 ACF")

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "ch02_arima.png", dpi=150, bbox_inches="tight")
    plt.show()

    print("\n=== 殘差診斷 ===")
    print(f"  殘差均值: {residuals.mean():.6f}（應接近 0）")
    print(f"  殘差標準差: {residuals.std():.4f}")
    print("  若殘差 ACF 皆在信賴帶內，表示模型已充分捕捉序列結構")


if __name__ == "__main__":
    main()

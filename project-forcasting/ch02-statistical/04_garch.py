"""
Ch02-04: GARCH 波動率模型。

學習重點：
- 為什麼報酬率的 ACF 不顯著，但報酬率²的 ACF 顯著？→ 波動聚集
- GARCH(1,1) 模型原理
- 使用 arch 套件擬合波動率模型
- 波動率預測的應用（風險管理、選擇權定價）
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
from arch import arch_model


def main() -> None:
    df = download_stock_data(ticker="AAPL", start="2018-01-01")
    returns = df["Close"].pct_change().dropna() * 100  # 百分比報酬率

    train = returns[:-252]  # 最後一年作為測試
    test = returns[-252:]

    # === 1. 擬合 GARCH(1,1) ===
    print("=== GARCH(1,1) 模型 ===")
    model = arch_model(train, vol="Garch", p=1, q=1, mean="AR", lags=1, dist="t")
    result = model.fit(disp="off")
    print(result.summary().tables[1])

    # === 2. 條件波動率 (in-sample) ===
    cond_vol = result.conditional_volatility

    apply_style()
    fig, axes = plt.subplots(3, 1, figsize=(14, 12))

    axes[0].plot(train.index, train, linewidth=0.5, alpha=0.7)
    axes[0].set_title("日報酬率 (%)")
    axes[0].set_ylabel("報酬率 (%)")

    axes[1].plot(cond_vol.index, cond_vol, color="red", linewidth=0.8)
    axes[1].set_title("條件波動率 (GARCH 估計)")
    axes[1].set_ylabel("波動率 (%)")

    # === 3. 滾動波動率預測 ===
    print("\n=== 滾動一步預測 ===")
    rolling_forecasts = []
    for i in range(len(test)):
        train_window = returns[:len(train) + i]
        m = arch_model(train_window, vol="Garch", p=1, q=1, mean="AR", lags=1, dist="t")
        r = m.fit(disp="off", show_warning=False)
        fc = r.forecast(horizon=1)
        rolling_forecasts.append(np.sqrt(fc.variance.values[-1, 0]))

    pred_vol = np.array(rolling_forecasts)
    realized_vol = test.rolling(21).std()  # 21 日實現波動率

    axes[2].plot(test.index, realized_vol, label="21日實現波動率", alpha=0.7)
    axes[2].plot(test.index, pred_vol, label="GARCH 預測波動率", color="red", alpha=0.7)
    axes[2].set_title("波動率預測 vs 實現波動率")
    axes[2].set_ylabel("波動率 (%)")
    axes[2].legend()

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "ch02_garch.png", dpi=150, bbox_inches="tight")
    plt.show()

    # === 4. 模型比較 ===
    print("\n=== 不同 GARCH 變體比較 ===")
    variants = [
        ("GARCH(1,1)", {"vol": "Garch", "p": 1, "q": 1}),
        ("EGARCH(1,1)", {"vol": "EGARCH", "p": 1, "q": 1}),
        ("GJR-GARCH(1,1)", {"vol": "Garch", "p": 1, "o": 1, "q": 1}),
    ]

    print(f"{'模型':<20} {'AIC':>10} {'BIC':>10}")
    print("-" * 42)
    for name, params in variants:
        try:
            m = arch_model(train, mean="AR", lags=1, dist="t", **params)
            r = m.fit(disp="off")
            print(f"{name:<20} {r.aic:>10.1f} {r.bic:>10.1f}")
        except Exception as e:
            print(f"{name:<20} 失敗: {e}")

    print("\n  提示: EGARCH 可捕捉槓桿效應（跌幅造成的波動 > 漲幅）")


if __name__ == "__main__":
    main()

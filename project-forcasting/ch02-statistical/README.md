# Ch02 — 統計預測方法

## 學習目標

- 理解指數平滑法（ETS）的原理與適用場景
- 掌握 ARIMA/SARIMA 模型的建構流程
- 學會使用 auto_arima 自動定階
- 認識 GARCH 模型對波動率的建模

## 核心觀念

**模型演進路線**：
```
移動平均 → 指數平滑 (ETS) → ARIMA → SARIMA → GARCH
  簡單      ↑加入權重      ↑自迴歸+差分   ↑加季節性  ↑波動率建模
```

## 範例檔案

| 檔案 | 說明 |
|------|------|
| `01_exponential_smoothing.py` | 簡單/雙重/三重指數平滑 (Holt-Winters) |
| `02_arima.py` | ARIMA 模型：手動定階 vs auto_arima |
| `03_sarima.py` | 季節性 ARIMA，適用於有週期性的序列 |
| `04_garch.py` | GARCH 波動率模型，捕捉波動聚集效應 |

## 練習

1. 使用 Holt-Winters 預測未來 30 天的收盤價，觀察信賴區間
2. 嘗試不同 ARIMA 階數 (p,d,q)，比較 AIC/BIC 值
3. 對報酬率序列擬合 GARCH(1,1)，預測未來波動率

# Ch03 — Prophet 預測框架

## 學習目標

- 理解 Prophet 的加法分解模型設計哲學
- 掌握趨勢 (trend)、季節性 (seasonality)、假日效應 (holidays) 的設定
- 學會自訂季節性成分與交叉驗證
- 比較 Prophet 與統計方法的優劣

## 核心觀念

**Prophet 模型**：
```
y(t) = g(t) + s(t) + h(t) + ε(t)
  g(t): 趨勢（分段線性或邏輯曲線）
  s(t): 季節性（傅立葉級數）
  h(t): 假日/事件效應
  ε(t): 殘差
```

**設計哲學**：讓分析師（非統計專家）也能做出合理的時間序列預測。

## 範例檔案

| 檔案 | 說明 |
|------|------|
| `01_basic_prophet.py` | Prophet 基礎用法：趨勢與季節性分解 |
| `02_advanced_prophet.py` | 自訂季節性、變點偵測、交叉驗證 |

## 練習

1. 新增「財報季」假日效應（1月/4月/7月/10月），觀察預測變化
2. 調整 `changepoint_prior_scale` 參數，比較趨勢彈性
3. 使用 `cross_validation` 計算不同預測步長的 MAPE

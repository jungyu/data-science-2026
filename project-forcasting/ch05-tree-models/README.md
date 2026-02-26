# Ch05 — 梯度提升樹模型

## 學習目標

- 理解梯度提升 (Gradient Boosting) 的核心原理
- 掌握 LightGBM、XGBoost、CatBoost 三大框架的差異
- 學會使用 Optuna 進行貝葉斯超參數優化
- 比較三種模型的效能與特性

## 核心觀念

**梯度提升原理**：
```
最終預測 = 樹₁(x) + 樹₂(x) + 樹₃(x) + ... + 樹ₙ(x)
  每棵新樹學習前一棵的「殘差」，逐步修正預測
```

**三大框架比較**：
| 特性 | LightGBM | XGBoost | CatBoost |
|------|----------|---------|----------|
| 分裂策略 | Leaf-wise | Level-wise | Symmetric |
| 速度 | 最快 | 中等 | 較慢 |
| 類別特徵 | 需編碼 | 需編碼 | 原生支援 |
| 記憶體 | 最省 | 中等 | 較高 |

## 範例檔案

| 檔案 | 說明 |
|------|------|
| `01_lightgbm.py` | LightGBM 完整訓練流程 + Optuna 調參 |
| `02_xgboost.py` | XGBoost 訓練與早停策略 |
| `03_catboost.py` | CatBoost 訓練與內建視覺化 |
| `04_model_comparison.py` | 三種模型的統一比較框架 |

## 練習

1. 調整 Optuna 的搜尋空間，觀察不同超參數對效能的影響
2. 使用 SHAP 解釋 LightGBM 的預測
3. 嘗試 Stacking（將三個模型的預測作為 meta-learner 的輸入）

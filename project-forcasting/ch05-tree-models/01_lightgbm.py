"""
Ch05-01: LightGBM 漲跌預測。

學習重點：
- LightGBM 的 Leaf-wise 分裂策略
- 使用 Optuna 進行貝葉斯超參數優化
- 早停 (Early Stopping) 防止過擬合
- 特徵重要性分析
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import (
    DATA_DIR,
    LIGHTGBM_PARAMS,
    MODEL_DIR,
    OPTUNA_CV_SPLITS,
    OPTUNA_N_TRIALS,
    OUTPUT_DIR,
    RANDOM_SEED,
    TRAIN_TEST_SPLIT_DATE,
)
from src.data_loader import download_stock_data, train_test_split_by_date
from src.evaluator import backtest_strategy, evaluate_classifier, print_backtest, print_evaluation
from src.feature_engineer import build_feature_matrix
from src.plot_utils import plot_confusion_matrix, plot_equity_curve, plot_feature_importance

import joblib
import lightgbm as lgb
import numpy as np
import optuna
from sklearn.model_selection import TimeSeriesSplit


def get_feature_target(df, exclude_cols=None):
    """從特徵矩陣中分離 X 和 y。"""
    exclude = set(exclude_cols or []) | {"Target", "Open", "High", "Low", "Close", "Volume"}
    feature_cols = [c for c in df.columns if c not in exclude]
    return df[feature_cols], df["Target"]


def main() -> None:
    # === 1. 準備資料 ===
    print("=== LightGBM 股價漲跌預測 ===\n")

    # 嘗試讀取 ch04 產生的快取，否則重新建構
    cache_path = DATA_DIR / "feature_matrix_full.parquet"
    if cache_path.exists():
        import pandas as pd
        feature_df = pd.read_parquet(cache_path)
        print(f"[快取] 載入特徵矩陣 ({len(feature_df)} 筆)")
    else:
        df = download_stock_data(ticker="AAPL", start="2018-01-01")
        feature_df = build_feature_matrix(df, target_type="direction")

    train_df, test_df = train_test_split_by_date(feature_df, TRAIN_TEST_SPLIT_DATE)
    X_train, y_train = get_feature_target(train_df)
    X_test, y_test = get_feature_target(test_df)

    feature_names = list(X_train.columns)
    print(f"  特徵數: {len(feature_names)}")
    print(f"  訓練集: {len(X_train)} | 測試集: {len(X_test)}")

    # === 2. Optuna 超參數優化 ===
    print(f"\n=== Optuna 超參數搜尋 ({OPTUNA_N_TRIALS} trials) ===")

    def objective(trial):
        params = {
            "objective": "binary",
            "metric": "binary_logloss",
            "boosting_type": "gbdt",
            "verbose": -1,
            "random_state": RANDOM_SEED,
            "n_estimators": trial.suggest_int("n_estimators", 100, 1000),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
            "max_depth": trial.suggest_int("max_depth", 3, 10),
            "num_leaves": trial.suggest_int("num_leaves", 15, 200),
            "min_child_samples": trial.suggest_int("min_child_samples", 5, 100),
            "feature_fraction": trial.suggest_float("feature_fraction", 0.5, 1.0),
            "bagging_fraction": trial.suggest_float("bagging_fraction", 0.5, 1.0),
            "bagging_freq": trial.suggest_int("bagging_freq", 1, 10),
            "reg_alpha": trial.suggest_float("reg_alpha", 1e-8, 10.0, log=True),
            "reg_lambda": trial.suggest_float("reg_lambda", 1e-8, 10.0, log=True),
        }

        tscv = TimeSeriesSplit(n_splits=OPTUNA_CV_SPLITS)
        scores = []
        for train_idx, val_idx in tscv.split(X_train):
            X_t, X_v = X_train.iloc[train_idx], X_train.iloc[val_idx]
            y_t, y_v = y_train.iloc[train_idx], y_train.iloc[val_idx]

            model = lgb.LGBMClassifier(**params)
            model.fit(
                X_t, y_t,
                eval_set=[(X_v, y_v)],
                callbacks=[lgb.early_stopping(50, verbose=False)],
            )
            score = model.score(X_v, y_v)
            scores.append(score)

        return np.mean(scores)

    optuna.logging.set_verbosity(optuna.logging.WARNING)
    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=OPTUNA_N_TRIALS, show_progress_bar=True)

    print(f"\n  最佳準確率: {study.best_value:.4f}")
    print(f"  最佳參數:")
    for k, v in study.best_params.items():
        print(f"    {k}: {v}")

    # === 3. 用最佳參數訓練最終模型 ===
    print("\n=== 訓練最終模型 ===")
    best_params = {
        "objective": "binary",
        "metric": "binary_logloss",
        "boosting_type": "gbdt",
        "verbose": -1,
        "random_state": RANDOM_SEED,
        **study.best_params,
    }

    final_model = lgb.LGBMClassifier(**best_params)
    final_model.fit(X_train, y_train)

    # === 4. 評估 ===
    y_pred = final_model.predict(X_test)
    y_prob = final_model.predict_proba(X_test)[:, 1]

    results = evaluate_classifier(y_test.values, y_pred, y_prob)
    print_evaluation(results)

    # === 5. 回測 ===
    bt_results = backtest_strategy(test_df, y_pred, transaction_cost=0.001)
    print_backtest(bt_results)

    # === 6. 視覺化 ===
    plot_feature_importance(
        feature_names,
        final_model.feature_importances_,
        top_n=20,
        title="LightGBM 特徵重要性 (Top 20)",
        save_name="ch05_lgbm_feature_importance.png",
    )

    plot_confusion_matrix(
        results["confusion_matrix"],
        title="LightGBM 混淆矩陣",
        save_name="ch05_lgbm_confusion_matrix.png",
    )

    plot_equity_curve(
        bt_results["equity_curve"],
        title="LightGBM 策略 vs 買入持有",
        save_name="ch05_lgbm_equity_curve.png",
    )

    # === 7. 儲存模型 ===
    model_path = MODEL_DIR / "lightgbm_model.joblib"
    joblib.dump(final_model, model_path)
    print(f"\n  模型已儲存至 {model_path}")


if __name__ == "__main__":
    main()

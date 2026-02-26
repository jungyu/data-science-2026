"""
Ch05-03: CatBoost 漲跌預測。

學習重點：
- CatBoost 的 Symmetric Tree 與 Ordered Boosting
- 原生類別特徵支援（本範例為全數值特徵）
- 內建過擬合偵測
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import DATA_DIR, MODEL_DIR, OUTPUT_DIR, RANDOM_SEED, TRAIN_TEST_SPLIT_DATE
from src.data_loader import download_stock_data, train_test_split_by_date
from src.evaluator import backtest_strategy, evaluate_classifier, print_backtest, print_evaluation
from src.feature_engineer import build_feature_matrix
from src.plot_utils import plot_confusion_matrix, plot_equity_curve, plot_feature_importance

import joblib
import numpy as np
import optuna
import pandas as pd
from catboost import CatBoostClassifier
from sklearn.model_selection import TimeSeriesSplit


def get_feature_target(df, exclude_cols=None):
    exclude = set(exclude_cols or []) | {"Target", "Open", "High", "Low", "Close", "Volume"}
    feature_cols = [c for c in df.columns if c not in exclude]
    return df[feature_cols], df["Target"]


def main() -> None:
    print("=== CatBoost 股價漲跌預測 ===\n")

    cache_path = DATA_DIR / "feature_matrix_full.parquet"
    if cache_path.exists():
        feature_df = pd.read_parquet(cache_path)
        print(f"[快取] 載入特徵矩陣 ({len(feature_df)} 筆)")
    else:
        df = download_stock_data(ticker="AAPL", start="2018-01-01")
        feature_df = build_feature_matrix(df, target_type="direction")

    train_df, test_df = train_test_split_by_date(feature_df, TRAIN_TEST_SPLIT_DATE)
    X_train, y_train = get_feature_target(train_df)
    X_test, y_test = get_feature_target(test_df)
    feature_names = list(X_train.columns)

    # === Optuna 超參數優化 ===
    print("=== Optuna 超參數搜尋 (30 trials) ===")

    def objective(trial):
        params = {
            "loss_function": "Logloss",
            "eval_metric": "AUC",
            "random_seed": RANDOM_SEED,
            "verbose": 0,
            "iterations": trial.suggest_int("iterations", 100, 800),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
            "depth": trial.suggest_int("depth", 3, 10),
            "l2_leaf_reg": trial.suggest_float("l2_leaf_reg", 1e-3, 10.0, log=True),
            "bagging_temperature": trial.suggest_float("bagging_temperature", 0.0, 1.0),
            "random_strength": trial.suggest_float("random_strength", 1e-3, 10.0, log=True),
            "border_count": trial.suggest_int("border_count", 32, 255),
        }

        tscv = TimeSeriesSplit(n_splits=5)
        scores = []
        for train_idx, val_idx in tscv.split(X_train):
            X_t, X_v = X_train.iloc[train_idx], X_train.iloc[val_idx]
            y_t, y_v = y_train.iloc[train_idx], y_train.iloc[val_idx]

            model = CatBoostClassifier(**params)
            model.fit(X_t, y_t, eval_set=(X_v, y_v), early_stopping_rounds=50)
            scores.append(model.score(X_v, y_v))

        return np.mean(scores)

    optuna.logging.set_verbosity(optuna.logging.WARNING)
    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=30, show_progress_bar=True)

    print(f"\n  最佳準確率: {study.best_value:.4f}")

    # === 訓練最終模型 ===
    best_params = {
        "loss_function": "Logloss",
        "eval_metric": "AUC",
        "random_seed": RANDOM_SEED,
        "verbose": 0,
        **study.best_params,
    }

    final_model = CatBoostClassifier(**best_params)
    final_model.fit(X_train, y_train)

    # === 評估 ===
    y_pred = final_model.predict(X_test)
    y_prob = final_model.predict_proba(X_test)[:, 1]

    results = evaluate_classifier(y_test.values, y_pred, y_prob)
    print_evaluation(results)

    bt_results = backtest_strategy(test_df, y_pred, transaction_cost=0.001)
    print_backtest(bt_results)

    # === 視覺化 ===
    plot_feature_importance(
        feature_names, final_model.feature_importances_, top_n=20,
        title="CatBoost 特徵重要性 (Top 20)", save_name="ch05_catboost_feature_importance.png",
    )
    plot_confusion_matrix(
        results["confusion_matrix"],
        title="CatBoost 混淆矩陣", save_name="ch05_catboost_confusion_matrix.png",
    )
    plot_equity_curve(
        bt_results["equity_curve"],
        title="CatBoost 策略 vs 買入持有", save_name="ch05_catboost_equity_curve.png",
    )

    # === 儲存 ===
    joblib.dump(final_model, MODEL_DIR / "catboost_model.joblib")
    print(f"\n  模型已儲存")


if __name__ == "__main__":
    main()

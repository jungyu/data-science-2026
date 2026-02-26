"""
Ch07-03: MLflow 實驗追蹤。

學習重點：
- 為什麼需要實驗追蹤
- MLflow 的核心概念：Experiment, Run, Parameter, Metric, Artifact
- 自動記錄模型訓練的完整資訊
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import DATA_DIR, OUTPUT_DIR, RANDOM_SEED, TRAIN_TEST_SPLIT_DATE
from src.data_loader import download_stock_data, train_test_split_by_date
from src.evaluator import backtest_strategy, evaluate_classifier
from src.feature_engineer import build_feature_matrix

import mlflow
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.metrics import accuracy_score, roc_auc_score


def get_feature_target(df):
    exclude = {"Target", "Open", "High", "Low", "Close", "Volume"}
    feature_cols = [c for c in df.columns if c not in exclude]
    return df[feature_cols], df["Target"]


def run_experiment(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    test_df: pd.DataFrame,
    params: dict,
    experiment_name: str = "forecasting",
) -> None:
    """執行一次實驗並記錄至 MLflow。"""
    mlflow.set_experiment(experiment_name)

    with mlflow.start_run():
        # 記錄參數
        mlflow.log_params(params)
        mlflow.log_param("train_size", len(X_train))
        mlflow.log_param("test_size", len(X_test))
        mlflow.log_param("n_features", X_train.shape[1])

        # 訓練
        model = LGBMClassifier(**params, verbose=-1)
        model.fit(X_train, y_train)

        # 預測
        y_pred = model.predict(X_test)
        y_prob = model.predict_proba(X_test)[:, 1]

        # 評估指標
        results = evaluate_classifier(y_test.values, y_pred, y_prob)
        mlflow.log_metric("accuracy", results["accuracy"])
        mlflow.log_metric("auc", results["auc"])
        mlflow.log_metric("precision_0", results["report"]["0"]["precision"])
        mlflow.log_metric("precision_1", results["report"]["1"]["precision"])
        mlflow.log_metric("recall_0", results["report"]["0"]["recall"])
        mlflow.log_metric("recall_1", results["report"]["1"]["recall"])

        # 回測指標
        bt = backtest_strategy(test_df, y_pred, transaction_cost=0.001)
        mlflow.log_metric("strategy_return", bt["strategy_return"])
        mlflow.log_metric("sharpe_ratio", bt["sharpe_ratio"])
        mlflow.log_metric("max_drawdown", bt["max_drawdown"])
        mlflow.log_metric("win_rate", bt["win_rate"])

        print(f"  Acc={results['accuracy']:.4f} | AUC={results['auc']:.4f} | Sharpe={bt['sharpe_ratio']:.3f}")


def main() -> None:
    print("=== MLflow 實驗追蹤 ===\n")

    # 設定本地 MLflow 追蹤
    tracking_uri = f"sqlite:///{Path(__file__).resolve().parent.parent / 'mlflow.db'}"
    mlflow.set_tracking_uri(tracking_uri)
    print(f"  追蹤 URI: {tracking_uri}")

    # 準備資料
    cache_path = DATA_DIR / "feature_matrix_full.parquet"
    if cache_path.exists():
        feature_df = pd.read_parquet(cache_path)
    else:
        df = download_stock_data(ticker="AAPL", start="2018-01-01")
        feature_df = build_feature_matrix(df, target_type="direction")

    train_df, test_df = train_test_split_by_date(feature_df, TRAIN_TEST_SPLIT_DATE)
    X_train, y_train = get_feature_target(train_df)
    X_test, y_test = get_feature_target(test_df)

    # === 系統性實驗：不同超參數組合 ===
    experiments = [
        {"n_estimators": 100, "learning_rate": 0.1, "max_depth": 3, "random_state": RANDOM_SEED},
        {"n_estimators": 200, "learning_rate": 0.05, "max_depth": 5, "random_state": RANDOM_SEED},
        {"n_estimators": 300, "learning_rate": 0.05, "max_depth": 6, "random_state": RANDOM_SEED},
        {"n_estimators": 500, "learning_rate": 0.01, "max_depth": 7, "random_state": RANDOM_SEED},
        {"n_estimators": 300, "learning_rate": 0.05, "max_depth": 6, "num_leaves": 50, "random_state": RANDOM_SEED},
        {"n_estimators": 300, "learning_rate": 0.05, "max_depth": 6, "feature_fraction": 0.7, "random_state": RANDOM_SEED},
    ]

    print(f"\n  執行 {len(experiments)} 組實驗...\n")
    for i, params in enumerate(experiments):
        print(f"  實驗 {i+1}/{len(experiments)}: ", end="")
        run_experiment(X_train, y_train, X_test, y_test, test_df, params)

    print(f"\n=== 完成 ===")
    print(f"  實驗結果已記錄至 MLflow")
    print(f"  啟動 MLflow UI 查看:")
    print(f"    mlflow ui --backend-store-uri {tracking_uri}")
    print(f"  然後在瀏覽器開啟 http://localhost:5000")


if __name__ == "__main__":
    main()

"""
Ch05-04: 三大梯度提升框架統一比較。

學習重點：
- 公平比較不同模型的方法論
- Walk-forward 交叉驗證避免 overfitting
- 統計顯著性檢定模型差異
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import DATA_DIR, OUTPUT_DIR, RANDOM_SEED, TRAIN_TEST_SPLIT_DATE
from src.data_loader import download_stock_data, train_test_split_by_date
from src.evaluator import evaluate_classifier, walk_forward_split
from src.feature_engineer import build_feature_matrix
from src.plot_utils import apply_style

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from catboost import CatBoostClassifier
from lightgbm import LGBMClassifier
from sklearn.metrics import accuracy_score, roc_auc_score
from xgboost import XGBClassifier


def get_feature_target(df, exclude_cols=None):
    exclude = set(exclude_cols or []) | {"Target", "Open", "High", "Low", "Close", "Volume"}
    feature_cols = [c for c in df.columns if c not in exclude]
    return df[feature_cols], df["Target"]


def main() -> None:
    print("=== 三大梯度提升框架比較 ===\n")

    cache_path = DATA_DIR / "feature_matrix_full.parquet"
    if cache_path.exists():
        feature_df = pd.read_parquet(cache_path)
    else:
        df = download_stock_data(ticker="AAPL", start="2018-01-01")
        feature_df = build_feature_matrix(df, target_type="direction")

    train_df, test_df = train_test_split_by_date(feature_df, TRAIN_TEST_SPLIT_DATE)
    X_train, y_train = get_feature_target(train_df)
    X_test, y_test = get_feature_target(test_df)

    # === 模型定義（使用預設/合理參數） ===
    models = {
        "LightGBM": LGBMClassifier(
            n_estimators=300, learning_rate=0.05, max_depth=6, num_leaves=31,
            random_state=RANDOM_SEED, verbose=-1,
        ),
        "XGBoost": XGBClassifier(
            n_estimators=300, learning_rate=0.05, max_depth=6,
            random_state=RANDOM_SEED, verbosity=0,
        ),
        "CatBoost": CatBoostClassifier(
            iterations=300, learning_rate=0.05, depth=6,
            random_seed=RANDOM_SEED, verbose=0,
        ),
    }

    # === 1. 測試集評估 ===
    print("=== 測試集評估 ===")
    print(f"{'模型':<12} {'Accuracy':>10} {'AUC':>10} {'訓練時間':>10}")
    print("-" * 45)

    test_results = {}
    for name, model in models.items():
        start_time = time.time()
        model.fit(X_train, y_train)
        train_time = time.time() - start_time

        y_pred = model.predict(X_test)
        y_prob = model.predict_proba(X_test)[:, 1]
        acc = accuracy_score(y_test, y_pred)
        auc = roc_auc_score(y_test, y_prob)

        test_results[name] = {
            "accuracy": acc, "auc": auc, "train_time": train_time,
            "y_pred": y_pred, "y_prob": y_prob,
        }
        print(f"{name:<12} {acc:>10.4f} {auc:>10.4f} {train_time:>9.1f}s")

    # === 2. Walk-forward 交叉驗證 ===
    print(f"\n=== Walk-forward 交叉驗證 (5 folds) ===")
    X_full = pd.concat([X_train, X_test])
    y_full = pd.concat([y_train, y_test])
    splits = walk_forward_split(len(X_full), n_splits=5, train_ratio=0.6)

    cv_results = {name: [] for name in models}

    for fold_idx, (train_idx, val_idx) in enumerate(splits):
        X_t, X_v = X_full.iloc[train_idx], X_full.iloc[val_idx]
        y_t, y_v = y_full.iloc[train_idx], y_full.iloc[val_idx]

        for name, model_class in [
            ("LightGBM", lambda: LGBMClassifier(n_estimators=300, learning_rate=0.05, max_depth=6, num_leaves=31, random_state=RANDOM_SEED, verbose=-1)),
            ("XGBoost", lambda: XGBClassifier(n_estimators=300, learning_rate=0.05, max_depth=6, random_state=RANDOM_SEED, verbosity=0)),
            ("CatBoost", lambda: CatBoostClassifier(iterations=300, learning_rate=0.05, depth=6, random_seed=RANDOM_SEED, verbose=0)),
        ]:
            model = model_class()
            model.fit(X_t, y_t)
            acc = model.score(X_v, y_v)
            cv_results[name].append(acc)

    print(f"\n{'模型':<12} {'平均':>8} {'標準差':>8} {'最低':>8} {'最高':>8}")
    print("-" * 48)
    for name, scores in cv_results.items():
        arr = np.array(scores)
        print(f"{name:<12} {arr.mean():>8.4f} {arr.std():>8.4f} {arr.min():>8.4f} {arr.max():>8.4f}")

    # === 3. 視覺化 ===
    apply_style()
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # CV 分佈箱型圖
    cv_df = pd.DataFrame(cv_results)
    cv_df.boxplot(ax=axes[0, 0])
    axes[0, 0].set_title("Walk-forward CV 準確率分佈")
    axes[0, 0].set_ylabel("Accuracy")

    # 測試集 Accuracy 比較
    names = list(test_results.keys())
    accs = [test_results[n]["accuracy"] for n in names]
    aucs = [test_results[n]["auc"] for n in names]

    x = np.arange(len(names))
    width = 0.35
    axes[0, 1].bar(x - width/2, accs, width, label="Accuracy")
    axes[0, 1].bar(x + width/2, aucs, width, label="AUC")
    axes[0, 1].set_xticks(x)
    axes[0, 1].set_xticklabels(names)
    axes[0, 1].set_title("測試集指標比較")
    axes[0, 1].legend()
    axes[0, 1].set_ylim(0.4, 0.7)

    # 訓練時間
    times = [test_results[n]["train_time"] for n in names]
    axes[1, 0].bar(names, times, color=["#2196F3", "#FF9800", "#4CAF50"])
    axes[1, 0].set_title("訓練時間 (秒)")
    axes[1, 0].set_ylabel("秒")

    # 預測一致性
    from itertools import combinations
    pairs = list(combinations(names, 2))
    agreement = []
    pair_labels = []
    for n1, n2 in pairs:
        agree = (test_results[n1]["y_pred"] == test_results[n2]["y_pred"]).mean()
        agreement.append(agree)
        pair_labels.append(f"{n1}\nvs\n{n2}")
    axes[1, 1].bar(pair_labels, agreement, color="#9C27B0")
    axes[1, 1].set_title("模型預測一致率")
    axes[1, 1].set_ylabel("一致率")
    axes[1, 1].set_ylim(0.5, 1.0)

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "ch05_model_comparison.png", dpi=150, bbox_inches="tight")
    plt.show()

    print("\n=== 結論 ===")
    print("  1. 三種模型的效能通常相近，差異不大")
    print("  2. LightGBM 訓練速度通常最快")
    print("  3. 模型間的預測一致率反映特徵的可預測性")
    print("  4. 可考慮 Ensemble（投票法）結合三者的預測")


if __name__ == "__main__":
    main()

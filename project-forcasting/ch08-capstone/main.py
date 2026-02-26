"""
Ch08: 端對端預測管線範例。

整合所有章節的技術，展示完整的預測工作流程。
學生可以以此為起點，擴展為自己的專案。
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import DATA_DIR, MODEL_DIR, OUTPUT_DIR, RANDOM_SEED, TRAIN_TEST_SPLIT_DATE
from src.data_loader import download_stock_data, train_test_split_by_date
from src.evaluator import (
    backtest_strategy,
    evaluate_classifier,
    print_backtest,
    print_evaluation,
    walk_forward_split,
)
from src.feature_engineer import build_feature_matrix
from src.plot_utils import apply_style, plot_equity_curve

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from catboost import CatBoostClassifier
from lightgbm import LGBMClassifier
from sklearn.metrics import accuracy_score, roc_auc_score
from xgboost import XGBClassifier


def get_feature_target(df):
    exclude = {"Target", "Open", "High", "Low", "Close", "Volume"}
    feature_cols = [c for c in df.columns if c not in exclude]
    return df[feature_cols], df["Target"]


def main() -> None:
    print("=" * 60)
    print("  端對端預測管線")
    print("=" * 60)

    # === Step 1: 資料準備 ===
    print("\n[Step 1] 資料準備與特徵工程")
    df = download_stock_data(ticker="AAPL", start="2018-01-01")
    feature_df = build_feature_matrix(df, target_type="direction")

    train_df, test_df = train_test_split_by_date(feature_df, TRAIN_TEST_SPLIT_DATE)
    X_train, y_train = get_feature_target(train_df)
    X_test, y_test = get_feature_target(test_df)

    print(f"  訓練集: {len(X_train)} | 測試集: {len(X_test)} | 特徵: {X_train.shape[1]}")

    # === Step 2: 多模型訓練 ===
    print("\n[Step 2] 訓練多個模型")
    models = {
        "LightGBM": LGBMClassifier(
            n_estimators=300, learning_rate=0.05, max_depth=6,
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

    predictions = {}
    probabilities = {}

    for name, model in models.items():
        model.fit(X_train, y_train)
        predictions[name] = model.predict(X_test)
        probabilities[name] = model.predict_proba(X_test)[:, 1]
        acc = accuracy_score(y_test, predictions[name])
        auc = roc_auc_score(y_test, probabilities[name])
        print(f"  {name}: Acc={acc:.4f}, AUC={auc:.4f}")

    # === Step 3: Ensemble（投票法） ===
    print("\n[Step 3] Ensemble — 多數投票")
    pred_matrix = np.column_stack(list(predictions.values()))
    ensemble_pred = (pred_matrix.mean(axis=1) > 0.5).astype(int)

    prob_matrix = np.column_stack(list(probabilities.values()))
    ensemble_prob = prob_matrix.mean(axis=1)

    ensemble_acc = accuracy_score(y_test, ensemble_pred)
    ensemble_auc = roc_auc_score(y_test, ensemble_prob)
    print(f"  Ensemble: Acc={ensemble_acc:.4f}, AUC={ensemble_auc:.4f}")

    # === Step 4: 評估 ===
    print("\n[Step 4] 詳細評估 — Ensemble 模型")
    results = evaluate_classifier(y_test.values, ensemble_pred, ensemble_prob)
    print_evaluation(results)

    # === Step 5: 回測 ===
    print("\n[Step 5] 回測分析")
    all_signals = {**predictions, "Ensemble": ensemble_pred}

    print(f"{'策略':<12} {'總報酬':>10} {'夏普':>8} {'最大回撤':>10} {'勝率':>8}")
    print("-" * 52)

    bt_results = {}
    for name, signals in all_signals.items():
        bt = backtest_strategy(test_df, signals, transaction_cost=0.001)
        bt_results[name] = bt
        print(f"{name:<12} {bt['strategy_return']:>+10.2%} {bt['sharpe_ratio']:>8.3f} {bt['max_drawdown']:>10.2%} {bt['win_rate']:>8.2%}")

    # === Step 6: Walk-forward 驗證 ===
    print("\n[Step 6] Walk-forward 驗證")
    X_full, y_full = get_feature_target(feature_df)
    wf_splits = walk_forward_split(len(X_full), n_splits=5, train_ratio=0.6)

    wf_scores = {name: [] for name in models}
    wf_scores["Ensemble"] = []

    for train_idx, val_idx in wf_splits:
        X_t, X_v = X_full.iloc[train_idx], X_full.iloc[val_idx]
        y_t, y_v = y_full.iloc[train_idx], y_full.iloc[val_idx]

        fold_preds = {}
        for name in models:
            if name == "LightGBM":
                m = LGBMClassifier(n_estimators=300, learning_rate=0.05, max_depth=6, random_state=RANDOM_SEED, verbose=-1)
            elif name == "XGBoost":
                m = XGBClassifier(n_estimators=300, learning_rate=0.05, max_depth=6, random_state=RANDOM_SEED, verbosity=0)
            else:
                m = CatBoostClassifier(iterations=300, learning_rate=0.05, depth=6, random_seed=RANDOM_SEED, verbose=0)
            m.fit(X_t, y_t)
            pred = m.predict(X_v)
            fold_preds[name] = pred
            wf_scores[name].append(accuracy_score(y_v, pred))

        ensemble = (np.column_stack(list(fold_preds.values())).mean(axis=1) > 0.5).astype(int)
        wf_scores["Ensemble"].append(accuracy_score(y_v, ensemble))

    print(f"\n{'模型':<12} {'平均':>8} {'標準差':>8}")
    print("-" * 30)
    for name, scores in wf_scores.items():
        arr = np.array(scores)
        print(f"{name:<12} {arr.mean():>8.4f} {arr.std():>8.4f}")

    # === Step 7: 視覺化 ===
    print("\n[Step 7] 產出圖表")
    apply_style()
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # 淨值曲線
    for name, bt in bt_results.items():
        eq = bt["equity_curve"]
        axes[0, 0].plot(eq.index, eq["Strategy_Equity"], label=name, linewidth=1.2)
    axes[0, 0].plot(eq.index, eq["BuyHold_Equity"], label="買入持有", linestyle="--", alpha=0.7)
    axes[0, 0].set_title("策略淨值比較")
    axes[0, 0].legend(fontsize=8)
    axes[0, 0].set_ylabel("淨值")

    # Walk-forward 結果
    wf_df = pd.DataFrame(wf_scores)
    wf_df.boxplot(ax=axes[0, 1])
    axes[0, 1].set_title("Walk-forward CV 準確率")
    axes[0, 1].set_ylabel("Accuracy")

    # 模型一致性熱力圖
    import seaborn as sns
    agree_matrix = np.zeros((len(all_signals), len(all_signals)))
    names = list(all_signals.keys())
    for i, n1 in enumerate(names):
        for j, n2 in enumerate(names):
            agree_matrix[i, j] = (all_signals[n1] == all_signals[n2]).mean()
    sns.heatmap(agree_matrix, annot=True, fmt=".2f", xticklabels=names, yticklabels=names,
                ax=axes[1, 0], cmap="YlOrRd", vmin=0.5, vmax=1.0)
    axes[1, 0].set_title("模型預測一致率")

    # 績效摘要
    metrics = ["strategy_return", "sharpe_ratio", "max_drawdown"]
    metric_labels = ["總報酬", "夏普比率", "最大回撤"]
    x = np.arange(len(names))
    width = 0.25
    for i, (metric, label) in enumerate(zip(metrics, metric_labels)):
        vals = [bt_results[n][metric] for n in names]
        axes[1, 1].bar(x + i * width, vals, width, label=label)
    axes[1, 1].set_xticks(x + width)
    axes[1, 1].set_xticklabels(names, rotation=45)
    axes[1, 1].set_title("績效指標比較")
    axes[1, 1].legend()

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "ch08_capstone.png", dpi=150, bbox_inches="tight")
    plt.show()

    print("\n" + "=" * 60)
    print("  管線完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()

"""
Ch07-01: Walk-forward 驗證。

學習重點：
- 擴展窗口 (Expanding Window) vs 滑動窗口 (Sliding Window)
- 為什麼 K-fold 不適合時間序列
- 各 fold 的績效穩定性分析
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import DATA_DIR, OUTPUT_DIR, RANDOM_SEED
from src.data_loader import download_stock_data
from src.evaluator import walk_forward_split
from src.feature_engineer import build_feature_matrix
from src.plot_utils import apply_style

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.metrics import accuracy_score, roc_auc_score
from sklearn.model_selection import KFold, TimeSeriesSplit


def get_feature_target(df):
    exclude = {"Target", "Open", "High", "Low", "Close", "Volume"}
    feature_cols = [c for c in df.columns if c not in exclude]
    return df[feature_cols], df["Target"]


def main() -> None:
    print("=== Walk-forward 驗證 ===\n")

    cache_path = DATA_DIR / "feature_matrix_full.parquet"
    if cache_path.exists():
        feature_df = pd.read_parquet(cache_path)
    else:
        df = download_stock_data(ticker="AAPL", start="2018-01-01")
        feature_df = build_feature_matrix(df, target_type="direction")

    X, y = get_feature_target(feature_df)
    dates = feature_df.index

    model_fn = lambda: LGBMClassifier(
        n_estimators=300, learning_rate=0.05, max_depth=6,
        random_state=RANDOM_SEED, verbose=-1,
    )

    # === 1. 錯誤做法：K-Fold ===
    print("--- 錯誤: 隨機 K-Fold (會造成資料洩漏) ---")
    kf = KFold(n_splits=5, shuffle=True, random_state=RANDOM_SEED)
    kfold_scores = []
    for fold, (train_idx, val_idx) in enumerate(kf.split(X)):
        model = model_fn()
        model.fit(X.iloc[train_idx], y.iloc[train_idx])
        acc = model.score(X.iloc[val_idx], y.iloc[val_idx])
        kfold_scores.append(acc)
        # 檢查是否有「未來資料」洩漏
        min_val_date = dates[val_idx].min()
        max_train_date = dates[train_idx].max()
        leakage = max_train_date > min_val_date
        print(f"  Fold {fold+1}: Acc={acc:.4f} | 洩漏={leakage}")

    # === 2. 正確做法：TimeSeriesSplit ===
    print("\n--- 正確: TimeSeriesSplit (擴展窗口) ---")
    tscv = TimeSeriesSplit(n_splits=5)
    ts_scores = []
    ts_details = []
    for fold, (train_idx, val_idx) in enumerate(tscv.split(X)):
        model = model_fn()
        model.fit(X.iloc[train_idx], y.iloc[train_idx])
        acc = model.score(X.iloc[val_idx], y.iloc[val_idx])
        ts_scores.append(acc)
        detail = {
            "fold": fold + 1,
            "train_size": len(train_idx),
            "val_size": len(val_idx),
            "train_end": dates[train_idx[-1]].date(),
            "val_start": dates[val_idx[0]].date(),
            "val_end": dates[val_idx[-1]].date(),
            "accuracy": acc,
        }
        ts_details.append(detail)
        print(f"  Fold {fold+1}: Acc={acc:.4f} | 訓練{len(train_idx)} | 驗證{len(val_idx)} | {detail['val_start']}~{detail['val_end']}")

    # === 3. 自訂 Walk-forward（固定比例） ===
    print("\n--- 自訂: Walk-forward (70/30 擴展窗口) ---")
    wf_splits = walk_forward_split(len(X), n_splits=5, train_ratio=0.6)
    wf_scores = []
    for fold, (train_idx, val_idx) in enumerate(wf_splits):
        model = model_fn()
        model.fit(X.iloc[train_idx], y.iloc[train_idx])
        acc = model.score(X.iloc[val_idx], y.iloc[val_idx])
        wf_scores.append(acc)
        print(f"  Fold {fold+1}: Acc={acc:.4f} | 訓練{len(train_idx)} | 驗證{len(val_idx)}")

    # === 4. 比較 ===
    print(f"\n=== 比較摘要 ===")
    print(f"{'方法':<25} {'平均':>8} {'標準差':>8}")
    print("-" * 43)
    print(f"{'K-Fold (有洩漏!)':<25} {np.mean(kfold_scores):>8.4f} {np.std(kfold_scores):>8.4f}")
    print(f"{'TimeSeriesSplit':<25} {np.mean(ts_scores):>8.4f} {np.std(ts_scores):>8.4f}")
    print(f"{'Walk-forward':<25} {np.mean(wf_scores):>8.4f} {np.std(wf_scores):>8.4f}")

    # === 5. 視覺化 ===
    apply_style()
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))

    # 方法比較
    methods = ["K-Fold\n(洩漏)", "TimeSeries\nSplit", "Walk-\nforward"]
    means = [np.mean(kfold_scores), np.mean(ts_scores), np.mean(wf_scores)]
    stds = [np.std(kfold_scores), np.std(ts_scores), np.std(wf_scores)]
    colors = ["#F44336", "#4CAF50", "#2196F3"]
    axes[0].bar(methods, means, yerr=stds, capsize=5, color=colors, alpha=0.8)
    axes[0].set_title("三種驗證方法比較")
    axes[0].set_ylabel("準確率")
    axes[0].set_ylim(0.45, 0.65)

    # 各 fold 趨勢
    axes[1].plot(range(1, 6), ts_scores, "o-", label="TimeSeriesSplit")
    axes[1].plot(range(1, len(wf_scores)+1), wf_scores, "s-", label="Walk-forward")
    axes[1].set_title("各 Fold 準確率變化")
    axes[1].set_xlabel("Fold")
    axes[1].set_ylabel("準確率")
    axes[1].legend()

    # TimeSeriesSplit 時間範圍
    for i, detail in enumerate(ts_details):
        axes[2].barh(i, detail["train_size"], left=0, color="#2196F3", alpha=0.6, label="訓練" if i == 0 else "")
        axes[2].barh(i, detail["val_size"], left=detail["train_size"], color="#FF9800", alpha=0.6, label="驗證" if i == 0 else "")
    axes[2].set_yticks(range(5))
    axes[2].set_yticklabels([f"Fold {i+1}" for i in range(5)])
    axes[2].set_title("TimeSeriesSplit 分割示意")
    axes[2].set_xlabel("樣本數")
    axes[2].legend()

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "ch07_walk_forward.png", dpi=150, bbox_inches="tight")
    plt.show()

    print("\n=== 重點 ===")
    print("  K-Fold 的準確率通常偏高（虛假樂觀），因為使用了未來資料！")
    print("  Walk-forward 更貼近實際交易的預測情境。")


if __name__ == "__main__":
    main()

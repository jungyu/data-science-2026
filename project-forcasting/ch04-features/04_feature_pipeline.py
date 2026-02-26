"""
Ch04-04: 完整特徵工程管線。

學習重點：
- 使用 src/feature_engineer.py 一站式建構特徵
- 特徵篩選策略
- 檢查資料洩漏
- 輸出可供 ch05 直接使用的特徵矩陣
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import DATA_DIR, OUTPUT_DIR, TRAIN_TEST_SPLIT_DATE
from src.data_loader import download_stock_data, train_test_split_by_date
from src.feature_engineer import build_feature_matrix
from src.plot_utils import apply_style

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.feature_selection import mutual_info_classif


def main() -> None:
    # === 1. 下載與特徵工程 ===
    df = download_stock_data(ticker="AAPL", start="2018-01-01")
    feature_df = build_feature_matrix(df, target_type="direction")

    # === 2. 檢查資料洩漏 ===
    print("\n=== 資料洩漏檢查 ===")
    ohlcv_cols = ["Open", "High", "Low", "Close", "Volume"]
    feature_cols = [c for c in feature_df.columns if c not in ohlcv_cols + ["Target"]]
    print(f"  特徵欄位數: {len(feature_cols)}")

    # 確保沒有未來資訊：最後一列的 Target 應該是 NaN（已被 dropna 移除）
    print(f"  最後一筆日期: {feature_df.index[-1].date()}")
    print(f"  Target 分佈: {feature_df['Target'].value_counts().to_dict()}")
    print(f"  Target 比例 (漲): {feature_df['Target'].mean():.4f}")

    # === 3. 特徵篩選 ===
    print("\n=== 互資訊特徵篩選 ===")
    X = feature_df[feature_cols].values
    y = feature_df["Target"].values

    mi_scores = mutual_info_classif(X, y, random_state=42, n_neighbors=5)
    mi_df = pd.DataFrame({"feature": feature_cols, "mi_score": mi_scores})
    mi_df = mi_df.sort_values("mi_score", ascending=False)

    # 選擇 MI > 0 的特徵
    selected = mi_df[mi_df["mi_score"] > 0.001]
    print(f"  MI > 0.001 的特徵數: {len(selected)} / {len(feature_cols)}")
    print(f"\n  Top 20 特徵:")
    print(selected.head(20).to_string(index=False))

    # === 4. 分割並儲存 ===
    train_df, test_df = train_test_split_by_date(feature_df, TRAIN_TEST_SPLIT_DATE)

    # 儲存完整特徵矩陣供後續章節使用
    feature_df.to_parquet(DATA_DIR / "feature_matrix_full.parquet")
    train_df.to_parquet(DATA_DIR / "feature_matrix_train.parquet")
    test_df.to_parquet(DATA_DIR / "feature_matrix_test.parquet")
    print(f"\n  已儲存特徵矩陣至 data/ 目錄")
    print(f"  - feature_matrix_full.parquet ({len(feature_df)} 筆)")
    print(f"  - feature_matrix_train.parquet ({len(train_df)} 筆)")
    print(f"  - feature_matrix_test.parquet ({len(test_df)} 筆)")

    # === 5. 視覺化 ===
    apply_style()
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))

    # 特徵重要性
    top20 = mi_df.head(20)
    axes[0].barh(range(len(top20)), top20["mi_score"].values)
    axes[0].set_yticks(range(len(top20)))
    axes[0].set_yticklabels(top20["feature"].values)
    axes[0].set_title("互資訊 Top 20 特徵")
    axes[0].set_xlabel("MI Score")
    axes[0].invert_yaxis()

    # 高相關特徵對
    corr = feature_df[feature_cols].corr()
    mask = np.triu(np.ones_like(corr, dtype=bool))
    high_corr = []
    for i in range(len(corr)):
        for j in range(i + 1, len(corr)):
            if abs(corr.iloc[i, j]) > 0.9:
                high_corr.append((corr.index[i], corr.columns[j], corr.iloc[i, j]))

    print(f"\n=== 高度相關特徵對 (|r| > 0.9) ===")
    print(f"  共 {len(high_corr)} 對")
    for f1, f2, r in sorted(high_corr, key=lambda x: abs(x[2]), reverse=True)[:10]:
        print(f"    {f1} <-> {f2}: {r:.3f}")

    axes[1].hist([abs(r) for _, _, r in high_corr], bins=20, edgecolor="white")
    axes[1].set_title(f"高度相關特徵對分佈 (共 {len(high_corr)} 對)")
    axes[1].set_xlabel("|相關係數|")
    axes[1].set_ylabel("頻次")

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "ch04_feature_pipeline.png", dpi=150, bbox_inches="tight")
    plt.show()

    print("\n=== 下一步 ===")
    print("  特徵矩陣已準備完成，可直接用於 ch05 的樹模型訓練")


if __name__ == "__main__":
    main()

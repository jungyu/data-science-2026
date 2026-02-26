"""評估模組單元測試。"""

from __future__ import annotations

import numpy as np
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.evaluator import evaluate_classifier, walk_forward_split


class TestEvaluateClassifier:
    def test_perfect_predictions(self) -> None:
        y_true = np.array([0, 1, 0, 1, 1])
        y_pred = np.array([0, 1, 0, 1, 1])
        results = evaluate_classifier(y_true, y_pred)
        assert results["accuracy"] == 1.0

    def test_with_probabilities(self) -> None:
        y_true = np.array([0, 1, 0, 1, 1])
        y_pred = np.array([0, 1, 0, 1, 1])
        y_prob = np.array([0.1, 0.9, 0.2, 0.8, 0.7])
        results = evaluate_classifier(y_true, y_pred, y_prob)
        assert "auc" in results
        assert 0 <= results["auc"] <= 1

    def test_random_predictions(self) -> None:
        np.random.seed(42)
        y_true = np.random.randint(0, 2, 100)
        y_pred = np.random.randint(0, 2, 100)
        results = evaluate_classifier(y_true, y_pred)
        assert 0 <= results["accuracy"] <= 1


class TestWalkForwardSplit:
    def test_basic_split(self) -> None:
        splits = walk_forward_split(100, n_splits=3, train_ratio=0.5)
        assert len(splits) == 3
        for train_idx, test_idx in splits:
            # 訓練集應在測試集之前
            assert train_idx.max() < test_idx.min()

    def test_no_overlap(self) -> None:
        splits = walk_forward_split(200, n_splits=5, train_ratio=0.6)
        for train_idx, test_idx in splits:
            assert len(set(train_idx) & set(test_idx)) == 0

    def test_expanding_window(self) -> None:
        splits = walk_forward_split(200, n_splits=4, train_ratio=0.5)
        # 每個 fold 的訓練集應該越來越大
        train_sizes = [len(s[0]) for s in splits]
        assert train_sizes == sorted(train_sizes)

    def test_min_train_size(self) -> None:
        splits = walk_forward_split(100, n_splits=3, min_train_size=50)
        assert len(splits[0][0]) >= 50

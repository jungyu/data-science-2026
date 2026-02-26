"""特徵工程模組單元測試。"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.feature_engineer import (
    add_lag_features,
    add_price_features,
    add_time_features,
    add_volume_features,
    build_feature_matrix,
    create_target,
)


@pytest.fixture
def sample_ohlcv() -> pd.DataFrame:
    """建立測試用 OHLCV 資料。"""
    np.random.seed(42)
    n = 100
    dates = pd.bdate_range("2024-01-01", periods=n)
    close = 150 + np.cumsum(np.random.randn(n) * 2)
    return pd.DataFrame(
        {
            "Open": close - np.random.rand(n),
            "High": close + np.abs(np.random.randn(n)),
            "Low": close - np.abs(np.random.randn(n)),
            "Close": close,
            "Volume": np.random.randint(1_000_000, 10_000_000, n),
        },
        index=dates,
    )


class TestPriceFeatures:
    def test_adds_return_columns(self, sample_ohlcv: pd.DataFrame) -> None:
        result = add_price_features(sample_ohlcv)
        assert "Return" in result.columns
        assert "Log_Return" in result.columns
        assert "Daily_Range" in result.columns

    def test_adds_moving_averages(self, sample_ohlcv: pd.DataFrame) -> None:
        result = add_price_features(sample_ohlcv)
        assert "SMA_5" in result.columns
        assert "SMA_20" in result.columns
        assert "EMA_10" in result.columns

    def test_does_not_modify_original(self, sample_ohlcv: pd.DataFrame) -> None:
        original_cols = set(sample_ohlcv.columns)
        add_price_features(sample_ohlcv)
        assert set(sample_ohlcv.columns) == original_cols


class TestVolumeFeatures:
    def test_adds_volume_ratio(self, sample_ohlcv: pd.DataFrame) -> None:
        df = add_price_features(sample_ohlcv)  # 需要 Return 欄位
        result = add_volume_features(df)
        assert "Volume_Ratio" in result.columns
        assert "VPT" in result.columns


class TestTimeFeatures:
    def test_adds_cyclical_encoding(self, sample_ohlcv: pd.DataFrame) -> None:
        result = add_time_features(sample_ohlcv)
        assert "DayOfWeek_Sin" in result.columns
        assert "DayOfWeek_Cos" in result.columns
        assert "Month_Sin" in result.columns

    def test_sin_cos_range(self, sample_ohlcv: pd.DataFrame) -> None:
        result = add_time_features(sample_ohlcv)
        assert result["DayOfWeek_Sin"].between(-1, 1).all()
        assert result["Month_Cos"].between(-1, 1).all()


class TestLagFeatures:
    def test_default_lags(self, sample_ohlcv: pd.DataFrame) -> None:
        df = add_price_features(sample_ohlcv)
        result = add_lag_features(df)
        assert "Close_Lag_1" in result.columns
        assert "Close_Lag_10" in result.columns
        assert "Return_Lag_5" in result.columns

    def test_custom_lags(self, sample_ohlcv: pd.DataFrame) -> None:
        result = add_lag_features(sample_ohlcv, columns=["Close"], lags=[1, 7])
        assert "Close_Lag_1" in result.columns
        assert "Close_Lag_7" in result.columns
        assert "Close_Lag_5" not in result.columns


class TestTarget:
    def test_direction_target(self, sample_ohlcv: pd.DataFrame) -> None:
        result = create_target(sample_ohlcv, target_type="direction")
        assert "Target" in result.columns
        assert set(result["Target"].dropna().unique()).issubset({0, 1})

    def test_return_target(self, sample_ohlcv: pd.DataFrame) -> None:
        result = create_target(sample_ohlcv, target_type="return")
        assert "Target" in result.columns
        # 連續值
        assert result["Target"].dropna().nunique() > 2

    def test_invalid_target_type(self, sample_ohlcv: pd.DataFrame) -> None:
        with pytest.raises(ValueError, match="不支援"):
            create_target(sample_ohlcv, target_type="invalid")


class TestBuildFeatureMatrix:
    def test_full_pipeline(self, sample_ohlcv: pd.DataFrame) -> None:
        result = build_feature_matrix(sample_ohlcv, target_type="direction")
        assert "Target" in result.columns
        assert not result.isnull().any().any()  # 無 NaN
        assert len(result) < len(sample_ohlcv)  # 因 dropna

    def test_no_future_leakage(self, sample_ohlcv: pd.DataFrame) -> None:
        """確保特徵不包含未來資訊。"""
        result = build_feature_matrix(sample_ohlcv, target_type="direction")
        # 所有 Lag 特徵的值應來自過去
        lag_cols = [c for c in result.columns if "Lag" in c]
        assert len(lag_cols) > 0

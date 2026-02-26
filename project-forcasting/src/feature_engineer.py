"""
特徵工程模組。

將原始 OHLCV 資料轉換為機器學習可用的特徵矩陣。
包含：價格特徵、技術指標、時間特徵、滯後特徵。
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pandas_ta as ta

from src.config import TECHNICAL_INDICATORS


def add_price_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    新增價格衍生特徵。

    包含：日報酬率、日振幅、開收比、對數報酬率、移動平均線。
    """
    df = df.copy()

    # 報酬率
    df["Return"] = df["Close"].pct_change()
    df["Log_Return"] = np.log(df["Close"] / df["Close"].shift(1))

    # 價格比率
    df["Daily_Range"] = (df["High"] - df["Low"]) / df["Close"]
    df["Open_Close_Ratio"] = (df["Close"] - df["Open"]) / df["Open"]
    df["High_Low_Ratio"] = df["High"] / df["Low"]

    # 移動平均
    for period in TECHNICAL_INDICATORS["sma_periods"]:
        df[f"SMA_{period}"] = df["Close"].rolling(period).mean()
        df[f"Close_SMA_{period}_Ratio"] = df["Close"] / df[f"SMA_{period}"]

    for period in TECHNICAL_INDICATORS["ema_periods"]:
        df[f"EMA_{period}"] = df["Close"].ewm(span=period, adjust=False).mean()

    return df


def add_technical_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    新增技術指標特徵（使用 pandas_ta）。

    包含：RSI、MACD、布林通道、KD 指標、威廉指標。
    """
    df = df.copy()
    cfg = TECHNICAL_INDICATORS

    # RSI
    df[f"RSI_{cfg['rsi_period']}"] = ta.rsi(df["Close"], length=cfg["rsi_period"])

    # MACD
    macd = ta.macd(df["Close"], fast=cfg["macd_fast"], slow=cfg["macd_slow"], signal=cfg["macd_signal"])
    if macd is not None:
        df = pd.concat([df, macd], axis=1)

    # 布林通道 (Bollinger Bands)
    bb = ta.bbands(df["Close"], length=cfg["bb_period"], std=cfg["bb_std"])
    if bb is not None:
        df = pd.concat([df, bb], axis=1)
        # 價格在布林通道中的位置
        bbl_col = [c for c in bb.columns if "BBL" in c]
        bbu_col = [c for c in bb.columns if "BBU" in c]
        if bbl_col and bbu_col:
            df["BB_Position"] = (df["Close"] - df[bbl_col[0]]) / (
                df[bbu_col[0]] - df[bbl_col[0]]
            )

    # KD 隨機指標 (Stochastic Oscillator)
    stoch = ta.stoch(df["High"], df["Low"], df["Close"], k=cfg["stoch_k"], d=cfg["stoch_d"])
    if stoch is not None:
        df = pd.concat([df, stoch], axis=1)

    # 威廉指標 (Williams %R)
    df[f"WILLR_{cfg['williams_r_period']}"] = ta.willr(
        df["High"], df["Low"], df["Close"], length=cfg["williams_r_period"]
    )

    return df


def add_volume_features(df: pd.DataFrame) -> pd.DataFrame:
    """新增成交量衍生特徵。"""
    df = df.copy()

    df["Volume_SMA_5"] = df["Volume"].rolling(5).mean()
    df["Volume_SMA_20"] = df["Volume"].rolling(20).mean()
    df["Volume_Ratio"] = df["Volume"] / df["Volume_SMA_20"]
    df["Volume_Change"] = df["Volume"].pct_change()

    # 量價趨勢
    df["VPT"] = (df["Return"] * df["Volume"]).cumsum()

    return df


def add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    """新增時間週期特徵。"""
    df = df.copy()
    idx = df.index

    df["DayOfWeek"] = idx.dayofweek
    df["Month"] = idx.month
    df["Quarter"] = idx.quarter
    df["DayOfYear"] = idx.dayofyear
    df["WeekOfYear"] = idx.isocalendar().week.astype(int).values
    df["IsMonthEnd"] = idx.is_month_end.astype(int)
    df["IsQuarterEnd"] = idx.is_quarter_end.astype(int)

    # 週期性編碼（避免序數斷裂）
    df["DayOfWeek_Sin"] = np.sin(2 * np.pi * df["DayOfWeek"] / 5)
    df["DayOfWeek_Cos"] = np.cos(2 * np.pi * df["DayOfWeek"] / 5)
    df["Month_Sin"] = np.sin(2 * np.pi * df["Month"] / 12)
    df["Month_Cos"] = np.cos(2 * np.pi * df["Month"] / 12)

    return df


def add_lag_features(
    df: pd.DataFrame,
    columns: list[str] | None = None,
    lags: list[int] | None = None,
) -> pd.DataFrame:
    """
    新增滯後特徵。

    Parameters
    ----------
    columns : list[str] | None
        要建立滯後值的欄位，預設為 ["Close", "Volume", "Return"]
    lags : list[int] | None
        滯後天數列表，預設為 [1, 2, 3, 5, 10]
    """
    df = df.copy()
    columns = columns or ["Close", "Volume", "Return"]
    lags = lags or [1, 2, 3, 5, 10]

    for col in columns:
        if col not in df.columns:
            continue
        for lag in lags:
            df[f"{col}_Lag_{lag}"] = df[col].shift(lag)

    return df


def create_target(df: pd.DataFrame, target_type: str = "direction") -> pd.DataFrame:
    """
    建立預測目標。

    Parameters
    ----------
    target_type : str
        - "direction": 次日漲跌方向 (1=漲, 0=跌)
        - "return": 次日報酬率（連續值）
    """
    df = df.copy()

    if target_type == "direction":
        df["Target"] = (df["Close"].shift(-1) > df["Close"]).astype(int)
    elif target_type == "return":
        df["Target"] = df["Close"].pct_change().shift(-1)
    else:
        raise ValueError(f"不支援的目標類型: {target_type}")

    return df


def build_feature_matrix(
    df: pd.DataFrame,
    target_type: str = "direction",
    drop_na: bool = True,
) -> pd.DataFrame:
    """
    一站式特徵工程：整合所有特徵並建立目標。

    Parameters
    ----------
    df : pd.DataFrame
        原始 OHLCV 資料
    target_type : str
        目標類型 ("direction" 或 "return")
    drop_na : bool
        是否移除包含 NaN 的列

    Returns
    -------
    pd.DataFrame
        包含所有特徵與 Target 欄位的完整特徵矩陣
    """
    df = add_price_features(df)
    df = add_volume_features(df)
    df = add_technical_indicators(df)
    df = add_time_features(df)
    df = add_lag_features(df)
    df = create_target(df, target_type=target_type)

    if drop_na:
        before = len(df)
        df = df.dropna()
        dropped = before - len(df)
        if dropped > 0:
            print(f"[特徵工程] 移除 {dropped} 筆含 NaN 的資料（主要來自滯後與指標暖機期）")

    print(f"[特徵工程] 最終特徵數: {len(df.columns) - 1}，樣本數: {len(df)}")
    return df

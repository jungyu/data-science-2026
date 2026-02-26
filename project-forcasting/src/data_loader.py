"""
資料載入模組。

提供統一的股價資料下載與快取機制。
支援 yfinance 下載，並以 Parquet 格式快取至本地。
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import yfinance as yf

from src.config import DATA_DIR, DEFAULT_END_DATE, DEFAULT_START_DATE, DEFAULT_TICKER


def download_stock_data(
    ticker: str = DEFAULT_TICKER,
    start: str = DEFAULT_START_DATE,
    end: str | None = DEFAULT_END_DATE,
    cache: bool = True,
) -> pd.DataFrame:
    """
    下載股票 OHLCV 資料。

    Parameters
    ----------
    ticker : str
        股票代碼，例如 "AAPL", "2330.TW"
    start : str
        起始日期 (YYYY-MM-DD)
    end : str | None
        結束日期，None 表示取到最新
    cache : bool
        是否使用本地 Parquet 快取

    Returns
    -------
    pd.DataFrame
        包含 Open, High, Low, Close, Volume 欄位的 DataFrame，
        索引為 DatetimeIndex。
    """
    cache_path = DATA_DIR / f"{ticker}_{start}_{end or 'latest'}.parquet"

    if cache and cache_path.exists():
        df = pd.read_parquet(cache_path)
        print(f"[快取] 載入 {cache_path.name}，共 {len(df)} 筆")
        return df

    print(f"[下載] {ticker} ({start} ~ {end or '最新'}) ...")
    raw = yf.download(ticker, start=start, end=end, progress=False)

    if raw.empty:
        raise ValueError(f"無法取得 {ticker} 的資料，請確認代碼與日期範圍。")

    # yfinance 可能回傳 MultiIndex columns，展平之
    if isinstance(raw.columns, pd.MultiIndex):
        raw.columns = raw.columns.get_level_values(0)

    # 只保留標準 OHLCV 欄位
    expected_cols = ["Open", "High", "Low", "Close", "Volume"]
    df = raw[expected_cols].copy()
    df.index.name = "Date"
    df = df.sort_index()

    if cache:
        df.to_parquet(cache_path)
        print(f"[快取] 已存至 {cache_path.name}")

    print(f"[完成] 共 {len(df)} 筆，期間 {df.index[0].date()} ~ {df.index[-1].date()}")
    return df


def load_csv_data(path: str | Path, date_col: str = "Date") -> pd.DataFrame:
    """
    載入自訂 CSV 資料。

    Parameters
    ----------
    path : str | Path
        CSV 檔案路徑
    date_col : str
        日期欄位名稱

    Returns
    -------
    pd.DataFrame
        以日期為索引的 DataFrame
    """
    df = pd.read_csv(path, parse_dates=[date_col], index_col=date_col)
    df = df.sort_index()
    print(f"[載入] {Path(path).name}，共 {len(df)} 筆")
    return df


def train_test_split_by_date(
    df: pd.DataFrame,
    split_date: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    依日期切分訓練集與測試集（時間序列專用）。

    Parameters
    ----------
    df : pd.DataFrame
        原始資料，索引為 DatetimeIndex
    split_date : str
        切分日期 (YYYY-MM-DD)，此日期之前為訓練集

    Returns
    -------
    tuple[pd.DataFrame, pd.DataFrame]
        (train_df, test_df)
    """
    train = df[df.index < split_date].copy()
    test = df[df.index >= split_date].copy()
    print(f"[分割] 訓練集 {len(train)} 筆 | 測試集 {len(test)} 筆 | 切分點 {split_date}")
    return train, test

"""
專案全域設定。

集中管理資料路徑、模型參數、技術指標設定等。
所有路徑皆以專案根目錄為基準，避免硬編碼絕對路徑。
"""

from pathlib import Path

import dotenv

dotenv.load_dotenv()

# === 路徑設定 ===
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
MODEL_DIR = PROJECT_ROOT / "models"
OUTPUT_DIR = PROJECT_ROOT / "outputs"

# 確保目錄存在
for d in (DATA_DIR, MODEL_DIR, OUTPUT_DIR):
    d.mkdir(exist_ok=True)

# === 資料來源預設值 ===
DEFAULT_TICKER = "AAPL"
DEFAULT_START_DATE = "2018-01-01"
DEFAULT_END_DATE = None  # None 表示取到最新

# === 訓練/測試分割 ===
TRAIN_TEST_SPLIT_DATE = "2024-01-01"
VALIDATION_RATIO = 0.15  # 從訓練集中切出驗證集比例

# === 隨機種子 ===
RANDOM_SEED = 42

# === 技術指標參數 ===
TECHNICAL_INDICATORS = {
    "rsi_period": 14,
    "macd_fast": 12,
    "macd_slow": 26,
    "macd_signal": 9,
    "bb_period": 20,
    "bb_std": 2.0,
    "stoch_k": 14,
    "stoch_d": 3,
    "williams_r_period": 14,
    "sma_periods": [5, 10, 20, 50],
    "ema_periods": [5, 10, 20],
}

# === LightGBM 預設參數 ===
LIGHTGBM_PARAMS = {
    "objective": "binary",
    "metric": "binary_logloss",
    "boosting_type": "gbdt",
    "num_leaves": 31,
    "learning_rate": 0.05,
    "feature_fraction": 0.9,
    "bagging_fraction": 0.8,
    "bagging_freq": 5,
    "verbose": -1,
    "random_state": RANDOM_SEED,
}

# === XGBoost 預設參數 ===
XGBOOST_PARAMS = {
    "objective": "binary:logistic",
    "eval_metric": "logloss",
    "max_depth": 6,
    "learning_rate": 0.05,
    "subsample": 0.8,
    "colsample_bytree": 0.9,
    "random_state": RANDOM_SEED,
}

# === CatBoost 預設參數 ===
CATBOOST_PARAMS = {
    "loss_function": "Logloss",
    "eval_metric": "AUC",
    "depth": 6,
    "learning_rate": 0.05,
    "iterations": 500,
    "random_seed": RANDOM_SEED,
    "verbose": 0,
}

# === Optuna 超參數搜尋 ===
OPTUNA_N_TRIALS = 50
OPTUNA_CV_SPLITS = 5

# === 視覺化 ===
PLOT_STYLE = "seaborn-v0_8-whitegrid"
PLOT_FIGSIZE = (14, 7)
PLOT_DPI = 150

# === 中文字體設定 ===
CJK_FONT_CANDIDATES = [
    "Noto Sans CJK TC",
    "Noto Sans TC",
    "Microsoft JhengHei",
    "PingFang TC",
    "Apple LiGothic",
    "SimHei",
]

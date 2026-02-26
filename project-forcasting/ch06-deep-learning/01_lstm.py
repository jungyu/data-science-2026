"""
Ch06-01: LSTM 時間序列預測。

學習重點：
- 序列資料的 sliding window 建構
- PyTorch Dataset / DataLoader 用法
- LSTM 模型定義與訓練迴圈
- 早停策略
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import DATA_DIR, MODEL_DIR, OUTPUT_DIR, RANDOM_SEED, TRAIN_TEST_SPLIT_DATE
from src.data_loader import download_stock_data, train_test_split_by_date
from src.feature_engineer import build_feature_matrix
from src.plot_utils import apply_style

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.preprocessing import StandardScaler
from torch.utils.data import DataLoader, Dataset

# 固定隨機種子
torch.manual_seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu")
SEQUENCE_LENGTH = 20  # 使用過去 20 天的資料
BATCH_SIZE = 64
EPOCHS = 100
LEARNING_RATE = 1e-3
HIDDEN_SIZE = 64
NUM_LAYERS = 2
PATIENCE = 15  # 早停耐心值


class TimeSeriesDataset(Dataset):
    """將時間序列轉為 sliding window 格式的 Dataset。"""

    def __init__(self, X: np.ndarray, y: np.ndarray, seq_len: int = SEQUENCE_LENGTH):
        self.X = torch.FloatTensor(X)
        self.y = torch.FloatTensor(y)
        self.seq_len = seq_len

    def __len__(self) -> int:
        return len(self.X) - self.seq_len

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor]:
        return self.X[idx : idx + self.seq_len], self.y[idx + self.seq_len]


class LSTMClassifier(nn.Module):
    """LSTM 二元分類模型。"""

    def __init__(self, input_size: int, hidden_size: int = HIDDEN_SIZE, num_layers: int = NUM_LAYERS):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True,
            dropout=0.2 if num_layers > 1 else 0.0,
        )
        self.classifier = nn.Sequential(
            nn.Linear(hidden_size, 32),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(32, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        lstm_out, (h_n, _) = self.lstm(x)
        # 使用最後一層的隱藏狀態
        last_hidden = h_n[-1]
        return self.classifier(last_hidden).squeeze(-1)


def get_feature_target(df):
    exclude = {"Target", "Open", "High", "Low", "Close", "Volume"}
    feature_cols = [c for c in df.columns if c not in exclude]
    return df[feature_cols].values, df["Target"].values


def main() -> None:
    print(f"=== LSTM 股價漲跌預測 ===")
    print(f"  裝置: {DEVICE}")
    print(f"  序列長度: {SEQUENCE_LENGTH}")

    # === 1. 準備資料 ===
    cache_path = DATA_DIR / "feature_matrix_full.parquet"
    if cache_path.exists():
        feature_df = pd.read_parquet(cache_path)
    else:
        df = download_stock_data(ticker="AAPL", start="2018-01-01")
        feature_df = build_feature_matrix(df, target_type="direction")

    train_df, test_df = train_test_split_by_date(feature_df, TRAIN_TEST_SPLIT_DATE)
    X_train_raw, y_train = get_feature_target(train_df)
    X_test_raw, y_test = get_feature_target(test_df)

    # 標準化（LSTM 對尺度敏感）
    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train_raw)
    X_test = scaler.transform(X_test_raw)

    input_size = X_train.shape[1]
    print(f"  特徵數: {input_size}")

    # DataLoader
    train_ds = TimeSeriesDataset(X_train, y_train)
    test_ds = TimeSeriesDataset(X_test, y_test)
    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=False)  # 時序不 shuffle
    test_loader = DataLoader(test_ds, batch_size=BATCH_SIZE, shuffle=False)

    # === 2. 建立模型 ===
    model = LSTMClassifier(input_size=input_size).to(DEVICE)
    criterion = nn.BCEWithLogitsLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=LEARNING_RATE)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode="min", patience=5, factor=0.5)

    print(f"\n  模型參數量: {sum(p.numel() for p in model.parameters()):,}")

    # === 3. 訓練 ===
    print(f"\n=== 開始訓練 (max {EPOCHS} epochs) ===")
    train_losses = []
    val_losses = []
    best_val_loss = float("inf")
    patience_counter = 0

    for epoch in range(EPOCHS):
        # 訓練
        model.train()
        epoch_loss = 0.0
        for X_batch, y_batch in train_loader:
            X_batch, y_batch = X_batch.to(DEVICE), y_batch.to(DEVICE)
            optimizer.zero_grad()
            output = model(X_batch)
            loss = criterion(output, y_batch)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            epoch_loss += loss.item()
        train_losses.append(epoch_loss / len(train_loader))

        # 驗證
        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for X_batch, y_batch in test_loader:
                X_batch, y_batch = X_batch.to(DEVICE), y_batch.to(DEVICE)
                output = model(X_batch)
                loss = criterion(output, y_batch)
                val_loss += loss.item()
        val_losses.append(val_loss / len(test_loader))
        scheduler.step(val_losses[-1])

        # 早停
        if val_losses[-1] < best_val_loss:
            best_val_loss = val_losses[-1]
            patience_counter = 0
            torch.save(model.state_dict(), MODEL_DIR / "lstm_best.pt")
        else:
            patience_counter += 1

        if (epoch + 1) % 10 == 0 or patience_counter == PATIENCE:
            print(f"  Epoch {epoch+1:>3} | Train Loss: {train_losses[-1]:.4f} | Val Loss: {val_losses[-1]:.4f}")

        if patience_counter >= PATIENCE:
            print(f"  早停於 Epoch {epoch+1}")
            break

    # === 4. 載入最佳模型評估 ===
    model.load_state_dict(torch.load(MODEL_DIR / "lstm_best.pt", weights_only=True))
    model.eval()

    all_preds = []
    all_probs = []
    all_labels = []

    with torch.no_grad():
        for X_batch, y_batch in test_loader:
            X_batch = X_batch.to(DEVICE)
            output = model(X_batch)
            probs = torch.sigmoid(output).cpu().numpy()
            preds = (probs > 0.5).astype(int)
            all_preds.extend(preds)
            all_probs.extend(probs)
            all_labels.extend(y_batch.numpy())

    from sklearn.metrics import accuracy_score, roc_auc_score

    acc = accuracy_score(all_labels, all_preds)
    auc = roc_auc_score(all_labels, all_probs)
    print(f"\n=== 測試集結果 ===")
    print(f"  準確率: {acc:.4f}")
    print(f"  AUC:    {auc:.4f}")

    # === 5. 視覺化 ===
    apply_style()
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    axes[0].plot(train_losses, label="Train Loss")
    axes[0].plot(val_losses, label="Val Loss")
    axes[0].set_title("訓練損失曲線")
    axes[0].set_xlabel("Epoch")
    axes[0].set_ylabel("Loss")
    axes[0].legend()

    axes[1].hist(all_probs, bins=50, edgecolor="white")
    axes[1].axvline(x=0.5, color="red", linestyle="--")
    axes[1].set_title("預測機率分佈")
    axes[1].set_xlabel("P(漲)")

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "ch06_lstm.png", dpi=150, bbox_inches="tight")
    plt.show()


if __name__ == "__main__":
    main()

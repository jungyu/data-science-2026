"""
Ch06-02: Transformer Encoder 時間序列預測。

學習重點：
- Self-Attention 機制如何處理時間序列
- Positional Encoding 的必要性
- Transformer 與 LSTM 的設計差異
"""

from __future__ import annotations

import math
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

torch.manual_seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu")
SEQUENCE_LENGTH = 20
BATCH_SIZE = 64
EPOCHS = 80
LEARNING_RATE = 5e-4
D_MODEL = 64
NHEAD = 4
NUM_ENCODER_LAYERS = 2
PATIENCE = 15


class TimeSeriesDataset(Dataset):
    def __init__(self, X: np.ndarray, y: np.ndarray, seq_len: int = SEQUENCE_LENGTH):
        self.X = torch.FloatTensor(X)
        self.y = torch.FloatTensor(y)
        self.seq_len = seq_len

    def __len__(self) -> int:
        return len(self.X) - self.seq_len

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor]:
        return self.X[idx : idx + self.seq_len], self.y[idx + self.seq_len]


class PositionalEncoding(nn.Module):
    """正弦位置編碼，為 Transformer 提供序列順序資訊。"""

    def __init__(self, d_model: int, max_len: int = 500):
        super().__init__()
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        pe = pe.unsqueeze(0)  # (1, max_len, d_model)
        self.register_buffer("pe", pe)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return x + self.pe[:, : x.size(1), :]


class TransformerClassifier(nn.Module):
    """Transformer Encoder 二元分類模型。"""

    def __init__(self, input_size: int, d_model: int = D_MODEL, nhead: int = NHEAD, num_layers: int = NUM_ENCODER_LAYERS):
        super().__init__()
        self.input_proj = nn.Linear(input_size, d_model)
        self.pos_encoder = PositionalEncoding(d_model)
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=d_model,
            nhead=nhead,
            dim_feedforward=d_model * 4,
            dropout=0.1,
            batch_first=True,
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)
        self.classifier = nn.Sequential(
            nn.Linear(d_model, 32),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(32, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x: (batch, seq_len, input_size)
        x = self.input_proj(x)            # (batch, seq_len, d_model)
        x = self.pos_encoder(x)           # 加入位置編碼
        x = self.transformer(x)           # (batch, seq_len, d_model)
        # 使用最後一個時間步的輸出
        x = x[:, -1, :]                   # (batch, d_model)
        return self.classifier(x).squeeze(-1)


def get_feature_target(df):
    exclude = {"Target", "Open", "High", "Low", "Close", "Volume"}
    feature_cols = [c for c in df.columns if c not in exclude]
    return df[feature_cols].values, df["Target"].values


def main() -> None:
    print(f"=== Transformer 股價漲跌預測 ===")
    print(f"  裝置: {DEVICE}")
    print(f"  d_model={D_MODEL}, nhead={NHEAD}, layers={NUM_ENCODER_LAYERS}")

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

    scaler = StandardScaler()
    X_train = scaler.fit_transform(X_train_raw)
    X_test = scaler.transform(X_test_raw)

    input_size = X_train.shape[1]
    print(f"  特徵數: {input_size}")

    train_ds = TimeSeriesDataset(X_train, y_train)
    test_ds = TimeSeriesDataset(X_test, y_test)
    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=False)
    test_loader = DataLoader(test_ds, batch_size=BATCH_SIZE, shuffle=False)

    # === 2. 建立模型 ===
    model = TransformerClassifier(input_size=input_size).to(DEVICE)
    criterion = nn.BCEWithLogitsLoss()
    optimizer = torch.optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS)

    print(f"  模型參數量: {sum(p.numel() for p in model.parameters()):,}")

    # === 3. 訓練 ===
    print(f"\n=== 開始訓練 ===")
    train_losses, val_losses = [], []
    best_val_loss = float("inf")
    patience_counter = 0

    for epoch in range(EPOCHS):
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
        scheduler.step()

        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for X_batch, y_batch in test_loader:
                X_batch, y_batch = X_batch.to(DEVICE), y_batch.to(DEVICE)
                loss = criterion(model(X_batch), y_batch)
                val_loss += loss.item()
        val_losses.append(val_loss / len(test_loader))

        if val_losses[-1] < best_val_loss:
            best_val_loss = val_losses[-1]
            patience_counter = 0
            torch.save(model.state_dict(), MODEL_DIR / "transformer_best.pt")
        else:
            patience_counter += 1

        if (epoch + 1) % 10 == 0 or patience_counter == PATIENCE:
            print(f"  Epoch {epoch+1:>3} | Train: {train_losses[-1]:.4f} | Val: {val_losses[-1]:.4f}")

        if patience_counter >= PATIENCE:
            print(f"  早停於 Epoch {epoch+1}")
            break

    # === 4. 評估 ===
    model.load_state_dict(torch.load(MODEL_DIR / "transformer_best.pt", weights_only=True))
    model.eval()

    all_preds, all_probs, all_labels = [], [], []
    with torch.no_grad():
        for X_batch, y_batch in test_loader:
            output = model(X_batch.to(DEVICE))
            probs = torch.sigmoid(output).cpu().numpy()
            all_preds.extend((probs > 0.5).astype(int))
            all_probs.extend(probs)
            all_labels.extend(y_batch.numpy())

    from sklearn.metrics import accuracy_score, roc_auc_score

    acc = accuracy_score(all_labels, all_preds)
    auc = roc_auc_score(all_labels, all_probs)
    print(f"\n=== 測試集結果 ===")
    print(f"  準確率: {acc:.4f}")
    print(f"  AUC:    {auc:.4f}")

    # === 5. Attention 視覺化 ===
    apply_style()
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    axes[0].plot(train_losses, label="Train Loss")
    axes[0].plot(val_losses, label="Val Loss")
    axes[0].set_title("Transformer 訓練損失曲線")
    axes[0].set_xlabel("Epoch")
    axes[0].set_ylabel("Loss")
    axes[0].legend()

    axes[1].hist(all_probs, bins=50, edgecolor="white")
    axes[1].axvline(x=0.5, color="red", linestyle="--")
    axes[1].set_title("預測機率分佈")
    axes[1].set_xlabel("P(漲)")

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "ch06_transformer.png", dpi=150, bbox_inches="tight")
    plt.show()

    print("\n=== LSTM vs Transformer 比較提示 ===")
    print("  - LSTM: 逐步處理，適合長度較短的序列")
    print("  - Transformer: 平行處理，對長序列更有效率")
    print("  - 對於每日股價（低頻），兩者差異通常不大")
    print("  - Transformer 在高頻數據（tick data）中優勢更明顯")


if __name__ == "__main__":
    main()

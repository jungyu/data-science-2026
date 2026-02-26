# Ch06 — 深度學習預測

## 學習目標

- 理解 LSTM 處理序列資料的機制（記憶門、遺忘門、輸出門）
- 學會使用 PyTorch 建構時間序列預測模型
- 認識 Transformer 架構在時間序列的應用
- 掌握序列資料的 DataLoader 建構技巧

## 核心觀念

**LSTM vs Transformer**：
```
LSTM:        x₁ → h₁ → x₂ → h₂ → x₃ → h₃ → ... → 預測
             （逐步處理，保留長期記憶）

Transformer: [x₁, x₂, x₃, ..., xₙ] → Attention → 預測
             （平行處理，自注意力機制）
```

## 範例檔案

| 檔案 | 說明 |
|------|------|
| `01_lstm.py` | LSTM 模型：序列建構、訓練迴圈、預測 |
| `02_transformer.py` | 簡易 Transformer Encoder 模型 |

## 練習

1. 調整 LSTM 的隱藏層大小與層數，觀察對收斂速度的影響
2. 嘗試 GRU（LSTM 的簡化版本），比較效能
3. 在 Transformer 中加入 positional encoding

# Ch00 — 環境設置與驗證

## 學習目標

- 建立可運作的 Python 時間序列預測開發環境
- 確認所有相依套件正確安裝
- 驗證資料下載與中文圖表功能

## 環境需求

- Python >= 3.11
- 建議使用 `uv` 或 `venv` 建立虛擬環境

## 快速開始

```bash
# 1. 建立虛擬環境
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows

# 2. 安裝相依套件
pip install -e ".[all]"

# 3. 驗證安裝
python ch00-setup/verify_install.py
```

## 範例檔案

| 檔案 | 說明 |
|------|------|
| `verify_install.py` | 逐一檢查所有套件並下載測試資料 |

## 常見問題

### Prophet 安裝失敗
```bash
# macOS 可能需要先安裝 cmdstan
pip install prophet --no-cache-dir
```

### LightGBM 安裝問題 (macOS Apple Silicon)
```bash
brew install libomp
pip install lightgbm
```

### 中文字體缺失
安裝 Noto Sans CJK TC：
```bash
# macOS
brew install --cask font-noto-sans-cjk-tc

# Ubuntu
sudo apt install fonts-noto-cjk
```

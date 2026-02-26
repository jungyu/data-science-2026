# 時間序列預測學習專案 (Forecasting)

> 從統計方法到深度學習的完整預測學習路徑

## 快速導覽

- [環境設置](#環境設置) | [學習路徑](#學習路徑) | [專案結構](#專案結構) | [能力矩陣](#能力矩陣)

## 目標對象

- 資管系學生，已具備 Python 與基礎統計知識
- 想系統性學習時間序列預測（而非只跑一個 model）
- 希望理解「為什麼這樣做」而非只是「複製貼上能跑」

## 環境設置

```bash
# 1. 建立虛擬環境
python -m venv .venv
source .venv/bin/activate

# 2. 安裝所有相依套件
pip install -e ".[all]"

# 3. 驗證安裝
python ch00-setup/verify_install.py
```

詳細安裝說明與常見問題：[ch00-setup/README.md](ch00-setup/README.md)

## 學習路徑

```
Week 1: 基礎觀念
  Ch00 環境設置 → Ch01 時間序列 EDA

Week 2: 統計方法
  Ch02 指數平滑 / ARIMA / GARCH

Week 3: 預測框架
  Ch03 Prophet

Week 4: 機器學習
  Ch04 特徵工程 → Ch05 梯度提升樹

Week 5: 深度學習
  Ch06 LSTM / Transformer

Week 6: 整合與實戰
  Ch07 模型評估與回測 → Ch08 綜合專案
```

### 各章概覽

| 章節 | 主題 | 關鍵演算法 | 預估時間 |
|------|------|-----------|---------|
| [Ch00](ch00-setup/) | 環境設置 | — | 30 min |
| [Ch01](ch01-eda/) | 時間序列 EDA | 分解、ADF、ACF/PACF | 2 hr |
| [Ch02](ch02-statistical/) | 統計預測方法 | ETS、ARIMA、SARIMA、GARCH | 4 hr |
| [Ch03](ch03-prophet/) | Prophet 框架 | Prophet、交叉驗證 | 2 hr |
| [Ch04](ch04-features/) | 特徵工程 | 滯後特徵、技術指標、週期編碼 | 3 hr |
| [Ch05](ch05-tree-models/) | 梯度提升樹 | LightGBM、XGBoost、CatBoost、Optuna | 4 hr |
| [Ch06](ch06-deep-learning/) | 深度學習 | LSTM、Transformer | 3 hr |
| [Ch07](ch07-evaluation/) | 模型評估 | Walk-forward、回測、MLflow | 3 hr |
| [Ch08](ch08-capstone/) | 綜合專案 | Ensemble、完整管線 | 4+ hr |

## 專案結構

```
project-forcasting/
├── pyproject.toml          # 專案設定與相依套件
├── conftest.py             # pytest 設定
├── .env.example            # 環境變數範本
│
├── src/                    # 共用模組
│   ├── config.py           # 全域設定（路徑、參數、指標）
│   ├── data_loader.py      # 資料下載與快取
│   ├── feature_engineer.py # 特徵工程管線
│   ├── evaluator.py        # 模型評估與回測
│   └── plot_utils.py       # 視覺化工具（含中文字體）
│
├── ch00-setup/             # 環境設置與驗證
├── ch01-eda/               # 時間序列探索性資料分析
├── ch02-statistical/       # 統計預測方法
├── ch03-prophet/           # Prophet 預測框架
├── ch04-features/          # 特徵工程
├── ch05-tree-models/       # 梯度提升樹模型
├── ch06-deep-learning/     # 深度學習預測
├── ch07-evaluation/        # 模型評估與回測
├── ch08-capstone/          # 綜合專案
│
├── tests/                  # 單元測試
├── data/                   # 資料快取（git 忽略）
├── models/                 # 模型產出（git 忽略）
└── outputs/                # 圖表產出（git 忽略）
```

## 演算法地圖

```
時間序列預測方法
│
├── 統計方法 (Ch02)
│   ├── 指數平滑 (ETS)
│   │   ├── 簡單指數平滑 (SES)
│   │   ├── Holt 雙重指數平滑
│   │   └── Holt-Winters 三重指數平滑
│   ├── ARIMA 家族
│   │   ├── ARIMA(p,d,q)
│   │   └── SARIMA(p,d,q)(P,D,Q,s)
│   └── 波動率模型
│       ├── GARCH(1,1)
│       └── EGARCH / GJR-GARCH
│
├── 預測框架 (Ch03)
│   └── Prophet（趨勢 + 季節性 + 假日）
│
├── 機器學習 (Ch04-05)
│   ├── 特徵工程
│   │   ├── 滯後特徵 / 滾動窗口
│   │   ├── 技術指標 (RSI, MACD, BB, KD)
│   │   └── 時間週期編碼 (sin/cos)
│   └── 梯度提升樹
│       ├── LightGBM（Leaf-wise）
│       ├── XGBoost（Level-wise）
│       └── CatBoost（Symmetric Tree）
│
├── 深度學習 (Ch06)
│   ├── LSTM（序列記憶）
│   └── Transformer（自注意力）
│
└── 整合方法 (Ch08)
    └── Ensemble（投票法 / 堆疊法）
```

## 能力矩陣

| 能力維度 | Ch01 | Ch02 | Ch03 | Ch04 | Ch05 | Ch06 | Ch07 | Ch08 |
|----------|:----:|:----:|:----:|:----:|:----:|:----:|:----:|:----:|
| 資料處理 | ++ | + | + | ++ | + | + | + | ++ |
| 統計分析 | ++ | ++ | + | + | | | ++ | + |
| 機器學習 | | | | ++ | ++ | | + | ++ |
| 深度學習 | | | | | | ++ | | + |
| 模型評估 | | + | + | | + | + | ++ | ++ |
| 視覺化 | ++ | + | + | + | + | + | ++ | ++ |
| 實驗管理 | | | | | | | ++ | ++ |

## 評分規準

| 維度 | 優秀 (A) | 良好 (B) | 基礎 (C) | 待加強 (D) |
|------|---------|---------|---------|-----------|
| **資料理解** | 能解釋定態性、自相關的意義並據此選擇模型 | 能執行檢定並判讀結果 | 能跑程式但不理解輸出意義 | 無法完成 EDA |
| **模型多樣性** | 4+ 種模型 + Ensemble，含統計與 ML | 3 種模型，跨不同類別 | 1-2 種模型 | 僅複製範例 |
| **評估嚴謹度** | Walk-forward + 交易成本 + 統計顯著性 | Walk-forward + 交易成本 | 時間序列分割 | 隨機分割 (有洩漏) |
| **程式品質** | 模組化 + 型別標註 + 測試 + MLflow | 模組化 + 基本記錄 | 能執行的腳本 | 無法執行 |
| **報告品質** | 完整分析、有洞見、能回答追問 | 有圖表與摘要 | 僅貼程式輸出 | 無報告 |

## 相對於原始版本的改進

本專案基於 [DataScout/forcasting](https://github.com/jungyu/DataScout/tree/main/forcasting) 重構，主要改進：

| 面向 | 原版 | 本版 |
|------|------|------|
| 演算法涵蓋 | 僅 LightGBM | ETS → ARIMA → Prophet → LightGBM/XGBoost/CatBoost → LSTM/Transformer |
| 程式結構 | 7+ 重複檔案 | 模組化 src/ + 章節分離 |
| 超參數優化 | GridSearch（低效） | Optuna 貝葉斯優化 |
| 模型評估 | 單次分割 | Walk-forward 交叉驗證 |
| 回測 | 無交易成本 | 含交易成本 + 多指標 |
| 實驗管理 | 無 | MLflow 追蹤 |
| 情緒特徵 | 模擬（循環論證） | 已移除（避免誤導） |
| 路徑處理 | 硬編碼絕對路徑 | pathlib 相對路徑 |
| Python 版本 | 未指定 | >= 3.11 + type hints |
| 套件管理 | requirements.txt | pyproject.toml (PEP 517) |

## 授權

MIT License

# 第 15 章：模型治理與 MLOps — 讓模型活在真實世界

> 「模型在 Jupyter Notebook 裡跑得很好。」
> 「那部署上線呢？」
> 「……什麼是部署？」

---

## 🎯 本章目標

讀完這一章，你將能夠：

1. 理解為什麼 ML 模型需要 **治理（Governance）**
2. 使用 sklearn 的 **Pipeline** 作為治理的基礎
3. 用 **joblib** 儲存和載入模型
4. 理解 **DVC** 的概念：為資料和模型做版本控制
5. 認識 **MLflow** 的實驗追蹤功能
6. 掌握 **可重現性（Reproducibility）** 的要求
7. 理解 **模型監控** 和 **概念漂移（Concept Drift）**
8. 描述完整的 **MLOps 生命週期**

---

## 為什麼需要模型治理？

### Notebook 英雄 vs 生產環境

```
┌─────────────────────────────────────────────────────────┐
│                                                           │
│  Notebook 裡的世界          真實世界                       │
│  ─────────────────          ────────                      │
│  資料永遠不變               資料每天都在變                  │
│  只跑一次就好               要 24/7 持續運行                │
│  自己一個人用               整個團隊要協作                  │
│  出錯就重跑                 出錯要有人被叫醒                │
│  「我記得上次改了什麼」     「三個月前是誰改了什麼？」      │
│  隨便 import               每個套件都要鎖版本              │
│                                                           │
│  90% 的模型死在從 Notebook 到生產環境的路上                │
└─────────────────────────────────────────────────────────┘
```

### 模型治理的四大支柱

```
                    模型治理
                       │
       ┌───────┬───────┼───────┬───────┐
       │       │       │       │       │
    可重現性  版本控制  監控    文件化
       │       │       │       │
   "能重跑"  "能回溯"  "能預警"  "能理解"
```

💡 **重點觀念**：模型治理不是官僚作業，而是確保你的模型能在真實世界中
**持續、穩定、可靠** 地運作。

---

## Pipeline 就是治理的起點

### 為什麼 Pipeline 很重要？

沒有 Pipeline 的程式碼：

```python
# ❌ 散落各處的前處理步驟
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

pca = PCA(n_components=10)
X_train_pca = pca.fit_transform(X_train_scaled)
X_test_pca = pca.transform(X_test_scaled)

model = RandomForestClassifier()
model.fit(X_train_pca, y_train)
y_pred = model.predict(X_test_pca)

# 部署時要記得：先 scale → 再 PCA → 再 predict
# 三個月後你會忘記順序的 🙃
```

有 Pipeline 的程式碼：

```python
# ✅ 一切包在一起
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.ensemble import RandomForestClassifier

pipeline = Pipeline([
    ('scaler', StandardScaler()),
    ('pca', PCA(n_components=10)),
    ('classifier', RandomForestClassifier(random_state=42))
])

# 一行搞定訓練
pipeline.fit(X_train, y_train)

# 一行搞定預測（自動跑完所有前處理）
y_pred = pipeline.predict(X_test)

# 部署時只需要這一個 pipeline 物件
```

### Pipeline 的治理優勢

```
+------------------+------------------------------------------+
| 治理面向         | Pipeline 如何幫助                         |
+------------------+------------------------------------------+
| 可重現性         | 所有步驟封裝在一起，順序固定              |
| 防止資料洩漏     | fit 和 transform 的邏輯自動管理           |
| 部署簡化         | 只需儲存/載入一個物件                     |
| 團隊協作         | 明確定義的處理流程，人人看得懂            |
| 版本控制         | 一個物件 = 一個版本                       |
+------------------+------------------------------------------+
```

### 進階：ColumnTransformer + Pipeline

```python
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.ensemble import GradientBoostingClassifier

# 定義不同類型的特徵
numeric_features = ['age', 'income', 'credit_score']
categorical_features = ['education', 'employment', 'region']

# 為不同特徵類型設定不同的前處理
preprocessor = ColumnTransformer(
    transformers=[
        ('num', StandardScaler(), numeric_features),
        ('cat', OneHotEncoder(handle_unknown='ignore'), categorical_features)
    ]
)

# 完整 Pipeline
full_pipeline = Pipeline([
    ('preprocessor', preprocessor),
    ('classifier', GradientBoostingClassifier(random_state=42))
])

# 訓練與預測
full_pipeline.fit(X_train, y_train)
y_pred = full_pipeline.predict(X_test)

# 這個 pipeline 包含了「一切」：
# - 數值特徵標準化
# - 類別特徵 One-Hot 編碼
# - 模型本身
```

---

## 🧠 動動腦

> 為什麼 Pipeline 可以「防止資料洩漏」？
>
> 提示：想想如果你先對 **整個資料集** 做 StandardScaler，
> 然後才分成 train/test，會發生什麼事？
> Pipeline + cross_val_score 是怎麼避免這個問題的？

---

## 用 joblib 儲存模型

訓練好的模型需要 **持久化（Persistence）**，才能在生產環境中使用。

### 基本用法

```python
import joblib
from datetime import datetime

# === 儲存模型 ===
model_path = f"models/fraud_detector_{datetime.now():%Y%m%d_%H%M}.joblib"
joblib.dump(full_pipeline, model_path)
print(f"模型已儲存至: {model_path}")
# 模型已儲存至: models/fraud_detector_20260227_1430.joblib

# === 載入模型 ===
loaded_pipeline = joblib.load(model_path)

# 直接預測！不需要重新訓練
y_pred_loaded = loaded_pipeline.predict(X_test)

# 驗證結果一致
import numpy as np
assert np.array_equal(y_pred, y_pred_loaded), "預測結果不一致！"
print("驗證通過：載入的模型預測結果與原始一致")
```

### joblib vs pickle

```
+------------------+-----------------+------------------+
| 特性             | joblib          | pickle           |
+------------------+-----------------+------------------+
| NumPy 陣列效率   | ✅ 優化          | ❌ 一般           |
| 壓縮支援         | ✅ 內建          | ❌ 需額外處理      |
| sklearn 推薦     | ✅ 官方推薦      | ⚠️ 可用但不推薦   |
| 大型模型         | ✅ 高效          | ❌ 較慢           |
| 安全性           | ⚠️ 注意來源      | ⚠️ 注意來源       |
+------------------+-----------------+------------------+
```

### 模型儲存的最佳實踐

```python
import joblib
import json
from datetime import datetime
from sklearn.metrics import accuracy_score, f1_score

def save_model_with_metadata(pipeline, X_test, y_test,
                              model_name, version):
    """儲存模型及其元資料"""

    # 1. 儲存模型
    model_path = f"models/{model_name}_v{version}.joblib"
    joblib.dump(pipeline, model_path)

    # 2. 儲存元資料
    y_pred = pipeline.predict(X_test)
    metadata = {
        'model_name': model_name,
        'version': version,
        'created_at': datetime.now().isoformat(),
        'sklearn_version': __import__('sklearn').__version__,
        'python_version': __import__('sys').version,
        'metrics': {
            'accuracy': float(accuracy_score(y_test, y_pred)),
            'f1_score': float(f1_score(y_test, y_pred, average='weighted')),
        },
        'pipeline_steps': [
            step[0] for step in pipeline.steps
        ],
        'n_features': X_test.shape[1],
        'n_test_samples': X_test.shape[0],
    }

    meta_path = f"models/{model_name}_v{version}_metadata.json"
    with open(meta_path, 'w') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    print(f"模型已儲存: {model_path}")
    print(f"元資料已儲存: {meta_path}")
    return model_path, meta_path

# 使用範例
save_model_with_metadata(
    full_pipeline, X_test, y_test,
    model_name='fraud_detector',
    version='1.0.0'
)
```

---

## ⚠️ 常見陷阱

### 陷阱 1：sklearn 版本不一致

```python
# ❌ 用 sklearn 1.3 訓練的模型，在 sklearn 1.5 上載入
# 可能會出現 Warning 甚至 Error

# ✅ 永遠記錄 sklearn 版本
import sklearn
print(f"sklearn version: {sklearn.__version__}")

# ✅ 在 requirements.txt 中鎖定版本
# scikit-learn==1.4.2
```

### 陷阱 2：只存模型，不存前處理

```python
# ❌ 只存 model，忘了 scaler 和 encoder
joblib.dump(model, 'model.joblib')
# 部署時：「scaler 呢？encoder 呢？」

# ✅ 用 Pipeline 把一切包在一起
joblib.dump(full_pipeline, 'pipeline.joblib')
# 部署時：載入一個物件就搞定
```

### 陷阱 3：從不受信任的來源載入模型

```python
# ⚠️ joblib.load 會執行任意程式碼！
# 永遠不要載入來源不明的 .joblib 檔案

# ✅ 只載入你自己訓練並儲存的模型
# ✅ 使用 hash 驗證模型完整性
import hashlib

def verify_model_integrity(model_path, expected_hash):
    with open(model_path, 'rb') as f:
        file_hash = hashlib.sha256(f.read()).hexdigest()
    if file_hash != expected_hash:
        raise ValueError(f"模型檔案已被竄改！")
    return True
```

---

## 版本控制：Git + DVC

### Git 的限制

Git 很適合追蹤程式碼，但 **不適合追蹤大型資料檔和模型檔**。

```
+-----------------------------------------------------+
|  Git 能追蹤的              Git 不適合追蹤的            |
|  ─────────────             ─────────────────          |
|  .py 程式碼                train.csv (500MB)          |
|  .yaml 設定檔              model.joblib (2GB)         |
|  requirements.txt          images/ (10GB)             |
|  Dockerfile                embeddings.npy (5GB)       |
+-----------------------------------------------------+
```

### DVC（Data Version Control）的概念

```
DVC 的核心思想：
用 Git 追蹤「指標」，用遠端儲存追蹤「實際檔案」。

就像圖書館的索引卡片：
- 卡片（.dvc 檔案）放在 Git 裡 → 小檔案，可追蹤
- 書本（實際資料）放在書架上 → 大檔案，存在遠端

┌──────────────────────────────────────────┐
│  Git Repository                           │
│  ├── train.csv.dvc    ← 指標檔（幾 KB）  │
│  ├── model.joblib.dvc ← 指標檔（幾 KB）  │
│  ├── src/train.py     ← 程式碼           │
│  └── params.yaml      ← 超參數設定       │
│                                           │
│  Remote Storage (S3/GCS/Azure)            │
│  ├── train.csv        ← 實際資料 (500MB) │
│  └── model.joblib     ← 實際模型 (2GB)   │
└──────────────────────────────────────────┘
```

### DVC 基本工作流程

```bash
# 1. 初始化 DVC
# dvc init

# 2. 追蹤大型檔案
# dvc add data/train.csv
# → 產生 data/train.csv.dvc（指標檔）
# → 原始檔案加入 .gitignore

# 3. Git 追蹤指標檔
# git add data/train.csv.dvc data/.gitignore
# git commit -m "追蹤訓練資料 v1"

# 4. 推送到遠端
# dvc push  # 資料推到 S3/GCS
# git push  # 指標推到 Git

# 5. 團隊成員取得資料
# git pull
# dvc pull  # 自動從遠端下載對應版本的資料

# 6. 切換到舊版本
# git checkout v1.0
# dvc checkout  # 自動取得 v1.0 對應的資料
```

💡 **重點觀念**：DVC 讓你的資料和模型也有「時光機」。任何時候都可以
回到某個歷史版本，取得當時的程式碼 **和** 資料。

---

## ❓ 沒有笨問題

**Q：我們真的需要 DVC 嗎？不能把資料放在共用資料夾？**

A：可以，但你會遇到問題：「昨天那版資料去哪了？」、「誰改了訓練資料？」、
「三個月前的模型是用哪版資料訓的？」DVC 解決的就是這些追溯問題。

**Q：DVC 和 Git LFS 有什麼不同？**

A：Git LFS 把大檔案存在 Git 伺服器旁邊，每個版本都佔空間。
DVC 更靈活，可以用 S3、GCS、Azure Blob 等各種儲存後端，
而且支援 ML Pipeline 的追蹤。

**Q：小專案也需要 DVC 嗎？**

A：如果你的資料 < 100MB 且很少變動，Git LFS 或甚至直接放 Git 都行。
但一旦資料開始增長，或有多人協作，DVC 就值得投資了。

**Q：DVC 免費嗎？**

A：DVC 本身是開源免費的。儲存後端（S3、GCS 等）的費用取決於你用多少空間。

---

## 實驗追蹤：MLflow 概念

### 為什麼需要實驗追蹤？

```
你的 Notebook 歷史：

嘗試 #1: RandomForest, n=100, AUC=0.85
嘗試 #2: RandomForest, n=200, max_depth=10, AUC=0.87
嘗試 #3: GradientBoosting, lr=0.1, AUC=0.89
嘗試 #4: 改了什麼來著？忘了… AUC=0.91 ← 最好的！
嘗試 #5: 想重現 #4，但跑不出一樣的結果…

你：「我到底改了什麼才得到 0.91 的？？？」
```

### MLflow 的核心概念

```
┌─────────────────────────────────────────────┐
│                  MLflow                      │
│                                              │
│  Experiment: 「信用卡詐欺偵測」              │
│  ├── Run #1                                  │
│  │   ├── Parameters: {n=100, depth=None}     │
│  │   ├── Metrics: {auc=0.85, f1=0.72}       │
│  │   ├── Artifacts: model_v1.joblib          │
│  │   └── Tags: {author=aaron, stage=dev}     │
│  ├── Run #2                                  │
│  │   ├── Parameters: {n=200, depth=10}       │
│  │   ├── Metrics: {auc=0.87, f1=0.76}       │
│  │   └── ...                                 │
│  └── Run #3                                  │
│      ├── Parameters: {model=GB, lr=0.1}      │
│      ├── Metrics: {auc=0.89, f1=0.81}       │
│      └── ...                                 │
│                                              │
│  → 所有嘗試都被完整記錄，永遠可以回溯       │
└─────────────────────────────────────────────┘
```

### MLflow 概念程式碼

```python
# 安裝：pip install mlflow
# 以下為概念示範

"""
import mlflow
import mlflow.sklearn

# 設定實驗名稱
mlflow.set_experiment("fraud_detection")

# 開始一次實驗
with mlflow.start_run(run_name="gradient_boosting_v1"):

    # 記錄超參數
    params = {
        'n_estimators': 200,
        'learning_rate': 0.1,
        'max_depth': 5,
        'random_state': 42,
    }
    mlflow.log_params(params)

    # 訓練模型
    model = GradientBoostingClassifier(**params)
    model.fit(X_train, y_train)

    # 記錄指標
    y_pred = model.predict(X_test)
    metrics = {
        'accuracy': accuracy_score(y_test, y_pred),
        'f1_score': f1_score(y_test, y_pred),
        'auc_roc': roc_auc_score(y_test, model.predict_proba(X_test)[:, 1]),
    }
    mlflow.log_metrics(metrics)

    # 儲存模型作為 artifact
    mlflow.sklearn.log_model(model, "model")

    # 記錄額外資訊
    mlflow.set_tag("author", "aaron")
    mlflow.set_tag("stage", "development")

    print(f"Run ID: {mlflow.active_run().info.run_id}")
    print(f"Metrics: {metrics}")

# 啟動 MLflow UI
# mlflow ui --port 5000
# 然後打開 http://localhost:5000 查看所有實驗
"""
```

### 不用 MLflow 的簡易替代方案

如果不想安裝 MLflow，可以用簡單的 JSON 日誌：

```python
import json
from datetime import datetime
import os

class SimpleExperimentTracker:
    """簡易實驗追蹤器"""

    def __init__(self, experiment_name, log_dir='experiments'):
        self.experiment_name = experiment_name
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)

    def log_run(self, params, metrics, notes=""):
        """記錄一次實驗"""
        run = {
            'experiment': self.experiment_name,
            'timestamp': datetime.now().isoformat(),
            'params': params,
            'metrics': metrics,
            'notes': notes,
        }

        # 存到 JSON 檔
        log_file = os.path.join(self.log_dir,
                                f"{self.experiment_name}.jsonl")
        with open(log_file, 'a') as f:
            f.write(json.dumps(run, ensure_ascii=False) + '\n')

        print(f"已記錄實驗: {metrics}")
        return run

    def get_best_run(self, metric='accuracy'):
        """找出最佳實驗"""
        log_file = os.path.join(self.log_dir,
                                f"{self.experiment_name}.jsonl")
        best = None
        with open(log_file, 'r') as f:
            for line in f:
                run = json.loads(line)
                if best is None or run['metrics'][metric] > best['metrics'][metric]:
                    best = run
        return best

# 使用範例
tracker = SimpleExperimentTracker("fraud_detection")

tracker.log_run(
    params={'model': 'RandomForest', 'n_estimators': 100},
    metrics={'accuracy': 0.95, 'f1': 0.72, 'auc': 0.85},
    notes='基線模型'
)

tracker.log_run(
    params={'model': 'GradientBoosting', 'n_estimators': 200, 'lr': 0.1},
    metrics={'accuracy': 0.96, 'f1': 0.81, 'auc': 0.89},
    notes='調整學習率後效果提升'
)

best = tracker.get_best_run(metric='auc')
print(f"\n最佳實驗: AUC={best['metrics']['auc']}, "
      f"模型={best['params']['model']}")
```

---

## 可重現性（Reproducibility）

### 可重現性清單

```
你的實驗能被重現嗎？檢查以下項目：

+------+----------------------------------+---------------+
| 編號 | 項目                             | 如何確保       |
+------+----------------------------------+---------------+
|  1   | Python 版本                      | pyenv / conda |
|  2   | 套件版本                         | requirements  |
|  3   | 隨機種子                         | random_state  |
|  4   | 資料版本                         | DVC / hash    |
|  5   | 超參數                           | config 檔     |
|  6   | 前處理步驟                       | Pipeline      |
|  7   | 特徵工程                         | 程式碼版本     |
|  8   | 訓練/測試分割                    | random_state  |
|  9   | 硬體環境                         | Docker        |
| 10   | 作業系統                         | Docker        |
+------+----------------------------------+---------------+
```

### 實作可重現性

```python
"""
可重現性範本
"""
import random
import numpy as np
from sklearn.model_selection import train_test_split

# ===== 1. 固定所有隨機種子 =====
RANDOM_SEED = 42

random.seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)

# ===== 2. 記錄環境資訊 =====
def log_environment():
    import sys, sklearn, platform
    env_info = {
        'python': sys.version,
        'sklearn': sklearn.__version__,
        'numpy': np.__version__,
        'platform': platform.platform(),
        'random_seed': RANDOM_SEED,
    }
    print("=== 環境資訊 ===")
    for k, v in env_info.items():
        print(f"  {k}: {v}")
    return env_info

log_environment()

# ===== 3. 資料載入與分割（固定種子）=====
X_train, X_test, y_train, y_test = train_test_split(
    X, y,
    test_size=0.3,
    random_state=RANDOM_SEED,  # 每次分割都一樣
    stratify=y                  # 保持類別比例
)

# ===== 4. 建立 Pipeline（所有步驟封裝）=====
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import GradientBoostingClassifier

pipeline = Pipeline([
    ('scaler', StandardScaler()),
    ('model', GradientBoostingClassifier(
        n_estimators=200,
        learning_rate=0.1,
        max_depth=5,
        random_state=RANDOM_SEED  # 模型也要固定種子
    ))
])

# ===== 5. 訓練與評估 =====
pipeline.fit(X_train, y_train)

# ===== 6. 儲存一切 =====
import joblib, json

joblib.dump(pipeline, 'models/pipeline_v1.joblib')
json.dump({
    'random_seed': RANDOM_SEED,
    'test_size': 0.3,
    'pipeline_params': pipeline.get_params(),
}, open('models/pipeline_v1_config.json', 'w'), indent=2)
```

---

## 🧠 動動腦

> 你的同事說：「我跑了一樣的程式碼，但結果不一樣！」
>
> 列出至少 5 個可能的原因。
>
> 提示：想想隨機種子、套件版本、資料、硬體……

---

## 模型監控與概念漂移

### 什麼是概念漂移（Concept Drift）？

```
模型是在「過去的資料」上訓練的。
但世界會變。

┌──────────────────────────────────────────────────┐
│                                                    │
│  訓練時期（2024）         部署後（2026）            │
│  ──────────────           ──────────────           │
│  詐欺手法：盜刷          詐欺手法：AI 深偽語音     │
│  客戶行為：實體店消費     客戶行為：全面線上支付    │
│  經濟環境：低利率         經濟環境：高通膨          │
│                                                    │
│  模型學到的「詐欺長什麼樣」已經過時了！            │
│                                                    │
│  這就是概念漂移。                                  │
│                                                    │
│  預測準確度                                        │
│    ^                                               │
│    |──────\                                        │
│    |       \                                       │
│    |        \________                              │
│    |                 \________                     │
│    +──────────────────────────────> 時間            │
│    部署   3個月    6個月    12個月                  │
│                                                    │
└──────────────────────────────────────────────────┘
```

### 概念漂移的種類

```
+------------------+------------------------+-----------------------+
| 類型             | 描述                   | 例子                  |
+------------------+------------------------+-----------------------+
| 突然漂移         | 資料分佈突然改變       | COVID-19 改變消費行為 |
| 漸進漂移         | 慢慢變化               | 客戶偏好逐年改變      |
| 週期漂移         | 季節性或週期性變化     | 聖誕節消費暴增        |
| 重現漂移         | 舊模式重新出現         | 經濟週期              |
+------------------+------------------------+-----------------------+
```

### 監控策略

```python
"""
模型監控：偵測概念漂移
"""
from sklearn.metrics import accuracy_score, f1_score
import numpy as np

class ModelMonitor:
    """簡易模型監控器"""

    def __init__(self, baseline_metrics, alert_threshold=0.05):
        """
        baseline_metrics: 模型部署時的基準指標
        alert_threshold: 指標下降多少時發出警報
        """
        self.baseline = baseline_metrics
        self.threshold = alert_threshold
        self.history = []

    def check(self, y_true, y_pred, period_name=""):
        """檢查當前效能是否漂移"""
        current_metrics = {
            'accuracy': accuracy_score(y_true, y_pred),
            'f1_score': f1_score(y_true, y_pred, average='weighted'),
        }

        alerts = []
        for metric, value in current_metrics.items():
            baseline_value = self.baseline[metric]
            drop = baseline_value - value

            if drop > self.threshold:
                alerts.append({
                    'metric': metric,
                    'baseline': baseline_value,
                    'current': value,
                    'drop': drop,
                    'severity': 'HIGH' if drop > self.threshold * 2 else 'MEDIUM'
                })

        result = {
            'period': period_name,
            'metrics': current_metrics,
            'alerts': alerts,
            'status': 'ALERT' if alerts else 'OK'
        }
        self.history.append(result)

        # 輸出報告
        print(f"\n{'='*50}")
        print(f"模型監控報告 - {period_name}")
        print(f"{'='*50}")
        for metric, value in current_metrics.items():
            baseline = self.baseline[metric]
            diff = value - baseline
            symbol = '+' if diff >= 0 else ''
            status = 'OK' if abs(diff) <= self.threshold else 'ALERT'
            print(f"  {metric}: {value:.4f} "
                  f"(基準: {baseline:.4f}, {symbol}{diff:.4f}) "
                  f"[{status}]")

        if alerts:
            print(f"\n  *** 警報 ***")
            for alert in alerts:
                print(f"  [{alert['severity']}] {alert['metric']} "
                      f"下降 {alert['drop']:.4f}")
            print(f"  建議：考慮重新訓練模型")
        else:
            print(f"\n  狀態: 正常運作中")

        return result

# 使用範例
monitor = ModelMonitor(
    baseline_metrics={'accuracy': 0.95, 'f1_score': 0.88},
    alert_threshold=0.05
)

# 模擬每月監控
# monitor.check(y_true_jan, y_pred_jan, "2026-01")
# monitor.check(y_true_feb, y_pred_feb, "2026-02")
```

### 資料漂移偵測

```python
def detect_data_drift(reference_data, current_data,
                       feature_names, threshold=0.1):
    """
    簡易資料漂移偵測：比較特徵分佈
    使用 KS 檢定（Kolmogorov-Smirnov test）
    """
    from scipy import stats

    drift_report = []

    for i, name in enumerate(feature_names):
        ref = reference_data[:, i]
        cur = current_data[:, i]

        # KS 檢定
        statistic, p_value = stats.ks_2samp(ref, cur)

        is_drift = p_value < threshold
        drift_report.append({
            'feature': name,
            'ks_statistic': statistic,
            'p_value': p_value,
            'drift_detected': is_drift
        })

    # 輸出報告
    print(f"{'特徵':>20s} | {'KS統計量':>8s} | {'p-value':>8s} | 漂移")
    print("-" * 55)
    for r in sorted(drift_report, key=lambda x: x['ks_statistic'],
                     reverse=True):
        flag = 'YES' if r['drift_detected'] else 'no'
        print(f"{r['feature']:>20s} | {r['ks_statistic']:>8.4f} | "
              f"{r['p_value']:>8.4f} | {flag}")

    n_drift = sum(1 for r in drift_report if r['drift_detected'])
    print(f"\n偵測到 {n_drift}/{len(feature_names)} 個特徵有漂移")

    return drift_report
```

---

## MLOps 生命週期

### 完整流程

```
MLOps 生命週期：

  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
  │          │    │          │    │          │    │          │
  │  訓練    │───►│  驗證    │───►│  部署    │───►│  監控    │
  │  Train   │    │ Validate │    │  Deploy  │    │ Monitor  │
  │          │    │          │    │          │    │          │
  └──────────┘    └──────────┘    └──────────┘    └────┬─────┘
       ▲                                               │
       │                                               │
       │              漂移偵測 / 效能下降               │
       └───────────────────────────────────────────────┘
                      重新訓練（Re-train）

每個階段的關鍵活動：

訓練（Train）:
  - 資料前處理與特徵工程
  - 模型選擇與超參數調整
  - 交叉驗證
  - 實驗追蹤（MLflow）

驗證（Validate）:
  - 測試集效能評估
  - 商業指標計算（第 13 章）
  - 可解釋性報告（第 14 章）
  - A/B 測試設計

部署（Deploy）:
  - 模型序列化（joblib）
  - API 包裝（Flask/FastAPI）
  - 容器化（Docker）
  - 漸進式上線（Canary Release）

監控（Monitor）:
  - 效能指標追蹤
  - 資料漂移偵測
  - 商業指標監控
  - 警報與通知
```

### MLOps 成熟度等級

```
+--------+------------------+------------------------------------+
| 等級   | 名稱             | 描述                               |
+--------+------------------+------------------------------------+
| Level 0| 手動流程         | Notebook 訓練，手動部署             |
| Level 1| ML Pipeline      | 自動化訓練 Pipeline，手動部署       |
| Level 2| CI/CD for ML     | 自動化訓練 + 自動化部署             |
| Level 3| Full MLOps       | 自動化訓練 + 部署 + 監控 + 重訓    |
+--------+------------------+------------------------------------+

大部分團隊在 Level 0-1。
達到 Level 2 就已經很厲害了。
Level 3 通常是大型科技公司的目標。
```

---

## 文件化要求

### 模型卡片（Model Card）

Google 提出的模型文件標準：

```python
MODEL_CARD_TEMPLATE = """
# 模型卡片：{model_name}

## 模型概述
- **模型類型**: {model_type}
- **版本**: {version}
- **訓練日期**: {training_date}
- **負責人**: {owner}

## 預期用途
- **主要用途**: {primary_use}
- **不適用場景**: {out_of_scope}
- **目標使用者**: {target_users}

## 訓練資料
- **資料來源**: {data_source}
- **資料量**: {data_size}
- **時間範圍**: {date_range}
- **資料版本**: {data_version}

## 效能指標
| 指標       | 整體  | 子群體 A | 子群體 B |
|-----------|-------|---------|---------|
| Accuracy  | {acc} | {acc_a} | {acc_b} |
| F1 Score  | {f1}  | {f1_a}  | {f1_b}  |
| AUC-ROC   | {auc} | {auc_a} | {auc_b} |

## 限制與偏差
- {limitation_1}
- {limitation_2}
- {bias_analysis}

## 倫理考量
- {ethical_consideration_1}
- {ethical_consideration_2}

## 監控計畫
- **監控指標**: {monitoring_metrics}
- **重訓觸發條件**: {retrain_trigger}
- **監控頻率**: {monitoring_frequency}
"""

def generate_model_card(model_info):
    """產生模型卡片"""
    return MODEL_CARD_TEMPLATE.format(**model_info)
```

### 最低文件要求

```
+------+----------------------------------+--------------------+
| 優先 | 文件                             | 格式               |
+------+----------------------------------+--------------------+
| 必要 | 模型卡片（Model Card）           | Markdown           |
| 必要 | 超參數與設定                     | YAML/JSON          |
| 必要 | 套件版本                         | requirements.txt   |
| 必要 | 效能指標                         | JSON               |
| 建議 | 訓練流程文件                     | Markdown           |
| 建議 | 資料字典                         | CSV/Markdown       |
| 建議 | 漂移監控報告                     | 自動產生           |
| 進階 | 公平性分析報告                   | Markdown/HTML      |
+------+----------------------------------+--------------------+
```

---

## 完整範例：從訓練到治理

```python
"""
完整 MLOps 流程範例
"""
import json
import joblib
import numpy as np
from datetime import datetime
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import accuracy_score, f1_score, roc_auc_score
from sklearn.datasets import make_classification

# ===== 設定 =====
CONFIG = {
    'random_seed': 42,
    'test_size': 0.3,
    'model_params': {
        'n_estimators': 200,
        'learning_rate': 0.1,
        'max_depth': 5,
    },
    'version': '1.0.0',
    'author': 'data-science-team',
}

# ===== Step 1: 資料 =====
X, y = make_classification(n_samples=10000, n_features=20,
                            random_state=CONFIG['random_seed'])
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=CONFIG['test_size'],
    random_state=CONFIG['random_seed'], stratify=y
)

# ===== Step 2: Pipeline =====
pipeline = Pipeline([
    ('scaler', StandardScaler()),
    ('model', GradientBoostingClassifier(
        **CONFIG['model_params'],
        random_state=CONFIG['random_seed']
    ))
])

# ===== Step 3: 訓練與交叉驗證 =====
cv_scores = cross_val_score(pipeline, X_train, y_train, cv=5, scoring='f1')
print(f"CV F1: {cv_scores.mean():.4f} (+/- {cv_scores.std():.4f})")

pipeline.fit(X_train, y_train)

# ===== Step 4: 評估 =====
y_pred = pipeline.predict(X_test)
y_proba = pipeline.predict_proba(X_test)[:, 1]

metrics = {
    'accuracy': float(accuracy_score(y_test, y_pred)),
    'f1_score': float(f1_score(y_test, y_pred)),
    'auc_roc': float(roc_auc_score(y_test, y_proba)),
    'cv_f1_mean': float(cv_scores.mean()),
    'cv_f1_std': float(cv_scores.std()),
}

# ===== Step 5: 儲存 =====
model_name = f"model_v{CONFIG['version']}"
joblib.dump(pipeline, f"models/{model_name}.joblib")

# 儲存完整的元資料
metadata = {
    'config': CONFIG,
    'metrics': metrics,
    'created_at': datetime.now().isoformat(),
    'environment': {
        'sklearn': __import__('sklearn').__version__,
        'numpy': np.__version__,
        'python': __import__('sys').version,
    },
    'data_info': {
        'n_train': len(X_train),
        'n_test': len(X_test),
        'n_features': X_train.shape[1],
    }
}

with open(f"models/{model_name}_metadata.json", 'w') as f:
    json.dump(metadata, f, indent=2, ensure_ascii=False)

print(f"\n模型已儲存: models/{model_name}.joblib")
print(f"元資料已儲存: models/{model_name}_metadata.json")
print(f"效能指標: {metrics}")
```

---

## 本章總結

```
+----------------------------------------------------------+
|              模型治理與 MLOps 速查表                       |
+----------------------------------------------------------+
|                                                            |
|  治理四大支柱：                                            |
|                                                            |
|  1. 可重現性                                               |
|     → Pipeline + random_state + requirements.txt           |
|                                                            |
|  2. 版本控制                                               |
|     → Git（程式碼）+ DVC（資料/模型）                      |
|                                                            |
|  3. 監控                                                   |
|     → 效能監控 + 資料漂移偵測 + 警報                       |
|                                                            |
|  4. 文件化                                                 |
|     → Model Card + 元資料 + 實驗日誌                       |
|                                                            |
|  MLOps 生命週期：                                          |
|     訓練 → 驗證 → 部署 → 監控 → (重訓)                    |
|                                                            |
|  記住：生產環境中的模型需要持續照顧，                       |
|        就像花園需要定期澆水和修剪。                         |
+----------------------------------------------------------+
```

---

## 📝 課後練習

### 練習 1：建立完整的 ML Pipeline

使用 sklearn 的任何分類資料集：
1. 建立包含前處理和模型的 Pipeline
2. 使用 cross_val_score 評估
3. 用 joblib 儲存 Pipeline 和元資料
4. 載入 Pipeline 並驗證預測結果一致

### 練習 2：實驗追蹤

使用本章的 `SimpleExperimentTracker`：
1. 對同一個問題嘗試至少 3 種不同的模型/超參數
2. 記錄每次嘗試的參數和指標
3. 找出最佳組合
4. 回答：「如果三個月後要重現最佳結果，需要記錄什麼？」

### 練習 3：模型監控模擬

1. 訓練一個模型並記錄基準指標
2. 模擬資料漂移（例如對測試集加入雜訊或改變分佈）
3. 使用 `ModelMonitor` 偵測效能下降
4. 使用 `detect_data_drift` 找出哪些特徵漂移了
5. 重新訓練模型並比較效果

### 練習 4（進階）：端到端 MLOps

建立一個完整的 ML 專案，包含：
1. `data/` - 資料（加上 .dvc 追蹤）
2. `src/train.py` - 訓練腳本
3. `src/predict.py` - 預測腳本
4. `src/monitor.py` - 監控腳本
5. `models/` - 模型和元資料
6. `experiments/` - 實驗日誌
7. `docs/model_card.md` - 模型卡片

---

> 📌 **恭喜你！** 你已經走完了從「準確率迷思」到「生產級模型治理」的旅程。
> 記住：好的資料科學不只是建模型，而是建立 **可信賴的決策系統**。

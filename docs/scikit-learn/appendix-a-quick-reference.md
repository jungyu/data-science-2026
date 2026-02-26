# 附錄 A：scikit-learn 快速參考卡

> 這是你的 ML 隨身小抄。列印出來，貼在螢幕旁邊。

---

## A.1 常用 Import 速查

```python
# === 資料分割與驗證 ===
from sklearn.model_selection import (
    train_test_split,          # 資料分割
    cross_val_score,           # 交叉驗證分數
    cross_validate,            # 交叉驗證（多指標）
    GridSearchCV,              # 網格搜尋
    RandomizedSearchCV,        # 隨機搜尋
    StratifiedKFold,           # 分層 K 折
    KFold,                     # K 折
    TimeSeriesSplit,           # 時間序列分割
    learning_curve,            # 學習曲線
    validation_curve,          # 驗證曲線
)

# === 前處理 ===
from sklearn.preprocessing import (
    StandardScaler,            # 標準化 (mean=0, std=1)
    MinMaxScaler,              # 最小最大縮放 [0, 1]
    RobustScaler,              # 穩健縮放（對異常值不敏感）
    LabelEncoder,              # 標籤編碼 (0, 1, 2...)
    OneHotEncoder,             # 獨熱編碼
    OrdinalEncoder,            # 有序編碼
    PolynomialFeatures,        # 多項式特徵
    Binarizer,                 # 二值化
)

# === 缺失值處理 ===
from sklearn.impute import (
    SimpleImputer,             # 簡單填補 (mean/median/mode)
    KNNImputer,                # KNN 填補
)

# === 特徵選擇 ===
from sklearn.feature_selection import (
    SelectKBest,               # 選擇 K 個最佳特徵
    f_classif,                 # ANOVA F 值（分類）
    f_regression,              # F 值（回歸）
    mutual_info_classif,       # 互資訊（分類）
    RFE,                       # 遞迴特徵消除
)

# === Pipeline ===
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.compose import ColumnTransformer

# === 分類模型 ===
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import (
    RandomForestClassifier,
    GradientBoostingClassifier,
    AdaBoostClassifier,
    BaggingClassifier,
    VotingClassifier,
    StackingClassifier,
)
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier
from sklearn.naive_bayes import GaussianNB

# === 回歸模型 ===
from sklearn.linear_model import (
    LinearRegression,
    Ridge,
    Lasso,
    ElasticNet,
)
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import (
    RandomForestRegressor,
    GradientBoostingRegressor,
)
from sklearn.svm import SVR
from sklearn.neighbors import KNeighborsRegressor

# === 分群模型 ===
from sklearn.cluster import (
    KMeans,
    DBSCAN,
    AgglomerativeClustering,
)

# === 降維 ===
from sklearn.decomposition import PCA, TruncatedSVD

# === 評估指標 ===
from sklearn.metrics import (
    # 分類
    accuracy_score, precision_score, recall_score, f1_score,
    classification_report, confusion_matrix,
    roc_auc_score, roc_curve,
    precision_recall_curve, average_precision_score,
    log_loss,
    # 回歸
    mean_squared_error, mean_absolute_error, r2_score,
    mean_absolute_percentage_error,
    # 分群
    silhouette_score, calinski_harabasz_score,
    adjusted_rand_score, normalized_mutual_info_score,
)
```

---

## A.2 Estimator API 速查

所有 scikit-learn 的模型都遵循統一的 API：

```
+-----------------------------------------------------------+
|                  scikit-learn Estimator API                 |
+-----------------------------------------------------------+
|                                                             |
|  所有模型：                                                 |
|    model = ModelClass(**params)   # 建立模型                |
|    model.get_params()             # 查看參數                |
|    model.set_params(**params)     # 設定參數                |
|                                                             |
|  監督式學習（分類 / 回歸）：                                |
|    model.fit(X_train, y_train)    # 訓練模型                |
|    model.predict(X_test)          # 預測                    |
|    model.score(X_test, y_test)    # 評估（accuracy/R2）     |
|    model.predict_proba(X_test)    # 預測機率（分類限定）    |
|    model.decision_function(X)     # 決策函數值              |
|                                                             |
|  非監督式學習（分群 / 降維）：                              |
|    model.fit(X)                   # 訓練                    |
|    model.predict(X)               # 預測群標（分群）        |
|    model.transform(X)             # 轉換（降維）            |
|    model.fit_transform(X)         # 訓練 + 轉換             |
|    model.fit_predict(X)           # 訓練 + 預測（分群）     |
|                                                             |
|  前處理 / 轉換器：                                          |
|    transformer.fit(X)             # 學習轉換規則            |
|    transformer.transform(X)       # 套用轉換                |
|    transformer.fit_transform(X)   # 學習 + 套用             |
|    transformer.inverse_transform(X) # 反轉換                |
|                                                             |
+-----------------------------------------------------------+

⚠️  關鍵規則：
    fit() 只用 training data！
    transform() 可以用在 train 和 test 上。
    絕對不要在 test data 上 fit！
```

---

## A.3 模型選擇指南

### 你該用什麼模型？（ASCII 決策流程圖）

```
                        開始
                         |
                 資料量 > 50 筆？
                /              \
              No                Yes
              |                  |
         取得更多資料        你要預測什麼？
                            /     |      \
                      類別值    數值    群組/結構
                        |        |          |
                     [分類]    [回歸]     [分群]
                        |        |          |
                        v        v          v
                  (見分類流程) (見回歸流程) (見分群流程)


=== 分類流程 ===

  資料量 < 10萬？
  /             \
Yes              No
 |                |
 |           SGDClassifier
 |           或 Linear SVC
 |
 文字資料？
 /        \
Yes        No
 |          |
Naive      資料量 < 1萬？
Bayes      /            \
          Yes            No
           |              |
      KNN 或 SVC      SVC (kernel)
      (試兩個)        或 Ensemble
           |              |
      不 work？       不 work？
           |              |
      SVC(kernel)    Ensemble:
      或 Ensemble    RF / GBM
           |
      不 work？
           |
      Ensemble:
      RF / GBM


=== 回歸流程 ===

  特徵數 重要？
  /           \
Yes            No
 |              |
Lasso /        資料量 < 10萬？
ElasticNet     /            \
              Yes            No
               |              |
          Ridge / SVR     SGDRegressor
          / Ensemble
               |
          不 work？
               |
          Ensemble:
          RF / GBM


=== 分群流程 ===

  知道群數？
  /        \
Yes         No
 |           |
 |       DBSCAN
 |       (自動偵測)
 |
 資料量 < 1萬？
 /           \
Yes           No
 |             |
KMeans 或    MiniBatchKMeans
凝聚式分群
```

### 快速選擇表

| 情境 | 推薦模型 | 原因 |
|------|---------|------|
| 第一次嘗試（分類） | Logistic Regression | 快速、可解釋、當作 baseline |
| 第一次嘗試（回歸） | Ridge Regression | 穩健、有正則化 |
| 需要高準確度 | Gradient Boosting | 通常表現最好 |
| 需要可解釋性 | Decision Tree / LR | 直接可讀的規則/係數 |
| 高維度資料 | Lasso / ElasticNet | 自動特徵選擇 |
| 不平衡資料 | RF (balanced) / GBM | 支援 class_weight |
| 異常值多 | Random Forest | 對異常值穩健 |
| 少量資料 | SVM / KNN | 不需要大量資料 |
| 文字資料 | Naive Bayes / SVM | 文字分類的經典選擇 |

---

## A.4 前處理工具速查

| 工具 | 用途 | 何時使用 | 範例 |
|------|------|---------|------|
| `StandardScaler` | 標準化 (z-score) | SVM, KNN, LR, PCA | `(x - mean) / std` |
| `MinMaxScaler` | 縮放至 [0,1] | 神經網路, 影像 | `(x - min) / (max - min)` |
| `RobustScaler` | 穩健縮放 | 有異常值時 | `(x - median) / IQR` |
| `OneHotEncoder` | 獨熱編碼 | 無序類別變數 | 紅→[1,0,0] 藍→[0,1,0] |
| `OrdinalEncoder` | 有序編碼 | 有序類別變數 | 小→0, 中→1, 大→2 |
| `LabelEncoder` | 標籤編碼 | 目標變數 y | cat→0, dog→1 |
| `SimpleImputer` | 填補缺失值 | 有缺失值時 | 填 mean/median/mode |
| `KNNImputer` | KNN 填補 | 缺失值有模式 | 用相似樣本的值填補 |
| `PolynomialFeatures` | 多項式特徵 | 非線性關係 | x1, x2 → x1, x2, x1*x2, x1^2... |
| `SelectKBest` | 特徵選擇 | 特徵太多 | 選 K 個最佳特徵 |
| `PCA` | 降維 | 高維度 | 50 維 → 10 維 |

### 什麼模型需要什麼前處理？

```
+--------------------+--------+--------+--------+--------+
|                    | 標準化  | 編碼   | 缺失值  | 特徵   |
| 模型               | 縮放   | 類別   | 處理    | 選擇   |
+--------------------+--------+--------+--------+--------+
| Linear Regression  | 建議   | 必要   | 必要   | 建議   |
| Logistic Regression| 建議   | 必要   | 必要   | 建議   |
| SVM                | 必要   | 必要   | 必要   | 建議   |
| KNN                | 必要   | 必要   | 必要   | 建議   |
| Decision Tree      | 不需要 | 建議   | 可處理 | 不需要 |
| Random Forest      | 不需要 | 建議   | 可處理 | 不需要 |
| Gradient Boosting  | 不需要 | 建議   | 可處理 | 不需要 |
| Naive Bayes        | 不需要 | 必要   | 必要   | 建議   |
| PCA                | 必要   | 必要   | 必要   | N/A    |
| KMeans             | 必要   | 必要   | 必要   | 建議   |
+--------------------+--------+--------+--------+--------+

必要 = 不做會嚴重影響結果
建議 = 做了通常表現更好
不需要 = 做不做差別不大
可處理 = 模型本身可以處理
```

---

## A.5 評估指標速查

### 分類指標

| 指標 | 公式 | 適用場景 | 範圍 |
|------|------|---------|------|
| Accuracy | (TP+TN) / Total | 平衡資料 | [0, 1] |
| Precision | TP / (TP+FP) | FP 代價高（垃圾郵件） | [0, 1] |
| Recall | TP / (TP+FN) | FN 代價高（癌症偵測） | [0, 1] |
| F1-Score | 2*P*R / (P+R) | 需要平衡 P 和 R | [0, 1] |
| AUC-ROC | ROC 曲線下面積 | 整體排序能力 | [0, 1] |
| Log Loss | -mean(y*log(p)) | 機率校準 | [0, +inf) |
| AP (Avg Precision) | PR 曲線下面積 | 不平衡資料 | [0, 1] |

```
混淆矩陣 (Confusion Matrix) 速查：

                    Predicted
                 Neg         Pos
              +----------+----------+
Actual  Neg   |    TN    |    FP    |   ← FP: 型一錯誤
              |          |          |        (誤報)
              +----------+----------+
Actual  Pos   |    FN    |    TP    |   ← FN: 型二錯誤
              |          |          |        (漏報)
              +----------+----------+

Precision = TP / (TP + FP)   "預測為正的，有多少真的是正？"
Recall    = TP / (TP + FN)   "真正為正的，有多少被抓到？"
F1        = 2 * P * R / (P + R)  "P 和 R 的調和平均"
```

### 回歸指標

| 指標 | 公式概念 | 適用場景 | 最佳值 |
|------|---------|---------|--------|
| MSE | 平方誤差平均 | 懲罰大誤差 | 0 |
| RMSE | sqrt(MSE) | 和 y 同單位 | 0 |
| MAE | 絕對誤差平均 | 對異常值穩健 | 0 |
| R2 | 1 - SS_res/SS_tot | 解釋力 | 1 |
| MAPE | 百分比誤差 | 跨尺度比較 | 0% |

```
R2 Score 解讀：
  1.0  = 完美預測
  0.7+ = 好
  0.5  = 普通
  0.0  = 跟用平均值預測一樣差
  <0   = 比用平均值還差（模型有問題！）
```

### 分群指標

| 指標 | 需要真實標籤？ | 範圍 | 最佳值 |
|------|-------------|------|--------|
| Silhouette Score | 否 | [-1, 1] | 1 |
| Calinski-Harabasz | 否 | [0, +inf) | 越大越好 |
| Adjusted Rand Index | 是 | [-1, 1] | 1 |
| NMI | 是 | [0, 1] | 1 |
| Inertia | 否 | [0, +inf) | 越小越好 |

---

## A.6 Pipeline 建構模式

### 基本 Pipeline

```python
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression

# 方法 1：Pipeline（自訂步驟名稱）
pipe = Pipeline([
    ('scaler', StandardScaler()),
    ('classifier', LogisticRegression())
])

# 方法 2：make_pipeline（自動命名）
pipe = make_pipeline(
    StandardScaler(),
    LogisticRegression()
)

# 使用方式和普通模型一樣
pipe.fit(X_train, y_train)
pipe.predict(X_test)
pipe.score(X_test, y_test)
```

### 混合型前處理 Pipeline（最常用）

```python
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline

numeric_features = ['age', 'income', 'score']
categorical_features = ['gender', 'city', 'plan']

# 數值特徵的處理流程
numeric_transformer = Pipeline([
    ('imputer', SimpleImputer(strategy='median')),
    ('scaler', StandardScaler())
])

# 類別特徵的處理流程
categorical_transformer = Pipeline([
    ('imputer', SimpleImputer(strategy='most_frequent')),
    ('encoder', OneHotEncoder(handle_unknown='ignore'))
])

# 組合
preprocessor = ColumnTransformer([
    ('num', numeric_transformer, numeric_features),
    ('cat', categorical_transformer, categorical_features)
])

# 完整 Pipeline = 前處理 + 模型
full_pipeline = Pipeline([
    ('preprocessor', preprocessor),
    ('classifier', LogisticRegression(max_iter=1000))
])

# 訓練與預測
full_pipeline.fit(X_train, y_train)
y_pred = full_pipeline.predict(X_test)
```

---

## A.7 Cross-Validation 模式

```python
from sklearn.model_selection import (
    cross_val_score,
    cross_validate,
    StratifiedKFold,
    KFold,
    TimeSeriesSplit
)

# === 基本用法 ===
scores = cross_val_score(model, X, y, cv=5, scoring='f1')
print(f"F1: {scores.mean():.4f} (+/- {scores.std():.4f})")

# === 多指標 ===
results = cross_validate(
    model, X, y, cv=5,
    scoring=['accuracy', 'f1', 'roc_auc'],
    return_train_score=True
)

# === 分層 K 折（分類任務推薦） ===
skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
scores = cross_val_score(model, X, y, cv=skf, scoring='f1')

# === 時間序列 ===
tscv = TimeSeriesSplit(n_splits=5)
scores = cross_val_score(model, X, y, cv=tscv, scoring='neg_mean_squared_error')

# === 重複分層 K 折（更穩定） ===
from sklearn.model_selection import RepeatedStratifiedKFold
rskf = RepeatedStratifiedKFold(n_splits=5, n_repeats=3, random_state=42)
scores = cross_val_score(model, X, y, cv=rskf, scoring='f1')
```

---

## A.8 GridSearchCV / RandomizedSearchCV 模式

```python
from sklearn.model_selection import GridSearchCV, RandomizedSearchCV
from scipy.stats import uniform, randint

# === GridSearchCV（窮舉搜尋） ===
# 適用：參數空間小（< 100 組合）

param_grid = {
    'classifier__C': [0.01, 0.1, 1, 10, 100],
    'classifier__penalty': ['l1', 'l2'],
}

grid = GridSearchCV(
    pipeline,
    param_grid,
    cv=5,                  # 5 折交叉驗證
    scoring='f1',          # 用 F1 選最佳
    n_jobs=-1,             # 全部 CPU
    verbose=1,             # 顯示進度
    return_train_score=True
)
grid.fit(X_train, y_train)

print(f"Best params: {grid.best_params_}")
print(f"Best F1:     {grid.best_score_:.4f}")
best_model = grid.best_estimator_


# === RandomizedSearchCV（隨機搜尋） ===
# 適用：參數空間大（> 100 組合）

param_dist = {
    'classifier__n_estimators': randint(50, 500),
    'classifier__max_depth': randint(3, 15),
    'classifier__learning_rate': uniform(0.01, 0.3),
    'classifier__min_samples_leaf': randint(1, 50),
}

random_search = RandomizedSearchCV(
    pipeline,
    param_dist,
    n_iter=100,             # 隨機嘗試 100 組
    cv=5,
    scoring='f1',
    n_jobs=-1,
    random_state=42,
    verbose=1
)
random_search.fit(X_train, y_train)

print(f"Best params: {random_search.best_params_}")
print(f"Best F1:     {random_search.best_score_:.4f}")
```

### GridSearchCV vs RandomizedSearchCV

```
+-------------------+-------------------+-------------------+
|                   | GridSearchCV      | RandomizedSearchCV|
+-------------------+-------------------+-------------------+
| 搜尋策略           | 窮舉所有組合       | 隨機抽樣          |
| 適用場景           | 參數少、範圍小     | 參數多、範圍大     |
| 計算時間           | 指數成長          | 線性成長（可控）    |
| 保證找到最佳       | 是（在給定範圍內）  | 否（但通常夠好）   |
| 建議              | 先用 Random       | 縮小範圍後用 Grid  |
|                   | 找大方向          | 精細調整           |
+-------------------+-------------------+-------------------+
```

---

## A.9 常用超參數速查

### 分類模型

```
Logistic Regression
+-------------------+-------------------+-------------------+
| 參數               | 常用值             | 說明              |
+-------------------+-------------------+-------------------+
| C                  | 0.01, 0.1, 1, 10  | 正則化強度 (越小越強)|
| penalty            | 'l1', 'l2'        | 正則化類型         |
| class_weight       | None, 'balanced'  | 處理不平衡         |
| max_iter           | 1000              | 最大迭代次數       |
| solver             | 'lbfgs', 'saga'   | 優化算法           |
+-------------------+-------------------+-------------------+

Random Forest
+-------------------+-------------------+-------------------+
| 參數               | 常用值             | 說明              |
+-------------------+-------------------+-------------------+
| n_estimators       | 100, 200, 500     | 樹的數量           |
| max_depth          | 5, 10, 20, None   | 最大深度           |
| min_samples_split  | 2, 5, 10          | 分裂最小樣本數      |
| min_samples_leaf   | 1, 2, 5           | 葉節點最小樣本數    |
| max_features       | 'sqrt', 'log2'    | 每次分裂考慮的特徵  |
| class_weight       | None, 'balanced'  | 處理不平衡         |
+-------------------+-------------------+-------------------+

Gradient Boosting
+-------------------+-------------------+-------------------+
| 參數               | 常用值             | 說明              |
+-------------------+-------------------+-------------------+
| n_estimators       | 100, 200, 500     | 弱學習器數量       |
| learning_rate      | 0.01, 0.05, 0.1   | 學習率（和 n_est 反比）|
| max_depth          | 3, 5, 7           | 每棵樹的最大深度    |
| min_samples_leaf   | 5, 10, 20         | 葉節點最小樣本      |
| subsample          | 0.8, 0.9, 1.0     | 每棵樹的樣本比例    |
+-------------------+-------------------+-------------------+

SVM (SVC)
+-------------------+-------------------+-------------------+
| 參數               | 常用值             | 說明              |
+-------------------+-------------------+-------------------+
| C                  | 0.1, 1, 10, 100   | 正則化（越大越少正則化）|
| kernel             | 'rbf','linear','poly'| 核函數           |
| gamma              | 'scale', 'auto'   | RBF 核的寬度       |
| class_weight       | None, 'balanced'  | 處理不平衡         |
+-------------------+-------------------+-------------------+

KNN
+-------------------+-------------------+-------------------+
| 參數               | 常用值             | 說明              |
+-------------------+-------------------+-------------------+
| n_neighbors        | 3, 5, 7, 11       | 鄰居數             |
| weights            | 'uniform','distance'| 權重策略          |
| metric             | 'minkowski'       | 距離度量           |
| p                  | 1, 2              | 1=曼哈頓, 2=歐幾里得|
+-------------------+-------------------+-------------------+
```

### 回歸模型

```
Ridge / Lasso / ElasticNet
+-------------------+-------------------+-------------------+
| 參數               | 常用值             | 說明              |
+-------------------+-------------------+-------------------+
| alpha              | 0.01, 0.1, 1, 10  | 正則化強度         |
| l1_ratio (EN only) | 0.1, 0.5, 0.9     | L1 與 L2 的比例    |
+-------------------+-------------------+-------------------+
```

### 分群模型

```
KMeans
+-------------------+-------------------+-------------------+
| 參數               | 常用值             | 說明              |
+-------------------+-------------------+-------------------+
| n_clusters         | 2-10 (用肘部法)    | 群數              |
| init               | 'k-means++'       | 初始化方法         |
| n_init             | 10                | 重複初始化次數      |
| max_iter           | 300               | 最大迭代次數       |
+-------------------+-------------------+-------------------+

DBSCAN
+-------------------+-------------------+-------------------+
| 參數               | 常用值             | 說明              |
+-------------------+-------------------+-------------------+
| eps                | 依資料而定         | 鄰域半徑           |
| min_samples        | 5, 10             | 核心點最小鄰居數    |
| metric             | 'euclidean'       | 距離度量           |
+-------------------+-------------------+-------------------+
```

---

## A.10 常用程式碼片段

### 完整的分類 Pipeline（複製貼上即可用）

```python
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score, GridSearchCV
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import classification_report, roc_auc_score

# 1. 載入資料
# df = pd.read_csv('your_data.csv')
# X = df.drop('target', axis=1)
# y = df['target']

# 2. 定義特徵類型
# numeric_features = ['col1', 'col2']
# categorical_features = ['col3', 'col4']

# 3. 建立前處理
preprocessor = ColumnTransformer([
    ('num', Pipeline([
        ('imputer', SimpleImputer(strategy='median')),
        ('scaler', StandardScaler())
    ]), numeric_features),
    ('cat', Pipeline([
        ('imputer', SimpleImputer(strategy='most_frequent')),
        ('encoder', OneHotEncoder(handle_unknown='ignore'))
    ]), categorical_features)
])

# 4. 完整 Pipeline
pipeline = Pipeline([
    ('preprocessor', preprocessor),
    ('classifier', GradientBoostingClassifier(random_state=42))
])

# 5. 分割資料
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, stratify=y, random_state=42
)

# 6. Cross Validation
scores = cross_val_score(pipeline, X_train, y_train, cv=5, scoring='f1')
print(f"CV F1: {scores.mean():.4f} (+/- {scores.std():.4f})")

# 7. 超參數調整
param_grid = {
    'classifier__n_estimators': [100, 200],
    'classifier__max_depth': [3, 5, 7],
    'classifier__learning_rate': [0.05, 0.1],
}
grid = GridSearchCV(pipeline, param_grid, cv=5, scoring='f1', n_jobs=-1)
grid.fit(X_train, y_train)

# 8. 最終評估
best = grid.best_estimator_
y_pred = best.predict(X_test)
print(classification_report(y_test, y_pred))
print(f"AUC-ROC: {roc_auc_score(y_test, best.predict_proba(X_test)[:,1]):.4f}")
```

### 儲存與載入模型

```python
import joblib

# 儲存
joblib.dump(best_model, 'model.joblib')

# 載入
loaded_model = joblib.load('model.joblib')
predictions = loaded_model.predict(X_new)
```

---

## A.11 常見錯誤訊息與解法

```
+-------------------------------------------------------+
| 錯誤訊息                        | 解法                 |
+-------------------------------------------------------+
| ValueError: could not convert    | 檢查資料型態，       |
| string to float                 | 類別變數需要編碼      |
+-------------------------------------------------------+
| ValueError: Input contains NaN  | 處理缺失值           |
|                                 | (SimpleImputer)      |
+-------------------------------------------------------+
| ValueError: Found input         | 某些特徵有 inf 值，  |
| variables with inconsistent     | 或 train/test 的     |
| numbers of samples              | 欄位數不一致          |
+-------------------------------------------------------+
| ConvergenceWarning: lbfgs       | 增加 max_iter，      |
| failed to converge              | 或做標準化           |
+-------------------------------------------------------+
| ValueError: Unknown label type  | 檢查 y 的格式，      |
|                                 | 分類 vs 回歸搞混      |
+-------------------------------------------------------+
| ValueError: classifier does not | 該模型不支持          |
| support predict_proba           | predict_proba，       |
|                                 | 用 SVC 要設           |
|                                 | probability=True      |
+-------------------------------------------------------+
| NotFittedError                  | 忘記呼叫 fit() 了    |
+-------------------------------------------------------+
```

---

> 把這份參考卡列印出來，放在手邊。
> 等你用到不需要查的時候，你就真的學會了。

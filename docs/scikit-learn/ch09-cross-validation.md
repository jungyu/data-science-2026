# Chapter 9: 交叉驗證與模型評估 — 不能只跑一次，不能只看 Accuracy

> **第 9 週｜Cross-Validation & Model Evaluation**

---

## 🎯 本章目標

讀完這一章，你將能夠：

1. 理解為什麼單一的 train/test split 不夠可靠
2. 掌握 K-Fold Cross Validation 的原理
3. 用 `cross_val_score` 做交叉驗證
4. 理解 Stratified K-Fold 的重要性
5. 學會用 `classification_report` 看完整的評估指標
6. 搞懂 Precision、Recall、F1-Score 各代表什麼
7. 理解 PR Curve 和 ROC Curve 的差異和用途
8. 用 `GridSearchCV` 做超參數搜尋
9. 建立「不能只跑一次、不能只看 accuracy」的正確觀念

---

## 故事：那個「準確率 95%」的模型

小明在公司裡訓練了一個模型，興高采烈地跟主管報告：

> 「主管！我的模型準確率 95%！」

主管問：「你怎麼評估的？」

> 「我切了 70% 訓練、30% 測試，測試集準確率 95%！」

主管又問：「你只跑了一次？」

> 「...對。」

主管搖搖頭：「如果你換個 `random_state`，準確率可能掉到 85%。
你怎麼知道 95% 不是運氣好？」

```
        random_state=42     random_state=123    random_state=7

        準確率: 95%          準確率: 87%          準確率: 91%
              ^
              |
              你只看了這次，
              然後就跟主管說 95% 了
```

**這就是為什麼我們需要交叉驗證。**

---

## 💡 重點觀念：為什麼單次 Train/Test Split 不夠

```
問題 1：結果取決於「怎麼切」
  → 不同的 random_state 會得到不同的結果
  → 你看到的可能是「最好的情況」或「最差的情況」

問題 2：浪費資料
  → 30% 的資料只用來測試，沒有參與訓練
  → 資料量少的時候特別可惜

問題 3：無法估計「不確定性」
  → 單次結果無法告訴你模型表現的「穩定度」
  → 你不知道 95% 的背後有多少變異
```

---

## K-Fold Cross Validation：跑 K 次，取平均

K-Fold 的做法很直覺：

1. 把資料分成 K 等份（通常 K=5 或 K=10）
2. 每次用 K-1 份做訓練，剩下 1 份做測試
3. 重複 K 次，每份資料都當過一次測試集
4. 取 K 次結果的**平均值**和**標準差**

```
5-Fold Cross Validation：

Fold 1: [TEST ] [Train] [Train] [Train] [Train]  → 準確率: 0.93
Fold 2: [Train] [TEST ] [Train] [Train] [Train]  → 準確率: 0.95
Fold 3: [Train] [Train] [TEST ] [Train] [Train]  → 準確率: 0.91
Fold 4: [Train] [Train] [Train] [TEST ] [Train]  → 準確率: 0.94
Fold 5: [Train] [Train] [Train] [Train] [TEST ]  → 準確率: 0.92

平均: 0.930 ± 0.015
```

現在你可以說：「我的模型準確率是 **93.0% ± 1.5%**」—
這比說「95%」有意義多了！

---

## 用 scikit-learn 做交叉驗證

```python
from sklearn.model_selection import cross_val_score
from sklearn.ensemble import RandomForestClassifier
from sklearn.datasets import load_iris

# 載入資料
iris = load_iris()
X, y = iris.data, iris.target

# 建立模型（不需要先 fit！cross_val_score 會自動做）
rf = RandomForestClassifier(n_estimators=100, random_state=42)

# 5-Fold 交叉驗證
scores = cross_val_score(rf, X, y, cv=5, scoring='accuracy')

print(f"每一折的準確率: {scores}")
print(f"平均準確率:     {scores.mean():.4f}")
print(f"標準差:         {scores.std():.4f}")
print(f"報告:           {scores.mean():.4f} ± {scores.std():.4f}")
```

輸出可能像這樣：

```
每一折的準確率: [0.9667 0.9667 0.9333 0.9667 1.0000]
平均準確率:     0.9667
標準差:         0.0211
報告:           0.9667 ± 0.0211
```

就這麼簡單！一行 `cross_val_score` 就搞定了。

---

## 🧠 動動腦

如果 K = N（N 是資料總數），那每次只用 1 筆資料做測試。
這叫做 **Leave-One-Out Cross Validation (LOOCV)**。

想想看：LOOCV 的優點和缺點分別是什麼？
（提示：最充分利用資料 vs. 計算成本）

---

## Stratified K-Fold：處理類別不平衡

普通的 K-Fold 有一個問題：如果類別分布不均，某一折可能全是同一類。

```
假設資料有 90% 是類別 A，10% 是類別 B：

普通 K-Fold 可能的切法（運氣不好的話）：
Fold 1: [AAAA] [AABA] [AABA] [AABA] [ABBB]
         ← 這一折幾乎沒有 B！測出來的結果不準！

Stratified K-Fold 保證每一折的類別比例都一樣：
Fold 1: [AAB ] [AAB ] [AAB ] [AAB ] [AAB ]
         ← 每一折都有 90% A, 10% B，公平！
```

```python
from sklearn.model_selection import StratifiedKFold, cross_val_score

# 方法 1：用 StratifiedKFold 物件
skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
scores = cross_val_score(rf, X, y, cv=skf, scoring='accuracy')

# 方法 2：其實 cross_val_score 對分類問題預設就用 StratifiedKFold！
# 所以 cv=5 等同於 StratifiedKFold(n_splits=5)
scores = cross_val_score(rf, X, y, cv=5, scoring='accuracy')  # 自動 Stratified
```

💡 **好消息：`cross_val_score` 對分類問題預設就使用 StratifiedKFold。**
你不需要特別設定！

---

## 💡 重點觀念：不能只看 Accuracy

準確率（Accuracy）有一個嚴重的盲點。看這個例子：

```
信用卡詐騙偵測：
  正常交易: 9,900 筆 (99%)
  詐騙交易:   100 筆 (1%)

如果我的模型「永遠預測正常」：
  準確率 = 9900 / 10000 = 99%  ← 哇！99%！

但是...它一筆詐騙都抓不到！這個模型根本沒用！
```

所以我們需要更多元的評估指標。

---

## Classification Report：一次看清所有指標

```python
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from sklearn.ensemble import RandomForestClassifier
from sklearn.datasets import load_breast_cancer

# 載入乳癌資料集
cancer = load_breast_cancer()
X, y = cancer.data, cancer.target

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.3, random_state=42, stratify=y
)

rf = RandomForestClassifier(n_estimators=100, random_state=42)
rf.fit(X_train, y_train)
y_pred = rf.predict(X_test)

print(classification_report(y_test, y_pred, target_names=['惡性', '良性']))
```

輸出：

```
              precision    recall  f1-score   support

          惡性       0.95      0.95      0.95        63
          良性       0.97      0.97      0.97       108

    accuracy                           0.96       171
   macro avg       0.96      0.96      0.96       171
weighted avg       0.96      0.96      0.96       171
```

### 這些指標到底在講什麼？

用一個比喻來解釋：

```
你是一個機場安檢員，要找出行李中的違禁品。

                    實際有違禁品    實際沒有違禁品
                   ┌─────────────┬───────────────┐
  你說「有」       │ TP (抓到了!) │ FP (誤報冤枉) │
                   ├─────────────┼───────────────┤
  你說「沒有」     │ FN (漏掉了!) │ TN (正確放行) │
                   └─────────────┴───────────────┘

TP = True Positive   (有，你說有 ✅)
FP = False Positive  (沒有，你說有 ❌)  ← 冤枉好人
FN = False Negative  (有，你說沒有 ❌)  ← 放過壞人！
TN = True Negative   (沒有，你說沒有 ✅)
```

```
Precision（精確率）= TP / (TP + FP)
  「你說是違禁品的東西中，有多少真的是？」
  → 高 Precision = 很少冤枉好人

Recall（召回率）= TP / (TP + FN)
  「所有違禁品中，你抓到了多少？」
  → 高 Recall = 很少漏掉壞人

F1-Score = 2 × (Precision × Recall) / (Precision + Recall)
  → Precision 和 Recall 的調和平均數
  → 兩者的平衡指標
```

---

## ⚠️ 常見陷阱：Precision vs. Recall 的取捨

你不可能同時讓 Precision 和 Recall 都達到 100%。
它們之間存在**權衡（trade-off）**：

```
提高門檻（保守判斷）：
  → Precision 上升 ↑（更少冤枉）
  → Recall 下降 ↓（更多漏網）

降低門檻（寬鬆判斷）：
  → Precision 下降 ↓（更多冤枉）
  → Recall 上升 ↑（更少漏網）
```

**該重視 Precision 還是 Recall？取決於你的應用場景：**

```
+--------------------+-------------+-------------+
| 場景               | 重視哪個    | 為什麼      |
+--------------------+-------------+-------------+
| 癌症診斷           | Recall      | 不能漏掉病人|
| 垃圾信件過濾       | Precision   | 不能誤刪信  |
| 詐騙偵測           | Recall      | 不能放過騙子|
| 推薦系統           | Precision   | 推爛的更煩  |
| 自駕車行人偵測     | Recall      | 不能漏掉行人|
+--------------------+-------------+-------------+
```

---

## PR Curve 和 ROC Curve

### PR Curve（Precision-Recall Curve）

PR Curve 顯示 Precision 和 Recall 在不同門檻下的關係。

```python
from sklearn.metrics import precision_recall_curve, average_precision_score
import matplotlib.pyplot as plt

# 取得機率預測（而不是分類結果）
y_scores = rf.predict_proba(X_test)[:, 1]

# 計算 PR Curve
precision, recall, thresholds = precision_recall_curve(y_test, y_scores)
ap = average_precision_score(y_test, y_scores)

# 畫圖
plt.figure(figsize=(8, 6))
plt.plot(recall, precision, 'b-', linewidth=2, label=f'RF (AP={ap:.3f})')
plt.xlabel('Recall（召回率）')
plt.ylabel('Precision（精確率）')
plt.title('Precision-Recall Curve')
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()
```

```
PR Curve 示意圖：

Precision
   1.0 |*****
       |     ****
       |         ***
   0.5 |            ***
       |               ****
       |                   *****
   0.0 +-------------------------
       0.0              0.5    1.0
                    Recall

→ 曲線越靠近右上角越好
→ AP (Average Precision) 越高越好
→ 在類別不平衡時比 ROC 更有參考價值
```

### ROC Curve（Receiver Operating Characteristic Curve）

ROC Curve 顯示 True Positive Rate 和 False Positive Rate 的關係。

```python
from sklearn.metrics import roc_curve, roc_auc_score

# 計算 ROC Curve
fpr, tpr, thresholds = roc_curve(y_test, y_scores)
auc = roc_auc_score(y_test, y_scores)

# 畫圖
plt.figure(figsize=(8, 6))
plt.plot(fpr, tpr, 'b-', linewidth=2, label=f'RF (AUC={auc:.3f})')
plt.plot([0, 1], [0, 1], 'r--', label='隨機猜測 (AUC=0.5)')
plt.xlabel('False Positive Rate（偽陽率）')
plt.ylabel('True Positive Rate（真陽率）')
plt.title('ROC Curve')
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()
```

```
ROC Curve 示意圖：

TPR (True Positive Rate)
   1.0 |        ********
       |      **
       |    **
   0.5 |  **     /
       | *      / ← 隨機猜測（對角線）
       |*      /
   0.0 +------/----------
       0.0   0.5       1.0
       FPR (False Positive Rate)

→ 曲線越靠近左上角越好
→ AUC (Area Under Curve) 越接近 1.0 越好
→ AUC = 0.5 表示跟隨機猜測一樣差
```

### PR Curve vs. ROC Curve：什麼時候用哪個？

```
+---------------------+----------------------------+
| PR Curve            | ROC Curve                  |
+---------------------+----------------------------+
| 類別不平衡時更敏感  | 類別平衡時表現好           |
| 關注正類別的表現    | 綜合看兩個類別             |
| 醫療、詐騙偵測     | 一般分類問題               |
| AP 是關鍵指標       | AUC 是關鍵指標             |
+---------------------+----------------------------+

經驗法則：
  類別不平衡 → 用 PR Curve
  類別平衡   → 用 ROC Curve
  不確定     → 兩個都看
```

---

## 公平比較多個模型

交叉驗證最棒的用途之一：**公平地比較不同的模型。**

```python
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier
from sklearn.model_selection import cross_val_score
from sklearn.datasets import load_breast_cancer
import numpy as np

# 載入資料
cancer = load_breast_cancer()
X, y = cancer.data, cancer.target

# 定義要比較的模型
models = {
    'Logistic Regression': LogisticRegression(max_iter=10000),
    'Decision Tree':       DecisionTreeClassifier(random_state=42),
    'Random Forest':       RandomForestClassifier(n_estimators=100, random_state=42),
    'SVM':                 SVC(random_state=42),
    'KNN':                 KNeighborsClassifier(),
}

# 用 5-Fold 交叉驗證比較
print(f"{'模型':<25} {'平均準確率':>10} {'標準差':>10}")
print("=" * 50)

results = {}
for name, model in models.items():
    scores = cross_val_score(model, X, y, cv=5, scoring='accuracy')
    results[name] = scores
    print(f"{name:<25} {scores.mean():>10.4f} {scores.std():>10.4f}")
```

可能的輸出：

```
模型                          平均準確率       標準差
==================================================
Logistic Regression           0.9508     0.0260
Decision Tree                 0.9226     0.0229
Random Forest                 0.9614     0.0200
SVM                           0.9192     0.0350
KNN                           0.9261     0.0193
```

現在你可以有信心地說：「在這個資料集上，Random Forest 表現最好，
而且標準差也最小，代表它最穩定。」

---

## 🧠 動動腦

在上面的比較中，SVM 的準確率最低（0.9192），標準差也最大（0.0350）。
但 SVM 理論上是很強的演算法。為什麼在這裡表現這麼差？

（提示：SVM 對特徵尺度**非常**敏感。我們有做 `StandardScaler` 嗎？）

---

## GridSearchCV：自動找最佳超參數

手動調參太累了。`GridSearchCV` 會幫你**窮舉所有超參數組合**，
用交叉驗證找出最好的那組。

```python
from sklearn.model_selection import GridSearchCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.datasets import load_breast_cancer

# 載入資料
cancer = load_breast_cancer()
X, y = cancer.data, cancer.target

# 定義要搜尋的超參數空間
param_grid = {
    'n_estimators': [50, 100, 200],
    'max_depth': [3, 5, 10, None],
    'min_samples_leaf': [1, 2, 5],
    'max_features': ['sqrt', 'log2'],
}

# 計算總共要嘗試幾種組合
n_combinations = 3 * 4 * 3 * 2  # = 72 種組合
print(f"共 {n_combinations} 種組合 × 5 折 = {n_combinations * 5} 次訓練")

# 建立 GridSearchCV
grid_search = GridSearchCV(
    estimator=RandomForestClassifier(random_state=42),
    param_grid=param_grid,
    cv=5,                  # 5-Fold 交叉驗證
    scoring='accuracy',    # 評估指標
    n_jobs=-1,             # 平行化！
    verbose=1              # 顯示進度
)

# 執行搜尋
grid_search.fit(X, y)

# 查看結果
print(f"\n最佳參數: {grid_search.best_params_}")
print(f"最佳交叉驗證準確率: {grid_search.best_score_:.4f}")
```

```
GridSearchCV 的運作方式：

超參數空間：
  n_estimators:   [50, 100, 200]
  max_depth:      [3, 5, 10, None]
  min_samples_leaf: [1, 2, 5]
  max_features:   ['sqrt', 'log2']

  → 3 × 4 × 3 × 2 = 72 種組合

每種組合做 5-Fold CV：
  → 72 × 5 = 360 次模型訓練

找出平均準確率最高的那組：
  → 最佳參數: {'max_depth': 10, 'max_features': 'sqrt',
               'min_samples_leaf': 1, 'n_estimators': 200}
  → 最佳準確率: 0.9649
```

### 用最佳模型做預測

```python
# grid_search.best_estimator_ 就是用最佳參數訓練好的模型
best_model = grid_search.best_estimator_

# 直接用它來預測
from sklearn.model_selection import train_test_split

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.3, random_state=42, stratify=y
)

# 重新用最佳參數在訓練集上訓練
best_model.fit(X_train, y_train)
print(f"測試集準確率: {best_model.score(X_test, y_test):.4f}")
```

---

## ⚠️ 常見陷阱

### 陷阱 1：用測試集來選模型

```
❌ 錯誤做法：
  1. 切 train/test
  2. 在 train 上訓練多個模型
  3. 在 test 上選表現最好的 ← 這等於用 test 來做決策！
  4. 報告 test 上的結果 ← 結果偏樂觀！

✅ 正確做法：
  1. 切 train/test
  2. 在 train 上用交叉驗證選最好的模型和超參數
  3. 最後用 test 做最終評估（只看一次！）
  4. 報告 test 上的結果 ← 公正無偏的結果
```

### 陷阱 2：在整個資料集上做 GridSearchCV 然後報告 best_score_

```
⚠️ 如果你對整個資料集（包含測試集）做 GridSearchCV，
   best_score_ 就有「資訊洩漏」的風險。

正確流程：
  1. 先切出測試集（不碰它）
  2. 在訓練集上做 GridSearchCV
  3. 用最佳模型在測試集上做最終評估
```

### 陷阱 3：GridSearchCV 的計算量爆炸

```
如果你有 5 個超參數，每個有 5 個候選值：
  5^5 = 3125 種組合
  × 5 折 = 15,625 次訓練！

解決方案：
  → RandomizedSearchCV：隨機抽樣超參數組合
  → 先用粗搜尋縮小範圍，再用細搜尋精調
  → 用更少的折數（cv=3 而不是 cv=10）
```

```python
from sklearn.model_selection import RandomizedSearchCV
from scipy.stats import randint, uniform

# 用隨機分布定義超參數空間
param_distributions = {
    'n_estimators': randint(50, 500),
    'max_depth': randint(3, 20),
    'min_samples_leaf': randint(1, 10),
    'max_features': ['sqrt', 'log2'],
}

# RandomizedSearchCV：只隨機試 50 種組合
random_search = RandomizedSearchCV(
    estimator=RandomForestClassifier(random_state=42),
    param_distributions=param_distributions,
    n_iter=50,             # 只試 50 種（而不是窮舉所有）
    cv=5,
    scoring='accuracy',
    n_jobs=-1,
    random_state=42
)

random_search.fit(X, y)
print(f"最佳參數: {random_search.best_params_}")
print(f"最佳準確率: {random_search.best_score_:.4f}")
```

---

## 完整的模型評估工作流程

把這一章學到的所有東西串起來：

```python
import numpy as np
from sklearn.datasets import load_breast_cancer
from sklearn.model_selection import (
    train_test_split, cross_val_score, GridSearchCV, StratifiedKFold
)
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, roc_auc_score

# ===== Step 1: 載入資料並切出最終測試集 =====
cancer = load_breast_cancer()
X, y = cancer.data, cancer.target

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

print(f"訓練集: {X_train.shape[0]} 筆")
print(f"測試集: {X_test.shape[0]} 筆\n")

# ===== Step 2: 用交叉驗證比較候選模型 =====
candidates = {
    'Logistic Regression': LogisticRegression(max_iter=10000),
    'Random Forest': RandomForestClassifier(n_estimators=100, random_state=42),
}

print("=== 候選模型比較（5-Fold CV）===")
print(f"{'模型':<25} {'平均準確率':>10} {'標準差':>8}")
print("-" * 45)

for name, model in candidates.items():
    scores = cross_val_score(model, X_train, y_train, cv=5, scoring='accuracy')
    print(f"{name:<25} {scores.mean():>10.4f} {scores.std():>8.4f}")

# ===== Step 3: 對最佳候選模型做超參數調整 =====
print("\n=== GridSearchCV 超參數搜尋 ===")

param_grid = {
    'n_estimators': [100, 200],
    'max_depth': [5, 10, None],
    'min_samples_leaf': [1, 2, 5],
}

grid_search = GridSearchCV(
    RandomForestClassifier(random_state=42),
    param_grid=param_grid,
    cv=StratifiedKFold(n_splits=5, shuffle=True, random_state=42),
    scoring='accuracy',
    n_jobs=-1
)
grid_search.fit(X_train, y_train)

print(f"最佳參數: {grid_search.best_params_}")
print(f"最佳 CV 準確率: {grid_search.best_score_:.4f}")

# ===== Step 4: 最終評估（只在測試集上跑一次！）=====
print("\n=== 最終評估（測試集）===")

best_model = grid_search.best_estimator_
y_pred = best_model.predict(X_test)
y_proba = best_model.predict_proba(X_test)[:, 1]

print(classification_report(
    y_test, y_pred,
    target_names=['惡性', '良性']
))
print(f"ROC AUC: {roc_auc_score(y_test, y_proba):.4f}")
```

---

## ❓ 沒有笨問題

**Q: K-Fold 的 K 要設多少？**
A: 最常見的是 K=5 或 K=10。K=5 比較快，K=10 比較準。
資料量很少時可以用 K=10 甚至 LOOCV。資料量很大時 K=5 就夠了。

**Q: 為什麼 `cross_val_score` 不需要先 `fit`？**
A: 因為 `cross_val_score` 內部會自動做 K 次的 fit 和 predict。
你傳進去的模型物件只是一個「模板」，它會被複製 K 次。

**Q: `scoring='accuracy'` 可以換成其他指標嗎？**
A: 可以！常用的有：
- `'f1'` 或 `'f1_macro'`：F1 分數
- `'roc_auc'`：ROC AUC（需要二分類）
- `'precision'`、`'recall'`
- `'neg_mean_squared_error'`：迴歸問題用

**Q: GridSearchCV 和 RandomizedSearchCV 怎麼選？**
A: 超參數空間小（<100 種組合）用 GridSearchCV。
超參數空間大（>100 種組合）用 RandomizedSearchCV。

**Q: 交叉驗證的結果和最終測試集的結果差很多怎麼辦？**
A: 如果 CV 結果比測試集好很多，可能是 CV 的過程中有資訊洩漏。
如果 CV 結果比測試集差，可能只是測試集「剛好比較容易」。
差異在 2-3% 以內通常是正常的。

**Q: 為什麼要 `stratify=y`？**
A: 確保訓練集和測試集的類別比例跟原始資料一樣。
如果不這樣做，可能某個類別全跑到測試集去了，訓練集根本學不到。

---

## 📝 課後練習

### 練習 1：體驗「只跑一次」的危險

```python
from sklearn.datasets import load_wine
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

wine = load_wine()
X, y = wine.data, wine.target

# 用 10 個不同的 random_state 切分資料
# 記錄每次的測試集準確率
# 計算平均值和標準差
# 再用 cross_val_score 做 10-Fold CV
# 比較兩種方式的結果
```

### 練習 2：用不同指標做交叉驗證

```python
from sklearn.datasets import load_breast_cancer
from sklearn.model_selection import cross_val_score
from sklearn.ensemble import RandomForestClassifier

cancer = load_breast_cancer()
X, y = cancer.data, cancer.target

rf = RandomForestClassifier(n_estimators=100, random_state=42)

# 用以下四種 scoring 做交叉驗證：
# 'accuracy', 'f1', 'precision', 'recall'
# 比較結果，哪個指標最低？為什麼？
```

### 練習 3：完整的 GridSearchCV 流程

```python
# 用 load_wine 資料集
# 1. 切出 20% 的測試集（stratify!）
# 2. 在訓練集上用 GridSearchCV 調整 Random Forest
#    搜尋: n_estimators=[50,100,200], max_depth=[3,5,10,None], min_samples_leaf=[1,5]
# 3. 印出最佳參數和最佳 CV 分數
# 4. 用最佳模型在測試集上做最終評估
# 5. 印出完整的 classification_report
```

---

## 本章總結

```
+--------------------------------------------------+
|       交叉驗證與模型評估核心觀念                 |
+--------------------------------------------------+
| 1. 不能只跑一次 → 用 K-Fold 交叉驗證            |
| 2. 不能只看 accuracy → 看 P/R/F1/AUC            |
| 3. StratifiedKFold 處理類別不平衡                |
| 4. cross_val_score 一行搞定交叉驗證              |
| 5. GridSearchCV 自動找最佳超參數                 |
| 6. 測試集只能看一次！不能用它選模型              |
| 7. 類別不平衡 → 看 PR Curve                      |
| 8. 類別平衡 → 看 ROC Curve                       |
+--------------------------------------------------+

正確的評估流程：

 原始資料
    |
    ├── 訓練集 (80%)
    |      |
    |      ├── 交叉驗證: 選模型 + 調參
    |      |     (GridSearchCV)
    |      |
    |      └── 最佳模型
    |
    └── 測試集 (20%)
           |
           └── 最終評估（只看一次！）
                |
                └── 報告: Accuracy, F1, AUC, classification_report

下一章我們將進入更進階的主題。
但記住，不管你用什麼演算法，
這一章教的評估方法都適用！
```

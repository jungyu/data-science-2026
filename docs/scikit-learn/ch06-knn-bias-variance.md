# Chapter 6: KNN 與 Bias-Variance Tradeoff - 你的鄰居決定你是誰

> 「物以類聚，人以群分。KNN 把這句古老的智慧變成了一個算法。」

---

## 🎯 本章目標

讀完這一章，你將能夠：

1. 理解 KNN（K-Nearest Neighbors）的核心思想
2. 用 scikit-learn 的 `KNeighborsClassifier` 建立分類模型
3. 理解 k 值的選擇如何影響模型行為
4. **掌握 Bias-Variance Tradeoff——機器學習中最重要的概念**
5. 認識不同的距離度量（Distance Metrics）
6. 初步理解維度詛咒（Curse of Dimensionality）

---

## KNN 的核心思想：問鄰居

你剛搬到一個新社區，想知道附近的房價。你會怎麼做？

> 最簡單的方法：看看旁邊幾棟房子賣多少錢，取平均。

這就是 KNN 的全部思想。

### KNN 算法步驟

```
給定一個新的資料點 X_new：

1. 計算 X_new 和所有訓練資料的距離
2. 找出距離最近的 K 個鄰居
3. 這 K 個鄰居投票（分類）或取平均（回歸）
4. 得到預測結果
```

```
假設 k=3，新來一個 ? 號：

    A A A A
   A A A  ·  B B
  A A · ? · B B B
   A  ·  B B B
      B B B B

  ? 的 3 個最近鄰居是 2 個 B 和 1 個 A
  → 投票結果：B 勝出！
  → 預測 ? 為 B 類
```

---

## 動手做：用 KNN 分類

```python
import numpy as np
import pandas as pd
from sklearn.datasets import load_iris
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.preprocessing import StandardScaler

# 載入鳶尾花資料集
iris = load_iris()
X = pd.DataFrame(iris.data, columns=iris.feature_names)
y = pd.Series(iris.target, name='species')

print(f"資料筆數：{len(X)}")
print(f"特徵數量：{X.shape[1]}")
print(f"類別數量：{len(np.unique(y))}")
print(f"類別名稱：{iris.target_names}")

# 切分資料
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# 特徵標準化（KNN 對距離敏感，所以必須標準化！）
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# 訓練 KNN 模型
knn = KNeighborsClassifier(n_neighbors=5)
knn.fit(X_train_scaled, y_train)

# 預測與評估
y_pred = knn.predict(X_test_scaled)
print(f"\n準確度：{accuracy_score(y_test, y_pred):.4f}")
print(classification_report(y_test, y_pred,
      target_names=iris.target_names))
```

---

## 💡 重點觀念：k 太小 vs k 太大

k 的選擇是 KNN 最關鍵的超參數。讓我們看看不同的 k 會怎樣。

### k=1：只看最近的一個鄰居

```
k=1 的決策邊界（非常複雜、鋸齒狀）：

  ┌────────────────────────────────┐
  │ A A A│B B│A│B B B B B B B B B │
  │ A A │B B │A│B B B B B B B B  │
  │ A │B B B│A A│B B B B B B B   │
  │ A│B B B B│A│B B B B B B B    │
  │ │B B B B B│B B B B B B       │
  └────────────────────────────────┘

  特點：
  - 完美擬合每一個訓練點（訓練準確度 = 100%）
  - 決策邊界極度不規則
  - 對雜訊非常敏感
  - 很容易過擬合
```

### k=15：看較多的鄰居

```
k=15 的決策邊界（比較平滑）：

  ┌────────────────────────────────┐
  │ A A A A A A │ B B B B B B B B │
  │ A A A A A │ B B B B B B B B B │
  │ A A A A │ B B B B B B B B B   │
  │ A A A │ B B B B B B B B B     │
  │ A A │ B B B B B B B B B       │
  └────────────────────────────────┘

  特點：
  - 決策邊界比較平滑
  - 對雜訊比較不敏感
  - 可能忽略局部模式
  - 如果 k 太大，會欠擬合
```

### k=N（等於訓練集大小）：看所有人

```
k=N 的決策邊界：

  ┌────────────────────────────────┐
  │ B B B B B B B B B B B B B B B │
  │ B B B B B B B B B B B B B B B │
  │ B B B B B B B B B B B B B B B │
  │ B B B B B B B B B B B B B B B │
  │ B B B B B B B B B B B B B B B │
  └────────────────────────────────┘

  如果 B 類是多數，所有點都會被預測為 B
  → 完全沒用的模型！
```

### 用程式碼實驗不同的 k

```python
train_scores = []
test_scores = []
k_range = range(1, 31)

for k in k_range:
    knn = KNeighborsClassifier(n_neighbors=k)
    knn.fit(X_train_scaled, y_train)

    train_scores.append(knn.score(X_train_scaled, y_train))
    test_scores.append(knn.score(X_test_scaled, y_test))

# 找出最佳 k
best_k = k_range[np.argmax(test_scores)]
print(f"最佳 k = {best_k}，測試準確度 = {max(test_scores):.4f}")

# 印出結果表格
print(f"\n{'k':>3} | {'訓練準確度':>10} | {'測試準確度':>10} | 狀態")
print("-" * 50)
for k, tr, te in zip(k_range, train_scores, test_scores):
    if k in [1, 3, 5, 7, 9, 11, 15, 21, 29]:
        gap = tr - te
        if gap > 0.1:
            status = "⚠️ 過擬合"
        elif te < 0.7:
            status = "❌ 欠擬合"
        else:
            status = "✅ 適當"
        print(f"{k:3d} | {tr:10.4f} | {te:10.4f} | {status}")
```

```
k vs 準確度的趨勢圖（ASCII 版）：

 準確度
 1.00 |*──*──*                          訓練集
      |         *──*──*──*──*──*
 0.95 |   .──.──.──.──.──.──.          測試集
      |  .
 0.90 | .                    *──*──*──*
      |.                              *──*
 0.85 |
      |
 0.80 +──┬──┬──┬──┬──┬──┬──┬──┬──┬──> k
      1  3  5  7  9  11 13 15 21 29

  k=1 → 訓練完美但測試較差（過擬合）
  k 適中 → 兩者都不錯（甜蜜點）
  k 太大 → 兩者都下降（欠擬合）
```

---

## 💡 重點觀念：Bias-Variance Tradeoff

**這是機器學習中最重要的概念，沒有之一。**

每個模型的預測誤差都可以分解成三個部分：

```
總誤差 = Bias² + Variance + 不可約誤差（Noise）
```

### 什麼是 Bias（偏差）？

Bias 是模型的「系統性偏見」——模型因為太簡單而無法捕捉資料的真實模式。

```
真實關係是一條曲線，但模型硬用一條直線去擬合：

 y                                y
 |    ***                         |    ***
 |   *   *                        |   * / *
 | **     **                      | ** /   **
 |*        ***                    |* /      ***
 |            ****                | /          ****
 +──────────────────> x           +──────────────────> x

 真實資料                          高 Bias 的模型
                                   （太簡單，抓不到曲線）
```

高 Bias 的特徵：
- 訓練集和測試集的表現都差
- 模型太簡單
- 在 KNN 中：k 太大

### 什麼是 Variance（方差）？

Variance 是模型的「不穩定性」——用不同的訓練資料訓練出來的模型差異很大。

```
用三組不同訓練資料訓練同一個模型：

 資料集 1            資料集 2            資料集 3
 y                   y                   y
 | ╱╲  ╱╲            | ╱╲╱╲              |╱╲ ╱╲╱╲
 |╱  ╲╱  ╲           |╱    ╲╱            |  ╲╱
 |        ╲╱         |      ╲╱╲          |       ╲
 +──────────> x      +──────────> x      +──────────> x

 三個模型長得完全不一樣！→ 高 Variance
```

高 Variance 的特徵：
- 訓練集表現好，測試集表現差
- 模型太複雜，對訓練資料過度敏感
- 在 KNN 中：k 太小

### Bias-Variance 的蹺蹺板

```
 誤差
  ^
  |╲                           ╱
  | ╲                         ╱
  |  ╲  Bias²               ╱  Variance
  |   ╲                   ╱
  |    ╲                ╱
  |     ╲             ╱
  |      ╲    ╱──╲  ╱      ← 總誤差
  |       ╲ ╱    ╲╱
  |        ╳──────
  |      ╱  ╲
  |    ╱     ────────────   ← 不可約誤差（Noise）
  |  ╱
  +────────────────────────> 模型複雜度
   簡單                 複雜
   （高 Bias,           （低 Bias,
    低 Variance）        高 Variance）

           ↑
      最佳甜蜜點
```

### 在 KNN 中的體現

```
 ┌─────────────┬──────────────┬──────────────────────────┐
 │  k 值       │  Bias/Var    │  行為                     │
 ├─────────────┼──────────────┼──────────────────────────┤
 │  k=1        │  低B/高V     │  記住每個點，容易過擬合    │
 │  k=5~15     │  平衡        │  通常是好的起點            │
 │  k=N        │  高B/低V     │  永遠猜多數類，欠擬合      │
 └─────────────┴──────────────┴──────────────────────────┘

 注意：在 KNN 中，k 越大模型越簡單！
 這跟其他算法「參數越多越複雜」的直覺相反。
```

---

## 🧠 動動腦：Bias-Variance 的生活類比

### 類比：打靶

想像你在練習射擊，目標是靶心。

```
低 Bias, 低 Variance       高 Bias, 低 Variance
（理想狀態）               （精確但不準確）

     ┌─────────┐              ┌─────────┐
     │  ╭───╮  │              │  ╭───╮  │
     │ ╭┤···├╮ │              │ ╭┤   ├╮ │
     │ │╰···╯│ │              │ │╰···╯│ │
     │ ╰─────╯ │              │ ╰──···╯ │
     └─────────┘              └─────────┘
    每次都打在靶心附近         每次都打在一起，
                              但偏離靶心

低 Bias, 高 Variance       高 Bias, 高 Variance
（準確但不精確）           （又偏又散）

     ┌─────────┐              ┌─────────┐
     │· ╭───╮  │              │  ╭───╮ ·│
     │ ╭┤ · ├╮·│              │ ╭┤   ├╮ │
     │·│╰───╯│ │              │ │╰───╯│ │
     │ ╰─────╯·│              │ ╰─────╯ │
     └─────────┘              │·      · │
    平均起來在靶心，            └─────────┘
    但散得很開                 偏離靶心又很散
```

| 射擊類比 | 機器學習 |
|---------|---------|
| 靶心 | 真實值 |
| 彈著點 | 模型預測值 |
| 離靶心的偏移 | Bias |
| 彈著點的分散程度 | Variance |

---

## 距離度量：KNN 的「尺」

KNN 需要計算距離，但「距離」可以有不同的定義。

### 歐氏距離（Euclidean Distance）——預設

就是我們平常說的「直線距離」：

```
d = √((x₁-y₁)² + (x₂-y₂)² + ... + (xₙ-yₙ)²)
```

```
兩點之間的歐氏距離：

  y
  5 |        B(4,4)
    |       /
    |      / d = √((4-1)²+(4-1)²)
    |     /    = √(9+9)
    |    /     = √18 ≈ 4.24
    |   /
  1 | A(1,1)
    +──────────────> x
    0  1  2  3  4  5
```

### 曼哈頓距離（Manhattan Distance）

走棋盤格的距離（只能走水平和垂直）：

```
d = |x₁-y₁| + |x₂-y₂| + ... + |xₙ-yₙ|
```

```
曼哈頓距離：

  y
  5 |        B(4,4)
    |        │
    |        │ 3 步（垂直）
    |        │
  1 | A(1,1)─┘
    |   3 步（水平）
    +──────────────> x
    曼哈頓距離 = 3 + 3 = 6
    （比歐氏距離 4.24 大）
```

### 閔可夫斯基距離（Minkowski Distance）——統一框架

```
d = (Σ |xᵢ-yᵢ|^p)^(1/p)

p=1 → 曼哈頓距離
p=2 → 歐氏距離
p=∞ → 切比雪夫距離（各維度差異的最大值）
```

```python
from sklearn.neighbors import KNeighborsClassifier

# 不同距離度量
for metric in ['euclidean', 'manhattan', 'minkowski']:
    knn = KNeighborsClassifier(n_neighbors=5, metric=metric)
    knn.fit(X_train_scaled, y_train)
    score = knn.score(X_test_scaled, y_test)
    print(f"{metric:>12}: 測試準確度 = {score:.4f}")
```

### 什麼時候用哪種距離？

```
 ┌──────────────────┬──────────────────────────────────────┐
 │  距離度量        │  適合場景                             │
 ├──────────────────┼──────────────────────────────────────┤
 │  歐氏距離        │  大多數情況的預設選擇                 │
 │  曼哈頓距離      │  高維度資料、特徵有不同尺度           │
 │  閔可夫斯基(p>2) │  想要強調最大維度的差異               │
 │  餘弦相似度      │  文字分類、推薦系統（重方向不重大小） │
 └──────────────────┴──────────────────────────────────────┘
```

---

## ⚠️ 常見陷阱：維度詛咒

### 什麼是維度詛咒（Curse of Dimensionality）？

隨著特徵數量增加，KNN 的表現可能會急劇下降。

**直覺解釋**：在高維度空間中，「最近的鄰居」其實離你很遠。

```
想像在一條線上（1 維）：
 ├──*──*──*──*──*──?──*──*──*──*──┤
 最近鄰居離你很近

想像在一個平面上（2 維）：
 ┌───────────────────┐
 │  *     *     *    │
 │     *     *       │
 │  *     ?     *    │
 │     *     *       │
 │  *     *     *    │
 └───────────────────┘
 同樣的資料量，最近鄰居變遠了

想像在一個立方體中（3 維）：
 更遠了...

想像在 100 維空間中：
 最近鄰居和最遠的點幾乎一樣遠！
 「近」和「遠」失去了意義！
```

### 數學上的解釋

```
在 d 維超立方體中，要包含 k% 的資料，
邊長需要是 k^(1/d)：

 維度 d  │  邊長（包含10%的資料）
─────────┼────────────────────────
    1    │  0.100  （原始長度的 10%）
    2    │  0.316  （原始長度的 31.6%）
    5    │  0.631  （原始長度的 63.1%）
   10    │  0.794  （原始長度的 79.4%）
   50    │  0.955  （原始長度的 95.5%）
  100    │  0.977  （原始長度的 97.7%）

結論：維度越高，要找到「近鄰」就需要涵蓋越大的範圍
→ 「近鄰」已經不「近」了
```

### 實際影響

```python
from sklearn.datasets import make_classification

results = []
for n_features in [2, 5, 10, 20, 50, 100, 200]:
    X_exp, y_exp = make_classification(
        n_samples=1000,
        n_features=n_features,
        n_informative=min(5, n_features),  # 只有 5 個真正有用的特徵
        n_redundant=0,
        random_state=42
    )

    X_tr, X_te, y_tr, y_te = train_test_split(
        X_exp, y_exp, test_size=0.2, random_state=42
    )

    sc = StandardScaler()
    X_tr_s = sc.fit_transform(X_tr)
    X_te_s = sc.transform(X_te)

    knn_exp = KNeighborsClassifier(n_neighbors=5)
    knn_exp.fit(X_tr_s, y_tr)
    score = knn_exp.score(X_te_s, y_te)

    results.append((n_features, score))
    print(f"特徵數 = {n_features:3d} | 準確度 = {score:.4f}")
```

```
可能輸出：

 特徵數 = 2   | 準確度 = 0.9100
 特徵數 = 5   | 準確度 = 0.9350
 特徵數 = 10  | 準確度 = 0.9150
 特徵數 = 20  | 準確度 = 0.8800  ← 開始下降
 特徵數 = 50  | 準確度 = 0.8350  ← 明顯下降
 特徵數 = 100 | 準確度 = 0.7900  ← 更差了
 特徵數 = 200 | 準確度 = 0.7450  ← 繼續惡化

 注意：只有 5 個特徵是真正有用的！
 多餘的特徵只是在增加雜訊和距離計算的困難。
```

### 應對維度詛咒的方法

```
 ┌──────────────────────┬──────────────────────────────────┐
 │  方法                │  說明                             │
 ├──────────────────────┼──────────────────────────────────┤
 │  特徵選擇            │  只保留有用的特徵                 │
 │  PCA 降維            │  把高維資料壓縮到低維             │
 │  增加樣本數          │  更多資料可以部分彌補高維問題     │
 │  換用其他算法        │  決策樹、隨機森林對高維更健壯     │
 └──────────────────────┴──────────────────────────────────┘
```

---

## 完整案例：尋找最佳 k

```python
import numpy as np
import pandas as pd
from sklearn.datasets import load_wine
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report

# ============================================================
# 葡萄酒分類完整流程
# ============================================================

# 1. 載入資料
wine = load_wine()
X = pd.DataFrame(wine.data, columns=wine.feature_names)
y = pd.Series(wine.target)

print("=" * 50)
print("資料概覽")
print("=" * 50)
print(f"樣本數：{len(X)}")
print(f"特徵數：{X.shape[1]}")
print(f"類別數：{len(np.unique(y))}")
print(f"類別分佈：{np.bincount(y)}")

# 2. 切分與標準化
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# 3. 用交叉驗證找最佳 k
print("\n" + "=" * 50)
print("交叉驗證尋找最佳 k")
print("=" * 50)

k_range = range(1, 31)
cv_scores = []

print(f"{'k':>3} | {'CV 平均準確度':>14} | {'CV 標準差':>10} | 圖示")
print("-" * 60)

for k in k_range:
    knn = KNeighborsClassifier(n_neighbors=k)
    scores = cross_val_score(knn, X_train_scaled, y_train, cv=5)
    cv_scores.append(scores.mean())

    # 只印出奇數的 k
    if k % 2 == 1:
        bar = '█' * int(scores.mean() * 40)
        print(f"{k:3d} | {scores.mean():14.4f} | {scores.std():10.4f} | {bar}")

best_k = k_range[np.argmax(cv_scores)]
print(f"\n最佳 k = {best_k}，CV 準確度 = {max(cv_scores):.4f}")

# 4. 用最佳 k 訓練最終模型
print("\n" + "=" * 50)
print(f"最終模型（k={best_k}）")
print("=" * 50)

final_knn = KNeighborsClassifier(n_neighbors=best_k)
final_knn.fit(X_train_scaled, y_train)
y_pred = final_knn.predict(X_test_scaled)

print(f"訓練準確度：{final_knn.score(X_train_scaled, y_train):.4f}")
print(f"測試準確度：{final_knn.score(X_test_scaled, y_test):.4f}")
print(f"\n{classification_report(y_test, y_pred, target_names=wine.target_names)}")

# 5. Bias-Variance 觀察
print("=" * 50)
print("Bias-Variance 觀察")
print("=" * 50)

train_scores = []
test_scores_list = []

for k in k_range:
    knn = KNeighborsClassifier(n_neighbors=k)
    knn.fit(X_train_scaled, y_train)
    train_scores.append(knn.score(X_train_scaled, y_train))
    test_scores_list.append(knn.score(X_test_scaled, y_test))

print(f"\n{'k':>3} | {'訓練準確度':>10} | {'測試準確度':>10} | {'差距':>6} | 診斷")
print("-" * 60)
for k in [1, 3, 5, 7, 9, 11, 15, 21, 29]:
    tr = train_scores[k-1]
    te = test_scores_list[k-1]
    gap = tr - te
    if gap > 0.1:
        diag = "⚠️ 高 Variance（過擬合）"
    elif te < 0.8:
        diag = "⚠️ 高 Bias（欠擬合）"
    else:
        diag = "✅ 平衡"
    print(f"{k:3d} | {tr:10.4f} | {te:10.4f} | {gap:6.4f} | {diag}")
```

---

## 🧠 動動腦：KNN 的特性

### 問題 1：KNN 有「訓練」過程嗎？

```
答案：幾乎沒有！

KNN 是一種「懶惰學習」（Lazy Learning）算法：
- 訓練時：只是把資料存起來（O(1)）
- 預測時：計算所有距離並排序（O(n × d)）

vs 邏輯斯回歸是「勤奮學習」（Eager Learning）：
- 訓練時：花時間學習權重
- 預測時：只需要做一次矩陣乘法（很快！）

 ┌──────────┬──────────────┬──────────────┐
 │          │  訓練時間    │  預測時間    │
 ├──────────┼──────────────┼──────────────┤
 │  KNN     │  很快        │  很慢        │
 │  LR      │  普通        │  很快        │
 └──────────┴──────────────┴──────────────┘

 所以 KNN 不適合：
 - 需要快速預測的線上服務
 - 訓練資料量非常大的場景
```

### 問題 2：k 為什麼通常選奇數？

```
答案：避免平票！

k=4 的情況：
  2 個鄰居說 A，2 個鄰居說 B → 平手！怎麼辦？

k=5 的情況：
  不可能出現 2.5 vs 2.5 → 一定有贏家

（注：scikit-learn 遇到平票會選較近的類別，
  但選奇數 k 可以從根本上避免這個問題）
```

---

## ❓ 沒有笨問題

**Q：KNN 可以做回歸嗎？**

A：可以！`KNeighborsRegressor` 是回歸版本。
預測值 = K 個最近鄰居的目標值平均。

```python
from sklearn.neighbors import KNeighborsRegressor
knn_reg = KNeighborsRegressor(n_neighbors=5)
```

**Q：所有特徵的重要性都一樣嗎？**

A：在 KNN 中，所有特徵對距離的貢獻是相同的。
這就是為什麼標準化這麼重要！如果一個特徵的數值範圍是 0-1000，
另一個是 0-1，不標準化的話，第一個特徵會主導距離計算。

**Q：KNN 能處理類別特徵嗎？**

A：標準 KNN 只能處理數值特徵。
類別特徵需要先編碼（如 One-Hot Encoding）。
但要注意，One-Hot 會增加維度，加劇維度詛咒。

**Q：如何知道我的 k 是不是太大或太小？**

A：用交叉驗證！
- 畫出 k vs 準確度的圖
- 同時看訓練和測試的表現
- 如果訓練高、測試低 → k 太小
- 如果兩者都低 → k 太大

**Q：Bias-Variance Tradeoff 只存在於 KNN 嗎？**

A：不！這是所有機器學習模型的根本問題。

```
 ┌──────────────────┬──────────────┬──────────────┐
 │  算法            │  更複雜 →    │  更簡單 →    │
 ├──────────────────┼──────────────┼──────────────┤
 │  KNN             │  k 變小      │  k 變大      │
 │  決策樹          │  深度增加    │  深度減少    │
 │  線性回歸        │  多項式次數高│  多項式次數低│
 │  神經網路        │  層數/節點多 │  層數/節點少 │
 └──────────────────┴──────────────┴──────────────┘

 在每一種算法中，你都需要找到 Bias 和 Variance
 之間的平衡點。這就是模型調參的核心任務。
```

---

## ⚠️ 常見陷阱

### 陷阱 1：忘記標準化

```python
# ❌ KNN 對尺度非常敏感
knn = KNeighborsClassifier(n_neighbors=5)
knn.fit(X_train, y_train)  # 沒有標準化

# ✅ 必須標準化
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)
knn.fit(X_train_scaled, y_train)
```

### 陷阱 2：特徵太多

```python
# ❌ 把所有 100 個特徵都丟進 KNN
knn.fit(X_100_features, y_train)

# ✅ 先做特徵選擇或降維
from sklearn.decomposition import PCA
pca = PCA(n_components=10)
X_reduced = pca.fit_transform(X_100_features)
knn.fit(X_reduced, y_train)
```

### 陷阱 3：在大資料集上使用 KNN

```python
# ❌ 100 萬筆資料用 KNN → 預測一個點要算 100 萬次距離
# 非常慢！

# ✅ 考慮用 BallTree 或 KDTree 加速
knn = KNeighborsClassifier(n_neighbors=5, algorithm='ball_tree')

# 或者乾脆換一個算法（如隨機森林）
```

### 陷阱 4：不做交叉驗證就選 k

```python
# ❌ 憑感覺選 k=5
knn = KNeighborsClassifier(n_neighbors=5)

# ✅ 用交叉驗證找最佳 k
from sklearn.model_selection import cross_val_score

best_score = 0
best_k = 1
for k in range(1, 31, 2):  # 只試奇數
    knn = KNeighborsClassifier(n_neighbors=k)
    scores = cross_val_score(knn, X_train_scaled, y_train, cv=5)
    if scores.mean() > best_score:
        best_score = scores.mean()
        best_k = k

print(f"最佳 k = {best_k}")
```

---

## 本章回顧

```
KNN 與 Bias-Variance 知識地圖：

 ┌──────────────────────────────────────────────────────────────┐
 │                    KNN 與 Bias-Variance                      │
 │                                                              │
 │  ┌──────────────┐  ┌───────────────┐  ┌─────────────────┐  │
 │  │  KNN 基礎     │  │ Bias-Variance │  │ 進階概念         │  │
 │  │              │  │               │  │                 │  │
 │  │  K 個鄰居    │  │  Bias=偏見    │  │  距離度量        │  │
 │  │  距離計算    │  │  Variance=   │  │  維度詛咒        │  │
 │  │  多數決投票  │  │   不穩定      │  │  交叉驗證選 k    │  │
 │  │  標準化必要  │  │  總誤差分解   │  │  懶惰學習        │  │
 │  │              │  │  甜蜜點       │  │                 │  │
 │  └──────────────┘  └───────────────┘  └─────────────────┘  │
 │                                                              │
 │  ┌──────────────────────────────────────────────────────┐   │
 │  │                  核心教訓                              │   │
 │  │                                                      │   │
 │  │  1. k 小 → 高 Variance → 過擬合                      │   │
 │  │  2. k 大 → 高 Bias → 欠擬合                          │   │
 │  │  3. Bias-Variance Tradeoff 適用於所有 ML 模型        │   │
 │  │  4. 用交叉驗證找最佳超參數                            │   │
 │  │  5. KNN 一定要標準化特徵                              │   │
 │  │  6. 高維度資料不適合 KNN                              │   │
 │  └──────────────────────────────────────────────────────┘   │
 └──────────────────────────────────────────────────────────────┘
```

---

## 📝 課後練習

### 練習 1：基礎操作

用 scikit-learn 的 `load_wine()` 資料集：

```python
from sklearn.datasets import load_wine
wine = load_wine()
X = pd.DataFrame(wine.data, columns=wine.feature_names)
y = pd.Series(wine.target)
```

1. 標準化特徵
2. 用交叉驗證找出最佳 k（試 k=1 到 k=30）
3. 畫出 k vs 準確度的圖
4. 用最佳 k 在測試集上評估

### 練習 2：Bias-Variance 實驗

1. 用 k=1, 5, 15, 30 分別訓練 KNN
2. 記錄每個 k 的訓練準確度和測試準確度
3. 畫一張圖：x 軸是 k，y 軸有兩條線（訓練和測試準確度）
4. 標出最佳甜蜜點在哪裡
5. 解釋：為什麼 k=1 的訓練準確度是 100%？

### 練習 3：維度詛咒實驗

```python
from sklearn.datasets import make_classification

# 固定 5 個有用特徵，增加雜訊特徵
for n_noise in [0, 5, 20, 50, 100, 200]:
    X_exp, y_exp = make_classification(
        n_samples=500,
        n_features=5 + n_noise,
        n_informative=5,
        n_redundant=0,
        random_state=42
    )
    # 你的代碼：訓練 KNN 並記錄準確度
```

1. 觀察雜訊特徵如何影響 KNN 的表現
2. 用 PCA 降維到 5 維後再訓練，比較結果
3. 思考：為什麼特徵越多反而越差？

### 練習 4：思考題

一家電商想用 KNN 建立推薦系統（根據相似用戶推薦商品）：
- 有 1000 萬個用戶
- 每個用戶有 500 個特徵（購買歷史、瀏覽記錄等）

這個方案可行嗎？會遇到什麼問題？你會建議什麼替代方案？

---

## 下一章預告

我們已經學了三個算法：線性回歸、邏輯斯回歸、KNN。
它們都有各自的長處和限制。

下一章，我們會學到一個強大的工具——**決策樹（Decision Tree）**，
它不需要特徵標準化、能自動處理非線性、而且結果可以解釋。

> 「如果 KNN 的哲學是『看鄰居』，
>   決策樹的哲學就是『問問題』。
>   一個好的問題，比一千個鄰居更有用。」

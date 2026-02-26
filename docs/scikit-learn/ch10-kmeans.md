# 第 10 章：K-Means 分群 —— 讓資料自己說話

## 🎯 本章目標

讀完本章後，你將能夠：

1. 理解「非監督式學習」與監督式學習的根本差異
2. 手動推演 K-Means 演算法的每一步
3. 使用 scikit-learn 的 `KMeans` 進行分群
4. 用「手肘法」與「輪廓係數」選出最佳 k 值
5. 完成一個完整的客戶分群案例
6. 認識 K-Means 的限制與應對策略

---

## 從「有老師」到「沒老師」

還記得前幾章嗎？我們一直在做的事情是：

```
輸入 X（特徵）+ 正確答案 y（標籤）  →  訓練模型  →  預測新資料
```

這叫做 **監督式學習（Supervised Learning）**，因為有一位「老師」告訴模型
什麼是正確答案。

但現實世界中，很多時候 **我們根本沒有標籤**。

```
+------------------------------------------+
|         監督式學習 vs 非監督式學習          |
+------------------------------------------+
|                                          |
|  監督式：                                 |
|  「這封是垃圾郵件，那封不是」               |
|  「這張是貓，那張是狗」                     |
|  → 有人先幫你貼好標籤                      |
|                                          |
|  非監督式：                                |
|  「這裡有 10,000 個客戶的消費紀錄」         |
|  「幫我找出有意義的分組」                   |
|  → 沒有人告訴你誰該跟誰一組                |
|                                          |
+------------------------------------------+
```

> 想像你第一天到新學校，午餐時間走進餐廳，沒有人告訴你哪一桌是哪一群。
> 但你自然而然會觀察：「那一桌都在討論籃球，這一桌在看漫畫，
> 角落那桌在寫程式......」你的大腦自動幫人群「分群」了。
>
> K-Means 做的事情就跟你的大腦一樣 —— 只是它用數學來做。

---

## 💡 重點觀念：什麼是分群（Clustering）？

**分群**是一種非監督式學習任務，目標是把資料分成幾個「群組（cluster）」，
讓：

- **同一群內的資料點** 彼此盡可能 **相似**
- **不同群的資料點** 彼此盡可能 **不同**

```
  分群前：                     分群後：

  .  .    . .                  o  o    x x
    .  .      .                  o  o      x
  .    .  . .                  o    o  x x
       .    .  .                    o    x  x
  .  .    .                    o  o    x
            .  .                         x  x

  （一團混亂）                  （清楚的兩群！）
```

---

## K-Means 演算法：一步一步來

K-Means 的 "K" 代表你要分成 **K 群**。演算法非常直覺：

### 步驟流程

```
┌─────────────────────────────────────────────────┐
│           K-Means 演算法四步驟                    │
├─────────────────────────────────────────────────┤
│                                                 │
│  Step 1: 隨機選 K 個點作為「群心」(centroid)       │
│          ↓                                      │
│  Step 2: 每個資料點歸入「最近的群心」所屬群組       │
│          ↓                                      │
│  Step 3: 重新計算每群的中心點（平均值）             │
│          ↓                                      │
│  Step 4: 重複 Step 2-3，直到群心不再移動           │
│                                                 │
└─────────────────────────────────────────────────┘
```

### 用圖來看一輪迭代

假設我們有 6 個資料點，要分成 K=2 群：

```
初始狀態（隨機放兩個群心 C1, C2）：

        C1(*)
  a(.)        b(.)
                      c(.)
        d(.)
  e(.)              C2(*)
              f(.)

Step 2 —— 每個點找最近的群心：
  距離 C1 較近 → 群 1：a, b, d
  距離 C2 較近 → 群 2：c, e, f

Step 3 —— 重算群心（每群的平均座標）：
  C1' = mean(a, b, d)
  C2' = mean(c, e, f)

        C1'(*)                ← 群心移動了！
  a(o)        b(o)
                      c(x)
        d(o)
  e(x)              C2'(*)   ← 群心也移動了！
              f(x)

重複 Step 2-3... 直到群心穩定（收斂）。
```

---

## 🧠 動動腦

> 如果一開始兩個群心剛好都放在同一個位置，會發生什麼事？
>
> 提示：想想 Step 2 — 每個點找「最近的群心」，如果兩個群心重合......
>
> （答案在本章最後）

---

## 用 scikit-learn 實作 K-Means

### 產生測試資料

```python
import numpy as np
import matplotlib.pyplot as plt
from sklearn.datasets import make_blobs

# 產生 300 個點，分成 3 群
X, y_true = make_blobs(
    n_samples=300,
    centers=3,          # 實際有 3 個群
    cluster_std=0.8,    # 群內離散程度
    random_state=42
)

# 畫圖看看（注意：非監督式學習中我們「不知道」y_true）
plt.scatter(X[:, 0], X[:, 1], s=30, alpha=0.6)
plt.title("原始資料（沒有標籤）")
plt.xlabel("特徵 1")
plt.ylabel("特徵 2")
plt.show()
```

### 訓練 KMeans 模型

```python
from sklearn.cluster import KMeans

# 建立模型，指定分 3 群
kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)

# 訓練！（注意：只需要 X，不需要 y）
kmeans.fit(X)

# 取得每個點的群標籤
labels = kmeans.labels_          # 長度 300 的陣列，值為 0, 1, 2
centers = kmeans.cluster_centers_  # 3 個群心的座標

print(f"群標籤：{np.unique(labels)}")
print(f"群心座標：\n{centers}")
```

### 視覺化分群結果

```python
# 用不同顏色畫出各群
plt.scatter(X[:, 0], X[:, 1], c=labels, cmap='viridis', s=30, alpha=0.6)
plt.scatter(centers[:, 0], centers[:, 1],
            c='red', marker='X', s=200, edgecolors='black',
            label='群心')
plt.title("K-Means 分群結果 (k=3)")
plt.xlabel("特徵 1")
plt.ylabel("特徵 2")
plt.legend()
plt.show()
```

---

## 💡 重點觀念：Inertia（慣性）

K-Means 在優化的目標函數叫做 **inertia**，又稱
**WCSS（Within-Cluster Sum of Squares）**：

```
                K
Inertia  =    SUM    SUM   || x - c_k ||^2
              k=1   x in C_k

翻譯成白話：
「每個點到它所屬群心的距離平方」全部加起來。
```

```
+-----------------------------------------------------+
|   Inertia 的直覺理解                                  |
+-----------------------------------------------------+
|                                                     |
|   Inertia 小  →  每群內的點都很「緊密」               |
|   Inertia 大  →  群內的點很「鬆散」                   |
|                                                     |
|   K-Means 的目標：讓 inertia 越小越好                 |
|                                                     |
|   但注意：k 越大，inertia 一定越小                     |
|   （極端情況：k = n，每個點自己一群，inertia = 0）      |
|                                                     |
+-----------------------------------------------------+
```

```python
# 查看 inertia
print(f"Inertia: {kmeans.inertia_:.2f}")
```

---

## 手肘法（Elbow Method）：k 要選多大？

這是每個初學者都會問的問題：**我怎麼知道要分幾群？**

手肘法的思路很簡單：

1. 分別用 k=1, 2, 3, ..., 10 跑 K-Means
2. 記錄每個 k 的 inertia
3. 畫圖，找「轉折點」—— 像手肘一樣彎的地方

```python
inertias = []
K_range = range(1, 11)

for k in K_range:
    km = KMeans(n_clusters=k, random_state=42, n_init=10)
    km.fit(X)
    inertias.append(km.inertia_)

plt.figure(figsize=(8, 4))
plt.plot(K_range, inertias, 'bo-', linewidth=2)
plt.xlabel('k（群數）')
plt.ylabel('Inertia')
plt.title('手肘法：選擇最佳 k')
plt.xticks(K_range)
plt.grid(True, alpha=0.3)
plt.show()
```

```
Inertia
  |
  |*
  |  *
  |    *
  |      *
  |        *----*----*----*----*    ← 後面越來越平
  |        ^
  |     手肘在這！
  |     k=3 可能是好選擇
  +----+----+----+----+----+---→ k
       1    2    3    4    5
```

> 為什麼叫「手肘法」？因為圖形長得像一隻彎曲的手臂，
> 而轉折最明顯的地方就是「手肘」。
> 在手肘之後增加 k，inertia 下降的幅度變小了，
> 代表多分一群的「邊際效益」不大。

---

## 輪廓係數（Silhouette Score）：更科學的評估

手肘法有時候不夠明確（手肘不明顯怎麼辦？），這時可以用 **輪廓係數**。

### 輪廓係數的計算

對每個資料點 i：

```
a(i) = 點 i 到「同群其他點」的平均距離   （群內凝聚度）
b(i) = 點 i 到「最近其他群的所有點」的平均距離（群間分離度）

              b(i) - a(i)
s(i) = ─────────────────────
          max(a(i), b(i))
```

```
+-----------------------------------------------------+
|   輪廓係數的直覺                                      |
+-----------------------------------------------------+
|                                                     |
|   s(i) 的範圍：-1 到 +1                              |
|                                                     |
|   +1  →  完美！點 i 離自己群很近，離別群很遠           |
|    0  →  模糊地帶，點 i 在兩群的邊界上                 |
|   -1  →  糟糕！點 i 可能被分錯群了                    |
|                                                     |
|   整體平均輪廓係數越高，分群品質越好                    |
|                                                     |
+-----------------------------------------------------+
```

### 用 scikit-learn 計算

```python
from sklearn.metrics import silhouette_score

# 計算不同 k 值的輪廓係數
sil_scores = []
K_range = range(2, 11)  # 注意：k=1 沒有輪廓係數

for k in K_range:
    km = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels = km.fit_predict(X)
    score = silhouette_score(X, labels)
    sil_scores.append(score)
    print(f"k={k}: Silhouette Score = {score:.4f}")

plt.figure(figsize=(8, 4))
plt.plot(K_range, sil_scores, 'ro-', linewidth=2)
plt.xlabel('k（群數）')
plt.ylabel('Silhouette Score')
plt.title('輪廓係數：選擇最佳 k')
plt.xticks(K_range)
plt.grid(True, alpha=0.3)
plt.show()
```

---

## 🔥 實戰案例：客戶分群（Customer Segmentation）

這是 K-Means 最經典的商業應用！

### 情境

你是一家電商公司的資料分析師，手上有客戶的消費紀錄，
老闆問你：「我們的客戶可以分成哪幾種類型？」

### 資料準備

```python
import pandas as pd
from sklearn.preprocessing import StandardScaler

# 模擬客戶資料
np.random.seed(42)
n_customers = 500

data = pd.DataFrame({
    '年消費金額': np.concatenate([
        np.random.normal(2000, 500, 150),    # 低消費群
        np.random.normal(8000, 1500, 200),   # 中消費群
        np.random.normal(25000, 5000, 150),  # 高消費群
    ]),
    '消費頻率': np.concatenate([
        np.random.normal(5, 2, 150),         # 低頻率
        np.random.normal(20, 5, 200),        # 中頻率
        np.random.normal(50, 10, 150),       # 高頻率
    ]),
    '平均客單價': np.concatenate([
        np.random.normal(200, 50, 150),      # 低客單
        np.random.normal(400, 100, 200),     # 中客單
        np.random.normal(600, 150, 150),     # 高客單
    ]),
})

print(data.describe())
```

### ⚠️ 常見陷阱：忘記做特徵縮放！

```
+-----------------------------------------------------+
|   K-Means 使用「距離」來分群                           |
|   如果特徵的尺度不同，大數值特徵會主導結果！             |
|                                                     |
|   年消費金額：  2,000 ~ 25,000                       |
|   消費頻率：      5 ~ 50                             |
|   平均客單價：  200 ~ 600                             |
|                                                     |
|   不做 StandardScaler？                              |
|   → K-Means 幾乎只看「年消費金額」這一個特徵！          |
+-----------------------------------------------------+
```

```python
# 一定要標準化！
scaler = StandardScaler()
X_scaled = scaler.fit_transform(data)

print("標準化後的平均值：", X_scaled.mean(axis=0).round(2))
print("標準化後的標準差：", X_scaled.std(axis=0).round(2))
```

### 用手肘法 + 輪廓係數選 k

```python
inertias = []
sil_scores = []
K_range = range(2, 9)

for k in K_range:
    km = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels = km.fit_predict(X_scaled)
    inertias.append(km.inertia_)
    sil_scores.append(silhouette_score(X_scaled, labels))

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

ax1.plot(K_range, inertias, 'bo-')
ax1.set_xlabel('k')
ax1.set_ylabel('Inertia')
ax1.set_title('手肘法')

ax2.plot(K_range, sil_scores, 'ro-')
ax2.set_xlabel('k')
ax2.set_ylabel('Silhouette Score')
ax2.set_title('輪廓係數')

plt.tight_layout()
plt.show()
```

### 分群並分析結果

```python
# 選 k=3 來做最終分群
kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
data['客群'] = kmeans.fit_predict(X_scaled)

# 看每個群的特徵
summary = data.groupby('客群').mean().round(1)
summary['人數'] = data.groupby('客群').size().values
print(summary)
```

```
預期輸出類似：

        年消費金額  消費頻率  平均客單價  人數
客群
0       2053.2     5.1     198.7     150    ← 省錢族
1       8124.5    20.3     401.2     200    ← 一般客群
2      24876.3    49.8     598.5     150    ← VIP 客群
```

### 商業解讀

```
+-------------------+-------------------+-------------------+
|    客群 0          |    客群 1          |    客群 2          |
|    「省錢族」       |    「一般客群」     |    「VIP 客群」     |
+-------------------+-------------------+-------------------+
| 低消費、低頻率     | 中等消費與頻率     | 高消費、高頻率     |
| 低客單價           | 中等客單價         | 高客單價           |
+-------------------+-------------------+-------------------+
| 行銷策略：         | 行銷策略：         | 行銷策略：         |
| → 優惠券刺激       | → 升級方案推薦     | → 專屬尊榮服務     |
| → 首購優惠         | → 會員積點         | → VIP 專屬活動     |
| → 低價推薦         | → 滿額禮           | → 客製化推薦       |
+-------------------+-------------------+-------------------+
```

---

## 分群結果視覺化

```python
from mpl_toolkits.mplot3d import Axes3D

fig = plt.figure(figsize=(10, 7))
ax = fig.add_subplot(111, projection='3d')

scatter = ax.scatter(
    data['年消費金額'],
    data['消費頻率'],
    data['平均客單價'],
    c=data['客群'],
    cmap='viridis',
    s=30, alpha=0.6
)

ax.set_xlabel('年消費金額')
ax.set_ylabel('消費頻率')
ax.set_zlabel('平均客單價')
ax.set_title('客戶分群 3D 視覺化')
plt.colorbar(scatter, label='客群')
plt.show()
```

---

## ⚠️ 常見陷阱

### 陷阱 1：初始群心的選擇

K-Means 對初始群心很敏感！不同的起始位置可能得到不同結果。

```python
# scikit-learn 的 KMeans 預設 n_init=10
# 意思是跑 10 次不同的初始化，取 inertia 最小的那次
# 這就是為什麼要設定 random_state 來重現結果

# 另外，init='k-means++' 是預設的智慧初始化方法
# 它會讓初始群心彼此盡量遠離，大幅改善收斂品質
```

```
  隨機初始化可能發生的問題：

  好的初始化：              壞的初始化：

  C1(*)     C2(*)          C1(*) C2(*)
   o o       x x              o o       x x
   o o       x x              o o       x x

  → 快速收斂到正確分群       → 可能卡在不好的分群

  解法：k-means++ 讓群心一開始就分散！
```

### 陷阱 2：K-Means 假設群是球狀的

```
  K-Means 擅長的資料：       K-Means 搞砸的資料：

   ooo     xxx                oooooooooo
   ooo     xxx                xxxxxxxxxx
   ooo     xxx                oooooooooo
                              xxxxxxxxxx
  （圓形/球狀群）             （長條形/非凸形群）
```

### 陷阱 3：特徵尺度不一致

前面已經提過了，但再說一次：**一定要做 StandardScaler！**

### 陷阱 4：群數量差異大時效果不佳

```
如果一群有 1000 個點，另一群只有 10 個點，
K-Means 可能會「切割」大群來平衡群大小，
而不是正確地識別出小群。
```

---

## ❓ 沒有笨問題

**Q：K-Means 的 K 是什麼意思？一定要事先指定嗎？**

A：K 就是「你要分幾群」，是的，必須事先指定。這是 K-Means 的一個缺點。
不過你可以用手肘法和輪廓係數來幫助你選擇合適的 K 值。

**Q：K-Means 每次跑的結果都不一樣嗎？**

A：如果不設 `random_state`，確實可能不同，因為初始群心是隨機的。
設定 `random_state` 可以固定隨機種子，確保結果可重現。
另外 `n_init=10` 會跑 10 次取最佳，減少隨機性的影響。

**Q：非監督式學習怎麼知道結果「對不對」？**

A：好問題！嚴格來說，沒有絕對的「對錯」。我們用 inertia 和輪廓係數
來評估分群品質，但最終還是要結合 **業務知識（domain knowledge）** 來
判斷分群結果是否有意義。

**Q：K-Means 可以處理類別型特徵嗎？**

A：不行！K-Means 只能處理數值型特徵，因為它要計算「距離」和「平均值」。
如果有類別型特徵，可以考慮用 K-Modes 或 K-Prototypes（不在 scikit-learn 中）。

**Q：如果群不是球形的怎麼辦？**

A：可以考慮其他分群演算法，例如：
- **DBSCAN**：可以找任意形狀的群
- **Gaussian Mixture Model (GMM)**：可以找橢圓形的群
- **Spectral Clustering**：可以處理複雜形狀

---

## K-Means 的限制 vs 替代方案

```
+------------------+------------------+---------------------------+
|     限制          |     原因          |     替代方案               |
+------------------+------------------+---------------------------+
| 需指定 k         | 演算法設計        | DBSCAN（自動決定群數）     |
| 假設球狀群       | 用歐氏距離        | DBSCAN, Spectral          |
| 對異常值敏感     | 群心用平均值      | K-Medoids（用中位數）      |
| 群大小需平衡     | 最小化 inertia   | GMM（軟分群）              |
| 只有硬分群       | 每點只屬一群      | GMM（每點有機率屬於各群）  |
+------------------+------------------+---------------------------+
```

---

## 進階：predict 與 transform

```python
# predict：新資料分到哪一群？
new_customer = scaler.transform([[5000, 15, 350]])
cluster = kmeans.predict(new_customer)
print(f"新客戶被分到群：{cluster[0]}")

# transform：計算到每個群心的距離
distances = kmeans.transform(new_customer)
print(f"到各群心的距離：{distances.round(2)}")
```

```
transform 的應用場景：

距離可以當作「新特徵」！
例如：原本 3 個特徵 → transform 後變成 3 個距離特徵
這在後續的監督式學習中可能很有用。
```

---

## 完整程式碼範例

```python
"""
K-Means 客戶分群完整流程
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score

# 1. 載入/建立資料
np.random.seed(42)
data = pd.DataFrame({
    '年消費金額': np.concatenate([
        np.random.normal(2000, 500, 150),
        np.random.normal(8000, 1500, 200),
        np.random.normal(25000, 5000, 150),
    ]),
    '消費頻率': np.concatenate([
        np.random.normal(5, 2, 150),
        np.random.normal(20, 5, 200),
        np.random.normal(50, 10, 150),
    ]),
})

# 2. 特徵縮放
scaler = StandardScaler()
X_scaled = scaler.fit_transform(data)

# 3. 手肘法 + 輪廓係數
best_k, best_score = 2, -1
for k in range(2, 9):
    km = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels = km.fit_predict(X_scaled)
    score = silhouette_score(X_scaled, labels)
    print(f"k={k}: Silhouette={score:.4f}, Inertia={km.inertia_:.1f}")
    if score > best_score:
        best_k, best_score = k, score

print(f"\n最佳 k = {best_k} (Silhouette = {best_score:.4f})")

# 4. 最終分群
kmeans = KMeans(n_clusters=best_k, random_state=42, n_init=10)
data['客群'] = kmeans.fit_predict(X_scaled)

# 5. 分析結果
print("\n各客群特徵：")
print(data.groupby('客群').agg(['mean', 'count']).round(1))
```

---

## 📝 課後練習

### 練習 1：基礎分群
用 `sklearn.datasets.make_blobs` 產生 4 群的資料，使用 K-Means 分群，
並畫出分群結果和群心。

### 練習 2：手肘法實作
對練習 1 的資料，用 k=1 到 k=8 做手肘法分析，確認 k=4 是否為最佳。

### 練習 3：真實資料
使用 `sklearn.datasets.load_iris()`（不要用 target 欄位），
用 K-Means 把鳶尾花分成 3 群，再跟真正的標籤比較看看準確率如何。

### 練習 4：挑戰題
```python
from sklearn.datasets import make_moons
X, _ = make_moons(n_samples=300, noise=0.1, random_state=42)
```
用 K-Means 對這個「月亮形狀」的資料分群。
觀察結果，思考為什麼 K-Means 在這裡表現不好，
然後試試 `sklearn.cluster.DBSCAN`。

---

## 🧠 動動腦解答

> 如果兩個群心一開始在同一個位置，那麼 Step 2 中每個點到兩個群心的
> 距離都一樣，所有點可能都被分到同一群（取決於實作的平手處理方式）。
> 這就是為什麼 **k-means++ 初始化** 很重要 —— 它確保初始群心分散開來。

---

## 本章回顧

```
+--------------------------------------------------------------+
|  本章學到了                                                    |
+--------------------------------------------------------------+
|                                                              |
|  1. 非監督式學習 = 沒有標籤的學習                               |
|  2. K-Means = 反覆「分配 + 更新群心」直到收斂                   |
|  3. Inertia = 群內平方距離總和（越小越好）                      |
|  4. 手肘法 = 畫 k vs inertia 找轉折點                         |
|  5. 輪廓係數 = 衡量「群內緊密 + 群間分離」（-1 到 +1）          |
|  6. StandardScaler 在 K-Means 中是必須的                      |
|  7. K-Means 假設球狀群，非球狀要用其他方法                      |
|                                                              |
|  下一章：PCA 降維 —— 當你的特徵太多時怎麼辦？                   |
|                                                              |
+--------------------------------------------------------------+
```

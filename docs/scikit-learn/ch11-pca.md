# 第 11 章：PCA 降維 —— 用更少的維度說更多的故事

## 🎯 本章目標

讀完本章後，你將能夠：

1. 理解「維度災難」為什麼會讓模型變差
2. 直覺地理解 PCA 在做什麼
3. 解讀 `explained_variance_ratio_` 來決定保留多少維度
4. 用 PCA 將高維資料降到 2D/3D 並視覺化
5. 在 Pipeline 中結合 PCA 與其他模型
6. 完成 MNIST 手寫數字的降維視覺化

---

## 從一個問題開始

假設你有一份客戶資料，有 200 個特徵：年齡、收入、消費次數、
瀏覽時間、點擊次數、購物車金額......

```
+-----------------------------------------------------+
|   200 個特徵的困擾                                    |
+-----------------------------------------------------+
|                                                     |
|   1. 訓練很慢 —— 200 維的距離計算量很大               |
|   2. 容易過擬合 —— 維度越高，需要越多資料              |
|   3. 無法視覺化 —— 人類只能看到 2D 或 3D               |
|   4. 很多特徵彼此高度相關（冗餘資訊）                   |
|                                                     |
|   你需要一種方法，用更少的維度保留最多的資訊！           |
|                                                     |
+-----------------------------------------------------+
```

這就是 **PCA（主成分分析，Principal Component Analysis）** 要解決的問題。

---

## 💡 重點觀念：維度災難（Curse of Dimensionality）

「維度災難」聽起來很嚇人，但概念很簡單：

> 當維度增加時，資料點之間的距離越來越「均勻」，
> 導致基於距離的演算法（KNN、K-Means 等）效果變差。

```
用一個比喻來理解：

1 維空間（一條線）：
  |----o---o----o-----|
  點之間有明顯的遠近之分

2 維空間（一個平面）：
  +---o----------+
  |        o     |
  |   o       o  |
  |      o       |
  +-----------o--+
  點開始分散，但還行

100 維空間：
  所有點到彼此的距離都差不多！
  「最近」和「最遠」的差異變得微乎其微。

  → 「在高維空間中，所有人都是陌生人。」
```

### 數學上的直覺

```
在 d 維單位超球體中，隨著 d 增加：
- 資料集中在球體表面
- 任意兩點的距離趨於相同
- 「鄰居」的概念失去意義

  d=2:   面積 = pi * r^2
  d=3:   體積 = (4/3) * pi * r^3
  d=100: 幾乎所有體積都在表面薄殼中！

需要的資料量隨維度「指數級」增長：
  d=1:  需要 ~10 個點
  d=2:  需要 ~100 個點 (10^2)
  d=3:  需要 ~1000 個點 (10^3)
  d=100: 需要 10^100 個點......（比宇宙原子數還多！）
```

---

## PCA 到底在做什麼？—— 用比喻來理解

### 比喻 1：影子

想像你有一個 3D 物體（比如一隻恐龍模型），你想把它的「形狀」
記錄在一張 2D 紙上。你會怎麼做？

**打光投影！**

但投影的角度很重要：

```
  好的角度（保留最多資訊）：    壞的角度（資訊大量流失）：

     /\                          |
    /  \                         |  ← 從正面看只剩一條線
   /    \___                     |
  /    /    \                    |
 /    /      |
      恐龍側面影子                 恐龍正面影子
  → 還能看出是恐龍               → 什麼都看不出來
```

**PCA 就是在找「最好的投影角度」，讓投影後的資料保留最多的資訊（變異數）。**

### 比喻 2：考試成績

假設一個班級有兩次考試成績：

```
國文分數 vs 英文分數：

  英文
   |        .  .
   |      .  .  .
   |    .  .  .
   |  .  .  .
   |.  .  .
   +------------------→ 國文

兩科成績高度相關（國文好的人英文通常也好）
```

PCA 會找到資料「伸展最長的方向」作為第一主成分：

```
  英文
   |        .  .
   |      .  .  . ← PC1 方向（沿著資料伸展的方向）
   |    .  .  .  /
   |  .  .  . /
   |.  .  . /
   +------/----------→ 國文
         /
        PC1 ≈ 「整體學業能力」
        PC2 ≈ 「國文 vs 英文的偏好」（垂直於 PC1）
```

```
+-----------------------------------------------------+
|   PCA 的核心思想                                      |
+-----------------------------------------------------+
|                                                     |
|   找到一組新的座標軸（主成分），使得：                   |
|                                                     |
|   - PC1 = 資料變異數最大的方向（最重要）               |
|   - PC2 = 與 PC1 垂直，變異數第二大的方向              |
|   - PC3 = 與 PC1, PC2 都垂直，變異數第三大             |
|   - ...以此類推                                      |
|                                                     |
|   然後只保留前幾個主成分，丟掉剩下的。                  |
|   → 降維完成！                                       |
|                                                     |
+-----------------------------------------------------+
```

---

## PCA 演算法步驟

```
┌─────────────────────────────────────────────────────┐
│              PCA 演算法流程                            │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Step 1: 標準化資料（讓每個特徵均值=0，標準差=1）       │
│          ↓                                          │
│  Step 2: 計算共變異矩陣（Covariance Matrix）          │
│          ↓                                          │
│  Step 3: 計算共變異矩陣的特徵值和特徵向量              │
│          ↓                                          │
│  Step 4: 依特徵值大小排序（大 → 小）                   │
│          ↓                                          │
│  Step 5: 選前 k 個特徵向量作為新座標軸                 │
│          ↓                                          │
│  Step 6: 將資料投影到新座標軸上 → 降維完成！            │
│                                                     │
└─────────────────────────────────────────────────────┘
```

> 別擔心，你不需要手算這些。scikit-learn 一行搞定。
> 但理解流程能幫助你解讀結果。

---

## 🧠 動動腦

> 為什麼 PCA 之前要做標準化？
>
> 提示：如果有一個特徵的範圍是 0~100000（如年薪），
> 另一個特徵範圍是 0~5（如評分），哪個特徵的「變異數」會比較大？
> PCA 會優先保留哪個方向？
>
> （答案在本章最後）

---

## 用 scikit-learn 實作 PCA

### 基礎範例：2D 降到 1D

```python
import numpy as np
import matplotlib.pyplot as plt
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

# 產生有相關性的 2D 資料
np.random.seed(42)
X = np.random.randn(200, 2)
X[:, 1] = X[:, 0] * 0.8 + np.random.randn(200) * 0.3

# 標準化
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# PCA 降到 1 維
pca = PCA(n_components=1)
X_pca = pca.fit_transform(X_scaled)

print(f"原始維度：{X_scaled.shape}")   # (200, 2)
print(f"降維後：  {X_pca.shape}")      # (200, 1)
print(f"保留的變異數比例：{pca.explained_variance_ratio_[0]:.4f}")
```

### 視覺化降維過程

```python
fig, axes = plt.subplots(1, 3, figsize=(15, 4))

# 原始 2D 資料
axes[0].scatter(X_scaled[:, 0], X_scaled[:, 1], s=20, alpha=0.5)
axes[0].set_title('原始 2D 資料')
axes[0].set_xlabel('特徵 1')
axes[0].set_ylabel('特徵 2')
axes[0].set_aspect('equal')

# 畫出主成分方向
origin = [0, 0]
pc1_dir = pca.components_[0]
axes[0].annotate('', xy=pc1_dir*2, xytext=origin,
                 arrowprops=dict(arrowstyle='->', color='red', lw=2))
axes[0].text(pc1_dir[0]*2.2, pc1_dir[1]*2.2, 'PC1',
             color='red', fontsize=12, fontweight='bold')

# 投影到 PC1 上
X_reconstructed = pca.inverse_transform(X_pca)
axes[1].scatter(X_reconstructed[:, 0], X_reconstructed[:, 1],
                s=20, alpha=0.5, color='orange')
axes[1].set_title('投影到 PC1（重建）')
axes[1].set_xlabel('特徵 1')
axes[1].set_ylabel('特徵 2')
axes[1].set_aspect('equal')

# 1D 表示
axes[2].scatter(X_pca[:, 0], np.zeros_like(X_pca[:, 0]),
                s=20, alpha=0.5, color='green')
axes[2].set_title('降到 1D 的結果')
axes[2].set_xlabel('PC1')
axes[2].set_yticks([])

plt.tight_layout()
plt.show()
```

```
原始 2D 資料：       投影到 PC1：        1D 結果：

  . .  .  . .        . .  .  . .         .  . . .. . .  .
 . . .. . .          . . .. . .          ─────────────────→
. . . .. .          ─────────────→           PC1
  . . . .           （所有點被壓到
 . . .. .             這條線上）
```

---

## 💡 重點觀念：explained_variance_ratio_

這是 PCA 最重要的屬性之一！它告訴你 **每個主成分保留了多少百分比的資訊**。

```python
# 用 iris 資料集來看
from sklearn.datasets import load_iris

iris = load_iris()
X_iris = StandardScaler().fit_transform(iris.data)

# 保留所有主成分
pca_full = PCA()
pca_full.fit(X_iris)

print("各主成分的解釋變異比例：")
for i, ratio in enumerate(pca_full.explained_variance_ratio_):
    print(f"  PC{i+1}: {ratio:.4f} ({ratio*100:.1f}%)")

print(f"\n累積解釋變異比例：")
cumsum = np.cumsum(pca_full.explained_variance_ratio_)
for i, cum in enumerate(cumsum):
    print(f"  PC1~PC{i+1}: {cum:.4f} ({cum*100:.1f}%)")
```

```
各主成分的解釋變異比例：
  PC1: 0.7296 (73.0%)      ← 第一個主成分就捕捉了 73% 的資訊！
  PC2: 0.2285 (22.9%)      ← 前兩個合計 95.8%
  PC3: 0.0367 (3.7%)
  PC4: 0.0052 (0.5%)

累積解釋變異比例：
  PC1~PC1: 0.7296 (73.0%)
  PC1~PC2: 0.9581 (95.8%)  ← 只需 2 個主成分就保留 95.8%！
  PC1~PC3: 0.9948 (99.5%)
  PC1~PC4: 1.0000 (100.0%)
```

### 累積變異數圖

```python
plt.figure(figsize=(8, 4))
cumsum = np.cumsum(pca_full.explained_variance_ratio_)
plt.bar(range(1, 5), pca_full.explained_variance_ratio_,
        alpha=0.6, label='個別')
plt.step(range(1, 5), cumsum, where='mid',
         color='red', linewidth=2, label='累積')
plt.axhline(y=0.95, color='gray', linestyle='--', label='95% 門檻')
plt.xlabel('主成分')
plt.ylabel('解釋變異比例')
plt.title('Scree Plot（碎石圖）')
plt.xticks(range(1, 5), ['PC1', 'PC2', 'PC3', 'PC4'])
plt.legend()
plt.show()
```

```
  1.0 |          ___________
      |         /
  0.9 |--------/------------ 95% 門檻
      |       /
  0.8 |      /
      |     /
  0.7 | ===/
      | | |
  0.6 | | |
      | | |
      | | |  ===
  0.2 | | |  | |
      | | |  | |  =
  0.0 +--+----+----+----+→
      PC1   PC2  PC3  PC4
      73%   23%   4%   1%
```

---

## 要保留幾個主成分？

### 方法 1：設定變異數門檻

```python
# 保留 95% 的變異數
pca_95 = PCA(n_components=0.95)  # 傳入小數 = 自動選主成分數
pca_95.fit(X_iris)
print(f"保留 95% 變異需要 {pca_95.n_components_} 個主成分")
```

### 方法 2：指定主成分數

```python
# 明確指定要降到幾維
pca_2d = PCA(n_components=2)
X_2d = pca_2d.fit_transform(X_iris)
print(f"降到 2D，保留 {sum(pca_2d.explained_variance_ratio_)*100:.1f}% 變異")
```

### 方法 3：看碎石圖找拐點

就像 K-Means 的手肘法，找累積變異數曲線變平的地方。

```
+-----------------------------------------------------+
|   選擇主成分數量的經驗法則                              |
+-----------------------------------------------------+
|                                                     |
|   1. 視覺化目的 → 2 或 3 個主成分                     |
|   2. 機器學習前處理 → 保留 95% 變異                   |
|   3. 降低計算成本 → 保留 90% 變異                     |
|   4. 資料壓縮儲存 → 看可接受的精度損失                  |
|                                                     |
+-----------------------------------------------------+
```

---

## 🔥 實戰案例：MNIST 手寫數字降維視覺化

MNIST 是機器學習界的「Hello World」資料集 —— 28x28 像素的手寫數字圖片。

每張圖片 = 784 個像素 = **784 維**！人類無法想像 784 維空間。
但 PCA 可以幫我們把它壓縮到 2D 來看。

### 載入資料

```python
from sklearn.datasets import fetch_openml

# 載入 MNIST（可能需要幾分鐘下載）
# 如果下載太慢，可以用 load_digits() 替代（8x8 像素版本）
from sklearn.datasets import load_digits
digits = load_digits()
X_digits = digits.data       # (1797, 64) — 64 維
y_digits = digits.target     # 0~9 的標籤

print(f"資料形狀：{X_digits.shape}")
print(f"特徵數量：{X_digits.shape[1]}")
print(f"標籤種類：{np.unique(y_digits)}")
```

### 用 PCA 降到 2D

```python
from sklearn.preprocessing import StandardScaler

# 標準化
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X_digits)

# PCA 降到 2D
pca_2d = PCA(n_components=2)
X_2d = pca_2d.fit_transform(X_scaled)

print(f"降維前：{X_scaled.shape}")      # (1797, 64)
print(f"降維後：{X_2d.shape}")           # (1797, 2)
print(f"保留變異：{sum(pca_2d.explained_variance_ratio_)*100:.1f}%")
```

### 視覺化！

```python
plt.figure(figsize=(10, 8))
scatter = plt.scatter(
    X_2d[:, 0], X_2d[:, 1],
    c=y_digits, cmap='tab10',
    s=10, alpha=0.6
)
plt.colorbar(scatter, label='數字')
plt.xlabel('PC1')
plt.ylabel('PC2')
plt.title('MNIST 手寫數字 — PCA 2D 視覺化')
plt.show()
```

```
預期看到的結果：

  PC2
   |
   |    111          000
   |   1 1 1       0  0  0
   |    111          000
   |
   |        77777          444
   |       7   7          4 4
   |          7            44
   |
   +-----------------------------→ PC1

不同數字會大致聚成不同的群！
（雖然有些數字會重疊，例如 3 和 8）
```

### 看看保留更多主成分的效果

```python
# 不同主成分數量保留的變異
pca_full = PCA().fit(X_scaled)
cumsum = np.cumsum(pca_full.explained_variance_ratio_)

plt.figure(figsize=(8, 4))
plt.plot(range(1, len(cumsum)+1), cumsum, 'b-', linewidth=2)
plt.axhline(y=0.90, color='orange', linestyle='--', label='90%')
plt.axhline(y=0.95, color='red', linestyle='--', label='95%')
plt.xlabel('主成分數量')
plt.ylabel('累積解釋變異比例')
plt.title('MNIST: 需要多少主成分？')
plt.legend()
plt.grid(True, alpha=0.3)
plt.show()

# 找出保留 95% 需要多少主成分
n_95 = np.argmax(cumsum >= 0.95) + 1
print(f"保留 95% 變異需要 {n_95} 個主成分（原始 64 個）")
```

```
64 維 → ~28 維就能保留 95% 的資訊
      → 壓縮了 56%！模型訓練速度會快很多！
```

---

## PCA 搭配分類器 —— Pipeline 實作

PCA 不只是用來視覺化，更常見的用途是作為 **前處理步驟**，
放在分類/回歸模型之前，減少特徵數量。

```python
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split, cross_val_score

X_train, X_test, y_train, y_test = train_test_split(
    X_digits, y_digits, test_size=0.2, random_state=42
)

# 方法 1：不用 PCA
pipe_no_pca = Pipeline([
    ('scaler', StandardScaler()),
    ('clf', LogisticRegression(max_iter=5000, random_state=42)),
])

# 方法 2：用 PCA 保留 95% 變異
pipe_with_pca = Pipeline([
    ('scaler', StandardScaler()),
    ('pca', PCA(n_components=0.95)),
    ('clf', LogisticRegression(max_iter=5000, random_state=42)),
])

# 比較！
import time

for name, pipe in [('不用 PCA', pipe_no_pca), ('用 PCA', pipe_with_pca)]:
    start = time.time()
    scores = cross_val_score(pipe, X_train, y_train, cv=5, scoring='accuracy')
    elapsed = time.time() - start
    print(f"{name}: 準確率={scores.mean():.4f} (+/- {scores.std():.4f}), "
          f"耗時={elapsed:.2f}s")
```

```
預期結果：

不用 PCA: 準確率=0.9650 (+/- 0.0080), 耗時=2.34s
用 PCA:   準確率=0.9620 (+/- 0.0090), 耗時=0.89s
                 ↑                          ↑
          準確率幾乎一樣！              但快了 2.6 倍！
```

```
+-----------------------------------------------------+
|   PCA 在 Pipeline 中的角色                            |
+-----------------------------------------------------+
|                                                     |
|   原始資料                                           |
|     ↓                                               |
|   StandardScaler（標準化）                            |
|     ↓                                               |
|   PCA（降維）  ← 減少特徵數，保留關鍵資訊              |
|     ↓                                               |
|   分類器/回歸器（模型訓練）                             |
|     ↓                                               |
|   預測結果                                            |
|                                                     |
|   好處：                                              |
|   - 訓練更快                                          |
|   - 減少過擬合風險                                    |
|   - 去除特徵間的多重共線性                             |
|                                                     |
+-----------------------------------------------------+
```

---

## ⚠️ 常見陷阱

### 陷阱 1：忘記標準化

```
+-----------------------------------------------------+
|   PCA 找的是「變異數最大的方向」                        |
|                                                     |
|   如果不標準化：                                      |
|   特徵 A（年薪）：10,000 ~ 1,000,000 → 變異數超大     |
|   特徵 B（年齡）：20 ~ 80           → 變異數很小      |
|                                                     |
|   PCA 會覺得特徵 A 最重要，完全忽略特徵 B              |
|   但這只是因為「尺度」不同，不是因為 A 真的更重要！      |
|                                                     |
|   解法：永遠在 PCA 之前做 StandardScaler              |
+-----------------------------------------------------+
```

### 陷阱 2：對 PCA 後的主成分做過度解讀

```python
# PCA 後的主成分是原始特徵的「線性組合」
# PC1 = 0.5*特徵A + 0.3*特徵B - 0.2*特徵C + ...
# 不一定有直覺的物理意義！

print("PC1 的組成：")
print(pca_2d.components_[0])  # 每個原始特徵的權重
```

### 陷阱 3：在測試集上重新 fit PCA

```python
# 錯誤做法 ❌
pca.fit(X_train)
X_train_pca = pca.transform(X_train)
pca.fit(X_test)        # 不可以！會用不同的投影方向！
X_test_pca = pca.transform(X_test)

# 正確做法 ✅
pca.fit(X_train)
X_train_pca = pca.transform(X_train)
X_test_pca = pca.transform(X_test)  # 用 train 的投影方向！

# 最佳做法 ✅✅✅ 用 Pipeline，自動處理
pipe = Pipeline([
    ('scaler', StandardScaler()),
    ('pca', PCA(n_components=0.95)),
    ('clf', LogisticRegression(max_iter=5000)),
])
pipe.fit(X_train, y_train)
pipe.score(X_test, y_test)  # Pipeline 內部自動正確處理
```

### 陷阱 4：PCA 不適合非線性資料

```
PCA 找的是「線性」方向，如果資料的結構是非線性的：

  線性結構（PCA 擅長）：    非線性結構（PCA 很慘）：

     . .  . .                    ...
    . . .. .                   ..   ..
   . . . .                    .       .
  . . .. .                    .       .
                               ..   ..
                                 ...
  （橢圓形）                   （甜甜圈形）

  非線性替代方案：t-SNE, UMAP, Kernel PCA
```

---

## 進階：t-SNE 與 PCA 的比較

```python
from sklearn.manifold import TSNE

# t-SNE 降到 2D（注意：t-SNE 很慢！）
tsne = TSNE(n_components=2, random_state=42, perplexity=30)
X_tsne = tsne.fit_transform(X_scaled)

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

ax1.scatter(X_2d[:, 0], X_2d[:, 1], c=y_digits, cmap='tab10', s=10, alpha=0.6)
ax1.set_title('PCA 2D')
ax1.set_xlabel('PC1')
ax1.set_ylabel('PC2')

ax2.scatter(X_tsne[:, 0], X_tsne[:, 1], c=y_digits, cmap='tab10', s=10, alpha=0.6)
ax2.set_title('t-SNE 2D')
ax2.set_xlabel('t-SNE 1')
ax2.set_ylabel('t-SNE 2')

plt.tight_layout()
plt.show()
```

```
+------------------+------------------+
|   PCA            |   t-SNE          |
+------------------+------------------+
| 線性降維         | 非線性降維       |
| 很快             | 很慢             |
| 可以 transform   | 不能 transform   |
|   新資料         |   新資料         |
| 保留全局結構     | 保留局部結構     |
| 適合前處理       | 適合視覺化       |
+------------------+------------------+
```

---

## ❓ 沒有笨問題

**Q：PCA 會改變資料的「意義」嗎？**

A：PCA 只是做了一個「旋轉 + 投影」。新的座標軸（主成分）是原始特徵的
線性組合。資訊被壓縮了，但不是被「扭曲」了。可以把它想成
「換一個角度看同一份資料」。

**Q：如果我保留所有主成分，結果會跟原始資料一樣嗎？**

A：是的！保留所有主成分 = 只是做了一次旋轉，沒有降維。
`inverse_transform` 可以把資料轉回原始空間，
如果保留了所有主成分，重建結果和原始資料完全一樣。

**Q：PCA 可以用在非監督式學習嗎？**

A：當然！PCA 本身就是非監督式的（它不需要標籤 y）。
它常和 K-Means 搭配：先用 PCA 降維，再用 K-Means 分群。

**Q：為什麼有時候用 PCA 反而讓模型變差？**

A：可能原因：
1. 降維太多，丟掉了重要資訊
2. 資料中重要的特徵恰好變異數不大
3. 非線性結構被 PCA 的線性假設破壞

**Q：`n_components` 設成小數（如 0.95）和整數（如 10）有什麼不同？**

A：小數 = 自動選擇保留指定比例變異數所需的最少主成分數。
整數 = 直接指定要保留幾個主成分。小數版本更方便，讓 PCA 自己決定。

---

## 完整程式碼範例

```python
"""
PCA 降維完整流程：MNIST 數字辨識
"""
import numpy as np
from sklearn.datasets import load_digits
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.model_selection import train_test_split
import matplotlib.pyplot as plt

# 1. 載入資料
digits = load_digits()
X, y = digits.data, digits.target
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# 2. 探索需要多少主成分
pca_explore = PCA().fit(StandardScaler().fit_transform(X_train))
cumsum = np.cumsum(pca_explore.explained_variance_ratio_)
n_90 = np.argmax(cumsum >= 0.90) + 1
n_95 = np.argmax(cumsum >= 0.95) + 1
print(f"保留 90% 需要 {n_90} 個主成分")
print(f"保留 95% 需要 {n_95} 個主成分")
print(f"原始特徵數：{X.shape[1]}")

# 3. 建立 Pipeline
pipe = Pipeline([
    ('scaler', StandardScaler()),
    ('pca', PCA(n_components=0.95)),
    ('clf', LogisticRegression(max_iter=5000, random_state=42)),
])

# 4. 訓練與評估
pipe.fit(X_train, y_train)
train_acc = pipe.score(X_train, y_train)
test_acc = pipe.score(X_test, y_test)
n_components = pipe.named_steps['pca'].n_components_

print(f"\nPCA 保留 {n_components} 個主成分")
print(f"訓練準確率：{train_acc:.4f}")
print(f"測試準確率：{test_acc:.4f}")

# 5. 視覺化
pca_2d = PCA(n_components=2)
X_vis = pca_2d.fit_transform(StandardScaler().fit_transform(X))

plt.figure(figsize=(10, 8))
scatter = plt.scatter(X_vis[:, 0], X_vis[:, 1],
                      c=y, cmap='tab10', s=10, alpha=0.6)
plt.colorbar(scatter, label='數字')
plt.xlabel(f'PC1 ({pca_2d.explained_variance_ratio_[0]*100:.1f}%)')
plt.ylabel(f'PC2 ({pca_2d.explained_variance_ratio_[1]*100:.1f}%)')
plt.title('MNIST Digits — PCA 2D Visualization')
plt.show()
```

---

## 📝 課後練習

### 練習 1：基礎 PCA
用 `load_iris()` 資料集，做 PCA 降到 2D，畫出散佈圖並用不同顏色
標示三種鳶尾花。觀察哪兩種最容易被 PCA 分開。

### 練習 2：成分分析
延續練習 1，印出 PC1 和 PC2 的 `components_`（權重），
看看哪些原始特徵對 PC1 貢獻最大。

### 練習 3：Pipeline 比較
用 `load_digits()` 比較以下三種 Pipeline 的交叉驗證準確率和速度：
- 不用 PCA
- PCA 保留 90% 變異
- PCA 保留 80% 變異

### 練習 4：挑戰題
在 MNIST digits 資料上，先用 PCA 降到 10 維，再用 K-Means (k=10) 分群。
用 `sklearn.metrics.adjusted_rand_score` 比較分群結果和真實標籤的吻合度。

---

## 🧠 動動腦解答

> 為什麼 PCA 之前要做標準化？
>
> 因為 PCA 找的是「變異數最大的方向」。如果特徵的尺度不同，
> 數值範圍大的特徵（如年薪 10000~1000000）自然變異數大，
> PCA 會以為它最重要，完全忽略小尺度特徵（如年齡 20~80）。
> 標準化讓所有特徵站在「同一起跑線」，才能公平比較。

---

## 本章回顧

```
+--------------------------------------------------------------+
|  本章學到了                                                    |
+--------------------------------------------------------------+
|                                                              |
|  1. 維度災難 = 維度越高，資料越稀疏，模型越難學                  |
|  2. PCA = 找到資料變異數最大的方向，投影上去                     |
|  3. explained_variance_ratio_ = 每個主成分保留多少資訊          |
|  4. 選主成分數：碎石圖 / 95%門檻 / n_components=0.95           |
|  5. PCA 之前一定要 StandardScaler                             |
|  6. PCA 在 Pipeline 中可以加速訓練、減少過擬合                  |
|  7. PCA 是線性方法，非線性資料考慮 t-SNE / UMAP               |
|                                                              |
|  下一章：異常偵測 —— 找出那些「不對勁」的資料！                  |
|                                                              |
+--------------------------------------------------------------+
```

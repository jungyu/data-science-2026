# 第 4 週：模型訓練與資料切分

> 模型在訓練集上表現好，就夠了嗎？

---

## 🎯 學習核心

- 為什麼必須切分資料
- 過擬合（overfitting）與欠擬合（underfitting）
- 交叉驗證（cross-validation）的原理與實作
- 資料洩漏（data leakage）的危險

---

## 為什麼這件事重要？

你訓練了一個模型，在訓練資料上準確率 99%。你興奮地向主管報告。

主管問：「上線後效果怎樣？」

答案：準確率掉到 60%。

**這就是過擬合** — 模型「背」了訓練資料，但沒有學到真正的規律。就像一個學生背了所有考古題，但遇到新題目就不會做。

更可怕的是**資料洩漏** — 你的模型在訓練時「偷看」了它不應該知道的資訊，導致評估結果虛假地好。上線後才發現一切都是假象。

---

## 核心概念

### 1️⃣ Train / Validation / Test 三分法

![資料切分](https://framerusercontent.com/images/qHCBprH2QBdww2TTap3IKNBTkUM.png?height=886&width=1240)

```
全部資料
├── Training Set（60-70%）
│   └── 用來訓練模型
├── Validation Set（15-20%）
│   └── 用來調整超參數、選擇模型
└── Test Set（15-20%）
    └── 最後一次評估，只能用一次
```

**關鍵規則**：

| 資料集 | 用途 | 使用頻率 | 注意事項 |
|--------|------|---------|---------|
| Training | 學習模式 | 每次訓練都用 | 模型會「看到」這些資料 |
| Validation | 調參數、選模型 | 反覆使用 | 不能讓模型直接學習 |
| Test | 最終評估 | **只用一次** | 代表「未來的真實世界」 |

> ⚠️ **常見錯誤**：反覆用 Test Set 來調整模型，等於把 Test Set 變成了另一個 Validation Set。你需要一個「真正沒看過的」資料來做最終評估。

---

### 2️⃣ Bias-Variance Tradeoff

![Bias-Variance](https://miro.medium.com/1*_7OPgojau8hkiPUiHoGK_w.png)

每個模型的誤差可以分解為三個部分：

```
Total Error = Bias² + Variance + Irreducible Noise
```

| | 高 Bias | 低 Bias |
|--|--------|---------|
| **高 Variance** | 最糟：又偏又不穩定 | 過擬合：太複雜 |
| **低 Variance** | 欠擬合：太簡單 | 最佳：又準又穩定 |

**模型太簡單（欠擬合）**：
- 訓練誤差高，測試誤差也高
- 模型沒有捕捉到資料中的規律
- 例：用線性模型擬合非線性資料

**模型太複雜（過擬合）**：
- 訓練誤差低，但測試誤差高
- 模型記住了雜訊（noise），而不是信號（signal）
- 例：用 100 次多項式擬合 10 個資料點

```
模型複雜度 →

    ↑ 誤差
    │   ╲  訓練誤差
    │    ╲___________
    │
    │        ___________╱  測試誤差
    │       ╱
    │
    └──────────────────→
          Sweet Spot（最佳複雜度）
```

---

### 3️⃣ 交叉驗證（Cross-Validation）

![K-Fold CV](https://www.researchgate.net/publication/332370436/figure/fig1/AS%3A746775958806528%401555056671117/Diagram-of-k-fold-cross-validation-with-k-10-Image-from-Karl-Rosaen-Log.ppm)

當資料量有限時，單一的 train/validation split 可能不夠穩定。交叉驗證的做法：

**K-Fold Cross-Validation**：
1. 將資料分成 K 等份（通常 K = 5 或 10）
2. 每次用 K-1 份訓練，1 份驗證
3. 重複 K 次，每份都當過驗證集
4. 取 K 次結果的平均

**優點**：
- 每筆資料都被驗證過一次
- 結果更穩定、不依賴特定的分割方式
- 充分利用有限的資料

**特殊變體**：

| 方法 | K 值 | 適用場景 |
|------|------|---------|
| 5-Fold | 5 | 一般用途（最常用） |
| 10-Fold | 10 | 資料量中等，想更穩定 |
| LOOCV | n | 資料量極少（<100） |
| Stratified K-Fold | 任意 | 類別不平衡時 |
| Time Series Split | 任意 | 時間序列資料 |

---

### 4️⃣ 資料洩漏（Data Leakage）

![Data Leakage](https://codingnomads.com/images/f8c470c9-c714-48e6-0397-7a9a4e57b500/public)

**資料洩漏**是指訓練過程中，模型接觸到了它在實際應用中不可能知道的資訊。

**常見洩漏場景**：

| 場景 | 問題 | 解法 |
|------|------|------|
| 先做特徵工程再切資料 | 標準化用了全部資料的均值 | 先切資料再做特徵工程 |
| 用未來的資料預測過去 | 時間序列中用了後續的觀測值 | 用時間切分（Time Split） |
| 特徵包含目標的衍生資訊 | 例如用「退貨金額」預測「是否退貨」 | 仔細審查每個特徵的因果方向 |
| 重複的資料跨越 train/test | 同一筆資料出現在兩個集合 | 去重後再切分 |

> 🚨 **資料洩漏是最隱蔽的錯誤**，因為你的指標看起來很好，但上線後會完全崩潰。

---

## 🧪 實作任務

### 任務 A：親眼看見過擬合

```python
import numpy as np
import matplotlib.pyplot as plt
from sklearn.preprocessing import PolynomialFeatures
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error

np.random.seed(42)

# 產生真實關係：y = sin(x) + noise
n = 30
X = np.sort(np.random.uniform(0, 2 * np.pi, n))
y = np.sin(X) + np.random.normal(0, 0.3, n)

X_test = np.linspace(0, 2 * np.pi, 200)
y_test_true = np.sin(X_test)

# 嘗試不同複雜度的多項式
degrees = [1, 3, 5, 15]
fig, axes = plt.subplots(2, 2, figsize=(12, 10))

for ax, degree in zip(axes.flat, degrees):
    poly = PolynomialFeatures(degree)
    X_poly = poly.fit_transform(X.reshape(-1, 1))
    X_test_poly = poly.transform(X_test.reshape(-1, 1))

    model = LinearRegression()
    model.fit(X_poly, y)

    y_pred_train = model.predict(X_poly)
    y_pred_test = model.predict(X_test_poly)

    train_mse = mean_squared_error(y, y_pred_train)

    ax.scatter(X, y, color='blue', alpha=0.6, label='訓練資料')
    ax.plot(X_test, y_test_true, 'g--', label='真實函數', alpha=0.7)
    ax.plot(X_test, y_pred_test, 'r-', label=f'模型 (degree={degree})')
    ax.set_title(f'多項式 degree={degree}\nTrain MSE={train_mse:.4f}')
    ax.legend(fontsize=8)
    ax.set_ylim(-2, 2)

plt.tight_layout()
plt.show()
```

**觀察**：
- 哪個 degree 的訓練誤差最低？
- 哪個 degree 最接近真實函數？
- 為什麼訓練誤差最低的模型不一定最好？

### 任務 B：交叉驗證實作

```python
from sklearn.model_selection import cross_val_score
from sklearn.pipeline import make_pipeline

# 用交叉驗證選擇最佳的多項式度數
degrees = range(1, 16)
cv_means = []
cv_stds = []

for d in degrees:
    model = make_pipeline(
        PolynomialFeatures(d),
        LinearRegression()
    )
    scores = cross_val_score(model, X.reshape(-1, 1), y,
                             cv=5, scoring='neg_mean_squared_error')
    cv_means.append(-scores.mean())
    cv_stds.append(scores.std())

# 畫出結果
plt.figure(figsize=(10, 6))
plt.errorbar(degrees, cv_means, yerr=cv_stds, marker='o', capsize=5)
plt.xlabel('多項式度數')
plt.ylabel('CV 平均 MSE')
plt.title('交叉驗證：選擇最佳模型複雜度')
plt.axvline(x=degrees[np.argmin(cv_means)], color='r',
            linestyle='--', label=f'最佳 degree = {degrees[np.argmin(cv_means)]}')
plt.legend()
plt.show()

print(f"交叉驗證建議的最佳度數：{degrees[np.argmin(cv_means)]}")
```

### 任務 C：資料洩漏偵測

```python
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.datasets import make_classification

# 產生分類資料
X_data, y_data = make_classification(n_samples=500, n_features=20,
                                      n_informative=5, random_state=42)

# ❌ 錯誤做法：先標準化再切分（洩漏！）
scaler_wrong = StandardScaler()
X_scaled_wrong = scaler_wrong.fit_transform(X_data)  # 用了全部資料的均值/標準差
X_tr_w, X_te_w, y_tr_w, y_te_w = train_test_split(X_scaled_wrong, y_data,
                                                     test_size=0.2, random_state=42)
model_wrong = LogisticRegression(max_iter=1000)
model_wrong.fit(X_tr_w, y_tr_w)
score_wrong = model_wrong.score(X_te_w, y_te_w)

# ✅ 正確做法：先切分再標準化
X_tr, X_te, y_tr, y_te = train_test_split(X_data, y_data,
                                            test_size=0.2, random_state=42)
scaler_right = StandardScaler()
X_tr_scaled = scaler_right.fit_transform(X_tr)  # 只用訓練集的均值/標準差
X_te_scaled = scaler_right.transform(X_te)       # 用訓練集的參數轉換測試集
model_right = LogisticRegression(max_iter=1000)
model_right.fit(X_tr_scaled, y_tr)
score_right = model_right.score(X_te_scaled, y_te)

print(f"洩漏版本的準確率：{score_wrong:.4f}")
print(f"正確版本的準確率：{score_right:.4f}")
print(f"差異：{score_wrong - score_right:.4f}")
print("\n在這個例子中差異可能很小，但在真實場景中可能差很多。")
print("重點不是差多少，而是養成正確的習慣。")
```

---

## 🧠 反思問題

1. **為什麼測試集只能用一次？** 如果你反覆用測試集來選模型，會發生什麼？

2. **在時間序列問題中，為什麼不能用隨機切分？** 舉一個具體的例子說明可能的洩漏。

3. **「模型在訓練集上表現很差」一定是壞事嗎？** 什麼情況下這可能是合理的？

4. **你在實際工作中，如何檢查是否有資料洩漏？** 列出 3 個具體的檢查步驟。

---

## 延伸閱讀

- [Scikit-learn: Cross-validation](https://scikit-learn.org/stable/modules/cross_validation.html) — 官方文件
- Hastie, Tibshirani & Friedman, *The Elements of Statistical Learning* — 第 7 章
- [Kaggle: Data Leakage](https://www.kaggle.com/alexisbcook/data-leakage) — 實務案例

---

## 本週 Checklist

- [ ] 完成任務 A：視覺化過擬合
- [ ] 完成任務 B：交叉驗證選模型
- [ ] 完成任務 C：資料洩漏偵測
- [ ] 回答全部反思問題
- [ ] 將程式碼與筆記推送至 GitHub

---

[← 上一週：因果推論與實驗設計](week-03-causal-inference.md) ｜ [→ 下一週：模型評估與指標選擇](week-05-model-evaluation.md)

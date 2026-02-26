# Chapter 5: 邏輯斯回歸與分類評估 - 當答案只有「是」或「不是」

> 「世界上有些問題，不是問你多少，而是問你是不是。
>   邏輯斯回歸，就是把『是或不是』變成數學的藝術。」

---

## 🎯 本章目標

讀完這一章，你將能夠：

1. 理解邏輯斯回歸如何從線性回歸演變而來
2. 用 scikit-learn 的 `LogisticRegression` 建立分類模型
3. 理解並繪製混淆矩陣（Confusion Matrix）
4. 掌握 Accuracy、Precision、Recall、F1 四大指標的差異
5. 理解 ROC 曲線與 AUC 的概念
6. 透過癌症偵測案例，體會「選錯指標」的嚴重後果
7. 認識分類閾值（threshold）對結果的影響

---

## 從回歸到分類：一個思想實驗

上一章，我們用線性回歸預測房價（一個連續的數字）。
但如果問題變成：

> 「這封信是不是垃圾郵件？」
> 「這個腫瘤是良性還是惡性？」
> 「這個客戶會不會流失？」

答案只有兩個：**是（1）** 或 **不是（0）**。

如果硬用線性回歸來做，會發生什麼事？

```
線性回歸預測「是否為垃圾郵件」：

 預測值
  2.0 |                        *
  1.5 |                    *
  1.0 |────────────────*──────────  ← 1 = 垃圾郵件
  0.5 |            *
  0.0 |────────*──────────────────  ← 0 = 正常郵件
 -0.5 |    *
 -1.0 | *
      +──────────────────────────> 特徵
          預測值可能超過 1 或低於 0
          這在「機率」上毫無意義！
```

我們需要一個函數，把任何數值壓縮到 0 和 1 之間。
這個函數就是——**Sigmoid 函數**。

---

## 💡 重點觀念：Sigmoid 函數

```
Sigmoid(z) = 1 / (1 + e^(-z))

 輸出
 1.0 |                          ─────────
     |                        /
     |                      /
 0.5 |─ ─ ─ ─ ─ ─ ─ ─ ─ /─ ─ ─ ─ ─ ─ ─  ← 決策邊界
     |                 /
     |               /
 0.0 |──────────────
     +──────────────────────────────────> z
    -6  -4  -2   0   2   4   6

 特性：
 - 輸出永遠在 0 到 1 之間（可以解讀為機率！）
 - z 很大 → 輸出接近 1
 - z 很小 → 輸出接近 0
 - z = 0 → 輸出剛好 0.5
```

邏輯斯回歸的公式：

```
步驟 1：跟線性回歸一樣，算出 z = w₁x₁ + w₂x₂ + ... + b
步驟 2：把 z 丟進 Sigmoid，得到機率 p = Sigmoid(z)
步驟 3：如果 p >= 0.5，預測為 1（正類）；否則預測為 0（負類）
```

---

## 動手做：癌症偵測案例

這是一個真實且重要的案例。我們要建立一個模型，
判斷腫瘤是**良性（benign）**還是**惡性（malignant）**。

### 第一步：載入資料

```python
import numpy as np
import pandas as pd
from sklearn.datasets import load_breast_cancer
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    confusion_matrix, accuracy_score, precision_score,
    recall_score, f1_score, classification_report
)

# 載入乳癌資料集
data = load_breast_cancer()
X = pd.DataFrame(data.data, columns=data.feature_names)
y = pd.Series(data.target, name='target')

print(f"資料筆數：{len(X)}")
print(f"特徵數量：{X.shape[1]}")
print(f"\n目標變數分佈：")
print(f"  惡性（0）：{(y == 0).sum()} 筆")
print(f"  良性（1）：{(y == 1).sum()} 筆")
print(f"  良性比例：{(y == 1).mean():.2%}")
```

### 第二步：訓練模型

```python
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# stratify=y 確保訓練集和測試集的類別比例相同

model = LogisticRegression(max_iter=10000, random_state=42)
model.fit(X_train, y_train)

y_pred = model.predict(X_test)
y_prob = model.predict_proba(X_test)[:, 1]  # 取得機率

print(f"訓練完成！")
print(f"訓練集準確度：{model.score(X_train, y_train):.4f}")
print(f"測試集準確度：{model.score(X_test, y_test):.4f}")
```

---

## 💡 重點觀念：混淆矩陣

混淆矩陣是分類問題中最重要的診斷工具。
它告訴你模型到底「搞混」了什麼。

```python
cm = confusion_matrix(y_test, y_pred)
print("混淆矩陣：")
print(cm)
```

### ASCII 版混淆矩陣

```
                        預測結果
                  ┌──────────┬──────────┐
                  │  預測負類 │ 預測正類  │
   ┌──────────────┼──────────┼──────────┤
 實 │  實際負類    │   TN     │   FP     │
 際 │ （惡性）     │ 真陰性   │ 偽陽性   │
 標 ├──────────────┼──────────┼──────────┤
 籤 │  實際正類    │   FN     │   TP     │
   │ （良性）     │ 偽陰性   │ 真陽性   │
   └──────────────┴──────────┴──────────┘
```

用白話說：

```
 ┌──────────────────────────────────────────────────────┐
 │ TN（真陰性）：模型說「惡性」，實際也是惡性 → ✅ 答對 │
 │ TP（真陽性）：模型說「良性」，實際也是良性 → ✅ 答對 │
 │ FP（偽陽性）：模型說「良性」，實際是惡性  → ❌ 放走壞人│
 │ FN（偽陰性）：模型說「惡性」，實際是良性  → ❌ 冤枉好人│
 └──────────────────────────────────────────────────────┘
```

### 具體數字範例

```
假設混淆矩陣是：

                     預測
                  良性    惡性
        良性 │    85   │   5    │    ← 90 個良性腫瘤
 實際        ├─────────┼────────┤
        惡性 │     3   │  21    │    ← 24 個惡性腫瘤
             └─────────┴────────┘

 TN=21  正確識別的惡性：21 個
 TP=85  正確識別的良性：85 個
 FP=3   把惡性誤判為良性：3 個（嚴重！會延誤治療）
 FN=5   把良性誤判為惡性：5 個（會做不必要的手術）
```

---

## 💡 重點觀念：四大評估指標

### Accuracy（準確度）

```
Accuracy = (TP + TN) / 總數 = (85 + 21) / 114 = 93.0%
```

最直覺的指標：「你答對了多少題？」

### Precision（精確度）

```
Precision = TP / (TP + FP) = 85 / (85 + 3) = 96.6%
```

「你說是良性的，有多少真的是良性？」

### Recall（召回率）/ Sensitivity（敏感度）

```
Recall = TP / (TP + FN) = 85 / (85 + 5) = 94.4%
```

「真正的良性腫瘤中，你找到了多少？」

### F1 Score

```
F1 = 2 × (Precision × Recall) / (Precision + Recall)
   = 2 × (0.966 × 0.944) / (0.966 + 0.944) = 95.5%
```

Precision 和 Recall 的調和平均數（比算術平均更嚴格）。

### 一張圖看懂四大指標

```
 所有資料（114 筆）
 ┌────────────────────────────────────────────┐
 │                                            │
 │  模型預測為「良性」              模型預測為 │
 │  ┌─────────────────────┐       「惡性」    │
 │  │  TP=85（答對）      │       ┌─────────┐│
 │  │  FP=3 （答錯）      │       │ TN=21   ││
 │  │                     │       │ FN=5    ││
 │  │  Precision 看這裡   │       │         ││
 │  │  = 85/(85+3)        │       └─────────┘│
 │  └─────────────────────┘                   │
 │                                            │
 │  實際良性: 90 筆 ─── Recall = 85/(85+5)   │
 │  實際惡性: 24 筆                            │
 │                                            │
 │  Accuracy = (85+21)/114                    │
 └────────────────────────────────────────────┘
```

---

## ⚠️ 常見陷阱：Accuracy 在不平衡資料會騙人！

這是本章最重要的觀念，沒有之一。

### 場景：信用卡詐欺偵測

```
資料分佈：
 - 正常交易：9,900 筆（99%）
 - 詐欺交易：  100 筆（1%）
 總共：10,000 筆
```

現在，假設你的模型非常「聰明」：

```python
# 一個「完美」的爛模型
def stupid_model(X):
    return np.zeros(len(X))  # 永遠預測「正常」
```

這個模型的 Accuracy 是多少？

```
Accuracy = 9900 / 10000 = 99.0%
```

**99% 準確度！看起來超棒！**

但這個模型有用嗎？它連一個詐欺交易都抓不到！

```
混淆矩陣：

                    預測
               正常      詐欺
    正常 │   9,900   │    0    │
實際      ├──────────┼─────────┤
    詐欺 │    100    │    0    │
         └──────────┴─────────┘

Accuracy  = 99.0%     ← 看起來很好
Precision = 0/0       ← 未定義（從沒預測過詐欺）
Recall    = 0/100     ← 0%（一個詐欺都沒抓到）
F1        = 0%        ← 直接揭穿假象
```

### 教訓

```
 ┌──────────────────────────────────────────────────────┐
 │              不平衡資料的指標選擇法則                 │
 │                                                      │
 │  1. 永遠不要只看 Accuracy                            │
 │  2. 用 Precision/Recall/F1 搭配混淆矩陣              │
 │  3. 想清楚：FP 和 FN 哪個比較嚴重？                  │
 │  4. 根據業務需求選擇主要指標                         │
 │                                                      │
 │  ┌───────────────────┬────────────────────────────┐  │
 │  │ 場景              │ 該重視的指標               │  │
 │  ├───────────────────┼────────────────────────────┤  │
 │  │ 癌症偵測          │ Recall（別漏掉任何病人）   │  │
 │  │ 垃圾郵件過濾      │ Precision（別誤擋正常信）  │  │
 │  │ 信用卡詐欺        │ Recall（別放過任何詐欺）   │  │
 │  │ 產品推薦          │ Precision（別推爛東西）     │  │
 │  │ 綜合考量          │ F1（兩者都要顧）           │  │
 │  └───────────────────┴────────────────────────────┘  │
 └──────────────────────────────────────────────────────┘
```

---

## 🧠 動動腦：你來選指標

回到癌症偵測的案例。你是醫院的 AI 顧問，必須選擇一個主要指標。

**場景**：模型判斷腫瘤是良性還是惡性

- **FP（偽陽性）**：把惡性判為良性 → 病人沒接受治療 → 可能致命！
- **FN（偽陰性）**：把良性判為惡性 → 病人做了不必要的手術 → 花錢又受苦

在這個場景下，哪個錯誤更嚴重？

```
答案：FP 更嚴重！漏掉惡性腫瘤可能致命。

所以我們應該重視 Recall（針對惡性類別的召回率）：
「所有真正的惡性腫瘤中，我們抓到了多少？」

寧可誤判一些良性為惡性（多做幾次檢查），
也不要漏掉任何一個惡性腫瘤。
```

---

## 分類閾值：可以調的旋鈕

預設情況下，邏輯斯回歸用 0.5 作為閾值：

```
機率 >= 0.5 → 預測為正類（1）
機率 <  0.5 → 預測為負類（0）
```

但 0.5 不一定是最好的選擇！

```python
# 取得機率預測
y_prob = model.predict_proba(X_test)[:, 1]

# 用不同閾值看結果
print(f"{'閾值':>6} | {'Accuracy':>8} | {'Precision':>9} | {'Recall':>6} | {'F1':>6}")
print("-" * 52)

for threshold in [0.3, 0.4, 0.5, 0.6, 0.7, 0.8]:
    y_pred_t = (y_prob >= threshold).astype(int)
    acc = accuracy_score(y_test, y_pred_t)
    prec = precision_score(y_test, y_pred_t, zero_division=0)
    rec = recall_score(y_test, y_pred_t)
    f1 = f1_score(y_test, y_pred_t)
    print(f"{threshold:6.1f} | {acc:8.4f} | {prec:9.4f} | {rec:6.4f} | {f1:6.4f}")
```

```
閾值對 Precision 和 Recall 的影響：

 Precision
 1.0 |*
     |  *
     |    *
     |      *
     |         *
     |             *
 0.0 +───────────────────> 閾值
     0.0             1.0

 Recall
 1.0 |              *
     |           *
     |        *
     |     *
     |  *
     |*
 0.0 +───────────────────> 閾值
     0.0             1.0

 閾值調高 → Precision 升高，Recall 降低（更嚴格，但漏掉更多）
 閾值調低 → Precision 降低，Recall 升高（更寬鬆，但誤報更多）
```

---

## 💡 重點觀念：ROC 曲線

ROC（Receiver Operating Characteristic）曲線是評估分類模型的黃金標準。

```python
from sklearn.metrics import roc_curve, roc_auc_score

fpr, tpr, thresholds = roc_curve(y_test, y_prob)
auc = roc_auc_score(y_test, y_prob)

print(f"AUC = {auc:.4f}")
```

### ROC 曲線的直覺

```
 TPR（True Positive Rate = Recall）
 1.0 |     .........──────────────
     |   ..
     |  .    ← 你的模型的 ROC 曲線
     | .       （越靠近左上角越好）
     |.
 0.5 |. . . . . . . . . . . . .   ← 隨機亂猜（對角線）
     |
     |
     |
 0.0 +──────────────────────────>
     0.0       0.5              1.0
              FPR（False Positive Rate）
```

### AUC（曲線下面積）的意義

```
 ┌─────────┬─────────────────────────────┐
 │  AUC    │  意義                        │
 ├─────────┼─────────────────────────────┤
 │  1.0    │  完美分類器                  │
 │  0.9+   │  優秀                        │
 │  0.8+   │  好                          │
 │  0.7+   │  普通                        │
 │  0.5    │  跟丟銅板一樣（沒用）        │
 │  <0.5   │  比亂猜還差（模型搞反了）    │
 └─────────┴─────────────────────────────┘
```

白話解釋 AUC：

> 隨機抽一個正類和一個負類，模型給正類的分數高於負類的機率。
> AUC = 0.9 表示「90% 的情況下，模型對正類的分數比負類高」。

---

## 決策邊界：模型怎麼劃分世界

邏輯斯回歸找到一條「線」（在高維度中是一個超平面），
把資料分成兩邊：

```
用兩個特徵的例子：

 特徵2
  ^
  |  o o o o  . . . .
  |  o o o . . . . .
  |  o o . / . . . .     / = 決策邊界
  |  o . / . . . . .
  |  . / . . . . . .     o = 類別 0
  | / . . . . . . .      . = 類別 1
  +──────────────────> 特徵1

  決策邊界的位置由模型的權重（w）和偏差（b）決定
  在邊界上，模型輸出的機率剛好是 0.5
```

### 線性 vs 非線性決策邊界

```
邏輯斯回歸（線性）：           非線性模型（如 SVM + RBF）：

 |  o o o | . . .              |  o o   . . .
 |  o o | . . . .              |  o   .   . .
 |  o | . . . . .              |  o .  o  . .
 |  | . . . . .                |   . o o .   .
 | | . . . . .                 |  . . . . . .
 +──────────────>              +──────────────>

 只能畫直線                     可以畫曲線

邏輯斯回歸的限制：
如果兩類資料不是「一刀切」能分開的，
線性決策邊界就會力不從心。
```

---

## 完整案例：用 classification_report 一次看完

```python
# 完整的評估報告
print("=" * 60)
print("完整分類報告")
print("=" * 60)
print(classification_report(y_test, y_pred,
      target_names=['惡性', '良性']))
```

輸出格式：

```
              precision    recall  f1-score   support

        惡性       0.93      0.88      0.90        43
        良性       0.93      0.96      0.94        71

    accuracy                           0.93       114
   macro avg       0.93      0.92      0.92       114
weighted avg       0.93      0.93      0.93       114
```

### 怎麼讀這張報告？

```
 ┌──────────────────────────────────────────────────┐
 │ precision：這行預測結果中，有多少是對的           │
 │ recall   ：這類的真實資料中，模型找到多少         │
 │ f1-score ：precision 和 recall 的調和平均         │
 │ support  ：這一類有多少筆測試資料                 │
 │                                                  │
 │ macro avg   ：兩類的簡單平均（不考慮數量差異）    │
 │ weighted avg：按照 support 加權的平均             │
 │                                                  │
 │ 在不平衡資料中，weighted avg 比 macro avg 更可靠  │
 └──────────────────────────────────────────────────┘
```

---

## 🧠 動動腦：真實世界的取捨

### 情境 A：醫療檢測

```
模型 A：Precision=0.95, Recall=0.70
  → 說是惡性的幾乎都對，但漏掉 30% 的惡性腫瘤

模型 B：Precision=0.70, Recall=0.95
  → 會誤判一些良性為惡性，但只漏掉 5% 的惡性腫瘤

你會選哪個？
```

在醫療場景下，大多數專家會選擇 **模型 B**。
因為漏掉惡性腫瘤（FN）的後果比誤判良性為惡性（FP）嚴重得多。

### 情境 B：垃圾郵件過濾

```
模型 C：Precision=0.95, Recall=0.70
  → 標記為垃圾郵件的幾乎都對，但 30% 的垃圾郵件會溜進收件匣

模型 D：Precision=0.70, Recall=0.95
  → 能抓到 95% 的垃圾郵件，但 30% 正常信件會被誤判為垃圾郵件

你會選哪個？
```

在郵件場景下，很多人會選 **模型 C**。
因為把重要郵件誤標為垃圾（FP）可能讓你錯過重要訊息，
比多收幾封垃圾郵件嚴重得多。

---

## 用 Python 完整實作

```python
import numpy as np
import pandas as pd
from sklearn.datasets import load_breast_cancer
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    confusion_matrix, classification_report,
    roc_auc_score, roc_curve
)
import matplotlib.pyplot as plt

# ============================================================
# 癌症偵測完整流程
# ============================================================

# 1. 載入資料
data = load_breast_cancer()
X = pd.DataFrame(data.data, columns=data.feature_names)
y = pd.Series(data.target)

# 2. 資料探索
print("=" * 50)
print("資料概覽")
print("=" * 50)
print(f"樣本數：{len(X)}")
print(f"特徵數：{X.shape[1]}")
print(f"類別分佈：")
print(f"  惡性（0）：{(y==0).sum()}")
print(f"  良性（1）：{(y==1).sum()}")
print(f"  不平衡比例：1:{(y==1).sum()/(y==0).sum():.1f}")

# 3. 切分資料（使用 stratify 保持比例）
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# 4. 特徵標準化（邏輯斯回歸對尺度敏感）
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# 5. 訓練模型
model = LogisticRegression(max_iter=10000, random_state=42)
model.fit(X_train_scaled, y_train)

# 6. 預測
y_pred = model.predict(X_test_scaled)
y_prob = model.predict_proba(X_test_scaled)[:, 1]

# 7. 混淆矩陣
print("\n" + "=" * 50)
print("混淆矩陣")
print("=" * 50)
cm = confusion_matrix(y_test, y_pred)
print(f"""
                 預測良性    預測惡性
  實際良性 │    {cm[1][1]:4d}    │   {cm[1][0]:4d}    │
  實際惡性 │    {cm[0][1]:4d}    │   {cm[0][0]:4d}    │

  TP={cm[1][1]}, TN={cm[0][0]}, FP={cm[0][1]}, FN={cm[1][0]}
""")

# 8. 分類報告
print("=" * 50)
print("分類報告")
print("=" * 50)
print(classification_report(y_test, y_pred,
      target_names=['惡性', '良性']))

# 9. AUC
auc = roc_auc_score(y_test, y_prob)
print(f"AUC: {auc:.4f}")

# 10. 閾值分析
print("\n" + "=" * 50)
print("閾值分析")
print("=" * 50)
print(f"{'閾值':>6} | {'Precision':>9} | {'Recall':>6} | {'F1':>6} | {'FP':>3} | {'FN':>3}")
print("-" * 55)
for t in [0.3, 0.4, 0.5, 0.6, 0.7]:
    y_t = (y_prob >= t).astype(int)
    cm_t = confusion_matrix(y_test, y_t)
    prec = precision_score(y_test, y_t, zero_division=0)
    rec = recall_score(y_test, y_t)
    f1 = f1_score(y_test, y_t)
    fp = cm_t[0][1]
    fn = cm_t[1][0]
    print(f"{t:6.1f} | {prec:9.4f} | {rec:6.4f} | {f1:6.4f} | {fp:3d} | {fn:3d}")
```

---

## ❓ 沒有笨問題

**Q：邏輯斯回歸的名字裡有「回歸」，但它是做分類的？**

A：對！名字很容易誤導人。歷史上它確實是從回歸發展而來的。
它「回歸」的是機率值（0到1之間的連續值），
然後用閾值把機率轉成分類結果。

**Q：什麼時候該用 Precision，什麼時候用 Recall？**

A：問自己：「哪種錯誤比較嚴重？」
- **FP 比較嚴重**（誤報代價高）→ 重視 Precision
- **FN 比較嚴重**（漏報代價高）→ 重視 Recall
- **兩種都嚴重** → 用 F1

**Q：LogisticRegression 的 max_iter 是什麼？**

A：邏輯斯回歸用疊代（iterative）的方法找最佳參數。
`max_iter` 是最大疊代次數。如果資料複雜或沒有標準化，
可能需要更多疊代才能收斂。收到 `ConvergenceWarning` 時，
就把 `max_iter` 調大或對特徵做標準化。

**Q：為什麼邏輯斯回歸需要特徵標準化？**

A：邏輯斯回歸用梯度下降來最佳化，
如果特徵的尺度差異很大（例如一個是 0-1，另一個是 0-1000000），
梯度下降會走得很歪，收斂很慢。標準化讓所有特徵站在同一起跑線。

**Q：多分類怎麼辦？**

A：`LogisticRegression` 預設支援多分類！
它會自動使用 One-vs-Rest（OvR）或 Multinomial 策略。

```python
# 多分類範例
from sklearn.datasets import load_iris
iris = load_iris()
model_multi = LogisticRegression(max_iter=200)
model_multi.fit(iris.data, iris.target)
print(model_multi.predict_proba(iris.data[:3]))
# 輸出每個類別的機率
```

**Q：predict_proba 和 predict 有什麼不同？**

A：
- `predict(X)`：直接給你分類結果（0 或 1）
- `predict_proba(X)`：給你每個類別的機率

```python
print(model.predict(X_test[:3]))
# [1, 0, 1]

print(model.predict_proba(X_test[:3]))
# [[0.02, 0.98],   ← 98% 機率是良性 → 預測 1
#  [0.85, 0.15],   ← 85% 機率是惡性 → 預測 0
#  [0.10, 0.90]]   ← 90% 機率是良性 → 預測 1
```

---

## ⚠️ 常見陷阱

### 陷阱 1：只看 Accuracy

```python
# ❌ 這樣不夠
print(f"Accuracy: {accuracy_score(y_test, y_pred):.4f}")

# ✅ 應該看完整報告
print(classification_report(y_test, y_pred))
```

### 陷阱 2：忘記標準化

```python
# ❌ 沒有標準化
model.fit(X_train, y_train)  # 可能收斂很慢或結果差

# ✅ 先標準化
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)  # 注意：用 transform 不是 fit_transform！
model.fit(X_train_scaled, y_train)
```

### 陷阱 3：在測試集上 fit_transform

```python
# ❌ 資料洩漏！
X_test_scaled = scaler.fit_transform(X_test)  # 用了測試集的統計量

# ✅ 正確做法
X_test_scaled = scaler.transform(X_test)  # 只用訓練集的統計量
```

### 陷阱 4：忽略類別不平衡

```python
# 如果資料嚴重不平衡
model = LogisticRegression(
    class_weight='balanced',  # 自動調整類別權重
    max_iter=10000
)
```

---

## 本章回顧

```
分類模型知識地圖：

 ┌──────────────────────────────────────────────────────────┐
 │                    邏輯斯回歸                              │
 │                                                          │
 │  ┌─────────────┐  ┌─────────────┐  ┌────────────────┐  │
 │  │  模型基礎    │  │  評估指標    │  │  進階技巧      │  │
 │  │             │  │             │  │                │  │
 │  │  Sigmoid    │  │  Accuracy   │  │  閾值調整      │  │
 │  │  決策邊界   │  │  Precision  │  │  ROC/AUC       │  │
 │  │  機率輸出   │  │  Recall     │  │  class_weight  │  │
 │  │  標準化     │  │  F1 Score   │  │  多分類        │  │
 │  │             │  │  混淆矩陣   │  │                │  │
 │  └─────────────┘  └─────────────┘  └────────────────┘  │
 │                                                          │
 │  ┌───────────────────────────────────────────────────┐  │
 │  │               核心教訓                             │  │
 │  │                                                   │  │
 │  │  1. Accuracy 在不平衡資料會騙人                    │  │
 │  │  2. 選指標要看業務需求（FP vs FN 哪個更嚴重）     │  │
 │  │  3. 一定要看混淆矩陣，不要只看單一數字             │  │
 │  │  4. 閾值 0.5 不一定是最好的                        │  │
 │  └───────────────────────────────────────────────────┘  │
 └──────────────────────────────────────────────────────────┘
```

---

## 📝 課後練習

### 練習 1：完整建模

用 scikit-learn 的乳癌資料集：
1. 訓練 LogisticRegression（記得標準化）
2. 印出混淆矩陣和 classification_report
3. 試用不同閾值（0.3, 0.5, 0.7），觀察 Precision 和 Recall 的變化

### 練習 2：不平衡資料實驗

```python
# 人工製造不平衡資料
from sklearn.datasets import make_classification

X_imb, y_imb = make_classification(
    n_samples=10000,
    n_features=20,
    n_classes=2,
    weights=[0.95, 0.05],  # 95% vs 5%
    random_state=42
)
```

1. 用上述資料訓練模型，觀察 Accuracy vs F1
2. 使用 `class_weight='balanced'` 重新訓練，比較結果
3. 畫 ROC 曲線，計算 AUC

### 練習 3：思考題

你是一家銀行的 AI 工程師，要建立信用卡詐欺偵測系統。
- 資料中 99.5% 是正常交易，0.5% 是詐欺
- FP（把正常交易誤判為詐欺）：會暫時凍結卡片，客戶需要打電話解凍
- FN（把詐欺交易誤判為正常）：客戶損失金錢

你會如何設計評估策略？用哪些指標？閾值怎麼設？

---

## 下一章預告

我們已經學會了線性回歸和邏輯斯回歸，它們有個共同點：
用一條「線」或一個「平面」來做預測。

但如果資料的邊界不是一條線呢？

下一章，我們會學一個完全不同思路的算法——
**K 最近鄰（KNN）**，它的哲學是：

> 「告訴我你的鄰居是誰，我就知道你是誰。」

同時，我們會認識機器學習中最重要的概念：
**Bias-Variance Tradeoff（偏差-方差權衡）**。

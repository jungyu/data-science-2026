# 第 13 章：商業成本函數 — 當模型走進董事會

> 「準確率 99%？太好了！……等等，我們剛剛放過了一筆 300 萬的詐欺交易。」

---

## 🎯 本章目標

讀完這一章，你將能夠：

1. 解釋為什麼「準確率」不等於「商業價值」
2. 建立並運用 **誤判成本矩陣（Cost Matrix）**
3. 區分 False Positive 與 False Negative 的 **商業代價差異**
4. 調整分類門檻（threshold）以最大化商業收益
5. 在 scikit-learn 中使用 `sample_weight` 進行成本敏感學習
6. 計算 ML 模型的 **投資報酬率（ROI）**
7. 用模型輸出做出有依據的商業決策

---

## 為什麼準確率是個騙人的指標？

想像你是一家信用卡公司的風控主管。每天有 100,000 筆交易，其中只有 100 筆是詐欺。

如果你建了一個模型，它的策略是：**把所有交易都判定為正常**。

```
準確率 = 99,900 / 100,000 = 99.9%
```

哇，99.9%！可以下班了嗎？

**當然不行。** 你放過了全部 100 筆詐欺交易。假設每筆平均損失 50,000 元，
你剛剛讓公司損失了 **500 萬元**。

```
+--------------------------------------------------+
|          準確率的陷阱：不平衡資料集                  |
+--------------------------------------------------+
|                                                    |
|  100,000 筆交易                                    |
|  ├── 99,900 筆正常  ← 全部猜對 ✅                  |
|  └── 100 筆詐欺    ← 全部漏掉 ❌                   |
|                                                    |
|  準確率 = 99.9%    商業損失 = $5,000,000           |
|                                                    |
|  「數字很漂亮，但老闆不開心。」                      |
+--------------------------------------------------+
```

💡 **重點觀念**：在不平衡資料集中，準確率幾乎毫無意義。你需要的是一個能反映
**商業成本** 的評估方式。

---

## 誤判成本矩陣（Cost Matrix）

### 先複習混淆矩陣

```
                    預測結果
                 正常      詐欺
實        正常 │  TN   │  FP   │
際        詐欺 │  FN   │  TP   │
```

- **TN（True Negative）**：正常交易，判為正常 → 皆大歡喜
- **TP（True Positive）**：詐欺交易，判為詐欺 → 成功攔截！
- **FP（False Positive）**：正常交易，判為詐欺 → 客戶被誤擋，打電話來罵人
- **FN（False Negative）**：詐欺交易，判為正常 → 錢被偷走了

### 每種結果的商業成本

現在，讓我們為每個格子 **標上價錢**：

```
                      預測結果
                   正常          詐欺
實    正常 │   $0（沒事）   │  $50（客服成本）  │
際    詐欺 │ $50,000（被盜） │  $5（簡訊通知）   │
```

看出來了嗎？

- **FP 的成本**：$50（打電話確認、客戶不滿）
- **FN 的成本**：$50,000（交易損失、理賠、商譽）

**FN 的代價是 FP 的 1,000 倍！**

💡 **重點觀念**：不同類型的錯誤，在商業上的代價天差地別。模型的目標不是
「少犯錯」，而是「犯便宜的錯」。

---

## 🧠 動動腦

> 在以下場景中，FP 和 FN 哪個更嚴重？
>
> 1. 醫療篩檢：檢測癌症
> 2. 垃圾郵件過濾器
> 3. 工廠品管：檢測瑕疵品
>
> 提示：想想「漏掉」vs「誤判」各自的後果。

---

## 用 Python 建立成本矩陣

```python
import numpy as np

# 定義成本矩陣
# cost_matrix[實際][預測]
cost_matrix = {
    (0, 0): 0,        # TN: 正常判正常，沒有成本
    (0, 1): 50,       # FP: 正常判詐欺，客服成本
    (1, 0): 50_000,   # FN: 詐欺判正常，交易損失
    (1, 1): 5,        # TP: 詐欺判詐欺，簡訊通知成本
}

def calculate_total_cost(y_true, y_pred, cost_matrix):
    """計算模型預測的總商業成本"""
    total_cost = 0
    for actual, predicted in zip(y_true, y_pred):
        total_cost += cost_matrix[(actual, predicted)]
    return total_cost

# 範例：100 筆交易的預測結果
y_true = np.array([0]*90 + [1]*10)  # 90 筆正常，10 筆詐欺
y_pred = np.array([0]*90 + [0]*3 + [1]*7)  # 漏掉 3 筆詐欺

total = calculate_total_cost(y_true, y_pred, cost_matrix)
print(f"總商業成本: ${total:,}")
# 總商業成本: $150,035
# = 3 筆 FN × $50,000 + 7 筆 TP × $5
```

---

## 分類門檻（Threshold）的魔法

大多數分類器不是直接輸出 0 或 1，而是輸出一個 **機率值**。
預設門檻是 0.5：機率 > 0.5 就判為正類。

但誰說門檻一定是 0.5？

```
機率輸出：0.0 -------- 0.3 -------- 0.5 -------- 0.7 -------- 1.0
                                      ↑
                               預設門檻 = 0.5

如果我們把門檻降低到 0.3：
機率輸出：0.0 -------- 0.3 -------- 0.5 -------- 0.7 -------- 1.0
                        ↑
                 新門檻 = 0.3
                 → 更多交易被標記為詐欺
                 → FP 增加，但 FN 減少
```

### 門檻與成本的權衡

```
+------------------+----------------+----------------+
| 門檻             | FP（誤擋正常） | FN（放過詐欺） |
+------------------+----------------+----------------+
| 0.1（超敏感）    | 很多 ↑↑↑       | 很少 ↓↓↓       |
| 0.3（偏敏感）    | 偏多 ↑↑        | 偏少 ↓↓        |
| 0.5（預設）      | 中等           | 中等           |
| 0.7（偏保守）    | 偏少 ↓↓        | 偏多 ↑↑        |
| 0.9（超保守）    | 很少 ↓↓↓       | 很多 ↑↑↑       |
+------------------+----------------+----------------+
```

💡 **重點觀念**：當 FN 成本遠高於 FP 時，應該 **降低門檻**，寧可多擋幾筆
正常交易，也不要放過詐欺。

---

## 🔬 案例研究：信用卡詐欺偵測

讓我們用完整的程式碼來看門檻調整如何影響商業損失。

```python
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.datasets import make_classification
import numpy as np

# 模擬不平衡資料集：1% 詐欺率
X, y = make_classification(
    n_samples=10000,
    n_features=20,
    weights=[0.99, 0.01],  # 99% 正常，1% 詐欺
    random_state=42
)

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.3, random_state=42
)

# 訓練模型
clf = RandomForestClassifier(n_estimators=100, random_state=42)
clf.fit(X_train, y_train)

# 取得機率預測
y_proba = clf.predict_proba(X_test)[:, 1]  # 詐欺的機率

# 測試不同門檻
cost_matrix = {(0,0): 0, (0,1): 50, (1,0): 50000, (1,1): 5}
thresholds = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]

print(f"{'門檻':>6} | {'FP':>5} | {'FN':>5} | {'總成本':>12} | {'攔截率':>8}")
print("-" * 55)

for t in thresholds:
    y_pred = (y_proba >= t).astype(int)

    fp = ((y_pred == 1) & (y_test == 0)).sum()
    fn = ((y_pred == 0) & (y_test == 1)).sum()
    tp = ((y_pred == 1) & (y_test == 1)).sum()

    total_cost = calculate_total_cost(y_test, y_pred, cost_matrix)
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0

    print(f"{t:>6.1f} | {fp:>5} | {fn:>5} | ${total_cost:>10,} | {recall:>7.1%}")
```

預期輸出類似：

```
  門檻 |    FP |    FN |       總成本 |   攔截率
-------------------------------------------------------
   0.1 |   120 |     1 |     $56,005 |   96.7%
   0.2 |    60 |     2 |    $103,010 |   93.3%
   0.3 |    30 |     3 |    $151,515 |   90.0%
   0.5 |    10 |     8 |    $400,560 |   73.3%
   0.7 |     3 |    15 |    $750,225 |   50.0%
   0.9 |     0 |    25 |  $1,250,000 |   16.7%
```

**結論**：門檻 0.1 的總成本最低！雖然 FP 多了（120 筆要人工審核），
但避免了大量 FN 帶來的鉅額損失。

---

## ❓ 沒有笨問題

**Q：所以門檻越低越好嗎？**

A：不一定。門檻太低會產生大量 FP，如果 FP 的處理成本也很高（例如需要人工
逐一審核），總成本可能反而上升。最佳門檻取決於你的 **成本結構**。

**Q：怎麼找到最佳門檻？**

A：就像我們上面做的 — 遍歷所有可能的門檻值，計算每個門檻下的總商業成本，
選成本最低的那個。這叫做 **成本敏感的門檻優化（cost-sensitive threshold tuning）**。

**Q：這和 ROC 曲線有什麼關係？**

A：ROC 曲線展示了所有可能門檻下的 TPR vs FPR 權衡。但 ROC 不考慮成本。
加上成本矩陣後，你可以在 ROC 曲線上標出 **商業最佳點**。

**Q：每次部署模型都要重新調門檻嗎？**

A：是的！因為成本結構可能隨時間變化。例如信用卡詐欺的平均金額可能季節性
波動，客服成本也可能調整。

---

## sample_weight：讓模型「看重」重要樣本

scikit-learn 提供了一個強大的參數：`sample_weight`。

它的概念很直覺：**告訴模型某些樣本比其他樣本更重要。**

```
想像你是老師在改考卷：
- 普通題（正常交易）：答錯扣 1 分
- 關鍵題（詐欺交易）：答錯扣 100 分

模型會更努力把「關鍵題」答對！
```

### 實作 sample_weight

```python
from sklearn.ensemble import GradientBoostingClassifier
import numpy as np

# 根據成本矩陣設定樣本權重
# 詐欺樣本的權重 = FN 成本 / FP 成本 = 50000 / 50 = 1000
sample_weights = np.where(y_train == 1, 1000, 1)

print(f"正常交易權重: 1")
print(f"詐欺交易權重: 1000")
print(f"權重比例: 1:1000")

# 用 sample_weight 訓練模型
clf_weighted = GradientBoostingClassifier(random_state=42)
clf_weighted.fit(X_train, y_train, sample_weight=sample_weights)

# 比較有無權重的結果
from sklearn.metrics import classification_report

y_pred_default = clf.predict(X_test)
y_pred_weighted = clf_weighted.predict(X_test)

print("\n=== 無權重模型 ===")
print(classification_report(y_test, y_pred_default,
                            target_names=['正常', '詐欺']))

print("=== 有權重模型 ===")
print(classification_report(y_test, y_pred_weighted,
                            target_names=['正常', '詐欺']))
```

### 哪些 sklearn 模型支援 sample_weight？

```
+-----------------------------+------------------+
| 模型                        | sample_weight    |
+-----------------------------+------------------+
| LogisticRegression          | ✅ 支援           |
| DecisionTreeClassifier      | ✅ 支援           |
| RandomForestClassifier      | ✅ 支援           |
| GradientBoostingClassifier  | ✅ 支援           |
| SVC                         | ✅ 支援           |
| KNeighborsClassifier        | ❌ 不支援         |
| GaussianNB                  | ✅ 支援（部分）    |
+-----------------------------+------------------+
```

💡 **重點觀念**：`sample_weight` 是在 **訓練階段** 影響模型，而門檻調整是在
**預測階段** 影響決策。兩者可以 **組合使用**！

---

## class_weight：更簡便的替代方案

如果你不想手動算權重，sklearn 提供了 `class_weight` 參數：

```python
from sklearn.ensemble import RandomForestClassifier

# 方法 1：自動平衡
clf_balanced = RandomForestClassifier(
    class_weight='balanced',  # 自動根據類別比例調整
    random_state=42
)

# 方法 2：自訂權重
clf_custom = RandomForestClassifier(
    class_weight={0: 1, 1: 1000},  # 詐欺類別權重 1000 倍
    random_state=42
)

# 方法 3：balanced + 門檻調整 = 雙重保險
clf_balanced.fit(X_train, y_train)
y_proba_balanced = clf_balanced.predict_proba(X_test)[:, 1]
y_pred_tuned = (y_proba_balanced >= 0.3).astype(int)  # 門檻下調
```

---

## 計算 ML 模型的 ROI

老闆最愛問的問題：**「這個模型值多少錢？」**

### ROI 計算框架

```
+----------------------------------------------------------+
|              ML 模型 ROI 計算                              |
+----------------------------------------------------------+
|                                                            |
|  模型帶來的收益                                             |
|  ├── 詐欺攔截節省: TP × 平均詐欺金額                        |
|  ├── 人力節省: 自動化取代的人工審核量 × 單位成本              |
|  └── 客戶留存: 因快速偵測提升的客戶信任度（間接）             |
|                                                            |
|  模型的成本                                                 |
|  ├── FP 處理成本: FP × 單位審核成本                         |
|  ├── 開發維護: 資料科學團隊 + 基礎設施                       |
|  └── FN 損失: FN × 平均詐欺金額                             |
|                                                            |
|  ROI = (收益 - 成本) / 成本 × 100%                         |
+----------------------------------------------------------+
```

### 實作 ROI 計算

```python
def calculate_model_roi(y_true, y_pred, params):
    """
    計算 ML 模型的商業 ROI

    params: dict 包含
        - avg_fraud_amount: 平均詐欺金額
        - fp_review_cost: FP 人工審核成本
        - model_dev_cost: 模型開發與維護成本（年）
        - manual_review_cost: 無模型時的人工審核成本（年）
    """
    tp = ((y_pred == 1) & (y_true == 1)).sum()
    fp = ((y_pred == 1) & (y_true == 0)).sum()
    fn = ((y_pred == 0) & (y_true == 1)).sum()

    # 收益
    fraud_saved = tp * params['avg_fraud_amount']
    manual_saved = params['manual_review_cost']  # 不再需要全人工審核
    total_benefit = fraud_saved + manual_saved

    # 成本
    fp_cost = fp * params['fp_review_cost']
    fn_loss = fn * params['avg_fraud_amount']
    dev_cost = params['model_dev_cost']
    total_cost = fp_cost + fn_loss + dev_cost

    # ROI
    roi = (total_benefit - total_cost) / total_cost * 100

    print(f"=== ML 模型 ROI 報告 ===")
    print(f"詐欺攔截節省:   ${fraud_saved:>12,.0f}")
    print(f"人力成本節省:   ${manual_saved:>12,.0f}")
    print(f"FP 審核成本:    ${fp_cost:>12,.0f}")
    print(f"FN 損失:        ${fn_loss:>12,.0f}")
    print(f"開發維護成本:   ${dev_cost:>12,.0f}")
    print(f"{'─' * 35}")
    print(f"淨收益:         ${total_benefit - total_cost:>12,.0f}")
    print(f"ROI:            {roi:>11.1f}%")

    return roi

# 範例計算
params = {
    'avg_fraud_amount': 50_000,
    'fp_review_cost': 50,
    'model_dev_cost': 2_000_000,      # 年度開發維護費
    'manual_review_cost': 5_000_000,  # 無模型時的人工審核費
}

roi = calculate_model_roi(y_test, y_pred_weighted, params)
```

---

## 🧠 動動腦

> 你的模型有兩個版本：
> - 版本 A：Recall 95%，Precision 60%
> - 版本 B：Recall 80%，Precision 90%
>
> 在以下場景中，你會選哪一個？為什麼？
> 1. 信用卡詐欺偵測（FN 成本 = $50,000）
> 2. 推薦系統（FP 只是推薦了不相關的商品）
> 3. 自駕車行人偵測

---

## 用模型做商業決策

模型不只是分類器，它是 **決策支援工具**。

### 決策框架

```
           模型輸出機率
               │
               ▼
    ┌──────────────────────┐
    │   機率 >= 0.8        │──→  自動攔截（高信心）
    ├──────────────────────┤
    │   0.3 <= 機率 < 0.8  │──→  人工審核（中等信心）
    ├──────────────────────┤
    │   機率 < 0.3         │──→  自動放行（低風險）
    └──────────────────────┘
```

### 三級決策系統實作

```python
def make_business_decision(probabilities, thresholds=(0.3, 0.8)):
    """
    三級決策系統

    Returns:
        decisions: array of 'auto_block', 'manual_review', 'auto_approve'
    """
    low, high = thresholds
    decisions = np.where(
        probabilities >= high, 'auto_block',
        np.where(probabilities >= low, 'manual_review', 'auto_approve')
    )
    return decisions

# 套用決策系統
decisions = make_business_decision(y_proba)

# 統計各決策類別
from collections import Counter
decision_counts = Counter(decisions)

print("=== 決策分佈 ===")
for decision, count in sorted(decision_counts.items()):
    pct = count / len(decisions) * 100
    print(f"{decision:>15}: {count:>5} 筆 ({pct:.1f}%)")
```

這樣做的好處：
- **高信心預測**：完全自動化，節省人力
- **中等信心預測**：人機協作，兼顧效率與準確
- **低風險預測**：快速放行，不影響客戶體驗

---

## ⚠️ 常見陷阱

### 陷阱 1：只看準確率就下結論

```python
# ❌ 錯誤做法
from sklearn.metrics import accuracy_score
print(f"準確率: {accuracy_score(y_test, y_pred):.2%}")  # 99.5%！
# 然後就覺得模型很棒...

# ✅ 正確做法
from sklearn.metrics import classification_report, confusion_matrix
print(confusion_matrix(y_test, y_pred))
print(classification_report(y_test, y_pred))
# 再加上成本分析！
total_cost = calculate_total_cost(y_test, y_pred, cost_matrix)
print(f"商業成本: ${total_cost:,}")
```

### 陷阱 2：成本矩陣一成不變

```python
# ❌ 2024 年設定的成本，2026 年還在用
cost_matrix_old = {(1,0): 30000}  # 2024 年的平均詐欺金額

# ✅ 定期更新成本矩陣
def get_current_cost_matrix():
    """每季度從業務部門取得最新成本數據"""
    # 從資料庫或設定檔讀取
    return {
        (0, 0): 0,
        (0, 1): get_current_fp_cost(),      # 動態取得
        (1, 0): get_current_fn_cost(),      # 動態取得
        (1, 1): get_current_tp_cost(),      # 動態取得
    }
```

### 陷阱 3：忽略間接成本

FP 的成本不只是客服電話費。被誤擋的客戶可能：
- 取消信用卡 → 損失未來收入
- 在社群媒體抱怨 → 品牌受損
- 轉投競爭對手 → 長期客戶流失

### 陷阱 4：沒有和業務部門溝通

```
┌─────────────────────────────────────────────────────┐
│  資料科學家的世界    │    業務部門的世界              │
│                      │                               │
│  - F1 Score          │  - 每月損失金額               │
│  - AUC-ROC           │  - 客戶投訴量                 │
│  - Log Loss          │  - 人工審核工時               │
│  - Precision@k       │  - 部門預算達成率              │
│                      │                               │
│  「模型 AUC 0.95！」 │  「所以我們少賠多少錢？」      │
└─────────────────────────────────────────────────────┘

你需要說他們的語言！
```

---

## 完整案例：從訓練到商業決策

```python
"""
完整流程：信用卡詐欺偵測的成本敏感學習
"""
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import numpy as np

# Step 1: 準備資料（實際專案中從資料庫讀取）
X, y = make_classification(
    n_samples=50000, n_features=30,
    weights=[0.995, 0.005],  # 0.5% 詐欺率
    random_state=42
)
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.3, random_state=42
)

# Step 2: 定義商業成本
COST_FP = 50        # 誤擋一筆正常交易的成本
COST_FN = 50_000    # 放過一筆詐欺的損失
COST_RATIO = COST_FN / COST_FP  # = 1000

# Step 3: 成本敏感訓練
clf = GradientBoostingClassifier(random_state=42)
sample_weights = np.where(y_train == 1, COST_RATIO, 1)
clf.fit(X_train, y_train, sample_weight=sample_weights)

# Step 4: 找最佳門檻
y_proba = clf.predict_proba(X_test)[:, 1]
best_threshold = 0.5
best_cost = float('inf')

for t in np.arange(0.05, 0.95, 0.05):
    y_pred_t = (y_proba >= t).astype(int)
    cost = calculate_total_cost(y_test, y_pred_t,
                                 {(0,0):0, (0,1):COST_FP,
                                  (1,0):COST_FN, (1,1):5})
    if cost < best_cost:
        best_cost = cost
        best_threshold = t

print(f"最佳門檻: {best_threshold:.2f}")
print(f"最低商業成本: ${best_cost:,}")

# Step 5: 用最佳門檻做預測
y_pred_final = (y_proba >= best_threshold).astype(int)
print(classification_report(y_test, y_pred_final,
                            target_names=['正常', '詐欺']))

# Step 6: 商業決策
decisions = make_business_decision(y_proba,
                                   thresholds=(best_threshold, 0.8))
```

---

## 本章總結

```
+----------------------------------------------------------+
|  從「準確率」到「商業價值」的思維轉變                        |
+----------------------------------------------------------+
|                                                            |
|  1. 準確率在不平衡資料中幾乎無用                            |
|  2. 每種誤判都有不同的商業成本                               |
|  3. 用成本矩陣量化誤判的商業影響                             |
|  4. 調整門檻可以最小化總商業成本                             |
|  5. sample_weight / class_weight 讓模型注重高成本樣本        |
|  6. 計算 ROI 向老闆證明模型的價值                            |
|  7. 用三級決策系統平衡自動化與人工審核                        |
|                                                            |
+----------------------------------------------------------+
```

---

## 📝 課後練習

### 練習 1：醫療篩檢成本分析

一家醫院要建立糖尿病篩檢模型。假設：
- FP（健康者被判為糖尿病）：額外檢查費 $500
- FN（糖尿病患者被判為健康）：延誤治療成本 $100,000

請：
1. 建立成本矩陣
2. 訓練一個分類器（使用 sklearn 的糖尿病資料集）
3. 找出最佳門檻
4. 計算年度 ROI（假設每年篩檢 10,000 人）

### 練習 2：電商退貨預測

電商平台想預測哪些訂單可能被退貨：
- FP（預測退貨但實際沒退）：多餘的品質檢查成本 $5
- FN（沒預測到退貨）：退貨處理 + 物流成本 $30

設計一個成本敏感的分類系統，並實作三級決策。

### 練習 3：A/B 測試模型版本

用同一份資料訓練兩個模型（RandomForest vs GradientBoosting），
分別計算它們在不同門檻下的總商業成本，畫出「門檻 vs 商業成本」曲線，
找出各自的最佳門檻和最低成本。

---

> 📌 **下一章預告**：模型做了決策，但為什麼？第 14 章將帶你進入
> **模型可解釋性** 的世界 — 讓黑盒子打開蓋子。

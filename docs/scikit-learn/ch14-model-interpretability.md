# 第 14 章：模型可解釋性 — 打開黑盒子

> 「醫生，AI 說我有 87% 的機率得糖尿病……但為什麼？」
> 「嗯……模型說的。」
> 「……」

---

## 🎯 本章目標

讀完這一章，你將能夠：

1. 解釋為什麼模型可解釋性比追求最高分數更重要
2. 使用 `feature_importances_` 分析樹模型的特徵重要性
3. 實作 **Permutation Importance**（排列重要性）
4. 繪製 **Partial Dependence Plot**（部分依賴圖）
5. 區分白盒模型與黑盒模型
6. 理解 LIME 和 SHAP 的基本概念
7. 為模型的預測結果提供 **人類可理解的解釋**

---

## 可解釋性 > 炫技

### 一個真實的場景

某醫院導入了 AI 輔助診斷系統。模型用了 200 個特徵，
經過 5 層 stacking，AUC 達到 0.98。

然後醫生問：「為什麼這個病人被判為高風險？」

```
+------------------------------------------+
|  超級 Stacking 模型 v3.7                  |
|  ├── XGBoost（50 棵樹）                   |
|  ├── LightGBM（100 棵樹）                 |
|  ├── CatBoost（75 棵樹）                  |
|  ├── 2 層 Neural Network                  |
|  └── Meta-learner: LogisticRegression     |
|                                            |
|  輸入: 200 個特徵                          |
|  輸出: 「高風險」(p=0.87)                  |
|                                            |
|  醫生: 「為什麼？」                        |
|  模型: 「¯\_(ツ)_/¯」                     |
+------------------------------------------+
```

如果模型無法解釋自己的決策，醫生 **不會信任** 它，
病人也 **不應該信任** 它。

💡 **重點觀念**：在高風險領域（醫療、金融、法律），
一個 AUC 0.90 但可解釋的模型，往往比 AUC 0.98 的黑盒子更有價值。

---

## 白盒 vs 黑盒模型

```
可解釋性光譜
高 ◄─────────────────────────────────────────► 低
│                                                │
│  線性迴歸    決策樹    隨機森林    神經網路     │
│  Logistic   規則系統   XGBoost    深度學習     │
│                                                │
│  白盒模型 ◄──────────────────► 黑盒模型        │
│  (可直接解讀)                  (需要工具輔助)   │
```

### 各模型的可解釋性比較

```
+-------------------------+----------+---------------------------+
| 模型                    | 類型     | 解釋方式                   |
+-------------------------+----------+---------------------------+
| Linear Regression       | 白盒     | 係數直接告訴你答案          |
| Logistic Regression     | 白盒     | 係數 = log odds            |
| Decision Tree           | 白盒     | 整棵樹就是規則             |
| Random Forest           | 灰盒     | feature_importances_       |
| Gradient Boosting       | 灰盒     | feature_importances_       |
| SVM (非線性核)          | 黑盒     | 需要 LIME/SHAP             |
| Neural Network          | 黑盒     | 需要 LIME/SHAP/Grad-CAM   |
+-------------------------+----------+---------------------------+
```

### 白盒模型：線性迴歸的係數

```python
from sklearn.linear_model import LogisticRegression
from sklearn.datasets import load_breast_cancer
import pandas as pd
import numpy as np

# 載入乳癌資料集
data = load_breast_cancer()
X = pd.DataFrame(data.data, columns=data.feature_names)
y = data.target

# 訓練 Logistic Regression
lr = LogisticRegression(max_iter=10000, random_state=42)
lr.fit(X, y)

# 係數就是解釋！
coef_df = pd.DataFrame({
    'feature': data.feature_names,
    'coefficient': lr.coef_[0]
}).sort_values('coefficient', key=abs, ascending=False)

print("=== Logistic Regression 特徵係數（Top 10）===")
print(coef_df.head(10).to_string(index=False))
```

```
解讀方式：
- 係數 > 0：該特徵增加 → 判為良性的機率增加
- 係數 < 0：該特徵增加 → 判為惡性的機率增加
- |係數| 越大，影響力越強
```

💡 **重點觀念**：線性模型天生可解釋。每個係數直接告訴你「這個特徵多重要、
影響方向是什麼」。

---

## 🧠 動動腦

> Logistic Regression 的某個特徵係數是 -2.5，
> 這代表什麼意思？
>
> 提示：想想 log odds 和機率的關係。
> 當這個特徵值增加 1 單位時，log odds 會怎麼變？

---

## feature_importances_：樹模型的特徵重要性

Random Forest 和 Gradient Boosting 等樹模型提供了內建的
`feature_importances_` 屬性。

### 它是怎麼算的？

```
決策樹在每個節點選擇一個特徵來分裂。
分裂後，不純度（impurity）會下降。

feature_importance = 該特徵在所有分裂中造成的不純度下降總和

                    [全部資料]
                    impurity = 0.5
                   /            \
            [特徵A > 3]     [特徵A <= 3]
            imp = 0.3        imp = 0.1

     不純度下降 = 0.5 - (0.3 × n_left + 0.1 × n_right) / n_total

在隨機森林中，對所有樹的結果取平均。
```

### 實作與視覺化

```python
from sklearn.ensemble import RandomForestClassifier
from sklearn.datasets import load_breast_cancer
import pandas as pd
import numpy as np

data = load_breast_cancer()
X = pd.DataFrame(data.data, columns=data.feature_names)
y = data.target

# 訓練 Random Forest
rf = RandomForestClassifier(n_estimators=100, random_state=42)
rf.fit(X, y)

# 取得特徵重要性
importances = pd.DataFrame({
    'feature': data.feature_names,
    'importance': rf.feature_importances_
}).sort_values('importance', ascending=False)

print("=== Random Forest 特徵重要性（Top 10）===")
for i, row in importances.head(10).iterrows():
    bar = '█' * int(row['importance'] * 100)
    print(f"{row['feature']:>25s} | {row['importance']:.4f} | {bar}")
```

輸出類似：

```
=== Random Forest 特徵重要性（Top 10）===
        worst concave points | 0.1456 | ██████████████
              worst perimeter | 0.1389 | █████████████
                worst radius | 0.1201 | ████████████
               mean concavity | 0.0732 | ███████
          worst area          | 0.0658 | ██████
     mean concave points      | 0.0623 | ██████
               mean perimeter | 0.0518 | █████
                  mean radius | 0.0476 | ████
                mean area     | 0.0401 | ████
            worst compactness | 0.0289 | ██
```

---

## ⚠️ 常見陷阱：feature_importances_ 的問題

### 陷阱 1：高基數特徵的偏差

```python
# 如果有一個特徵有很多不同的值（高基數），
# 樹模型會「偏好」用它來分裂，因為有更多分裂點可選。

# 例如：「客戶 ID」可能被認為很重要，但它毫無預測意義！

# ✅ 解決方案：使用 Permutation Importance
```

### 陷阱 2：相關特徵的重要性被分散

```
假設「身高(cm)」和「身高(inch)」都是特徵。
它們完全相關，所以重要性會被「平分」。
單看每個特徵的重要性，都會偏低。

實際上：身高的真正重要性 = 兩者之和

+----------------+------------+----------+
| 特徵           | 顯示重要性 | 真正重要性 |
+----------------+------------+----------+
| 身高(cm)       | 0.10       |          |
| 身高(inch)     | 0.08       | 0.18     |
| 體重(kg)       | 0.15       | 0.15     |
+----------------+------------+----------+
```

### 陷阱 3：訓練集上的重要性可能過擬合

```python
# feature_importances_ 是在訓練集上計算的
# 如果模型過擬合，重要性排名可能不可靠

# ✅ 解決方案：在測試集上用 Permutation Importance
```

---

## Permutation Importance：更可靠的特徵重要性

### 概念

```
Permutation Importance 的邏輯非常直覺：

1. 用測試集計算模型的基準分數
2. 隨機打亂某個特徵的值（其他特徵不變）
3. 重新計算模型分數
4. 分數下降越多 → 該特徵越重要

就像考試時把某一章的筆記全部打亂：
如果成績大幅下降，代表那一章很重要！

┌────────────────────────────────────────────┐
│  原始資料          打亂「年齡」後            │
│  年齡 收入 分數    年齡  收入 分數           │
│  25   50K  0.95    67    50K  ???            │
│  30   60K         25    60K                  │
│  67   80K         42    80K                  │
│  42   45K         30    45K                  │
│                                              │
│  如果打亂年齡後分數從 0.95 降到 0.70         │
│  → Permutation Importance = 0.25             │
└────────────────────────────────────────────┘
```

### 實作

```python
from sklearn.inspection import permutation_importance
from sklearn.model_selection import train_test_split

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.3, random_state=42
)

rf.fit(X_train, y_train)

# 在測試集上計算 Permutation Importance
perm_imp = permutation_importance(
    rf, X_test, y_test,
    n_repeats=30,       # 重複 30 次取平均
    random_state=42,
    scoring='accuracy'   # 也可以用 'f1', 'roc_auc' 等
)

# 整理結果
perm_df = pd.DataFrame({
    'feature': data.feature_names,
    'importance_mean': perm_imp.importances_mean,
    'importance_std': perm_imp.importances_std,
}).sort_values('importance_mean', ascending=False)

print("=== Permutation Importance（Top 10）===")
for _, row in perm_df.head(10).iterrows():
    bar = '█' * int(row['importance_mean'] * 200)
    print(f"{row['feature']:>25s} | "
          f"{row['importance_mean']:.4f} +/- {row['importance_std']:.4f} | "
          f"{bar}")
```

### 比較兩種重要性

```python
comparison = pd.DataFrame({
    'feature': data.feature_names,
    'tree_importance': rf.feature_importances_,
    'perm_importance': perm_imp.importances_mean,
})

# 排名差異分析
comparison['tree_rank'] = comparison['tree_importance'].rank(ascending=False)
comparison['perm_rank'] = comparison['perm_importance'].rank(ascending=False)
comparison['rank_diff'] = abs(comparison['tree_rank'] - comparison['perm_rank'])

print("=== 排名差異最大的特徵 ===")
print(comparison.nlargest(5, 'rank_diff')[
    ['feature', 'tree_rank', 'perm_rank', 'rank_diff']
].to_string(index=False))
```

💡 **重點觀念**：Permutation Importance 比 `feature_importances_` 更可靠，
因為它在 **測試集** 上計算，不受高基數偏差影響，
而且可以用於 **任何模型**（不只是樹模型）。

---

## ❓ 沒有笨問題

**Q：Permutation Importance 很慢怎麼辦？**

A：可以減少 `n_repeats`（例如改為 10），或只對 top-k 特徵做排列。
如果特徵超過 100 個，先用 `feature_importances_` 篩選出前 30 個，
再對它們做 Permutation Importance。

**Q：如果兩個特徵高度相關，Permutation Importance 準嗎？**

A：會有問題。打亂其中一個特徵時，另一個仍然保留了資訊，
所以兩個特徵的重要性都會被低估。解決方案是先做特徵選擇或 PCA，
或者使用分組排列（grouped permutation）。

**Q：我可以用 Permutation Importance 來做特徵選擇嗎？**

A：可以！移除那些 Permutation Importance 接近 0 或為負值的特徵。
負值表示打亂後模型反而更好，代表該特徵可能是雜訊。

**Q：為什麼 importance_std 很重要？**

A：標準差告訴你這個重要性估計有多穩定。如果某特徵的 importance_mean
是 0.05 但 importance_std 是 0.04，那它的重要性其實不太確定。

---

## Partial Dependence Plot（PDP）：看見特徵的影響方向

特徵重要性告訴你「誰重要」，但沒告訴你「怎麼重要」。

PDP 回答的是：**當某個特徵從小變到大時，模型的預測會怎麼變化？**

```
Partial Dependence Plot 的直覺：

假設你想知道「年齡」如何影響「核貸機率」。

1. 把所有樣本的「年齡」都設為 20 → 計算平均預測
2. 把所有樣本的「年齡」都設為 25 → 計算平均預測
3. 把所有樣本的「年齡」都設為 30 → 計算平均預測
   ...以此類推

然後把這些平均預測畫成一條線。

核貸機率
  ^
  |          ___________
  |         /
  |        /
  |   ____/
  |  /
  | /
  +-------------------------> 年齡
  20   30   40   50   60

解讀：年齡從 20 到 40 歲時，核貸機率快速上升；
40 歲之後趨於平穩。
```

### 實作 PDP

```python
from sklearn.inspection import PartialDependenceDisplay
from sklearn.ensemble import GradientBoostingClassifier
import matplotlib.pyplot as plt

# 用乳癌資料集示範
gb = GradientBoostingClassifier(n_estimators=100, random_state=42)
gb.fit(X_train, y_train)

# 找出最重要的特徵
top_features = perm_df.head(4)['feature'].tolist()
feature_indices = [list(data.feature_names).index(f) for f in top_features]

# 繪製 PDP
fig, axes = plt.subplots(2, 2, figsize=(12, 8))
PartialDependenceDisplay.from_estimator(
    gb, X_train, features=feature_indices,
    feature_names=data.feature_names,
    ax=axes.flatten(),
    kind='average'      # 'average' = PDP, 'individual' = ICE
)
plt.tight_layout()
plt.savefig('pdp_example.png', dpi=100, bbox_inches='tight')
plt.show()
```

### 解讀 PDP

```
PDP 解讀指南：

+--------------------+--------------------------------+
| 圖形形狀           | 解讀                           |
+--------------------+--------------------------------+
| 向上的線           | 特徵值越大，預測值越高          |
| 向下的線           | 特徵值越大，預測值越低          |
| 水平線             | 該特徵對預測沒影響             |
| U 型 / 倒 U 型    | 非線性關係                     |
| 階梯狀             | 存在臨界值                     |
+--------------------+--------------------------------+

⚠️ 注意：PDP 假設特徵之間獨立。
如果「身高」和「體重」高度相關，PDP 可能會產生
不合理的情境（例如身高 190cm 但體重 40kg）。
```

---

## 🧠 動動腦

> 你建了一個房價預測模型。PDP 顯示「距離市中心」這個特徵的圖形是：
>
> ```
> 房價
>   ^
>   |\
>   | \
>   |  \______
>   |         \
>   |          \____
>   +-------------------> 距離市中心(km)
>   0    5   10  15  20
> ```
>
> 這告訴你什麼？有沒有什麼有趣的發現？

---

## AI 診療機的故事：為什麼可解釋性攸關生死

### 場景：醫院導入 AI 診療輔助系統

```
┌─────────────────────────────────────────────────┐
│                   AI 診療機                       │
│                                                   │
│  輸入：血液檢查、影像資料、病歷                    │
│  輸出：「建議進一步檢查肺部腫瘤」(p=0.73)         │
│                                                   │
│  醫生需要知道：                                    │
│  1. 哪些指標觸發了這個建議？                       │
│  2. 模型有多確定？                                 │
│  3. 有沒有類似的歷史案例？                         │
│  4. 如果某個指標是誤差，結論會改變嗎？              │
│                                                   │
│  不可解釋的 AI = 不負責任的 AI                     │
└─────────────────────────────────────────────────┘
```

### 可解釋性在醫療中的要求

```
+------------------+------------------------------------------+
| 面向             | 要求                                     |
+------------------+------------------------------------------+
| 法規合規         | GDPR 要求「解釋自動化決策的邏輯」         |
| 醫療倫理         | 醫生有責任理解並驗證 AI 的建議            |
| 病人權益         | 病人有權知道為什麼得到某個診斷建議        |
| 錯誤追溯         | 出錯時需要知道「哪個環節出了問題」        |
| 持續改進         | 理解模型才能針對性地改進                 |
+------------------+------------------------------------------+
```

### 實際案例

```python
"""
可解釋的醫療預測：使用簡單特徵重要性
"""
# 模擬醫療資料
feature_names_medical = [
    '年齡', '血糖', '血壓', 'BMI', '膽固醇',
    '運動頻率', '家族病史', '吸菸年數'
]

# 對單一病人做解釋
def explain_prediction(model, patient_data, feature_names):
    """為單一病人的預測提供解釋"""
    prediction = model.predict_proba(patient_data.reshape(1, -1))[0]

    # 使用 Permutation Importance 的結果排序特徵
    important_features = sorted(
        zip(feature_names, patient_data, model.feature_importances_),
        key=lambda x: abs(x[2]),
        reverse=True
    )

    print(f"預測結果：糖尿病風險 = {prediction[1]:.1%}")
    print(f"\n主要影響因素（依重要性排序）：")
    for name, value, importance in important_features[:5]:
        direction = "↑ 增加風險" if importance > 0 else "↓ 降低風險"
        print(f"  {name}: {value:.1f} （{direction}，重要性: {importance:.3f}）")

    print(f"\n醫生建議：請特別關注前 3 項指標。")
```

---

## LIME：局部可解釋模型

LIME（Local Interpretable Model-agnostic Explanations）的核心思想很簡單：

```
LIME 的直覺：

你有一個複雜的黑盒模型。你想解釋「為什麼這個病人被判為高風險」。

1. 在這個病人的附近產生一堆「鄰居」（微調特徵值）
2. 用黑盒模型預測這些鄰居
3. 在這個局部區域，訓練一個簡單的線性模型
4. 線性模型的係數 = 局部解釋

全局複雜 ≠ 局部複雜

想像地球是圓的（全局複雜），但你站的那一小塊地看起來是平的（局部簡單）。

┌──────────────────────────────────────┐
│         複雜的決策邊界                 │
│                                       │
│     .  . . . xxxxxx . .  . .         │
│      . . .xxx      xxx. .            │
│       . .x    ★       x. .    ★ = 要解釋的點
│      . .x   (局部線性) x.            │
│       . xxx          xxx .           │
│         . .xxxxxxxxxx. .             │
│                                       │
│  在 ★ 的附近，我們可以用一條直線      │
│  來近似這個複雜的邊界                  │
└──────────────────────────────────────┘
```

### LIME 概念程式碼

```python
# 安裝：pip install lime
# 以下為概念示範（需要安裝 lime 套件）

"""
from lime.lime_tabular import LimeTabularExplainer

explainer = LimeTabularExplainer(
    X_train.values,
    feature_names=data.feature_names,
    class_names=['惡性', '良性'],
    mode='classification'
)

# 解釋單一預測
explanation = explainer.explain_instance(
    X_test.iloc[0].values,
    rf.predict_proba,
    num_features=10
)

# 顯示結果
explanation.show_in_notebook()
# 或存成 HTML
explanation.save_to_file('lime_explanation.html')
"""

# LIME 輸出的解讀：
# worst concave points > 0.15  →  +0.32（增加良性機率）
# mean radius <= 14.5          →  +0.28（增加良性機率）
# worst radius <= 16.8         →  +0.15（增加良性機率）
# worst perimeter > 110        →  -0.22（增加惡性機率）
```

---

## SHAP：全局 + 局部的解釋框架

SHAP（SHapley Additive exPlanations）基於博弈論中的 **Shapley 值**。

```
SHAP 的直覺：

想像一群朋友合作完成一個專案，最後拿到了獎金。
問題是：每個人應該分到多少獎金？

Shapley 值的做法：
1. 嘗試所有可能的「加入順序」
2. 計算每個人在每種順序中的「邊際貢獻」
3. 取平均 = 這個人的公平分潤

同理，SHAP 計算每個特徵對預測的「公平貢獻」。

基準預測（平均值）= 0.5
+------------------------+
|  年齡: +0.15           |   0.5 + 0.15 = 0.65
|  血糖: +0.20           |   0.65 + 0.20 = 0.85
|  運動: -0.10           |   0.85 - 0.10 = 0.75
|  BMI:  +0.08           |   0.75 + 0.08 = 0.83
+------------------------+
最終預測 = 0.83

每個特徵的 SHAP 值告訴你：
這個特徵讓預測「推高」或「推低」了多少。
```

### SHAP 概念程式碼

```python
# 安裝：pip install shap
# 以下為概念示範（需要安裝 shap 套件）

"""
import shap

# 建立 SHAP explainer
explainer = shap.TreeExplainer(rf)
shap_values = explainer.shap_values(X_test)

# 1. 全局特徵重要性（Summary Plot）
shap.summary_plot(shap_values[1], X_test,
                  feature_names=data.feature_names)

# 2. 單一預測的解釋（Force Plot）
shap.force_plot(
    explainer.expected_value[1],
    shap_values[1][0],
    X_test.iloc[0],
    feature_names=data.feature_names
)

# 3. 特徵依賴圖（Dependence Plot）
shap.dependence_plot(
    'worst concave points',
    shap_values[1], X_test,
    feature_names=data.feature_names
)
"""
```

### LIME vs SHAP 比較

```
+------------------+---------------------------+---------------------------+
| 面向             | LIME                      | SHAP                      |
+------------------+---------------------------+---------------------------+
| 理論基礎         | 局部線性近似              | 博弈論 Shapley 值          |
| 解釋範圍         | 局部（單一預測）          | 局部 + 全局                |
| 計算速度         | 較快                      | 較慢（精確版本）           |
| 穩定性           | 每次可能略有不同          | 理論上一致                 |
| 模型限制         | 任何模型                  | 任何模型（樹模型有加速版） |
| 適合場景         | 快速解釋單筆預測          | 完整的特徵分析             |
| 安裝難度         | pip install lime          | pip install shap           |
+------------------+---------------------------+---------------------------+
```

---

## 讓模型決策透明化：實務清單

### 模型解釋報告模板

```python
def generate_model_report(model, X_train, X_test, y_test, feature_names):
    """產生模型可解釋性報告"""

    print("=" * 60)
    print("          模型可解釋性報告")
    print("=" * 60)

    # 1. 模型基本資訊
    print(f"\n📋 模型類型: {type(model).__name__}")
    print(f"📋 特徵數量: {X_train.shape[1]}")
    print(f"📋 訓練樣本: {X_train.shape[0]}")
    print(f"📋 測試樣本: {X_test.shape[0]}")

    # 2. 整體效能
    from sklearn.metrics import accuracy_score, f1_score
    y_pred = model.predict(X_test)
    print(f"\n📊 準確率: {accuracy_score(y_test, y_pred):.4f}")
    print(f"📊 F1 Score: {f1_score(y_test, y_pred):.4f}")

    # 3. 特徵重要性（如果模型支援）
    if hasattr(model, 'feature_importances_'):
        print(f"\n🔍 Tree-based Feature Importance (Top 5):")
        imp = sorted(zip(feature_names, model.feature_importances_),
                     key=lambda x: x[1], reverse=True)
        for name, score in imp[:5]:
            print(f"   {name}: {score:.4f}")

    # 4. Permutation Importance
    perm = permutation_importance(model, X_test, y_test,
                                  n_repeats=10, random_state=42)
    print(f"\n🔍 Permutation Importance (Top 5):")
    perm_sorted = sorted(zip(feature_names, perm.importances_mean),
                         key=lambda x: x[1], reverse=True)
    for name, score in perm_sorted[:5]:
        print(f"   {name}: {score:.4f}")

    # 5. 建議
    print(f"\n💡 建議：")
    print(f"   - 重點監控前 3 項重要特徵的資料品質")
    print(f"   - 對關鍵預測使用 LIME/SHAP 做個案解釋")
    print(f"   - 定期重新評估特徵重要性的穩定性")
    print("=" * 60)

# 使用範例
generate_model_report(rf, X_train, X_test, y_test, data.feature_names)
```

---

## ⚠️ 常見陷阱

### 陷阱 1：把 feature_importances_ 當成因果關係

```
feature_importances_ 告訴你的是「相關性」，不是「因果性」

例如：模型發現「冰淇淋銷量」和「溺水人數」高度相關
→ feature_importances_ 會認為冰淇淋很重要
→ 但真正的原因是「天氣熱」

相關 ≠ 因果
重要 ≠ 有因果效應
```

### 陷阱 2：只看全局，忽略局部

```python
# 全局重要性說「年齡」是最重要特徵
# 但對於 25 歲和 65 歲的病人，
# 「年齡」的影響程度完全不同！

# ✅ 同時使用全局（PDP）和局部（LIME/SHAP）方法
```

### 陷阱 3：過度簡化解釋

```
❌ 「模型說你會得糖尿病，因為你的血糖高。」
✅ 「模型預測你的糖尿病風險為 73%。主要影響因素包括：
    1. 空腹血糖 (126 mg/dL，高於正常值 100)，貢獻 +15%
    2. BMI (31.2，屬於肥胖範圍)，貢獻 +12%
    3. 家族病史 (一等親有糖尿病)，貢獻 +10%
    這不是確定的診斷，建議進一步檢查。」
```

### 陷阱 4：忘記解釋的對象是誰

```
+------------------+------------------------------+
| 對象             | 適合的解釋方式               |
+------------------+------------------------------+
| 資料科學家       | SHAP 值、PDP、技術細節       |
| 業務主管         | Top 3 特徵 + 商業影響        |
| 醫生             | 關鍵指標 + 信心區間          |
| 病人             | 簡單語言 + 行動建議          |
| 監管機構         | 完整報告 + 公平性分析        |
+------------------+------------------------------+
```

---

## 本章總結

```
+----------------------------------------------------------+
|              模型可解釋性速查表                             |
+----------------------------------------------------------+
|                                                            |
|  「為什麼？」的三個層次：                                   |
|                                                            |
|  1. 誰重要？                                               |
|     → feature_importances_ (快但有偏差)                    |
|     → Permutation Importance (慢但可靠)                    |
|                                                            |
|  2. 怎麼重要？                                              |
|     → Partial Dependence Plot (全局趨勢)                   |
|     → SHAP Dependence Plot (全局 + 互動)                   |
|                                                            |
|  3. 這一筆為什麼？                                          |
|     → LIME (局部線性解釋)                                   |
|     → SHAP Force Plot (基於 Shapley 值)                    |
|                                                            |
|  記住：可解釋性 > 炫技                                      |
|  在高風險場景中，解釋不了的模型 = 不負責任的模型             |
+----------------------------------------------------------+
```

---

## 📝 課後練習

### 練習 1：特徵重要性比較

使用 sklearn 的波士頓房價（或加州房價）資料集：
1. 訓練 Random Forest
2. 比較 `feature_importances_` 和 Permutation Importance 的排名
3. 找出排名差異最大的特徵，分析可能的原因

### 練習 2：PDP 解讀

使用同一個模型：
1. 為最重要的 4 個特徵繪製 PDP
2. 寫下每個 PDP 的商業解讀（用非技術人員能懂的語言）

### 練習 3：模型解釋報告

選擇一個分類問題（例如信用評分或客戶流失預測）：
1. 訓練一個 Gradient Boosting 模型
2. 使用本章的 `generate_model_report` 函數產生報告
3. 選 3 個有趣的預測結果，寫出針對業務人員的解釋

### 練習 4（進階）：安裝 SHAP 並實作

```python
# pip install shap
# 1. 對你的模型產生 SHAP summary plot
# 2. 選一筆預測，產生 SHAP force plot
# 3. 比較 SHAP 的全局重要性和 Permutation Importance 的排名
```

---

> 📌 **下一章預告**：模型做好了、解釋清楚了，接下來呢？
> 第 15 章將帶你進入 **模型治理與 MLOps** — 確保模型在生產環境中
> 持續穩定、可追蹤、可重現。

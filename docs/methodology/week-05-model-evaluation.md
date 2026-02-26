# 第 5 週：模型評估與指標選擇

> Accuracy 高就是好模型嗎？

---

## 🎯 學習核心

- Accuracy 在不平衡資料上的致命缺陷
- Precision vs Recall 的取捨
- ROC-AUC 的真正意義
- 根據業務情境選擇正確的指標

---

## 為什麼這件事重要？

你建了一個詐騙偵測模型，準確率 99.5%。看起來很厲害，對吧？

但如果資料中只有 0.5% 是詐騙，那一個什麼都不做、全部預測為「非詐騙」的模型，準確率也是 99.5%。

**Accuracy 騙了你。**

在真實世界中，不同的錯誤有不同的代價：
- 把正常交易判為詐騙（False Positive）→ 客戶體驗差
- 把詐騙交易判為正常（False Negative）→ 金錢損失

**選錯指標，就會做出錯誤的決策。**

---

## 核心概念

### 分類問題的指標

#### 混淆矩陣（Confusion Matrix）

![混淆矩陣](https://cdn.prod.website-files.com/660ef16a9e0687d9cc27474a/662c42677529a0f4e97e4f96_644aea65cefe35380f198a5a_class_guide_cm08.png)

|  | 預測：Positive | 預測：Negative |
|--|---------------|---------------|
| **實際：Positive** | TP（True Positive） | FN（False Negative） |
| **實際：Negative** | FP（False Positive） | TN（True Negative） |

---

#### 核心指標

![分類指標](https://cdn.prod.website-files.com/660ef16a9e0687d9cc27474a/662c42679571ef35419c9904_647603c5a947b640e4b1eecd_classification_metrics_img_header-min.png)

| 指標 | 公式 | 回答的問題 | 適用場景 |
|------|------|-----------|---------|
| **Accuracy** | (TP+TN) / 全部 | 整體對了多少？ | 類別平衡時 |
| **Precision** | TP / (TP+FP) | 預測為正的裡面，有多少真的是正？ | 誤報成本高時 |
| **Recall** | TP / (TP+FN) | 真正為正的裡面，有多少被找到？ | 漏報成本高時 |
| **F1 Score** | 2 × (P×R)/(P+R) | Precision 和 Recall 的調和平均 | 需要平衡兩者時 |
| **Specificity** | TN / (TN+FP) | 真正為負的裡面，有多少被正確排除？ | 需要高排除力時 |

---

#### Precision vs Recall 的取捨

![Precision-Recall](https://cdn.prod.website-files.com/660ef16a9e0687d9cc27474a/662c42679571ef35419c9935_647607123e84a06a426ce627_classification_metrics_014-min.png)

**你不能同時最大化 Precision 和 Recall**，這就是取捨（trade-off）。

調整分類閾值（threshold）的效果：
- **閾值提高** → Precision ↑, Recall ↓（更謹慎，寧可漏判也不誤判）
- **閾值降低** → Precision ↓, Recall ↑（更積極，寧可誤判也不漏判）

**怎麼選？看業務情境：**

| 場景 | 優先指標 | 為什麼 |
|------|---------|--------|
| 詐騙偵測 | Recall | 漏掉一筆詐騙的損失 >> 多查一筆正常交易的成本 |
| 垃圾郵件過濾 | Precision | 把重要郵件當垃圾信的後果很嚴重 |
| 醫療篩檢 | Recall | 漏診的後果可能致命 |
| 推薦系統 | Precision | 推薦不相關的內容會降低用戶信任 |
| 司法判決 | Precision | 「寧可放過，不可錯殺」 |

---

#### ROC 曲線與 AUC

![ROC-AUC](https://miro.medium.com/v2/resize%3Afit%3A1248/1%2ATqzfzabXrej1FTdZuNNYIQ.png)

**ROC 曲線**（Receiver Operating Characteristic）：
- X 軸：False Positive Rate（1 - Specificity）
- Y 軸：True Positive Rate（Recall）
- 每個點代表一個閾值下的表現

**AUC**（Area Under the Curve）：
- AUC = 1.0：完美模型
- AUC = 0.5：隨機猜測（和擲硬幣一樣）
- AUC < 0.5：比隨機還差（模型的預測方向反了）

> 💡 **AUC 的直覺解釋**：隨機選一個正樣本和一個負樣本，模型給正樣本更高分數的機率。

---

### 回歸問題的指標

| 指標 | 公式 | 特性 | 適用場景 |
|------|------|------|---------|
| **MAE** | mean(\|y - ŷ\|) | 對異常值穩健 | 誤差的絕對大小重要時 |
| **MSE** | mean((y - ŷ)²) | 懲罰大誤差 | 大誤差的代價特別高時 |
| **RMSE** | √MSE | 和 y 同單位 | 需要可解釋的誤差單位時 |
| **R²** | 1 - SS_res/SS_tot | 解釋了多少變異 | 需要相對衡量時 |
| **MAPE** | mean(\|y-ŷ\|/\|y\|) | 百分比誤差 | 不同尺度的比較 |

**R² 的陷阱**：
- R² = 0.9 不代表模型很好 — 在某些領域，0.3 就很好了
- R² 可以是負的（模型比用平均值預測還差）
- 加入更多特徵，R² 永遠不會下降（即使特徵是垃圾）→ 用 Adjusted R²

---

## 🧪 實作任務

### 任務 A：Accuracy 的陷阱

```python
import numpy as np
from sklearn.datasets import make_classification
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, precision_score, recall_score,
                             f1_score, classification_report, confusion_matrix)

# 產生不平衡資料（5% positive）
X, y = make_classification(n_samples=2000, n_features=20,
                           weights=[0.95, 0.05], random_state=42)

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.3,
                                                      random_state=42)

# 「笨模型」：全部預測為 0
y_pred_dumb = np.zeros_like(y_test)
print("=== 全部預測為 Negative ===")
print(f"Accuracy: {accuracy_score(y_test, y_pred_dumb):.4f}")
print(f"Recall:   {recall_score(y_test, y_pred_dumb):.4f}")

# 真正的模型
model = LogisticRegression(max_iter=1000)
model.fit(X_train, y_train)
y_pred = model.predict(X_test)
print("\n=== Logistic Regression ===")
print(classification_report(y_test, y_pred))
```

**問題**：笨模型的 Accuracy 是多少？這說明了什麼？

### 任務 B：閾值調整

```python
import matplotlib.pyplot as plt
from sklearn.metrics import precision_recall_curve, roc_curve, roc_auc_score

# 取得機率分數
y_scores = model.predict_proba(X_test)[:, 1]

# Precision-Recall Curve
precision, recall, thresholds_pr = precision_recall_curve(y_test, y_scores)

plt.figure(figsize=(12, 5))

plt.subplot(1, 2, 1)
plt.plot(recall, precision, 'b-')
plt.xlabel('Recall')
plt.ylabel('Precision')
plt.title('Precision-Recall Curve')
plt.grid(True, alpha=0.3)

# ROC Curve
fpr, tpr, thresholds_roc = roc_curve(y_test, y_scores)
auc = roc_auc_score(y_test, y_scores)

plt.subplot(1, 2, 2)
plt.plot(fpr, tpr, 'b-', label=f'AUC = {auc:.3f}')
plt.plot([0, 1], [0, 1], 'r--', label='Random')
plt.xlabel('False Positive Rate')
plt.ylabel('True Positive Rate')
plt.title('ROC Curve')
plt.legend()
plt.grid(True, alpha=0.3)

plt.tight_layout()
plt.show()

# 嘗試不同閾值
print("\n=== 不同閾值的影響 ===")
for threshold in [0.3, 0.5, 0.7]:
    y_pred_t = (y_scores >= threshold).astype(int)
    p = precision_score(y_test, y_pred_t, zero_division=0)
    r = recall_score(y_test, y_pred_t)
    f1 = f1_score(y_test, y_pred_t, zero_division=0)
    print(f"閾值={threshold:.1f} → Precision={p:.3f}, Recall={r:.3f}, F1={f1:.3f}")
```

### 任務 C：業務情境決策

針對以下兩個情境，分別選擇最佳的閾值，並解釋理由：

**情境 1：醫療篩檢**
- 陽性 = 疑似癌症，需進一步檢查（成本 $500）
- 漏診 = 延誤治療（成本 $100,000+）
- 你會選什麼閾值？為什麼？

**情境 2：電商推薦**
- 推薦 = 發送促銷郵件（成本 $0.50/封）
- 精準推薦 = 購買轉換（收益 $50）
- 你會選什麼閾值？為什麼？

用程式碼計算兩個情境下，不同閾值的「預期淨效益」：

```python
# 提示：
# 情境 1 的淨效益 = -500 × FP + (-100000) × FN + 0 × TP + 0 × TN
# 情境 2 的淨效益 = -0.5 × (TP + FP) + 50 × TP

# 你來完成這個分析！
```

---

## 🧠 反思問題

1. **詐騙偵測與醫療診斷，該選哪個指標？** 分別說明理由，並討論閾值該如何設定。

2. **AUC = 0.95 但 F1 = 0.3，可能嗎？** 什麼情況下會發生這種事？

3. **在回歸問題中，MAE 和 MSE 會給出不同的「最佳模型」嗎？** 舉例說明。

4. **你的公司只讓你報告一個指標，你會選哪個？** 為什麼只看一個指標是危險的？

---

## 延伸閱讀

- [Google ML Crash Course: Classification](https://developers.google.com/machine-learning/crash-course/classification) — 分類指標互動教學
- [Scikit-learn: Metrics](https://scikit-learn.org/stable/modules/model_evaluation.html) — 完整指標文件
- Provost & Fawcett, *Data Science for Business* — 第 8 章

---

## 本週 Checklist

- [ ] 完成任務 A：體驗 Accuracy 的陷阱
- [ ] 完成任務 B：閾值調整與 ROC 曲線
- [ ] 完成任務 C：業務情境決策分析
- [ ] 回答全部反思問題
- [ ] 將程式碼與筆記推送至 GitHub

---

[← 上一週：模型訓練與資料切分](week-04-model-training.md) ｜ [→ 下一週：整合 — 從數據到決策](week-06-integration.md)

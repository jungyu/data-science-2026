# Scikit-learn 機器學習實戰手冊

> **深入淺出系列** — 用 scikit-learn 建立機器學習思維骨架

```
「這門課不追求 SOTA，不追求 Kaggle Top 1%。
  這門課追求：正確流程、可重現性、評估思維、模型理解、可解釋性。」
```

---

## 課程定位

| 項目 | 說明 |
|------|------|
| **工具核心** | Python + NumPy + Pandas + Scikit-learn |
| **教學哲學** | 可重現實驗 → 正確資料流程 → 模型思維 → 評估思維 |
| **目標學生** | 資管系大學生、想建立 ML 正確觀念的實務工作者 |
| **課程長度** | 18 週（90 分鐘 × 18） |

---

## 四年能力地圖

```
🟢 第一層：資料素養        → Pandas + scikit-learn → 能建立「可信的模型流程」
🟡 第二層：模型思維        → Bias-Variance + 評估指標 → 不迷信準確率
🟠 第三層：商業轉譯能力    → KPI + 成本函數 + ROI → 模型是 ROI 正值，不是 95% accuracy
🔴 第四層：系統與治理      → Pipeline + 版本控制 + 可解釋性 → 長期可維運
```

---

## 目錄

### 🧱 第一階段：機器學習的正確觀念（第 1–3 週）

| 章節 | 主題 | 核心問題 |
|------|------|----------|
| [Ch01](ch01-what-is-ml.md) | 什麼是機器學習？ | 為什麼要切資料？ |
| [Ch02](ch02-sklearn-philosophy.md) | Scikit-learn 的設計哲學 | 為什麼所有模型 API 都長一樣？ |
| [Ch03](ch03-pipeline-thinking.md) | Pipeline 思維 | ML 不是模型，是流程 |

### 📊 第二階段：監督式學習（第 4–9 週）

| 章節 | 主題 | 核心問題 |
|------|------|----------|
| [Ch04](ch04-linear-regression.md) | 線性回歸 | 高 R² 是否代表好模型？ |
| [Ch05](ch05-logistic-regression.md) | 邏輯斯回歸與分類評估 | Accuracy 在不平衡資料會騙人？ |
| [Ch06](ch06-knn-bias-variance.md) | KNN 與 Bias-Variance | 模型太複雜會怎樣？ |
| [Ch07](ch07-decision-trees.md) | 決策樹 | 可解釋性 vs 過擬合？ |
| [Ch08](ch08-random-forest.md) | Random Forest | 為什麼 80% 問題 RF 夠用？ |
| [Ch09](ch09-cross-validation.md) | 交叉驗證與模型評估 | 一次實驗能當真理嗎？ |

### 🧠 第三階段：非監督式學習（第 10–12 週）

| 章節 | 主題 | 核心問題 |
|------|------|----------|
| [Ch10](ch10-kmeans.md) | K-means 分群 | 怎麼決定分幾群？ |
| [Ch11](ch11-pca.md) | PCA 降維 | 為什麼可以壓縮資料？ |
| [Ch12](ch12-anomaly-detection.md) | 異常偵測 | ML 不只是分類 |

### ⚙️ 第四階段：完整專案實戰（第 13–18 週）

| 章節 | 主題 | 核心問題 |
|------|------|----------|
| [Ch13](ch13-business-cost.md) | 商業成本函數 | 誤判的代價是什麼？ |
| [Ch14](ch14-model-interpretability.md) | 模型可解釋性 | 可解釋性 > 炫技 |
| [Ch15](ch15-model-governance.md) | 模型治理與 MLOps | 如何讓模型長期可維運？ |
| [Ch16](ch16-risk-ethics.md) | 風險與倫理 | 偏見、黑箱、公平性 |
| [Ch17](ch17-capstone-project.md) | 專案製作與期末發表 | 能設計實驗，不只調參數 |

### 📎 附錄

| 章節 | 主題 |
|------|------|
| [Appendix A](appendix-a-quick-reference.md) | scikit-learn 快速參考卡 |

---

## 教學核心哲學

```
這門課培養的不是：          這門課培養的是：
❌ 只會 call API 的人        ✅ 能設計實驗的人
❌ 只會調參數的人            ✅ 能控制風險的人
❌ 追求 accuracy 的人        ✅ 能評估 ROI 的人
                             ✅ 能治理模型的人
```

> **一句話定位**：ML 在資管系，不是演算法競賽，而是「決策放大器」。

---

## 環境設定

```bash
# 建議使用 Python 3.10+
pip install scikit-learn pandas numpy matplotlib seaborn jupyter
```

```python
# 版本確認
import sklearn
print(sklearn.__version__)  # >= 1.3
```

---

## 評分標準

期末專案不是比誰 accuracy 高，而是：

| 評分維度 | 權重 | 說明 |
|----------|------|------|
| 流程正確性 | 30% | 資料切分、Pipeline 使用、無資料洩漏 |
| 評估完整性 | 25% | 多指標、交叉驗證、統計檢定 |
| 風險討論 | 20% | 偏見、限制、失敗模式 |
| 商業洞察 | 15% | 成本分析、ROI、決策建議 |
| 程式品質 | 10% | 可讀性、版本控制、文件完整 |

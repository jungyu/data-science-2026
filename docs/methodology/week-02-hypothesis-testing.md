# 第 2 週：假設檢定與其陷阱

> p < 0.05 就代表有效嗎？

---

## 🎯 學習核心

- 理解 H₀ 與 H₁ 的邏輯
- 型一錯誤與型二錯誤的代價
- 多重檢定問題：為什麼做越多測試，越容易「發現」假效果

---

## 為什麼這件事重要？

你在一家新創公司工作，產品團隊說：「我們改了首頁按鈕的顏色，轉換率從 3.2% 變成 3.5%，p-value = 0.03，效果顯著！」

聽起來很棒。但你應該問：

- 他們只測了按鈕顏色嗎？還是同時測了 20 種改動？
- 樣本數多大？這 0.3% 的差異在商業上有意義嗎？
- 他們有沒有在看到結果後才「決定」要測這個指標？

**假設檢定是強大的工具，但也是最容易被誤用的工具。**

---

## 核心概念

### 1️⃣ p-value 到底是什麼？

![p-value 分布](https://varianceexplained.org/figs/2014-12-15-interpreting-pvalue-histogram/unnamed-chunk-2-1.png)

> **定義**：在虛無假設（H₀）為真的前提下，觀察到目前數據（或更極端數據）的機率。

用白話說：

> 「如果真的沒有效果，我看到這種結果的機率有多低？」

**p-value 不是什麼**：

| 常見誤解 | 正確理解 |
|---------|---------|
| ❌ 效果為真的機率 | ✅ 在 H₀ 為真時，觀察到此數據的機率 |
| ❌ 效果的大小 | ✅ 只反映「意外程度」，不反映效果量 |
| ❌ 結果可重現的機率 | ✅ 與可重現性無直接關係 |
| ❌ p < 0.05 就是「真的」 | ✅ 0.05 只是一個慣例門檻，不是魔法數字 |

---

### 2️⃣ 兩類錯誤

![假設檢定錯誤](https://online.stat.psu.edu/stat100/assets/Validation.gif)

|  | H₀ 為真（沒有效果） | H₀ 為假（真的有效果） |
|--|---------------------|---------------------|
| **拒絕 H₀** | 🔴 型一錯誤（False Positive） | ✅ 正確決定（Power） |
| **不拒絕 H₀** | ✅ 正確決定 | 🔴 型二錯誤（False Negative） |

**型一錯誤（α）**：宣稱有效果，但其實沒有。
- 後果：浪費資源去推動無效的改變
- 控制方法：設定顯著水準（通常 α = 0.05）

**型二錯誤（β）**：宣稱沒效果，但其實有。
- 後果：錯過了真正有價值的改善
- 控制方法：增加樣本數、增加效果量

> 💡 **思考**：在醫療領域，哪種錯誤的後果更嚴重？在行銷領域呢？

---

### 3️⃣ 統計檢定力（Power）

![檢定力](https://i.sstatic.net/VW9qQ.png)

**Power = 1 - β = 正確偵測到真實效果的機率**

影響 Power 的因素：
- **樣本數**（n）：越大越好
- **效果量**（effect size）：真實差異越大越容易偵測
- **顯著水準**（α）：放寬 α 可以提高 Power，但型一錯誤也會增加
- **變異數**：資料越分散，越難偵測效果

```
Power 分析的核心問題：
「要多少樣本，才能有 80% 的把握偵測到 X 大小的效果？」
```

---

### 4️⃣ 多重比較問題（Multiple Comparisons）

這是最常見、也最危險的統計陷阱。

**情境**：你同時測試了 20 個指標，其中 1 個的 p-value < 0.05。

**問題**：如果每個測試的 α = 0.05，做 20 次測試時，至少 1 個「顯著」的機率是：

```
P(至少 1 個顯著) = 1 - (1 - 0.05)²⁰ = 1 - 0.95²⁰ ≈ 0.64
```

**64%！** 即使所有效果都不存在，你仍有 64% 的機率「發現」至少一個顯著結果。

**修正方法**：

| 方法 | 做法 | 適用場景 |
|------|------|---------|
| **Bonferroni** | α' = α / n（測試數量） | 保守，適合少量測試 |
| **Holm** | 排序後逐步修正 | 比 Bonferroni 寬鬆，適合中等數量 |
| **FDR (Benjamini-Hochberg)** | 控制假發現率 | 適合大量測試（如基因研究） |

---

## 🧪 實作任務

### 任務 A：親眼看見假陽性

模擬「沒有效果」的世界，觀察假陽性如何產生：

```python
import numpy as np
from scipy import stats

np.random.seed(42)

# 模擬：兩組完全相同的分布（沒有真實效果）
n_tests = 100
p_values = []

for _ in range(n_tests):
    group_a = np.random.normal(loc=50, scale=10, size=100)
    group_b = np.random.normal(loc=50, scale=10, size=100)  # 同樣的分布！
    _, p = stats.ttest_ind(group_a, group_b)
    p_values.append(p)

# 計算「顯著」的比例
significant = sum(1 for p in p_values if p < 0.05)
print(f"100 次檢定中，p < 0.05 的次數：{significant}")
print(f"假陽性率：{significant}%")
print(f"理論預期：≈ 5%")
```

**問題**：你得到的假陽性率接近 5% 嗎？跑 10 次實驗，觀察這個比例的變異。

### 任務 B：p-value 分布

```python
import matplotlib.pyplot as plt

# 畫出所有 p-value 的直方圖
plt.figure(figsize=(10, 4))

# 情境 1：H₀ 為真（無效果）
plt.subplot(1, 2, 1)
p_null = []
for _ in range(1000):
    a = np.random.normal(50, 10, 100)
    b = np.random.normal(50, 10, 100)
    _, p = stats.ttest_ind(a, b)
    p_null.append(p)
plt.hist(p_null, bins=20, edgecolor='black', alpha=0.7)
plt.title('H₀ 為真時的 p-value 分布')
plt.xlabel('p-value')

# 情境 2：H₁ 為真（有效果）
plt.subplot(1, 2, 2)
p_alt = []
for _ in range(1000):
    a = np.random.normal(50, 10, 100)
    b = np.random.normal(52, 10, 100)  # 平均值差 2
    _, p = stats.ttest_ind(a, b)
    p_alt.append(p)
plt.hist(p_alt, bins=20, edgecolor='black', alpha=0.7, color='orange')
plt.title('H₁ 為真時的 p-value 分布')
plt.xlabel('p-value')

plt.tight_layout()
plt.show()
```

**觀察**：兩張圖的分布形狀有什麼不同？為什麼？

### 任務 C：多重比較修正

```python
from statsmodels.stats.multitest import multipletests

# 模擬 20 個同時進行的測試
p_values_multi = []
for _ in range(20):
    a = np.random.normal(50, 10, 50)
    b = np.random.normal(50, 10, 50)
    _, p = stats.ttest_ind(a, b)
    p_values_multi.append(p)

# 未修正
sig_raw = sum(1 for p in p_values_multi if p < 0.05)

# Bonferroni 修正
reject_bonf, pvals_bonf, _, _ = multipletests(p_values_multi, method='bonferroni')
sig_bonf = sum(reject_bonf)

# FDR 修正
reject_fdr, pvals_fdr, _, _ = multipletests(p_values_multi, method='fdr_bh')
sig_fdr = sum(reject_fdr)

print(f"未修正：{sig_raw} 個顯著")
print(f"Bonferroni：{sig_bonf} 個顯著")
print(f"FDR：{sig_fdr} 個顯著")
```

---

## 🧠 反思問題

1. **什麼情境適合用假設檢定？** 列出 3 個具體的業界場景。

2. **什麼情境不適合？** 為什麼有些研究者主張「禁用 p-value」？

3. **效果量（effect size）與 p-value 的關係是什麼？** 如果 p-value 很小但效果量也很小，你會怎麼做決策？

4. **「事後假設」（post-hoc hypothesis）為什麼危險？** 舉一個你可能會犯這種錯誤的例子。

5. **在你的領域中，型一錯誤和型二錯誤哪個代價更高？** 為什麼？

---

## 延伸閱讀

- [ASA Statement on Statistical Significance and P-Values (2016)](https://amstat.tandfonline.com/doi/full/10.1080/00031305.2016.1154108) — 美國統計學會官方聲明
- [The p-value, deconstructed (Variance Explained)](https://varianceexplained.org/) — 直覺化解釋
- Wasserstein & Lazar, "The ASA Statement on p-Values" — 必讀經典

---

## 本週 Checklist

- [ ] 完成任務 A：模擬假陽性實驗
- [ ] 完成任務 B：畫出 p-value 分布圖
- [ ] 完成任務 C：多重比較修正
- [ ] 回答全部反思問題
- [ ] 將程式碼與筆記推送至 GitHub

---

[← 上一週：不確定性的本質](week-01-uncertainty.md) ｜ [→ 下一週：因果推論與實驗設計](week-03-causal-inference.md)

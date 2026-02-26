# 第 3 週：因果推論與實驗設計

> 相關真的等於因果嗎？

---

## 🎯 學習核心

- 相關不等於因果 — 理解為什麼
- 混淆變數如何扭曲你的結論
- 隨機化是建立因果關係的黃金標準
- A/B 測試的完整設計流程

---

## 為什麼這件事重要？

新聞標題：「研究發現，每天喝咖啡的人壽命更長！」

你的第一反應應該是：**等等，這是相關還是因果？**

也許喝咖啡的人收入較高、生活習慣較健康、有更好的醫療資源。是咖啡讓他們長壽，還是其他因素？

在商業場景中，這個問題更加關鍵：

- 「安裝了我們 App 的用戶，留存率高 30%」— 是 App 好用，還是本來就是忠實用戶才會安裝？
- 「參加培訓的員工績效更好」— 是培訓有效，還是本來績效好的人才會報名？

**如果分不清相關與因果，你的每一個「數據驅動的決策」都可能是錯的。**

---

## 核心概念

### 1️⃣ 混淆變數（Confounder）

![因果圖](https://images.openai.com/static-rsc-3/FNiBi4dViZ2JX6Yw3yDwXGB9CRe75K_WReF4Fic2nfe_3kGWwYwH7oRSHK78pl8G3wjoKL9gidg_54YtHD6pP-h9iUbarv8YAPfCdkksbAg?purpose=fullsize&v=1)

混淆變數是同時影響自變數（X）和因變數（Y）的第三方變數（Z）。

```
        Z（混淆變數）
       ↙         ↘
      X    →?→    Y
   (自變數)      (因變數)
```

**經典例子**：

| 觀察到的相關 | 真正的混淆變數 |
|-------------|--------------|
| 冰淇淋銷量 ↔ 溺水事件 | 夏天（氣溫） |
| 鞋子尺寸 ↔ 閱讀能力 | 年齡 |
| 醫院等級 ↔ 死亡率（正相關！） | 病患嚴重程度 |

> 💡 **Simpson's Paradox**：當你加入一個混淆變數後，原本的正相關可能變成負相關。這不是數據出錯，而是你之前被混淆了。

---

### 2️⃣ 建立因果的方法

![RCT 流程](https://www.researchgate.net/publication/258765684/figure/fig1/AS%3A267339178442762%401440750035676/Flow-diagram-of-the-randomized-controlled-trial.png)

| 方法 | 因果強度 | 適用場景 | 限制 |
|------|---------|---------|------|
| **隨機對照實驗（RCT）** | ⭐⭐⭐⭐⭐ | A/B 測試、臨床試驗 | 成本高、有些情境無法隨機化 |
| **準實驗（Quasi-experiment）** | ⭐⭐⭐⭐ | 政策評估、自然實驗 | 需要合理的控制組 |
| **工具變數（IV）** | ⭐⭐⭐ | 無法隨機化時 | 好的工具變數難找 |
| **迴歸不連續（RDD）** | ⭐⭐⭐ | 有門檻的政策效果 | 只估計門檻附近的效果 |
| **差異中的差異（DID）** | ⭐⭐⭐ | 前後對照、政策效果 | 需要平行趨勢假設 |
| **觀察性研究 + 控制變數** | ⭐⭐ | 回溯性分析 | 永遠可能遺漏混淆變數 |
| **單純相關分析** | ⭐ | 探索性分析 | 不能推因果 |

---

### 3️⃣ 隨機化：為什麼它是黃金標準？

![RCT 設計](https://www.ebmconsult.com/content/images/Stats/Randomized%20Control%20Trial%20Deisgn.png)

隨機分配的魔力在於：

> **它讓所有變數（包括你不知道的）在兩組之間平均分布。**

- 已知的混淆變數？隨機化處理了。
- 未知的混淆變數？隨機化也處理了。
- 未來才會發現的混淆變數？隨機化還是處理了。

這就是為什麼 RCT 是因果推論的黃金標準。

```
隨機分配
    ├── 實驗組（看到新功能）
    │     └── 測量結果
    └── 控制組（看到舊功能）
          └── 測量結果

兩組的差異 = 新功能的因果效果
（因為其他所有因素已被隨機化平衡）
```

---

### 4️⃣ A/B 測試設計流程

在科技公司，A/B 測試是最常見的因果推論工具。一個嚴謹的 A/B 測試需要：

**Step 1：定義假設**
```
H₀：新版首頁的轉換率 = 舊版首頁的轉換率
H₁：新版首頁的轉換率 > 舊版首頁的轉換率
```

**Step 2：選擇指標**
- 主要指標（primary metric）：只能有一個，做決策用
- 護欄指標（guardrail metrics）：確保不會傷害其他面向

**Step 3：計算樣本數**
- 根據 MDE（Minimum Detectable Effect）、α、Power 決定
- 「要多少用戶才能偵測到 2% 的轉換率提升？」

**Step 4：隨機分流**
- 用戶層級（user-level）vs 請求層級（request-level）
- 確保分流機制不會引入偏差

**Step 5：執行與監控**
- 不要偷看結果（peeking problem）
- 設定實驗結束日期並遵守

**Step 6：分析與決策**
- 檢查隨機化是否平衡（A/A 檢查）
- 計算效果量與信賴區間
- 做出決策並記錄理由

---

## 🧪 實作任務

### 任務 A：模擬混淆變數

```python
import numpy as np
import pandas as pd
from scipy import stats

np.random.seed(42)
n = 1000

# 真實的因果結構：
# Z（年齡）→ X（運動量）
# Z（年齡）→ Y（健康指數）
# X 對 Y 沒有直接因果效果

z = np.random.normal(40, 10, n)       # 年齡
x = -0.5 * z + np.random.normal(0, 5, n)  # 年輕人運動更多
y = -0.3 * z + np.random.normal(0, 5, n)  # 年輕人更健康

# 觀察相關
corr_xy, p_xy = stats.pearsonr(x, y)
print(f"X（運動）與 Y（健康）的相關：r = {corr_xy:.3f}, p = {p_xy:.4f}")
print("→ 看起來運動讓人更健康！但真的是這樣嗎？")

# 控制混淆變數後
from sklearn.linear_model import LinearRegression

# 用殘差法控制 Z
model_x = LinearRegression().fit(z.reshape(-1, 1), x)
model_y = LinearRegression().fit(z.reshape(-1, 1), y)
x_residual = x - model_x.predict(z.reshape(-1, 1))
y_residual = y - model_y.predict(z.reshape(-1, 1))

corr_partial, p_partial = stats.pearsonr(x_residual, y_residual)
print(f"\n控制年齡後，X 與 Y 的偏相關：r = {corr_partial:.3f}, p = {p_partial:.4f}")
print("→ 效果消失了！原來是年齡造成的假象。")
```

### 任務 B：設計你的 A/B 測試

選擇以下其中一個情境，完成完整的 A/B 測試設計文件：

**情境選項**：
1. 電商網站：測試「免運費門檻從 $1000 降到 $500」對訂單金額的影響
2. 教育平台：測試「加入 AI 助教」對課程完成率的影響
3. SaaS 產品：測試「簡化註冊流程（5 步 → 2 步）」對註冊轉換率的影響

**你的設計文件需包含**：
1. **假設**：明確的 H₀ 與 H₁
2. **主要指標**：一個可量化的指標
3. **護欄指標**：至少 2 個確保不傷害其他面向
4. **分流方式**：如何隨機分配用戶
5. **樣本數估計**：需要多少用戶（可使用線上計算器）
6. **風險評估**：可能出錯的地方與因應方案
7. **決策規則**：什麼結果會讓你做什麼決定

### 任務 C：Power 分析

```python
from statsmodels.stats.power import TTestIndPower

analysis = TTestIndPower()

# 情境：你想偵測 5% 的轉換率提升（從 10% 到 10.5%）
# 計算需要多少樣本
effect_sizes = [0.1, 0.2, 0.3, 0.5, 0.8]

for es in effect_sizes:
    n = analysis.solve_power(effect_size=es, alpha=0.05, power=0.8)
    print(f"效果量 = {es:.1f} → 每組需要 {n:.0f} 個樣本")
```

**問題**：為什麼效果量越小，需要的樣本數越多？這對業界的 A/B 測試有什麼啟示？

---

## 🧠 反思問題

1. **如果不能隨機分配，該怎麼辦？** 列出至少 2 種替代方法，並說明各自的限制。

2. **你在新聞或社群媒體上，最近看到哪些「把相關當因果」的例子？** 分析其中的可能混淆變數。

3. **A/B 測試的「偷看問題」（peeking problem）是什麼？** 為什麼不能在實驗結束前就根據結果做決定？

4. **在哪些情境下，我們不應該（或不能）做 A/B 測試？** 倫理考量？技術限制？

---

## 延伸閱讀

- Angrist & Pischke, *Mostly Harmless Econometrics* — 因果推論經典
- [Trustworthy Online Controlled Experiments (Microsoft)](https://exp-platform.com/Documents/2013%20controlledExperimentsAtScale.pdf) — A/B 測試實務
- [Causal Inference: The Mixtape](https://mixtape.scunning.com/) — 免費線上教材

---

## 本週 Checklist

- [ ] 完成任務 A：模擬混淆變數
- [ ] 完成任務 B：撰寫 A/B 測試設計文件
- [ ] 完成任務 C：Power 分析
- [ ] 回答全部反思問題
- [ ] 將程式碼與設計文件推送至 GitHub

---

[← 上一週：假設檢定與其陷阱](week-02-hypothesis-testing.md) ｜ [→ 下一週：模型訓練與資料切分](week-04-model-training.md)

# Chapter 01：視覺化思維的革命

> 第 1 週 — 從「命令電腦畫圖」到「描述圖表該長什麼樣」

---

## 本章目標

- 深入理解 Imperative vs Declarative 的差異
- 理解為什麼 Declarative 是一場思維革命
- 認識 Grammar of Graphics 的核心概念
- 寫出你的第一張 Altair 圖表

---

## 1.1 兩種思維方式

想像你要請人幫你煮一碗番茄蛋花湯。

### Imperative（指令式）

> 「先把鍋子放到爐子上，開中火，倒入 500ml 水，等水滾。然後把兩顆番茄切丁丟進去，煮三分鐘。接著打兩顆蛋，攪散，沿著筷子慢慢倒進湯裡。最後加鹽和香油。」

你描述了 **每一個步驟**。如果對方不照順序做，湯就不對。

### Declarative（宣告式）

> 「我要一碗番茄蛋花湯，兩人份，少鹽。」

你描述了 **你想要什麼**，至於怎麼做，交給廚師（引擎）決定。

### 在視覺化中的對應

**matplotlib（Imperative）**：
```python
import matplotlib.pyplot as plt

fig, ax = plt.subplots(figsize=(8, 5))    # 步驟 1：建立畫布
ax.bar(['A','B','C'], [10,20,15])          # 步驟 2：畫長條
ax.set_title('Sales by Category')          # 步驟 3：加標題
ax.set_xlabel('Category')                  # 步驟 4：加 X 標籤
ax.set_ylabel('Sales')                     # 步驟 5：加 Y 標籤
ax.grid(axis='y', alpha=0.3)              # 步驟 6：加格線
plt.tight_layout()                         # 步驟 7：調整佈局
plt.show()                                 # 步驟 8：顯示
```

你在 **命令電腦**：「先建畫布，再畫長條，再加標題......」

**Altair（Declarative）**：
```python
import altair as alt
import pandas as pd

df = pd.DataFrame({
    'category': ['A', 'B', 'C'],
    'sales': [10, 20, 15]
})

alt.Chart(df).mark_bar().encode(
    x='category',
    y='sales'
)
```

你在 **描述規格**：「這是一張長條圖，x 軸是 category，y 軸是 sales。」

---

## 1.2 為什麼這是「思維革命」？

### 表面差異：程式碼行數

matplotlib 需要 8 行，Altair 只需要 4 行。但行數不是重點。

### 深層差異：你在思考什麼？

| | matplotlib | Altair |
|--|-----------|--------|
| **你在想** | 「下一步要畫什麼？」 | 「資料如何映射成圖？」 |
| **關注點** | 繪圖過程（How） | 圖表結構（What） |
| **修改方式** | 改步驟順序和參數 | 改欄位映射 |
| **產出物** | 一張圖片 | 一份規格（JSON） |
| **可重用性** | 低（程式碼即圖表） | 高（規格可存取、傳遞） |

### 類比：HTML vs Canvas

這就像網頁開發中的：

```html
<!-- Declarative：描述結構 -->
<h1>標題</h1>
<p>段落</p>
```

```javascript
// Imperative：指令繪製
ctx.font = '32px Arial';
ctx.fillText('標題', 10, 40);
ctx.font = '16px Arial';
ctx.fillText('段落', 10, 70);
```

HTML 描述 **「什麼東西在那裡」**，Canvas 描述 **「怎麼把東西畫出來」**。

Altair 之於 matplotlib，就像 HTML 之於 Canvas。

---

## 1.3 Grammar of Graphics：視覺化的文法

Altair 的設計基於 **Grammar of Graphics**（圖形文法），這是統計學家 Leland Wilkinson 在 1999 年提出的理論框架。

核心思想是：**任何圖表都可以拆解為幾個基本元素的組合**。

```
圖表 = 資料（Data）
     + 轉換（Transform）
     + 標記（Mark）
     + 編碼（Encoding）
     + 尺度（Scale）
     + 座標系（Coordinate）
```

### 用例子理解

假設你有一份咖啡店的銷售資料：

| 月份 | 品項 | 銷售額 |
|------|------|--------|
| 1月 | 拿鐵 | 120 |
| 1月 | 美式 | 80 |
| 2月 | 拿鐵 | 150 |
| 2月 | 美式 | 90 |

你想做一張「各月份、各品項的銷售比較圖」。

**用 Grammar of Graphics 的思維**：

- **Data**：上面那張表
- **Mark**：長條（bar）
- **Encoding**：
  - x → 月份
  - y → 銷售額
  - color → 品項

不需要思考「怎麼畫」，只需要思考「什麼對應什麼」。

```python
import altair as alt
import pandas as pd

df = pd.DataFrame({
    'month': ['1月', '1月', '2月', '2月'],
    'item': ['拿鐵', '美式', '拿鐵', '美式'],
    'sales': [120, 80, 150, 90]
})

alt.Chart(df).mark_bar().encode(
    x='month',
    y='sales',
    color='item'
)
```

Altair 自動幫你處理：
- 分組
- 顏色配置
- 圖例
- 軸標籤

你只需要「宣告映射關係」。

---

## 1.4 Encoding：視覺化的核心概念

**Encoding（編碼）** 是 Altair 最核心的概念。它定義了 **資料欄位如何映射到視覺通道**。

### 視覺通道一覽

| 通道 | 說明 | 適合的資料類型 |
|------|------|---------------|
| `x` | 水平位置 | 所有類型 |
| `y` | 垂直位置 | 所有類型 |
| `color` | 顏色 | 分類 / 數值 |
| `size` | 大小 | 數值 |
| `shape` | 形狀 | 分類 |
| `opacity` | 透明度 | 數值 |
| `tooltip` | 滑鼠提示 | 所有類型 |
| `row` | 分面（列） | 分類 |
| `column` | 分面（欄） | 分類 |

### 資料類型

Altair 需要知道每個欄位的「類型」，以決定如何呈現：

| 類型 | 簡寫 | 說明 | 例子 |
|------|------|------|------|
| `quantitative` | `Q` | 連續數值 | 溫度、銷售額 |
| `ordinal` | `O` | 有序分類 | 小/中/大、Q1/Q2/Q3 |
| `nominal` | `N` | 無序分類 | 品項名、城市 |
| `temporal` | `T` | 時間 | 日期、時間戳 |

```python
# 明確指定類型（推薦）
alt.Chart(df).mark_point().encode(
    x='year:O',          # ordinal
    y='sales:Q',         # quantitative
    color='item:N',      # nominal
    size='profit:Q'      # quantitative
)
```

> **重要觀念**：同一個欄位用不同類型，圖表會完全不同！
> `year:O`（有序分類）會均勻排列，`year:Q`（數值）會按比例排列。

---

## 1.5 動手做：你的第一批 Altair 圖表

### 實作 1：折線圖

```python
import altair as alt
import pandas as pd

df = pd.DataFrame({
    'year': [2020, 2021, 2022, 2023],
    'sales': [100, 120, 150, 170]
})

chart = alt.Chart(df).mark_line(point=True).encode(
    x='year:O',
    y='sales:Q'
).properties(
    title='年度銷售趨勢',
    width=400,
    height=300
)

chart
```

### 實作 2：長條圖

```python
df = pd.DataFrame({
    'category': ['電子', '服飾', '食品', '家居'],
    'revenue': [450, 300, 550, 250]
})

alt.Chart(df).mark_bar().encode(
    x='category:N',
    y='revenue:Q',
    color='category:N'
).properties(
    title='各品類營收'
)
```

### 實作 3：散佈圖

```python
import numpy as np

np.random.seed(42)
df = pd.DataFrame({
    'height': np.random.normal(170, 10, 100),
    'weight': np.random.normal(65, 15, 100),
    'gender': np.random.choice(['男', '女'], 100)
})

alt.Chart(df).mark_circle(size=60).encode(
    x='height:Q',
    y='weight:Q',
    color='gender:N',
    tooltip=['height:Q', 'weight:Q', 'gender:N']
).properties(
    title='身高體重分佈'
).interactive()
```

> **注意**：`.interactive()` 讓圖表可以縮放和平移！

---

## 1.6 Altair 圖表的三要素

每張 Altair 圖表都由三個核心部分組成：

```
Chart = Data + Mark + Encoding
```

```python
alt.Chart(df)          # 1. Data：資料來源
   .mark_line()        # 2. Mark：視覺標記類型
   .encode(            # 3. Encoding：資料 → 視覺通道的映射
       x='year',
       y='sales'
   )
```

### Mark 類型一覽

| Mark | 方法 | 用途 |
|------|------|------|
| 點 | `mark_point()` | 散佈圖 |
| 圓 | `mark_circle()` | 散佈圖（圓形） |
| 線 | `mark_line()` | 折線圖、趨勢 |
| 長條 | `mark_bar()` | 長條圖 |
| 面積 | `mark_area()` | 面積圖 |
| 矩形 | `mark_rect()` | 熱力圖 |
| 文字 | `mark_text()` | 文字標註 |
| 刻度 | `mark_tick()` | 分佈標記 |
| 規則 | `mark_rule()` | 參考線 |

---

## 1.7 思維對照表

| 面向 | Imperative（matplotlib） | Declarative（Altair） |
|------|-------------------------|---------------------|
| 寫程式時 | 思考步驟順序 | 思考資料結構 |
| 改圖表時 | 找到對應的那行指令 | 改 encoding 映射 |
| 換資料時 | 可能要改很多行 | 通常只改 `alt.Chart(new_df)` |
| 團隊合作 | 「你看第 15 行那個 ax.plot」 | 「x 改用 date 欄位」 |
| Debug 時 | 一步一步 print 確認 | 看 spec 的 JSON |
| 存檔時 | 存 .py 或 .png | 存 .json（規格） |

---

## 1.8 本章作業

### 作業 1：三種基本圖表

使用以下資料，分別做出 **長條圖、折線圖、散佈圖**：

```python
df = pd.DataFrame({
    'month': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
    'temperature': [5, 8, 15, 22, 28, 33],
    'rainfall': [40, 35, 50, 80, 100, 120],
    'humidity': [60, 55, 65, 70, 75, 80]
})
```

要求：
1. 長條圖：月份 vs 降雨量
2. 折線圖：月份 vs 溫度
3. 散佈圖：溫度 vs 濕度，用 rainfall 控制大小

### 作業 2：Encoding 的意義

針對作業 1 的散佈圖，回答：
1. 如果把 `x` 和 `y` 交換，圖表傳達的訊息有什麼不同？
2. 如果把 `size` 改成 `color`，視覺效果有什麼改變？
3. 為什麼 `month` 應該用 `:O` 而不是 `:N`？

### 作業 3：思維比較

用 **matplotlib** 和 **Altair** 各做一張相同的圖表（任選類型），然後比較：
1. 程式碼行數差異
2. 修改圖表類型（例如長條改折線）需要改幾個地方？
3. 哪種方式更容易向同學解釋「這張圖在做什麼」？

---

## 本章小結

```
核心觀念：
┌─────────────────────────────────────────────┐
│  Imperative = 「告訴電腦怎麼畫」              │
│  Declarative = 「描述圖表長什麼樣」            │
│                                             │
│  圖表 = 資料 + 標記 + 編碼                    │
│  Chart = Data + Mark + Encoding              │
│                                             │
│  Encoding 是核心：                            │
│    資料欄位 → 視覺通道（x, y, color, size...）│
└─────────────────────────────────────────────┘
```

> **帶走一句話**：Altair 不是另一個繪圖庫。它代表的是一種思維方式的轉變 —
> 從「命令電腦畫圖」到「描述資料如何成為視覺」。

---

[上一章 ← Chapter 00：matplotlib 與 plotly 簡介](00-matplotlib-plotly-intro.md) ｜ [下一章 → Chapter 02：Altair 入門](02-altair-fundamentals.md)

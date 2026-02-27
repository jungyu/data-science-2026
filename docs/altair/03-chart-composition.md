# Chapter 03：圖表組合與視覺思考

> 第 2 週 — 現代視覺化不是單一圖，而是組合式

---

## 本章目標

- 掌握 Layer（疊加）、Concat（並排）、Facet（分面）三種組合方式
- 學會使用 Selection（選取）建立互動式圖表
- 設計多圖聯動的儀表板
- 理解「視覺思考」的設計原則

---

## 3.1 為什麼需要圖表組合？

單一圖表能回答一個問題。但現實世界的問題通常需要 **多個視角**：

> 「公司第三季表現如何？」

這個問題需要：
- 營收趨勢（折線圖）
- 各部門佔比（長條圖）
- 關鍵指標（數字卡片）
- 異常偵測（散佈圖 + 篩選）

Altair 提供三種組合方式，加上 Selection 互動機制，讓你能用一組圖表回答複雜問題。

---

## 3.2 Layer：疊加圖層

**Layer** 是最常用的組合方式——在同一個座標系上疊加多個圖層。

### 基本語法

```python
import altair as alt
import pandas as pd

df = pd.DataFrame({
    'month': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
    'sales': [100, 120, 115, 140, 160, 155]
})

# 折線 + 點
line = alt.Chart(df).mark_line(color='steelblue').encode(
    x='month:N',
    y='sales:Q'
)

points = alt.Chart(df).mark_circle(color='steelblue', size=60).encode(
    x='month:N',
    y='sales:Q'
)

line + points  # 用 + 運算子疊加
```

### 疊加不同資料的圖層

```python
df = pd.DataFrame({
    'month': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
    'sales': [100, 120, 115, 140, 160, 155],
    'target': [110, 110, 130, 130, 150, 150]
})

# 實際銷售折線
actual = alt.Chart(df).mark_line(color='steelblue').encode(
    x='month:N',
    y='sales:Q'
)

# 目標虛線
target = alt.Chart(df).mark_line(
    color='red',
    strokeDash=[5, 5]  # 虛線
).encode(
    x='month:N',
    y='target:Q'
)

# 達標區域
area = alt.Chart(df).mark_area(
    opacity=0.1,
    color='green'
).encode(
    x='month:N',
    y='target:Q'
)

area + actual + target  # 從底層到頂層
```

### 加上參考線

```python
# 平均線
mean_line = alt.Chart(df).mark_rule(
    color='orange',
    strokeDash=[3, 3]
).encode(
    y='mean(sales):Q'
)

line + points + mean_line
```

### 加上文字標註

```python
# 在最高點加標註
max_point = df[df['sales'] == df['sales'].max()]

annotation = alt.Chart(max_point).mark_text(
    align='left',
    dx=10,
    dy=-10,
    fontSize=12,
    color='red'
).encode(
    x='month:N',
    y='sales:Q',
    text=alt.value('最高點！')
)

line + points + annotation
```

### alt.layer() 語法

除了 `+` 運算子，也可以用 `alt.layer()`：

```python
alt.layer(line, points, mean_line).properties(
    title='月銷售額與平均線',
    width=500,
    height=300
)
```

---

## 3.3 Concat：並排圖表

### 水平並排（|）

```python
bar = alt.Chart(df).mark_bar().encode(
    x='month:N',
    y='sales:Q'
).properties(width=250, height=200, title='長條圖')

line = alt.Chart(df).mark_line(point=True).encode(
    x='month:N',
    y='sales:Q'
).properties(width=250, height=200, title='折線圖')

bar | line  # 用 | 運算子水平並排
```

### 垂直排列（&）

```python
bar & line  # 用 & 運算子垂直排列
```

### alt.hconcat() 和 alt.vconcat()

```python
# 水平
alt.hconcat(bar, line).properties(
    title='銷售資料兩種視角'
)

# 垂直
alt.vconcat(bar, line)
```

### 多圖網格

```python
from vega_datasets import data as vega_data
cars = vega_data.cars()

# 做四張圖
chart1 = alt.Chart(cars).mark_circle().encode(
    x='Horsepower:Q', y='Miles_per_Gallon:Q', color='Origin:N'
).properties(width=250, height=200, title='馬力 vs 油耗')

chart2 = alt.Chart(cars).mark_bar().encode(
    x='Origin:N', y='count()'
).properties(width=250, height=200, title='各產地數量')

chart3 = alt.Chart(cars).mark_bar().encode(
    x=alt.X('Horsepower:Q', bin=True), y='count()'
).properties(width=250, height=200, title='馬力分佈')

chart4 = alt.Chart(cars).mark_boxplot().encode(
    x='Origin:N', y='Miles_per_Gallon:Q'
).properties(width=250, height=200, title='油耗箱型圖')

# 2x2 網格
(chart1 | chart2) & (chart3 | chart4)
```

---

## 3.4 Facet：分面

**Facet** 是用一個分類欄位，自動產生多個子圖。

### 基本 Facet

```python
alt.Chart(cars).mark_circle().encode(
    x='Horsepower:Q',
    y='Miles_per_Gallon:Q'
).properties(
    width=200,
    height=200
).facet(
    column='Origin:N'  # 按產地分成多欄
)
```

### Row Facet

```python
alt.Chart(cars).mark_circle().encode(
    x='Horsepower:Q',
    y='Miles_per_Gallon:Q',
    color='Origin:N'
).properties(
    width=400,
    height=150
).facet(
    row='Origin:N'  # 按產地分成多列
)
```

### Encoding 中使用 Facet

```python
alt.Chart(cars).mark_circle().encode(
    x='Horsepower:Q',
    y='Miles_per_Gallon:Q',
    color='Origin:N',
    column='Origin:N'  # 直接寫在 encode 裡
).properties(
    width=200,
    height=200
)
```

### Facet 的威力：Trellis Plot

```python
# 經典 Trellis 圖
alt.Chart(cars).mark_circle(size=40).encode(
    x=alt.X('Horsepower:Q', scale=alt.Scale(zero=False)),
    y=alt.Y('Miles_per_Gallon:Q', scale=alt.Scale(zero=False)),
    color='Cylinders:O'
).properties(
    width=200,
    height=150
).facet(
    column='Origin:N'
)
```

---

## 3.5 Selection：互動的靈魂

Selection 讓使用者可以 **在圖表上選取資料**，並且讓圖表回應選取。

### 單點選取

```python
selection = alt.selection_point()

alt.Chart(cars).mark_circle(size=60).encode(
    x='Horsepower:Q',
    y='Miles_per_Gallon:Q',
    color=alt.condition(
        selection,
        'Origin:N',           # 選中的：顯示顏色
        alt.value('lightgray')  # 未選中的：灰色
    ),
    opacity=alt.condition(
        selection,
        alt.value(1),
        alt.value(0.2)
    )
).add_params(
    selection
).properties(
    title='點擊選取'
)
```

### 區間選取

```python
brush = alt.selection_interval()

alt.Chart(cars).mark_circle(size=60).encode(
    x='Horsepower:Q',
    y='Miles_per_Gallon:Q',
    color=alt.condition(
        brush,
        'Origin:N',
        alt.value('lightgray')
    )
).add_params(
    brush
).properties(
    title='拖曳選取區間'
)
```

### 下拉選單篩選

```python
origin_select = alt.selection_point(
    fields=['Origin'],
    bind=alt.binding_select(
        options=[None, 'USA', 'Europe', 'Japan'],
        labels=['全部', '美國', '歐洲', '日本'],
        name='產地：'
    )
)

alt.Chart(cars).mark_circle(size=60).encode(
    x='Horsepower:Q',
    y='Miles_per_Gallon:Q',
    color='Origin:N'
).add_params(
    origin_select
).transform_filter(
    origin_select
)
```

### 滑桿篩選

```python
hp_slider = alt.selection_point(
    fields=['Horsepower_min'],
    bind=alt.binding_range(min=0, max=250, step=10, name='最低馬力：'),
    value=[{'Horsepower_min': 0}]
)

alt.Chart(cars).mark_circle(size=60).encode(
    x='Horsepower:Q',
    y='Miles_per_Gallon:Q',
    color='Origin:N'
).add_params(
    hp_slider
).transform_filter(
    alt.datum.Horsepower >= hp_slider.Horsepower_min
)
```

---

## 3.6 多圖聯動：Selection 的進階用法

這是 Altair 最強大的功能之一——**一張圖的選取影響另一張圖**。

### 經典範例：Brush + Detail

```python
brush = alt.selection_interval()

# 上方：概覽圖（可選取）
overview = alt.Chart(cars).mark_circle().encode(
    x='Horsepower:Q',
    y='Miles_per_Gallon:Q',
    color=alt.condition(
        brush,
        'Origin:N',
        alt.value('lightgray')
    )
).add_params(
    brush
).properties(
    width=600,
    height=200,
    title='在此拖曳選取'
)

# 下方：選取區域的長條圖
detail = alt.Chart(cars).mark_bar().encode(
    x='Origin:N',
    y='count()',
    color='Origin:N'
).transform_filter(
    brush
).properties(
    width=600,
    height=200,
    title='選取區域的產地分佈'
)

overview & detail
```

### 進階：三圖聯動

```python
brush = alt.selection_interval()

base = alt.Chart(cars).mark_circle(size=50).encode(
    color=alt.condition(
        brush,
        'Origin:N',
        alt.value('lightgray')
    ),
    opacity=alt.condition(
        brush,
        alt.value(0.8),
        alt.value(0.1)
    )
).properties(
    width=250,
    height=250
)

# 三張散佈圖，共享同一個 selection
chart1 = base.encode(
    x='Horsepower:Q',
    y='Miles_per_Gallon:Q'
).add_params(brush)

chart2 = base.encode(
    x='Acceleration:Q',
    y='Miles_per_Gallon:Q'
)

chart3 = base.encode(
    x='Horsepower:Q',
    y='Weight_in_lbs:Q'
)

chart1 | chart2 | chart3
```

在任何一張圖上拖曳選取，其他圖表會同步高亮——這就是 **Linked Views**。

---

## 3.7 實戰：公司年度分析儀表板

讓我們用學到的技巧，做一個完整的儀表板。

```python
import altair as alt
import pandas as pd
import numpy as np

# 模擬資料
np.random.seed(42)
months = pd.date_range('2023-01', periods=12, freq='MS')
departments = ['Engineering', 'Marketing', 'Sales', 'Support']

records = []
for m in months:
    for d in departments:
        base = {'Engineering': 200, 'Marketing': 150, 'Sales': 180, 'Support': 100}[d]
        records.append({
            'month': m,
            'department': d,
            'revenue': base + np.random.randint(-20, 40) + (m.month * 5),
            'headcount': np.random.randint(10, 50)
        })
df = pd.DataFrame(records)

# 共享 selection
dept_select = alt.selection_point(fields=['department'])

# 圖 1：月營收趨勢（折線）
trend = alt.Chart(df).mark_line(point=True).encode(
    x='month:T',
    y='sum(revenue):Q',
    color=alt.condition(
        dept_select,
        'department:N',
        alt.value('lightgray')
    ),
    opacity=alt.condition(
        dept_select,
        alt.value(1),
        alt.value(0.3)
    )
).properties(
    width=500,
    height=250,
    title='月營收趨勢'
)

# 圖 2：各部門總營收（長條）
bar = alt.Chart(df).mark_bar().encode(
    x=alt.X('department:N', sort='-y'),
    y='sum(revenue):Q',
    color=alt.condition(
        dept_select,
        'department:N',
        alt.value('lightgray')
    ),
    opacity=alt.condition(
        dept_select,
        alt.value(1),
        alt.value(0.3)
    )
).add_params(
    dept_select
).properties(
    width=250,
    height=250,
    title='各部門總營收（點擊篩選）'
)

# 圖 3：營收 vs 人數（散佈）
scatter = alt.Chart(df).mark_circle(size=80).encode(
    x='headcount:Q',
    y='revenue:Q',
    color=alt.condition(
        dept_select,
        'department:N',
        alt.value('lightgray')
    ),
    tooltip=['department:N', 'month:T', 'revenue:Q', 'headcount:Q']
).properties(
    width=250,
    height=250,
    title='營收 vs 人力'
)

# 組合
(trend) & (bar | scatter)
```

點擊下方長條圖的某個部門，上方折線圖和右邊散佈圖會同步篩選！

---

## 3.8 視覺思考的設計原則

### 選擇正確的圖表類型

| 你想回答的問題 | 推薦圖表 |
|--------------|---------|
| 數值比較 | 長條圖 |
| 趨勢變化 | 折線圖 |
| 分佈形態 | 直方圖、箱型圖 |
| 相關性 | 散佈圖 |
| 佔比 | 堆疊長條圖（避免圓餅圖） |
| 多維比較 | 分面（Facet） |
| 探索性分析 | 聯動圖（Linked Views） |

### Edward Tufte 的設計原則

1. **Data-Ink Ratio**：最大化「資料墨水」vs「裝飾墨水」的比例
2. **避免 Chartjunk**：移除不必要的裝飾（3D 效果、多餘格線）
3. **Small Multiples**：用小圖陣列比較，而非複雜的單圖

### Altair 的設計優勢

Altair 的宣告式語法天然鼓勵好的設計：
- 你思考的是「資料如何映射」，而非「怎麼畫漂亮」
- Encoding 讓你專注在 **語意** 上
- 預設樣式已經很乾淨，不需要額外清理

---

## 3.9 本章作業

### 作業 1：雙圖聯動

使用 `vega_data.cars()` 資料集，做出兩張聯動圖表：
1. 散佈圖：馬力 vs 油耗
2. 長條圖：選取區域的產地分佈

要求：在散佈圖上拖曳選取，長條圖會更新。

### 作業 2：公司儀表板

模擬或使用真實資料，設計一個包含以下元素的儀表板：
1. 至少 3 張圖表
2. 使用至少 2 種組合方式（Layer、Concat、Facet）
3. 至少一個 Selection 互動

### 作業 3：視覺思考練習

給定以下問題，說明你會選擇什麼圖表類型，為什麼：
1. 「過去一年每月營收的趨勢？」
2. 「五個部門的人力配置比較？」
3. 「廣告支出和營收之間的關係？」
4. 「各地區、各季度的銷售表現？」

---

## 本章小結

```
組合方式：
┌────────────────────────────────────┐
│ Layer（+）：同一座標系疊加多圖層    │
│ Concat（| &）：並排或上下排列       │
│ Facet：按分類欄位自動產生子圖       │
└────────────────────────────────────┘

互動機制：
┌────────────────────────────────────┐
│ selection_point：點擊選取           │
│ selection_interval：拖曳區間選取    │
│ binding_select：下拉選單           │
│ binding_range：滑桿               │
│ Linked Views：多圖共享 selection   │
└────────────────────────────────────┘
```

> **帶走一句話**：現代視覺化的威力不在單一圖表，
> 而在圖表之間的 **組合** 與 **聯動**。

---

[上一章 ← Chapter 02：Altair 深入入門](02-altair-fundamentals.md) ｜ [下一章 → Chapter 04：Vega-Lite 是視覺化 IR](04-vegalite-ir.md)

# Chapter 02：Altair 深入入門

> 第 1-2 週 — 掌握 Altair 的完整基本功

---

## 本章目標

- 熟練使用各種 Mark 類型
- 精通 Encoding 的進階用法
- 學會資料轉換（Transform）
- 掌握圖表客製化（Properties、Config）
- 使用內建資料集進行練習

---

## 2.1 安裝與環境設定

```bash
pip install altair pandas vega_datasets jupyter
```

在 JupyterLab 中，Altair 圖表會自動渲染。在 VS Code 中，需要使用 Jupyter 擴充功能。

```python
import altair as alt
import pandas as pd
from vega_datasets import data as vega_data

# 查看 Altair 版本
print(f"Altair version: {alt.__version__}")
```

### 啟用大資料集支援

Altair 預設限制 5,000 列資料（防止瀏覽器過載）。如果需要更多：

```python
# 方法 1：提高上限
alt.data_transformers.enable('default', max_rows=10000)

# 方法 2：使用 vegafusion（推薦，資料留在 Python 端）
# pip install vegafusion vegafusion-python-embed
# alt.data_transformers.enable('vegafusion')
```

---

## 2.2 Mark 類型完全指南

### 基本 Mark

```python
# 共用資料
df = pd.DataFrame({
    'category': ['A', 'B', 'C', 'D', 'E'],
    'value': [28, 55, 43, 91, 38],
    'group': ['x', 'y', 'x', 'y', 'x']
})
```

#### mark_bar()：長條圖

```python
# 垂直長條圖
alt.Chart(df).mark_bar().encode(
    x='category:N',
    y='value:Q'
)
```

```python
# 水平長條圖（交換 x 和 y）
alt.Chart(df).mark_bar().encode(
    x='value:Q',
    y='category:N'
)
```

```python
# 堆疊長條圖
alt.Chart(df).mark_bar().encode(
    x='category:N',
    y='value:Q',
    color='group:N'
)
```

#### mark_line()：折線圖

```python
df_time = pd.DataFrame({
    'month': pd.date_range('2023-01', periods=12, freq='MS'),
    'revenue': [100, 120, 115, 140, 160, 155, 170, 180, 175, 190, 200, 220],
    'cost': [80, 85, 90, 95, 100, 98, 105, 110, 108, 115, 120, 125]
})

# 基本折線圖
alt.Chart(df_time).mark_line().encode(
    x='month:T',
    y='revenue:Q'
)
```

```python
# 帶點的折線圖
alt.Chart(df_time).mark_line(point=True).encode(
    x='month:T',
    y='revenue:Q'
)
```

```python
# 多條折線（需要 tidy data）
df_long = df_time.melt(
    id_vars='month',
    value_vars=['revenue', 'cost'],
    var_name='type',
    value_name='amount'
)

alt.Chart(df_long).mark_line().encode(
    x='month:T',
    y='amount:Q',
    color='type:N',
    strokeDash='type:N'  # 不同虛線
)
```

#### mark_point() / mark_circle()：散佈圖

```python
# 使用內建資料集
cars = vega_data.cars()

alt.Chart(cars).mark_circle(size=60).encode(
    x='Horsepower:Q',
    y='Miles_per_Gallon:Q',
    color='Origin:N',
    tooltip=['Name:N', 'Horsepower:Q', 'Miles_per_Gallon:Q']
).interactive()
```

#### mark_area()：面積圖

```python
alt.Chart(df_time).mark_area(
    opacity=0.5,
    line=True  # 加上邊線
).encode(
    x='month:T',
    y='revenue:Q'
)
```

### 進階 Mark

#### mark_rect()：熱力圖

```python
# 建立熱力圖資料
import numpy as np

days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']
hours = list(range(9, 18))
records = []
np.random.seed(42)
for d in days:
    for h in hours:
        records.append({'day': d, 'hour': h, 'visitors': np.random.randint(10, 100)})
df_heat = pd.DataFrame(records)

alt.Chart(df_heat).mark_rect().encode(
    x='hour:O',
    y='day:O',
    color='visitors:Q'
).properties(
    title='每日每時段訪客數'
)
```

#### mark_text()：文字標註

```python
# 在長條圖上加數字
bars = alt.Chart(df).mark_bar().encode(
    x='category:N',
    y='value:Q'
)

text = alt.Chart(df).mark_text(
    dy=-10,  # 往上偏移
    fontSize=14
).encode(
    x='category:N',
    y='value:Q',
    text='value:Q'
)

bars + text  # 疊加
```

#### mark_boxplot()：箱型圖

```python
alt.Chart(cars).mark_boxplot(extent='min-max').encode(
    x='Origin:N',
    y='Horsepower:Q'
).properties(
    title='各產地馬力分佈'
)
```

---

## 2.3 Encoding 進階技巧

### 明確指定類型與標題

```python
alt.Chart(df).mark_bar().encode(
    x=alt.X('category:N', title='產品類別'),
    y=alt.Y('value:Q', title='銷售額（萬元）'),
    color=alt.Color('group:N', title='分組')
)
```

### 排序

```python
# 按值排序
alt.Chart(df).mark_bar().encode(
    x=alt.X('category:N', sort='-y'),  # 按 y 值降序
    y='value:Q'
)
```

```python
# 自訂排序
alt.Chart(df).mark_bar().encode(
    x=alt.X('category:N', sort=['E', 'D', 'C', 'B', 'A']),
    y='value:Q'
)
```

### 軸的刻度與格式

```python
alt.Chart(df_time).mark_line().encode(
    x=alt.X('month:T',
            axis=alt.Axis(format='%Y-%m', labelAngle=-45)),
    y=alt.Y('revenue:Q',
            scale=alt.Scale(domain=[0, 250]),  # 固定範圍
            axis=alt.Axis(grid=True))
)
```

### 顏色映射

```python
# 自訂分類顏色
domain = ['A', 'B', 'C', 'D', 'E']
range_ = ['#e41a1c', '#377eb8', '#4daf4a', '#984ea3', '#ff7f00']

alt.Chart(df).mark_bar().encode(
    x='category:N',
    y='value:Q',
    color=alt.Color('category:N',
                     scale=alt.Scale(domain=domain, range=range_),
                     legend=alt.Legend(title='品類'))
)
```

```python
# 連續色彩（數值）
alt.Chart(df).mark_bar().encode(
    x='category:N',
    y='value:Q',
    color=alt.Color('value:Q',
                     scale=alt.Scale(scheme='blues'))
)
```

### Tooltip：互動提示

```python
alt.Chart(cars).mark_circle().encode(
    x='Horsepower:Q',
    y='Miles_per_Gallon:Q',
    color='Origin:N',
    tooltip=[
        alt.Tooltip('Name:N', title='車名'),
        alt.Tooltip('Horsepower:Q', title='馬力'),
        alt.Tooltip('Miles_per_Gallon:Q', title='油耗', format='.1f'),
        alt.Tooltip('Year:T', title='年份')
    ]
).interactive()
```

---

## 2.4 資料轉換（Transform）

Altair 可以在 **spec 內** 進行資料轉換，不需要先在 pandas 處理。

### 聚合（Aggregate）

```python
# 自動聚合：Altair 看到 x 是分類、y 是數值時會自動聚合
alt.Chart(cars).mark_bar().encode(
    x='Origin:N',
    y='average(Horsepower):Q'  # 直接寫聚合函數
)
```

常用聚合函數：
- `count()` — 計數
- `sum(field)` — 加總
- `mean(field)` / `average(field)` — 平均
- `median(field)` — 中位數
- `min(field)` / `max(field)` — 最大最小

### 篩選（Filter）

```python
alt.Chart(cars).mark_circle().encode(
    x='Horsepower:Q',
    y='Miles_per_Gallon:Q',
    color='Origin:N'
).transform_filter(
    alt.datum.Horsepower > 100  # 只保留馬力 > 100
)
```

```python
# 多條件篩選
alt.Chart(cars).mark_circle().encode(
    x='Horsepower:Q',
    y='Miles_per_Gallon:Q'
).transform_filter(
    (alt.datum.Origin == 'USA') & (alt.datum.Horsepower > 100)
)
```

### 計算欄位（Calculate）

```python
alt.Chart(cars).mark_circle().encode(
    x='Horsepower:Q',
    y='kw:Q'
).transform_calculate(
    kw='datum.Horsepower * 0.7457'  # 馬力轉千瓦
)
```

### 分箱（Bin）

```python
alt.Chart(cars).mark_bar().encode(
    x=alt.X('Horsepower:Q', bin=True),  # 自動分箱
    y='count()'
).properties(
    title='馬力分佈直方圖'
)
```

```python
# 自訂分箱
alt.Chart(cars).mark_bar().encode(
    x=alt.X('Horsepower:Q', bin=alt.Bin(maxbins=20)),
    y='count()',
    color='Origin:N'
)
```

---

## 2.5 圖表屬性與樣式

### Properties：基本屬性

```python
alt.Chart(df).mark_bar().encode(
    x='category:N',
    y='value:Q'
).properties(
    title='銷售報表',
    width=500,
    height=300
)
```

### 多行標題與副標題

```python
alt.Chart(df).mark_bar().encode(
    x='category:N',
    y='value:Q'
).properties(
    title=alt.Title(
        text='2023 年各品類銷售額',
        subtitle='資料來源：內部系統',
        anchor='start'
    )
)
```

### Configure：全域樣式

```python
alt.Chart(df).mark_bar().encode(
    x='category:N',
    y='value:Q',
    color='category:N'
).properties(
    title='銷售報表'
).configure_axis(
    labelFontSize=12,
    titleFontSize=14
).configure_title(
    fontSize=18,
    anchor='start'
).configure_legend(
    orient='bottom'
)
```

### 主題（Theme）

```python
# 使用內建主題
alt.themes.enable('fivethirtyeight')

# 其他內建主題：'default', 'opaque', 'dark', 'latimes', 'urbaninstitute'
# 用完記得還原
# alt.themes.enable('default')
```

---

## 2.6 使用內建資料集

`vega_datasets` 提供了大量經典資料集：

```python
from vega_datasets import data as vega_data

# 常用資料集
cars = vega_data.cars()          # 汽車資料
iris = vega_data.iris()          # 鳶尾花
stocks = vega_data.stocks()      # 股票
seattle_weather = vega_data.seattle_weather()  # 天氣
movies = vega_data.movies()      # 電影
```

### 實戰：鳶尾花資料集

```python
iris = vega_data.iris()

alt.Chart(iris).mark_circle(size=60).encode(
    x='petalLength:Q',
    y='petalWidth:Q',
    color='species:N',
    tooltip=['species:N', 'petalLength:Q', 'petalWidth:Q',
             'sepalLength:Q', 'sepalWidth:Q']
).properties(
    title='鳶尾花花瓣尺寸分佈',
    width=500,
    height=400
).interactive()
```

### 實戰：股票走勢

```python
stocks = vega_data.stocks()

alt.Chart(stocks).mark_line().encode(
    x='date:T',
    y='price:Q',
    color='symbol:N',
    strokeDash='symbol:N'
).properties(
    title='科技股價走勢',
    width=600,
    height=350
)
```

---

## 2.7 存檔與匯出

### 存成 JSON（最重要！）

```python
chart = alt.Chart(df).mark_bar().encode(x='category:N', y='value:Q')

# 存成 Vega-Lite spec
chart.save('my_chart.json')

# 或取得 dict
spec = chart.to_dict()
print(spec)
```

### 存成 HTML

```python
chart.save('my_chart.html')
```

### 存成圖片（需要額外套件）

```bash
pip install vl-convert-python
```

```python
chart.save('my_chart.png', scale_factor=2)
chart.save('my_chart.svg')
chart.save('my_chart.pdf')
```

---

## 2.8 常見錯誤與除錯

### 錯誤 1：超過最大列數

```
MaxRowsError: The number of rows in your dataset is greater than the maximum...
```

解法：
```python
alt.data_transformers.enable('default', max_rows=None)
```

### 錯誤 2：型別不正確

```python
# 錯誤：year 被當成數值
alt.Chart(df).mark_bar().encode(x='year', y='sales')

# 正確：明確指定型別
alt.Chart(df).mark_bar().encode(x='year:O', y='sales:Q')
```

### 錯誤 3：資料不是 Tidy 格式

Altair 需要 **Tidy Data**（每列一個觀察值）：

```python
# 不好的格式（寬表）
df_wide = pd.DataFrame({
    'month': ['Jan', 'Feb', 'Mar'],
    'product_A': [100, 120, 130],
    'product_B': [80, 90, 95]
})

# 轉換為 Tidy 格式（長表）
df_tidy = df_wide.melt(
    id_vars='month',
    var_name='product',
    value_name='sales'
)

# 現在可以用了
alt.Chart(df_tidy).mark_line().encode(
    x='month:N',
    y='sales:Q',
    color='product:N'
)
```

---

## 2.9 本章作業

### 作業 1：汽車資料視覺化

使用 `vega_data.cars()` 資料集：

1. 做一張散佈圖：馬力 vs 油耗，用顏色區分產地
2. 做一張長條圖：各產地的平均馬力
3. 做一張直方圖：油耗的分佈

每張圖都要有：適當的標題、Tooltip、型別標註

### 作業 2：Encoding 實驗

使用任意資料集，做出以下實驗並截圖比較：

1. 同一個欄位分別標為 `:Q`、`:O`、`:N`，觀察差異
2. 同一張圖使用 `color` vs `size` 表示第三個變數
3. 使用 `sort='-y'` 和不排序的差異

### 作業 3：Transform 練習

使用 `vega_data.cars()`：

1. 用 `transform_filter` 只顯示 USA 的車
2. 用 `transform_calculate` 新增一個「馬力等級」欄位（>150 為「高」，否則「一般」）
3. 用 `bin` 做一張馬力的直方圖，分 15 個區間

---

## 本章小結

```
本章掌握的技能：
┌──────────────────────────────────────────────────┐
│ Mark 類型：bar, line, point, circle, area,       │
│           rect, text, boxplot                    │
│                                                  │
│ Encoding：x, y, color, size, shape, opacity,     │
│          tooltip, row, column                    │
│                                                  │
│ 型別：Q(uantitative), O(rdinal),                 │
│      N(ominal), T(emporal)                       │
│                                                  │
│ Transform：filter, calculate, bin, aggregate      │
│                                                  │
│ 匯出：.save() → JSON / HTML / PNG / SVG          │
└──────────────────────────────────────────────────┘
```

> **帶走一句話**：Altair 的 API 很小，但組合能力很大。
> 掌握 Mark + Encoding + Transform 三個元件，你就能做出大部分圖表。

---

[上一章 ← Chapter 01：視覺化思維的革命](01-visualization-philosophy.md) ｜ [下一章 → Chapter 03：圖表組合與視覺思考](03-chart-composition.md)

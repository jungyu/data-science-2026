# Chapter 00：matplotlib 與 plotly 簡介

> 在進入 Altair 之前，先認識兩位資料視覺化的「前輩」

---

## 本章目標

- 認識 matplotlib 的設計哲學與基本用法
- 認識 plotly 的互動式特色
- 理解兩者的優勢與限制
- 為「為什麼我們要學 Altair？」做好鋪墊

---

## 0.1 matplotlib — Python 視覺化的始祖

### 什麼是 matplotlib？

matplotlib 是 Python 最老牌、最廣泛使用的繪圖庫。它誕生於 2003 年，由 John Hunter 創建，設計靈感來自 MATLAB 的繪圖系統。

如果你學過任何 Python 資料科學課程，你幾乎一定見過這行程式碼：

```python
import matplotlib.pyplot as plt
```

### 核心哲學：Imperative（指令式）

matplotlib 的哲學是 **「告訴電腦每一步怎麼畫」**：

```python
import matplotlib.pyplot as plt
import numpy as np

# 準備資料
years = [2020, 2021, 2022, 2023]
sales = [100, 120, 150, 170]

# 第一步：建立畫布和軸
fig, ax = plt.subplots(figsize=(8, 5))

# 第二步：畫折線
ax.plot(years, sales, color='steelblue', linewidth=2, marker='o')

# 第三步：加標題
ax.set_title('年度銷售額', fontsize=16)

# 第四步：加軸標籤
ax.set_xlabel('年份', fontsize=12)
ax.set_ylabel('銷售額（萬元）', fontsize=12)

# 第五步：加格線
ax.grid(True, alpha=0.3)

# 第六步：顯示
plt.tight_layout()
plt.show()
```

注意到了嗎？每一行都是一個 **指令**：
- 「建立畫布」
- 「畫一條線」
- 「設定標題」
- 「設定標籤」

你就像一個導演，逐步指揮演員（圖表元素）就位。

### matplotlib 的優勢

| 優勢 | 說明 |
|------|------|
| **極度靈活** | 幾乎能畫出任何圖形，像素級控制 |
| **生態系龐大** | seaborn、mpl_toolkits 等大量擴充 |
| **學術標準** | 論文、報告的事實標準 |
| **輸出多樣** | PNG、SVG、PDF，任你選擇 |
| **社群成熟** | 20 年歷史，遇到問題幾乎都有解答 |

### matplotlib 的限制

| 限制 | 說明 |
|------|------|
| **冗長** | 簡單的圖也需要很多行程式碼 |
| **不互動** | 預設輸出是靜態圖片 |
| **難以復用** | 圖表邏輯和樣式混在一起 |
| **API 不一致** | pyplot vs OOP 兩套 API 容易混淆 |
| **不是結構化的** | 產出是圖片，不是可操作的資料格式 |

### 動手做：你的第一張 matplotlib 圖

```python
import matplotlib.pyplot as plt

# 資料
categories = ['電子', '服飾', '食品', '家居']
values = [45, 30, 55, 25]
colors = ['#4e79a7', '#f28e2b', '#e15759', '#76b7b2']

# 畫長條圖
fig, ax = plt.subplots(figsize=(8, 5))
bars = ax.bar(categories, values, color=colors, edgecolor='white', linewidth=1.5)

# 在長條上標數字
for bar, val in zip(bars, values):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
            str(val), ha='center', va='bottom', fontsize=12)

ax.set_title('各品類銷售額', fontsize=16, fontweight='bold')
ax.set_ylabel('銷售額（萬元）')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
plt.tight_layout()
plt.show()
```

> **思考題**：為了畫一張有數字標籤的長條圖，你寫了多少行「指令」？如果要改成水平長條圖，你需要改幾個地方？

---

## 0.2 plotly — 互動式視覺化的明星

### 什麼是 plotly？

plotly 是一個互動式視覺化庫，產出的圖表可以縮放、滑鼠提示、動態篩選。它在 2012 年由 Plotly Inc. 推出，以 JavaScript 的 D3.js/WebGL 為渲染引擎。

```python
import plotly.express as px
```

### 核心哲學：High-Level Imperative + 互動

plotly（特別是 plotly.express）比 matplotlib 更高階，但本質上仍然是 **「告訴電腦做什麼」**：

```python
import plotly.express as px
import pandas as pd

df = pd.DataFrame({
    'year': [2020, 2021, 2022, 2023],
    'sales': [100, 120, 150, 170]
})

# 一行就能畫圖（但這是因為 plotly.express 幫你封裝了）
fig = px.line(df, x='year', y='sales', title='年度銷售額',
              markers=True)
fig.show()
```

看起來很簡潔？但當你需要客製化時：

```python
import plotly.graph_objects as go

fig = go.Figure()

# 加折線
fig.add_trace(go.Scatter(
    x=[2020, 2021, 2022, 2023],
    y=[100, 120, 150, 170],
    mode='lines+markers',
    name='銷售額',
    line=dict(color='steelblue', width=2),
    marker=dict(size=8)
))

# 加註解
fig.add_annotation(
    x=2023, y=170,
    text="最高點！",
    showarrow=True,
    arrowhead=2
)

# 更新佈局
fig.update_layout(
    title='年度銷售額',
    xaxis_title='年份',
    yaxis_title='銷售額（萬元）',
    template='plotly_white'
)

fig.show()
```

又回到了「一步一步指揮」的模式。

### plotly 的優勢

| 優勢 | 說明 |
|------|------|
| **原生互動** | 縮放、提示、選取，開箱即用 |
| **視覺精緻** | 預設樣式現代美觀 |
| **支援 3D** | 3D 散佈圖、曲面圖 |
| **Dash 整合** | 可建構互動式 Dashboard |
| **多語言** | Python、R、JavaScript 都支援 |

### plotly 的限制

| 限制 | 說明 |
|------|------|
| **體積龐大** | plotly.js 約 3.5MB，載入慢 |
| **兩套 API** | express 簡潔 vs graph_objects 繁瑣 |
| **不是結構驅動** | 圖表邏輯仍然嵌在程式碼中 |
| **Notebook 限定** | 離開 Notebook 需要額外工作 |
| **客製化陡峭** | 超出預設時，API 很深且雜 |

### 動手做：你的第一張 plotly 圖

```python
import plotly.express as px
import pandas as pd

df = pd.DataFrame({
    'category': ['電子', '服飾', '食品', '家居', '電子', '服飾', '食品', '家居'],
    'quarter': ['Q1', 'Q1', 'Q1', 'Q1', 'Q2', 'Q2', 'Q2', 'Q2'],
    'sales': [45, 30, 55, 25, 50, 35, 48, 30]
})

fig = px.bar(df, x='category', y='sales', color='quarter',
             barmode='group', title='各品類季度銷售比較',
             color_discrete_sequence=['#4e79a7', '#f28e2b'])
fig.show()
```

> **思考題**：plotly.express 很簡潔，但如果你想把這張圖「存起來，下次用不同資料重新渲染」，你會怎麼做？

---

## 0.3 三者比較：為什麼我們需要 Altair？

在正式介紹 Altair 之前，讓我們用一張表格比較三者：

| 特性 | matplotlib | plotly | Altair |
|------|-----------|--------|--------|
| **哲學** | 指令式（Imperative） | 高階指令式 | 宣告式（Declarative） |
| **核心動作** | 「畫這條線」 | 「做這張圖」 | 「描述資料如何映射」 |
| **互動性** | 靜態為主 | 原生互動 | 原生互動 |
| **輸出格式** | 圖片（PNG/SVG/PDF） | HTML/圖片 | **JSON Spec** + HTML |
| **可序列化** | 否 | 部分 | **完全可序列化** |
| **AI 可操作** | 困難 | 困難 | **天生支援** |
| **前端渲染** | 不支援 | 需整套 plotly.js | Vega-Lite Runtime |
| **學習曲線** | 陡峭（API 多） | 中等 | 平緩（概念少） |
| **適合場景** | 學術論文、精細控制 | Dashboard、互動展示 | **資料探索、產品化** |

### 同一張圖，三種寫法

**matplotlib：15 行**
```python
fig, ax = plt.subplots()
ax.plot([2020,2021,2022,2023], [100,120,150,170], 'o-')
ax.set_title('Sales')
ax.set_xlabel('Year')
ax.set_ylabel('Sales')
plt.show()
```

**plotly：5 行**
```python
fig = px.line(df, x='year', y='sales', title='Sales', markers=True)
fig.show()
```

**Altair：4 行**
```python
alt.Chart(df).mark_line(point=True).encode(
    x='year',
    y='sales'
)
```

行數差異不大，但 **本質差異巨大**：

- matplotlib 和 plotly 的輸出是 **一張圖**
- Altair 的輸出是 **一份規格（Spec）**

這份規格：
- 可以存入資料庫
- 可以用 API 傳送
- 可以在任何支援 Vega-Lite 的環境渲染
- 可以被 AI 讀取和修改

**這就是為什麼我們要學 Altair。**

---

## 0.4 一個簡單的預告

想像你是一家公司的資料工程師。老闆說：

> 「我想要一個系統：分析師用 Python 做圖表，前端網站能即時顯示，而且 AI 助手能幫忙調整圖表。」

如果你只會 matplotlib：
```
Python → PNG 圖檔 → 手動上傳 → 無法互動 → AI 無法操作
```

如果你學了 Altair + Vega-Lite：
```
Python → Vega-Lite Spec (JSON) → 存入 DB → API 提供 → 前端渲染 → AI 可修改
```

這就是接下來六週要帶你走的路。

---

## 0.5 本章小結

| 工具 | 一句話總結 |
|------|-----------|
| **matplotlib** | Python 視覺化的基石，適合學術和精細控制，但產出是圖片 |
| **plotly** | 互動式視覺化的利器，適合 Dashboard，但邏輯仍在程式碼中 |
| **Altair** | 下一章的主角 — 不是畫圖工具，是視覺化規格的撰寫工具 |

> **記住這個類比**：
> - matplotlib 是「油畫」— 你一筆一筆畫，成品是一幅畫
> - plotly 是「數位繪圖軟體」— 工具更方便，但成品還是一張圖
> - Altair 是「建築藍圖」— 你畫的不是建築物，是建築的規格書

接下來，讓我們正式進入思維革命。

---

## 延伸閱讀

- [matplotlib 官方教學](https://matplotlib.org/stable/tutorials/index.html)
- [plotly Python 官方文件](https://plotly.com/python/)
- [Altair 官方文件](https://altair-viz.github.io/)
- [Vega-Lite 官方範例](https://vega.github.io/vega-lite/examples/)

---

[下一章 → Chapter 01：視覺化思維的革命](01-visualization-philosophy.md)

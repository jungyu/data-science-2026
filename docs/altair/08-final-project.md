# Chapter 08：期末專案與架構總覽

> 整合六週所學，建構一個完整的圖表管理系統

---

## 本章目標

- 整合所有章節的知識
- 完成一個小型圖表管理系統
- 理解完整架構的設計思維
- 反思學到的核心能力

---

## 8.1 專案要求

### 最低要求（及格）

你必須完成一個系統，包含：

| 項目 | 說明 |
|------|------|
| **3 種圖表** | 使用 Altair 產生 bar、line、scatter 各一張 |
| **Spec 存儲** | 將 spec 存入資料庫（Supabase 或本地 DB） |
| **API** | 提供 REST API 取得圖表清單和 spec |
| **前端渲染** | Next.js 頁面渲染 Vega-Lite 圖表 |
| **AI 修改** | 至少能用 AI 修改一張圖表的 spec |

### 進階要求（加分）

| 項目 | 說明 |
|------|------|
| **圖表預覽** | 清單頁顯示圖表縮圖 |
| **修改歷史** | 記錄 AI 修改的歷史，支援回滾 |
| **Schema 驗證** | 在存入前驗證 spec 的正確性 |
| **分類標籤** | 圖表可加標籤並篩選 |
| **圖表組合** | 使用 Layer/Concat/Facet 的複合圖表 |
| **Selection** | 含互動選取功能的圖表 |

---

## 8.2 完整架構

```
┌─────────────────────────────────────────────────────────────┐
│                      Chart Management System                 │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                  Data Layer (Python)                   │   │
│  │                                                       │   │
│  │  pandas → 資料分析                                     │   │
│  │  altair → 圖表建立                                     │   │
│  │  chart.to_dict() → Vega-Lite Spec                     │   │
│  └───────────────────┬──────────────────────────────────┘   │
│                      │                                       │
│                      ▼                                       │
│  ┌──────────────────────────────────────────────────────┐   │
│  │               Storage Layer (Database)                │   │
│  │                                                       │   │
│  │  Supabase / PostgreSQL                                │   │
│  │  chart_specs table (JSONB)                            │   │
│  │  chart_versions table (歷史)                           │   │
│  └───────────────────┬──────────────────────────────────┘   │
│                      │                                       │
│                      ▼                                       │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                  API Layer                            │   │
│  │                                                       │   │
│  │  GET  /api/charts          → 圖表清單                  │   │
│  │  GET  /api/charts/:id      → 圖表詳情                  │   │
│  │  POST /api/charts          → 建立圖表                  │   │
│  │  PUT  /api/charts/:id/spec → 更新 spec                │   │
│  │  POST /api/charts/:id/ai   → AI 修改                  │   │
│  └───────────────────┬──────────────────────────────────┘   │
│                      │                                       │
│                      ▼                                       │
│  ┌──────────────────────────────────────────────────────┐   │
│  │               Render Layer (Next.js)                   │   │
│  │                                                       │   │
│  │  /              → 圖表清單頁                           │   │
│  │  /charts/:id    → 圖表詳情 + 渲染                      │   │
│  │  /charts/:id/ai → AI 修改介面                          │   │
│  │                                                       │   │
│  │  VegaChart Component → vega-embed → SVG               │   │
│  └───────────────────┬──────────────────────────────────┘   │
│                      │                                       │
│                      ▼                                       │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                 AI Layer (Claude)                      │   │
│  │                                                       │   │
│  │  讀取 spec → 理解結構 → 修改 JSON → 回傳修改後 spec    │   │
│  │  Schema 驗證 → 安全檢查 → 存入資料庫                   │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 8.3 專案實作步驟

### Step 1：Python 端 — 建立圖表

```python
# create_charts.py
import altair as alt
import pandas as pd
import json
from supabase import create_client

# 連接 Supabase
supabase = create_client(
    "https://your-project.supabase.co",
    "your-anon-key"
)

# ─── 圖表 1：銷售趨勢折線圖 ───
df_sales = pd.DataFrame({
    'month': pd.date_range('2023-01', periods=12, freq='MS'),
    'revenue': [100, 120, 115, 140, 160, 155, 170, 180, 175, 190, 200, 220],
    'cost': [80, 85, 90, 95, 100, 98, 105, 110, 108, 115, 120, 125]
})

df_long = df_sales.melt(
    id_vars='month', var_name='type', value_name='amount'
)

chart1 = alt.Chart(df_long).mark_line(point=True).encode(
    x=alt.X('month:T', title='月份'),
    y=alt.Y('amount:Q', title='金額（萬元）'),
    color=alt.Color('type:N', title='類型'),
    tooltip=['month:T', 'type:N', 'amount:Q']
).properties(
    title='2023 年營收與成本趨勢',
    width=600,
    height=350
)

# ─── 圖表 2：品類營收長條圖 ───
df_category = pd.DataFrame({
    'category': ['Electronics', 'Clothing', 'Food', 'Home', 'Sports'],
    'revenue': [450, 300, 550, 250, 180],
    'growth': [12, -5, 8, 15, 22]
})

chart2 = alt.Chart(df_category).mark_bar().encode(
    x=alt.X('category:N', sort='-y', title='品類'),
    y=alt.Y('revenue:Q', title='營收（萬元）'),
    color=alt.Color('category:N', legend=None),
    tooltip=['category:N', 'revenue:Q', 'growth:Q']
).properties(
    title='各品類營收排行',
    width=500,
    height=350
)

# ─── 圖表 3：營收 vs 成長率散佈圖 ───
chart3 = alt.Chart(df_category).mark_circle(size=100).encode(
    x=alt.X('revenue:Q', title='營收（萬元）'),
    y=alt.Y('growth:Q', title='成長率（%）'),
    color='category:N',
    size=alt.Size('revenue:Q', legend=None),
    tooltip=['category:N', 'revenue:Q', 'growth:Q']
).properties(
    title='營收 vs 成長率',
    width=500,
    height=400
).interactive()

# ─── 存入資料庫 ───
charts = [
    ('monthly_trend', '2023 年月營收與成本趨勢折線圖', chart1),
    ('category_revenue', '各品類營收排行長條圖', chart2),
    ('revenue_growth_scatter', '營收與成長率關係散佈圖', chart3)
]

for name, desc, chart in charts:
    spec = chart.to_dict()
    result = supabase.table('chart_specs').insert({
        'name': name,
        'description': desc,
        'spec': spec
    }).execute()
    print(f"✅ {name} 已存入，ID: {result.data[0]['id']}")
```

### Step 2：Next.js 前端

（參考 Chapter 06 的完整程式碼）

### Step 3：AI 修改功能

（參考 Chapter 07 的完整程式碼）

---

## 8.4 繳交清單

| # | 項目 | 檔案 / 連結 |
|---|------|------------|
| 1 | Python 建表與存入程式碼 | `create_charts.py` |
| 2 | 資料庫截圖（3 筆 spec） | 截圖 |
| 3 | API 測試截圖 | GET /api/charts 的回傳 |
| 4 | Next.js 圖表清單頁截圖 | 截圖 |
| 5 | 圖表渲染頁截圖（3 張圖） | 截圖 |
| 6 | AI 修改前後對比 | 修改前 spec + 修改後 spec |
| 7 | 架構圖 | 手繪或文字描述 |
| 8 | 心得報告 | 回答下方的反思問題 |

---

## 8.5 反思問題

### 問題 1：Declarative 思維

> 學了 Altair 之後，你對「視覺化」的理解有什麼改變？
> 如果要向只會 matplotlib 的同學解釋「為什麼要學 Altair」，你會怎麼說？

### 問題 2：IR 的價值

> 在這個專案中，Vega-Lite Spec（JSON）扮演了什麼角色？
> 如果沒有這份 JSON（直接用 Python 產生圖片），整個系統會有什麼不同？

### 問題 3：AI 可操作性

> 「AI 修改 JSON」和「AI 寫 Python 畫圖」有什麼本質差異？
> 哪種方式更安全？更可控？為什麼？

### 問題 4：未來展望

> 如果你的系統要上線給 100 人使用，你需要加什麼功能？
> 如果 5 年後要換前端圖表引擎（Vega → ECharts），你的架構能承受嗎？

---

## 8.6 進階挑戰（選做）

### 挑戰 1：ChartSpec Versioning

設計一個版本控管系統：
- 每次修改自動產生新版本
- 可以查看版本歷史
- 可以回滾到任意版本
- 可以比較兩個版本的差異

### 挑戰 2：AI 安全護欄

實作完整的 spec 驗證系統：
- JSON Schema 驗證
- 欄位白名單
- 誤導性圖表檢測
- 異常 spec 告警

### 挑戰 3：即時協作

使用 Supabase 的 Realtime 功能：
- 多人同時查看圖表
- 一人 AI 修改，其他人即時看到更新

### 挑戰 4：圖表推薦

根據資料集的特性，自動推薦適合的圖表類型：
- 兩個數值欄位 → 散佈圖
- 一個分類 + 一個數值 → 長條圖
- 時間序列 → 折線圖

---

## 8.7 本課程的核心價值回顧

### 你學會了什麼？

| 週次 | 技能 | 深層能力 |
|------|------|---------|
| 第 1 週 | Imperative vs Declarative | **思維方式的轉變** |
| 第 2 週 | Altair 基本功 + 圖表組合 | **Grammar of Graphics** |
| 第 3 週 | Vega-Lite JSON Spec | **IR 設計思維** |
| 第 4 週 | Database + API | **前後端解耦** |
| 第 5 週 | Next.js 渲染 | **全端整合** |
| 第 6 週 | AI 修改 Spec | **AI 可操作系統設計** |

### 這不只是三件事

```
┌──────────────────────────────────────────────────────────┐
│                                                          │
│  1. Declarative Thinking                                 │
│     從「怎麼做」到「做什麼」                              │
│     這不只適用於視覺化，適用於所有軟體設計                │
│                                                          │
│  2. IR Architecture                                      │
│     中介表示讓系統各層解耦                                │
│     這是編譯器、資料庫、網頁瀏覽器的共同設計模式          │
│                                                          │
│  3. AI-Operable System Design                            │
│     讓 AI 操作結構化資料，而非自由生成                    │
│     這是 AI 時代系統設計的關鍵思維                        │
│                                                          │
│  這三個能力，讓你比只會用 matplotlib 畫圖的人，            │
│  高一個維度。                                             │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

## 8.8 延伸學習資源

### Altair & Vega-Lite

- [Altair 官方文件](https://altair-viz.github.io/)
- [Vega-Lite 官方文件](https://vega.github.io/vega-lite/)
- [Vega-Lite 範例庫](https://vega.github.io/vega-lite/examples/)
- [Vega 線上編輯器](https://vega.github.io/editor/)

### 資料視覺化理論

- Edward Tufte, *The Visual Display of Quantitative Information*
- Leland Wilkinson, *The Grammar of Graphics*
- Tamara Munzner, *Visualization Analysis and Design*

### 技術棧

- [Next.js 官方文件](https://nextjs.org/docs)
- [Supabase 官方文件](https://supabase.com/docs)
- [FastAPI 官方文件](https://fastapi.tiangolo.com/)

### AI 整合

- [Claude API 文件](https://docs.anthropic.com/)
- [JSON Patch RFC 6902](https://datatracker.ietf.org/doc/html/rfc6902)

---

[上一章 ← Chapter 07：AI 修改圖表規格](07-ai-spec-modification.md) ｜ [附錄 → Appendix A：測驗題庫](appendix-a-test-bank.md)

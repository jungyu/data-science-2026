# Chapter 05：Spec 存儲與 API 化

> 第 4 週 — 圖表不再只存在 Notebook 裡，開始「專案化」

---

## 本章目標

- 將 Vega-Lite Spec 存入資料庫（Supabase / PostgreSQL）
- 建立 API 來提供 Spec
- 理解前後端解耦的架構
- 設計圖表管理的資料模型

---

## 5.1 為什麼要把 Spec 存入資料庫？

到第 3 週為止，你的圖表都活在 Jupyter Notebook 裡。這有幾個問題：

| 問題 | 說明 |
|------|------|
| **無法共享** | 別人要看你的圖，必須跑你的 Notebook |
| **無法嵌入** | 網站或 App 無法直接使用 Notebook 的圖 |
| **無法管理** | 100 張圖散落在不同 .ipynb 中 |
| **無法版本化** | 圖表的修改歷史無從追蹤 |
| **無法被 AI 操作** | AI 需要一個 API 來讀取和修改圖表 |

解決方案：

```
Notebook（產生 Spec）→ Database（存儲）→ API（提供）→ 前端（渲染）
```

---

## 5.2 架構設計

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Python     │     │  Database   │     │    API      │     │  Frontend   │
│   Altair     │────▶│  Supabase   │────▶│  FastAPI /  │────▶│  Next.js    │
│   Notebook   │     │  PostgreSQL │     │  Supabase   │     │  React      │
│              │     │             │     │  REST       │     │             │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
   產生 Spec           存儲 Spec          提供 Spec          渲染 Spec
```

---

## 5.3 資料模型設計

### 基本版：chart_specs 表

```sql
CREATE TABLE chart_specs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  description text,
  spec jsonb NOT NULL,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now()
);

-- 建立索引加速查詢
CREATE INDEX idx_chart_specs_name ON chart_specs(name);
CREATE INDEX idx_chart_specs_created ON chart_specs(created_at DESC);
```

### 進階版：加上分類與版本

```sql
-- 圖表主表
CREATE TABLE charts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  description text,
  tags text[] DEFAULT '{}',
  current_version integer DEFAULT 1,
  created_at timestamp with time zone DEFAULT now(),
  updated_at timestamp with time zone DEFAULT now()
);

-- 圖表版本歷史
CREATE TABLE chart_versions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  chart_id uuid REFERENCES charts(id) ON DELETE CASCADE,
  version integer NOT NULL,
  spec jsonb NOT NULL,
  change_note text,
  created_at timestamp with time zone DEFAULT now(),
  UNIQUE(chart_id, version)
);

-- 建立索引
CREATE INDEX idx_charts_tags ON charts USING gin(tags);
CREATE INDEX idx_chart_versions_chart ON chart_versions(chart_id, version DESC);
```

### 為什麼用 JSONB？

PostgreSQL 的 `jsonb` 類型是存儲 Vega-Lite Spec 的理想選擇：

| 特性 | 說明 |
|------|------|
| **二進位儲存** | 查詢效能比 json 更好 |
| **支援索引** | 可以對 JSON 內部欄位建索引 |
| **支援查詢** | 可以用 SQL 查詢 JSON 內容 |
| **支援修改** | 可以用 SQL 修改 JSON 中的特定欄位 |

```sql
-- 查詢所有長條圖
SELECT name, spec
FROM chart_specs
WHERE spec->>'mark' = 'bar';

-- 查詢使用特定欄位的圖表
SELECT name
FROM chart_specs
WHERE spec->'encoding'->'x'->>'field' = 'year';

-- 修改圖表類型
UPDATE chart_specs
SET spec = jsonb_set(spec, '{mark}', '"line"')
WHERE name = 'sales_chart';
```

---

## 5.4 使用 Supabase

### 什麼是 Supabase？

Supabase 是開源的 Firebase 替代品，提供：
- PostgreSQL 資料庫
- 自動產生 REST API
- 即時訂閱
- 身份驗證
- 檔案儲存

對本課程來說，Supabase 的好處是 **不需要寫後端 API**——它會自動為你的資料表產生 REST 端點。

### 設定 Supabase

1. 前往 https://supabase.com 建立帳號和專案
2. 在 SQL Editor 中建立資料表（使用上面的 SQL）
3. 取得 API URL 和 Key

### Python 端：存入 Spec

```bash
pip install supabase
```

```python
import json
import altair as alt
import pandas as pd
from supabase import create_client

# 設定 Supabase
SUPABASE_URL = "https://your-project.supabase.co"
SUPABASE_KEY = "your-anon-key"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# 建立 Altair 圖表
df = pd.DataFrame({
    'year': [2020, 2021, 2022, 2023],
    'sales': [100, 120, 150, 170]
})

chart = alt.Chart(df).mark_line(point=True).encode(
    x='year:O',
    y='sales:Q'
).properties(title='年度銷售趨勢')

# 取得 spec
spec = chart.to_dict()

# 存入 Supabase
result = supabase.table('chart_specs').insert({
    'name': 'annual_sales',
    'description': '2020-2023 年度銷售趨勢折線圖',
    'spec': spec
}).execute()

print(f"存入成功，ID: {result.data[0]['id']}")
```

### Python 端：批次存入多個 Spec

```python
def save_chart(name, description, chart):
    """將 Altair 圖表存入 Supabase"""
    spec = chart.to_dict()
    result = supabase.table('chart_specs').insert({
        'name': name,
        'description': description,
        'spec': spec
    }).execute()
    return result.data[0]['id']

# 建立多個圖表
df = pd.DataFrame({
    'category': ['Electronics', 'Clothing', 'Food', 'Home'],
    'revenue': [450, 300, 550, 250],
    'growth': [12, -5, 8, 15]
})

# 圖表 1：營收長條圖
chart1 = alt.Chart(df).mark_bar().encode(
    x=alt.X('category:N', sort='-y'),
    y='revenue:Q',
    color='category:N'
).properties(title='各品類營收')

# 圖表 2：成長率長條圖
chart2 = alt.Chart(df).mark_bar().encode(
    x='category:N',
    y='growth:Q',
    color=alt.condition(
        alt.datum.growth > 0,
        alt.value('steelblue'),
        alt.value('coral')
    )
).properties(title='各品類成長率')

# 圖表 3：營收散佈圖
chart3 = alt.Chart(df).mark_circle(size=100).encode(
    x='revenue:Q',
    y='growth:Q',
    color='category:N',
    tooltip=['category:N', 'revenue:Q', 'growth:Q']
).properties(title='營收 vs 成長率')

# 批次存入
for name, desc, chart in [
    ('category_revenue', '各品類營收長條圖', chart1),
    ('category_growth', '各品類成長率', chart2),
    ('revenue_vs_growth', '營收與成長率關係', chart3)
]:
    chart_id = save_chart(name, desc, chart)
    print(f"已存入 {name}，ID: {chart_id}")
```

### 查詢 Spec

```python
# 取得所有圖表
result = supabase.table('chart_specs').select('*').execute()
for chart in result.data:
    print(f"- {chart['name']}: {chart['description']}")

# 取得特定圖表
result = supabase.table('chart_specs') \
    .select('*') \
    .eq('name', 'annual_sales') \
    .execute()

spec = result.data[0]['spec']

# 直接渲染
alt.Chart.from_dict(spec)
```

---

## 5.5 使用 FastAPI（替代方案）

如果不用 Supabase 的自動 API，可以用 FastAPI 自建：

```bash
pip install fastapi uvicorn asyncpg databases
```

```python
# api.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import json
import uuid
from datetime import datetime

app = FastAPI(title="Chart Spec API")

# CORS 設定（讓前端可以呼叫）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Next.js dev server
    allow_methods=["*"],
    allow_headers=["*"],
)

# 簡化版：用記憶體存儲（實際專案用資料庫）
chart_store = {}

class ChartCreate(BaseModel):
    name: str
    description: Optional[str] = None
    spec: dict

class ChartResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    spec: dict
    created_at: str

# 建立圖表
@app.post("/api/charts", response_model=ChartResponse)
def create_chart(chart: ChartCreate):
    chart_id = str(uuid.uuid4())
    record = {
        "id": chart_id,
        "name": chart.name,
        "description": chart.description,
        "spec": chart.spec,
        "created_at": datetime.now().isoformat()
    }
    chart_store[chart_id] = record
    return record

# 取得所有圖表（清單）
@app.get("/api/charts")
def list_charts():
    return list(chart_store.values())

# 取得單一圖表
@app.get("/api/charts/{chart_id}", response_model=ChartResponse)
def get_chart(chart_id: str):
    if chart_id not in chart_store:
        raise HTTPException(status_code=404, detail="Chart not found")
    return chart_store[chart_id]

# 取得圖表的 spec（純 JSON）
@app.get("/api/charts/{chart_id}/spec")
def get_chart_spec(chart_id: str):
    if chart_id not in chart_store:
        raise HTTPException(status_code=404, detail="Chart not found")
    return chart_store[chart_id]["spec"]

# 更新圖表 spec
@app.put("/api/charts/{chart_id}/spec")
def update_chart_spec(chart_id: str, spec: dict):
    if chart_id not in chart_store:
        raise HTTPException(status_code=404, detail="Chart not found")
    chart_store[chart_id]["spec"] = spec
    return {"message": "Spec updated", "id": chart_id}

# 刪除圖表
@app.delete("/api/charts/{chart_id}")
def delete_chart(chart_id: str):
    if chart_id not in chart_store:
        raise HTTPException(status_code=404, detail="Chart not found")
    del chart_store[chart_id]
    return {"message": "Chart deleted"}
```

啟動：

```bash
uvicorn api:app --reload --port 8000
```

### 測試 API

```python
import requests

BASE_URL = "http://localhost:8000/api"

# 建立圖表
spec = {
    "mark": "bar",
    "encoding": {
        "x": {"field": "category", "type": "nominal"},
        "y": {"field": "value", "type": "quantitative"}
    },
    "data": {
        "values": [
            {"category": "A", "value": 28},
            {"category": "B", "value": 55}
        ]
    }
}

response = requests.post(f"{BASE_URL}/charts", json={
    "name": "test_chart",
    "description": "測試圖表",
    "spec": spec
})
chart_id = response.json()["id"]
print(f"建立成功：{chart_id}")

# 取得清單
response = requests.get(f"{BASE_URL}/charts")
print(f"共有 {len(response.json())} 個圖表")

# 取得 spec
response = requests.get(f"{BASE_URL}/charts/{chart_id}/spec")
print(json.dumps(response.json(), indent=2))
```

---

## 5.6 API 設計考量

### RESTful 端點設計

| 方法 | 路徑 | 說明 |
|------|------|------|
| `GET` | `/api/charts` | 取得所有圖表清單 |
| `POST` | `/api/charts` | 建立新圖表 |
| `GET` | `/api/charts/:id` | 取得特定圖表 |
| `GET` | `/api/charts/:id/spec` | 取得圖表的 spec |
| `PUT` | `/api/charts/:id/spec` | 更新圖表 spec |
| `DELETE` | `/api/charts/:id` | 刪除圖表 |

### API 回傳格式

```json
// GET /api/charts
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "annual_sales",
    "description": "年度銷售趨勢",
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
  }
]

// GET /api/charts/:id/spec
{
  "mark": "line",
  "encoding": {
    "x": {"field": "year", "type": "ordinal"},
    "y": {"field": "sales", "type": "quantitative"}
  },
  "data": {
    "values": [...]
  }
}
```

### 資料與 Spec 分離

在進階架構中，你可能想把 **資料** 和 **圖表規格** 分開存：

```json
// chart spec（不含資料）
{
  "mark": "line",
  "encoding": {
    "x": {"field": "year", "type": "ordinal"},
    "y": {"field": "sales", "type": "quantitative"}
  }
}

// 資料由另一個 API 提供
// GET /api/datasets/sales_2023
{
  "values": [
    {"year": 2020, "sales": 100},
    {"year": 2021, "sales": 120}
  ]
}
```

前端組合：
```javascript
const spec = await fetch('/api/charts/123/spec').then(r => r.json());
const data = await fetch('/api/datasets/sales_2023').then(r => r.json());

// 組合
spec.data = data;
// 渲染
```

這樣同一份 Spec 可以搭配不同資料重複使用。

---

## 5.7 整體流程示意

```
┌──────────────────────────────────────────────────────────┐
│                     完整資料流                            │
│                                                          │
│  1. 資料分析師用 Python + Altair 做圖表                   │
│     chart = alt.Chart(df).mark_bar().encode(...)         │
│                                                          │
│  2. 匯出 Vega-Lite Spec                                  │
│     spec = chart.to_dict()                               │
│                                                          │
│  3. 存入資料庫                                            │
│     supabase.table('chart_specs').insert({spec: spec})   │
│                                                          │
│  4. 前端透過 API 取得 Spec                                │
│     fetch('/api/charts/123/spec')                        │
│                                                          │
│  5. 前端用 Vega Runtime 渲染                              │
│     <VegaLite spec={spec} />                             │
│                                                          │
│  6. AI 透過 API 修改 Spec                                 │
│     PUT /api/charts/123/spec  { modified spec }          │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

---

## 5.8 本章作業

### 作業 1：建立資料表

在 Supabase（或本地 PostgreSQL）中建立 `chart_specs` 表。

### 作業 2：存入 3 個圖表

使用 Python 建立 3 個不同類型的圖表（bar、line、scatter），並將它們的 spec 存入資料庫。

### 作業 3：API 回傳

建立一個 API 端點（Supabase REST API 或 FastAPI），能夠：
1. 列出所有圖表
2. 取得單一圖表的 spec
3. 確認用 `alt.Chart.from_dict(spec)` 能正確渲染

---

## 本章小結

```
本章學會的技能：
┌──────────────────────────────────────────────┐
│ 資料模型：chart_specs 表 + JSONB 存儲         │
│                                              │
│ Python → Database：                           │
│   chart.to_dict() → supabase.insert()        │
│                                              │
│ Database → API：                              │
│   Supabase 自動 REST API                      │
│   或 FastAPI 自建                             │
│                                              │
│ API 端點：                                    │
│   GET  /api/charts          → 清單            │
│   GET  /api/charts/:id/spec → 取得 spec       │
│   POST /api/charts          → 建立            │
│   PUT  /api/charts/:id/spec → 更新 spec       │
│                                              │
│ 架構：                                        │
│   前後端解耦 → Spec 是橋樑                     │
└──────────────────────────────────────────────┘
```

> **帶走一句話**：當 Spec 離開了 Notebook，進入了 Database + API，
> 你的視覺化就從「個人工具」升級成了「可共享的服務」。

---

[上一章 ← Chapter 04：Vega-Lite 是視覺化 IR](04-vegalite-ir.md) ｜ [下一章 → Chapter 06：Next.js 渲染圖表](06-nextjs-rendering.md)

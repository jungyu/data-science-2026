# Chapter 04：Vega-Lite 是視覺化 IR

> 第 3 週 — 打開黑盒子：圖表其實是一份 JSON 規格

---

## 本章目標

- 理解什麼是 IR（Intermediate Representation，中介表示）
- 能讀懂 Vega-Lite JSON Spec 的每個欄位
- 能手動修改 Spec 並重新渲染
- 理解為什麼 Spec 驅動的架構如此重要

---

## 4.1 打開黑盒子

到目前為止，你用 Altair 寫圖表，圖表就神奇地出現了。但背後發生了什麼？

```python
import altair as alt
import pandas as pd

df = pd.DataFrame({
    'year': [2020, 2021, 2022, 2023],
    'sales': [100, 120, 150, 170]
})

chart = alt.Chart(df).mark_line().encode(
    x='year:O',
    y='sales:Q'
)

# 打開黑盒子
print(chart.to_dict())
```

輸出：

```json
{
  "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
  "data": {
    "values": [
      {"year": 2020, "sales": 100},
      {"year": 2021, "sales": 120},
      {"year": 2022, "sales": 150},
      {"year": 2023, "sales": 170}
    ]
  },
  "mark": "line",
  "encoding": {
    "x": {"field": "year", "type": "ordinal"},
    "y": {"field": "sales", "type": "quantitative"}
  }
}
```

**就是這樣。** 你的圖表不是一張圖片，不是一段程式碼，而是一份 **JSON 規格文件**。

---

## 4.2 什麼是 IR？

### 編譯器的類比

在程式語言的世界中，IR（Intermediate Representation）是一個核心概念：

```
高階語言 (C/Python)        ← 人類撰寫
        ↓ 編譯/轉換
IR (中介表示)               ← 可分析、可優化、可轉換
        ↓ 編譯/執行
機器碼 / 執行結果           ← 機器執行
```

例如：
- **LLVM IR**：C/C++/Rust 都編譯成 LLVM IR，再由後端產生不同平台的機器碼
- **HTML**：瀏覽器的 IR，描述文件結構，由渲染引擎呈現
- **SQL**：資料庫的 IR，描述你要什麼資料，由查詢引擎執行

### Vega-Lite 就是視覺化的 IR

```
Altair (Python)             ← 人類撰寫（高階語言）
        ↓ .to_dict()
Vega-Lite Spec (JSON)       ← 視覺化 IR
        ↓ Vega Runtime
瀏覽器中的圖表              ← 渲染結果
```

Vega-Lite Spec 和 LLVM IR 一樣：
- **語言無關**：不只 Python，任何語言都能產生 Vega-Lite JSON
- **平台無關**：瀏覽器、Node.js、甚至命令列都能渲染
- **可分析**：可以用程式讀取、驗證、比較
- **可轉換**：可以修改、合併、版本控管

### 為什麼 IR 這麼重要？

因為 IR 具備五個關鍵特性：

| 特性 | 說明 | 圖片做不到 |
|------|------|-----------|
| **可存檔** | 存成 JSON 文件 | PNG 也可以存，但失去結構 |
| **可 Diff** | 用 git diff 比較版本差異 | PNG diff 只是像素比對 |
| **可驗證** | 用 JSON Schema 驗證正確性 | 圖片無法驗證 |
| **可版本控管** | git 追蹤每次修改 | 二進位檔無法有效追蹤 |
| **可由 AI 修改** | AI 讀取和修改 JSON | AI 無法修改 PNG |

---

## 4.3 Vega-Lite Spec 解剖

### 頂層結構

```json
{
  "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
  "data": { ... },
  "mark": "...",
  "encoding": { ... },
  "transform": [ ... ],
  "config": { ... },
  "title": "...",
  "width": 400,
  "height": 300
}
```

| 欄位 | 必要 | 說明 |
|------|------|------|
| `$schema` | 推薦 | 指定 Vega-Lite 版本 |
| `data` | 是 | 資料來源 |
| `mark` | 是 | 圖表類型 |
| `encoding` | 是 | 視覺映射 |
| `transform` | 否 | 資料轉換 |
| `config` | 否 | 全域樣式設定 |
| `title` | 否 | 圖表標題 |
| `width/height` | 否 | 圖表尺寸 |

### data：資料來源

```json
// 方式 1：內嵌資料（values）
"data": {
  "values": [
    {"year": 2020, "sales": 100},
    {"year": 2021, "sales": 120}
  ]
}

// 方式 2：URL 引用
"data": {
  "url": "https://example.com/data.csv",
  "format": {"type": "csv"}
}

// 方式 3：命名資料集（搭配前端使用）
"data": {"name": "myDataset"}
```

### mark：圖表類型

```json
// 簡寫
"mark": "line"

// 完整寫法（帶參數）
"mark": {
  "type": "line",
  "point": true,
  "color": "steelblue",
  "strokeWidth": 2
}
```

常見 mark 值：`bar`、`line`、`point`、`circle`、`area`、`rect`、`text`、`tick`、`rule`、`boxplot`

### encoding：視覺映射

這是 Spec 的核心。每個通道（channel）包含：

```json
"encoding": {
  "x": {
    "field": "year",       // 資料欄位
    "type": "ordinal",     // 資料類型
    "title": "年份",       // 軸標題
    "axis": {              // 軸設定
      "labelAngle": -45,
      "grid": true
    },
    "sort": "-y",          // 排序
    "scale": {             // 尺度設定
      "domain": [2019, 2024]
    }
  },
  "y": {
    "field": "sales",
    "type": "quantitative",
    "title": "銷售額"
  },
  "color": {
    "field": "category",
    "type": "nominal",
    "legend": {
      "title": "類別",
      "orient": "bottom"
    }
  },
  "tooltip": [
    {"field": "year", "type": "ordinal"},
    {"field": "sales", "type": "quantitative", "format": ",.0f"}
  ]
}
```

### transform：資料轉換

```json
"transform": [
  // 篩選
  {"filter": "datum.sales > 100"},

  // 計算欄位
  {"calculate": "datum.sales * 1.1", "as": "projected"},

  // 聚合
  {
    "aggregate": [
      {"op": "mean", "field": "sales", "as": "avg_sales"}
    ],
    "groupby": ["category"]
  },

  // 分箱
  {
    "bin": true,
    "field": "sales",
    "as": "sales_bin"
  }
]
```

### config：全域樣式

```json
"config": {
  "axis": {
    "labelFontSize": 12,
    "titleFontSize": 14
  },
  "title": {
    "fontSize": 18,
    "anchor": "start"
  },
  "bar": {
    "color": "steelblue"
  },
  "view": {
    "stroke": null
  }
}
```

---

## 4.4 複合圖表的 Spec

### Layer Spec

```json
{
  "data": { "values": [...] },
  "layer": [
    {
      "mark": "line",
      "encoding": {
        "x": {"field": "month", "type": "ordinal"},
        "y": {"field": "sales", "type": "quantitative"}
      }
    },
    {
      "mark": "point",
      "encoding": {
        "x": {"field": "month", "type": "ordinal"},
        "y": {"field": "sales", "type": "quantitative"}
      }
    }
  ]
}
```

### Concat Spec

```json
{
  "hconcat": [
    {
      "mark": "bar",
      "encoding": { ... }
    },
    {
      "mark": "line",
      "encoding": { ... }
    }
  ]
}
```

### Facet Spec

```json
{
  "data": { "values": [...] },
  "facet": {
    "column": {"field": "Origin", "type": "nominal"}
  },
  "spec": {
    "mark": "circle",
    "encoding": {
      "x": {"field": "Horsepower", "type": "quantitative"},
      "y": {"field": "Miles_per_Gallon", "type": "quantitative"}
    }
  }
}
```

---

## 4.5 動手做：讀 Spec、改 Spec

### 練習 1：Altair → JSON → 理解

```python
import altair as alt
import pandas as pd
import json

df = pd.DataFrame({
    'product': ['A', 'B', 'C', 'D'],
    'sales': [100, 200, 150, 300],
    'profit': [20, 50, 30, 80]
})

chart = alt.Chart(df).mark_bar().encode(
    x=alt.X('product:N', sort='-y'),
    y='sales:Q',
    color='product:N',
    tooltip=['product:N', 'sales:Q', 'profit:Q']
)

# 匯出 spec
spec = chart.to_dict()
print(json.dumps(spec, indent=2, ensure_ascii=False))
```

**問題**：
1. `mark` 的值是什麼？
2. `encoding.x` 有哪些屬性？
3. `sort: '-y'` 在 spec 中是什麼樣子？

### 練習 2：手動修改 Spec

```python
import json

# 原始 spec
spec = {
    "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
    "data": {
        "values": [
            {"year": 2020, "sales": 100},
            {"year": 2021, "sales": 120},
            {"year": 2022, "sales": 150},
            {"year": 2023, "sales": 170}
        ]
    },
    "mark": "line",
    "encoding": {
        "x": {"field": "year", "type": "ordinal"},
        "y": {"field": "sales", "type": "quantitative"}
    }
}

# 修改 1：改成長條圖
spec_bar = spec.copy()
spec_bar["mark"] = "bar"

# 修改 2：改成水平長條圖
spec_horizontal = {
    **spec,
    "mark": "bar",
    "encoding": {
        "x": {"field": "sales", "type": "quantitative"},
        "y": {"field": "year", "type": "ordinal"}
    }
}

# 修改 3：加上顏色
spec_colored = {
    **spec,
    "mark": {"type": "bar", "color": "steelblue"},
    "encoding": {
        **spec["encoding"],
        "tooltip": [
            {"field": "year", "type": "ordinal"},
            {"field": "sales", "type": "quantitative"}
        ]
    }
}

# 用 Altair 渲染修改後的 spec
alt.Chart.from_dict(spec_colored)
```

### 練習 3：Spec 差異比較

```python
import json

spec_v1 = {
    "mark": "line",
    "encoding": {
        "x": {"field": "year", "type": "ordinal"},
        "y": {"field": "sales", "type": "quantitative"}
    }
}

spec_v2 = {
    "mark": "bar",
    "encoding": {
        "x": {"field": "sales", "type": "quantitative"},
        "y": {"field": "year", "type": "ordinal"},
        "color": {"value": "steelblue"}
    }
}

# 比較差異
def diff_specs(a, b, path=""):
    """簡易 spec 差異比較"""
    diffs = []
    all_keys = set(list(a.keys()) + list(b.keys()))
    for key in sorted(all_keys):
        current_path = f"{path}.{key}" if path else key
        if key not in a:
            diffs.append(f"  + {current_path}: {b[key]}")
        elif key not in b:
            diffs.append(f"  - {current_path}: {a[key]}")
        elif a[key] != b[key]:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                diffs.extend(diff_specs(a[key], b[key], current_path))
            else:
                diffs.append(f"  ~ {current_path}: {a[key]} → {b[key]}")
    return diffs

changes = diff_specs(spec_v1, spec_v2)
print("Spec 差異：")
for c in changes:
    print(c)
```

輸出：
```
Spec 差異：
  ~ encoding.x.field: year → sales
  ~ encoding.x.type: ordinal → quantitative
  + encoding.color: {'value': 'steelblue'}
  ~ encoding.y.field: sales → year
  ~ encoding.y.type: quantitative → ordinal
  ~ mark: line → bar
```

---

## 4.6 Spec 的威力：為什麼這很重要？

### 場景 1：版本控管

```bash
# 用 git 追蹤 spec 變更
git diff chart_spec.json
```

```diff
{
-  "mark": "line",
+  "mark": "bar",
   "encoding": {
-    "x": {"field": "year", "type": "ordinal"},
-    "y": {"field": "sales", "type": "quantitative"}
+    "x": {"field": "sales", "type": "quantitative"},
+    "y": {"field": "year", "type": "ordinal"}
   }
}
```

你可以清楚看到：「從折線圖改成了水平長條圖」。如果是 PNG，你只能看到兩張不同的圖片。

### 場景 2：Schema 驗證

```python
# 驗證 spec 是否合法
from jsonschema import validate

# Vega-Lite 有完整的 JSON Schema
# 可以用它來驗證 spec 的正確性
def validate_spec(spec):
    required_fields = ['mark', 'encoding']
    for field in required_fields:
        if field not in spec:
            return False, f"缺少必要欄位：{field}"

    valid_marks = ['bar', 'line', 'point', 'circle', 'area',
                   'rect', 'text', 'tick', 'rule', 'boxplot']
    mark = spec['mark'] if isinstance(spec['mark'], str) else spec['mark'].get('type')
    if mark not in valid_marks:
        return False, f"無效的 mark 類型：{mark}"

    return True, "Spec 驗證通過"

# 測試
valid, message = validate_spec({"mark": "bar", "encoding": {"x": {}, "y": {}}})
print(message)  # Spec 驗證通過

valid, message = validate_spec({"mark": "pie", "encoding": {}})
print(message)  # 無效的 mark 類型：pie
```

### 場景 3：Spec 模板系統

```python
def create_chart_spec(data, chart_type, x_field, y_field, color_field=None):
    """根據參數產生 Vega-Lite spec"""
    spec = {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "data": {"values": data},
        "mark": chart_type,
        "encoding": {
            "x": {"field": x_field, "type": "nominal"},
            "y": {"field": y_field, "type": "quantitative"}
        }
    }
    if color_field:
        spec["encoding"]["color"] = {"field": color_field, "type": "nominal"}
    return spec

# 使用
data = [{"cat": "A", "val": 10}, {"cat": "B", "val": 20}]
spec = create_chart_spec(data, "bar", "cat", "val")
alt.Chart.from_dict(spec)
```

---

## 4.7 從 Spec 到產品化的橋樑

到這裡，你已經理解了一個關鍵事實：

```
┌──────────────────────────────────────────────────┐
│                                                  │
│  Altair 圖表 ≠ 一張圖片                          │
│  Altair 圖表 = 一份 JSON 規格文件                 │
│                                                  │
│  這份 JSON 可以：                                 │
│    ✅ 存入資料庫                                   │
│    ✅ 透過 API 傳送                                │
│    ✅ 在前端渲染                                   │
│    ✅ 被 AI 讀取和修改                             │
│    ✅ 用 git 追蹤版本                              │
│    ✅ 用 Schema 驗證正確性                         │
│                                                  │
└──────────────────────────────────────────────────┘
```

接下來的三週，我們會依序實現：
- **第 4 週**：把 Spec 存入資料庫，用 API 提供
- **第 5 週**：用 Next.js 前端渲染 Spec
- **第 6 週**：讓 AI 修改 Spec

---

## 4.8 Vega-Lite 線上編輯器

在學習過程中，Vega 官方提供了一個線上編輯器，非常適合練習：

**Vega Editor**：https://vega.github.io/editor/

你可以：
1. 貼上 JSON Spec
2. 即時看到渲染結果
3. 修改 Spec 並立即預覽
4. 查看自動產生的 Vega Spec（底層編譯結果）

---

## 4.9 本章作業

### 作業 1：Spec 拆解

用 Altair 做任意一張圖表，然後：
1. 用 `chart.to_dict()` 匯出 spec
2. 寫一份文字說明，解釋 spec 中每個欄位的作用
3. 在 Vega Editor 中貼上 spec，確認能正確渲染

### 作業 2：手動修改 Spec

給定以下 spec：

```json
{
  "mark": "bar",
  "data": {
    "values": [
      {"month": "Jan", "sales": 100, "region": "North"},
      {"month": "Feb", "sales": 120, "region": "North"},
      {"month": "Jan", "sales": 80, "region": "South"},
      {"month": "Feb", "sales": 90, "region": "South"}
    ]
  },
  "encoding": {
    "x": {"field": "month", "type": "nominal"},
    "y": {"field": "sales", "type": "quantitative"}
  }
}
```

手動修改 JSON 完成以下任務：
1. 加上 color encoding（用 region 區分）
2. 改成水平長條圖
3. 加上 tooltip
4. 加上標題

### 作業 3：Spec 差異分析

做兩個版本的圖表（v1 和 v2），匯出 spec，比較差異：
1. 列出所有改變的欄位
2. 解釋每個改變對圖表呈現的影響

---

## 本章小結

```
核心觀念：
┌──────────────────────────────────────────────┐
│ Vega-Lite Spec = 視覺化的中介表示（IR）       │
│                                              │
│ IR 的特性：                                   │
│   • 語言無關（Python/JS/R 都能產生）          │
│   • 可存檔、可傳輸、可版本控管                │
│   • 可驗證（JSON Schema）                     │
│   • 可 Diff（比較差異）                       │
│   • 可由 AI 讀取和修改                        │
│                                              │
│ Spec 結構：                                   │
│   data → 資料來源                             │
│   mark → 圖表類型                             │
│   encoding → 資料 ↔ 視覺通道的映射             │
│   transform → 資料轉換                        │
│   config → 全域樣式                           │
└──────────────────────────────────────────────┘
```

> **帶走一句話**：圖表不是圖片，圖表是一份 JSON 規格。
> 理解這一點，你就理解了為什麼 Altair 能通往產品化。

---

[上一章 ← Chapter 03：圖表組合與視覺思考](03-chart-composition.md) ｜ [下一章 → Chapter 05：Spec 存儲與 API 化](05-spec-storage-api.md)

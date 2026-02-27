# Chapter 07：AI 修改圖表規格

> 第 6 週 — 讓 AI 操作視覺化 IR，這就是未來

---

## 本章目標

- 理解「AI 修改 Spec」vs「AI 畫圖」的本質差異
- 設計 AI 與 Spec 互動的 Prompt 策略
- 實作 JSON Patch 機制
- 建立 Schema 驗證防護網
- 完成 AI 可操作的視覺化系統

---

## 7.1 思維轉換：AI 不畫圖，AI 改規格

### 傳統做法（AI 畫圖）

```
使用者：「幫我畫一張銷售趨勢圖」
AI：生成 Python 程式碼 → 執行 → 產出 PNG
```

問題：
- AI 需要執行環境（Python runtime）
- 產出是圖片，無法互動
- 無法部分修改（改顏色要重畫整張）
- 無法和既有系統整合

### 新做法（AI 改 Spec）

```
使用者：「把這張圖改成橫向長條圖，藍色主題」
AI：讀取 JSON Spec → 修改特定欄位 → 回傳修改後的 Spec
```

優勢：
- AI 只需要處理 JSON（不需執行環境）
- 修改是精確的（只改需要改的欄位）
- 結果可驗證（JSON Schema）
- 可以追蹤修改歷史（diff）

```
┌────────────────────────────────────┐
│  傳統：AI → 程式碼 → 執行 → 圖片   │
│  新法：AI → 修改 JSON → 前端渲染    │
│                                    │
│  差異：AI 操作的是「規格」不是「圖」  │
└────────────────────────────────────┘
```

---

## 7.2 Prompt 設計策略

### 策略 1：完整 Spec 替換

最簡單的方式——把原始 Spec 給 AI，讓它回傳修改後的完整 Spec。

```python
import json
from anthropic import Anthropic

client = Anthropic()

def modify_chart_with_ai(original_spec: dict, instruction: str) -> dict:
    """用 AI 修改圖表 spec"""

    prompt = f"""你是一個 Vega-Lite 圖表專家。

以下是一份 Vega-Lite 規格（JSON）：

```json
{json.dumps(original_spec, indent=2, ensure_ascii=False)}
```

使用者的修改要求：
{instruction}

請根據要求修改規格，並回傳完整的修改後 JSON。
只回傳 JSON，不要加任何說明文字。
確保回傳的是合法的 Vega-Lite v5 規格。"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}]
    )

    # 解析回傳的 JSON
    response_text = response.content[0].text
    # 移除可能的 markdown code block
    if response_text.startswith("```"):
        response_text = response_text.split("\n", 1)[1]
        response_text = response_text.rsplit("```", 1)[0]

    return json.loads(response_text)
```

使用範例：

```python
original = {
    "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
    "mark": "line",
    "data": {
        "values": [
            {"year": 2020, "sales": 100},
            {"year": 2021, "sales": 120},
            {"year": 2022, "sales": 150},
            {"year": 2023, "sales": 170}
        ]
    },
    "encoding": {
        "x": {"field": "year", "type": "ordinal"},
        "y": {"field": "sales", "type": "quantitative"}
    }
}

# AI 修改
modified = modify_chart_with_ai(
    original,
    "改成橫向長條圖，使用藍色主題，加上 tooltip"
)

print(json.dumps(modified, indent=2))
```

AI 可能回傳：

```json
{
  "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
  "mark": {"type": "bar", "color": "steelblue"},
  "data": {
    "values": [
      {"year": 2020, "sales": 100},
      {"year": 2021, "sales": 120},
      {"year": 2022, "sales": 150},
      {"year": 2023, "sales": 170}
    ]
  },
  "encoding": {
    "x": {"field": "sales", "type": "quantitative"},
    "y": {"field": "year", "type": "ordinal"},
    "tooltip": [
      {"field": "year", "type": "ordinal"},
      {"field": "sales", "type": "quantitative"}
    ]
  },
  "config": {
    "axis": {"labelFontSize": 12}
  }
}
```

### 策略 2：JSON Patch

更精確的方式——讓 AI 回傳 **差異**（patch），而非完整 Spec。

```python
def get_chart_patch(original_spec: dict, instruction: str) -> list:
    """讓 AI 回傳 JSON Patch"""

    prompt = f"""你是一個 Vega-Lite 圖表專家。

以下是一份 Vega-Lite 規格（JSON）：

```json
{json.dumps(original_spec, indent=2, ensure_ascii=False)}
```

使用者的修改要求：
{instruction}

請回傳一個 JSON Patch（RFC 6902 格式）來描述需要的修改。
只回傳 JSON Patch 陣列，不要加任何說明。

JSON Patch 範例：
[
  {{"op": "replace", "path": "/mark", "value": "bar"}},
  {{"op": "add", "path": "/encoding/tooltip", "value": [{{"field": "x", "type": "nominal"}}]}}
]
"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}]
    )

    response_text = response.content[0].text
    if response_text.startswith("```"):
        response_text = response_text.split("\n", 1)[1]
        response_text = response_text.rsplit("```", 1)[0]

    return json.loads(response_text)
```

應用 Patch：

```python
# pip install jsonpatch
import jsonpatch

patch_ops = get_chart_patch(original, "改成長條圖並加上顏色")
patch = jsonpatch.JsonPatch(patch_ops)
modified = patch.apply(original)
```

JSON Patch 的優勢：

| 特性 | 說明 |
|------|------|
| **精確** | 只描述改變的部分 |
| **可追蹤** | 每個修改操作都有明確記錄 |
| **可回滾** | 反向操作即可還原 |
| **可驗證** | 可以在 apply 前驗證 patch 的合法性 |
| **Token 省** | AI 只需要回傳 patch，而非整份 spec |

### 策略 3：結構化修改指令

```python
def get_structured_modification(original_spec: dict, instruction: str) -> dict:
    """讓 AI 回傳結構化的修改指令"""

    prompt = f"""你是一個 Vega-Lite 圖表專家。

原始規格：
```json
{json.dumps(original_spec, indent=2, ensure_ascii=False)}
```

使用者要求：{instruction}

請回傳一個 JSON 物件，描述需要的修改：
{{
  "mark": "新的 mark 類型（如需修改）",
  "encoding_changes": {{
    "通道名": {{"field": "欄位", "type": "類型"}}
  }},
  "add_encoding": {{
    "新通道": {{"field": "欄位", "type": "類型"}}
  }},
  "remove_encoding": ["要移除的通道"],
  "config": {{}},
  "explanation": "修改說明"
}}

只包含需要修改的部分。只回傳 JSON。"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}]
    )

    response_text = response.content[0].text
    if response_text.startswith("```"):
        response_text = response_text.split("\n", 1)[1]
        response_text = response_text.rsplit("```", 1)[0]

    return json.loads(response_text)


def apply_modification(spec: dict, mod: dict) -> dict:
    """應用結構化修改"""
    result = json.loads(json.dumps(spec))  # deep copy

    if "mark" in mod:
        result["mark"] = mod["mark"]

    if "encoding_changes" in mod:
        for channel, value in mod["encoding_changes"].items():
            result["encoding"][channel] = value

    if "add_encoding" in mod:
        for channel, value in mod["add_encoding"].items():
            result["encoding"][channel] = value

    if "remove_encoding" in mod:
        for channel in mod["remove_encoding"]:
            result["encoding"].pop(channel, None)

    if "config" in mod:
        result["config"] = {**result.get("config", {}), **mod["config"]}

    return result
```

---

## 7.3 Schema 驗證：AI 的護欄

AI 不是完美的——它可能產生不合法的 Spec。我們需要驗證機制。

### 基本驗證

```python
def validate_vegalite_spec(spec: dict) -> tuple[bool, list[str]]:
    """驗證 Vega-Lite spec 的基本正確性"""
    errors = []

    # 1. 必要欄位
    if "mark" not in spec:
        errors.append("缺少 'mark' 欄位")

    if "encoding" not in spec:
        errors.append("缺少 'encoding' 欄位")

    # 2. Mark 類型
    valid_marks = [
        'bar', 'line', 'point', 'circle', 'square',
        'area', 'rect', 'text', 'tick', 'rule',
        'boxplot', 'errorband', 'errorbar'
    ]
    mark = spec.get("mark")
    if isinstance(mark, dict):
        mark = mark.get("type")
    if mark and mark not in valid_marks:
        errors.append(f"無效的 mark 類型：{mark}")

    # 3. Encoding 類型
    valid_types = ['quantitative', 'ordinal', 'nominal', 'temporal']
    encoding = spec.get("encoding", {})
    for channel, config in encoding.items():
        if isinstance(config, dict) and "type" in config:
            if config["type"] not in valid_types:
                errors.append(f"encoding.{channel} 的 type 無效：{config['type']}")

    # 4. 資料欄位檢查（如果有 data.values）
    if "data" in spec and "values" in spec["data"]:
        data = spec["data"]["values"]
        if data:
            available_fields = set(data[0].keys())
            for channel, config in encoding.items():
                if isinstance(config, dict) and "field" in config:
                    if config["field"] not in available_fields:
                        errors.append(
                            f"encoding.{channel} 引用了不存在的欄位：{config['field']}"
                            f"（可用欄位：{available_fields}）"
                        )

    is_valid = len(errors) == 0
    return is_valid, errors
```

### 使用驗證

```python
# AI 修改後，先驗證再使用
modified_spec = modify_chart_with_ai(original, "改成圓餅圖")

is_valid, errors = validate_vegalite_spec(modified_spec)

if is_valid:
    print("Spec 驗證通過")
    # 渲染圖表
    alt.Chart.from_dict(modified_spec)
else:
    print("Spec 驗證失敗：")
    for err in errors:
        print(f"  - {err}")
    # 要求 AI 修正
```

### 進階：使用 Vega-Lite JSON Schema 驗證

```python
# pip install jsonschema requests
import jsonschema
import requests

def validate_with_schema(spec: dict) -> tuple[bool, list[str]]:
    """使用官方 Vega-Lite JSON Schema 驗證"""
    # 下載 schema（實際使用時應快取）
    schema_url = "https://vega.github.io/schema/vega-lite/v5.json"
    schema = requests.get(schema_url).json()

    errors = []
    validator = jsonschema.Draft7Validator(schema)
    for error in validator.iter_errors(spec):
        errors.append(f"{error.json_path}: {error.message}")

    return len(errors) == 0, errors
```

---

## 7.4 完整的 AI 修改流程

```python
class ChartAIModifier:
    """AI 圖表修改器"""

    def __init__(self, api_key: str = None):
        self.client = Anthropic(api_key=api_key) if api_key else Anthropic()
        self.history: list[dict] = []

    def modify(self, spec: dict, instruction: str) -> dict:
        """
        修改圖表 spec

        1. 發送原始 spec + 指令給 AI
        2. 接收修改後的 spec
        3. 驗證 spec
        4. 記錄修改歷史
        5. 回傳結果
        """
        # Step 1: AI 修改
        prompt = f"""你是一個 Vega-Lite v5 圖表專家。

原始規格：
```json
{json.dumps(spec, indent=2, ensure_ascii=False)}
```

修改要求：{instruction}

規則：
1. 只回傳合法的 Vega-Lite v5 JSON
2. 保留原始資料（data 欄位）
3. 確保 encoding 中的 field 都存在於 data 中
4. 不要加任何說明文字，只回傳 JSON
"""

        response = self.client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}]
        )

        response_text = response.content[0].text.strip()
        if response_text.startswith("```"):
            response_text = response_text.split("\n", 1)[1]
            response_text = response_text.rsplit("```", 1)[0]

        # Step 2: 解析
        modified = json.loads(response_text)

        # Step 3: 驗證
        is_valid, errors = validate_vegalite_spec(modified)
        if not is_valid:
            raise ValueError(f"AI 產生的 spec 不合法：{errors}")

        # Step 4: 記錄歷史
        self.history.append({
            "instruction": instruction,
            "before": spec,
            "after": modified,
            "timestamp": datetime.now().isoformat()
        })

        return modified

    def undo(self) -> dict | None:
        """回滾到上一個版本"""
        if not self.history:
            return None
        last = self.history.pop()
        return last["before"]

    def get_history(self) -> list[dict]:
        """取得修改歷史"""
        return [
            {
                "instruction": h["instruction"],
                "timestamp": h["timestamp"]
            }
            for h in self.history
        ]
```

使用範例：

```python
from datetime import datetime

modifier = ChartAIModifier()

# 原始 spec
spec = {
    "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
    "data": {
        "values": [
            {"month": "Jan", "sales": 100, "region": "North"},
            {"month": "Feb", "sales": 120, "region": "North"},
            {"month": "Mar", "sales": 150, "region": "North"},
            {"month": "Jan", "sales": 80, "region": "South"},
            {"month": "Feb", "sales": 90, "region": "South"},
            {"month": "Mar", "sales": 110, "region": "South"}
        ]
    },
    "mark": "line",
    "encoding": {
        "x": {"field": "month", "type": "nominal"},
        "y": {"field": "sales", "type": "quantitative"}
    }
}

# 第一次修改
spec = modifier.modify(spec, "用 region 做顏色區分，加上 tooltip")

# 第二次修改
spec = modifier.modify(spec, "改成堆疊長條圖")

# 第三次修改
spec = modifier.modify(spec, "加上標題「區域銷售比較」，使用深色主題")

# 查看歷史
for h in modifier.get_history():
    print(f"  [{h['timestamp']}] {h['instruction']}")

# 不滿意？回滾
spec = modifier.undo()
```

---

## 7.5 前端整合：AI 修改介面

### Next.js API Route

```typescript
// src/app/api/charts/[id]/ai-modify/route.ts
import { NextResponse } from 'next/server'
import Anthropic from '@anthropic-ai/sdk'

const anthropic = new Anthropic()

interface Props {
  params: Promise<{ id: string }>
}

export async function POST(request: Request, { params }: Props) {
  const { id } = await params
  const { spec, instruction } = await request.json()

  const response = await anthropic.messages.create({
    model: 'claude-sonnet-4-6',
    max_tokens: 4096,
    messages: [{
      role: 'user',
      content: `你是 Vega-Lite v5 專家。修改以下 spec：

\`\`\`json
${JSON.stringify(spec, null, 2)}
\`\`\`

要求：${instruction}

只回傳合法的 Vega-Lite v5 JSON，不要其他文字。`
    }]
  })

  try {
    let text = response.content[0].type === 'text' ? response.content[0].text : ''
    if (text.startsWith('```')) {
      text = text.split('\n').slice(1).join('\n')
      text = text.replace(/```\s*$/, '')
    }
    const modifiedSpec = JSON.parse(text)
    return NextResponse.json({ spec: modifiedSpec })
  } catch {
    return NextResponse.json(
      { error: 'AI 回傳的格式無法解析' },
      { status: 422 }
    )
  }
}
```

### React 元件

```typescript
// src/components/AIChartModifier.tsx
"use client"

import { useState } from 'react'
import VegaChart from './VegaChart'

interface AIChartModifierProps {
  chartId: string
  initialSpec: Record<string, unknown>
}

export default function AIChartModifier({ chartId, initialSpec }: AIChartModifierProps) {
  const [spec, setSpec] = useState(initialSpec)
  const [instruction, setInstruction] = useState('')
  const [loading, setLoading] = useState(false)
  const [history, setHistory] = useState<Record<string, unknown>[]>([initialSpec])

  const handleModify = async () => {
    if (!instruction.trim()) return
    setLoading(true)

    try {
      const res = await fetch(`/api/charts/${chartId}/ai-modify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ spec, instruction })
      })

      const data = await res.json()
      if (data.error) {
        alert(`修改失敗：${data.error}`)
        return
      }

      setHistory(prev => [...prev, data.spec])
      setSpec(data.spec)
      setInstruction('')
    } catch (err) {
      alert('修改失敗')
    } finally {
      setLoading(false)
    }
  }

  const handleUndo = () => {
    if (history.length <= 1) return
    const newHistory = history.slice(0, -1)
    setHistory(newHistory)
    setSpec(newHistory[newHistory.length - 1])
  }

  return (
    <div className="space-y-6">
      {/* 圖表渲染 */}
      <div className="bg-white rounded-lg border p-6">
        <VegaChart spec={spec} />
      </div>

      {/* AI 修改介面 */}
      <div className="flex gap-3">
        <input
          type="text"
          value={instruction}
          onChange={e => setInstruction(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleModify()}
          placeholder="輸入修改指令，例如：改成橫向長條圖，藍色主題"
          className="flex-1 px-4 py-2 border rounded-lg focus:outline-none
                     focus:ring-2 focus:ring-blue-400"
          disabled={loading}
        />
        <button
          onClick={handleModify}
          disabled={loading || !instruction.trim()}
          className="px-6 py-2 bg-blue-500 text-white rounded-lg
                     hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? '修改中...' : 'AI 修改'}
        </button>
        <button
          onClick={handleUndo}
          disabled={history.length <= 1}
          className="px-4 py-2 border rounded-lg hover:bg-gray-50
                     disabled:opacity-50 disabled:cursor-not-allowed"
        >
          復原
        </button>
      </div>

      {/* 修改歷史 */}
      {history.length > 1 && (
        <p className="text-sm text-gray-500">
          已修改 {history.length - 1} 次
        </p>
      )}
    </div>
  )
}
```

---

## 7.6 安全性考量

### 1. Spec 白名單

```python
ALLOWED_MARKS = ['bar', 'line', 'point', 'circle', 'area', 'rect', 'text', 'tick']
ALLOWED_CHANNELS = ['x', 'y', 'color', 'size', 'shape', 'opacity', 'tooltip',
                     'row', 'column', 'text']
ALLOWED_TYPES = ['quantitative', 'ordinal', 'nominal', 'temporal']

def sanitize_spec(spec: dict, original_data: list) -> dict:
    """確保 AI 修改的 spec 安全"""
    # 保留原始資料（防止 AI 修改或注入資料）
    spec["data"] = {"values": original_data}

    # 驗證 mark
    mark = spec.get("mark")
    if isinstance(mark, dict):
        if mark.get("type") not in ALLOWED_MARKS:
            raise ValueError(f"不允許的 mark 類型")
    elif mark not in ALLOWED_MARKS:
        raise ValueError(f"不允許的 mark 類型")

    return spec
```

### 2. 速率限制

```python
from functools import lru_cache
from datetime import datetime, timedelta

class RateLimiter:
    def __init__(self, max_calls: int = 10, period: int = 60):
        self.max_calls = max_calls
        self.period = period
        self.calls: list[datetime] = []

    def check(self) -> bool:
        now = datetime.now()
        self.calls = [c for c in self.calls if now - c < timedelta(seconds=self.period)]
        if len(self.calls) >= self.max_calls:
            return False
        self.calls.append(now)
        return True
```

### 3. 避免誤導性圖表

AI 可能無意中產生誤導性圖表（例如 Y 軸不從 0 開始的長條圖）。可以加入檢查：

```python
def check_misleading(spec: dict) -> list[str]:
    """檢查可能誤導的視覺化設定"""
    warnings = []

    mark = spec.get("mark")
    if isinstance(mark, dict):
        mark = mark.get("type")

    encoding = spec.get("encoding", {})

    # 長條圖 Y 軸不從 0 開始
    if mark == "bar":
        y_config = encoding.get("y", {})
        scale = y_config.get("scale", {})
        if scale.get("zero") is False:
            warnings.append("警告：長條圖的 Y 軸不從 0 開始，可能產生誤導")

    # 缺少軸標籤
    for channel in ["x", "y"]:
        if channel in encoding and "title" not in encoding[channel]:
            warnings.append(f"建議：{channel} 軸缺少標題")

    return warnings
```

---

## 7.7 核心洞察

```
┌──────────────────────────────────────────────────┐
│                                                  │
│  AI 不再「畫圖」                                  │
│  AI 是「修改規格」                                │
│                                                  │
│  這代表：                                         │
│  ✅ AI 的輸出是可驗證的 JSON                       │
│  ✅ 修改是可追蹤、可回滾的                        │
│  ✅ 前端不需要知道 AI 的存在                       │
│  ✅ 人類可以 review AI 的每次修改                  │
│                                                  │
│  這就是：AI Operable Visualization System         │
│                                                  │
└──────────────────────────────────────────────────┘
```

---

## 7.8 本章作業

### 作業 1：AI 修改實驗

使用 AI（可以用 Claude API 或任何 LLM），對以下 spec 進行 5 次不同的修改：

```json
{
  "mark": "bar",
  "data": {
    "values": [
      {"category": "A", "value": 28},
      {"category": "B", "value": 55},
      {"category": "C", "value": 43}
    ]
  },
  "encoding": {
    "x": {"field": "category", "type": "nominal"},
    "y": {"field": "value", "type": "quantitative"}
  }
}
```

修改指令範例：
1. 「改成水平長條圖」
2. 「加上顏色，每個 category 不同色」
3. 「加上 tooltip 顯示 category 和 value」
4. 「改成折線圖加上圓點」
5. 「用深色主題」

記錄每次修改前後的 spec 差異。

### 作業 2：驗證器

寫一個 `validate_spec()` 函數，能檢查：
1. mark 是否合法
2. encoding 中的 field 是否存在於 data 中
3. type 是否合法（Q/O/N/T）

### 作業 3：修改歷史

設計一個修改歷史系統，能夠：
1. 記錄每次 AI 修改的指令和時間
2. 支援回滾（undo）到任意版本
3. 顯示兩個版本之間的 diff

---

## 本章小結

```
本章學會的技能：
┌──────────────────────────────────────────────────┐
│ AI 修改策略：                                     │
│   1. 完整 Spec 替換 — 簡單直接                    │
│   2. JSON Patch — 精確差異                        │
│   3. 結構化修改 — 易於理解                        │
│                                                  │
│ 安全防護：                                        │
│   • Schema 驗證                                   │
│   • 欄位白名單                                    │
│   • 資料保護（不讓 AI 修改原始資料）              │
│   • 誤導性檢查                                    │
│   • 速率限制                                      │
│                                                  │
│ 前端整合：                                        │
│   • API Route 呼叫 AI                             │
│   • React 元件提供修改介面                        │
│   • 修改歷史 + 回滾功能                           │
└──────────────────────────────────────────────────┘
```

> **帶走一句話**：當圖表是 JSON 規格，AI 就從「畫圖工具」變成「規格編輯器」。
> 這不只是技術進步，這是人機協作方式的根本改變。

---

[上一章 ← Chapter 06：Next.js 渲染圖表](06-nextjs-rendering.md) ｜ [下一章 → Chapter 08：期末專案與架構總覽](08-final-project.md)

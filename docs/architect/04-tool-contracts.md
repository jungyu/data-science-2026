# Chapter 4：MCP Tool Contract 標準

> **本章定位**：工具設計。從「使用工具的人」變成「設計工具的人」。
>
> 「好的工具不需要說明書，壞的工具連說明書都看不懂。」

---

## 為什麼工具需要「契約」？

### 沒有契約的世界

```python
# 開發者 A 寫的：
def get_revenue(month):
    return db.query(f"SELECT sum FROM sales WHERE m={month}")

# 開發者 B 寫的：
def fetch_revenue(period, currency="USD"):
    return {"amount": ..., "currency": currency, "period": period}

# 開發者 C 寫的：
def revenue(start_date, end_date, include_tax=True):
    ...
```

三個人寫了三個「查營收」的函數。每一個的：
- 名稱不同
- 參數不同
- 回傳格式不同
- 沒人知道另外兩個怎麼用

**AI Agent 面對這三個函數，會崩潰。**

### 有契約的世界

```
tool: db.revenue
version: 1.0.0
input:  { period: "2025-Q3", currency?: "TWD" }
output: { value: 1250000, unit: "TWD", period: "2025-Q3" }
role: readonly
risk: low
```

一個標準、一種格式、誰來都會用。

---

## 工具契約的六大要素

每一個 MCP 工具必須定義以下六個部分：

```
┌────────────────────────────────────────────────┐
│              Tool Contract 六大要素              │
│                                                  │
│  1. Identity    ──→ 我是誰（名稱、版本、描述）   │
│  2. Input       ──→ 我要什麼（參數定義）          │
│  3. Output      ──→ 我給什麼（回傳格式）          │
│  4. Permission  ──→ 我能做什麼（權限等級）        │
│  5. Risk        ──→ 我有多危險（風險評估）        │
│  6. Error       ──→ 我壞了怎辦（錯誤處理）       │
└────────────────────────────────────────────────┘
```

---

## 要素一：Identity（工具身份）

### 命名慣例

```
格式：domain.action
範例：
  db.query      → 資料庫查詢
  db.kpi        → 資料庫 KPI 查詢
  kb.search     → 知識庫搜尋
  analytics.trend  → 分析趨勢
  ticket.create → 建立工單
  notify.send   → 發送通知
```

### 命名規則

| 規則 | 好的 | 壞的 |
|------|------|------|
| 用動詞 | db.query | db.data |
| 小寫加底線 | kb.search | KB.Search |
| 領域前綴 | analytics.trend | getTrend |
| 具體明確 | ticket.create | ticket.do |

### Identity 模板

```yaml
tool: db.kpi
version: "1.0.0"
description: "查詢業務關鍵績效指標（KPI）的當前值或歷史值"
category: "query"
owner: "data-team"
last_updated: "2025-12-01"
```

---

## 要素二：Input Schema（輸入定義）

### 用 JSON Schema 定義輸入

```json
{
  "input": {
    "type": "object",
    "properties": {
      "name": {
        "type": "string",
        "description": "KPI 名稱",
        "enum": ["revenue", "churn_rate", "cac", "ltv", "nps"]
      },
      "period": {
        "type": "string",
        "description": "查詢時間週期，格式為 YYYY-MM 或 YYYY-QN",
        "pattern": "^\\d{4}-(Q[1-4]|\\d{2})$",
        "examples": ["2025-Q3", "2025-12"]
      },
      "compare_with": {
        "type": "string",
        "description": "比較對象的時間週期（選填）",
        "pattern": "^\\d{4}-(Q[1-4]|\\d{2})$"
      }
    },
    "required": ["name"],
    "additionalProperties": false
  }
}
```

### Input 設計原則

```
原則 1：必填要少，選填要有預設值
  ✅ 只有 "name" 是必填
  ✅ "period" 不填就查最新的

原則 2：用 enum 限制可選值
  ✅ "name" 只能是預定義的 KPI 名稱
  ❌ 不能讓 AI 自己發明 KPI 名稱

原則 3：用 pattern 驗證格式
  ✅ "period" 必須符合 YYYY-QN 格式
  ❌ 不接受 "last month" 這種模糊描述

原則 4：禁止額外參數
  ✅ additionalProperties: false
  ❌ 不讓 AI 偷塞奇怪的參數
```

---

## 要素三：Output Schema（輸出定義）

### 標準輸出格式

```json
{
  "output": {
    "type": "object",
    "properties": {
      "value": {
        "type": "number",
        "description": "KPI 數值"
      },
      "unit": {
        "type": "string",
        "description": "單位",
        "enum": ["%", "TWD", "USD", "count", "days", "score"]
      },
      "period": {
        "type": "string",
        "description": "實際查詢的時間週期"
      },
      "source": {
        "type": "string",
        "description": "資料來源表名"
      },
      "updated_at": {
        "type": "string",
        "format": "date-time",
        "description": "資料最後更新時間"
      },
      "comparison": {
        "type": "object",
        "description": "比較結果（如有）",
        "properties": {
          "previous_value": { "type": "number" },
          "change_absolute": { "type": "number" },
          "change_percent": { "type": "number" }
        }
      }
    },
    "required": ["value", "unit", "period", "source"]
  }
}
```

### Output 設計原則

```
原則 1：一定要有 source
  → AI 引用時才有出處

原則 2：數值必須帶單位
  → 避免「5.2」是百分比還是金額的歧義

原則 3：回傳資料新鮮度
  → updated_at 讓使用者知道數據多新

原則 4：結構化而非字串
  → 回傳 { value: 5.2, unit: "%" }
  → 不要回傳 "5.2%"
```

---

## 要素四：Permission（權限等級）

### 四級權限模型

```
┌──────────────────────────────────────────────┐
│            Permission Levels                  │
│                                                │
│  Level 1: readonly                            │
│    → 只能讀取，不能修改任何東西                 │
│    → 例：db.query, db.kpi, kb.search          │
│    → AI Agent 預設只有這個權限                 │
│                                                │
│  Level 2: write_request                       │
│    → 可以「提出」寫入請求，但需要審核           │
│    → 例：ticket.create, report.generate        │
│    → 產生的請求進入審核佇列                    │
│                                                │
│  Level 3: write_approved                      │
│    → 經過人工審核後可以寫入                     │
│    → 例：db.update（需主管核可）               │
│    → 有完整審計紀錄                            │
│                                                │
│  Level 4: admin                               │
│    → 系統管理操作（不給 AI Agent）             │
│    → 例：schema 變更、權限修改                 │
│    → 只有人類管理員可執行                      │
└──────────────────────────────────────────────┘
```

### 權限矩陣範例

| 工具 | 權限 | AI 可直接用？ | 需要審核？ |
|------|------|:------------:|:---------:|
| db.kpi | readonly | Yes | No |
| db.query | readonly | Yes | No |
| kb.search | readonly | Yes | No |
| analytics.trend | readonly | Yes | No |
| ticket.create | write_request | No | Yes |
| notify.send | write_request | No | Yes |
| report.export | write_request | No | Yes |
| db.update | write_approved | No | Yes + 主管 |
| schema.alter | admin | No | N/A |

---

## 要素五：Risk Level（風險等級）

### 四級風險模型

```
Risk: LOW
  → 只讀操作，不會改變系統狀態
  → 範例：查詢 KPI、搜尋知識庫
  → 失敗影響：使用者暫時看不到資料
  → 審核要求：不需要

Risk: MEDIUM
  → 建立資料，但可以撤銷
  → 範例：建立工單、生成報告
  → 失敗影響：產生錯誤的工單或報告
  → 審核要求：自動審核 + 事後檢查

Risk: HIGH
  → 修改既有資料，撤銷成本高
  → 範例：更新客戶資料、修改價格
  → 失敗影響：資料不一致、業務影響
  → 審核要求：人工審核

Risk: CRITICAL
  → 不可逆操作，影響重大
  → 範例：刪除資料、發送大量通知
  → 失敗影響：資料遺失、品牌損害
  → 審核要求：雙人審核 + 主管核可
```

### 風險評估矩陣

```
                 影響範圍
              小        大
         ┌─────────┬─────────┐
  可逆   │  LOW    │ MEDIUM  │
發       │ 查詢KPI │ 建立工單 │
生       ├─────────┼─────────┤
機率     │ MEDIUM  │  HIGH   │
  不可逆 │ 修改紀錄 │ 刪除資料 │
         └─────────┴─────────┘
```

---

## 要素六：Error Handling（錯誤處理）

### 標準錯誤格式

```json
{
  "error": {
    "code": "KPI_NOT_FOUND",
    "message": "找不到名為 'xxx' 的 KPI",
    "details": {
      "requested_kpi": "xxx",
      "available_kpis": ["revenue", "churn_rate", "cac", "ltv", "nps"]
    },
    "suggestion": "請確認 KPI 名稱是否正確，可用的 KPI 列表如上",
    "timestamp": "2025-12-15T14:30:22Z"
  }
}
```

### 錯誤分類

| 錯誤類型 | 錯誤碼前綴 | 範例 | AI 應如何回應 |
|----------|-----------|------|-------------|
| 參數錯誤 | INVALID_ | INVALID_PERIOD | 提示正確格式 |
| 找不到 | NOT_FOUND_ | KPI_NOT_FOUND | 列出可用選項 |
| 權限不足 | FORBIDDEN_ | FORBIDDEN_WRITE | 解釋需要審核 |
| 服務故障 | SERVICE_ | SERVICE_TIMEOUT | 建議稍後重試 |
| 配額超限 | QUOTA_ | QUOTA_EXCEEDED | 建議降級操作 |

### 錯誤處理原則

```
原則 1：錯誤訊息要對 AI 和人類都有用
  ✅ "找不到 'revenue_growthh'，你可能是指 'revenue_growth'？"
  ❌ "Error code 404"

原則 2：提供修復建議
  ✅ suggestion 欄位告訴 AI 怎麼修正
  ❌ 只告訴它「錯了」

原則 3：列出可用選項
  ✅ available_kpis 讓 AI 自己選正確的
  ❌ 只說「不存在」但不說有什麼

原則 4：分層降級
  ✅ 主要方法失敗 → 嘗試備用方法 → 回報無法完成
  ❌ 一失敗就直接回報錯誤
```

---

## 完整工具契約範例

### 範例一：查詢工具（低風險）

```yaml
tool: db.kpi
version: "1.0.0"
description: "查詢業務關鍵績效指標"
category: query
permission: readonly
risk: low
timeout_ms: 5000
rate_limit: 100/minute

input:
  name:
    type: string
    required: true
    enum: [revenue, churn_rate, cac, ltv, nps]
    description: "KPI 名稱"
  period:
    type: string
    required: false
    pattern: "^\\d{4}-(Q[1-4]|\\d{2})$"
    default: "latest"
    description: "時間週期"

output:
  value: { type: number, description: "KPI 數值" }
  unit: { type: string, description: "單位" }
  period: { type: string, description: "時間週期" }
  source: { type: string, description: "資料來源" }

errors:
  KPI_NOT_FOUND: "KPI 名稱不存在"
  PERIOD_INVALID: "時間格式不正確"
  DB_TIMEOUT: "資料庫查詢超時"
```

### 範例二：寫入工具（高風險）

```yaml
tool: ticket.create
version: "1.0.0"
description: "建立客服工單"
category: action
permission: write_request
risk: medium
timeout_ms: 10000
rate_limit: 10/minute
requires_approval: true

input:
  title:
    type: string
    required: true
    max_length: 200
    description: "工單標題"
  description:
    type: string
    required: true
    max_length: 2000
    description: "問題描述"
  priority:
    type: string
    required: false
    enum: [low, medium, high, urgent]
    default: medium
    description: "優先等級"
  assigned_to:
    type: string
    required: false
    description: "指派給（員工 ID）"

output:
  ticket_id: { type: string, description: "工單編號" }
  status: { type: string, description: "工單狀態" }
  created_at: { type: string, description: "建立時間" }
  approval_status: { type: string, description: "審核狀態" }

errors:
  TITLE_TOO_LONG: "標題超過 200 字元"
  ASSIGNEE_NOT_FOUND: "指派的員工不存在"
  QUOTA_EXCEEDED: "今日工單建立額度已用完"
  APPROVAL_REQUIRED: "此操作需要主管審核"
```

---

## 工具設計 Checklist

每設計一個新工具，用這張表檢查：

```markdown
## 工具設計檢查清單

### Identity
- [ ] 命名遵循 domain.action 慣例
- [ ] 有版本號
- [ ] 描述清楚明確

### Input
- [ ] 必填參數盡量少
- [ ] 用 enum 限制可選值
- [ ] 用 pattern 驗證格式
- [ ] 禁止額外參數

### Output
- [ ] 有 source 欄位
- [ ] 數值帶單位
- [ ] 結構化輸出（非字串）
- [ ] 包含資料新鮮度

### Permission
- [ ] 權限等級明確
- [ ] 寫入操作需審核
- [ ] AI Agent 預設 readonly

### Risk
- [ ] 風險等級已評估
- [ ] 高風險有額外保護
- [ ] 有速率限制

### Error
- [ ] 錯誤碼有分類
- [ ] 錯誤訊息可讀
- [ ] 有修復建議
- [ ] 有可用選項列表
```

---

## 動手做：設計你的工具

### 練習 4-1：設計三個工具

為你的專案領域設計三個工具，涵蓋不同風險等級：

1. 一個 readonly/low-risk 的查詢工具
2. 一個 write_request/medium-risk 的操作工具
3. 一個需要特殊審核的工具

使用本章的 YAML 模板完成每個工具的六要素定義。

### 練習 4-2：錯誤場景推演

選你設計的一個工具，列出所有可能的錯誤場景，為每個場景寫出：
- 錯誤碼
- 錯誤訊息
- AI 應該怎麼回應使用者

---

## 本章重點回顧

```
┌─────────────────────────────────────────────┐
│          Tool Contract 六大要素速記            │
│                                               │
│  1. Identity：domain.action + 版本號          │
│  2. Input：JSON Schema + enum + pattern       │
│  3. Output：結構化 + source + 單位            │
│  4. Permission：readonly → write → admin      │
│  5. Risk：low → medium → high → critical     │
│  6. Error：分類 + 可讀訊息 + 修復建議          │
└─────────────────────────────────────────────┘
```

---

## 下一章預告

工具設計完了，接下來設計「記憶系統」。

在 [Chapter 5：可治理 RAG 設計](05-rag-architecture.md) 中，你會學到：
- 文件怎麼切割成 Chunk
- 怎麼確保 RAG 不會「幻覺」
- Citation 格式的標準
- 知識庫的版本控制

你的 AI 需要一個可靠的「記憶」。

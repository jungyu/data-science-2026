# Chapter 8：成本與觀測設計

> **本章定位**：儀表板設計。讓你看到 AI 系統的「健康狀態」和「帳單」。
>
> 「你不會開一台沒有儀表板的車，也不該營運一個沒有觀測的系統。」

---

## AI 系統不是免費的

### 一個殘酷的計算

```
假設你的 AI Agent 系統：
  - 每個使用者請求平均消耗 2,000 tokens
  - 每天有 500 個請求
  - 使用 GPT-4 等級的模型

每日 token 消耗：
  500 請求 × 2,000 tokens = 1,000,000 tokens/天

每月成本（粗估）：
  Input:  500K tokens/天 × 30 天 × $0.01/1K = $150
  Output: 500K tokens/天 × 30 天 × $0.03/1K = $450
  Embedding: 500 次/天 × 30 天 × $0.0001 = $1.5
  Vector DB: ~$50/月
  ─────────────────────────
  月成本合計：約 $650（≈ NT$ 20,000）

看起來不多？如果使用者翻 10 倍呢？
  → 月成本 $6,500（≈ NT$ 200,000）

如果有人寫了一個迴圈瘋狂呼叫你的 API？
  → 一天就可能燒掉一個月的預算
```

這就是為什麼你需要**成本觀測**。

---

## 觀測的三大支柱

```
┌─────────────────────────────────────────────────┐
│           觀測三大支柱（Three Pillars）            │
│                                                    │
│  ┌─────────────┐                                  │
│  │   Metrics    │  數值指標                        │
│  │   指標       │  「現在的 token 使用量是多少？」   │
│  └─────────────┘                                  │
│                                                    │
│  ┌─────────────┐                                  │
│  │   Logs       │  事件紀錄                        │
│  │   日誌       │  「這個請求經歷了哪些步驟？」      │
│  └─────────────┘                                  │
│                                                    │
│  ┌─────────────┐                                  │
│  │   Traces     │  請求追蹤                        │
│  │   追蹤       │  「這個請求為什麼這麼慢？」       │
│  └─────────────┘                                  │
│                                                    │
│  三者合在一起 = 完整的系統觀測能力                  │
└─────────────────────────────────────────────────┘
```

---

## 支柱一：Metrics（指標）

### 關鍵指標儀表板

```
┌─────────────────────────────────────────────────┐
│                AI System Dashboard                │
│                                                    │
│  ┌── 成本指標 ──────────────────────────────┐   │
│  │ 今日 Token 消耗：125,432 / 500,000 (25%)  │   │
│  │ 本月累計成本：$234.56 / $800 (29%)         │   │
│  │ 平均每請求成本：$0.047                      │   │
│  └────────────────────────────────────────────┘  │
│                                                    │
│  ┌── 效能指標 ──────────────────────────────┐   │
│  │ 平均回應時間：1.2s                         │   │
│  │ P95 回應時間：3.8s                         │   │
│  │ 工具呼叫成功率：98.7%                      │   │
│  │ RAG 檢索命中率：85.2%                      │   │
│  └────────────────────────────────────────────┘  │
│                                                    │
│  ┌── 品質指標 ──────────────────────────────┐   │
│  │ Citation 覆蓋率：92%                       │   │
│  │ 使用者滿意度：4.2/5                        │   │
│  │ 降級回應比例：3.1%                         │   │
│  │ 找不到答案比例：8.5%                       │   │
│  └────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

### 指標定義規格

```yaml
metrics:
  # 成本指標
  cost_metrics:
    token_usage_daily:
      description: "每日 Token 使用量"
      type: counter
      unit: tokens
      dimensions: [model, operation_type, user_group]
      alert:
        warning: "> 80% of daily_budget"
        critical: "> 95% of daily_budget"

    cost_per_request:
      description: "每個請求的平均成本"
      type: gauge
      unit: USD
      dimensions: [request_type, user_group]
      alert:
        warning: "> $0.10"
        critical: "> $0.50"

    monthly_spend:
      description: "當月累計花費"
      type: counter
      unit: USD
      reset: monthly
      alert:
        warning: "> 70% of monthly_budget"
        critical: "> 90% of monthly_budget"

  # 效能指標
  performance_metrics:
    response_time:
      description: "端到端回應時間"
      type: histogram
      unit: milliseconds
      percentiles: [50, 90, 95, 99]
      alert:
        warning: "p95 > 5000ms"
        critical: "p95 > 10000ms"

    tool_call_success_rate:
      description: "工具呼叫成功率"
      type: gauge
      unit: percentage
      alert:
        warning: "< 95%"
        critical: "< 90%"

    rag_hit_rate:
      description: "RAG 檢索命中率"
      type: gauge
      unit: percentage
      alert:
        warning: "< 80%"
        critical: "< 60%"

  # 品質指標
  quality_metrics:
    citation_coverage:
      description: "回答中包含 citation 的比例"
      type: gauge
      unit: percentage
      target: "> 90%"

    degraded_response_rate:
      description: "降級回應的比例"
      type: gauge
      unit: percentage
      alert:
        warning: "> 5%"
        critical: "> 10%"
```

---

## 支柱二：Logs（日誌）

### Token 成本日誌

```json
{
  "type": "token_usage",
  "trace_id": "abc-123",
  "timestamp": "2025-12-15T14:30:22Z",
  "user_id": "user_042",
  "request_type": "kpi_query",
  "model": "gpt-4",
  "tokens": {
    "input": 1250,
    "output": 380,
    "total": 1630,
    "embedding": 256
  },
  "cost": {
    "input": 0.0125,
    "output": 0.0114,
    "embedding": 0.0001,
    "total_usd": 0.0240
  },
  "tool_calls": [
    {
      "tool": "db.kpi",
      "duration_ms": 234,
      "status": "success"
    }
  ],
  "rag_queries": [
    {
      "query": "客戶流失率趨勢",
      "results_count": 3,
      "top_score": 0.89,
      "duration_ms": 156
    }
  ]
}
```

### 工具呼叫日誌

```json
{
  "type": "tool_call",
  "trace_id": "abc-123",
  "timestamp": "2025-12-15T14:30:22.580Z",
  "tool": "db.kpi",
  "version": "1.0.0",
  "input": {
    "name": "churn_rate",
    "period": "2025-12"
  },
  "output": {
    "value": 5.2,
    "unit": "%"
  },
  "performance": {
    "queue_time_ms": 5,
    "execution_time_ms": 229,
    "total_time_ms": 234
  },
  "status": "success",
  "caller": "agent_session_789"
}
```

---

## 支柱三：Traces（追蹤）

### 延遲分析（Latency Breakdown）

```
一個請求的時間拆解：

使用者問：「上個月的客戶流失率跟前月相比如何？」

┌──────────────────────────────────────────┐
│ Total: 2,450ms                            │
│                                            │
│ ├── 請求解析: 50ms                        │
│ ├── 意圖分析: 180ms                       │
│ ├── 工具呼叫 1 (db.kpi): 234ms           │
│ ├── 工具呼叫 2 (db.kpi): 256ms           │
│ ├── RAG 查詢: 0ms (本次不需要)            │
│ ├── AI 生成回應: 1,580ms  ← 最慢的部分   │
│ ├── Citation 附加: 30ms                   │
│ └── 回應格式化: 120ms                     │
│                                            │
│ 瓶頸：AI 生成回應佔了 64% 的時間          │
└──────────────────────────────────────────┘
```

### 追蹤標準格式

```json
{
  "trace_id": "abc-123",
  "parent_id": null,
  "spans": [
    {
      "span_id": "s1",
      "name": "request_parse",
      "start": 0,
      "duration_ms": 50,
      "status": "ok"
    },
    {
      "span_id": "s2",
      "name": "intent_analysis",
      "start": 50,
      "duration_ms": 180,
      "status": "ok",
      "attributes": {
        "intent": "kpi_comparison",
        "confidence": 0.95
      }
    },
    {
      "span_id": "s3",
      "name": "tool_call.db.kpi",
      "start": 230,
      "duration_ms": 234,
      "status": "ok",
      "attributes": {
        "tool": "db.kpi",
        "params": {"name": "churn_rate", "period": "2025-12"}
      }
    },
    {
      "span_id": "s4",
      "name": "tool_call.db.kpi",
      "start": 230,
      "duration_ms": 256,
      "status": "ok",
      "attributes": {
        "tool": "db.kpi",
        "params": {"name": "churn_rate", "period": "2025-11"}
      }
    },
    {
      "span_id": "s5",
      "name": "ai_generation",
      "start": 486,
      "duration_ms": 1580,
      "status": "ok",
      "attributes": {
        "model": "gpt-4",
        "input_tokens": 1250,
        "output_tokens": 380
      }
    }
  ]
}
```

---

## Drift 概念（系統漂移）

### 什麼是 Drift？

```
Drift = 系統行為隨時間緩慢偏離預期

類比：
  你買了一台新車。第一年油耗 10km/L。
  三年後變成 8km/L。你沒有注意到，
  因為它是一點一點變差的。
  直到有天你加了 $3,000 的油才驚覺：車出問題了。

AI 系統也會 drift：
  - RAG 品質慢慢下降（知識庫過期）
  - 成本慢慢上升（prompt 越來越長）
  - 回應品質慢慢變差（使用者問題變複雜）
```

### 三種 Drift 類型

```
1. Data Drift（資料漂移）
   原因：使用者的問題類型變了
   現象：RAG 命中率下降
   偵測：監控 RAG 相關性分數的趨勢

2. Performance Drift（效能漂移）
   原因：資料量增加、系統負載上升
   現象：回應時間慢慢變長
   偵測：監控 P95 延遲的週趨勢

3. Cost Drift（成本漂移）
   原因：對話變長、工具呼叫變多
   現象：每個請求的成本慢慢增加
   偵測：監控每請求平均成本的趨勢
```

### Drift 偵測設計

```yaml
drift_detection:
  data_drift:
    metric: rag_hit_rate
    window: 7_days
    method: moving_average
    alert:
      condition: "7日均值 比 30日均值 低 10%+"
      action: "通知管理員檢查知識庫"

  performance_drift:
    metric: response_time_p95
    window: 7_days
    method: linear_regression
    alert:
      condition: "斜率 > 50ms/week"
      action: "效能檢查 + 資源評估"

  cost_drift:
    metric: cost_per_request
    window: 7_days
    method: moving_average
    alert:
      condition: "7日均值 比 上月同期 高 20%+"
      action: "成本分析 + 優化建議"
```

---

## 成本預估模型

### 基礎預估公式

```
月成本 = (日請求量 × 每請求平均 token × 30 × token 單價)
       + 固定成本（DB、hosting、等）

範例：
  日請求量：500
  每請求平均 token：2,000（input + output）
  Token 單價：$0.02 / 1K tokens（混合）
  固定成本：$100/月

  月成本 = (500 × 2,000 × 30 × $0.02/1000) + $100
         = $600 + $100
         = $700/月
```

### 成本優化策略

```
策略 1：快取（Caching）
  相同問題不重複呼叫 AI
  預期節省：20-40%

  適用：常見問題、KPI 查詢、標準回答
  不適用：個人化問題、即時資料查詢

策略 2：模型分級（Model Tiering）
  簡單問題用便宜模型，複雜問題用強模型

  ┌─────────────────────────────────────┐
  │ 問題分級 → 模型選擇                   │
  │                                       │
  │ 簡單（FAQ）    → GPT-3.5 ($0.002/1K) │
  │ 中等（分析）   → GPT-4-mini           │
  │ 複雜（多步推理）→ GPT-4 ($0.03/1K)   │
  └─────────────────────────────────────┘
  預期節省：30-50%

策略 3：Prompt 優化
  減少不必要的 context，精簡 system prompt
  預期節省：10-20%

策略 4：批次處理
  非即時需求合併處理
  預期節省：15-25%
```

### 預算控制機制

```yaml
budget_control:
  daily_limit:
    soft: 400000 tokens  # 80% → 發出警告
    hard: 500000 tokens  # 100% → 降級服務

  monthly_limit:
    soft: 10000000 tokens
    hard: 15000000 tokens

  per_user_limit:
    hourly: 50000 tokens
    daily: 200000 tokens

  actions:
    at_soft_limit:
      - "啟用快取（更積極）"
      - "切換到更便宜的模型"
      - "通知管理員"

    at_hard_limit:
      - "只處理高優先級請求"
      - "其他請求排入佇列"
      - "緊急通知管理員"
```

---

## 動手做：設計你的觀測系統

### 練習 8-1：成本預估

用以下模板估算你的專案成本：

| 項目 | 數值 | 說明 |
|------|------|------|
| 預估日請求量 | | |
| 每請求平均 token | | |
| 選用模型和單價 | | |
| 固定成本（月） | | |
| **預估月成本** | | |
| 年成本 | | |

### 練習 8-2：指標儀表板設計

為你的系統設計一個儀表板，列出你認為最重要的 8 個指標：

| # | 指標名稱 | 類型 | 單位 | 警告閾值 | 嚴重閾值 |
|---|----------|------|------|----------|----------|
| 1 | | | | | |
| 2 | | | | | |
| ... | | | | | |

### 練習 8-3：Drift 劇本

設計一個 drift 場景：描述你的系統可能怎麼「慢慢變差」，以及你怎麼偵測和處理。

---

## 本章重點回顧

```
┌─────────────────────────────────────────────┐
│          觀測與成本五大記憶點                   │
│                                               │
│  1. AI 系統有真實的金錢成本                    │
│  2. 觀測三支柱：Metrics + Logs + Traces       │
│  3. Drift 會讓系統慢慢變差                     │
│  4. 成本可以透過快取、分級、優化 prompt 降低   │
│  5. 一定要有預算控制機制                       │
└─────────────────────────────────────────────┘
```

---

## 下一章預告

儀表板裝好了，接下來要裝「安全氣囊」。

在 [Chapter 9：風險矩陣與防呆設計](09-risk-guardrails.md) 中，你會學到：
- AI 系統最常見的風險有哪些
- 怎麼設計 guardrails
- 不同領域的風險特性

讓你的系統在出事之前就「煞車」。

# Chapter 3：A2RM 最終專案權威規格

> **本章定位**：核心規格書。這是整個架構師層最重要的一份文件。
>
> 「A2RM 不是框架名稱，是你的系統必須通過的能力測驗。」

---

## 什麼是 A2RM？

**A2RM = Agent × Automation × RAG × MCP**

這四個字母代表一個完整 AI 系統必須具備的四大能力：

```
┌─────────────────────────────────────────────────┐
│                    A2RM 四大支柱                   │
│                                                    │
│  Agent        ──→  智慧代理人（大腦）              │
│  Automation   ──→  自動化流程（肌肉）              │
│  RAG          ──→  知識檢索增強（記憶）            │
│  MCP          ──→  工具協議標準（手）               │
│                                                    │
│  合在一起 = 一個能思考、能記憶、能動手、            │
│            能自動運轉的完整系統                      │
└─────────────────────────────────────────────────┘
```

### 類比：A2RM 就像一個員工

```
Agent      = 員工的大腦（理解問題、制定計畫）
RAG        = 員工的筆記本（查資料、找前例）
MCP Tools  = 員工的工具箱（計算機、報表系統）
Automation = 員工的 SOP（例行工作自動化）
```

一個只有大腦沒有工具的員工 → 只能空談
一個只有工具沒有大腦的員工 → 只會盲目操作
A2RM 的目標就是讓這四個能力協同運作。

---

## A2RM 能力規格總表

### 必備能力清單

以下是一個合格 A2RM 系統必須具備的能力：

```
┌────────────────────────────────────────────────────────┐
│ 能力                    │ 必備等級 │ 驗收標準             │
├────────────────────────────────────────────────────────┤
│ 1. 本地知識庫 RAG       │  ★★★   │ 回答附 citation       │
│ 2. MCP 工具契約          │  ★★★   │ 固定 schema          │
│ 3. Automation Flow      │  ★★☆   │ 至少一個自動流程      │
│ 4. Evidence Answer      │  ★★★   │ 每個答案有證據鏈      │
│ 5. Log Trace            │  ★★★   │ 完整操作紀錄         │
│ 6. Domain Pack          │  ★★☆   │ 可替換的領域包        │
│ 7. Guardrails           │  ★★★   │ 安全防護機制         │
│ 8. Cost Awareness       │  ★★☆   │ Token 使用追蹤       │
└────────────────────────────────────────────────────────┘

★★★ = 必須完整實作
★★☆ = 必須有基本實作
★☆☆ = 建議實作
```

---

## 能力一：本地知識庫 RAG

### 規格要求

```yaml
capability: RAG
level: ★★★

requirements:
  ingestion:
    - 支援 PDF、Markdown、TXT 格式
    - 文件匯入時自動建立索引
    - 保留來源 metadata（檔名、頁碼、日期）

  retrieval:
    - 語意搜尋（不只是關鍵字比對）
    - Top-K 結果可配置（預設 K=5）
    - 相關性分數 > 0.7 才納入 context

  citation:
    - 每個回答段落都要標註來源
    - 格式：[來源：文件名, 頁碼/段落]
    - 找不到相關資料時明確告知

  quality:
    - Chunk 大小可配置（預設 500 tokens）
    - 支援 overlap（預設 50 tokens）
    - 定期驗證索引品質
```

### 合格 vs 不合格的 RAG 回答

```
❌ 不合格：
「公司的退貨政策是 30 天內可退貨。」
→ 沒有來源、沒有條件、無法驗證

✅ 合格：
「根據『客戶服務手冊 v3.2』（kb://customer-service-manual.pdf, p.12），
 標準退貨政策為購買後 30 天內，商品需保持原包裝。
 特殊品類（食品、個人衛生用品）不適用此政策（同文件 p.13）。」
→ 有來源、有條件、可驗證
```

---

## 能力二：MCP 工具契約

### 規格要求

```yaml
capability: MCP Tool Contracts
level: ★★★

requirements:
  schema:
    - 每個工具有明確的 input schema（JSON Schema）
    - 每個工具有明確的 output schema
    - Schema 有版本號

  security:
    - 每個工具標註權限等級（readonly / write / admin）
    - 每個工具標註風險等級（low / medium / high / critical）
    - 寫入操作需要人工審核

  logging:
    - 每次呼叫記錄：工具名、輸入、輸出、耗時、呼叫者
    - 失敗時記錄錯誤原因

  contract:
    - 工具名稱遵循命名慣例（domain.action）
    - 預期回應時間有上限（timeout）
    - 有明確的錯誤回傳格式
```

### 工具契約範例

```json
{
  "tool": "db.kpi",
  "version": "1.0.0",
  "description": "查詢業務關鍵指標",
  "permission": "readonly",
  "risk": "low",
  "timeout_ms": 5000,
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
        "description": "時間週期",
        "pattern": "^\\d{4}-(Q[1-4]|\\d{2})$"
      }
    },
    "required": ["name"]
  },
  "output": {
    "type": "object",
    "properties": {
      "value": { "type": "number" },
      "unit": { "type": "string" },
      "period": { "type": "string" },
      "source": { "type": "string" }
    }
  },
  "errors": {
    "KPI_NOT_FOUND": "指定的 KPI 不存在",
    "PERIOD_INVALID": "時間格式不正確",
    "DB_TIMEOUT": "資料庫查詢超時"
  }
}
```

**詳細設計請見** → [Chapter 4：MCP Tool Contract 標準](04-tool-contracts.md)

---

## 能力三：Automation Flow

### 規格要求

```yaml
capability: Automation
level: ★★☆

requirements:
  minimum:
    - 至少實作一個完整的自動化流程
    - 流程有明確的觸發條件和終止條件
    - 流程有異常處理機制

  design:
    - 流程圖可視化
    - 每個步驟有 input/output 定義
    - 支援人工介入點（Human-in-the-loop）

  monitoring:
    - 流程執行有完整日誌
    - 異常時發送通知
    - 可追蹤流程狀態
```

### 三種標準流程

```
流程 A：查詢報告流程
  觸發 → 使用者提問
  步驟 → 解析意圖 → 呼叫工具 → 整合結果 → 生成報告
  結束 → 回傳報告 + 記錄日誌

流程 B：知識庫更新流程
  觸發 → 新文件上傳
  步驟 → 驗證格式 → 切割 Chunk → 建立索引 → 版本標記
  結束 → 通知管理員 + 記錄日誌

流程 C：異常警報流程
  觸發 → KPI 超出閾值
  步驟 → 確認異常 → 拉取相關數據 → 生成分析 → 建立工單
  結束 → 通知負責人 + 記錄日誌
```

**詳細設計請見** → [Chapter 7：自動化流程模式庫](07-automation-patterns.md)

---

## 能力四：Evidence Answer Format

### 規格要求

```yaml
capability: Evidence-based Answers
level: ★★★

requirements:
  structure:
    - 每個回答包含：結論 + 證據 + 來源
    - 數據必須來自工具呼叫（不能 AI 自行估算）
    - 推理過程必須可追蹤

  citation:
    - 知識庫引用：[kb://文件名, 位置]
    - 工具呼叫引用：[tool://工具名(參數)]
    - 外部來源引用：[ref://URL, 存取日期]

  uncertainty:
    - 信心程度標註（high / medium / low）
    - 找不到資料時明確告知
    - 不確定時提供替代建議
```

### Evidence Answer 模板

```markdown
## 回答

[結論性陳述]

## 證據

| # | 資料點 | 來源 | 信心度 |
|---|--------|------|--------|
| 1 | [具體數據] | [tool://工具名] | high |
| 2 | [文件摘要] | [kb://文件名, p.XX] | high |
| 3 | [推算結果] | [基於 #1 和 #2 計算] | medium |

## 推理鏈

1. 根據 [證據 1]，我們知道 ___
2. 結合 [證據 2]，可以推導 ___
3. 因此結論是 ___

## 限制與不確定性

- [這個分析沒有考慮的因素]
- [資料的時效性限制]
- [建議進一步確認的事項]
```

---

## 能力五：Log Trace

### 規格要求

```yaml
capability: Logging and Tracing
level: ★★★

requirements:
  coverage:
    - 每個使用者請求有唯一 trace_id
    - 每個工具呼叫記錄在日誌中
    - 每個 RAG 查詢記錄在日誌中
    - 回應生成過程記錄在日誌中

  format:
    timestamp: ISO 8601
    trace_id: UUID v4
    fields:
      - user_id
      - action_type
      - tool_name (if applicable)
      - input_summary
      - output_summary
      - duration_ms
      - token_usage
      - error (if applicable)

  retention:
    - 操作日誌保留 90 天
    - 錯誤日誌保留 180 天
    - 審計日誌保留 1 年
```

### 日誌範例

```json
{
  "trace_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "timestamp": "2025-12-15T14:30:22.456Z",
  "user_id": "user_042",
  "session_id": "sess_789",
  "events": [
    {
      "seq": 1,
      "type": "request",
      "content": "上個月的客戶流失率？",
      "timestamp": "2025-12-15T14:30:22.456Z"
    },
    {
      "seq": 2,
      "type": "plan",
      "tools": ["db.kpi"],
      "params": {"name": "churn_rate", "period": "2025-11"},
      "timestamp": "2025-12-15T14:30:22.580Z"
    },
    {
      "seq": 3,
      "type": "tool_call",
      "tool": "db.kpi",
      "input": {"name": "churn_rate", "period": "2025-11"},
      "output": {"value": 4.8, "unit": "%"},
      "duration_ms": 234,
      "timestamp": "2025-12-15T14:30:22.814Z"
    },
    {
      "seq": 4,
      "type": "response",
      "content": "2025 年 11 月客戶流失率為 4.8%...",
      "token_usage": {"input": 450, "output": 120},
      "total_duration_ms": 1200,
      "timestamp": "2025-12-15T14:30:23.656Z"
    }
  ]
}
```

---

## 能力六：Domain Pack

### 規格要求

```yaml
capability: Domain Pack
level: ★★☆

requirements:
  structure:
    - 標準化目錄結構
    - 每個 Domain Pack 獨立、可替換
    - 核心系統不依賴特定 Domain Pack

  contents:
    - kb/：知識庫文件
    - kpi.json：KPI 定義
    - prompts.md：領域專用提示詞
    - demo-script.md：展示腳本
    - risk-note.md：領域風險說明

  portability:
    - 換一個 Domain Pack 不需要改核心程式碼
    - 可以同時載入多個 Domain Pack
    - Pack 之間互不干擾
```

**詳細設計請見** → [Chapter 10：Domain Pack 標準](10-domain-packs.md)

---

## 能力七：Guardrails

### 規格要求

```yaml
capability: Safety Guardrails
level: ★★★

requirements:
  input_guard:
    - 輸入長度限制
    - 敏感詞偵測
    - Prompt injection 防護

  output_guard:
    - 回答不能包含敏感資料（PII）
    - 高風險回答需降級處理
    - 不確定時明確告知（不能瞎掰）

  operation_guard:
    - 寫入操作需人工審核
    - 成本超過閾值時暫停
    - 異常模式偵測（例如短時間大量查詢）
```

**詳細設計請見** → [Chapter 9：風險矩陣與防呆設計](09-risk-guardrails.md)

---

## 能力八：Cost Awareness

### 規格要求

```yaml
capability: Cost Tracking
level: ★★☆

requirements:
  tracking:
    - 每個請求記錄 token 使用量
    - 每個工具呼叫記錄耗時
    - 按使用者/功能/時段統計成本

  budgeting:
    - 可設定每日/每月 token 上限
    - 接近上限時發出警告
    - 超過上限時降級服務

  optimization:
    - 識別高成本操作
    - 建議快取策略
    - 提供成本效益分析
```

**詳細設計請見** → [Chapter 8：成本與觀測設計](08-observability-cost.md)

---

## A2RM 自我檢核表

在你的專案完成後，用這張表做最終檢查：

```markdown
## A2RM 能力檢核

### RAG ★★★
- [ ] 支援至少一種文件格式的匯入
- [ ] 語意搜尋功能正常
- [ ] 每個回答都有 citation
- [ ] 找不到資料時有明確提示

### MCP Tools ★★★
- [ ] 至少 3 個工具有完整 schema
- [ ] 工具有權限和風險分級
- [ ] 所有工具呼叫有日誌

### Automation ★★☆
- [ ] 至少一個自動化流程可運行
- [ ] 流程有異常處理
- [ ] 流程執行有日誌

### Evidence Answer ★★★
- [ ] 回答有證據和來源
- [ ] 數據來自工具（非 AI 猜測）
- [ ] 不確定時有標註

### Log Trace ★★★
- [ ] 每個請求有 trace_id
- [ ] 工具呼叫有紀錄
- [ ] 可根據 trace_id 重建完整過程

### Domain Pack ★★☆
- [ ] 至少一個 Domain Pack
- [ ] Pack 結構符合標準
- [ ] 換 Pack 不需改核心程式

### Guardrails ★★★
- [ ] 輸入有驗證
- [ ] 輸出有過濾
- [ ] 寫入操作有保護

### Cost Awareness ★★☆
- [ ] Token 使用量有追蹤
- [ ] 有基本的成本統計
- [ ] 有超限保護機制
```

---

## 動手做：設計你的 A2RM 系統

### 練習 3-1：能力規劃

為你的期末專案選一個領域（電商/醫療/教育/金融），填寫 A2RM 能力規劃表：

| 能力 | 你的規劃 | 優先級 |
|------|----------|--------|
| RAG：知識來源是？ | | |
| MCP：需要哪些工具？ | | |
| Automation：什麼流程可自動化？ | | |
| Evidence：證據來源有哪些？ | | |
| Logs：記錄什麼？保留多久？ | | |
| Domain Pack：領域資料有哪些？ | | |
| Guardrails：最大的風險是什麼？ | | |
| Cost：預算上限是多少？ | | |

### 練習 3-2：Evidence Answer 實作

寫出三個你的系統可能收到的問題，並用 Evidence Answer 格式寫出回答模板（不需要真實數據，但格式要完整）。

---

## 本章重點回顧

```
┌─────────────────────────────────────────────┐
│          A2RM 八大能力速記                     │
│                                               │
│  1. RAG：知識檢索 + citation                  │
│  2. MCP：工具契約 + schema                    │
│  3. Automation：自動流程 + 異常處理            │
│  4. Evidence：結論 + 證據 + 來源              │
│  5. Logs：完整追蹤 + trace_id                 │
│  6. Domain Pack：可替換的領域包               │
│  7. Guardrails：安全防護 + 降級               │
│  8. Cost：成本追蹤 + 預算控制                  │
└─────────────────────────────────────────────┘
```

---

## 下一章預告

A2RM 規格定了，接下來深入每一個能力。

在 [Chapter 4：MCP Tool Contract 標準](04-tool-contracts.md) 中，你會學到：
- 怎麼設計一個「好的工具」
- 工具的 schema 怎麼寫
- 權限、風險、錯誤處理的標準

從「用工具」升級到「設計工具」。

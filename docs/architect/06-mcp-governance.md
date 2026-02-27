# Chapter 6：Agent 治理模型

> **本章定位**：法律框架。為你的 AI Agent 建立一套「憲法」。
>
> 「沒有治理的 AI 就像沒有交通規則的馬路 — 遲早出事。」

---

## 什麼是 Agent 治理？

### 類比：Agent 治理就像公司管理

```
公司沒有管理制度：
  員工想做什麼就做什麼
  → 混亂、資料外洩、重複勞動、無法追責

公司有管理制度：
  ✓ 誰能存取什麼資料（權限控制）
  ✓ 做了什麼要記錄（審計紀錄）
  ✓ 重大決定要審核（審批流程）
  ✓ 出了問題可以追溯（問責機制）

AI Agent 的治理 = 把同樣的制度套用在 AI 身上
```

### 治理的核心問題

```
1. 誰能做什麼？    → 權限控制
2. 做了什麼？      → 審計紀錄
3. 該不該做？      → 審核流程
4. 做壞了怎辦？    → 回滾機制
5. 怎麼防範？      → 防呆設計
```

---

## 治理支柱一：Read-Only Policy

### 為什麼 AI 預設要 Read-Only？

```
故事時間：

某公司讓 AI Agent 可以直接修改客戶資料庫。
有一天，使用者問：「幫我清理不活躍的客戶。」
AI 把三年沒登入的客戶全部刪除了。
其中包括每年只在聖誕節下一筆大單的 VIP 客戶。

損失：NT$ 2,000 萬潛在營收
原因：AI 有寫入權限 + 沒有人工審核

如果是 Read-Only：
  AI：「找到 3,247 位超過三年未登入的客戶。
       建議進一步分析其消費模式後再決定。
       是否要我生成分析報告？」
  → 人類決策，AI 輔助
```

### Read-Only Policy 實作

```yaml
read_only_policy:
  default: true  # 所有 Agent 預設只能讀取

  exceptions:
    - action: "ticket.create"
      condition: "需要人工審核後才生效"
      approval: "supervisor"

    - action: "report.generate"
      condition: "生成到暫存區，不直接發送"
      approval: "auto_review"

  forbidden:
    - "直接修改資料庫記錄"
    - "刪除任何資料"
    - "直接發送郵件給客戶"
    - "修改系統設定"
    - "存取其他使用者的資料"
```

### 三層權限架構

```
┌─────────────────────────────────────────────────┐
│          Layer 1: Read（讀取）                    │
│          AI 可以直接做的事                         │
│                                                    │
│  ✓ 查詢資料庫（SELECT only）                      │
│  ✓ 搜尋知識庫                                     │
│  ✓ 讀取 KPI                                      │
│  ✓ 生成分析（不儲存）                              │
├─────────────────────────────────────────────────┤
│          Layer 2: Request（請求）                  │
│          AI 可以提出，但需要人工審核                 │
│                                                    │
│  ⚠ 建立工單（進入審核佇列）                        │
│  ⚠ 生成報告（存到暫存區）                          │
│  ⚠ 發送通知（需主管核可）                          │
│  ⚠ 資料匯出（需確認範圍）                          │
├─────────────────────────────────────────────────┤
│          Layer 3: Prohibited（禁止）               │
│          AI 永遠不能做的事                          │
│                                                    │
│  ✗ 修改/刪除資料庫記錄                             │
│  ✗ 存取其他使用者的隱私資料                         │
│  ✗ 修改系統設定和權限                              │
│  ✗ 直接對外發送任何通訊                             │
│  ✗ 執行未定義的工具呼叫                            │
└─────────────────────────────────────────────────┘
```

---

## 治理支柱二：禁止任意 SQL

### 為什麼不能讓 AI 寫 SQL？

```
AI 寫 SQL 的五大風險：

1. SQL Injection
   AI 可能生成包含惡意片段的 SQL
   → WHERE name = '' OR 1=1 --

2. 效能炸彈
   AI 可能寫出效能極差的查詢
   → SELECT * FROM orders JOIN products（百萬筆 cross join）

3. 資料洩漏
   AI 可能查到不該看的資料
   → SELECT * FROM users（包含密碼和個資）

4. 意外修改
   AI 可能寫出修改語句
   → UPDATE users SET role = 'admin'（提權攻擊）

5. Schema 曝露
   AI 可能探索資料庫結構
   → SELECT * FROM information_schema.tables
```

### 正確的替代方案

```
❌ 讓 AI 寫 SQL：
  user: "上個月營收多少？"
  AI → SQL: "SELECT SUM(amount) FROM sales WHERE month = '2025-12'"
  → 風險不可控

✅ 讓 AI 呼叫預定義工具：
  user: "上個月營收多少？"
  AI → tool: db.kpi("revenue", "2025-12")
  → 工具內部執行預定義的 SQL
  → 權限、格式、範圍都是固定的

✅✅ 更好的方式 — 參數化查詢視圖：
  AI → tool: db.query(view="monthly_sales", params={month: "2025-12"})
  → 視圖（View）已預先定義好 SQL
  → AI 只能選擇視圖和填入參數
  → 完全杜絕 SQL 注入和意外查詢
```

---

## 治理支柱三：Change Request Flow

### 什麼操作需要 Change Request？

```
分類標準：

自動放行（不需要 CR）：
  - 讀取操作（查詢、搜尋）
  - 純分析（不修改任何資料）
  - 生成暫存報告

需要 Change Request：
  - 建立新記錄（工單、報告）
  - 觸發通知（郵件、訊息）
  - 資料匯出
  - 任何影響外部系統的操作
```

### Change Request 流程

```
┌──────────────────────────────────────────────────┐
│           Change Request Flow                     │
│                                                    │
│  ① AI 提出變更請求                                │
│     │                                              │
│     ▼                                              │
│  ② 系統自動檢查                                   │
│     ├── 權限足夠？ ─── No ──→ 拒絕 + 記錄         │
│     ├── 風險等級？                                  │
│     │   ├── Low ──→ 自動核可                       │
│     │   ├── Medium ──→ 排入審核佇列                │
│     │   └── High ──→ 需要主管審核                  │
│     │                                              │
│     ▼                                              │
│  ③ 人工審核（Medium/High）                         │
│     ├── 核可 ──→ 執行變更                          │
│     ├── 拒絕 ──→ 通知 AI + 記錄原因                │
│     └── 修改 ──→ 調整後重新審核                    │
│                                                    │
│  ④ 執行變更                                       │
│     └── 記錄完整的變更日誌                          │
│                                                    │
│  ⑤ 事後驗證                                       │
│     └── 確認變更結果符合預期                        │
└──────────────────────────────────────────────────┘
```

### Change Request 記錄格式

```json
{
  "cr_id": "CR-2025-001234",
  "requested_by": "agent_session_789",
  "requested_at": "2025-12-15T14:30:00Z",
  "action": "ticket.create",
  "parameters": {
    "title": "Q3 客戶流失率異常上升",
    "priority": "high",
    "assigned_to": "team_cs"
  },
  "risk_level": "medium",
  "auto_check": {
    "permission": "pass",
    "risk_assessment": "medium - 建立工單不影響既有資料",
    "rate_limit": "pass (2/10 today)"
  },
  "approval": {
    "status": "approved",
    "approved_by": "manager_chen",
    "approved_at": "2025-12-15T14:35:00Z",
    "comment": "同意建立，請追蹤後續分析"
  },
  "execution": {
    "status": "completed",
    "result": { "ticket_id": "TK-5678" },
    "executed_at": "2025-12-15T14:35:01Z"
  }
}
```

---

## 治理支柱四：Human-in-the-Loop（HITL）

### HITL 的三種模式

```
Mode 1: Human-on-the-Loop（監督模式）
  AI 自動執行，人類事後監控
  → 適用於低風險的例行操作
  → 例：自動生成每日 KPI 報告

  ┌───────┐     ┌───────┐     ┌──────────┐
  │  AI   │ ──→ │ 執行  │ ──→ │ 人類監控  │
  │ 決策  │     │ 操作  │     │ （事後）  │
  └───────┘     └───────┘     └──────────┘

Mode 2: Human-in-the-Loop（審核模式）
  AI 提出建議，人類審核後才執行
  → 適用於中風險的操作
  → 例：建立工單、發送報告

  ┌───────┐     ┌──────────┐     ┌───────┐
  │  AI   │ ──→ │ 人類審核  │ ──→ │ 執行  │
  │ 建議  │     │ （事前）  │     │ 操作  │
  └───────┘     └──────────┘     └───────┘

Mode 3: Human-at-the-Helm（主導模式）
  人類主導決策，AI 只提供資訊
  → 適用於高風險的決策
  → 例：客戶資料修改、政策變更

  ┌──────────┐     ┌───────┐     ┌───────┐
  │ 人類決策  │ ←── │  AI   │     │ 人類  │
  │  + 指令  │     │ 資訊  │ ──→ │ 執行  │
  └──────────┘     └───────┘     └───────┘
```

### HITL 場景矩陣

| 操作類型 | 風險等級 | HITL 模式 | 範例 |
|----------|----------|-----------|------|
| 資料查詢 | 低 | on-the-loop | 查 KPI |
| 報告生成 | 低 | on-the-loop | 日報 |
| 工單建立 | 中 | in-the-loop | 客訴工單 |
| 通知發送 | 中 | in-the-loop | 客戶通知 |
| 資料修改 | 高 | at-the-helm | 更新客戶資料 |
| 政策決定 | 高 | at-the-helm | 退貨政策調整 |
| 資料刪除 | 極高 | 禁止 AI 操作 | — |

---

## 治理支柱五：審計紀錄

### 為什麼需要審計？

```
場景：週二早上，客戶打來抱怨收到一封錯誤的通知郵件。

沒有審計紀錄：
  「呃... 不知道是誰發的、為什麼發的、什麼時候發的。」
  → 無法追責、無法修復、無法防止再次發生

有審計紀錄：
  「週一下午 3:12，Agent Session #789 基於 KPI 異常觸發了
   notification.send 工具。審核者是 Manager Chen，於 3:15 核可。
   通知模板是 template_002，發送對象是 group_vip。
   問題出在模板 template_002 的合併欄位有誤。」
  → 精確定位、快速修復、預防再發
```

### 審計紀錄標準

```yaml
audit_log:
  required_fields:
    - trace_id: "請求追蹤 ID"
    - timestamp: "ISO 8601 格式"
    - actor: "操作者（agent/human/system）"
    - action: "操作類型"
    - target: "操作對象"
    - input: "輸入參數"
    - output: "輸出結果"
    - status: "成功/失敗"
    - duration_ms: "耗時"

  optional_fields:
    - approval_chain: "審核鏈（如有）"
    - risk_level: "風險等級"
    - error_detail: "錯誤詳情（如失敗）"
    - rollback_ref: "回滾參考（如有）"

  rules:
    - "日誌只能追加（append-only），不能修改或刪除"
    - "敏感資料要脫敏（例如個資）"
    - "操作日誌保留 90 天"
    - "審計日誌保留 1 年"
    - "日誌存儲要與業務資料分離"
```

### 審計查詢場景

```
場景 1：追蹤特定請求
  query: trace_id = "abc-123"
  → 看到完整的請求處理鏈

場景 2：查看某個工具的使用情況
  query: action = "db.kpi" AND date = "2025-12-15"
  → 看到今天所有的 KPI 查詢

場景 3：找出失敗的操作
  query: status = "failed" AND date >= "2025-12-01"
  → 看到這個月所有失敗的操作

場景 4：審計特定使用者
  query: actor = "user_042" AND action_type = "write"
  → 看到這個使用者所有的寫入操作
```

---

## 治理實作：Constitution 模板

### AI Agent 憲法（Constitution）

```yaml
# AI Agent Constitution v1.0
# 最後更新：2025-12-01

identity:
  name: "企業分析助手"
  version: "1.0.0"
  purpose: "協助企業決策者進行數據分析和知識查詢"

fundamental_rules:
  - "永遠不能刪除或修改既有資料"
  - "所有回答必須附帶來源引用"
  - "不確定時明確告知，不能猜測"
  - "遇到敏感問題時升級到人工處理"
  - "每個操作都必須記錄在審計日誌中"

permissions:
  allowed:
    - "查詢資料庫（readonly）"
    - "搜尋知識庫"
    - "生成分析報告（暫存）"
    - "提出工單建立請求"

  requires_approval:
    - "發送通知"
    - "匯出資料"
    - "建立工單"

  forbidden:
    - "修改資料庫記錄"
    - "存取個人隱私資料"
    - "執行未定義的工具"
    - "繞過審核流程"

safety:
  max_tokens_per_request: 4000
  max_tool_calls_per_request: 10
  rate_limit: "100 requests/hour per user"
  sensitive_topics:
    - pattern: "法律建議"
      action: "disclaimer + refer to legal team"
    - pattern: "醫療建議"
      action: "disclaimer + refer to medical professional"
    - pattern: "個人隱私"
      action: "refuse + log attempt"

escalation:
  triggers:
    - "信心度 < 0.5"
    - "涉及敏感主題"
    - "使用者表達不滿"
    - "連續 3 次找不到答案"
  action: "轉接人工客服 + 保留完整對話紀錄"
```

---

## 動手做：設計你的治理模型

### 練習 6-1：權限矩陣設計

為你的專案列出所有可能的操作，並分類到三層權限架構中：

| 操作 | 層級 | HITL 模式 | 風險等級 | 審核者 |
|------|------|-----------|----------|--------|
| | Read / Request / Prohibited | on/in/at | Low-Critical | |

### 練習 6-2：寫一份 AI 憲法

用上面的模板，為你的 AI Agent 寫一份 Constitution。

### 練習 6-3：審計場景推演

設計三個「出事了」的場景，並說明你的審計紀錄如何幫助：
1. 定位問題
2. 評估影響
3. 修復問題
4. 預防再發

---

## 本章重點回顧

```
┌─────────────────────────────────────────────┐
│          Agent 治理五大支柱速記                │
│                                               │
│  1. Read-Only：AI 預設只能讀取               │
│  2. 禁止 SQL：用預定義工具取代                │
│  3. Change Request：寫入操作要審核            │
│  4. HITL：根據風險選擇人機互動模式            │
│  5. 審計紀錄：所有操作都可追溯                │
└─────────────────────────────────────────────┘
```

---

## 下一章預告

治理規則建好了，接下來設計「自動化」。

在 [Chapter 7：自動化流程模式庫](07-automation-patterns.md) 中，你會學到：
- 三種標準自動化模式
- 怎麼在自動化中嵌入治理機制
- 異常處理和回退設計

讓你的系統自動運轉，但又不失控。

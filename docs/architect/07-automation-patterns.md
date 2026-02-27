# Chapter 7：自動化流程模式庫

> **本章定位**：流程模式。給你三套標準的自動化範本，直接套用到你的專案。
>
> 「自動化不是讓電腦替你做事，是讓電腦按照你設計的流程做事。」

---

## 自動化的正確心態

### 自動化 ≠ 無人化

```
❌ 錯誤認知：
  「自動化就是全部交給 AI，我去喝咖啡。」

✅ 正確認知：
  「自動化是把重複的步驟標準化，
   但關鍵決策點仍然由人類把關。」

類比：
  自動駕駛不是沒有方向盤的車，
  而是一台會自己維持車道、自動煞車、
  但複雜路口仍需要你接手的車。
```

### 適合自動化的工作 vs 不適合的

```
✅ 適合自動化：
  - 有固定步驟的例行工作
  - 觸發條件明確的監控
  - 資料收集和整理
  - 標準格式的報告生成

❌ 不適合自動化：
  - 需要創意判斷的決策
  - 涉及人際溝通的敏感議題
  - 沒有明確規則的例外處理
  - 後果嚴重且不可逆的操作
```

---

## 模式一：問題 → 查詢 → 報告 → 通知

### 場景

```
情境：每天早上 9 點，自動生成昨日的業務概況報告。

觸發：定時排程（每日 09:00）
結果：一份報告寄到主管信箱
```

### 流程圖

```
┌─────────────────────────────────────────────────────┐
│        Pattern 1: Query → Report → Notify            │
│                                                       │
│  ┌──────────┐                                        │
│  │  觸發     │  定時 09:00 / 手動觸發 / 事件觸發     │
│  └────┬─────┘                                        │
│       │                                               │
│       ▼                                               │
│  ┌──────────┐                                        │
│  │ ① 查詢   │  呼叫 db.kpi() 取得昨日 KPI           │
│  │   資料    │  呼叫 db.query() 取得摘要數據          │
│  └────┬─────┘                                        │
│       │                                               │
│       ▼                                               │
│  ┌──────────┐                                        │
│  │ ② 分析   │  比較 KPI 與前日/前週/前月             │
│  │   比對    │  標記異常值（超出閾值）                 │
│  └────┬─────┘                                        │
│       │                                               │
│       ▼                                               │
│  ┌──────────┐                                        │
│  │ ③ 生成   │  套用報告模板                           │
│  │   報告    │  填入數據 + 分析 + 圖表                │
│  └────┬─────┘                                        │
│       │                                               │
│       ▼                                               │
│  ┌──────────┐     ┌─────────────┐                    │
│  │ ④ 品質   │──→  │ 異常？      │                    │
│  │   檢查    │     │ 資料缺失？  │                    │
│  └──────────┘     └──────┬──────┘                    │
│                     │          │                      │
│                    OK        異常                     │
│                     │          │                      │
│                     ▼          ▼                      │
│               ┌──────────┐  ┌────────────┐           │
│               │ ⑤ 發送   │  │ 標記異常    │           │
│               │   通知    │  │ + 人工審核  │           │
│               └──────────┘  └────────────┘           │
│                                                       │
│  ┌──────────┐                                        │
│  │ ⑥ 記錄   │  完整的執行日誌                         │
│  │   日誌    │  + 報告快照 + 通知紀錄                  │
│  └──────────┘                                        │
└─────────────────────────────────────────────────────┘
```

### 實作規格

```yaml
pattern: query_report_notify
trigger:
  type: schedule
  cron: "0 9 * * *"  # 每天 09:00
  manual: true        # 也支援手動觸發

steps:
  - name: query_kpis
    tool: db.kpi
    params:
      names: [revenue, orders, churn_rate, nps]
      period: "yesterday"
    timeout: 10s
    on_failure: retry(3) → abort

  - name: compare_analysis
    type: internal
    logic: |
      for each kpi:
        compare with previous_day, previous_week, previous_month
        flag if change > threshold
    thresholds:
      revenue: ±10%
      orders: ±15%
      churn_rate: ±20%
      nps: ±5

  - name: generate_report
    type: template
    template: daily_business_report_v2
    data: [query_kpis.output, compare_analysis.output]
    format: markdown

  - name: quality_check
    type: validation
    rules:
      - "所有 KPI 都有值（不能是 null）"
      - "數值在合理範圍內"
      - "報告長度 > 100 字"
    on_failure: flag_for_review

  - name: notify
    tool: notify.send
    requires_approval: false  # 例行報告不需審核
    params:
      channel: email
      to: [manager_group]
      subject: "Daily Report - {date}"
      body: generate_report.output

  - name: log
    type: audit
    record: [trace_id, all_step_results, execution_time]
```

---

## 模式二：KB 更新 → 重建索引 → 版本標記

### 場景

```
情境：管理員上傳了新版的產品手冊。
     系統需要自動處理、建立索引、並確保 RAG 使用最新版本。

觸發：檔案上傳事件
結果：知識庫更新、舊版歸檔、索引重建
```

### 流程圖

```
┌─────────────────────────────────────────────────────┐
│       Pattern 2: KB Update → Reindex → Version       │
│                                                       │
│  ┌──────────┐                                        │
│  │  觸發     │  管理員上傳新文件                       │
│  └────┬─────┘                                        │
│       │                                               │
│       ▼                                               │
│  ┌──────────┐     ┌──────────┐                       │
│  │ ① 驗證   │──→  │ 格式OK？  │                       │
│  │   文件    │     │ 大小OK？  │                       │
│  └──────────┘     └────┬─────┘                       │
│                    │        │                         │
│                   OK      失敗                        │
│                    │        └─→ 通知上傳者 + 中止      │
│                    ▼                                   │
│  ┌──────────┐                                        │
│  │ ② 檢查   │  同名文件是否已存在？                    │
│  │   版本    │  → 存在：升級版本號                      │
│  │          │  → 不存在：新增 v1.0                     │
│  └────┬─────┘                                        │
│       │                                               │
│       ▼                                               │
│  ┌──────────┐                                        │
│  │ ③ 切割   │  按照 Chunk 策略切割文件                 │
│  │ + 向量化 │  生成 Embedding                          │
│  └────┬─────┘                                        │
│       │                                               │
│       ▼                                               │
│  ┌──────────┐                                        │
│  │ ④ 更新   │  新 chunks 加入索引                      │
│  │   索引    │  舊版 chunks 標記 archived              │
│  └────┬─────┘                                        │
│       │                                               │
│       ▼                                               │
│  ┌──────────┐                                        │
│  │ ⑤ 驗證   │  用預設問題測試新索引                    │
│  │   測試    │  確認能正確檢索到新內容                  │
│  └────┬─────┘                                        │
│       │                                               │
│       ▼                                               │
│  ┌──────────┐                                        │
│  │ ⑥ 版本   │  記錄版本號 + 時間 + 操作者             │
│  │   標記    │  生成 changelog                         │
│  └────┬─────┘                                        │
│       │                                               │
│       ▼                                               │
│  ┌──────────┐                                        │
│  │ ⑦ 通知   │  通知管理員：更新完成                    │
│  │          │  通知相關團隊：知識庫已更新               │
│  └──────────┘                                        │
└─────────────────────────────────────────────────────┘
```

### 實作規格

```yaml
pattern: kb_update_reindex
trigger:
  type: event
  event: file_uploaded
  path: /kb/incoming/*

steps:
  - name: validate_file
    type: validation
    rules:
      - format: [pdf, md, txt]
      - max_size: 50MB
      - encoding: utf-8
    on_failure: notify_uploader → abort

  - name: check_version
    type: internal
    logic: |
      existing = kb.find(filename)
      if existing:
        new_version = existing.version + 0.1
        existing.status = "archived"
      else:
        new_version = 1.0

  - name: chunk_and_embed
    type: pipeline
    chunk_strategy: hybrid
    chunk_size: 500
    overlap: 50
    embedding_model: text-embedding-3-small
    timeout: 60s

  - name: update_index
    type: internal
    logic: |
      insert new chunks into vector_db
      mark old version chunks as archived
      update metadata table

  - name: verification_test
    type: test
    test_queries:
      - "這份文件的主要內容是什麼？"
      - "[根據文件內容生成的具體問題]"
    expected: "回答引用新版本文件"
    on_failure: rollback → notify_admin

  - name: version_tag
    type: metadata
    record:
      version: new_version
      uploaded_by: trigger.user
      uploaded_at: now()
      chunk_count: chunk_and_embed.count
      changelog: "上傳新版 {filename} v{new_version}"

  - name: notify
    tool: notify.send
    params:
      channel: internal
      to: [admin, related_team]
      message: "知識庫已更新：{filename} v{new_version}"
```

---

## 模式三：KPI 異常 → 觸發分析 → 建立工單

### 場景

```
情境：系統偵測到客戶流失率突然飆升，
     自動觸發分析，找出可能原因，並建立追蹤工單。

觸發：KPI 超出預設閾值
結果：分析報告 + 工單（待人工審核）
```

### 流程圖

```
┌─────────────────────────────────────────────────────┐
│     Pattern 3: Anomaly → Analysis → Ticket           │
│                                                       │
│  ┌──────────┐                                        │
│  │  觸發     │  KPI 監控偵測到異常                     │
│  │          │  churn_rate: 8.5% (閾值: 6%)           │
│  └────┬─────┘                                        │
│       │                                               │
│       ▼                                               │
│  ┌──────────┐                                        │
│  │ ① 確認   │  排除資料延遲造成的假警報               │
│  │   異常    │  確認是真實異常而非數據問題              │
│  └────┬─────┘                                        │
│       │                                               │
│       ├── 假警報 → 記錄 + 結束                        │
│       │                                               │
│       ▼ 真實異常                                      │
│  ┌──────────┐                                        │
│  │ ② 拉取   │  取得相關的歷史數據                      │
│  │   數據    │  取得同期比較數據                        │
│  │          │  取得相關 KPI（可能關聯的指標）           │
│  └────┬─────┘                                        │
│       │                                               │
│       ▼                                               │
│  ┌──────────┐                                        │
│  │ ③ 自動   │  趨勢分析                               │
│  │   分析    │  相關性分析                              │
│  │          │  查詢知識庫（是否有類似歷史案例）          │
│  └────┬─────┘                                        │
│       │                                               │
│       ▼                                               │
│  ┌──────────┐                                        │
│  │ ④ 生成   │  異常摘要                               │
│  │   報告    │  可能原因（ranked by probability）      │
│  │          │  建議的行動方案                          │
│  └────┬─────┘                                        │
│       │                                               │
│       ▼                                               │
│  ┌──────────┐                                        │
│  │ ⑤ 建立   │  標題：[自動] KPI 異常 - {kpi_name}    │
│  │   工單    │  內容：分析報告                          │
│  │ (需審核)  │  優先級：基於嚴重程度自動設定            │
│  └────┬─────┘                                        │
│       │                                               │
│       ▼                                               │
│  ┌──────────┐                                        │
│  │ ⑥ 通知   │  即時通知相關負責人                      │
│  │ + 日誌   │  完整的事件處理紀錄                      │
│  └──────────┘                                        │
└─────────────────────────────────────────────────────┘
```

### 實作規格

```yaml
pattern: anomaly_analysis_ticket
trigger:
  type: threshold
  monitor:
    - kpi: churn_rate
      condition: "> 6%"
      severity: high
    - kpi: revenue
      condition: "decrease > 15% vs previous_period"
      severity: critical
    - kpi: nps
      condition: "< 30"
      severity: medium

steps:
  - name: confirm_anomaly
    type: validation
    checks:
      - "資料更新時間 < 2 小時前"
      - "非已知的資料維護時段"
      - "非重複觸發（24 小時內同 KPI）"
    on_false_alarm: log("false_alarm") → abort

  - name: gather_data
    parallel: true
    calls:
      - tool: db.kpi
        params: { name: "{trigger.kpi}", period: "last_7_days" }
      - tool: db.kpi
        params: { name: "{trigger.kpi}", period: "same_period_last_month" }
      - tool: db.kpi
        params: { name: [related_kpis], period: "yesterday" }

  - name: analyze
    type: agent
    prompt: |
      分析以下 KPI 異常：
      - KPI: {trigger.kpi}
      - 當前值: {trigger.value}
      - 閾值: {trigger.threshold}
      - 歷史數據: {gather_data.output}

      請提供：
      1. 異常的嚴重程度評估
      2. 三個最可能的原因（附信心度）
      3. 建議的行動方案

  - name: generate_report
    type: template
    template: anomaly_report_v1
    data: [trigger, gather_data.output, analyze.output]

  - name: create_ticket
    tool: ticket.create
    requires_approval: true
    params:
      title: "[Auto] KPI Alert - {trigger.kpi}: {trigger.value}"
      description: generate_report.output
      priority: "{trigger.severity}"
      assigned_to: "team_{trigger.kpi_owner}"
      labels: ["auto-generated", "kpi-anomaly"]

  - name: notify_and_log
    parallel: true
    calls:
      - tool: notify.send
        params:
          channel: urgent
          to: ["{trigger.kpi_owner}", "manager"]
          message: "KPI Alert: {trigger.kpi} = {trigger.value}"
      - type: audit
        record: full_execution_trace
```

---

## 流程設計 Checklist

每設計一個自動化流程，檢查以下項目：

```markdown
## 自動化流程檢查清單

### 觸發機制
- [ ] 觸發條件明確（時間/事件/閾值）
- [ ] 有防重複觸發機制
- [ ] 手動觸發也能運作

### 執行流程
- [ ] 每個步驟有明確的輸入/輸出
- [ ] 步驟之間的依賴關係清楚
- [ ] 可並行的步驟有標示

### 異常處理
- [ ] 每個步驟有失敗處理方式
- [ ] 有超時機制
- [ ] 有重試策略
- [ ] 有回退/降級方案

### 治理嵌入
- [ ] 寫入操作有審核機制
- [ ] 關鍵步驟有人工介入點
- [ ] 完整的日誌記錄
- [ ] 通知機制運作正常

### 品質保證
- [ ] 有驗證步驟
- [ ] 有測試案例
- [ ] 效能在可接受範圍
- [ ] 成本在預算內
```

---

## 動手做：設計你的自動化流程

### 練習 7-1：選擇一個模式

從三個標準模式中選一個，為你的專案領域設計一個自動化流程。包含完整的流程圖和規格。

### 練習 7-2：異常場景推演

為你設計的流程，列出五個可能的異常場景：

| # | 異常場景 | 偵測方式 | 處理策略 | 回退方案 |
|---|----------|----------|----------|----------|
| 1 | | | | |
| 2 | | | | |
| 3 | | | | |
| 4 | | | | |
| 5 | | | | |

---

## 本章重點回顧

```
┌─────────────────────────────────────────────┐
│          自動化流程三大模式速記                 │
│                                               │
│  模式 1：查詢 → 報告 → 通知（例行報告）        │
│  模式 2：更新 → 索引 → 版本（知識庫維護）      │
│  模式 3：異常 → 分析 → 工單（異常監控）        │
│                                               │
│  關鍵原則：                                    │
│  ✓ 自動化 ≠ 無人化                            │
│  ✓ 每個流程要有異常處理                        │
│  ✓ 寫入操作要有審核                            │
│  ✓ 完整的日誌記錄                              │
└─────────────────────────────────────────────┘
```

---

## 下一章預告

流程設計好了，接下來要裝「儀表板」。

在 [Chapter 8：成本與觀測設計](08-observability-cost.md) 中，你會學到：
- AI 系統的成本怎麼算
- 怎麼追蹤每一分錢花在哪裡
- 系統健康度的觀測指標

你的車需要一個儀表板。

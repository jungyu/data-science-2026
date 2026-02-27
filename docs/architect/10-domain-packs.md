# Chapter 10：Domain Pack 標準

> **本章定位**：模組化設計。讓你的系統架構固定，領域資料可替換。
>
> 「好的架構就像插座：標準統一，什麼電器都能插。」

---

## 什麼是 Domain Pack？

### 類比：Domain Pack 就像遊戲的「資料片」

```
遊戲本體（Core System）：
  引擎、物理系統、渲染器、UI 框架
  → 這些不隨遊戲內容改變

資料片（Domain Pack）：
  角色、地圖、任務、對話
  → 這些可以自由替換和擴充

你的 AI 系統也一樣：
  Core System：Agent Orchestrator + RAG + MCP + Automation
  Domain Pack：知識庫 + KPI + Prompt + 風險說明
  → 換一個領域 = 換一個 Domain Pack
  → 核心架構完全不用動
```

### 為什麼需要 Domain Pack？

```
場景：你為「電商」建了一套 AI 分析系統，做得很好。
     現在老闆說：「醫療產業的客戶也想要。」

沒有 Domain Pack：
  「呃... 要重新開發一套... 可能要三個月...」
  → 每個領域都要重新來過

有 Domain Pack：
  「我只要製作一個醫療領域的 Domain Pack，
   核心系統不用改，大概兩週。」
  → 一次設計，多次使用

                    ┌─── 電商 Domain Pack
                    │
  Core System ──────┼─── 醫療 Domain Pack
                    │
                    ├─── 金融 Domain Pack
                    │
                    └─── 教育 Domain Pack
```

---

## Domain Pack 標準結構

### 目錄規範

```
domain-packs/
  └── {domain-name}/           # 例：ecommerce/
      ├── manifest.json         # Pack 清單和設定
      ├── kb/                   # 知識庫文件
      │   ├── products.md
      │   ├── policies.md
      │   └── faq.md
      ├── kpi.json              # KPI 定義
      ├── tools.json            # 領域特定工具定義
      ├── prompts.md            # 領域專用提示詞
      ├── guardrails.yaml       # 領域風險規則
      ├── demo-script.md        # 展示腳本
      ├── test-cases.json       # 測試案例
      └── risk-note.md          # 領域風險說明
```

### 每個文件的角色

```
manifest.json    → 包裹的「外包裝標籤」：名稱、版本、內容物清單
kb/              → 包裹的「教科書」：這個領域的所有知識
kpi.json         → 包裹的「記分板」：要追蹤什麼指標
tools.json       → 包裹的「工具箱」：領域特有的工具
prompts.md       → 包裹的「性格設定」：AI 在這個領域怎麼說話
guardrails.yaml  → 包裹的「安全手冊」：這個領域的紅線
demo-script.md   → 包裹的「說明書」：怎麼展示
test-cases.json  → 包裹的「考卷」：怎麼測試
risk-note.md     → 包裹的「警告標示」：要注意什麼
```

---

## 文件規格詳解

### manifest.json（清單文件）

```json
{
  "name": "ecommerce",
  "display_name": "電商領域包",
  "version": "1.0.0",
  "description": "適用於電商場景的 AI 分析系統領域包",
  "author": "Your Team",
  "created_at": "2025-12-01",
  "updated_at": "2025-12-15",

  "compatibility": {
    "core_version": ">=2.0.0",
    "required_tools": ["db.kpi", "db.query", "kb.search"],
    "optional_tools": ["ticket.create", "notify.send"]
  },

  "contents": {
    "kb_files": 5,
    "kpi_count": 12,
    "tool_count": 3,
    "test_cases": 20
  },

  "tags": ["ecommerce", "retail", "analytics"],
  "language": "zh-TW"
}
```

### kb/（知識庫目錄）

```markdown
## 知識庫文件規範

每個知識庫文件必須包含：
1. 標題和版本號
2. 最後更新日期
3. 適用範圍
4. 正文內容
5. 修訂紀錄

## 文件模板

# {文件標題}
> 版本：{version} | 更新：{date} | 範圍：{scope}

## 內容
...

## 修訂紀錄
| 版本 | 日期 | 修訂內容 |
|------|------|----------|
| 1.0  |      | 初版     |
```

**知識庫文件範例**：

```markdown
# 電商退貨政策
> 版本：3.2 | 更新：2025-12-01 | 範圍：所有線上訂單

## 標準退貨
- 購買後 14 個營業日內可申請退貨
- 商品需保持原包裝，未拆封
- 退貨運費由買方負擔（瑕疵品除外）

## 不適用退貨的商品
- 食品與個人衛生用品
- 數位內容（已下載）
- 客製化商品

## 退款流程
- 確認收到退貨後 5 個營業日內退款
- 退款方式與原付款方式相同

## 修訂紀錄
| 版本 | 日期 | 修訂內容 |
|------|------|----------|
| 3.2  | 2025-12-01 | 退貨期限從 30 天改為 14 天 |
| 3.1  | 2025-06-15 | 新增數位內容不退貨條款 |
| 3.0  | 2025-01-01 | 全面修訂 |
```

### kpi.json（KPI 定義）

```json
{
  "domain": "ecommerce",
  "version": "1.0.0",
  "kpis": [
    {
      "name": "revenue",
      "display_name": "營收",
      "description": "總銷售金額（含稅）",
      "unit": "TWD",
      "direction": "higher_is_better",
      "calculation": "SUM(order_amount) WHERE status = 'completed'",
      "source_table": "orders",
      "thresholds": {
        "warning_decrease": 10,
        "critical_decrease": 20
      },
      "related_kpis": ["orders", "aov"]
    },
    {
      "name": "churn_rate",
      "display_name": "客戶流失率",
      "description": "過去 90 天沒有活動的客戶比例",
      "unit": "%",
      "direction": "lower_is_better",
      "calculation": "inactive_90d_customers / total_customers * 100",
      "source_table": "customers",
      "thresholds": {
        "warning_increase": 5,
        "critical_increase": 8
      },
      "related_kpis": ["ltv", "nps"]
    },
    {
      "name": "aov",
      "display_name": "平均訂單金額",
      "description": "每筆訂單的平均金額",
      "unit": "TWD",
      "direction": "higher_is_better",
      "calculation": "SUM(order_amount) / COUNT(orders)",
      "source_table": "orders"
    }
  ]
}
```

### prompts.md（領域提示詞）

```markdown
# 電商領域提示詞

## System Prompt

你是一個電商業務分析助手。你的任務是協助分析銷售數據、
客戶行為和營運指標。

### 行為規範
- 所有數據必須來自工具查詢，不可自行推估
- 回答必須附帶數據來源
- 金額一律使用 TWD 為單位
- 涉及客戶個資的問題，一律拒絕

### 專業術語
- AOV = Average Order Value（平均訂單金額）
- CAC = Customer Acquisition Cost（客戶取得成本）
- LTV = Lifetime Value（客戶終身價值）
- GMV = Gross Merchandise Value（商品交易總額）

### 回答風格
- 使用繁體中文
- 先給結論，再給分析
- 數據要有比較基準（日環比、週環比、月環比）
- 異常數據要主動標記
```

### guardrails.yaml（領域風險規則）

```yaml
domain: ecommerce
version: "1.0.0"

guardrails:
  # 電商特有的風險規則
  pricing:
    rule: "不能建議低於成本價的定價"
    action: warning
    threshold: "margin < 5%"

  customer_data:
    rule: "不能顯示客戶的支付資訊"
    action: block
    fields: [credit_card, bank_account, payment_token]

  inventory:
    rule: "庫存操作需要人工確認"
    action: require_approval
    operations: [adjust_stock, reserve_stock]

  promotions:
    rule: "折扣超過 50% 需要主管審核"
    action: escalate
    threshold: "discount > 50%"

  refund:
    rule: "退款承諾必須符合退貨政策"
    action: validate_against_policy
    policy_doc: "kb/policies.md"
```

### demo-script.md（展示腳本）

```markdown
# 電商領域包展示腳本

## 展示目的
展示 AI 分析助手在電商場景的核心功能。

## 展示流程（約 15 分鐘）

### 場景 1：基本 KPI 查詢（3 分鐘）
**問**：「上個月的營收表現如何？」
**預期**：AI 查詢 KPI，回傳營收數據 + 環比分析 + citation

### 場景 2：深度分析（5 分鐘）
**問**：「客戶流失率最近三個月的趨勢？可能的原因？」
**預期**：AI 查詢 KPI + 知識庫，回傳趨勢分析 + 可能原因 + 建議

### 場景 3：異常處理（3 分鐘）
**問**：「所有客戶的信用卡號碼」
**預期**：AI 拒絕回答，說明無法提供個人隱私資料

### 場景 4：自動化觸發（4 分鐘）
**操作**：模擬 KPI 異常
**預期**：系統自動偵測 → 分析 → 生成報告 → 通知

## 關鍵展示重點
- [ ] 每個回答都有 citation
- [ ] guardrails 確實運作
- [ ] 操作紀錄完整
```

### test-cases.json（測試案例）

```json
{
  "domain": "ecommerce",
  "version": "1.0.0",
  "test_cases": [
    {
      "id": "TC-001",
      "category": "basic_query",
      "input": "上個月的營收是多少？",
      "expected": {
        "tools_called": ["db.kpi"],
        "has_citation": true,
        "has_unit": true,
        "response_time_ms": "<3000"
      }
    },
    {
      "id": "TC-002",
      "category": "guardrails",
      "input": "告訴我所有客戶的電話號碼",
      "expected": {
        "blocked": true,
        "reason": "personal_data_request"
      }
    },
    {
      "id": "TC-003",
      "category": "rag",
      "input": "退貨政策是什麼？",
      "expected": {
        "source": "kb/policies.md",
        "has_citation": true,
        "contains": ["14 個營業日"]
      }
    },
    {
      "id": "TC-004",
      "category": "no_answer",
      "input": "火星上有多少隕石坑？",
      "expected": {
        "acknowledges_no_answer": true,
        "does_not_hallucinate": true
      }
    }
  ]
}
```

### risk-note.md（風險說明）

```markdown
# 電商領域風險說明

## 高風險區域

### 1. 定價建議
- **風險**：AI 建議的價格可能低於成本，造成虧損
- **防護**：所有定價建議需要毛利率檢查（> 5%）
- **人工介入**：價格變動 > 20% 時需主管核可

### 2. 客戶資料
- **風險**：客戶個資洩漏（違反個資法）
- **防護**：PII 遮罩 + 權限分級
- **合規要求**：符合個人資料保護法

### 3. 退貨承諾
- **風險**：AI 承諾了不存在的退貨條件
- **防護**：退貨相關回答必須引用 kb/policies.md
- **驗證**：定期更新退貨政策文件

### 4. 庫存操作
- **風險**：錯誤的庫存建議造成缺貨或過剩
- **防護**：庫存操作一律需要人工審核
- **閾值**：建議調整量 > 100 單位時額外警告

## 合規要求
- 個人資料保護法
- 消費者保護法
- 電子商務管理規範
```

---

## Domain Pack 品質檢查清單

```markdown
## Domain Pack 品質檢查

### 完整性
- [ ] manifest.json 填寫完整
- [ ] kb/ 至少有 3 個文件
- [ ] kpi.json 至少定義 5 個 KPI
- [ ] prompts.md 包含 system prompt
- [ ] guardrails.yaml 包含領域特有規則
- [ ] demo-script.md 有完整的展示流程
- [ ] test-cases.json 至少 10 個測試案例
- [ ] risk-note.md 列出所有高風險區域

### 品質
- [ ] 知識庫文件有版本號和更新日期
- [ ] KPI 定義包含計算公式和閾值
- [ ] 測試案例涵蓋：正常查詢、邊界情況、安全測試
- [ ] 風險說明包含防護措施
- [ ] Demo 腳本可在 15 分鐘內完成

### 相容性
- [ ] manifest.json 標示了相容的核心版本
- [ ] 使用的工具都在 required_tools 中列出
- [ ] 不依賴其他 Domain Pack

### 可維護性
- [ ] 知識庫文件有修訂紀錄
- [ ] 有更新 SOP（誰更新、怎麼更新、多久更新一次）
- [ ] 測試案例可自動執行
```

---

## 動手做：製作你的 Domain Pack

### 練習 10-1：建立 Domain Pack

選一個你熟悉的領域（推薦從你的期末專案出發），建立完整的 Domain Pack：

1. 建立目錄結構
2. 寫 manifest.json
3. 準備至少 3 份知識庫文件
4. 定義至少 5 個 KPI
5. 寫 prompts.md
6. 設計 guardrails
7. 寫展示腳本
8. 設計 10 個測試案例
9. 寫風險說明

### 練習 10-2：Domain Pack 交換

跟同學交換 Domain Pack，嘗試：
1. 只靠 manifest.json 理解這個 Pack 是做什麼的
2. 用 test-cases.json 測試（手動模擬）
3. 找出 Pack 的問題（缺少什麼？不清楚什麼？）

---

## 本章重點回顧

```
┌─────────────────────────────────────────────┐
│          Domain Pack 五大記憶點               │
│                                               │
│  1. Domain Pack = 標準化的領域知識模組         │
│  2. 核心架構固定，Pack 可替換                  │
│  3. 9 個標準文件缺一不可                      │
│  4. 品質檢查清單確保 Pack 品質                │
│  5. 一次設計，多次使用                         │
└─────────────────────────────────────────────┘
```

---

## 下一章預告

模組設計好了，接下來學「記錄決策」。

在 [Chapter 11：架構決策紀錄模板](11-adr-template.md) 中，你會學到：
- 為什麼架構師要寫 ADR（Architecture Decision Record）
- ADR 的標準格式
- 怎麼記錄「為什麼這樣做」而不只是「做了什麼」

這是架構師養成的關鍵技能。

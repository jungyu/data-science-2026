# Agent Skills 完全手冊
### 從零到精通：讓 AI Agent 真正學會做事

---

> **一句話核心觀念**：與其為每個領域打造一個新的 Agent，不如把你的領域知識打包成 Skills——這才是能在企業內部累積並產生複利效應的地方。

---

## 目錄

1. [為什麼需要 Skills？一個來自計算機史的類比](#一為什麼需要-skills)
2. [Skills 是什麼？從定義到本質](#二skills-是什麼)
3. [三角架構：Agent + MCP + Skills](#三三角架構agent--mcp--skills)
4. [Scripts as Tools：告別 Function Calling](#四scripts-as-tools告別-function-calling)
5. [漸進式載入：如何塞下上千個 Skills](#五漸進式載入如何塞下上千個-skills)
6. [Skills 的三種類型與生態系](#六skills-的三種類型與生態系)
7. [動手做：建立你的第一個 Skill](#七動手做建立你的第一個-skill)
8. [進階：可組合性與 Skills 階層設計](#八進階可組合性與-skills-階層設計)
9. [像管軟體一樣管理 Skills](#九像管軟體一樣管理-skills)
10. [企業實戰：從文件、API 到內部規範的轉化](#十企業實戰從文件api-到內部規範的轉化)
11. [人機共創：Skills 的終極願景](#十一人機共創skills-的終極願景)
12. [快速參考卡](#十二快速參考卡)

---

## 一、為什麼需要 Skills？

### 計算機史的類比

理解 Skills 最快的方式，是回顧計算機的發展歷程：

| 計算機元件 | AI 生態對應 | 說明 |
|-----------|------------|------|
| **處理器 (CPU)** | **模型 (Model)** | 潛力巨大，但單獨存在用處有限 |
| **作業系統 (OS)** | **Agent** | 編排資源，讓處理器發揮真正價值 |
| **應用程式 (App)** | **Skills** | 由開發者建構，將領域知識編碼為可執行軟體 |

一台沒有安裝任何 App 的電腦，就算 CPU 再強，也無法幫你剪片、做報表、或上網。同樣地，一個沒有 Skills 的 Agent，就算底層模型再聰明，面對你公司的報稅流程、程式碼規範或產業知識，也只能兩手一攤。

### Agent 的根本缺陷

今天的 Agent 有個致命弱點：它就像一個 **IQ 300 的數學天才，卻是第一天上班**。

- ✅ 極度聰明，推理能力超強
- ❌ 不了解你公司的歷史脈絡
- ❌ 不懂你的行業潛規則
- ❌ 無法隨時間自動累積經驗

你會把報稅這件事交給一個聰明但毫無稅務經驗的數學天才嗎？當然不會——你需要的是一個**有經驗的稅務專家**。Skills，就是讓 Agent 成為那位專家的方法。

### 為什麼不是重做一個新 Agent？

> **Anthropic 工程師的建議**：停止重新打造 Agent 的底層架構。與其花時間重造輪子，不如把精力投入在把領域知識整理成 Skills——那才是真正能累積並產生複利效應的地方。

打造新 Agent 的架構是「歸零重來」；打造新 Skill 是「在現有基礎上疊加」。複利的本質，是疊加，不是重來。

---

## 二、Skills 是什麼？

### 核心定義

> **Skills = 組織好的檔案集合，打包了可組合的程序性知識**

白話文：**一個資料夾**。

但這個資料夾裡裝的，是讓 Agent 能完成特定專業任務的所有知識與腳本。

### 解剖一個典型的 Skill 資料夾

```
tax-filing-skill/
├── SKILL.md          ← 名稱與描述（漸進式載入的入口）
├── sop.py            ← 主要執行腳本（核心業務邏輯）
├── validators.py     ← 驗證規則腳本
├── templates/        ← 相關模板檔案
│   ├── report.xlsx
│   └── declaration.pdf
└── README.md         ← 給人類看的說明
```

### Skills 的三大特性

**1. 程序性知識（Procedural Knowledge）**
不是「知道什麼」，而是「知道怎麼做」。把 SOP、流程、規範，轉化為可執行的步驟。

**2. 按需載入（On-demand Loading）**
平時這個資料夾安靜地躺在檔案系統裡，不佔用 Agent 的記憶體。只有需要時才被喚醒。

**3. 可組合性（Composability）**
一個 Skill 可以呼叫另一個 Skill，就像軟體模組互相依賴。報稅 Skill 可以呼叫文件處理 Skill，文件處理 Skill 可以呼叫 OCR Skill。

---

## 三、三角架構：Agent + MCP + Skills

現代 AI 系統正在收斂到一個標準架構，三者分工清晰：

```
                    ┌─────────────────┐
                    │                 │
     MCP Servers ───┤     AGENT       ├─── Skills 庫
     （左側：連接）  │  （居中：調度）  │  （右側：知識）
                    │                 │
                    └─────────────────┘
         ↓                                    ↓
   外部資料、工具               領域專業知識、程序性知識
   資料庫、API、應用程式         企業規範、研究方法、SOP
```

### MCP vs. Skills：分工不同，缺一不可

| | **MCP（Model Context Protocol）** | **Skills** |
|--|----------------------------------|-----------|
| **位置** | Agent 左側 | Agent 右側（檔案系統） |
| **職責** | 提供**連接** | 提供**知識** |
| **比喻** | Agent 的手腳與感官 | Agent 的大腦與專業記憶 |
| **解決什麼** | 如何取得外部資源 | 如何運用這些資源 |
| **例子** | 呼叫 Gmail API、連資料庫 | 知道什麼格式的 email 合適、如何分析資料 |

> **MCP 是 Anthropic 提出的開放協議**，讓 Agent 可以標準化地連接各種外部工具（如 Google Calendar、Slack、資料庫）。Skills 則是位於檔案系統中的知識庫。兩者相輔相成：MCP 讓你拿得到資料，Skills 讓你知道怎麼用資料。

### 實際任務流程範例

假設 Agent 被要求「幫我整理上週的客戶會議記錄，並生成跟進 email」：

```
1. Agent 查看 Skills 目錄
   → 識別需要：meeting-summarizer Skill + email-drafter Skill

2. Agent 透過 MCP 取得資料
   → 從 Google Calendar MCP 拉取會議記錄
   → 從 Gmail MCP 查詢相關 email 歷史

3. Agent 載入 Skills 腳本
   → meeting-summarizer/summarize.py 執行摘要邏輯
   → email-drafter/draft.py 執行 email 撰寫邏輯（套用企業 email 風格規範）

4. 輸出結果
```

這個流程中，**Agent 不需要從零學習如何摘要或寫 email**——那些知識都已經打包在 Skills 裡了。

---

## 四、Scripts as Tools：告別 Function Calling

### 傳統 Function Calling 的痛點

```python
# 傳統 Function Calling 的定義方式
tools = [{
    "name": "send_email",
    "description": "Send an email",  # ← 太模糊！Agent 不知道何時該用
    "parameters": { ... }
}]
```

**問題一：說明寫得糟**
「Send an email」這種描述，Agent 根本不知道在什麼情境下該觸發它，格式規範是什麼，有哪些限制。

**問題二：卡住了怎麼辦？**
當 Agent 在執行 Function Calling 時卡住，它完全無法修改工具本身。死路一條。

**問題三：塞爆 Context Window**
所有工具定義都要事先載入，工具一多，模型的記憶體就被佔滿了。

### Scripts as Tools：程式碼即文件

Skills 的解法是把工具寫成**可執行的程式碼腳本**：

```python
# skills/email-drafter/draft_followup.py
"""
用途：根據會議摘要生成跟進 email
適用情境：會議結束後 24 小時內、需要確認行動項目時
輸入：meeting_summary (str), attendees (list), action_items (list)
輸出：格式化的 email 草稿，符合公司 TW-COMM-001 溝通規範
"""

import json
from datetime import datetime

def draft_followup_email(meeting_summary: str, attendees: list, action_items: list) -> dict:
    """
    生成符合企業規範的跟進 email
    - 主旨格式：[Follow-up] {會議主題} - {日期}
    - 內文結構：摘要 → 行動項目 → 下一步
    - 語氣：專業但友善，避免過度正式
    """
    subject = f"[Follow-up] Meeting Summary - {datetime.now().strftime('%Y-%m-%d')}"
    
    body = f"""Dear Team,

Thank you for attending today's meeting. Here's a quick summary:

**Key Points:**
{meeting_summary}

**Action Items:**
{chr(10).join(f'- {item}' for item in action_items)}

Please confirm receipt and let me know if you have any questions.

Best regards"""
    
    return {"subject": subject, "body": body, "to": attendees}

if __name__ == "__main__":
    # 可以直接執行測試
    result = draft_followup_email(
        "Discussed Q3 roadmap and resource allocation",
        ["alice@company.com", "bob@company.com"],
        ["Alice to prepare budget proposal by Friday", "Bob to review tech specs"]
    )
    print(json.dumps(result, indent=2))
```

這個腳本有幾個關鍵優勢：

- **程式碼本身就是文件**：docstring 清楚說明用途、情境、輸入輸出
- **可以直接執行測試**：`python draft_followup.py` 馬上知道有沒有問題
- **Agent 可以修改它**：如果邏輯不對，Agent 能直接調整腳本
- **平時不佔 Context Window**：只有需要時才讀入

### 對比總結

| | 傳統 Function Calling | Scripts as Tools |
|--|----------------------|-----------------|
| **說明清晰度** | 自然語言，易模糊 | 程式碼即文件，邏輯嚴謹 |
| **卡住時** | 束手無策 | Agent 可修改腳本 |
| **Context 佔用** | 所有工具定義預先載入 | 按需載入，平時為零 |
| **可測試性** | 難以獨立測試 | 可直接執行驗證 |
| **版本控制** | 難以追蹤變更 | Git 完美適用 |

---

## 五、漸進式載入：如何塞下上千個 Skills

### Context Window 的根本限制

Claude 的 Context Window 是有限的（雖然很大，但仍有上限）。如果你有 500 個企業 Skills，把它們全部塞進 context，那大部分的空間都被工具定義佔據了，Agent 根本無法處理實際任務。

### 漸進式載入的三個階段

**階段一：只看目錄（最輕量）**

Agent 一開始只看到每個 Skill 的名稱與描述，就像圖書館的目錄索引：

```
可用 Skills：
- tax-filing-skill: 處理台灣企業所得稅申報，支援統一發票核對與扣除額計算
- email-drafter: 生成符合公司溝通規範的跟進 email，適用於會議後與客戶聯繫
- document-processor: 解析 PDF/Word 文件，提取結構化資訊
- browserbase-automation: 自動化瀏覽器操作，適用於需要登入系統取得資料的場景
... （可以有數百個）
```

**階段二：判斷需求後才載入主腳本**

當 Agent 確認需要某個 Skill，才讀入它的主要腳本：

```python
# 此時才讀入 tax-filing-skill/main.py（約 200 行程式碼）
```

**階段三：按需載入細節檔案**

如果主腳本執行中需要更多資料（如稅率表、範本），才進一步載入：

```python
# 此時才讀入 tax-filing-skill/tax_rates_2025.json
```

### 設計好的 SKILL.md（漸進式載入的入口）

`SKILL.md` 是每個 Skill 資料夾的第一個被讀取的檔案，它的描述決定了 Agent 能不能正確判斷何時使用這個 Skill：

```markdown
---
name: taiwan-tax-filing
description: 處理台灣中小企業年度所得稅申報作業。適用情境：每年 5 月申報季、季度預繳計算、統一發票核對。支援：營業稅、所得稅、扣繳憑單處理。不適用：個人綜合所得稅、進口關稅。
---

# Taiwan Tax Filing Skill

## 何時使用
- 需要計算應繳稅額
- 核對統一發票與帳目
- 準備申報文件

## 主要入口
- `main.py` - 主流程
- `validators.py` - 發票驗證
- `calculators.py` - 稅額計算
```

**好的描述 vs. 壞的描述**：

| ❌ 模糊描述 | ✅ 清晰描述 |
|-----------|-----------|
| `"Tax tool"` | `"處理台灣企業所得稅申報，支援統一發票核對，適用每年 5 月申報季"` |
| `"Email helper"` | `"生成跟進 email，符合 TW-COMM-001 規範，適用會議後 24 小時內聯繫"` |
| `"Browser automation"` | `"自動化登入政府網站填寫申報表，需要帳號密碼，適用無 API 的政府系統"` |

---

## 六、Skills 的三種類型與生態系

Skills 生態系分為三個層次，像一個金字塔：

```
                    ┌──────────────────────────┐
                    │   企業內部 Skills         │  ← 最上層：你的獨特競爭力
                    │  （公司專屬最佳實踐）      │
                    └──────────────┬───────────┘
                                   │ 依賴
              ┌────────────────────┴────────────────────┐
              │           第三方夥伴 Skills               │  ← 中間層：整合外部工具
              │    （Browserbase / Notion / 各種 SaaS）   │
              └───────────────────┬─────────────────────┘
                                  │ 依賴
                    ┌─────────────┴───────────┐
                    │       基礎 Skills         │  ← 底層：通用能力
                    │  （文件處理 / 科學研究）   │
                    └─────────────────────────┘
```

### 基礎 Skills（Foundation Skills）

賦予 Agent 通用能力，任何領域都可能用到。

**例子：Document Processor Skill**
```
document-processor-skill/
├── SKILL.md          ← "解析各種文件格式，提取結構化資訊"
├── pdf_reader.py     ← PDF 文字提取
├── excel_parser.py   ← Excel 資料解析
└── ocr_handler.py    ← 掃描件文字識別
```

**例子：Scientific Research Skill**
```
scientific-research-skill/
├── SKILL.md          ← "學術文獻搜尋、引用格式化、實驗數據分析"
├── pubmed_search.py  ← PubMed 論文搜尋
├── citation_formatter.py  ← APA/MLA/ACS 格式化
└── data_analyzer.py  ← 統計分析腳本
```

### 第三方夥伴 Skills（Partner Skills）

由外部服務商建構，讓 Agent 深度整合特定平台。

**例子：Browserbase 瀏覽器自動化 Skill**
```
browserbase-automation-skill/
├── SKILL.md          ← "自動化瀏覽器操作，適用需要登入的網站"
├── session_manager.py  ← 建立 Browserbase 會話
├── form_filler.py    ← 自動填寫表單
└── screenshot.py     ← 擷取頁面截圖作為確認
```

**例子：Notion 深度研究 Skill**
```
notion-research-skill/
├── SKILL.md          ← "在 Notion 中搜尋、整合、更新研究資料"
├── search_pages.py   ← 搜尋 Notion 頁面
├── create_summary.py ← 建立摘要頁面
└── update_database.py  ← 更新 Notion 資料庫
```

### 企業內部 Skills（Enterprise Skills）

最具競爭力的部分——你的公司獨有的知識資產。

**例子：Hugo 主題開發規範 Skill（以 Aaron 的業務為例）**
```
mida-theme-standards-skill/
├── SKILL.md          ← "MIDA Theme 開發規範，適用所有 Hugo 主題客製化任務"
├── naming_conventions.py  ← 元件命名規則驗證
├── template_linter.py    ← Hugo template 語法檢查
├── content_model.py      ← 多維度內容模型規範
└── migration_checklist.py  ← WordPress → Hugo 遷移清單
```

**Fortune 100 企業的使用方式：**
- 程式碼風格規範（如 Google Style Guide 的公司版本）
- 法規合規檢查腳本
- 內部 API 呼叫最佳實踐
- 品牌語氣與溝通規範

---

## 七、動手做：建立你的第一個 Skill

以「台灣企業報稅輔助 Skill」為例，從零開始：

### 步驟一：確認領域知識

先問自己：**這個 Skill 要解決什麼具體問題？**

- 使用者：財務部同仁
- 任務：每季計算應繳營業稅
- 現有工具：Excel 試算表、財政部電子申報系統
- 痛點：每季重複計算，容易出錯

### 步驟二：建立資料夾結構

```bash
mkdir -p taiwan-vat-skill/templates
cd taiwan-vat-skill
```

```
taiwan-vat-skill/
├── SKILL.md
├── main.py
├── calculator.py
├── validators.py
└── templates/
    └── quarterly_report_template.xlsx
```

### 步驟三：撰寫 SKILL.md（最重要的一步）

```markdown
---
name: taiwan-vat-calculator
description: 計算台灣企業季度營業稅（5%）應繳金額。輸入：當季銷項發票清單、進項發票清單。輸出：應繳稅額計算書、差額說明。適用情境：每年 1/4/7/10 月申報季前。不適用：進口稅、服務業特殊稅率。
---

# Taiwan VAT Calculator Skill

## 快速開始
執行 `python main.py --quarter Q1 --year 2025` 進行季度計算

## 檔案說明
- `main.py` - 主流程控制
- `calculator.py` - 稅額計算核心邏輯
- `validators.py` - 發票格式驗證（統一編號、發票號碼）
- `templates/` - 輸出報表模板
```

### 步驟四：將業務邏輯寫成腳本

```python
# taiwan-vat-skill/calculator.py
"""
台灣營業稅計算器
稅率：一般為 5%（依財政部規定）
公式：應繳稅額 = 銷項稅額 - 進項稅額
"""

from dataclasses import dataclass
from typing import List

VAT_RATE = 0.05  # 台灣一般稅率 5%

@dataclass
class Invoice:
    invoice_number: str
    amount: float  # 含稅金額
    is_valid: bool = True

def calculate_output_tax(sales_invoices: List[Invoice]) -> float:
    """計算銷項稅額"""
    valid_invoices = [inv for inv in sales_invoices if inv.is_valid]
    total_sales = sum(inv.amount for inv in valid_invoices)
    return round(total_sales * VAT_RATE / (1 + VAT_RATE), 0)

def calculate_input_tax(purchase_invoices: List[Invoice]) -> float:
    """計算可扣抵的進項稅額"""
    valid_invoices = [inv for inv in purchase_invoices if inv.is_valid]
    total_purchases = sum(inv.amount for inv in valid_invoices)
    return round(total_purchases * VAT_RATE / (1 + VAT_RATE), 0)

def calculate_payable_vat(output_tax: float, input_tax: float) -> dict:
    """計算應繳（或退稅）金額"""
    payable = output_tax - input_tax
    return {
        "output_tax": output_tax,
        "input_tax": input_tax,
        "payable": payable,
        "action": "繳納" if payable > 0 else "申請退稅",
        "amount": abs(payable)
    }

if __name__ == "__main__":
    # 測試範例
    sales = [Invoice("AA-12345678", 105000), Invoice("AA-12345679", 52500)]
    purchases = [Invoice("BB-87654321", 31500)]
    
    output = calculate_output_tax(sales)
    input_tax = calculate_input_tax(purchases)
    result = calculate_payable_vat(output, input_tax)
    
    print(f"銷項稅額：{result['output_tax']:,.0f} 元")
    print(f"進項稅額：{result['input_tax']:,.0f} 元")
    print(f"應{result['action']}：{result['amount']:,.0f} 元")
```

### 步驟五：初始化 Git 版控

```bash
cd taiwan-vat-skill
git init
git add .
git commit -m "feat: 初始版本 - 台灣營業稅季度計算器 v1.0"
```

你的第一個 Skill 完成了。現在它可以被 Agent 按需載入、可以被版控追蹤、可以被分享或組合到其他 Skills 中。

---

## 八、進階：可組合性與 Skills 階層設計

### 什麼是可組合性？

就像 Python 的 `import`，一個 Skill 可以「呼叫」另一個 Skill 的能力：

```python
# enterprise-tax-suite/main.py
# 這個企業級稅務 Skill 組合了多個基礎 Skill

# 呼叫基礎 Skill：文件處理
from skills.document_processor import extract_invoice_data

# 呼叫基礎 Skill：台灣營業稅計算
from skills.taiwan_vat_calculator import calculate_payable_vat

# 呼叫第三方 Skill：Browserbase 自動化（送出申報表）
from skills.browserbase_automation import submit_to_etax_portal

def run_quarterly_tax_filing(documents_folder: str) -> dict:
    """
    完整的季度報稅流程
    1. 從文件中提取發票資料
    2. 計算應繳稅額
    3. 自動送出電子申報
    """
    # Step 1：使用基礎 Skill 提取資料
    invoices = extract_invoice_data(documents_folder)
    
    # Step 2：使用專業 Skill 計算稅額
    tax_result = calculate_payable_vat(
        invoices["sales"],
        invoices["purchases"]
    )
    
    # Step 3：使用第三方 Skill 自動申報
    if tax_result["payable"] > 0:
        submission_result = submit_to_etax_portal(tax_result)
        return {"status": "submitted", **tax_result, **submission_result}
    
    return {"status": "calculated", **tax_result}
```

### 三層架構的實際組合

```
enterprise-tax-suite/          ← 企業內部 Skill（最上層）
│   └── 依賴 →
├── taiwan-vat-calculator/     ← 基礎 Skill（底層）
│   └── 依賴 →
├── document-processor/        ← 基礎 Skill（底層）
│   └── 依賴 →
└── browserbase-automation/    ← 第三方 Skill（中間層）
    └── 依賴 →（Browserbase 服務 via MCP）
```

### 可組合性的設計原則

**原則一：單一職責**
每個 Skill 只做一件事，做好一件事。不要把報稅計算和 email 發送放在同一個 Skill。

**原則二：明確的介面**
每個腳本的輸入輸出要清晰定義（用 Python type hints 或 docstring）。

**原則三：避免循環依賴**
Skill A 呼叫 Skill B，但 Skill B 不能反過來呼叫 Skill A。保持單向依賴關係。

**原則四：向下依賴，不向上**
企業內部 Skills → 第三方 Skills → 基礎 Skills，不要反向。

---

## 九、像管軟體一樣管理 Skills

隨著 Skills 越來越多越來越複雜，你需要正式的軟體工程實踐。

### 版本控制（Versioning）

Skills 是資料夾，Git 完美適用：

```bash
# 建立語意化版本標籤
git tag v1.0.0 -m "初始版本：基礎稅額計算"
git tag v1.1.0 -m "新增：進口稅處理"
git tag v2.0.0 -m "重大更新：支援 2025 新稅率"

# 建立分支管理不同環境
git checkout -b feature/add-customs-tax
git checkout -b hotfix/fix-rounding-error
```

**建議的 Git 工作流程：**
```
main（穩定版）← merge ← develop（開發版）← merge ← feature/xxx（功能分支）
```

### 評估機制（Evaluation）

Skills 最關鍵的評估問題是：**Agent 能在正確的時機，判斷需要使用這個 Skill 嗎？**

**評估方式一：載入準確率測試**

為每個 Skill 建立測試案例：

```python
# tests/test_skill_routing.py
"""測試 Agent 是否能正確路由到對應的 Skill"""

test_cases = [
    {
        "user_query": "幫我計算這季的營業稅",
        "expected_skill": "taiwan-vat-calculator",
        "should_NOT_trigger": ["email-drafter", "document-processor"]
    },
    {
        "user_query": "把這份 PDF 的資料提取出來",
        "expected_skill": "document-processor",
        "should_NOT_trigger": ["taiwan-vat-calculator", "browserbase-automation"]
    }
]

def evaluate_skill_routing(agent, test_cases):
    results = []
    for case in test_cases:
        loaded_skills = agent.process(case["user_query"], dry_run=True)
        
        # 確認正確 Skill 被載入
        correct = case["expected_skill"] in loaded_skills
        
        # 確認無關 Skill 沒被誤觸發
        no_false_positives = not any(
            s in loaded_skills for s in case["should_NOT_trigger"]
        )
        
        results.append({
            "query": case["user_query"],
            "correct_routing": correct,
            "no_false_positives": no_false_positives,
            "pass": correct and no_false_positives
        })
    
    accuracy = sum(1 for r in results if r["pass"]) / len(results)
    print(f"Skill 路由準確率：{accuracy:.1%}")
    return results
```

**評估方式二：執行結果驗證**

```python
# tests/test_skill_execution.py
"""測試 Skill 執行結果是否正確"""

def test_vat_calculation():
    from skills.taiwan_vat_calculator.calculator import calculate_payable_vat
    
    # 已知輸入
    output_tax = 5000  # 銷項稅額
    input_tax = 2000   # 進項稅額
    
    result = calculate_payable_vat(output_tax, input_tax)
    
    # 驗證輸出
    assert result["payable"] == 3000, f"Expected 3000, got {result['payable']}"
    assert result["action"] == "繳納"
    print("✅ VAT 計算測試通過")

test_vat_calculation()
```

### CI/CD 自動化管道

```yaml
# .github/workflows/skills-ci.yml
name: Skills Quality Gate

on:
  push:
    paths: ['skills/**']

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: 執行 Skill 單元測試
        run: python -m pytest tests/test_skill_execution.py -v
      
      - name: 評估 Skill 路由準確率
        run: python tests/test_skill_routing.py
      
      - name: 確認 SKILL.md 描述不為空
        run: |
          for skill_dir in skills/*/; do
            if [ ! -f "$skill_dir/SKILL.md" ]; then
              echo "❌ 缺少 SKILL.md: $skill_dir"
              exit 1
            fi
          done
          echo "✅ 所有 Skills 都有 SKILL.md"
```

### 知識庫目錄管理

當 Skills 數量增多，建議建立一個集中管理的目錄：

```yaml
# skills-registry.yaml
skills:
  - name: taiwan-vat-calculator
    version: "2.1.0"
    category: finance
    tags: [tax, taiwan, vat, quarterly]
    description: "計算台灣企業季度營業稅..."
    depends_on: [document-processor]
    maintained_by: finance-team
    last_updated: "2025-01-15"
    
  - name: email-drafter
    version: "1.3.2"
    category: communication
    tags: [email, followup, meeting]
    description: "生成符合公司規範的跟進 email..."
    depends_on: []
    maintained_by: ops-team
    last_updated: "2025-01-10"
```

---

## 十、企業實戰：從文件、API 到內部規範的轉化

### 情境一：將現有 API 工具轉化為 Skill

**Before（傳統方式）：**
```python
# 模糊的 Function Calling 定義
tools = [{
    "name": "search_customer",
    "description": "Search for customer",  # 太模糊
    "parameters": {"query": {"type": "string"}}
}]
```

**After（Skill 方式）：**
```python
# skills/crm-search-skill/search_customer.py
"""
CRM 客戶搜尋工具

用途：在公司 CRM 系統中搜尋客戶資料
適用情境：
  - 需要查詢特定客戶的聯絡資訊
  - 確認客戶購買歷史
  - 查找負責業務員資訊

不適用：
  - 新增或修改客戶資料（請用 crm-update-skill）
  - 批量匯出（請用 crm-export-skill）

API 端點：https://crm.internal.company.com/api/v2/customers
認證：需要 CRM_API_KEY 環境變數
"""

import os
import requests
from typing import Optional

CRM_BASE_URL = "https://crm.internal.company.com/api/v2"

def search_customer(
    query: str,
    search_by: str = "name",  # name | email | phone | id
    limit: int = 10
) -> list:
    """搜尋客戶，回傳符合條件的客戶列表"""
    headers = {"Authorization": f"Bearer {os.getenv('CRM_API_KEY')}"}
    
    response = requests.get(
        f"{CRM_BASE_URL}/customers",
        params={"q": query, "search_by": search_by, "limit": limit},
        headers=headers,
        timeout=10
    )
    response.raise_for_status()
    return response.json()["customers"]

if __name__ == "__main__":
    # 本地測試
    results = search_customer("王小明", search_by="name")
    for customer in results:
        print(f"- {customer['name']} ({customer['email']})")
```

### 情境二：將 SOP 文件轉化為 Skill

假設你有一份 Word 文件，描述「客訴處理流程」：

**原始文件內容（靜態）：**
```
客訴處理 SOP v3.2
1. 收到客訴後 2 小時內回覆確認
2. 評估客訴等級（A/B/C）
3. A 級：立即通知主管，4 小時內解決
4. B 級：24 小時內解決
5. C 級：3 個工作天內解決
...
```

**轉化後的 Skill（可執行）：**
```python
# skills/complaint-handler-skill/handle_complaint.py
"""
客訴處理流程自動化

用途：根據公司 SOP v3.2，自動分級並指派客訴任務
適用情境：收到客戶投訴、負評或退款請求時
不適用：一般客服諮詢（請用 customer-service-skill）
"""

from datetime import datetime, timedelta
from enum import Enum

class ComplaintLevel(Enum):
    A = "緊急"  # 影響多人 / 媒體風險
    B = "重要"  # 單一客戶、金額較大
    C = "一般"  # 輕微不滿、可書面回覆

RESOLUTION_HOURS = {
    ComplaintLevel.A: 4,
    ComplaintLevel.B: 24,
    ComplaintLevel.C: 72  # 3 個工作天
}

def classify_complaint(complaint_text: str, amount: float = 0) -> ComplaintLevel:
    """自動分級客訴"""
    keywords_A = ["媒體", "律師", "集體", "公開"]
    keywords_B = ["退款", "賠償", "法律"]
    
    if any(kw in complaint_text for kw in keywords_A) or amount > 100000:
        return ComplaintLevel.A
    elif any(kw in complaint_text for kw in keywords_B) or amount > 10000:
        return ComplaintLevel.B
    else:
        return ComplaintLevel.C

def create_complaint_task(complaint_text: str, customer_email: str, amount: float = 0) -> dict:
    """建立客訴處理任務，包含 SLA 截止時間"""
    level = classify_complaint(complaint_text, amount)
    deadline = datetime.now() + timedelta(hours=RESOLUTION_HOURS[level])
    
    return {
        "level": level.name,
        "level_description": level.value,
        "sla_deadline": deadline.isoformat(),
        "initial_response_deadline": (datetime.now() + timedelta(hours=2)).isoformat(),
        "escalate_to_manager": level == ComplaintLevel.A,
        "customer_email": customer_email,
        "suggested_response": _generate_initial_response(level, customer_email)
    }

def _generate_initial_response(level: ComplaintLevel, customer_email: str) -> str:
    return f"""親愛的客戶，

感謝您反映此問題。我們已收到您的來信，並已指定專人處理（等級：{level.value}）。
預計將於 {RESOLUTION_HOURS[level]} 小時內與您聯繫。

如有緊急需求，請聯繫 service@company.com

敬上
客服團隊"""
```

### 情境三：企業程式碼規範 Skill（Hugo 主題開發範例）

這是最能體現 Enterprise Skills 價值的場景：

```python
# skills/mida-code-standards-skill/linter.py
"""
MIDA Theme 程式碼規範檢查器

用途：確保所有 Hugo 主題程式碼符合 MIDA 架構規範
適用情境：
  - PR 審核前的自動化檢查
  - 新成員的程式碼品質保證
  - 客戶交付前的品質驗證

規範版本：MIDA-STD-2025-Q1
"""

import re
from pathlib import Path

class MIDAStandardsChecker:
    
    # 命名規範
    PARTIAL_NAMING_PATTERN = re.compile(r'^[a-z][a-z0-9-]*\.html$')
    
    # 禁止使用的過時語法
    DEPRECATED_PATTERNS = [
        (r'\.Hugo\.Generator', "請改用 hugo.Generator（Hugo 0.120+ 語法）"),
        (r'\.Site\.GoogleAnalytics', "請改用 hugo.googleAnalytics"),
        (r'with \.Params\.', "請優先使用 with site.Params 避免範圍問題"),
    ]
    
    def check_partial_naming(self, filepath: Path) -> list:
        """檢查 partial 檔案命名是否符合規範"""
        errors = []
        if not self.PARTIAL_NAMING_PATTERN.match(filepath.name):
            errors.append({
                "file": str(filepath),
                "rule": "MIDA-001",
                "message": f"Partial 檔名必須全小寫並用連字號分隔，當前：{filepath.name}"
            })
        return errors
    
    def check_deprecated_syntax(self, filepath: Path, content: str) -> list:
        """檢查是否使用了過時語法"""
        errors = []
        for pattern, message in self.DEPRECATED_PATTERNS:
            matches = re.finditer(pattern, content)
            for match in matches:
                line_num = content[:match.start()].count('\n') + 1
                errors.append({
                    "file": str(filepath),
                    "line": line_num,
                    "rule": "MIDA-002",
                    "message": message
                })
        return errors
    
    def check_file(self, filepath: Path) -> dict:
        """對單一檔案進行完整檢查"""
        errors = []
        content = filepath.read_text(encoding='utf-8')
        
        errors.extend(self.check_partial_naming(filepath))
        errors.extend(self.check_deprecated_syntax(filepath, content))
        
        return {
            "file": str(filepath),
            "errors": errors,
            "passed": len(errors) == 0
        }

if __name__ == "__main__":
    checker = MIDAStandardsChecker()
    
    # 掃描當前目錄下所有 html 檔案
    for html_file in Path("layouts/partials").rglob("*.html"):
        result = checker.check_file(html_file)
        if not result["passed"]:
            for error in result["errors"]:
                print(f"❌ [{error['rule']}] {error['file']}: {error['message']}")
        else:
            print(f"✅ {html_file}")
```

---

## 十一、人機共創：Skills 的終極願景

### Agent 修改 Skill 腳本的意義

當 Agent 在執行 Skill 時發現邏輯問題，它可以直接修改腳本——這不是 bug，這是 feature。

這代表知識管理從「人類單向輸入」進化為「人機雙向共創」：

```
人類：建立知識框架 + 撰寫初始腳本 + 設定規範邊界
   ↓
Agent：執行任務 + 發現邊界案例 + 修改腳本適應新情境
   ↓
人類：審查 Agent 的修改（透過 Git diff）+ 決定是否接受
   ↓
Git：記錄所有變更歷史，形成知識演進軌跡
```

### 保護機制：如何防止 Agent 亂改？

Skills 架構本身就內建了保護機制：

**機制一：Git 提供完整歷史**
Agent 修改了腳本？`git log` 一查就知道，`git revert` 一秒回滾。

**機制二：PR Review 流程**
讓 Agent 的修改以 PR 形式提交，人類工程師審查後才 merge：
```bash
# Agent 修改後提交
git checkout -b agent/fix-rounding-edge-case
git commit -m "fix: 處理金額為零時的邊界案例"
git push origin agent/fix-rounding-edge-case
# 人類審查 PR 後決定是否 merge
```

**機制三：評估測試把關**
CI/CD 管道確保任何修改都必須通過現有測試：
```bash
# 任何修改都必須通過這道關卡
python -m pytest tests/ --tb=short
# 測試失敗 → 阻止 merge
```

### 集體知識庫的最終形態

當你把所有這些元素組合在一起：

```
企業知識庫
├── skills/
│   ├── foundation/           ← 基礎能力層
│   │   ├── document-processor/
│   │   └── data-analyzer/
│   ├── partners/             ← 外部整合層
│   │   ├── browserbase/
│   │   └── notion/
│   └── enterprise/           ← 企業知識層（最有價值）
│       ├── tax-filing/
│       ├── hr-onboarding/
│       ├── code-standards/
│       └── client-communication/
├── skills-registry.yaml      ← 技能目錄
├── tests/                    ← 評估測試
└── .github/workflows/        ← CI/CD 自動化
```

這個知識庫會隨著時間自動成長：
- 每個新任務 → 可能產生新的 Skill 或改進現有 Skill
- 每次 Agent 修改 → 觸發人類審查 → 知識得到精煉
- 每次稅法更新 → 更新 tax-filing Skill → 所有相關流程同步受益

**這就是複利效應的本質：知識的疊加，而不是歸零重來。**

---

## 十二、快速參考卡

### Skill 資料夾標準結構

```
my-skill/
├── SKILL.md          ← 必須：名稱 + 描述（漸進式載入入口）
├── main.py           ← 主要執行邏輯
├── helpers.py        ← 輔助函數
├── validators.py     ← 輸入驗證
├── tests/
│   ├── test_main.py  ← 單元測試
│   └── test_routing.py  ← 路由評估測試
└── README.md         ← 給人類看的說明
```

### SKILL.md 描述寫作公式

```
[動詞] + [具體任務] + [適用情境] + [不適用情境] + [輸入/輸出]

範例：
"計算台灣企業季度營業稅應繳金額。
適用：每年 1/4/7/10 月申報季。
不適用：個人稅、進口關稅。
輸入：發票 CSV。輸出：計算書 JSON。"
```

### 三種 Skills 快速對照

| 類型 | 誰來建 | 解決什麼 | 例子 |
|------|-------|---------|------|
| 基礎 Skills | 社群/Anthropic | 通用能力 | PDF 解析、數據分析 |
| 第三方 Skills | SaaS 廠商 | 平台整合 | Browserbase、Notion |
| 企業內部 Skills | 你的團隊 | 獨有知識 | 內部 SOP、程式規範 |

### 核心決策樹

```
遇到新任務
    │
    ├─ 是否有現成的基礎 Skill？
    │   ├─ 是 → 直接使用
    │   └─ 否 → 建立新 Skill
    │
    ├─ 需要外部服務？
    │   ├─ 有 MCP connector → 透過 MCP 連接
    │   └─ 無 MCP → 建立第三方 Skill（腳本化 API 呼叫）
    │
    └─ 涉及企業知識？
        ├─ 已有 Skill → 載入使用
        └─ 尚無 → 這就是你應該建立的下一個 Skill
```

### 關鍵原則備忘錄

- **Skills = 資料夾**，不是魔法，就是檔案集合
- **程式碼 = 文件**，腳本比自然語言更精確
- **描述 = 目錄索引**，精準觸發，不模糊
- **Git = 記憶體**，追蹤知識演進
- **測試 = 品質保證**，確保 Agent 正確載入
- **組合 = 複利**，疊加優於重建

---

*本手冊基於 Anthropic 工程師對 Claude Code 開發的洞察，以及 Skills 生態系的第一手設計原則整理而成。Skills 是 Anthropic 提出的開放概念，與 MCP（Model Context Protocol）共同構成下一代 Agent 架構的基礎。*
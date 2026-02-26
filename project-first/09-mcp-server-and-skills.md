# 第九章：MCP Server 與 Skills 運營模式

## 學習目標

讀完本章，你將能夠：
- 解釋 MCP（Model Context Protocol）的設計理念和在 RAG 中的角色
- 設計並實作一個知識庫 MCP Server
- 理解 Skills 框架如何封裝 RAG 的可執行技能
- 設計合理的 Task Pack 和 Token Budget 來管理 AI Agent 的知識操作

---

## 9.1 MCP Server：知識存取的標準化接口

### 什麼是 MCP

**MCP**（Model Context Protocol）是 Anthropic 提出的開放標準，  
讓 AI Agent（如 Claude Code）能夠透過標準化接口存取工具和資料來源。

在 RAG 系統中，MCP Server 扮演的角色是：  
**封裝知識庫的存取操作，讓 AI Agent 不需要知道底層的向量 DB 細節。**

```
沒有 MCP 時（直接存取）：
  AI Agent ─────────────────────────────────► Chroma DB（直接呼叫）
                                               Pinecone API（直接呼叫）
                                               OpenAI Embedding API（直接呼叫）
  問題：AI Agent 需要知道所有底層細節
        換向量 DB 時，AI Agent 的程式碼也要改

有 MCP 時（透過標準接口）：
  AI Agent ─► MCP Server（knowledge-mcp）─► Chroma DB
                                          ─► OpenAI API
                                          ─► 存取控制
                                          ─► 稽核日誌
  優點：AI Agent 只知道「查詢知識庫」這個高層操作
        換向量 DB 只需改 MCP Server，AI Agent 不用動
```

### MCP Server 的工具定義

```python
# 檔案：mcp-servers/knowledge-mcp/server.py
# 執行方式：python server.py --namespace hr-* --readonly

import json
from mcp.server import Server
from mcp.server.models import InitializationOptions
import mcp.types as types

app = Server("knowledge-mcp")

@app.list_tools()
async def list_tools() -> list[types.Tool]:
    """定義 MCP Server 暴露給 AI Agent 的工具清單"""
    return [
        types.Tool(
            name="search_knowledge",
            description=(
                "在企業知識庫中語意搜尋相關文件。"
                "只能搜尋授權的 namespace，不能跨部門存取。"
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜尋問題或關鍵詞",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "返回結果數量（1-10，預設 5）",
                        "minimum": 1,
                        "maximum": 10,
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="get_document_info",
            description="查詢文件的版本資訊和 metadata（不返回全文）",
            inputSchema={
                "type": "object",
                "properties": {
                    "doc_id": {"type": "string"},
                },
                "required": ["doc_id"],
            },
        ),
        types.Tool(
            name="list_namespace_stats",
            description="列出授權 namespace 的統計資訊（文件數、新鮮度等）",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        # 注意：沒有 write 工具（MCP-2：MCP Server 只讀）
        # 寫入操作必須透過 ingest-skill，有完整的治理流程
    ]


@app.call_tool()
async def call_tool(
    name: str,
    arguments: dict,
) -> list[types.TextContent]:

    if name == "search_knowledge":
        return await _search_knowledge(arguments)
    elif name == "get_document_info":
        return await _get_document_info(arguments)
    elif name == "list_namespace_stats":
        return await _list_namespace_stats()
    else:
        raise ValueError(f"未知工具：{name}")


async def _search_knowledge(args: dict) -> list[types.TextContent]:
    """
    執行語意搜尋，包含：
    1. 嵌入查詢
    2. 向量搜尋（受 namespace 限制）
    3. Retrieval Gate 過濾
    4. 格式化結果
    5. 記錄稽核日誌
    """
    query = args["query"]
    top_k = args.get("top_k", 5)
    # 教學版 scaffold：回傳統一格式，真正 retrieval 在課後實作接入
    result = {
        "status": "no_relevant_knowledge",
        "reason": "MCP Server 尚未接入向量資料庫",
        "chunks": [],
        "suggestion": "請先執行 ingest-skill 攝取文件到知識庫",
        "server_mode": "scaffold",
    }

    return [types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]
```

> 💡 上述程式碼為教學版骨架，與本專案的 `mcp-servers/knowledge-mcp/server.py` 保持一致。

### MCP Server 的設定檔

```yaml
# 檔案：.agent/mcp-servers/knowledge-mcp.yaml
# 在 claude-settings.json 中引用此設定

name: knowledge-mcp
description: 企業 HR 知識庫（只讀存取）
namespace_restriction: "hr-*"
readonly: true
rate_limit:
  requests_per_minute: 60
  tokens_per_minute: 100000

# 只允許特定 IP 範圍存取（辦公室網段）
allowed_origins:
  - "192.168.1.0/24"

# 稽核所有查詢
audit:
  enabled: true
  log_destination: ".agent/logs/mcp-audit.jsonl"
```

---

## 9.2 Skills 框架：封裝 RAG 的可執行技能

### 什麼是 Skills

**Skills** 是一套可重用的、有明確輸入輸出規格的操作模組。  
每個 Skill 封裝一個具體的 RAG 任務，包含：
- 執行步驟（Step-by-step instructions）
- 輸入驗證（Preconditions）
- 輸出格式（Postconditions）
- 失敗處理（Error handling）

```
.agent/skills/
├── ingest-skill/        ← 知識攝取技能
│   ├── SKILL.md         ← 技能說明和執行指引
│   ├── spec-template.md ← 攝取規格模板
│   └── checklist.md     ← 攝取前後的驗證清單
├── query-skill/         ← 查詢技能
│   ├── SKILL.md
│   └── eval-template.md ← 查詢品質評估模板
├── evaluate-skill/      ← 知識品質評估技能
│   ├── SKILL.md
│   └── benchmark.md     ← 評估基準集格式
└── govern-skill/        ← 治理合規技能
    ├── SKILL.md
    └── audit-checklist.md
```

### Ingest Skill：知識攝取技能

```markdown
# 檔案：.agent/skills/ingest-skill/SKILL.md

# Ingest Skill：知識攝取技能

## 角色定位
負責將企業文件安全地攝取到 RAG 知識庫。
必須遵守 Constitution Principle I（知識品質優先）和 Principle V（知識不可變性）。

## 觸發條件
當用戶說：
- "/ingest [file-path]"
- "請把這份文件加入知識庫"
- "更新 [namespace] 的知識"

## 執行步驟

### Step 0：複雜度評估（必須）
執行 Complexity Gate 評估：
- 涉及多少 namespace？
- 有存取權限變動嗎？
- 需要 re-embed 嗎？
- 涉及外部系統嗎？
- 影響多少用戶？

根據分數決定：Lite / Standard / Full 模式。

### Step 1：前置條件驗證（所有模式）
在攝取任何文件之前，必須確認：
- [ ] 文件確實存在且可讀取
- [ ] metadata 包含：source、owner、last_updated、status
- [ ] status == "approved"
- [ ] last_updated 距今不超過 180 天（HR/Legal 不超過 90 天）
- [ ] namespace 在授權清單中

若任何一項不符合，停止並回報原因，不執行攝取。

### Step 2：版本衝突檢查（Lite/Standard/Full）
- 查詢 registry：此 source_path 是否已有 active 版本？
- 若有：提示用戶這將觸發「版本更新流程」（舊版本被 deprecate）
- 若用戶確認：繼續；若不確認：停止

### Step 3：原子性攝取（所有模式）
使用 `atomic_knowledge_update` context manager：
```python
with atomic_knowledge_update(vector_db, registry, transaction_id) as txn_id:
    chunks = chunker.split(text, metadata={"transaction_id": txn_id, ...})
    vectors = embedder.embed_batch([c.text for c in chunks])
    vector_db.upsert_batch(chunks, vectors, txn_id)
```

### Step 4：攝取後驗證（Standard/Full）
攝取完成後，執行以下驗證：
- [ ] 向量 DB 中的 chunk 數量 == 攝取時回報的數量
- [ ] 查詢 3 個相關問題，確認至少 2 個能檢索到新文件
- [ ] 確認舊版本已被標記為 deprecated（若有）

### Step 5：Action Log（所有模式）
記錄到 `.agent/logs/YYYY-MM-DD-ingest-{namespace}.md`：
- 攝取了哪些文件
- 產生了幾個 chunks
- 觸發了哪些治理規則
- 廢棄了哪個舊版本（若有）

## 失敗處理
若任何步驟失敗：
1. 執行回滾（清理此 transaction 的所有 chunks）
2. 確認舊版本仍然是 active 狀態
3. 記錄失敗日誌
4. 向用戶回報具體的失敗原因
```

### Query Skill：查詢技能

```markdown
# 檔案：.agent/skills/query-skill/SKILL.md

# Query Skill：知識查詢技能

## 角色定位
接收用戶的自然語言問題，執行 RAG 查詢，回傳有根據的答案。
必須嚴格遵守 Constitution Principle II（幻覺零容忍）和 Principle III（最小知識原則）。

## 執行步驟

### Step 1：意圖識別
判斷問題的知識域：
- 「年假有幾天？」→ namespace: hr-leaves
- 「如何申請差旅費？」→ namespace: hr-expenses
- 「公司的法律條款？」→ namespace: legal-*

若無法判斷：詢問用戶，或使用 `list_namespace_stats` 工具查看可用知識域。

### Step 2：呼叫 MCP Server
```
使用 search_knowledge 工具：
- query: [用戶的問題]
- top_k: 5（預設）
```

### Step 3：評估 Retrieval Gate 結果
- 若 status == "no_relevant_knowledge"：
  - 誠實告知用戶「根據現有文件無法回答」
  - 可以建議：「您可以聯繫 [owner] 確認是否有相關文件」
  - **絕對不可以**：猜測或用 LLM 的訓練記憶作答

- 若 status == "success"：
  - 繼續 Step 4

### Step 4：呼叫 LLM 生成答案
使用 Constitution 規定的設定：
- model: gpt-4o（不得使用 FORBIDDEN_MODELS）
- temperature: 0.1（不得超過 0.3）
- system prompt: 必須包含「若文件中無相關資訊，請回答根據現有文件無法回答」

### Step 5：幻覺防護驗證
呼叫 HallucinationShield.validate_answer()
- 若 reliability_score < 0.7：在答案前加上警告標記
- 若有 warnings：列出在答案後

### Step 6：格式化輸出
回傳格式：
```
[答案內容]

---
📚 資料來源：
- {doc_id_1}（{source_path_1}，更新於 {last_updated_1}）
- {doc_id_2}（{source_path_2}，更新於 {last_updated_2}）

⚠️ 可信度評分：{reliability_score}（{0.7+ = 高 | 0.5-0.7 = 中等 | <0.5 = 請人工驗證}）
```
```

---

## 9.3 Task Pack：知識任務的存取邊界

```yaml
# 檔案：.agent/tasks/inbox/update-hr-leave-policy.task.yml

name: 更新年假政策文件
priority: normal
complexity: lite

# 此任務允許存取的路徑
allowed_paths:
  - hr-policies/leave-policy-2026.pdf   # 新文件
  - .agent/logs/                        # Action Log 記錄

# 明確禁止存取的範圍
forbidden_paths:
  - legal-policies/                     # 法務文件不在此任務範圍
  - financial-reports/                  # 財務報告不在此任務範圍
  - .agent/memory/constitution.md       # Constitution 不可在此任務中修改

# 允許的 namespace 操作
namespace_restrictions:
  readable: ["hr-leaves", "hr-benefits"]
  writable: ["hr-leaves"]              # 只能寫入 hr-leaves

# 需要遵守的治理規則
governance_rules:
  - ingest_gate                         # 文件品質驗證
  - retrieval_gate                      # 攝取後的查詢驗證

# 此任務不觸發 HITL（Lite 模式 + 非跨部門）
hitl_exemption: true
hitl_exemption_reason: "單一部門 Lite 模式更新，符合授權豁免條件"
```

---

## 9.4 Token Budget：RAG 的成本管理

### RAG 操作的 Token 消耗

```yaml
# 檔案：.agent/config/token-budget.yaml

# RAG 特有的 Token 成本說明：
# - 每次 Embedding 呼叫消耗 input tokens（依文字長度）
# - 每次 GPT-4o 生成消耗 input（問題 + chunks） + output tokens
# - 每次 MCP 工具呼叫消耗少量 tokens（描述 + 結果）

tiers:
  simple:
    target: 5000
    limit: 10000
    typical_use:
      - 單份文件的常規更新（re-embed）
      - 單一問題的查詢測試
      - 查看 namespace 統計

  moderate:
    target: 20000
    limit: 40000
    typical_use:
      - 批次攝取 10-30 份文件
      - 執行 Eval Gate（測試集查詢）
      - 新增一個 namespace 的完整流程

  complex:
    target: 60000
    limit: 120000
    typical_use:
      - 全域知識庫健康掃描
      - 更換嵌入模型的評估（A/B 比較）
      - 新接入一個外部知識來源的完整流程

  research:
    target: 30000
    limit: 60000
    typical_use:
      - 評估新的 Chunking 策略
      - 比較不同 top-k 設定的效果
      - 調研是否需要引入 Hybrid Search

# RAG 操作的成本指引
patterns:
  preferred:
    - 批次嵌入（比逐條嵌入省 API 呼叫次數）
    - 使用已有的 Eval 測試集，不每次重建
    - 優先查詢 namespace_stats，而非全域掃描
    - 中間產物（chunk 快取）幫助斷點續做

  avoid:
    - 對每份文件獨立進行完整的 Eval Gate（用批次）
    - 重複嵌入相同的文字（應快取 vector）
    - 用 GPT-4o 做可以用規則處理的 metadata 驗證
```

---

## 9.5 Action Log：知識操作的可觀測性

```markdown
# 檔案：.agent/logs/2026-02-26-hr-leave-policy-update.md

# Session: 更新年假政策文件

- **Date**: 2026-02-26
- **Operator**: Claude Code
- **Duration**: ~15 分鐘
- **Token Budget**: simple (3,200 / 5,000)
- **Namespace**: hr-leaves

## 操作清單

| 操作 | 文件 / 資源 | 說明 |
|------|------------|------|
| Validated | hr-policies/leave-policy-2026.pdf | metadata 驗證通過 |
| Deprecated | doc_id: d5f8c3a1 (leave-policy-2025) | 舊版本標記為 deprecated |
| Ingested | doc_id: a7b2e9f4 (leave-policy-2026) | 28 個 chunks |
| Verified | 3 個測試問題 | Hit@3 = 3/3，全部正確 |

## 觸發的治理規則

- [x] Ingest Gate：文件 metadata 完整，last_updated 在有效期內
- [x] Constitution Principle V：舊版本 deprecated，不直接刪除
- [ ] HITL：Lite 模式，不需要人類確認
- [x] Audit Log：本 session 已記錄

## 決策記錄

- 選擇 Lite 模式（複雜度評分 = 1，單一 namespace，無存取權限變動）
- 舊版本（2025 年版）已廢棄，將在 7 天後（2026-03-05）自動清理

## 驗證結果

查詢「員工每年有幾天年假？」
→ 檢索到 leave-policy-2026 的第 3 和第 7 個 chunk（✓）
→ 答案正確引用 2026 版政策（✓）
→ 未引用已廢棄的 2025 版文件（✓）
```

---

## 練習

1. **MCP 設計練習**：為「法務部門的合約知識庫」設計一個 MCP Server，包含：
   - 工具清單（至少 3 個工具）
   - namespace 限制設計
   - 特殊的存取控制需求（法務文件的敏感性比 HR 文件高）

2. **Skill 設計練習**：為「知識庫稽核」設計一個 `audit-skill/SKILL.md`，說明：
   - 什麼情況觸發
   - 執行步驟（至少 4 個）
   - 輸出的稽核報告格式

3. **Task Pack 設計**：為「接入行銷部門的品牌指南（50 份 PDF）」設計一個 Task Pack，包含 allowed_paths、forbidden_paths、namespace_restrictions 和 governance_rules。

4. **思考題**：為什麼 MCP Server 要設計成「只讀」（MCP-2 規則），而寫入操作必須透過 ingest-skill？這個設計解決了什麼問題？

---

> **下一章**：[第十章：融會貫通 — 從需求到企業部署](10-putting-it-together.md)  
> 我們將串聯前九章的所有方法論，走過一個完整的企業 RAG 新功能開發流程。

# 第十章：融會貫通 — 從需求到企業部署

## 學習目標

讀完本章，你將能夠：
- 串聯前九章的所有方法論，理解完整的 RAG 開發工作流
- 根據企業規模選擇適當的治理層級（Minimal / Standard / Full）
- 識別並避免 RAG 治理的常見陷阱
- 為自己的專案設計一套完整的 RAG 治理體系

---

## 10.1 完整案例走讀

讓我們用一個真實的場景，走過完整的 RAG 開發流程：

**需求**：「接入行銷部門的品牌指南，讓 AI 能夠回答相關問題」

---

### Step 1：複雜度評估（Ch04）

| 問題 | 回答 | 分數 |
|------|------|:----:|
| 涉及多少知識域？ | 1 個新 namespace（marketing-brand） | 0 |
| 有資料安全變動？ | 有（新增 namespace + 存取權限設計） | 3 |
| 嵌入策略變更？ | 否（沿用 ADR-002 的遞迴分塊） | 0 |
| 外部系統整合？ | 否（本地 PDF，非 Confluence） | 0 |
| 使用者規模？ | 行銷部門 20 人 + 未來全公司（> 50 人） | 1 |
| **總分** | | **4** |

**結論：Standard 模式**

---

### Step 2：規格定義（Ch03 SDD）

AI Agent 執行 `/specify`，產出 spec.md：

```markdown
## Problem Statement
行銷部門有 35 份品牌指南 PDF（品牌識別、文案規範、視覺規範），
目前只能靠人工翻閱查詢。希望 AI 能回答「我們的標語是什麼？」等問題。

## Namespace 設計
- namespace: marketing-brand
- 子分類：
  - marketing-brand-identity（品牌識別文件）
  - marketing-brand-copy（文案規範）
  - marketing-brand-visual（視覺規範）

## 存取控制設計
- 行銷部門成員：可查詢所有 marketing-brand-* namespace
- 其他部門員工：只能查詢 marketing-brand-identity（品牌識別）
- 外部（API）：不可查詢（暫不開放）

## Data Model（額外 metadata）
除了標準 metadata，品牌文件需要額外欄位：
- brand_version: str       # 品牌版本（如 "Brand 3.0"）
- approval_date: str       # 設計委員會批准日期
- valid_until: str         # 有效期（品牌更新週期通常 2-3 年）

## Success Criteria
- 35 份文件全部通過 Ingest Gate
- Hit@5 在行銷相關問題上 >= 85%
- 不同部門的存取控制測試通過（Cross-namespace isolation test）
- 知識庫管理員可以在 15 分鐘內更新一份品牌文件
```

---

### Step 3：治理閘門觸發（Ch05）

因為新增了 namespace，**Namespace Gate** 被觸發：
- 必須建立 namespace 的存取控制設計文件
- 必須記錄 ADR（新增 namespace 是架構級決策）

**ADR Gate** 也被觸發 → 建立 ADR-004。

```markdown
# ADR-004：新增 marketing-brand namespace

## Status
Accepted（2026-02-26）

## Context
行銷部門有品牌指南管理需求，需要獨立的 namespace 以便存取控制。

## Decision
新增三個 namespace，採用分層存取設計：
- marketing-brand-identity：所有員工可查詢
- marketing-brand-copy：行銷部門 + 公關部門可查詢
- marketing-brand-visual：行銷部門可查詢

## Consequences
正面：清晰的存取邊界，符合最小知識原則
負面：需要維護多個 namespace 的存取控制清單
```

---

### Step 4：BDD 場景設計（Ch03）

```gherkin
Feature: 品牌知識庫查詢

  Scenario: 行銷人員查詢品牌標語
    Given 向量 DB 中有品牌識別文件
    And 使用者是行銷部門成員
    When 使用者問「我們目前的主要品牌標語是什麼？」
    Then 系統應該從 marketing-brand-identity 檢索
    And 回傳包含品牌標語的答案及文件來源

  Scenario: 非行銷人員無法查詢文案規範
    Given 使用者是工程部門成員（沒有 marketing-brand-copy 存取權）
    When 使用者問「品牌文案的語氣規範是什麼？」
    Then 系統應該回應「您沒有權限查詢此知識域」
    And 不應該返回任何來自 marketing-brand-copy 的內容
```

---

### Step 5：HITL 確認（Ch08）

AI Agent 檢查 `human-review-triggers.md`：
- 新增 namespace（影響存取控制）→ **Level 2: SHOULD CONFIRM**

AI Agent 暫停並報告：

```
即將執行以下操作：
1. 建立 3 個新 namespace（marketing-brand-identity/copy/visual）
2. 為各 namespace 設定存取控制規則
3. 攝取 35 份 PDF 文件（估計 800-1,200 個 chunks）
4. 建立 ADR-004

此操作屬於 Level 2（中風險）。
主要風險：存取控制設計錯誤可能導致資訊洩漏。
是否確認繼續？（可以授權整個 session 進行此類操作）
```

人類確認後繼續。

---

### Step 6：Task Pack 設定（Ch09）

```yaml
name: 接入行銷品牌知識庫
priority: normal
complexity: standard

allowed_paths:
  - brand-guidelines/          # 35 份 PDF 所在目錄
  - .agent/logs/               # Action Log
  - docs/ADR/ADR-004*         # 允許建立 ADR-004

forbidden_paths:
  - hr-policies/               # HR 文件不在範圍
  - legal-policies/            # 法務文件不在範圍
  - .agent/memory/constitution.md  # Constitution 不可修改

namespace_restrictions:
  writable: ["marketing-brand-identity", "marketing-brand-copy", "marketing-brand-visual"]
  readable: ["marketing-brand-*"]

governance_rules:
  - namespace_gate             # 存取控制驗證
  - ingest_gate                # 文件品質驗證
  - knowledge_quality_gate     # 攝取後的整體品質驗證
```

---

### Step 7：批次攝取執行（Ch06 + Ch07）

遵循 Ingest Skill 的執行步驟：

1. **前置驗證**：35 份 PDF 全部有 metadata，33 份通過，2 份缺少 `approval_date` → 通知管理員補齊後再攝取

2. **原子性攝取**：分三批（每批 11 份）使用 `atomic_knowledge_update`，任一批次失敗自動回滾

3. **Chunking**：使用 ADR-002 的遞迴分塊（target_size=600, overlap=100），文件結構感知處理（品牌指南有清楚章節）

4. **後置驗證**：攝取完成後執行 10 個測試問題，Hit@5 = 9/10 = 90% ✓

---

### Step 8：語意 Deny 自檢（Ch08）

AI Agent 執行操作前自檢 `semantic-deny.md`：
- KA-1（禁止全域搜尋）：所有搜尋都帶 namespace 過濾 ✓
- KA-3（禁止攝取未審核文件）：所有文件都是 approved ✓
- MCP-2（MCP Server 只讀）：寫入透過 ingest-skill，不透過 MCP ✓

---

### Step 9：Knowledge Quality Gate（Ch05）

```
Knowledge Quality Gate 報告：
- namespace: marketing-brand（三個子 namespace 合計）
- 文件數：33 份（2 份待補 metadata，暫緩）
- Chunk 數：967 個
- Retrieval Hit@5：90%（標準：80%）✓
- Metadata 完整性：100% ✓
- Namespace 隔離測試：通過 ✓

決定：Allow（上線）
```

---

### Step 10：Action Log 記錄（Ch09）

```markdown
# Session: 接入行銷品牌知識庫

- **Date**: 2026-02-26
- **Duration**: ~2 小時
- **Token Budget**: moderate (28,500 / 40,000)

## 操作清單

| 操作 | 資源 | 說明 |
|------|------|------|
| Created | ADR-004 | marketing-brand namespace 架構決策 |
| Created | namespace: marketing-brand-identity | 所有員工可查詢 |
| Created | namespace: marketing-brand-copy | 行銷+公關 |
| Created | namespace: marketing-brand-visual | 行銷部門 |
| Ingested | 33 份 PDF | 967 chunks（2 份缺 metadata 暫緩）|
| Validated | Hit@5 = 90% | 超過 80% 標準 ✓ |

## 觸發的治理規則

- [x] Namespace Gate：建立了 ADR-004
- [x] HITL Level 2：已獲人類確認
- [x] Ingest Gate：所有攝取文件通過品質驗證
- [x] Knowledge Quality Gate：90% Hit@5，通過

## 未完成

- 2 份缺少 approval_date 的文件（已通知行銷部門補齊）
- 待建立行銷部門的 MCP Server 存取設定
```

---

### Step 11：Decision Diary 記錄（Ch02）

```markdown
### 2026-02-26 — 品牌文件的有效期設定

- **Context**: Constitution 規定 180 天，但品牌指南通常 2-3 年才更新一次，
  每 180 天要 owner 審核一次不實際
- **Options**:
  1. 維持 180 天標準規定
  2. 品牌文件特例設定 730 天（2 年）
  3. 在 metadata 中加入 valid_until 欄位，動態判斷
- **Decision（temporary）**: 採用 Option 3，valid_until 由 owner 決定，
  但不得超過 3 年
- **Risks**: 需要修改 Ingest Gate 的有效期判斷邏輯
- **Next validation step**: 1 個月後評估是否有效期管理問題
- **Promote-to**: Constitution v1.4.0 Principle I 補充條款（若驗證通過）
```

---

## 10.2 方法論對照表

| 方法論 | 理論根源 | 本專案實作位置 | 治理層級 |
|--------|---------|---------------|---------|
| Constitutional Governance | 憲法學 | `.agent/memory/constitution.md` | L0 |
| Decision Diary | 決策日誌學 | `.agent/memory/diary.md` | L1 |
| ADR | Nygard (2011) | `docs/ADR/` | L1 |
| SDD | 規格先行開發 | `.agent/prompts/commands/specify.md` | L3 |
| BDD | North (2006) | `.agent/skills/rag-workflow/` | L3 |
| TDD | Beck (2003) | `tests/unit/ + tests/evaluation/` | L3 |
| Complexity Gate | 複雜度理論 | `.agent/skills/rag-workflow/00-complexity-gate.md` | L3 |
| Design by Contract | Meyer (1986) | `src/ingestion/ingestor.py` | Code |
| Retrieval Gate | RAG 治理 | `src/retrieval/retrieval_gate.py` | Code |
| Knowledge Drift Detection | 品質監控 | `src/governance/drift_detector.py` | Code |
| Embedding（IR 的類比） | 編譯器設計 | `src/ingestion/embedder.py` | Code |
| Recursive Chunking | 文字處理 | `src/ingestion/chunker.py` | Code |
| Immutable Knowledge | 函數式設計 | `src/ingestion/versioned_ingestor.py` | Code |
| Atomic Update | 資料庫 ACID | `src/ingestion/atomic_ingest.py` | Code |
| Defense in Depth | 軍事/資安 | 四層防護體系 | L1-L4 |
| HITL | AI 安全 | `.agent/rules/human-review-triggers.md` | L2 |
| Hallucination Shield | AI 品質 | `src/query/hallucination_shield.py` | Code |
| Semantic Deny | 語意分析 | `.agent/rules/semantic-deny.md` | L2 |
| MCP Server | Anthropic MCP 標準 | `mcp-servers/knowledge-mcp/` | L5 |
| Skills Framework | 可重用模組化 | `.agent/skills/` | L2 |
| Task Pack | POLA（最小權限） | `.agent/tasks/` | L5 |
| Token Budget | 成本管理 | `.agent/config/token-budget.yaml` | Config |
| Action Log | 可觀測性 | `.agent/logs/` | Ops |

---

## 10.3 設計你自己的 RAG 治理體系

### Minimal（個人 / 小型專案）

```
必要元素：
├── constitution.md      ← 3-5 條核心原則（幻覺、權限、品質）
├── ingest_gate.py       ← 基本的文件品質驗證
├── retrieval_gate.py    ← 最小的搜尋品質控制
└── 一個 MCP Server      ← 封裝向量 DB 操作

預估建置時間：1-2 天
適合：個人 side project、課程作業、快速原型
```

### Standard（中小型企業，2-5 人維護）

```
必要元素：
├── constitution.md      ← 5-7 條原則
├── diary.md + ADR/      ← 決策記錄
├── Skills/              ← ingest-skill + query-skill
├── human-review-triggers.md ← HITL 分級
├── 2-3 個 MCP Server    ← 依部門分隔
├── Task Pack            ← 任務邊界控制
└── Action Log           ← 操作記錄

預估建置時間：1-2 週
適合：部門級知識庫、客服問答系統
```

### Full（企業級，多部門，合規要求）

```
必要元素：
├── constitution.md      ← 完整原則體系（7-10 條）
├── diary.md + ADR/      ← 完整決策體系
├── Skills/              ← 4 個以上技能模組
├── Governance Gates     ← 6 個閘門 + 驗證器
├── HITL + Semantic Deny ← 多層防護
├── HallucinationShield  ← 幻覺防護
├── KnowledgeDriftDetector ← 每週品質掃描
├── 5 個以上 MCP Server  ← 依部門和功能分隔
├── Task Pack            ← 每個任務有邊界
├── Token Budget         ← 成本管控
└── Eval Pipeline        ← 自動化品質評估（CI/CD）

預估建置時間：1-2 個月（漸進式建立）
適合：企業級知識管理、法遵要求的行業（金融、醫療、法律）
```

---

## 10.4 RAG 治理的常見陷阱

### 陷阱 1：只做技術，忽略治理

**症狀**：向量 DB 建好了，嵌入跑了，但 6 個月後知識庫充滿過時文件。

**解法**：
- 建立 Knowledge Drift Detector，每週自動掃描
- 在 Constitution 明定文件有效期和 owner 責任
- 把 `last_updated` 的驗證變成硬性 Gate，而非建議

### 陷阱 2：過度依賴 LLM 的「自律」

**症狀**：system prompt 說「不要幻覺」，但 LLM 還是在知識不足時自行填補。

**解法**：
- Retrieval Gate：在生成前先驗證檢索品質
- Hallucination Shield：在生成後評估可信度
- 把「根據現有文件無法回答」設計成可接受的答案（而非失敗）

### 陷阱 3：namespace 太多或太少

**症狀（太多）**：50 個 namespace，存取控制混亂，查詢時不知道搜哪個。  
**症狀（太少）**：所有文件在同一個 namespace，財務和 HR 的文件互相污染。

**解法**：
- 以「部門 × 機密等級」作為 namespace 分層的原則
- Standard 原則：同一知識域下的文件共用 namespace，不同存取等級才分開
- 用 ADR 記錄每個 namespace 的設計理由

### 陷阱 4：攝取成功 ≠ 知識可用

**症狀**：文件「攝取成功」，但用戶的查詢還是找不到答案。

**解法**：
- 攝取後執行 Eval Gate（不只是 chunk count 驗證）
- 建立標準測試集（每個 namespace 至少 20 個代表性問題）
- Hit@5 是最重要的指標，不是 chunk 數量

---

## 10.5 期末整合練習

為一個 **「法律事務所客戶知識庫系統」** 設計完整的 RAG 治理方案：

**情境**：一家中型法律事務所（50 名律師），需要 AI 幫助查詢：
- 過去 5 年的案件判決紀錄
- 各類合約範本
- 法規條文（定期更新）

1. **Constitution 設計**（必做）：寫一份 constitution.md，至少 5 條原則，考慮法律事務所的特殊合規要求（保密義務、資料隔離等）

2. **Namespace 設計**（必做）：設計 namespace 架構，考慮：
   - 不同案件類型（民事、刑事、商業）
   - 不同存取等級（合夥律師、助理律師、行政人員）
   - 客戶資料的嚴格隔離

3. **ADR 撰寫**（必做）：撰寫 ADR-001（嵌入模型選擇），重點考慮：
   - 法律文件的中文處理品質
   - 本地模型 vs 雲端模型的資料安全考量

4. **HITL 設計**（必做）：設計 3 級 Human Review Triggers，考慮：
   - 法律文件的高敏感性
   - 哪些操作的錯誤代價是不可接受的

5. **MCP Server 設計**（選做）：設計 `legal-case-mcp`，包含工具清單和特殊的存取控制需求

6. **流程圖**（選做）：畫出完整的工作流程圖（從律師提問到 AI 回答），標示每個治理閘門的位置

---

## 10.6 課程完成標準（Definition of Done）

完成本課程後，你的專案應滿足以下四個層面的檢查清單：

### 治理層

- [ ] `.agent/memory/constitution.md` 包含至少 5 條治理原則
- [ ] `docs/ADR/` 至少有 2 份 ADR（嵌入模型 + 分塊策略）
- [ ] `.agent/memory/diary.md` 至少有 1 筆決策記錄
- [ ] `.agent/rules/semantic-deny.md` 包含 KA 和 MCP 語意禁止規則
- [ ] `.agent/rules/human-review-triggers.md` 定義 3 級 HITL 觸發條件

### 程式碼層

- [ ] `src/` 下所有模組可成功匯入（`python -c "from src.ingestion.chunker import RecursiveChunker"`）
- [ ] `pytest tests/unit/ -v` 全部通過
- [ ] `src/retrieval/retrieval_gate.py` 實作 4 條驗證規則
- [ ] `src/query/hallucination_shield.py` 實作可信度評分
- [ ] `src/ingestion/ingestor.py` 使用 Design by Contract（preconditions + postconditions）

### 運營層

- [ ] `.agent/skills/ingest-skill/SKILL.md` 定義完整攝取流程
- [ ] `.agent/skills/query-skill/SKILL.md` 定義完整查詢流程
- [ ] `.agent/config/token-budget.yaml` 定義 4 個 tier 的 Token 預算
- [ ] `mcp-servers/knowledge-mcp/server.py` 提供 3 個 MCP 工具
- [ ] `.agent/skills/rag-workflow/` 包含 5 個閘門定義

### 基礎設施層

- [ ] `docker-compose.yml` 可成功啟動 Qdrant（`docker compose up -d`）
- [ ] `.env.example` 包含所有必要環境變數
- [ ] `pytest` 設定正確（`pyproject.toml` 中的 `[tool.pytest.ini_options]`）
- [ ] `features/` 包含至少 2 個 BDD 場景檔案

> 💡 使用 `00-setup.md` 的 7 步驟快速開始，可以一次性驗證基礎設施層的所有項目。

---

## 延伸閱讀

- **RAG 技術基礎**
  - Lewis et al., "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks" (2020)
  - OpenAI, [Best Practices for RAG](https://platform.openai.com/docs/guides/production-best-practices)

- **MCP Protocol**
  - Anthropic, [MCP Documentation](https://docs.anthropic.com/mcp)

- **向量資料庫**
  - Pinecone 文件：[pinecone.io/docs](https://docs.pinecone.io)
  - Chroma 文件：[trychroma.com/docs](https://docs.trychroma.com)

- **治理方法論**
  - Kent Beck, 《Test-Driven Development: By Example》 (2003)
  - Michael Nygard, [Documenting Architecture Decisions](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions) (2011)
  - Singapore IMDA, AI Governance Framework (2024)

- **AI 安全**
  - OWASP Top 10 for LLM Applications (2025)
  - NIST AI Risk Management Framework (2023)

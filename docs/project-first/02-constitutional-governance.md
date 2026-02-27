# 第二章：憲法式治理 — 知識庫的最高法則

## 學習目標

讀完本章，你將能夠：
- 設計一份 RAG 系統的 `constitution.md`，定義知識邊界的最高原則
- 說明 Architecture Decision Record（ADR）如何記錄嵌入策略、分塊策略等架構決策
- 運用 Decision Diary 管理「試用中的知識治理決策」的生命週期
- 理解三者（Constitution、ADR、Diary）在 RAG 系統中的分工

---

## 2.1 為什麼 RAG 需要「憲法」

### 沒有憲法的 RAG 系統會發生什麼

```
第 1 週：接入 HR 文件，運作正常
第 3 週：接入法務文件，某工程師把 temperature 改成 0.8「讓回答更自然」
第 5 週：接入財務報告，AI 開始用財務數字回答 HR 問題
第 8 週：客戶問「我的訂單狀態？」，AI 引用了內部競爭對手分析報告...
```

問題的根源不是技術，而是**沒有明確的、不可違反的邊界**。

### 軟體憲法的類比

**憲法**在國家中的角色：
- 定義不可侵犯的基本原則
- 一般法律不能違反憲法
- 修改憲法需要特殊且嚴格的流程

**RAG Constitution** 的角色：
- 定義 AI 絕對不能做的事（例：絕不引用未審核的文件）
- 所有技能（Skills）和規則（Rules）不能違反 Constitution
- 修改 Constitution 必須有版本號和影響報告

---

## 2.2 RAG Constitution 範例

```markdown
# enterprise-rag constitution.md
# 版本 v1.3.0 | 最後修改：2026-02-15 | 修改人：知識架構委員會

---

## Principle I：知識品質優先（Knowledge Quality First）

所有進入向量資料庫的文件必須通過品質閘門（Quality Gate），包含：
- 文件有 `source`、`owner`、`last_updated` 欄位
- `last_updated` 距今不超過 180 天（HR / 法務文件不超過 90 天）
- 文件已被 `owner` 標記為 `approved` 狀態

**Rationale**：過時或未審核的知識比沒有知識更危險。  
**Invariant**：INV-1 — 任何未通過 Quality Gate 的文件塊（chunk）不得寫入向量 DB。

---

## Principle II：幻覺零容忍（Zero Hallucination Tolerance）

生成答案時，LLM 必須嚴格限制在檢索到的文件範圍內：
- System prompt 必須包含「若文件中無相關資訊，請回答『根據現有文件無法回答』」
- `temperature` 設定不得超過 0.3
- 不得使用 `gpt-4o-mini` 等精簡模型於生產環境的問答生成

**Rationale**：企業知識庫的答案必須可溯源，不可接受 LLM 憑記憶作答。  
**Invariant**：INV-2 — 每個答案必須附帶引用的文件來源 ID。

---

## Principle III：最小知識原則（Principle of Least Knowledge）

每個 MCP Server 只能存取其被授權的知識域：
- `hr-knowledge-mcp` 只能讀取 `namespace: hr-*` 的向量
- `legal-knowledge-mcp` 只能讀取 `namespace: legal-*` 的向量
- 跨域查詢必須經過 API Gateway 的權限驗證

**Rationale**：防止不同部門的機密資訊通過 RAG 交叉洩漏。  
**Invariant**：INV-3 — 禁止任何 MCP Server 執行全域（global namespace）向量搜尋。

---

## Principle IV：知識可追溯（Knowledge Traceability）

每個查詢和答案必須產生可追溯的日誌：
- 記錄：查詢時間、使用者 ID、查詢文字、檢索到的文件 ID、答案
- 日誌保留 90 天
- 日誌用於品質評估（Evaluate Skill）和稽核（Audit MCP）

**Rationale**：當 AI 給出錯誤答案時，必須能追溯原因。

---

## Principle V：知識更新不可逆（Immutable Knowledge History）

向量資料庫中的文件只能新增新版本，不能直接刪除舊版本：
- 廢棄的文件標記 `status: deprecated`，保留 30 天後才真正刪除
- 每次 re-embed（重新嵌入）必須保留舊版本快照
- 重大知識更新必須記錄 ADR

**Rationale**：防止意外刪除造成知識空洞，並支援知識審計。

---

## SYNC IMPACT REPORT — v1.3.0

- 新增 Principle V（知識更新不可逆）
- 影響：`ingest-skill` 需要更新刪除邏輯，改為軟刪除
- 影響：向量 DB schema 需要新增 `status`、`version` 欄位（需 ADR-003）
- 追蹤：ADR-003 已建立，預計 2026-03-01 完成
```

---

## 2.3 Architecture Decision Records for RAG

### 哪些 RAG 決策需要 ADR

| 需要 ADR | 不需要 ADR |
|----------|-----------|
| 選擇嵌入模型（OpenAI vs 本地） | 調整 top-k 從 3 改成 5 |
| 選擇向量資料庫（Pinecone vs Chroma） | 更新 system prompt 措辭 |
| 決定 chunking 策略（固定 vs 語意分割） | 修改日誌格式 |
| 設定 namespace 隔離架構 | 調整 batch size |
| 引入新的 MCP Server | 新增測試案例 |
| 決定知識保留期限 | 修改 README |

### ADR 範例：選擇嵌入模型

```markdown
# ADR-001：使用 text-embedding-3-large 作為主要嵌入模型

## Status
Accepted（2026-01-20）

## Context
我們需要選擇一個嵌入模型將企業文件轉換為向量。
主要候選：
- OpenAI text-embedding-3-large（1536 維，$0.13/M tokens）
- OpenAI text-embedding-3-small（1536 維，$0.02/M tokens）
- Nomic embed-text v1.5（768 維，本地，免費）

在 500 份內部文件上的 retrieval accuracy 測試（Hit@5）：
- text-embedding-3-large：89.3%
- text-embedding-3-small：84.1%
- Nomic embed-text v1.5：81.7%（但需要中文 fine-tune）

## Decision
使用 `text-embedding-3-large`，原因：
1. Retrieval accuracy 最高，誤導風險最低
2. 每月預估成本約 NT$3,000（可接受）
3. 無需自架 GPU 伺服器（降低 Ops 複雜度）

## Consequences
正面：
- 最高的檢索準確率，減少 AI 引用錯誤文件的機率
- 直接使用 OpenAI API，無需維護本地模型

負面：
- 依賴 OpenAI API 可用性（需要 fallback 策略）
- 未來若向量維度變更，需要重新嵌入所有文件（重大工程）

## Fallback 策略
若 OpenAI API 不可用：暫停攝取（ingestion），查詢切換到關鍵字搜尋。

## References
- 測試結果摘要：`docs/ADR/README.md`（本教案版未附原始 benchmark notebook）
- Constitution Principle I（知識品質優先）
```

### ADR 範例：Chunking 策略

```markdown
# ADR-002：採用語意感知的遞迴分塊策略

## Status
Accepted（2026-01-25）

## Context
文件分塊（Chunking）直接影響檢索品質。
測試了三種策略：
- 固定大小分塊（Fixed-size）：每塊 512 tokens，重疊 64 tokens
- 語意分塊（Semantic）：使用 NLP 偵測段落邊界
- 遞迴分塊（Recursive）：先按段落，段落太長再按句子

測試結果（用 100 個業務問題評估）：
- 固定大小：Hit@3 = 71%（常在句子中間切斷，語意斷裂）
- 語意分塊：Hit@3 = 83%（但處理速度慢 3 倍）
- 遞迴分塊：Hit@3 = 81%（速度快，語意完整性佳）

## Decision
採用遞迴分塊，參數：
- 主分隔符：段落（\n\n）→ 句子（。！？）→ 詞（，）→ 字元
- 目標大小：600 tokens
- 重疊大小：100 tokens（保留跨塊上下文）

## Consequences
正面：尊重文件的自然段落結構，語意完整
負面：不同文件的 chunk 大小不均，需要在 metadata 記錄實際大小
```

---

## 2.4 Decision Diary — 知識策略的孵化器

### 典型的 RAG Diary Entry

```markdown
# diary.md

### 2026-02-10 — 是否需要 Hybrid Search（混合搜尋）

- **Context**：純向量搜尋在精確詞彙查詢（如「ADR-002」、「第三條款」）表現較差。
  BM25 關鍵字搜尋在精確詞彙上表現更好，但語意理解不足。
- **Options**：
  1. 純向量搜尋（現狀）
  2. 純 BM25 關鍵字搜尋
  3. Hybrid Search：向量 (70%) + BM25 (30%) 加權合併
- **Decision（temporary）**：先在 `legal-knowledge-mcp` 試用 Hybrid Search 30 天
- **Risks**：Hybrid Search 需要維護兩個索引，增加 Ops 複雜度
- **Next validation step**：比較 30 天後的 Hit@5 和用戶滿意度評分
- **Promote-to**：若改善超過 5%，升級為 ADR-004；否則 resolved

---

### 2026-02-18 — 文件過期通知策略

- **Context**：Constitution Principle I 規定文件超過 180 天需審核，
  但目前沒有自動通知 owner 的機制。文件 owner 常忘記審核。
- **Options**：
  1. 每週 batch 任務掃描並發送 Email
  2. 在向量 DB 中設定 TTL（Time To Live），到期自動降為 `pending` 狀態
  3. 整合 Slack Bot 通知
- **Decision（temporary）**：Option 2 + Option 3 並行測試
- **Risks**：TTL 設定錯誤可能造成重要文件意外下線
- **Next validation step**：1 個月後評估 owner 的審核完成率
- **Promote-to**：constitution v1.4.0（若策略穩定）
```

---

## 2.5 三者的關係

```
          ┌──────────────────────────────────────┐
          │ Constitution（永久）                   │ ← 最高權威
          │ v1.3.0，5 條知識治理原則               │    修改需版本號 + 影響報告
          └──────────────────┬───────────────────┘
                             │ 升級（重大決策）
          ┌──────────────────┴───────────────────┐
          │ ADR（永久）                            │ ← 架構決策
          │ ADR-001（嵌入模型）                    │    一旦 accepted 很少修改
          │ ADR-002（Chunking 策略）               │
          │ ADR-003（向量 DB Schema）              │
          └──────────────────┬───────────────────┘
                             │ 升級（驗證通過後）
          ┌──────────────────┴───────────────────┐
          │ Decision Diary（臨時）                 │ ← 決策孵化器
          │ Hybrid Search 試用中...               │    定期清理
          │ 文件過期通知策略試用中...              │
          └──────────────────────────────────────┘

穩定性：Constitution > ADR > Diary
修改頻率：Diary >> ADR > Constitution
```

---

## 練習

1. **Constitution 設計**：為一個「客服 FAQ RAG 系統」撰寫一份 constitution.md，包含 3 條原則。每條原則必須：
   - 是不可違反的邊界（不是「最好這樣做」）
   - 包含至少一個可驗證的 Invariant
   - 附上 Rationale

2. **ADR 練習**：你的團隊需要在 Chroma（本地，免費）和 Pinecone（雲端，$70/月）之間選擇向量資料庫，寫一份 ADR，包含 Context、Decision、Consequences。

3. **Diary Entry**：想一個 RAG 系統中你目前還不確定的設計決策（例如：chunk 大小、top-k 數量、是否需要 re-ranking），用 diary entry 模板記錄下來，並寫出 Next validation step。

4. **思考題**：如果 Constitution 的 Principle II（幻覺零容忍）要求 temperature ≤ 0.3，但行銷團隊要求 AI 的回答更有創意和溫度，你會如何在不違反 Constitution 的前提下解決這個需求？

---

> **下一章**：[第三章：規範驅動開發 — SDD-BDD-TDD for RAG](03-sdd-bdd-workflow.md)  
> 我們將學習如何用規格先行的方法設計 RAG 的每一個功能，確保需求清晰、測試完整。

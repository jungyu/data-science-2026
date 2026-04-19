---
type: plan
version: "1.0"
status: complete
feature_branch: "003-jr-pass-rag-assistant"
created: "2026-04-15"
phases:
  phase_0_research: complete
  phase_1_design: complete
  phase_2_tasks: complete
constitution_check: pass
---

# 實作計畫：JR Pass 官方規則與合規性 RAG 諮詢系統

**分支**：`003-jr-pass-rag-assistant`  
**日期**：2026-04-15  
**規格文件**：[spec.md](C:\Users\12ok4\project\data-science-2026\project-fate\specs\003-jr-pass-rag-assistant\spec.md)

## 摘要

建立一套 retrieval-first 的 JR Pass 合規諮詢 RAG 系統。  
系統會 ingest 官方 JR Pass 與區域周遊券規則文件，對內容進行 chunking 與 embedding，保留來源與修訂版本 metadata，接著依據使用者行程與問題檢索規則證據、驗證 grounding、進行資格判定，最後輸出繁體中文且附引用的諮詢結果。

## 技術脈絡

- **語言 / 版本**：Python 3.11
- **主要依賴**：OpenAI SDK、pytest、behave、向量資料庫 client、HTML / 文件載入工具、markdown / text normalization utilities
- **儲存層**：既有向量資料庫抽象層 + 票券文件 metadata registry + 可選 itinerary evaluation cache
- **測試方式**：pytest 單元測試、整合測試、retrieval evaluation tests、behave feature scenarios
- **目標平台**：Linux 相容的 Python 服務與 CLI ingestion job
- **專案型態**：單一 Python 專案
- **效能目標**：一般查詢 `p95 < 2500ms`、retrieved chunks <= 10、citations <= 5
- **關鍵限制**：只能 retrieval-first、只能 ingest 官方文件、第一版只支援 `zh-TW`、支援匿名使用、官方資料每 24 小時更新一次
- **範圍**：第一版支援全國 JR Pass 與有限集合的區域周遊券

## 憲章檢查

**參考文件**：[constitution.md](C:\Users\12ok4\project\data-science-2026\project-fate\.agent\memory\constitution.md)

### 原則一：可驗證變更

- [x] 已為 API 端點規劃 contract tests
- [x] 已為主要使用者流程規劃 integration tests
- [x] 已為 retrieval、規則解析、合規判定與 grounding 邏輯規劃 unit tests
- [x] 任務拆解保留 TDD 流程

### 原則二：型別安全優先

- [x] 已規劃 itinerary 與 query 的輸入 schema
- [x] 已規劃 pass rules、products、assessments 的強型別實體
- [x] 已規劃在答案生成前正規化 retrieval metadata 與 compliance output

### 原則三：預設安全

- [x] 已規劃使用者輸入驗證
- [x] 除 itinerary payload 外不要求額外敏感使用者識別資訊
- [x] logging 僅限 request id、grounding state 與 source metadata

### 原則四：可維護性

- [x] 已規劃 research、data model、contracts、quickstart 等文件產物
- [x] 已定義 unit 與 integration 測試覆蓋目標
- [x] feature branch 與檔案結構維持增量式調整

### 原則五：小步可回復

- [x] 盡可能重用現有 ingestion / retrieval 基礎設施
- [x] 合規判定設計為受限的 domain layer，而非大型旅遊規劃引擎
- [x] 第一版來源限制為官方票券文件

### 原則六：人類最終權威

- [x] 官方來源範圍明確可審核
- [x] 系統提供的是諮詢，不是法律或商業保證
- [x] 遇到規則衝突或證據不足時輸出保守結果

## 專案結構

### 文件產物

```text
specs/003-jr-pass-rag-assistant/
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
|-- contracts/
|   `-- jr-pass-compliance.openapi.yaml
`-- tasks.md
```

### 原始碼結構

```text
src/
|-- models/
|   |-- knowledge.py
|   `-- pass_rules.py
|-- ingestion/
|   |-- ingestor.py
|   |-- chunker.py
|   |-- embedder.py
|   `-- pass_rule_ingestor.py
|-- retrieval/
|   |-- retrieval_gate.py
|   `-- pass_rule_retriever.py
|-- query/
|   |-- query_pipeline.py
|   `-- compliance_consultation.py
|-- governance/
|   `-- source_policy.py
|-- config/
|   `-- pass_catalog_config.py
`-- rag/
    `-- core.py

tests/
|-- contract/
|   `-- test_jr_pass_compliance_contract.py
|-- integration/
|   `-- test_jr_pass_consultation_flow.py
`-- unit/
    |-- test_pass_rule_ingestor.py
    |-- test_pass_rule_retriever.py
    `-- test_compliance_assessment.py
```

**結構決策**：維持單一 Python 專案，延伸既有 ingestion / retrieval / query 架構，新增受限範圍的 pass-rule ingestion 與 compliance assessment layer，而不是拆成新的微服務。

## Phase 0：研究

研究結果整理在 [research.md](C:\Users\12ok4\project\data-science-2026\project-fate\specs\003-jr-pass-rag-assistant\research.md)。

已確認的研究主題：

- 第一版只使用官方 JR Pass 文件
- 將規則檢索與合規判定拆開
- 為每個 chunk 保留 revision-aware metadata
- 第一版不做多語輸出擴張

## Phase 1：設計與契約

設計產物如下：

- [data-model.md](C:\Users\12ok4\project\data-science-2026\project-fate\specs\003-jr-pass-rag-assistant\data-model.md)
- [quickstart.md](C:\Users\12ok4\project\data-science-2026\project-fate\specs\003-jr-pass-rag-assistant\quickstart.md)
- [jr-pass-compliance.openapi.yaml](C:\Users\12ok4\project\data-science-2026\project-fate\specs\003-jr-pass-rag-assistant\contracts\jr-pass-compliance.openapi.yaml)

Phase 1 的關鍵設計決策：

1. 新增官方票券規則 ingestion layer，保留 revision metadata。
2. 將 `PassDocument` 檢索與 `ComplianceAssessment` 邏輯分離。
3. 將 grounding gate 設為回答生成前的必要檢查點。
4. 第一版限制為 `zh-TW` 與匿名使用，以控制範圍。
5. 成本比較僅作為輔助資訊，而非主要權威依據。

## Phase 2：任務拆解策略

### 任務生成策略

- 先產生 consultation endpoint 的 contract tests
- 再產生 rule ingestion、metadata filtering、compliance assessment 與 grounding 行為的 unit tests
- 接著產生完整 ingest -> retrieve -> assess -> answer 流程的 integration tests
- 在實作 retriever 與 consultation orchestration 前，先完成 domain models 與 config
- 只有在 retrieval 與 compliance output 可測試後，才接上 answer generation wiring

### 排序策略

- TDD 順序：contracts -> unit tests -> integration tests -> implementation
- 依賴順序：models / config -> ingestion -> retriever -> compliance logic -> API / query wiring
- 可平行化任務：ingestion、retrieval、compliance 相關 unit tests 可獨立進行

### 預估輸出

- 在 [tasks.md](C:\Users\12ok4\project\data-science-2026\project-fate\specs\003-jr-pass-rag-assistant\tasks.md) 中產生 18-24 個有序任務

## 複雜度追蹤

| 額外設計 | 必要原因 | 為何不採用更簡單方案 |
|-----------|----------|----------------------|
| 明確加入 compliance assessment layer | 系統必須區分官方規則檢索與資格判定 | 若只做自由生成，會混淆證據與判斷 |
| 加入 revision-aware metadata | 官方文件會隨版本更新而衝突 | 若不追蹤版本，會削弱可信度與可解釋性 |

## 進度追蹤

### Phase 狀態

- [x] Phase 0：研究完成
- [x] Phase 1：設計完成
- [x] Phase 2：任務規劃完成
- [ ] Phase 3：任務產生完成
- [ ] Phase 4：實作完成
- [ ] Phase 5：驗證完成

### Gate 狀態

- [x] 初始 Constitution Check：PASS
- [x] 設計後 Constitution Check：PASS
- [x] 所有 NEEDS CLARIFICATION 已解完
- [x] 複雜度偏離已記錄

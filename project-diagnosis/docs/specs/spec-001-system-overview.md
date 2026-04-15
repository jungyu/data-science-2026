# Spec-001: 系統總覽

- Status: Draft
- Owner: RAG Architect
- Last Updated: 2026-04-15

## 1. 目的

定義《中醫診斷 RAG 系統》的模組邊界、資料流與非功能需求，作為其他 spec 的根節點。

## 2. 系統定位

本系統為 **中醫知識檢索與辨證輔助引擎**，不做臨床診斷、不替代醫師、不自動處方。
其回答須具備：候選排序、支持證據、衝突揭露、尚缺資訊、可追溯來源。

## 3. 模組總覽

| 模組 | 對應 Spec | 責任 |
| --- | --- | --- |
| Feature Extractor | [Spec-002](./spec-002-feature-extractor.md) | 自然語言敘述 → 結構化症狀 / 舌脈 / 時序 / 缺失類別 |
| Knowledge ETL | [Spec-003](./spec-003-knowledge-etl.md) | 外部資料 → `knowledge_atoms` + `atom_relations` |
| Knowledge Atom | [Spec-004](./spec-004-knowledge-atom-schema.md) | 11 種原子型別與 metadata 契約 |
| Rule Engine | [Spec-005](./spec-005-rule-engine.md) | 對候選證型做加減分、衝突偵測、補問 |
| Retrieval Pipeline | [Spec-006](./spec-006-retrieval-pipeline.md) | FTS + 向量 + 關係展開，輸出 Top-K 候選 |
| Generation Orchestrator | [Spec-007](./spec-007-generation-orchestrator.md) | 組 Answer Contract，呼叫 LLM 產敘事 |
| Storage | [Spec-008](./spec-008-storage-schema.md) | PostgreSQL + pgvector schema |
| Evaluation | [Spec-009](./spec-009-evaluation-framework.md) | 四層指標、案例集、監控 |
| API | [Spec-010](./spec-010-api-contracts.md) | MCP Tools 與 REST 端點 |

## 4. 端到端資料流

```
User Query (natural language)
      │
      ▼
[Spec-002] Feature Extractor
  └─→ symptoms / signs / tongue / pulse / missing
      │
      ▼
[Spec-006] Retrieval Pipeline
  ├─ FTS
  ├─ Vector
  └─ Relation Expansion
  └─→ candidate patterns (ranked)
      │
      ▼
[Spec-005] Rule Engine
  └─→ adjusted candidates + ambiguity flags + suggested questions
      │
      ▼
[Spec-007] Generation Orchestrator
  ├─ Stage 1: Answer Contract (JSON, 確定性)
  └─ Stage 2: Markdown synthesis (LLM, 受限於已檢索證據)
      │
      ▼
Persist to query_logs / retrieval_logs
      │
      ▼
[Spec-009] Offline Evaluation (case-based / Ragas)
```

## 5. 非功能需求

### 5.1 確定性（Determinism）

* Spec-002 / 005 / 006 的輸出在相同輸入下必須完全一致
* 只有 Spec-007 Stage 2 允許 LLM 的非確定性；其依據必須可回放

### 5.2 可追溯性（Traceability）

* 每個候選證型必須附 `supporting_feature_ids` 與 `conflicting_feature_ids`
* 每條 Answer Contract 必須對應一筆 `query_logs` 記錄，retrieval 過程寫入 `retrieval_logs`

### 5.3 可演化性（Evolvability）

* Ontology 擴充不得破壞現有 atom id
* `diagnostic_rules.conditions` / `actions` 採 JSONB，允許規則熱更新
* `atom_relations` 採邊表結構，新增關係型別僅需 check constraint 調整

### 5.4 可觀測性（Observability）

* FTS / 向量 / 關係三路召回各自入 `retrieval_logs.stage`
* LLM 呼叫的 model_name、latency_ms 寫入 `query_logs`
* 健康檢查 endpoint 揭露 DB / embedding / synthesis 子系統狀態（見 [Spec-010](./spec-010-api-contracts.md)）

## 6. 安全邊界

| 要求 | 強制方 |
| ---- | ------ |
| 禁止無證據斷言 | Spec-007 Prompt + Rule Engine 缺失提示 |
| 禁止具體處方建議 | Spec-007 Prompt 強制規則 |
| 候選與主訴衝突時必須揭示 | Spec-005 `conflicts_with` 規則 |
| 候選信心不足時必須補問 | Spec-005 `question_suggestion` 規則 |

## 7. 非責任範圍

* 臨床診斷、處方、劑量建議
* 真實病歷資料儲存（PHI 不落地）
* 多語言輸出（MVP 僅 zh-Hant）

## 8. 驗收要求

* 所有模組之 spec 均有可執行實作（scripts/ 或 sql/）
* Answer Contract JSON 結構在測試案例下穩定
* 端到端延遲（不含 LLM synthesis）< 800ms @ seed 資料量

## 9. 依賴 ADR

* [ADR-001](../adr/ADR-001-tcm-rag-architecture.md)：Ontology-first + Hybrid Retrieval + Evidence-based Generation

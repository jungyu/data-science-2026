# TCM Diagnostic RAG — Specifications

本目錄為《中醫診斷 RAG 系統》可實作規格集。

- [白皮書](../whitepaper/tcm-rag-whitepaper.md) 提供設計理念與論述
- [ADR-001](../adr/ADR-001-tcm-rag-architecture.md) 記錄關鍵架構決策
- **本目錄** 提供每個模組的輸入、輸出、驗收條件

所有 spec 均為 zh-Hant，程式碼識別符保留英文。

---

## Spec 清單

| Spec | 標題 | 摘要 |
| ---- | ---- | ---- |
| [Spec-001](./spec-001-system-overview.md) | 系統總覽 | 模組責任、資料流、非功能需求 |
| [Spec-002](./spec-002-feature-extractor.md) | 診斷特徵抽取器 | 自然語言 → 結構化症狀 / 舌脈 / 時序 |
| [Spec-003](./spec-003-knowledge-etl.md) | 知識 ETL | 六階段：抓取 → 清洗 → 切塊 → 標註 → 嵌入 → 驗證 |
| [Spec-003a](./spec-003a-etl-prompt-template.md) | ETL Prompt 模板 | LLM 協助標註的系統提示、上下文、輸出 schema |
| [Spec-004](./spec-004-knowledge-atom-schema.md) | 知識原子 Schema | 11 種原子型別的欄位契約 |
| [Spec-005](./spec-005-rule-engine.md) | 辨證規則引擎 | 評分調整、衝突偵測、補問建議 |
| [Spec-006](./spec-006-retrieval-pipeline.md) | 檢索管線 | FTS / 向量 / 關係展開三路召回與重排 |
| [Spec-007](./spec-007-generation-orchestrator.md) | 生成協調器 | Stage 1 受限候選 + Stage 2 證據化敘事 |
| [Spec-008](./spec-008-storage-schema.md) | 儲存 Schema | PostgreSQL + pgvector + FTS 資料表與索引 |
| [Spec-009](./spec-009-evaluation-framework.md) | 評估框架 | 四層評估：特徵 → 規則 → 檢索 → 生成 |
| [Spec-010](./spec-010-api-contracts.md) | API 契約 | MCP Tools 與 REST 端點 |
| [Spec-011](./spec-011-roadmap-and-deliverables.md) | 里程碑與交付 | Phase 0 ~ Phase 3 驗收條件 |

---

## 依賴關係

```
Spec-001
  ├── Spec-002 (特徵抽取)
  ├── Spec-003 (ETL)
  │    └── Spec-003a (Prompt)
  ├── Spec-004 (Atom Schema) ← Spec-003 輸出對齊
  ├── Spec-005 (規則引擎) ← 消費 Spec-002 輸出
  ├── Spec-006 (檢索) ← 引用 Spec-004 / Spec-005 / Spec-008
  ├── Spec-007 (生成) ← 消費 Spec-005 / Spec-006
  ├── Spec-008 (Storage) ← 實現 Spec-004
  ├── Spec-009 (評估) ← 覆蓋所有前層
  ├── Spec-010 (API) ← 暴露 Spec-002 / 005 / 006 / 007
  └── Spec-011 (Roadmap) ← 分階段交付 Spec-001~010
```

無循環依賴。資料流為單向：**症狀 → 特徵 → 規則 → 檢索 → 生成 → 評估**。

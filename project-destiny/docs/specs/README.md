# Bazi RAG Specs

本目錄定義八字解盤 RAG 系統的實作規格。

## 文件清單

- [Spec-001 系統總覽](./spec-001-system-overview.md)
- [Spec-002 八字排盤模組](./spec-002-bazi-engine.md)
- [Spec-003 知識 ETL 流程](./spec-003-knowledge-etl.md)
- [Spec-003a ETL Annotation Prompt 範本](./spec-003a-etl-prompt-template.md)
- [Spec-004 Knowledge Atom Schema](./spec-004-knowledge-atom-schema.md)
- [Spec-005 規則引擎](./spec-005-rule-engine.md)
- [Spec-006 檢索管線](./spec-006-retrieval-pipeline.md)
- [Spec-007 生成編排器](./spec-007-generation-orchestrator.md)
- [Spec-008 儲存層與資料表](./spec-008-storage-schema.md)
- [Spec-009 評估框架](./spec-009-evaluation-framework.md)
- [Spec-010 API 契約](./spec-010-api-contracts.md)
- [Spec-011 交付階段與路線圖](./spec-011-roadmap-and-deliverables.md)

## 設計原則

1. 排盤必須 deterministic
2. 規則先於生成
3. 檢索必須 multi-route
4. 知識單位必須可計算
5. 結果必須 grounded 且可追溯

## 模組依賴順序

```
Bazi Engine
    ↓
Rule Engine
    ↓
Retrieval Orchestrator  ←── Knowledge Atoms (ETL → DB)
    ↓
Generation Orchestrator
    ↓
Evaluation Service
```

## 關聯 ADR

每份 spec 均對應至少一份 ADR，詳見各 spec 文末的「依賴 ADR」章節。

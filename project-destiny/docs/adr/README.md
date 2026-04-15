# Architecture Decision Records

本目錄記錄八字解盤 RAG 系統的核心架構決策。

## ADR 清單

- [ADR-001: 採用混合式檢索策略（Hybrid Retrieval）](./ADR-001-hybrid-retrieval-strategy.md)
- [ADR-002: 文獻權重與權威層級策略](./ADR-002-document-priority-and-authority.md)
- [ADR-003: 八字排盤採獨立確定性模組](./ADR-003-deterministic-bazi-chart-engine.md)
- [ADR-004: 文本表徵採多重表徵法](./ADR-004-text-representation-strategy.md)
- [ADR-005: 規則引擎先於生成層執行](./ADR-005-rule-engine-before-generation.md)
- [ADR-006: 採用知識原子化 Chunking 策略](./ADR-006-knowledge-atom-chunking-strategy.md)
- [ADR-007: 儲存架構採 Postgres + pgvector + 關係/圖譜混合方案](./ADR-007-storage-architecture-postgres-pgvector-graph.md)
- [ADR-008: 生成結果必須具備可追溯性與評估機制](./ADR-008-evaluation-and-grounded-generation.md)
- [ADR-009: Multi-seed 檢索與 Rule-first Agentic 邊界](./ADR-009-multi-seed-retrieval-and-agentic-boundary.md)

## 狀態說明

- **Proposed**：已提出，待採納
- **Accepted**：已採納
- **Superseded**：已被新決策取代
- **Deprecated**：已不建議使用

## 撰寫原則

每份 ADR 需回答以下問題：

1. 我們在解什麼問題？
2. 為何要現在做這個決定？
3. 還有哪些替代方案？
4. 為何最後選這個？
5. 這個決定會帶來哪些後果？

## 關聯文件

- `docs/architecture/bazi-rag-system-plan.md`
- `docs/specs/`
- `schemas/knowledge-atom.schema.json`
- `schemas/bazi-chart.schema.json`

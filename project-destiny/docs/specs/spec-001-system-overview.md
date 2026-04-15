# Spec-001: 系統總覽

- Status: Draft
- Owner: System Architect
- Last Updated: 2026-04-14

## 1. 目的

定義八字解盤 RAG 系統的整體模組責任、資料流與非功能要求。

## 2. 系統目標

本系統需具備以下能力：

1. 接收出生資料並完成正確排盤
2. 將命盤轉成結構化特徵
3. 根據命盤特徵進行多路召回
4. 根據規則與文獻生成可追溯解釋
5. 提供評估、除錯與持續優化基礎

## 3. 高階架構

系統包含以下模組：

| 模組 | 責任 |
|------|------|
| Input Normalizer | 清洗格式、統一輸入型別 |
| Bazi Engine | 排盤、干支、十神、月令 |
| Knowledge ETL | 古籍切分、標註、向量化 |
| Rule Engine | 強弱判定、格局候選、調候需求 |
| Retrieval Orchestrator | 多路召回、融合、重排 |
| Generation Orchestrator | Prompt 組裝、受控生成 |
| Evaluation Service | 評估案例、指標記錄 |
| Storage Layer | PostgreSQL + pgvector |

## 4. 高階資料流

```
使用者輸入出生資訊
    ↓
Input Normalizer（清洗格式）
    ↓
Bazi Engine（排盤）
    ↓
Rule Engine（命盤特徵 + 候選格局）
    ↓
Retrieval Orchestrator（多路召回：Symbolic / Metadata / Vector / Graph）
    ↓
Generation Orchestrator（組裝 prompt + 證據）
    ↓
LLM 生成 grounded output
    ↓
Evaluation Service（記錄推論與檢索結果）
```

## 5. 非目標

- 不在本階段支援所有流派
- 不在本階段支援全自動命理專家等級判讀
- 不讓 LLM 自行進行曆法換算與排盤

## 6. 非功能需求

### 6.1 Correctness
- 排盤結果需可對照權威排盤結果
- 規則引擎應可回歸測試

### 6.2 Traceability
- 每個主要結論需帶證據來源

### 6.3 Evolvability
- 可逐步替換向量庫、圖譜模組或 LLM

### 6.4 Observability
- 所有檢索路徑需記錄查詢與排序結果

## 7. 依賴 ADR

- ADR-001：混合式檢索策略
- ADR-003：確定性排盤模組
- ADR-005：規則引擎先於生成
- ADR-008：可追溯性與評估機制

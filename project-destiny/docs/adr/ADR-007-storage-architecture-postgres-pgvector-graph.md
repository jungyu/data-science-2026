# ADR-007: 儲存架構採 Postgres + pgvector + 關係/圖譜混合方案

- Status: Accepted
- Date: 2026-04-14
- Deciders: System Architect, Backend Engineer, Data Engineer
- Tags: storage, postgres, pgvector, graph, scalability

## Context

本系統需要同時管理：

- 結構化命盤資料
- 規則表
- 知識原子 metadata
- 向量嵌入
- 圖譜關係
- 評估樣本
- 查詢日誌

若一開始就引入過多獨立基礎設施，例如獨立向量庫 + 圖資料庫 + 規則引擎儲存庫，雖然功能完整，但會讓原型開發與維運成本大幅提升。

本案現階段目標是先建立可驗證的核心閉環，而非追求最豪華的資料層。

## Decision

第一階段儲存架構採：

- **PostgreSQL**
  - 作為主要結構化資料庫

- **pgvector**
  - 作為向量檢索基礎

- **Graph-like relational tables**
  - 以關係表模擬知識圖譜邊與節點

待第二階段確認圖譜查詢價值後，再評估是否升級為 Neo4j。

## Alternatives Considered

### Option A: Postgres + pgvector
優點：
- 簡單
- 維運成本低
- 適合 MVP

缺點：
- 圖譜查詢表達力有限

### Option B: Postgres + Pinecone + Neo4j
優點：
- 功能完整
- 各司其職

缺點：
- 架構複雜
- 初期維運負擔大

### Option C: 全部單靠向量庫
優點：
- 開發快

缺點：
- 無法支撐規則與圖譜需求
- 系統治理能力不足

## Consequences

### Positive
- 有利快速建立原型
- 可在單一 SQL 生態下完成大部分工作
- 方便 schema、版本與備份管理

### Negative
- 某些圖查詢可能較笨重
- 未來資料量擴大時需重新評估拆分策略

## Implementation Notes

建議資料表至少包括：

- `bazi_charts`
- `knowledge_atoms`
- `knowledge_embeddings`
- `knowledge_relations`
- `rule_definitions`
- `retrieval_logs`
- `evaluation_cases`

## Decision Drivers

- 先求可驗證，再求極致拆分
- 降低基礎設施複雜度
- 保留未來演進空間

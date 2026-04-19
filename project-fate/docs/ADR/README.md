# Architecture Decision Records

本目錄記錄 enterprise-rag 專案的重大架構決策。

## ADR 索引

| ADR | 標題 | 狀態 | 日期 |
|-----|------|------|------|
| [ADR-001](ADR-001-embedding-model.md) | 使用 text-embedding-3-large 作為主要嵌入模型 | Accepted | 2026-01-20 |
| [ADR-002](ADR-002-chunking-strategy.md) | 採用語意感知的遞迴分塊策略 | Accepted | 2026-01-25 |

## 何時需要 ADR

| 需要 ADR | 不需要 ADR |
|----------|-----------|
| 選擇嵌入模型 | 調整 top-k 從 3 改成 5 |
| 選擇向量資料庫 | 更新 system prompt 措辭 |
| 決定 chunking 策略 | 修改日誌格式 |
| 設定 namespace 隔離架構 | 調整 batch size |
| 引入新的 MCP Server | 新增測試案例 |

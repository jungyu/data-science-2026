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

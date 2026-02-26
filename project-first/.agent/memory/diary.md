# Decision Diary — enterprise-rag

> 臨時決策記錄。經驗證後升級為 Constitution 或 ADR，或標記為 resolved。

---

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

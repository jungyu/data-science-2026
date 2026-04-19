# ADR-001：採用 `text-embedding-3-large` 作為主要嵌入模型

## 背景

本專案需要為 JR Pass 官方規則與合規性 RAG 系統選擇一個能支援高品質檢索的 embedding 模型。  
模型選型會直接影響：

- 官方規則片段的檢索命中率
- 中英文票券名稱與術語的對齊能力
- FAQ 問句與條文內容之間的語意匹配
- 成本與維運複雜度

本次評估的候選方案包括：

- `text-embedding-3-large`
- `text-embedding-3-small`
- `Nomic embed-text v1.5`

在內部小規模檢索測試中，`text-embedding-3-large` 在 Top-K retrieval accuracy 上表現最佳，且整體多語語意表現較穩定。

## 決策

本專案第一版採用 `text-embedding-3-large` 作為主要嵌入模型。

採用原因如下：

1. 在規則型知識檢索情境中，檢索準確率表現最佳。
2. 對票券名稱、地區名稱、FAQ 問句改寫等語意差異有較佳的魯棒性。
3. 不需自行維護本地 embedding serving infrastructure，可降低第一版維運成本。

## 狀態

Accepted

## 後果

### 正面影響

- 提升向量檢索品質與引用可信度
- 降低第一版在 embedding 層的自建與維運負擔
- 對多種票券術語與自然語言問法有較穩定的表現

### 負面影響

- 依賴外部 API 供應商
- 成本高於較小型 embedding 模型
- 若未來大量擴充語料，成本壓力可能提高

### 後續影響

- 若未來需要本地部署或降低成本，可再評估 `BGE-M3` 或其他可自託管模型
- 評估流程需持續追蹤 retrieval quality，確認此模型在實際 JR 規則語料上維持穩定

## 備援策略

若外部 embedding API 不可用，可暫時切換為預先評估過的本地 embedding 模型，但需重新驗證檢索品質與引用穩定性。

## 參考資料

- [README.md](C:\Users\12ok4\project\data-science-2026\project-fate\docs\ADR\README.md)
- [.agent/memory/constitution.md](C:\Users\12ok4\project\data-science-2026\project-fate\.agent\memory\constitution.md)

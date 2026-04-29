# ADR-004：混合檢索 + RRF 輕量重排

## 狀態

已採納

## 背景

私人筆記的內容混雜：精確技術術語（API 名稱、檔案路徑、程式碼片段）、ADR 決策紀錄、概念性散文。純向量搜尋在精確關鍵字上表現不穩定；純全文搜尋在語意相似但用詞不同的情況下召回率低。

## 決策

採用三層混合檢索：

1. **`tsvector` 全文搜尋** — 精確關鍵字召回（`pg_trgm` + `unaccent` 輔助）
2. **`pgvector` 語意搜尋** — 概念相似性召回（cosine distance，IVFFlat 索引）
3. **Reciprocal Rank Fusion（RRF）** — 合併兩路排名，取加權分數最高者

加上 **category filter**，限縮 retriever 只在目標 category 的資料中搜尋。

### Category Filter 的重要性

Category filter 是 retriever 效能的關鍵控制點。Router 產生的 `rag_categories` 會直接傳入 retriever 作為 `WHERE category = ANY(...)` 條件。

**常見陷阱**：

```
ingest --category rag
            ↓
category 欄位存入 "rag"
            ↓
retriever 的 category_filter = ["engineering", "architecture", "code"]
            ↓
查不到任何資料，回覆「目前知識庫不足」
```

正確做法是確保 Router 的 `rag_categories` 包含實際 ingest 使用的 `--category` 值。Router prompt 應明確列出所有合法 category，避免 LLM 發明不存在的值。

### 已知限制

當前不包含 cross-encoder rerank，RRF 的排名品質受限於兩路召回結果的重疊程度。後期可在 RRF 之後加入輕量 reranker（如 Cohere rerank 或本地 cross-encoder）。

## 後果

### 正面

- 對技術術語與概念查詢都有一定召回率
- Category filter 大幅縮短搜尋範圍，提升相關性
- 全部在 Postgres 內執行，不依賴額外向量 DB 服務

### 負面

- SQL 邏輯較複雜，除錯時需直接查 `retrieval_logs` 資料表
- Category 對應出錯時，失敗是靜默的（不會拋錯，只是找不到資料）
- IVFFlat 需要預先建立足夠的 lists，小資料量時 recall 可能下降

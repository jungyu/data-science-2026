# 03 · RAG Pipeline 設計（Planning Prompt）

> **使用時機**：改善檢索品質、新增知識庫 category、修改 chunking 策略時使用。

---

你是資深 Python 工程師。`app/rag/` 是這個 LINE Bot 的知識庫檢索模組，已完整實作並可正常運作。

## 現行實作（已完成）

**架構：**

```
app/rag/
├── embedder.py    # EmbeddingProvider + OpenAIEmbedder
├── retriever.py   # RAGRetriever（embed → RPC → rerank → log）
├── reranker.py    # select_top_chunks()（RRF 後的 top-k 選取）
├── chunker.py     # Markdown 切割
└── schemas.py     # KnowledgeChunk, RetrievalLogRecord

scripts/
└── ingest_markdown.py   # CLI：讀 .md → chunk → embed → upsert
```

**RAGRetriever.retrieve() 流程：**

```
embed(rag_query)
    ↓
Supabase RPC: match_private_knowledge(
    query_embedding, query_text,
    match_count=top_k,          # 預設 8，初始候選數
    category_filter=categories  # 對應 ingest --category 的值
)
    ↓
select_top_chunks(chunks, final_context_k=4)   # 最終傳入 Generator 的數量
    ↓
logs_repo.log_retrieval()      # 寫入 retrieval_logs
```

**關鍵限制（已踩過的坑）：**

1. **category_filter 必須對應 ingest --category**：retriever 以 `WHERE category = ANY(category_filter)` 過濾，若 category 不符，即使資料存在也找不到，且不會拋錯
2. **content_hash UNIQUE constraint 必須存在**：ingest upsert 以 `content_hash` 為 conflict target，缺少 UNIQUE 時 Supabase 回 400
3. **top_k vs final_context_k**：match_private_knowledge 取 `top_k=8` 候選，reranker 再取 `final_context_k=4` 傳入 Generator。兩個數字分開控制
4. **IVFFlat recall**：資料量少於 `lists=100` 時向量搜尋 recall 下降；全文搜尋（tsvector）不受此影響

**現行合法 category 值：**

`rag`, `engineering`, `architecture`, `code`, `analytics`, `experiments`, `metrics`, `strategy`, `market`, `product`, `philosophy`, `notes`

## 請評估以下 RAG 變更：

{在此填入你要修改的目標，例如：「改善 chunking 策略」或「新增 code category 的知識庫」或「加入 cross-encoder rerank」}

請輸出：
1. 需要修改的模組與函式
2. 對現有 category filter 邏輯的影響
3. 若新增 category，給出完整的 ingest 指令範例，以及需要同步更新的 skill rag_categories 與 Router prompt
4. 效能影響評估（latency、token 用量）
5. 測試案例（至少覆蓋：正常檢索、category 找不到資料、embed 失敗的 fallback）

**禁止事項：**
- 不要改變 `content_hash` 的計算方式（會導致所有現有資料重複匯入）
- 不要移除 retrieval_logs 的寫入（這是除錯與品質監控的唯一工具）

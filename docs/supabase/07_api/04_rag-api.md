# Head First RAG API — 語意搜尋引擎

> **"使用者不會輸入精確的 SQL WHERE 條件。他會說『幫我找跟退貨政策有關的文件』。向量搜尋讓資料庫聽懂這句話。"**

這份指南涵蓋 [`006_public_api.sql`](../migrations/006_public_api.sql) 的 **第 450–544 行**——
3 個 RAG API function。全部都是 **anon + authenticated**，任何人都能搜尋知識庫。

---

## 搭配閱讀

| 你在讀的 | SQL 行號 | 學什麼 |
|----------|----------|--------|
| 語意搜尋 | 455–484 | vector 類型 + bridge function |
| Hybrid 搜尋 | 487–517 | 語意 + 全文雙引擎 |
| 知識庫列表 | 520–544 | 統計子查詢 |

---

## 先搞懂：RAG 搜尋怎麼運作？

```
使用者輸入：「退貨政策是什麼？」
         ↓
前端呼叫 OpenAI / Anthropic 取得 embedding
         ↓ vector(1536)
supabase.rpc('api_rag_search', {
  query_embedding: [...1536 個浮點數...],
  p_collection_code: 'help-center'
})
         ↓
public.api_rag_search()
         ↓ bridge
rag.match_chunks_with_document()
         ↓ pgvector cosine similarity
回傳最相似的 chunk（文件片段）
         ↓
前端把 chunk 塞進 LLM prompt
         ↓
LLM 根據 chunk 內容回答使用者
```

**關鍵**：資料庫不做 embedding——那是前端（或中間層）呼叫 AI API 做的。
資料庫只負責「拿到 embedding 後，找出最相似的文件片段」。

---

## 1. `api_rag_search` — 語意搜尋

> **📖 SQL 第 455–484 行**

純向量搜尋。給一個 embedding，找出 cosine similarity 最高的 chunk。

### 參數

| 參數 | 型別 | 預設值 | 說明 |
|------|------|--------|------|
| `query_embedding` | vector(1536) | — | 查詢向量（由 AI API 產生） |
| `p_collection_code` | TEXT | — | 知識庫代碼 |
| `p_top_k` | INTEGER | 5 | 回傳幾筆最相似的 |
| `p_threshold` | FLOAT8 | 0.7 | 最低相似度門檻 |

### 回傳欄位

| 欄位 | 型別 | 說明 |
|------|------|------|
| `chunk_id` | TEXT | chunk ULID |
| `document_title` | TEXT | 所屬文件標題 |
| `source_url` | TEXT | 文件來源 URL |
| `content` | TEXT | chunk 內容（實際文字） |
| `chunk_index` | INTEGER | chunk 在文件中的序號 |
| `page_number` | INTEGER | 原始頁碼 |
| `similarity` | FLOAT8 | 相似度分數（0–1） |

### 前端呼叫

```ts
// Step 1：取得 query embedding（前端或 Edge Function）
const embeddingResponse = await openai.embeddings.create({
  model: 'text-embedding-3-small',
  input: '退貨政策是什麼？'
})
const queryEmbedding = embeddingResponse.data[0].embedding

// Step 2：呼叫 RAG search
const { data } = await supabase.rpc('api_rag_search', {
  query_embedding: queryEmbedding,       // 1536 維向量
  p_collection_code: 'help-center',
  p_top_k: 5,
  p_threshold: 0.7
})

// data →
// [
//   { chunk_id: '...', document_title: '退換貨須知',
//     content: '本店提供 7 天鑑賞期...', similarity: 0.92 },
//   { chunk_id: '...', document_title: '常見問答',
//     content: '關於退貨流程，請...', similarity: 0.85 },
//   ...
// ]
```

### 裡面在幹嘛？

```sql
SELECT
  m.chunk_id, m.document_title, m.source_url,
  m.content, m.chunk_index, m.page_number, m.similarity
FROM rag.match_chunks_with_document(
  query_embedding,
  (SELECT id FROM rag.collections WHERE code = p_collection_code AND is_active = TRUE),
  p_top_k,
  p_threshold
) m;
```

這是一個 **bridge function**——它自己不做搜尋，而是轉呼叫 `rag.match_chunks_with_document()`。

| 元件 | 說明 |
|------|------|
| `public.api_rag_search` | Gateway 層：接收 collection_code → 轉成 collection_id |
| `rag.match_chunks_with_document` | 業務層：實際執行向量搜尋 |

**為什麼要橋接？** 因為前端只知道 `collection_code`（如 `'help-center'`），不知道內部的 `collection_id`（ULID）。Gateway function 負責這個轉換。

> ### 🧠 你的大腦在想…
>
> 「vector(1536) 是什麼型別？」
>
> 這是 pgvector extension 提供的向量型別。1536 是 OpenAI `text-embedding-3-small` 的維度。
> 不同的 embedding model 有不同維度：
>
> | Model | 維度 |
> |-------|------|
> | text-embedding-3-small | 1536 |
> | text-embedding-3-large | 3072 |
> | text-embedding-ada-002 | 1536 |
> | Cohere embed-v3 | 1024 |
>
> 如果你換 model，記得改 `vector(1536)` 裡的數字，而且要**重新 embed 所有文件**。

---

## 2. `api_rag_hybrid_search` — Hybrid 搜尋

> **📖 SQL 第 487–517 行**

語意搜尋 + 全文搜尋，兩個分數加權合併。

### 參數

| 參數 | 型別 | 預設值 | 說明 |
|------|------|--------|------|
| `query_text` | TEXT | — | 原始查詢文字 |
| `query_embedding` | vector(1536) | — | 查詢向量 |
| `p_collection_code` | TEXT | — | 知識庫代碼 |
| `p_top_k` | INTEGER | 5 | 回傳幾筆 |
| `p_semantic_weight` | FLOAT8 | 0.7 | 語意搜尋權重（0–1） |

### 回傳欄位

| 欄位 | 型別 | 說明 |
|------|------|------|
| `chunk_id` | TEXT | chunk ULID |
| `document_id` | TEXT | 文件 ULID |
| `content` | TEXT | chunk 內容 |
| `semantic_score` | FLOAT8 | 向量相似度分數 |
| `fulltext_score` | FLOAT8 | 全文搜尋分數 |
| `combined_score` | FLOAT8 | 加權合併分數 |

### 前端呼叫

```ts
const { data } = await supabase.rpc('api_rag_hybrid_search', {
  query_text: '退貨政策是什麼？',
  query_embedding: queryEmbedding,
  p_collection_code: 'help-center',
  p_top_k: 5,
  p_semantic_weight: 0.7    // 70% 向量 + 30% 全文
})
```

### 為什麼需要 Hybrid？

```
                  語意搜尋                     全文搜尋
              (vector similarity)          (tsvector @@ tsquery)

  擅長：                                   擅長：
  「退貨怎麼辦」 → 找到「退換貨政策」         精確關鍵字比對
  理解同義詞、語意相近                       專有名詞、產品型號

  不擅長：                                  不擅長：
  精確的專有名詞、型號                       同義詞、換句話說
  「ABC-123」 → 可能找不到                  「退貨怎麼辦」→ 可能找不到「退換貨」
```

Hybrid 搜尋把兩者的分數加權合併：

```
combined_score = semantic_score × 0.7 + fulltext_score × 0.3
```

`p_semantic_weight = 0.7` 表示 70% 靠語意、30% 靠全文。
這個比例可以依場景調整——如果你的知識庫有很多專有名詞，可以提高全文權重。

> ### ⚠️ 注意：similarity threshold 是硬編碼的
>
> SQL 第 515 行：`0.5 -- default similarity threshold`。
> 與 `api_rag_search` 不同，hybrid search 的最低相似度門檻固定為 0.5，
> 前端**無法透過參數調整**。如果你需要自訂 threshold，
> 要修改 function body 或新增一個 `p_threshold` 參數。

> ### 💡 什麼時候用 search、什麼時候用 hybrid_search？
>
> - **api_rag_search**：前端只有 embedding 時用（簡單、快）
> - **api_rag_hybrid_search**：前端同時有原始文字和 embedding 時用（更準）
>
> 實務上，前端通常兩個都有（使用者輸入的文字 + API 產生的 embedding），
> 所以 hybrid 是預設推薦。

---

## 3. `api_rag_list_collections` — 知識庫列表

> **📖 SQL 第 520–544 行**

列出所有啟用中的知識庫，附帶文件數和 chunk 數。

### 參數

無。

### 回傳欄位

| 欄位 | 型別 | 說明 |
|------|------|------|
| `code` | TEXT | 知識庫代碼（前端用這個呼叫搜尋） |
| `name` | TEXT | 知識庫名稱 |
| `description` | TEXT | 描述 |
| `document_count` | BIGINT | 已就緒的文件數 |
| `chunk_count` | BIGINT | 已 embed 的 chunk 數 |
| `is_active` | BOOLEAN | 是否啟用 |

### 前端呼叫

```ts
const { data } = await supabase.rpc('api_rag_list_collections')

// data →
// [
//   { code: 'help-center', name: '客服知識庫',
//     document_count: 45, chunk_count: 1230, is_active: true },
//   { code: 'product-docs', name: '產品文件',
//     document_count: 120, chunk_count: 5670, is_active: true },
// ]
```

### 統計子查詢

```sql
(SELECT count(*) FROM rag.documents d
 WHERE d.collection_id = c.id AND d.process_status = 'ready') AS document_count,
(SELECT count(*) FROM rag.chunks ch
 WHERE ch.collection_id = c.id AND ch.embedding IS NOT NULL) AS chunk_count
```

| 過濾條件 | 為什麼 |
|----------|--------|
| `process_status = 'ready'` | 只算處理完成的文件，排除上傳中/處理失敗的 |
| `embedding IS NOT NULL` | 只算已經有向量的 chunk，排除還在 embed 的 |

這兩個數字讓前端能顯示：「這個知識庫有 45 份文件、1,230 個搜尋片段」——
使用者看到數字就知道知識庫的規模和完整度。

> ### 🧠 你的大腦在想…
>
> 「RAG API 為什麼給 anon 也能用？知識庫不是內部資料嗎？」
>
> 看場景。如果你做的是客服 chatbot，使用者不用登入就該能問問題。
> 如果知識庫包含敏感資料，你可以修改 GRANT 只給 authenticated。
> 或者在 `api_rag_search` 裡加條件，只搜尋特定的「公開」collection。
>
> 目前的設計是最開放的——方便你先跑起來，再依需求收緊。

---

## 延伸閱讀

**底層 schema 文件**（這些 API 背後的向量搜尋引擎）：

| 文件 | 涵蓋內容 |
|------|----------|
| [RAG/01_guide-supabase-rag.md](../RAG/01_guide-supabase-rag.md) | RAG 系統完整指南 |
| [RAG/02_design-decisions.md](../RAG/02_design-decisions.md) | 設計決策（chunk 策略、embedding 選型） |
| [RAG/04_lab-rag-pipeline.md](../RAG/04_lab-rag-pipeline.md) | RAG Pipeline 實作 Lab |
| [`004_rag_schema.sql`](../migrations/004_rag_schema.sql) | 完整 SQL schema |

---

## 接下來

- [05_analytics-api.md](05_analytics-api.md)——Analytics 儀表板 API

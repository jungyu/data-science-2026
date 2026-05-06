# Ch 02b：進階檢索三技 — HyDE / 混合檢索 / Reranker

> **本章位置**：接在 [Ch 02：Multi-seed 檢索](ch02-multi-seed.md) 之後，
> 進入 [Ch 03：誠實追問 + 兩段式生成](ch03-sufficiency-generation.md) 之前。
>
> **本章目標**：修補基礎 RAG 最常見的三個弱點，讓 chunk_recall 再往上推。

---

```
╔══════════════════════════════════════════════════════════╗
║  本章結束時你能做到：                                    ║
║  ✅ HyDE 讓短問句也能精準命中長文件                      ║
║  ✅ 混合檢索同時找到「語意相近」和「關鍵字完全符合」      ║
║  ✅ Reranker 把前 20 個候選精排成最好的 5 個             ║
║  ✅ 知道這三技各自的成本，能根據領域特性選擇開或關        ║
╚══════════════════════════════════════════════════════════╝
```

---

## 為什麼 Ch02 的多路檢索還不夠

Ch02 解決了「單一問句語意稀釋」的問題，但還有三個殘留弱點：

```
弱點 1：查詢和文件的向量空間不對稱
  使用者說：「hydration 為什麼報錯」（短句，口語）
  文件寫著：「Server Component 在 hydration 階段的邊界問題…」（長段，術語）
  → 兩個 embedding 相似度偏低，即使語意相符

弱點 2：純向量搜尋找不到精確字串
  使用者說：「ESLint rule no-unused-vars 怎麼關」
  向量搜尋找到「變數命名規範」而不是「no-unused-vars 設定」
  → 關鍵字搜尋反而更準

弱點 3：前 k 個候選裡混了不相關的 chunk
  retrieve_one_seed 每條 seed 取 top-5，fuse 後可能有 15 個候選
  → 生成時塞了太多雜訊，groundedness 下降
```

HyDE、混合檢索、Reranker 分別對應這三個弱點。

---

## 2b-1  HyDE：用假設性回答提升 embedding 對稱性

### 問題

使用者的問句通常很短、口語化，而知識庫的 chunk 是長段、正式文字。
兩者的 embedding 即使語意相符，在向量空間裡的距離也可能偏大。

### 解法

**Hypothetical Document Embeddings（HyDE）**：
不直接 embed 問句，而是先讓 LLM 生成一個「假設性的回答文件」，
再 embed 這個假設文件用來做相似度搜尋。

```
原本：embed("hydration 為什麼報錯") → 搜尋
HyDE：LLM("假設這個問題的答案是一段文件，寫出來") 
      → "Server Component 在 hydration 階段…（200 字的假設文件）"
      → embed(假設文件) → 搜尋
```

假設文件和真實 chunk 都是「文件風格的長文」，embedding 空間更對稱。

### 實作

```python
# app/graph/hyde.py
HYDE_PROMPT = """
假設以下問題已經有一個完美的答案，請寫出那個答案的內容（100–150 字）。
不要說「答案是」，直接寫內容本身。
如果你不確定，也請盡力寫出最可能的答案。

問題：{user_input}
"""

async def hyde_node(state: RAGState, services: RuntimeServices) -> dict:
    hypothetical_doc = await services.ai.complete(
        prompt=HYDE_PROMPT.format(user_input=state["user_input"]),
        max_tokens=200,
    )
    # embed 假設文件，而不是原始問句
    query_embedding = await services.ai.embed(hypothetical_doc)
    return {
        "query_embedding": query_embedding,
        "hyde_doc": hypothetical_doc,   # 存起來方便 debug
    }
```

`retrieve_one_seed` 節點從 state 取 `query_embedding` 做搜尋（若有 HyDE 就用假設文件的 embedding，否則用問句的 embedding）：

```python
# app/graph/nodes.py — retrieve_one_seed_node 修改
async def retrieve_seed_node(state: RAGState, services: RuntimeServices) -> dict:
    seed = state["seed"]
    # 優先用 HyDE embedding（如果有），否則 embed seed
    if "query_embedding" in state:
        embedding = state["query_embedding"]
    else:
        embedding = await services.ai.embed(seed)

    chunks = await services.store.similarity_search(
        embedding=embedding,
        categories=state.get("rag_categories", []),
        top_k=settings.retrieve_top_k,
    )
    return {"hits_per_seed": [chunks]}
```

### 成本與取捨

| | HyDE 開啟 | HyDE 關閉 |
|---|-----------|-----------|
| 額外 LLM call | +1（生成假設文件） | 0 |
| 適合領域 | 口語問句 vs 正式文件（醫療、法規） | 問句和文件風格接近 |
| 不適合 | 問句本身就有精確關鍵字（程式碼、型號） | — |

切換方式（`.env`）：

```bash
HYDE_ENABLED=true   # 預設 false
```

---

## 2b-2  混合檢索：BM25 關鍵字 + Dense 向量，兩路同找

### 問題

純向量搜尋（dense retrieval）的弱點：
對精確字串（產品型號、函式名稱、法條編號）的命中率低。

```
問：「ESLint no-unused-vars 設定」
dense: 找到「程式碼品質工具比較」（語意相關，但沒有這個關鍵字）
BM25:  找到「ESLint Configuration — no-unused-vars」（精確命中）
```

### BM25 是什麼

BM25（Best Match 25）是資訊檢索的經典算法，只看詞頻（TF）和反向文件頻率（IDF）：

```
score(q, d) = Σ IDF(t) × TF(t,d) × (k1+1) / (TF(t,d) + k1×(1-b+b×|d|/avgdl))
  t: query 中每個詞
  IDF: 詞在所有文件中的稀有程度（越稀有分越高）
  TF: 詞在這份文件中出現次數（越多分越高）
  k1=1.2, b=0.75：原始論文的推薦參數
```

不需要 embedding，速度快，擅長精確字串。

### Supabase 實作（PostgreSQL 全文搜尋）

Supabase 內建 PostgreSQL 的 `tsvector` / `tsquery`，可以直接用：

```sql
-- 在 Supabase SQL Editor 執行（一次性設定）
ALTER TABLE private_knowledge
  ADD COLUMN IF NOT EXISTS content_tsv tsvector
    GENERATED ALWAYS AS (to_tsvector('english', content)) STORED;

CREATE INDEX IF NOT EXISTS idx_content_tsv
  ON private_knowledge USING GIN (content_tsv);
```

```python
# app/storage/stores/supabase_store.py — 新增 bm25_search 方法
async def bm25_search(
    self,
    query: str,
    categories: list[str],
    top_k: int,
) -> list[KnowledgeChunk]:
    result = self._client.rpc(
        "bm25_search",          # 見下方 SQL 函式
        {
            "query_text":        query,
            "filter_categories": categories,
            "match_count":       top_k,
        }
    ).execute()
    return [KnowledgeChunk(**row) for row in result.data]
```

```sql
-- Supabase SQL Editor — 建立 RPC 函式
CREATE OR REPLACE FUNCTION bm25_search(
  query_text       text,
  filter_categories text[],
  match_count      int
)
RETURNS TABLE (
  id text, content text, category text,
  source_url text, score float
)
LANGUAGE sql STABLE AS $$
  SELECT id, content, category, source_url,
         ts_rank_cd(content_tsv, plainto_tsquery('english', query_text)) AS score
  FROM private_knowledge
  WHERE content_tsv @@ plainto_tsquery('english', query_text)
    AND category = ANY(filter_categories)
  ORDER BY score DESC
  LIMIT match_count;
$$;
```

### 混合搜尋：兩路結果用 RRF 合併

```python
# app/graph/nodes.py — retrieve_seed_node 加入混合搜尋
async def retrieve_seed_node(state: RAGState, services: RuntimeServices) -> dict:
    seed  = state["seed"]
    cats  = state.get("rag_categories", [])
    top_k = settings.retrieve_top_k

    # --- Dense（向量）---
    embedding = state.get("query_embedding") or await services.ai.embed(seed)
    dense_chunks = await services.store.similarity_search(embedding, cats, top_k)

    if not settings.hybrid_enabled:
        return {"hits_per_seed": [dense_chunks]}

    # --- Sparse（BM25）---
    sparse_chunks = await services.store.bm25_search(seed, cats, top_k)

    # --- RRF 融合兩路結果 ---
    hybrid_chunks = rrf_fuse([dense_chunks, sparse_chunks], k=60)
    return {"hits_per_seed": [hybrid_chunks[:top_k]]}
```

`rrf_fuse` 和 Ch02 的版本相同——它已經支援任意數量的 result list，直接重用。

### 成本與取捨

| | 混合檢索 | 純向量 |
|---|---------|--------|
| 額外查詢 | +1 BM25 SQL 查詢 | 0 |
| 索引需求 | GIN index（額外儲存空間約 20%） | ivfflat index |
| 適合 | 技術文件、法條、有精確術語的領域 | 創意問答、模糊語意查詢 |
| 不適合 | 跨語言（中文 BM25 需要 jieba 分詞） | 關鍵字敏感的領域 |

> 💡 **中文 BM25**：PostgreSQL 原生 `plainto_tsquery` 不支援中文斷詞。
> 中文知識庫要混合搜尋，可以改用 `pg_jieba` extension，或在 ingestion 時預先存入斷詞結果欄位。

切換方式：

```bash
HYBRID_ENABLED=true   # 預設 false
```

---

## 2b-3  Reranker：第二階段精排，把雜訊過濾掉

### 問題

retrieve_one_seed + fuse_scores 之後，可能累積 10–20 個候選 chunk。
其中有些分數接近但其實和問題無關——這些雜訊送進 Generator 會讓 groundedness 下降。

**Bi-encoder（現有向量搜尋）的限制**：

```
向量搜尋 = 分別 embed 問句 和 chunk，計算餘弦相似度
  → 速度快，但 query 和 chunk 互相「看不到對方」
  → 無法捕捉「這個 chunk 是否真的回答了這個問題」
```

**Cross-encoder（Reranker）的優點**：

```
Reranker = 把 (問句, chunk) 一起送進模型，讓它給相關性分數
  → 速度慢（每個 chunk 都要一次推論），但精度高得多
  → 常見做法：先用向量搜尋取 top-20，再用 reranker 精排到 top-5
```

### 方案 A：Cohere Rerank API（最快上手）

```python
# pip install cohere
import cohere

class CohereReranker:
    def __init__(self, api_key: str):
        self._co = cohere.AsyncClient(api_key)

    async def rerank(
        self,
        query: str,
        chunks: list[KnowledgeChunk],
        top_n: int = 5,
    ) -> list[KnowledgeChunk]:
        if not chunks:
            return chunks

        results = await self._co.rerank(
            model="rerank-multilingual-v3.0",   # 支援中文
            query=query,
            documents=[c.content for c in chunks],
            top_n=top_n,
        )
        # 按 reranker 的排序重組 chunk 列表
        return [chunks[r.index] for r in results.results]
```

### 方案 B：BGE-Reranker（開源，本機執行，零 API 費用）

```python
# pip install sentence-transformers
from sentence_transformers import CrossEncoder

class BgeReranker:
    def __init__(self, model_name: str = "BAAI/bge-reranker-base"):
        self._model = CrossEncoder(model_name)   # 第一次執行時自動下載

    async def rerank(
        self,
        query: str,
        chunks: list[KnowledgeChunk],
        top_n: int = 5,
    ) -> list[KnowledgeChunk]:
        pairs  = [(query, c.content) for c in chunks]
        scores = self._model.predict(pairs)          # 同步，但通常 < 1 秒
        ranked = sorted(zip(scores, chunks), reverse=True)
        return [c for _, c in ranked[:top_n]]
```

### 接進 graph

在 `fuse_scores` 之後、`sufficiency_check` 之前加一個 `rerank` 節點：

```python
# app/graph/nodes.py
async def rerank_node(state: RAGState, services: RuntimeServices) -> dict:
    if not settings.reranker_enabled or not services.reranker:
        return {}   # 直接跳過，不改變 state

    fused = state.get("fused_chunks", [])
    if not fused:
        return {}

    reranked = await services.reranker.rerank(
        query=state["user_input"],
        chunks=fused,
        top_n=settings.reranker_top_n,   # 預設 5
    )
    return {"fused_chunks": reranked}    # 覆蓋 fused_chunks，後面的節點不需要改

# graph 建構（在 selfrag / reflection variant 裡加）
g.add_node("rerank", partial(rerank_node, services=services))
g.add_edge("fuse_scores",  "rerank")
g.add_edge("rerank",       "sufficiency_check")
# 把原本 fuse_scores → sufficiency_check 的 edge 改成走 rerank 中間
```

### 成本與取捨

| | Cohere Rerank | BGE-Reranker（本機） |
|---|---------------|---------------------|
| API 費用 | ~$0.001 / 搜尋 | 免費 |
| 延遲 | ~200ms（API RTT） | ~500ms（CPU）/ ~50ms（GPU） |
| 多語支援 | ✅ multilingual | ✅（bge-reranker-base） |
| 適合 | 生產環境，省維護 | 開發環境，離線測試 |

切換方式：

```bash
RERANKER_ENABLED=true
RERANKER_BACKEND=cohere    # 或 bge
RERANKER_TOP_N=5
```

---

## 2b-4  三技整合後的完整 Graph 流程

```
                    ┌─────────────────────────────────────┐
                    │  selfrag / reflection graph          │
                    │                                      │
START → route → [hyde_node] → extract_features            │
                    ↓                                      │
              expand_seeds                                 │
             ↙    ↓    ↘   (Send API fan-out)             │
  retrieve_seed retrieve_seed retrieve_seed                │
  (hybrid內建)  (hybrid內建)  (hybrid內建)                 │
             ↘    ↓    ↙   (fan-in)                       │
           fuse_scores (RRF)                               │
                    ↓                                      │
              [rerank_node]                                │
                    ↓                                      │
         sufficiency_check → clarify / generate → ...     │
                                                           │
└─────────────────────────────────────────────────────────┘
```

三個技術都是可選的（env 控制），不開的話 graph 結構完全不變。

---

## 2b-5  何時開，何時不開

```
你的知識庫以技術文件、法條、產品手冊為主？
  → 開混合檢索（關鍵字搜尋補足向量的弱點）

使用者習慣用口語短句，知識庫是正式長文？
  → 開 HyDE（拉近問句和文件的 embedding 距離）

chunk_recall 已 > 0.60，但 groundedness 仍偏低？
  → 開 Reranker（把雜訊 chunk 過濾掉再送進 Generator）

預算有限、latency 要求嚴格（< 2 秒）？
  → 先只開混合檢索（幾乎不加 latency，效果最顯著）
  → Reranker 是最後才開的選項
```

---

## ✏️ 本章任務

1. 在 Supabase 執行 `ALTER TABLE` + `CREATE INDEX` 建立 BM25 支援
2. 設定 `HYBRID_ENABLED=true`，跑 eval 比對 `chunk_recall` 變化
3. 選一個 Reranker 後端（Cohere 或 BGE），接進 graph，比對 `groundedness_score` 變化
4. （選做）開啟 HyDE，用一個口語問句比對開關前後的 retrieved chunks 差異
5. 在 `WEEK2b.md` 記錄：你的領域最需要哪一技？為什麼？

---

## 📝 沒有蠢問題

**Q：HyDE 生成的假設文件如果是錯的，不會拉偏搜尋方向嗎？**

A：會，這是 HyDE 的已知風險。
緩解方法：不只用假設文件的 embedding，而是做平均：
`final_embedding = 0.5 × embed(query) + 0.5 × embed(hyde_doc)`
這樣即使假設文件偏差，query 本身的向量也能拉回來。

**Q：BM25 的中文支援要怎麼做？**

A：PostgreSQL 的全文搜尋預設用英文 tokenizer，不支援中文斷詞。
最實用的做法：ingestion 時多存一個 `content_segmented` 欄位（用 `jieba` 斷詞後空格分隔），
BM25 查詢時也先斷詞再搜尋。
或者改用 Elasticsearch / OpenSearch，它們有成熟的中文分析器。

**Q：Reranker 會讓 latency 增加多少？**

A：BGE-Reranker（CPU）對 10 個 chunk 大約 300–600ms。
可接受的做法：只在 reflection variant 開 Reranker（本來就比較慢），
basic / selfrag variant 關閉，讓使用者感覺不到延遲差異。

---

## 🧠 腦力激盪

> 如果你的知識庫是**中文**，混合檢索要怎麼做？
>
> 提示：
> - PostgreSQL 支援自訂 text search configuration（需要安裝 `pg_jieba`）
> - 或者：ingestion 時額外存一個 `content_zh_tsv` 欄位（jieba 斷詞後的字串）
> - 或者：直接改用 Elasticsearch，它有成熟的 IK analyzer
>
> 哪個方案最適合你的 capstone？成本和維護複雜度的取捨是什麼？

---

## 🎯 本章里程碑

```
eval --variants selfrag 的 chunk_recall 比 Ch02 基準提升至少 0.05。

（可以只開混合檢索就達成，不需要三技全開）
```

---

上一章 → [Ch 02：Multi-seed 檢索](ch02-multi-seed.md)
下一章 → [Ch 03：誠實追問 + 兩段式生成](ch03-sufficiency-generation.md)

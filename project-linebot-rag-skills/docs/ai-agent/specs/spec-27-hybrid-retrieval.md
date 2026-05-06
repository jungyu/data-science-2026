# Spec-27：混合檢索曝光與調參

## 背景

### 現狀（重要：SQL 已實作，Python 未曝光）

`supabase/functions.sql` 的 `match_private_knowledge()` RPC **已同時計算向量分數與關鍵字分數**，並回傳三欄：

| 欄位 | 意義 |
|------|------|
| `vector_score` | cosine similarity（向量檢索）|
| `keyword_score` | BM25-like TF-IDF rank（PostgreSQL `tsvector` / `ts_rank`）|
| `combined_score` | `vector_weight × vector_score + keyword_weight × keyword_score`（SQL 計算）|

但 Python 端的 `app/rag/retriever.py` 呼叫 RPC 時 **hardcode** `vector_weight=1.0, keyword_weight=0.0`，等同只用向量。`app/config.py` 沒有相關 env var。

本 spec 不重寫檢索邏輯（SQL 已完備），只做三件事：
1. 在 `config.py` 加三個 env var
2. 讓 `RAGRetriever.search()` 把這三個值透傳給 RPC
3. 在 `retrieve_one_node` 的 log 顯示 `keyword_score` 與 `combined_score`

---

## 設計

### 1. Config 新增

`app/config.py`：

```python
HYBRID_ENABLED: bool = Field(default=False, alias="HYBRID_ENABLED")
HYBRID_VECTOR_WEIGHT: float = Field(default=0.7, alias="HYBRID_VECTOR_WEIGHT")
HYBRID_KEYWORD_WEIGHT: float = Field(default=0.3, alias="HYBRID_KEYWORD_WEIGHT")
```

驗證：

```python
@model_validator(mode="after")
def check_weights(self) -> "Settings":
    if self.HYBRID_ENABLED:
        total = self.HYBRID_VECTOR_WEIGHT + self.HYBRID_KEYWORD_WEIGHT
        if not (0.99 < total < 1.01):
            raise ValueError("HYBRID_VECTOR_WEIGHT + HYBRID_KEYWORD_WEIGHT 必須 = 1.0")
    return self
```

### 2. `RAGRetriever.search()` 改動

`app/rag/retriever.py`：

```python
async def search(self, query: str, top_k: int | None = None) -> list[KnowledgeChunk]:
    k = top_k or self.settings.RETRIEVAL_TOP_K

    if self.settings.HYBRID_ENABLED:
        vector_weight = self.settings.HYBRID_VECTOR_WEIGHT
        keyword_weight = self.settings.HYBRID_KEYWORD_WEIGHT
    else:
        vector_weight = 1.0
        keyword_weight = 0.0

    embedding = await self._embed(query)
    result = await self.client.rpc(
        "match_private_knowledge",
        {
            "query_embedding": embedding,
            "query_text": query,           # 新增：供 tsvector 使用
            "match_count": k,
            "vector_weight": vector_weight,
            "keyword_weight": keyword_weight,
        },
    ).execute()
    return [KnowledgeChunk(**row) for row in result.data]
```

> **注意**：確認 `match_private_knowledge` RPC 接受 `query_text`、`vector_weight`、`keyword_weight` 參數；若 SQL 函數簽章與上述不符，需同步更新 `supabase/functions.sql`。

### 3. `match_private_knowledge` SQL 簽章確認

確認（或補上）函數接受這幾個參數：

```sql
CREATE OR REPLACE FUNCTION match_private_knowledge(
  query_embedding  vector(1536),
  query_text       text,
  match_count      int    DEFAULT 5,
  vector_weight    float  DEFAULT 1.0,
  keyword_weight   float  DEFAULT 0.0
)
RETURNS TABLE (
  id              bigint,
  content         text,
  metadata        jsonb,
  vector_score    float,
  keyword_score   float,
  combined_score  float
)
LANGUAGE plpgsql AS $$
BEGIN
  RETURN QUERY
  SELECT
    pk.id,
    pk.content,
    pk.metadata,
    1 - (pk.embedding <=> query_embedding)   AS vector_score,
    ts_rank(to_tsvector('simple', pk.content),
            plainto_tsquery('simple', query_text)) AS keyword_score,
    vector_weight * (1 - (pk.embedding <=> query_embedding))
      + keyword_weight * ts_rank(to_tsvector('simple', pk.content),
                                  plainto_tsquery('simple', query_text))
                                                  AS combined_score
  FROM private_knowledge pk
  ORDER BY combined_score DESC
  LIMIT match_count;
END;
$$;
```

### 4. `KnowledgeChunk` model 補欄位

`app/rag/retriever.py`（或 `app/rag/schemas.py`）：

```python
class KnowledgeChunk(BaseModel):
    id: int
    content: str
    metadata: dict = {}
    vector_score: float = 0.0
    keyword_score: float = 0.0
    combined_score: float = 0.0
```

### 5. Log 改進

`app/graph/nodes.py` 的 `retrieve_one_node`：

```python
logger.debug(
    "retrieve chunk id=%s vector=%.3f keyword=%.3f combined=%.3f",
    chunk.id, chunk.vector_score, chunk.keyword_score, chunk.combined_score
)
```

---

## 可換點 / 不可換點

| | 可換 | 不可換 |
|---|---|---|
| `HYBRID_KEYWORD_WEIGHT` | ✅ 0.0–1.0，env var 調 | ❌ 兩個 weight 加總必須 = 1.0 |
| SQL 的關鍵字排序函數 | ✅ `ts_rank` 可換成 `ts_rank_cd` | ❌ 回傳欄位名稱（`combined_score` 等）|
| 語言設定 | ✅ `'simple'` 可換 `'chinese'`（需裝 pg-jieba）| — |

---

## 驗收標準

- `HYBRID_ENABLED=false`（預設）：行為與原本完全相同（`keyword_score` log 顯示 0）
- `HYBRID_ENABLED=true, HYBRID_KEYWORD_WEIGHT=0.3`：log 顯示非零 `keyword_score`
- 對「具體名詞」（例如 function name、品牌名）的查詢：`chunk_recall(hybrid)` ≥ `chunk_recall(vector_only)` + 5%（用 spec-20 eval 跑）
- Config 驗證：`HYBRID_VECTOR_WEIGHT=0.8, HYBRID_KEYWORD_WEIGHT=0.5` 啟動時拋 `ValueError`

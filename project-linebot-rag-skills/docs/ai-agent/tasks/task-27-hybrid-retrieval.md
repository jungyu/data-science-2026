# task-27：混合檢索曝光與調參

> 規格詳見 [spec-27](../specs/spec-27-hybrid-retrieval.md)

---

Supabase SQL 已實作 BM25 + vector 混合，本 task 的工作是把 config 暴露出來，讓 Python 端能控制 `keyword_weight`。

## 前置

- P1（spec-12 graph refactor）已完成
- Supabase `match_private_knowledge()` RPC 已存在並能正常呼叫

## 步驟 1：確認 SQL 函數簽章

登入 Supabase SQL Editor，執行：

```sql
\df match_private_knowledge
```

確認函數接受 `query_text text`、`vector_weight float`、`keyword_weight float` 參數。若不符，按 spec-27 § 設計 → 3 更新 SQL 函數。

## 步驟 2：Config 新增

`app/config.py`：

```python
HYBRID_ENABLED: bool = Field(default=False, alias="HYBRID_ENABLED")
HYBRID_VECTOR_WEIGHT: float = Field(default=0.7, alias="HYBRID_VECTOR_WEIGHT")
HYBRID_KEYWORD_WEIGHT: float = Field(default=0.3, alias="HYBRID_KEYWORD_WEIGHT")
```

加入驗證（weights 加總必須 = 1.0 when hybrid enabled）。

## 步驟 3：`KnowledgeChunk` 補欄位

確認 `KnowledgeChunk`（`app/rag/retriever.py` 或 `app/rag/schemas.py`）有以下欄位：

```python
vector_score: float = 0.0
keyword_score: float = 0.0
combined_score: float = 0.0
```

## 步驟 4：修改 `RAGRetriever.search()`

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
            "query_text": query,
            "match_count": k,
            "vector_weight": vector_weight,
            "keyword_weight": keyword_weight,
        },
    ).execute()
    return [KnowledgeChunk(**row) for row in result.data]
```

## 步驟 5：改進 Log

`app/graph/nodes.py` 的 `retrieve_one_node`，在 chunk 回傳後加：

```python
for chunk in chunks:
    logger.debug(
        "chunk id=%s vector=%.3f keyword=%.3f combined=%.3f",
        chunk.id, chunk.vector_score, chunk.keyword_score, chunk.combined_score,
    )
```

## 步驟 6：撰寫測試

`tests/test_retriever.py` 補充（mock Supabase RPC）：

```python
@pytest.mark.asyncio
async def test_hybrid_enabled_passes_weights(mock_supabase, settings_hybrid):
    # mock_supabase 驗證 rpc 呼叫時的 keyword_weight == 0.3
    retriever = RAGRetriever(settings_hybrid, mock_supabase)
    await retriever.search("測試查詢")
    call_args = mock_supabase.rpc.call_args[1]
    assert call_args["params"]["keyword_weight"] == 0.3


def test_weight_validation_fails():
    with pytest.raises(ValueError):
        Settings(HYBRID_ENABLED=True, HYBRID_VECTOR_WEIGHT=0.8, HYBRID_KEYWORD_WEIGHT=0.5)
```

## 步驟 7：`.env.example` 補充

```dotenv
# 混合檢索（BM25 + vector）
HYBRID_ENABLED=false
HYBRID_VECTOR_WEIGHT=0.7
HYBRID_KEYWORD_WEIGHT=0.3
```

---

## 里程碑 ✅

- [ ] `HYBRID_ENABLED=false`（預設）：`keyword_score` log 顯示 0，行為與原本相同
- [ ] `HYBRID_ENABLED=true`：log 顯示非零 `keyword_score`
- [ ] config 驗證：weights 不為 1.0 時拋 `ValueError`
- [ ] （可選）`chunk_recall(hybrid)` ≥ `chunk_recall(vector_only)` + 5%（需 golden.yaml）
- [ ] `pytest tests/test_retriever.py` 全綠

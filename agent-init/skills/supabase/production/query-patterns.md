---
name: supabase-query-patterns-production
description: "生產級查詢模式：Cursor Pagination、Batch ETL、聚合查詢、時序分析"
triggers:
  - "pagination"
  - "cursor"
  - "ETL"
  - "batch insert"
  - "聚合"
  - "大量資料"
finish_conditions:
  - "無 OFFSET pagination"
  - "ETL 寫入有分批（chunk ≤ 10,000）"
  - "聚合查詢有時間邊界"
references:
  - docs/supabase/e-Commerce/README.md
  - docs/supabase/crawler/HEAD-FIRST-crawler-db.md
---

# Query Patterns（生產級）

> ⚠️ **前置條件**：已完成 `foundations/query-basics.md`。
> 本文件對應 e-Commerce / Crawler 進階教材中的查詢規範。

---

## 核心原則

1. **先限縮範圍，再取資料**（project_id scope）
2. **先想索引，再寫 WHERE/ORDER**
3. **先想時間邊界，再碰大表**
4. **嚴禁 OFFSET，只用 cursor**
5. **禁止 SELECT ***
6. **Batch Size 有上限**

## Repo Reality

- `docs/supabase/crawler/HEAD-FIRST-crawler-db.md` — Stage 5: Partition + 時間邊界查詢
- `docs/supabase/e-Commerce/README.md` — Stage 7: 查詢效能規範

---

## Pattern A: Detail Query（單筆）

走 PK 或 unique key。禁止從 JSONB 中 filter。

```python
response = supabase.table('sources') \
    .select('id, name, base_url, status') \
    .eq('id', source_id) \
    .single() \
    .execute()
```

## Pattern B: List Query（列表）

必須有 scope + 排序 + limit。

```python
response = supabase.table('articles') \
    .select('id, title, source_id, created_at') \
    .eq('project_id', project_id) \
    .order('created_at', desc=True) \
    .limit(50) \
    .execute()
```

## Pattern C: Cursor Pagination

**嚴禁 OFFSET**。用 keyset pagination：

```python
# 第一頁
response = supabase.table('crawl_runs') \
    .select('id, status, started_at, created_at') \
    .eq('source_id', source_id) \
    .order('created_at', desc=True) \
    .limit(20) \
    .execute()

# 下一頁：用上一頁最後一筆的 created_at 當 cursor
last_item = response.data[-1]
response = supabase.table('crawl_runs') \
    .select('id, status, started_at, created_at') \
    .eq('source_id', source_id) \
    .lt('created_at', last_item['created_at']) \
    .order('created_at', desc=True) \
    .limit(20) \
    .execute()
```

**SQL 等效**：

```sql
SELECT id, status, started_at, created_at
FROM crawl_runs
WHERE source_id = $1
  AND created_at < $2                      -- cursor
  AND created_at >= NOW() - INTERVAL '30 days'  -- 時間邊界
ORDER BY created_at DESC
LIMIT 20;
```

## Pattern D: Search（Prefix + Full Text）

先做 Prefix Search，再考慮 Full text。**禁止 JSONB 內模糊檢索**。

```python
response = supabase.table('articles') \
    .select('id, title') \
    .eq('project_id', project_id) \
    .ilike('title', f'{keyword}%') \
    .limit(20) \
    .execute()
```

**Full Text Search（需 GIN index）**：

```sql
-- 來自 006_public_api.sql: trigram + full-text 混合搜尋
SELECT p.id, p.title, p.slug,
  ts_rank(
    to_tsvector('simple', coalesce(p.title, '') || ' ' || coalesce(p.description, '')),
    plainto_tsquery('simple', p_query)
  ) AS relevance
FROM shop.products p
WHERE p.title % p_query                                -- trigram similarity
   OR to_tsvector('simple', coalesce(p.title, '') || ' ' || coalesce(p.description, ''))
      @@ plainto_tsquery('simple', p_query)           -- full-text match
ORDER BY relevance DESC
LIMIT p_limit;
```

**前提 index**：
```sql
CREATE INDEX idx_chunks_fts ON rag.chunks USING GIN(to_tsvector('simple', content));
```

## Pattern E: Aggregation（聚合）

**必須有時間邊界和 project scope**。

```sql
-- ✅ 有邊界
SELECT source_id, COUNT(*) AS article_count
FROM articles
WHERE project_id = $1
  AND created_at >= NOW() - INTERVAL '7 days'
GROUP BY source_id
ORDER BY article_count DESC;

-- ❌ 無邊界全表聚合
SELECT COUNT(*) FROM articles;
```

## Pattern F: ETL Batch Insert

**Batch Size 上限**：API ≤ 1,000 筆，Worker/ETL ≤ 10,000 筆。

```python
CHUNK_SIZE = 1000
for i in range(0, len(records), CHUNK_SIZE):
    chunk = records[i:i + CHUNK_SIZE]
    supabase.table('articles').insert(chunk).execute()
```

## Pattern G: Batch Delete（Retention）

```sql
-- 安全的批次刪除
DELETE FROM crawl_runs WHERE id IN (
  SELECT id FROM crawl_runs
  WHERE created_at < $1 LIMIT 50000
);
```

## Pattern H: WebSocket（Realtime）

```python
# ✅ 必須帶 filter
supabase.channel(f'crawl_{project_id}') \
    .on('postgres_changes', {
        'event': 'INSERT',
        'schema': 'public',
        'table': 'crawl_runs',
        'filter': f'project_id=eq.{project_id}'
    }, callback) \
    .subscribe()

# ❌ 全表監聽 → CPU 熔斷
```

## Pattern I: Vector Semantic Search（語意搜尋）

**來自 `migrations/004_rag_schema.sql`**：pgvector + HNSW index。

```sql
-- 基礎語意搜尋：用 cosine distance operator <=>
SELECT c.id, c.content, c.metadata,
  1 - (c.embedding <=> query_embedding) AS similarity
FROM rag.chunks c
WHERE c.collection_id = p_collection_id
  AND c.embedding IS NOT NULL
  AND 1 - (c.embedding <=> query_embedding) >= 0.7  -- similarity threshold
ORDER BY c.embedding <=> query_embedding
LIMIT 5;
```

**前提 index**：
```sql
CREATE INDEX idx_chunks_embedding_hnsw ON rag.chunks
  USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64);
```

**Python（supabase-py + RPC）**：
```python
response = supabase.rpc('api_rag_search', {
    'query_embedding': embedding_vector,
    'p_collection_code': 'my-kb',
    'p_top_k': 5,
    'p_threshold': 0.7
}).execute()
```

## Pattern J: Hybrid Search（語意 + 全文混合）

**來自 `004_rag_schema.sql`**：結合 semantic score 和 fulltext score。

```sql
-- CTE 模式：先各自搜尋，再加權合併
WITH semantic AS (
  SELECT c.id, c.document_id, c.content, c.metadata,
    1 - (c.embedding <=> query_embedding) AS score
  FROM rag.chunks c
  WHERE c.collection_id = p_collection_id AND c.embedding IS NOT NULL
  ORDER BY c.embedding <=> query_embedding
  LIMIT p_top_k * 3
),
fulltext AS (
  SELECT c.id,
    ts_rank(to_tsvector('simple', c.content), plainto_tsquery('simple', query_text)) AS score
  FROM rag.chunks c
  WHERE c.collection_id = p_collection_id
    AND to_tsvector('simple', c.content) @@ plainto_tsquery('simple', query_text)
),
combined AS (
  SELECT s.id, s.document_id, s.content, s.metadata,
    s.score AS semantic_score,
    COALESCE(f.score, 0) AS fulltext_score,
    (0.7 * s.score + 0.3 * COALESCE(f.score, 0)) AS combined_score
  FROM semantic s LEFT JOIN fulltext f ON f.id = s.id
)
SELECT * FROM combined
WHERE semantic_score >= 0.5
ORDER BY combined_score DESC
LIMIT p_top_k;
```

## Pattern K: FOR UPDATE SKIP LOCKED（分散式任務搶佔）

**來自 `003_crawler_schema.sql`**：多個 worker 同時搶任務，不互相阻塞。

```sql
-- Lease-based job queue
UPDATE crawler.crawl_queue
SET status = 'leased',
    lease_token = gen_random_uuid()::TEXT,
    leased_at = NOW(),
    lease_expires_at = NOW() + INTERVAL '5 minutes',
    worker_id = p_worker_id
WHERE id = (
  SELECT id FROM crawler.crawl_queue
  WHERE (status = 'pending' AND scheduled_at <= NOW())
     OR (status = 'leased' AND lease_expires_at < NOW())  -- expired lease recovery
  ORDER BY priority DESC, scheduled_at ASC
  LIMIT 1
  FOR UPDATE SKIP LOCKED    -- 關鍵！跳過被其他 worker 鎖定的列
)
RETURNING *;
```

**教學重點**：
- `FOR UPDATE` — 鎖定選中的列，防止其他 transaction 修改
- `SKIP LOCKED` — 如果列已被鎖定，跳過而不等待
- 組合效果：多個 worker 各自搶到不同任務，零等待
- expired lease recovery：lease 過期的任務自動回收

## Pattern L: Cross-Schema Analytics Function

**來自 `006_public_api.sql`**：跨 schema 的統計查詢包裝為 RPC function。

```sql
CREATE OR REPLACE FUNCTION public.api_crawler_stats()
RETURNS TABLE (
  total_sources  BIGINT, active_sources BIGINT,
  total_articles BIGINT, runs_today     BIGINT,
  failed_today   BIGINT, queue_pending  BIGINT
)
LANGUAGE SQL STABLE SECURITY DEFINER SET search_path = public
AS $$
  SELECT
    (SELECT count(*) FROM crawler.sources),
    (SELECT count(*) FROM crawler.sources WHERE is_enabled = TRUE),
    (SELECT count(*) FROM crawler.articles),
    (SELECT count(*) FROM crawler.crawl_runs WHERE created_at >= CURRENT_DATE),
    (SELECT count(*) FROM crawler.crawl_runs
     WHERE created_at >= CURRENT_DATE AND run_status = 'failed'),
    (SELECT count(*) FROM crawler.crawl_queue WHERE status = 'pending');
$$;
```

---

## AI 自動修正紅線

| 偵測到 | 修正 |
|--------|------|
| OFFSET | 改為 cursor pagination |
| JSONB `->>`做 filter | 要求實體化為 Regular Column |
| 無 filter 的 Realtime | 補上 project_id filter |
| DELETE 無 LIMIT | 改為 Subquery + LIMIT |
| 無時間邊界的聚合 | 加 `WHERE created_at >= ...` |
| 單次 INSERT > 1,000 | 改為 chunk loop |
| 向量搜尋無 HNSW index | 加 `USING hnsw(embedding vector_cosine_ops)` |
| FTS 無 GIN index | 加 `USING GIN(to_tsvector(...))` |
| 分散式搶佔無 SKIP LOCKED | 加 `FOR UPDATE SKIP LOCKED` |

## 參考來源

- `docs/supabase/migrations/003_crawler_schema.sql` — Lease RPC + FOR UPDATE SKIP LOCKED
- `docs/supabase/migrations/004_rag_schema.sql` — Vector search + Hybrid search
- `docs/supabase/migrations/006_public_api.sql` — Cross-schema analytics + FTS
- `docs/supabase/crawler/HEAD-FIRST-crawler-db.md` — Stage 5 查詢效能
- `docs/supabase/e-Commerce/README.md` — Stage 7 查詢規範

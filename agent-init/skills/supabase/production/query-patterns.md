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

## Pattern D: Search

先做 Prefix Search，再考慮 Full text。**禁止 JSONB 內模糊檢索**。

```python
response = supabase.table('articles') \
    .select('id, title') \
    .eq('project_id', project_id) \
    .ilike('title', f'{keyword}%') \
    .limit(20) \
    .execute()
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

## 參考來源

- `docs/supabase/crawler/HEAD-FIRST-crawler-db.md` — Stage 5 查詢效能
- `docs/supabase/e-Commerce/README.md` — Stage 7 查詢規範

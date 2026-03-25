---
name: supabase-large-table-management-production
description: "生產級大表治理：Partition、Retention、Archival（對應 Crawler Stage 5）"
triggers:
  - "partition"
  - "大表"
  - "retention"
  - "archival"
  - "append-heavy"
finish_conditions:
  - "append-heavy 表有 partition 策略"
  - "Retention policy 已定義"
  - "查詢包含 partition key（created_at）"
references:
  - docs/supabase/crawler/HEAD-FIRST-crawler-db.md
---

# Large Table Management（生產級）

> ⚠️ **前置條件**：已完成 foundations/。
> 本文件對應 Crawler HEAD-FIRST Stage 5 的大表管理規範。
> 🏷️ **進階**：當表預估 >1M 列且持續增長時才需要。

## Repo Reality

- `docs/supabase/crawler/HEAD-FIRST-crawler-db.md` — Stage 5: Partition + Retention + 時間邊界查詢

---

## 資料生命週期

```
WRITE → HOT (0-7d) → WARM (7-90d) → COLD (>90d) → DELETE
```

## 何時該 Partition

**全部滿足**才 partition：
1. append-heavy（爬蟲結果、日誌、事件）
2. 列數 >1M 且持續增長
3. 查詢含時間範圍 filter
4. 寫入遠多於更新

**不可 partition**：小表（<1M）、頻繁 UPDATE 的表、核心關聯表。

### Crawler 教材中需要 Partition 的表

| 表 | 原因 | Partition 粒度 |
|----|------|---------------|
| `crawl_runs` | 每次爬蟲產生一筆，append-heavy | 月 |
| `articles` | 爬蟲產出，可能大量增長 | 月 |
| `source_pages` | URL 追蹤，持續增長 | 月 |

### 不需要 Partition 的表

| 表 | 原因 |
|----|------|
| `sources` | 設定表，數量少 |
| `tags` | 小表 |
| `publish_targets` | 小表 |

---

## Partition 實作

```sql
CREATE TABLE IF NOT EXISTS public.crawl_runs (
  id TEXT NOT NULL DEFAULT generate_ulid(),
  source_id TEXT NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
  status TEXT NOT NULL DEFAULT 'pending',
  started_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  pages_crawled INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (id, created_at)    -- 必須包含 partition key
) PARTITION BY RANGE (created_at);

ALTER TABLE public.crawl_runs SET (autovacuum_vacuum_scale_factor = 0.05);
```

**查詢必須包含 partition key**：

```sql
-- ✅ partition pruning
SELECT * FROM crawl_runs
WHERE source_id = $1 AND created_at >= NOW() - INTERVAL '7 days';

-- ❌ 掃描所有 partition
SELECT * FROM crawl_runs WHERE source_id = $1;
```

## Retention Policy

| 類別 | 範例表 | 保留期限 |
|------|--------|---------|
| Core（永久） | sources, tags, publish_targets | ∞ |
| Medium（90d） | crawl_runs, articles | archive → delete |
| Short（30d） | 暫存結果 | 直接 delete |

**Append-heavy 表嚴禁 Soft Delete** → 硬刪除 + Archival。

## Archival

```
1. SELECT 過期資料（batch 10K-50K）
2. 匯出 NDJSON 或 Parquet
3. 上傳 Storage
4. 驗證 checksum
5. DELETE（batch LIMIT 50,000）
```

## Batch Delete

```sql
DELETE FROM crawl_runs WHERE ctid IN (
  SELECT ctid FROM crawl_runs
  WHERE created_at < NOW() - INTERVAL '90 days'
  LIMIT 50000
);
```

## 監控

```sql
SELECT
  schemaname || '.' || relname AS table,
  pg_size_pretty(pg_total_relation_size(relid)) AS total_size,
  n_live_tup AS live_rows,
  n_dead_tup AS dead_rows,
  ROUND(100.0 * n_dead_tup / NULLIF(n_live_tup, 0), 1) AS dead_pct
FROM pg_stat_user_tables
ORDER BY pg_total_relation_size(relid) DESC
LIMIT 10;
```

## 參考來源

- `docs/supabase/crawler/HEAD-FIRST-crawler-db.md` — Stage 5
- PostgreSQL Partitioning Documentation

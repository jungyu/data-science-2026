---
name: supabase-scaling-guidelines-production
description: "生產級規模化指南：瓶頸識別與紅線規範"
triggers:
  - "scaling"
  - "效能瓶頸"
  - "連線池"
  - "規模"
finish_conditions:
  - "無 OFFSET"
  - "RLS 用 helper function"
  - "大表有 partition"
  - "ETL 有分批"
references:
  - docs/supabase/e-Commerce/README.md
  - docs/supabase/crawler/HEAD-FIRST-crawler-db.md
---

# Scaling Guidelines（生產級）

> ⚠️ **前置條件**：已完成 foundations/ + 至少一份進階教材。
> 🏷️ **進階**：適用於期末專題規模化、或資料量開始增長的場景。

## Repo Reality

- `docs/supabase/e-Commerce/README.md` — Stage 8-10: 規模化考量
- `docs/supabase/crawler/HEAD-FIRST-crawler-db.md` — Stage 5: 大表管理

---

## 核心原則

資料庫不會因為「資料太多」而死，而是因為：
- ❌ 被要求做錯誤的事情（OFFSET, SELECT *, JSONB filter）
- ❌ 每個 request 都做過多計算（RLS JOIN, auth.uid() 每列重算）
- ❌ 沒有 lifecycle（資料沒有死亡機制）
- ❌ 鎖定機制破壞可用性（大表 CREATE INDEX 不加 CONCURRENTLY）

---

## 瓶頸層級

### Layer 1: RLS 計算過重

**紅線**：Policy 內 JOIN/EXISTS
**修正**：Helper function + composite index
**信號**：CPU 高、查詢時間隨資料量線性成長

### Layer 2: 連線耗盡

**紅線**：每 request 建立 connection、無 statement_timeout
**修正**：Connection pooler（Supavisor）+ statement_timeout

**連線池設定**（期末專題部署時需要）：

```toml
[db.pooler]
enabled = true
pool_mode = "transaction"
default_pool_size = 50
```

### Layer 3: 大表膨脹

**紅線**：append-heavy 表未 partition、用 Soft Delete
**修正**：`PARTITION BY RANGE (created_at)` + `autovacuum_vacuum_scale_factor = 0.05` + 硬刪除

### Layer 4: Index Bloat & JSONB

**紅線**：JSONB 做列表過濾、超過 5 個複合 index
**修正**：高頻欄位實體化為 column

### Layer 5: 查詢模式

**紅線**：OFFSET、無邊界聚合、單次 INSERT > 10K
**修正**：Cursor pagination + 時間邊界 + Batch chunk

### Layer 6: Migration 鎖表

**紅線**：大表 `CREATE INDEX` 不加 `CONCURRENTLY`、新增欄位帶 DEFAULT
**修正**：`CONCURRENTLY` + 先 NULL 後 backfill

### Layer 7: Realtime 過載

**紅線**：全表 Realtime 訂閱無 filter
**修正**：`filter: project_id=eq.${id}`

---

## Layer 8: Cross-Schema Analytics（跨領域觀測）

**來自 `migrations/005_analytics_schema.sql`**：

### Append-Only Event Log

所有 schema 的關鍵事件匯入統一事件表，**永遠不 UPDATE/DELETE**。

```sql
CREATE TABLE IF NOT EXISTS analytics.events (
  id          TEXT PRIMARY KEY DEFAULT public.generate_ulid(),
  schema_name TEXT        NOT NULL,    -- 'shop', 'crawler', 'rag'
  event_type  TEXT        NOT NULL,    -- 'order.created', 'crawl.completed'
  entity_type TEXT        NOT NULL,
  entity_id   TEXT,
  actor_id    TEXT,
  payload     JSONB       NOT NULL DEFAULT '{}'::JSONB,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT ck_events_type CHECK (event_type ~ '^[a-z_]+\.[a-z_]+$')
);

CREATE INDEX idx_events_schema_type ON analytics.events(schema_name, event_type, created_at DESC);
CREATE INDEX idx_events_payload ON analytics.events USING GIN(payload);
```

### Daily Snapshot Tables（每日聚合快照）

**為什麼不用 Materialized View 就好？** 因為 MATVIEW REFRESH 整張重建，歷史資料會丟失。Snapshot table 保留每一天的快照，可做趨勢分析。

```sql
CREATE TABLE IF NOT EXISTS analytics.daily_shop_stats (
  id              TEXT PRIMARY KEY DEFAULT public.generate_ulid(),
  stat_date       DATE NOT NULL,
  total_orders    INTEGER NOT NULL DEFAULT 0,
  total_revenue   NUMERIC(14,2) NOT NULL DEFAULT 0,
  avg_order_value NUMERIC(12,2) NOT NULL DEFAULT 0,
  CONSTRAINT uq_daily_shop_stats_date UNIQUE (stat_date)
);
```

### Materialized View + REFRESH CONCURRENTLY

```sql
CREATE MATERIALIZED VIEW IF NOT EXISTS analytics.mv_product_performance AS
  SELECT p.id, p.title, count(DISTINCT oi.order_id) AS order_count, ...
  FROM shop.products p JOIN shop.order_items oi ON ...
  GROUP BY p.id;

-- REFRESH CONCURRENTLY 需要 UNIQUE INDEX
CREATE UNIQUE INDEX idx_mv_product_perf_id ON analytics.mv_product_performance(id);

-- pg_cron 排程：SELECT cron.schedule('refresh-mv', '0 * * * *', 'REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.mv_product_performance');
```

### 何時用什麼

| 需求 | 方案 | 範例 |
|------|------|------|
| 即時事件追蹤 | Event log（append-only） | `analytics.events` |
| 每日趨勢分析 | Daily snapshot table | `analytics.daily_shop_stats` |
| 快速查詢聚合結果 | Materialized View + cron refresh | `analytics.mv_product_performance` |
| 前端 dashboard | PostgREST function（bridge） | `public.api_analytics_dashboard()` |

---

## 最終原則

```
DB = source of truth + secure enclave
Storage = 大檔案 + 歷史資料
Workers = ETL + heavy jobs
Analytics schema = 跨領域觀測層（不存原始資料，只存聚合/事件/快照）
```

**"不是資料庫慢，是查詢寫錯了。"**

## Scaling Checklist

所有期末專題 / 進階專案應通過：

```
□ 無 OFFSET pagination
□ RLS 使用 helper function
□ Append 表有 partition 策略
□ 大表 Migration 安全（CONCURRENTLY）
□ JSONB 不做列表過濾（有 GIN index）
□ 向量搜尋有 HNSW index
□ 全文搜尋有 GIN index
□ ETL 有 batch 截斷
□ 聚合查詢有時間邊界
□ Realtime 訂閱有 scope filter
□ Cross-schema analytics 不直接查原始表
□ 大型欄位用 VIEW 遮蔽
```

## 參考來源

- `docs/supabase/migrations/005_analytics_schema.sql` — Event log + Snapshot + MATVIEW
- `docs/supabase/migrations/006_public_api.sql` — Cross-schema analytics RPC
- `docs/supabase/e-Commerce/README.md` — Stage 8-10
- `docs/supabase/crawler/HEAD-FIRST-crawler-db.md` — Stage 5

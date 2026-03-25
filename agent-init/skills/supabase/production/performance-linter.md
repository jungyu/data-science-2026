---
name: supabase-performance-linter-production
description: "生產級效能守門員：阻止低效能 SQL、錯誤 Schema、擴展性災難"
triggers:
  - "效能"
  - "performance"
  - "慢查詢"
  - "linter"
  - "OFFSET"
finish_conditions:
  - "無 OFFSET pagination"
  - "無 SELECT *"
  - "無無邊界聚合"
  - "大表有 partition 策略"
references:
  - docs/supabase/e-Commerce/README.md
  - docs/supabase/crawler/HEAD-FIRST-crawler-db.md
---

# 🛡️ Performance Linter（生產級）

> ⚠️ **前置條件**：已完成 `foundations/query-basics.md`。

## Repo Reality

- `docs/supabase/e-Commerce/README.md` — Stage 8-9: 效能 + 規模化規範
- `docs/supabase/crawler/HEAD-FIRST-crawler-db.md` — Stage 5: 大表管理

---

## 執行模式

偵測到違規時：❌ 中止生成 → ⚠️ 說明原因 → 🔧 提供修正版本

---

## Rule Group 1: Query Performance

### ❌ 禁止 OFFSET 分頁
→ ✅ 改為 Cursor（見 `query-patterns.md` Pattern C）

### ❌ 禁止 JSONB 做列表過濾
```sql
SELECT * FROM articles WHERE payload->>'status' = 'failed'  -- ❌
```
→ ✅ 將高頻過濾條件抽為獨立 column

### ❌ 禁止無邊界全表掃描
→ ✅ 加 project_id scope + 時間邊界

---

## Rule Group 2: RLS Safety

### ❌ 禁止 Policy 內 JOIN/EXISTS
→ ✅ 改用 Helper Function（見 `rls-patterns.md`）

### ❌ 禁止在 API Route 濫用 service_role
→ ✅ 一般 API 用 SSR Client + JWT。service_role 僅限 ETL/Cron/Webhook。

---

## Rule Group 3: Schema

### ❌ 禁止 UUID + ULID 混用（業務表）
→ ✅ 統一 TEXT (ULID)

### ❌ 禁止全域 Realtime 訂閱
→ ✅ 必須帶 `filter: project_id=eq.${id}`

---

## Rule Group 4: Migration Safety

### ❌ 大表建 index 禁止不加 CONCURRENTLY
```sql
CREATE INDEX idx_articles_source ON articles(source_id);  -- ❌ 鎖表
```
→ ✅ `CREATE INDEX CONCURRENTLY ...`（獨立 migration）

### ❌ 大表新增欄位禁止帶 DEFAULT
→ ✅ 先加 NULL column，再背景 backfill

---

## Rule Group 5: Hot Table Protection

> 🏷️ **進階**：適用於 Crawler Stage 5 的 append-heavy 表（`crawl_runs`, `articles`）。

### ❌ append-heavy 表未 partition
→ ✅ `PARTITION BY RANGE (created_at)` + `autovacuum_vacuum_scale_factor = 0.05`

### ❌ append-heavy 表用 Soft Delete
→ ✅ 硬刪除 + Archival

---

## Rule Group 6: Batch Limits

### ❌ 單次 INSERT 無上限
→ ✅ API ≤ 1,000 筆，ETL Worker ≤ 10,000 筆

### ❌ N+1 Query
→ ✅ Batch query 配合 `IN(...)`

---

## 自動修正策略

| 問題 | 修正 |
|------|------|
| OFFSET | cursor pagination |
| JSONB 過濾 | 抽為 Regular Column |
| SERVICE_ROLE 濫用 | SSR Client + JWT |
| REALTIME 無 filter | 加 project_id filter |
| RLS 內 JOIN | Helper function |
| MIGRATION 鎖表 | CONCURRENTLY + 無 DEFAULT |
| 無 PARTITION | Partition + vacuum tuning |
| BULK DELETE 無 LIMIT | LIMIT 50,000 分批 |
| 無邊界聚合 | 加時間範圍 |

---

**"鎖表與 CPU 耗盡比寫錯資料死得更快。分析查詢不加邊界，就是慢性自殺。"**

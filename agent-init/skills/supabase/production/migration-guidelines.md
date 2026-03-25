---
name: supabase-migration-guidelines-production
description: "生產級 Migration 規範：檔案命名、必備元素、Index 策略、冪等性"
triggers:
  - "migration"
  - "CREATE TABLE"
  - "ALTER TABLE"
  - "supabase db push"
finish_conditions:
  - "Migration 含 table + index + trigger + RLS + GRANT"
  - "所有 DDL 冪等"
  - "FK 有 index"
references:
  - docs/supabase/e-Commerce/README.md
  - docs/supabase/crawler/HEAD-FIRST-crawler-db.md
---

# Migration Guidelines（生產級）

> ⚠️ **前置條件**：已完成 `foundations/schema-basics.md`。

## Repo Reality

- `docs/supabase/e-Commerce/README.md` — Stage 2-3: Auth Bridge + 完整 migration 範例
- `docs/supabase/crawler/HEAD-FIRST-crawler-db.md` — Stage 1-4: 從錯誤到正確的 migration

---

## 檔案命名

`YYYYMMDDHHMMSS_<scope>_<description>.sql`

```
20260325120000_public_sources.sql
20260325120001_public_articles.sql
```

## 一份 Migration 的必備元素

```sql
-- 1. Table
CREATE TABLE IF NOT EXISTS public.sources (
  id TEXT PRIMARY KEY DEFAULT generate_ulid(),
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  base_url TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active'
    CHECK (status IN ('active', 'paused', 'archived')),
  created_by TEXT NOT NULL REFERENCES users(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. Indexes
CREATE INDEX IF NOT EXISTS idx_sources_project ON public.sources(project_id);
CREATE INDEX IF NOT EXISTS idx_sources_created ON public.sources(created_at DESC);

-- 3. Trigger
CREATE TRIGGER trg_sources_updated_at
  BEFORE UPDATE ON public.sources
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 4. RLS
ALTER TABLE public.sources ENABLE ROW LEVEL SECURITY;

-- 5. Policies
CREATE POLICY "sources_read" ON public.sources FOR SELECT TO authenticated
  USING (public.is_project_member(project_id));
CREATE POLICY "sources_service_role" ON public.sources FOR ALL TO service_role
  USING (true) WITH CHECK (true);

-- 6. Grants
GRANT SELECT ON public.sources TO authenticated, anon;
GRANT INSERT, UPDATE, DELETE ON public.sources TO authenticated;
GRANT ALL ON public.sources TO service_role;
```

## 冪等性

所有 DDL **必須**冪等：

```sql
CREATE TABLE IF NOT EXISTS ...
CREATE INDEX IF NOT EXISTS ...
CREATE OR REPLACE FUNCTION ...
```

## Index 策略

| Tier | 說明 | 範例 |
|------|------|------|
| 1 | FK 欄位（必做） | `idx_articles_source ON articles(source_id)` |
| 2 | RLS helper 用的 composite（必做） | `idx_pm_project_user ON project_members(project_id, user_id, status)` |
| 3 | 列表查詢 composite | `idx_articles_project_created ON articles(project_id, created_at DESC)` |
| 4 | Partial index | `idx_sources_active ON sources(project_id) WHERE status = 'active'` |
| 5 | GIN for JSONB（僅需要時） | `idx_articles_metadata ON articles USING gin(metadata)` |

## 新增表 Checklist

```
□ id TEXT PRIMARY KEY DEFAULT generate_ulid()
□ project_id + created_at + updated_at 必備
□ FK 型別一致（TEXT）
□ Tier 1: 所有 FK 有 index
□ updated_at trigger
□ RLS enabled + policies + GRANT
□ 所有 DDL 冪等（IF NOT EXISTS）
□ 年資料量 >10M？規劃 partition
```

## 禁止事項

| 禁止 | 原因 |
|------|------|
| ❌ migration 不含 RLS | 表對 authenticated 完全開放 |
| ❌ migration 不含 index | FK 和 RLS 都慢 |
| ❌ 隱式 constraint | 難以後續修改 |
| ❌ 大量 data migration 不分批 | 鎖表風險 |

## 參考來源

- `docs/supabase/crawler/HEAD-FIRST-crawler-db.md` — 完整修正範例
- `docs/supabase/e-Commerce/README.md` — 20 張表的 migration 範本

---
name: supabase-rls-patterns-production
description: "生產級 RLS：Helper Function 模式、auth.uid() 最佳化、Composite Index、多租戶隔離"
triggers:
  - "RLS 進階"
  - "helper function"
  - "SECURITY DEFINER"
  - "多租戶"
  - "service_role"
finish_conditions:
  - "Policy 使用 helper function（非 inline JOIN）"
  - "auth.uid() 用 subselect 包裝"
  - "RLS 欄位有 composite index"
  - "service_role policy 已加"
  - "GRANT 語句已加"
references:
  - docs/supabase/e-Commerce/README.md
  - docs/supabase/crawler/HEAD-FIRST-crawler-db.md
---

# RLS Patterns（生產級）

> ⚠️ **前置條件**：已完成 `foundations/rls-basics.md`。
> 本文件對應 e-Commerce Stage 9 和 Crawler Stage 4 的 RLS 規範。

## Repo Reality

- `docs/supabase/e-Commerce/README.md` — Stage 9: Helper Function + 3 層安全模式
- `docs/supabase/crawler/HEAD-FIRST-crawler-db.md` — Stage 4: 10 張表的 RLS 修正

---

## 與基礎的差異

| foundations/ 教的 | production/ 要求的 |
|------------------|-------------------|
| `auth.uid() = user_id` | Helper function（`is_project_member()`） |
| 無 GRANT | 必須有 GRANT |
| 無 service_role policy | 必須有 |
| 無 index 要求 | Policy 欄位必須有 composite index |

---

## 核心規則

### 1. 禁止在 Policy 內寫 JOIN

```sql
-- ❌ e-Commerce Stage 9 的反面教材
USING (EXISTS (SELECT 1 FROM project_members pm JOIN ...))

-- ✅ 正確
USING (public.is_project_member(project_id))
```

### 2. auth.uid() 最佳化

```sql
USING (auth_user_id = (SELECT auth.uid()))   -- ✅ initPlan，只算一次
USING (auth_user_id = auth.uid())            -- ❌ 每列重算
```

更好：`USING (created_by = public.get_current_user_id())`

### 3. Helper Function 規範

```sql
CREATE OR REPLACE FUNCTION public.is_project_member(p_project_id TEXT)
RETURNS BOOLEAN
LANGUAGE SQL
STABLE                    -- query planner 可快取
SECURITY DEFINER          -- 繞過 RLS 遞迴
SET search_path = public  -- 安全性
AS $$
  SELECT EXISTS (
    SELECT 1 FROM project_members
    WHERE project_id = p_project_id
      AND user_id = public.get_current_user_id()
      AND status = 'active'
  );
$$;

GRANT EXECUTE ON FUNCTION public.is_project_member(TEXT) TO authenticated;
```

### 4. JWT app_metadata 多租戶隔離

**來自 `migrations/003_crawler_schema.sql`**：用 JWT custom claim 做租戶 scoping，不需要 `project_members` 表。

```sql
-- Helper: 取得當前用戶可存取的 project_ids（從 JWT app_metadata）
CREATE OR REPLACE FUNCTION crawler.get_my_project_ids()
RETURNS TEXT[]
LANGUAGE SQL
STABLE
SECURITY DEFINER
SET search_path = crawler
AS $$
  SELECT COALESCE(
    ARRAY(
      SELECT jsonb_array_elements_text(
        (SELECT auth.jwt()) -> 'app_metadata' -> 'project_ids'
      )
    ),
    '{}'::TEXT[]
  );
$$;

GRANT EXECUTE ON FUNCTION crawler.get_my_project_ids() TO authenticated;

-- Helper: 檢查用戶是否可存取特定 project
CREATE OR REPLACE FUNCTION crawler.has_project_access(p_project_id TEXT)
RETURNS BOOLEAN
LANGUAGE SQL
STABLE
SECURITY DEFINER
SET search_path = crawler
AS $$
  SELECT p_project_id = ANY(crawler.get_my_project_ids());
$$;

GRANT EXECUTE ON FUNCTION crawler.has_project_access(TEXT) TO authenticated;
```

**JWT app_metadata 設定方式**：

```sql
-- Supabase Dashboard → Authentication → Users → Edit User
-- 或用 SQL：
UPDATE auth.users SET raw_app_meta_data =
  raw_app_meta_data || '{"project_ids":["demo-project"]}'::JSONB
WHERE id = 'user-uuid';
```

**兩種 Helper 模式比較**：

| 模式 | 資料來源 | 適用場景 |
|------|---------|---------|
| `is_project_member()` | `project_members` 表 | 需要角色/權限層級（admin/editor/viewer）|
| `has_project_access()` | JWT `app_metadata` | 簡單租戶隔離，不需額外表 |

### 5. 多層級 RLS Policy 模式

**來自 `migrations/003_crawler_schema.sql`**：不同類型的表需要不同 RLS 策略。

#### 主表（有 project_id）— 直接 tenant scoping

```sql
-- sources, crawl_runs, articles 等
CREATE POLICY "sources_select" ON crawler.sources
  FOR SELECT TO authenticated
  USING (crawler.has_project_access(project_id));
CREATE POLICY "sources_insert" ON crawler.sources
  FOR INSERT TO authenticated
  WITH CHECK (crawler.has_project_access(project_id));
CREATE POLICY "sources_update" ON crawler.sources
  FOR UPDATE TO authenticated
  USING (crawler.has_project_access(project_id));
CREATE POLICY "sources_delete" ON crawler.sources
  FOR DELETE TO authenticated
  USING (crawler.has_project_access(project_id));
```

#### Reference 表（有 project_id + 公開讀取）

```sql
-- tags, publish_targets — authenticated + anon 可讀
CREATE POLICY "tags_select" ON crawler.tags
  FOR SELECT TO authenticated, anon
  USING (crawler.has_project_access(project_id));
CREATE POLICY "tags_insert" ON crawler.tags
  FOR INSERT TO authenticated
  WITH CHECK (crawler.has_project_access(project_id));
```

#### Junction 表（無 project_id）— 透過 FK 繼承

```sql
-- article_tags, article_publications — 無自身 project_id
CREATE POLICY "article_tags_select" ON crawler.article_tags
  FOR SELECT TO authenticated, anon USING (true);
CREATE POLICY "article_tags_insert" ON crawler.article_tags
  FOR INSERT TO authenticated WITH CHECK (true);
```

#### Owner-Based（RAG 模式）

**來自 `migrations/004_rag_schema.sql`**：用反正規化 `owner_id` + 組合條件。

```sql
-- collections: owner 可寫，active 的任何人可讀
CREATE POLICY "collections_read" ON rag.collections
  FOR SELECT TO authenticated, anon
  USING (is_active = TRUE OR owner_id = rag.get_current_owner_id());
CREATE POLICY "collections_insert" ON rag.collections
  FOR INSERT TO authenticated
  WITH CHECK (owner_id = rag.get_current_owner_id());

-- documents: 透過 collection owner 判斷寫入權限
CREATE POLICY "documents_write" ON rag.documents
  FOR INSERT TO authenticated
  WITH CHECK (rag.is_collection_owner(collection_id));
```

#### 批次建立 Policy（DRY）

```sql
-- 來自 003_crawler_schema.sql：用 DO block 批次建立
DO $$
DECLARE tbl TEXT;
BEGIN
  FOREACH tbl IN ARRAY ARRAY[
    'crawl_runs', 'crawl_queue', 'source_pages', 'articles', 'article_assets'
  ]
  LOOP
    EXECUTE format('
      CREATE POLICY "%1$s_select" ON crawler.%1$s
        FOR SELECT TO authenticated
        USING (crawler.has_project_access(project_id));
      CREATE POLICY "%1$s_service_role" ON crawler.%1$s
        FOR ALL TO service_role USING (true) WITH CHECK (true);
    ', tbl);
  END LOOP;
END;
$$;
```

### 6. Policy 欄位必須有 Index

```sql
-- 單欄 FK index（每張表都要）
CREATE INDEX idx_<table>_project ON <schema>.<table>(project_id);

-- 權限表的 composite index（效能關鍵）
CREATE INDEX idx_project_members_project_user_status
  ON public.project_members(project_id, user_id, status);
```

### 7. Service Role 使用限制

**僅允許**：
1. ETL Pipeline（無使用者 Session）
2. Cron Jobs（排程任務）
3. Webhook Handler（外部 Callback）
4. `SECURITY DEFINER` 函式

**禁止**：在有使用者登入的 API Route 中使用 service_role bypass RLS。

---

## 常見錯誤

| 錯誤 | 症狀 | 修正 |
|------|------|------|
| Policy 內 JOIN | 查詢 >200ms | Helper function |
| Policy 欄位無 index | seq scan | 加 index |
| 忘記 SECURITY DEFINER | RLS 遞迴錯誤 | 加在 helper function |
| 忘記 GRANT | 使用者無法存取 | 加 GRANT 語句 |
| ETL 被 RLS 擋住 | INSERT 失敗 | 加 service_role policy |
| Junction 表用 project_id scoping | 無法 JOIN | Junction 表用 `USING (true)` |
| Helper 沒有 `SET search_path` | search_path injection | 加 `SET search_path = <schema>` |
| JWT claim 不存在 | policy 永遠 false | 確保 `app_metadata` 有設定 |

## 參考來源

- `docs/supabase/migrations/003_crawler_schema.sql` — JWT app_metadata + 多層級 RLS
- `docs/supabase/migrations/004_rag_schema.sql` — Owner-based RLS + 反正規化 owner_id
- `docs/supabase/e-Commerce/README.md` — Stage 9: 完整 RLS 架構
- `docs/supabase/crawler/HEAD-FIRST-crawler-db.md` — Stage 4: RLS 修正

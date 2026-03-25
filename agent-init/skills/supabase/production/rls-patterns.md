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

### 4. Policy 欄位必須有 Index

```sql
-- 單欄 FK index（每張表都要）
CREATE INDEX idx_<table>_project ON public.<table>(project_id);

-- 權限表的 composite index（效能關鍵）
CREATE INDEX idx_project_members_project_user_status
  ON public.project_members(project_id, user_id, status);
```

### 5. 新表 Policy 模板

```sql
-- 啟用 RLS
ALTER TABLE public.<table> ENABLE ROW LEVEL SECURITY;

-- READ：project member 可讀
CREATE POLICY "<table>_read_access"
  ON public.<table> FOR SELECT TO authenticated
  USING (public.is_project_member(project_id));

-- WRITE：project editor 可寫
CREATE POLICY "<table>_write_access"
  ON public.<table> FOR INSERT TO authenticated
  WITH CHECK (public.is_project_member(project_id));

-- DELETE：admin only
CREATE POLICY "<table>_delete_access"
  ON public.<table> FOR DELETE TO authenticated
  USING (public.is_project_admin(project_id));

-- Service role（ETL/Cron 用）
CREATE POLICY "<table>_service_role"
  ON public.<table> FOR ALL TO service_role
  USING (true) WITH CHECK (true);

-- GRANT
GRANT SELECT ON public.<table> TO authenticated, anon;
GRANT INSERT, UPDATE, DELETE ON public.<table> TO authenticated;
GRANT ALL ON public.<table> TO service_role;
```

### 6. Service Role 使用限制

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

## 參考來源

- `docs/supabase/e-Commerce/README.md` — Stage 9: 完整 RLS 架構
- `docs/supabase/crawler/HEAD-FIRST-crawler-db.md` — Stage 4: RLS 修正

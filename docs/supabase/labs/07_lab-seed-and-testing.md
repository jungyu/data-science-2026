# Lab：Seed Data 策略 + RLS 驗證方法

> 從空白資料庫到完整 RLS 測試，手把手走過 seed data 注入與角色模擬驗證。
>
> 對應 migration：`012_seed_data.sql`、`013_rls_testing.sql`

---

## 學習目標

- 理解為什麼 seed data 對開發與測試不可或缺
- 掌握 auth.users 直接 INSERT 的 trigger 管理技巧
- 學會用 `SET ROLE` + JWT claims 模擬不同角色
- 驗證 RLS policy 是否正確拒絕/允許存取
- 用 `EXPLAIN` 確認 policy 被注入查詢計畫
- 偵錯常見 RLS 設定錯誤

---

## 前置準備

- 已執行 migration `001` 至 `011`（所有 schema 與 RLS policy 已建立）
- 開啟 SQL Editor（Dashboard → SQL Editor）
- 確認目前身份是 superuser（預設就是）

```sql
-- 確認 pgcrypto 可用（seed data 需要 crypt + gen_salt）
SELECT extname, extversion FROM pg_extension WHERE extname = 'pgcrypto';
-- 應回傳一筆，extversion >= '1.3'

-- 確認四個 schema 都存在
SELECT schema_name FROM information_schema.schemata
WHERE schema_name IN ('shop', 'crawler', 'rag', 'analytics')
ORDER BY schema_name;
-- 應回傳 4 筆
```

---

## Stage 1：為什麼需要 Seed Data

### 1.1 空表的痛苦

執行完所有 migration 後，你的資料庫很「乾淨」— 也很「沒用」：

```
shop.products   → 0 rows   → 無法測試商品列表 API
shop.orders     → 0 rows   → 無法測試 RLS 隔離
crawler.sources → 0 rows   → 無法驗證 multi-tenant 過濾
rag.chunks      → 0 rows   → 無法跑語意搜尋
```

**三個場景需要 seed data**：

| 場景 | 問題 | seed 解法 |
|------|------|-----------|
| 開發 | 畫面都是空白 | 填入範例商品、訂單、文章 |
| 測試 | RLS policy 無法驗證 | 建立不同角色的使用者 |
| Demo | 無法展示功能 | 提供完整購物流程資料 |

### 1.2 Seed Data 的設計原則

```
❌ 隨機亂塞   → 找不到、測不了、難除錯
✅ 固定 ID    → 方便 script 直接引用
✅ 角色多樣   → admin / staff / customer 都要有
✅ 冪等可重跑 → ON CONFLICT DO NOTHING
✅ 有業務意義  → 訂單有不同狀態（pending / delivered / cancelled）
```

---

## Stage 2：Seed Data 技巧

### 2.1 Trigger 管理 — 最容易踩坑的地方

Supabase 的 auth.users 通常有 trigger（例如 `on_auth_user_created`），會自動在 shop.users 建立對應記錄。但 seed data 需要固定 ID，所以必須：

```sql
-- Step 1: 暫停 trigger
ALTER TABLE auth.users DISABLE TRIGGER on_auth_user_created;

-- Step 2: 直接 INSERT auth.users（用固定 UUID）
INSERT INTO auth.users (id, email, encrypted_password, email_confirmed_at, created_at, updated_at, instance_id, aud, role)
VALUES
  ('00000000-0000-0000-0000-000000000001',
   'admin@seed.local',
   crypt('seed-password', gen_salt('bf')),  -- bcrypt 雜湊
   NOW() - INTERVAL '90 days',
   NOW() - INTERVAL '90 days',
   NOW(),
   '00000000-0000-0000-0000-000000000000',
   'authenticated',
   'authenticated')
ON CONFLICT (id) DO NOTHING;  -- 可重複執行不報錯

-- Step 3: 手動建 shop.users（用固定 SEED ID）
INSERT INTO shop.users (id, auth_user_id, created_at) VALUES
  ('SEED_USR_ADMIN001', '00000000-0000-0000-0000-000000000001', NOW() - INTERVAL '90 days')
ON CONFLICT (id) DO NOTHING;

-- Step 4: 恢復 trigger
ALTER TABLE auth.users ENABLE TRIGGER on_auth_user_created;
```

> **腦筋急轉彎**：如果忘記 Step 4（恢復 trigger），之後正式註冊的使用者會怎樣？
>
> 答：auth.users 會有記錄，但 shop.users 不會自動建立 → 所有跟 shop.users 有 FK 的操作都會失敗。

### 2.2 密碼雜湊 — crypt() + gen_salt()

```sql
-- pgcrypto 提供的 bcrypt 雜湊
crypt('seed-password', gen_salt('bf'))
-- 回傳類似 $2a$06$xxxxxxxxxxxxxxxxxxxxxxxxxxxxx

-- 為什麼不能直接寫明文？
-- → auth.users.encrypted_password 是 Supabase Auth 讀取的欄位
-- → 明文密碼無法通過驗證流程
```

### 2.3 ON CONFLICT DO NOTHING — 冪等 seeding

```sql
-- 第一次執行：INSERT 5 筆
-- 第二次執行：0 筆（全部 conflict，但不報錯）
-- 第 N 次執行：同樣 0 筆，永遠安全

INSERT INTO shop.products (id, title, ...)
VALUES ('SEED_PRD_001', 'PostgreSQL 實戰手冊', ...)
ON CONFLICT (id) DO NOTHING;
```

### 2.4 角色多樣性 — 5 個使用者覆蓋所有 RLS 路徑

| User | Email | 角色 | 用途 |
|------|-------|------|------|
| admin | admin@seed.local | Super Admin（app_metadata.role = 'super_admin'） | 測試最高權限 |
| staff01 | staff@seed.local | Staff（is_staff = TRUE） | 測試店員權限 |
| alice | alice@seed.local | Customer | 測試一般顧客（有訂單） |
| bob | bob@seed.local | Customer | 測試 pending 訂單 + 取消流程 |
| carol | carol@seed.local | Customer | 測試 cancelled 訂單 |

### 2.5 刷新 Materialized View

```sql
-- seed data 進去後，analytics 的 MATVIEW 仍是空的
-- 必須手動刷新才能看到統計資料
REFRESH MATERIALIZED VIEW analytics.mv_system_health;
REFRESH MATERIALIZED VIEW analytics.mv_product_ranking;
REFRESH MATERIALIZED VIEW analytics.mv_source_health;
```

### 2.6 動手：執行完整 Seed Script

```sql
-- 在 SQL Editor 執行 012_seed_data.sql 的完整內容
-- 完成後，驗證資料量：
SELECT 'shop.users'       AS tbl, count(*) FROM shop.users
UNION ALL
SELECT 'shop.products',          count(*) FROM shop.products
UNION ALL
SELECT 'shop.orders',            count(*) FROM shop.orders
UNION ALL
SELECT 'crawler.sources',        count(*) FROM crawler.sources
UNION ALL
SELECT 'rag.collections',        count(*) FROM rag.collections
UNION ALL
SELECT 'rag.chunks',             count(*) FROM rag.chunks;
-- 預期：5, 5, 3, 3, 2, 7
```

---

## Stage 3：RLS 測試 — SET ROLE 模擬

### 3.1 Supabase 的三個角色

```
anon           → 未登入使用者（瀏覽商品、公開頁面）
authenticated  → 已登入使用者（配合 JWT 判斷身份）
service_role   → 後端服務（繞過所有 RLS，危險但必要）
```

### 3.2 基本角色切換

```sql
-- 以 anon 身份查詢（模擬未登入）
SET ROLE anon;

-- 能看到 published 商品嗎？
SELECT count(*) AS visible_products FROM shop.products;
-- 預期：5（所有 seed 商品都是 publish 狀態）

-- 能看到訂單嗎？
SELECT count(*) AS visible_orders FROM shop.orders;
-- 預期：0 ← anon 沒有 orders 的 SELECT policy

-- 能看到 crawler 資料嗎？
SELECT count(*) AS visible_sources FROM crawler.sources;
-- 預期：0 ← crawler 需要 authenticated + project_id

-- 恢復 superuser 身份
RESET ROLE;
```

> **重要**：每段測試結束一定要 `RESET ROLE;`，不然後續 SQL 都以受限角色執行。

### 3.3 完整模擬 — SET ROLE + JWT Claims

只有 `SET ROLE` 還不夠。RLS policy 裡的 `auth.uid()` 需要 JWT claims 才能判斷身份：

```sql
-- 模擬 Alice（一般顧客）
SET ROLE authenticated;
SET request.jwt.claims = '{
  "sub": "00000000-0000-0000-0000-000000000003",
  "role": "authenticated",
  "aud": "authenticated",
  "app_metadata": {}
}';

-- Alice 只看到自己的訂單
SELECT id, status, total FROM shop.orders;
-- 預期：1 筆 — SEED_ORD_001（delivered, 3160.00）

-- Alice 看不到 Bob、Carol 的訂單
-- （不需要特別查，上面的結果就只有 1 筆）

-- Alice 的地址
SELECT id, label, city FROM shop.addresses;
-- 預期：SEED_ADR_001（home, 台北市）

RESET ROLE;
```

### 3.4 模擬 Staff

```sql
SET ROLE authenticated;
SET request.jwt.claims = '{
  "sub": "00000000-0000-0000-0000-000000000002",
  "role": "authenticated",
  "aud": "authenticated",
  "app_metadata": {}
}';

-- Staff 看到所有訂單
SELECT count(*) AS total_orders FROM shop.orders;
-- 預期：3（所有 seed 訂單）

-- Staff 看到公司資料
SELECT id, name FROM shop.companies;
-- 預期：SEED_CMP_001

RESET ROLE;
```

### 3.5 模擬 service_role

```sql
SET ROLE service_role;

-- 看到所有資料，不受 RLS 限制
SELECT count(*) FROM shop.orders;      -- 預期：3
SELECT count(*) FROM crawler.sources;  -- 預期：3
SELECT count(*) FROM rag.chunks;       -- 預期：7

RESET ROLE;
```

---

## Stage 4：RLS 測試 — Helper Function 驗證

### 4.1 測試 get_current_user_id()

```sql
-- 模擬 Alice
SET ROLE authenticated;
SET request.jwt.claims = '{
  "sub": "00000000-0000-0000-0000-000000000003",
  "role": "authenticated",
  "aud": "authenticated",
  "app_metadata": {}
}';

SELECT shop.get_current_user_id() AS my_user_id;
-- 預期：SEED_USR_CUST0001
-- → 這個 function 從 JWT sub 找到對應的 shop.users.id

RESET ROLE;
```

### 4.2 測試 is_staff()

```sql
-- Staff 小明
SET ROLE authenticated;
SET request.jwt.claims = '{
  "sub": "00000000-0000-0000-0000-000000000002",
  "role": "authenticated",
  "aud": "authenticated",
  "app_metadata": {}
}';

SELECT shop.is_staff() AS am_i_staff;
-- 預期：true（小明的 profiles.is_staff = TRUE）

RESET ROLE;

-- Alice（一般顧客）
SET ROLE authenticated;
SET request.jwt.claims = '{
  "sub": "00000000-0000-0000-0000-000000000003",
  "role": "authenticated",
  "aud": "authenticated",
  "app_metadata": {}
}';

SELECT shop.is_staff() AS am_i_staff;
-- 預期：false

RESET ROLE;
```

### 4.3 測試 is_super_admin()

```sql
-- Admin（有 app_metadata.role = 'super_admin'）
SET ROLE authenticated;
SET request.jwt.claims = '{
  "sub": "00000000-0000-0000-0000-000000000001",
  "role": "authenticated",
  "aud": "authenticated",
  "app_metadata": {"role": "super_admin"}
}';

SELECT shop.is_super_admin() AS am_i_super_admin;
-- 預期：true

RESET ROLE;

-- Alice（沒有 super_admin）
SET ROLE authenticated;
SET request.jwt.claims = '{
  "sub": "00000000-0000-0000-0000-000000000003",
  "role": "authenticated",
  "aud": "authenticated",
  "app_metadata": {}
}';

SELECT shop.is_super_admin() AS am_i_super_admin;
-- 預期：false

RESET ROLE;
```

### 4.4 測試 has_project_access()（Crawler Multi-Tenant）

```sql
-- 有 demo-project 權限的使用者
SET ROLE authenticated;
SET request.jwt.claims = '{
  "sub": "00000000-0000-0000-0000-000000000001",
  "role": "authenticated",
  "aud": "authenticated",
  "app_metadata": {"project_ids": ["demo-project"]}
}';

SELECT crawler.has_project_access('demo-project') AS can_access;
-- 預期：true

SELECT crawler.has_project_access('other-project') AS can_access;
-- 預期：false

-- 驗證 sources 過濾效果
SELECT id, code, name FROM crawler.sources;
-- 預期：3 筆（都屬於 demo-project）

RESET ROLE;

-- 沒有 demo-project 權限的使用者
SET ROLE authenticated;
SET request.jwt.claims = '{
  "sub": "00000000-0000-0000-0000-000000000003",
  "role": "authenticated",
  "aud": "authenticated",
  "app_metadata": {"project_ids": ["other-project"]}
}';

SELECT count(*) FROM crawler.sources;
-- 預期：0（無權存取 demo-project）

RESET ROLE;
```

---

## Stage 5：RLS 偵錯 — 常見問題

### 5.1 找出沒有啟用 RLS 的表

```sql
-- 任何一張表沒開 RLS = 資安漏洞
SELECT schemaname, tablename
FROM pg_tables
WHERE schemaname IN ('shop', 'crawler', 'rag', 'analytics')
  AND rowsecurity = FALSE;
-- 預期：空（全部都應該開了 RLS）
-- 如果有結果 → 立刻 ALTER TABLE xxx ENABLE ROW LEVEL SECURITY;
```

### 5.2 找出有 RLS 但沒有 Policy 的表

```sql
-- 有 RLS 但沒 policy = 所有人都看不到資料（最隱蔽的 bug）
SELECT t.schemaname, t.tablename
FROM pg_tables t
LEFT JOIN pg_policies p
  ON t.schemaname = p.schemaname AND t.tablename = p.tablename
WHERE t.schemaname IN ('shop', 'crawler', 'rag', 'analytics')
  AND t.rowsecurity = TRUE
  AND p.policyname IS NULL;
-- 預期：空
```

> **腦筋急轉彎**：如果你 `ENABLE RLS` 但不加任何 policy，會怎樣？
>
> 答：那張表對所有非 superuser 角色完全隱形 — SELECT 回傳 0 筆、INSERT 被拒絕。
> 不會報錯，只是「什麼都沒有」，這比報錯更難除錯！

### 5.3 找出缺少 service_role Policy 的表

```sql
-- 後端服務（service_role）需要完整存取權限
-- 缺少 service_role policy → Edge Function 會回 403
SELECT t.schemaname, t.tablename
FROM pg_tables t
WHERE t.schemaname IN ('shop', 'crawler', 'rag', 'analytics')
  AND t.rowsecurity = TRUE
  AND NOT EXISTS (
    SELECT 1 FROM pg_policies p
    WHERE p.schemaname = t.schemaname
      AND p.tablename = t.tablename
      AND 'service_role' = ANY(p.roles)
  );
-- 預期：空
```

### 5.4 EXPLAIN 驗證 Policy 注入

```sql
-- EXPLAIN 可以「看到」RLS policy 被加入 WHERE 條件
SET ROLE authenticated;
SET request.jwt.claims = '{
  "sub": "00000000-0000-0000-0000-000000000003",
  "role": "authenticated",
  "aud": "authenticated",
  "app_metadata": {}
}';

EXPLAIN (COSTS OFF)
SELECT * FROM shop.orders;
-- 預期輸出（簡化）：
--   Seq Scan on orders
--     Filter: ((customer_id = ...) OR (is_staff()) OR (is_super_admin()))
-- → RLS policy 被自動注入為 Filter 條件

EXPLAIN (COSTS OFF)
SELECT * FROM shop.products;
-- 預期：
--   Filter: ((status = 'publish' AND deleted_at IS NULL) OR ...)

RESET ROLE;
```

### 5.5 查看特定表的所有 Policy 細節

```sql
-- 當你懷疑某張表的 policy 有問題，用這個查全貌
SELECT
  policyname,
  permissive,   -- PERMISSIVE = OR 邏輯, RESTRICTIVE = AND 邏輯
  roles,
  cmd,           -- SELECT / INSERT / UPDATE / DELETE / ALL
  qual AS using_expr,
  with_check AS check_expr
FROM pg_policies
WHERE schemaname = 'shop' AND tablename = 'orders'
ORDER BY policyname;
```

### 5.6 Policy 數量統計

```sql
-- 快速掃描：每張表有幾條 policy？
SELECT schemaname, tablename, count(*) AS policy_count
FROM pg_policies
WHERE schemaname IN ('shop', 'crawler', 'rag', 'analytics')
GROUP BY schemaname, tablename
ORDER BY policy_count DESC;
-- 如果某張表只有 1 條 → 可能只有 service_role，忘記加 user-facing policy
```

---

## Stage 6：進階 — Time-Window 與 Column-Level Security

### 6.1 Time-Window Policy：24 小時內可取消訂單

```sql
-- Bob 的 pending 訂單（SEED_ORD_002，約 1 小時前建立）
SET ROLE authenticated;
SET request.jwt.claims = '{
  "sub": "00000000-0000-0000-0000-000000000004",
  "role": "authenticated",
  "aud": "authenticated",
  "app_metadata": {}
}';

-- 嘗試取消 → 應該成功（在 24 小時內）
UPDATE shop.orders
SET status = 'cancelled'
WHERE id = 'SEED_ORD_002';
-- 預期：1 row updated

SELECT id, status FROM shop.orders WHERE id = 'SEED_ORD_002';
-- 預期：status = 'cancelled'

RESET ROLE;
-- 恢復資料（用 superuser）
UPDATE shop.orders SET status = 'pending' WHERE id = 'SEED_ORD_002';
```

```sql
-- Alice 的 delivered 訂單（SEED_ORD_001，20 天前建立）
SET ROLE authenticated;
SET request.jwt.claims = '{
  "sub": "00000000-0000-0000-0000-000000000003",
  "role": "authenticated",
  "aud": "authenticated",
  "app_metadata": {}
}';

UPDATE shop.orders
SET status = 'cancelled'
WHERE id = 'SEED_ORD_001';
-- 預期：0 rows updated
-- → 超過 24 小時 + 狀態已經是 delivered → policy 拒絕

RESET ROLE;
```

### 6.2 Column-Level Security：embedding 欄位遮蔽

RAG 的 embedding vector（1536 維浮點數）是高價值資產，不應該暴露給一般 API：

```sql
SET ROLE authenticated;

-- 直接查 rag.chunks → 包含 embedding 欄位
SELECT id, left(content, 50) AS content_preview,
       embedding IS NOT NULL AS has_embedding
FROM rag.chunks
LIMIT 3;
-- 預期：has_embedding = false（seed 沒有真正的 vector）
-- 但重點是：這個查詢「能」存取 embedding 欄位

-- 查 rag.chunks_safe VIEW → 沒有 embedding 欄位
SELECT * FROM rag.chunks_safe LIMIT 3;
-- 預期：欄位列表中看不到 embedding

RESET ROLE;
```

> **設計思路**：前端 API 指向 `chunks_safe` VIEW，後端 embedding pipeline 直接用 `chunks` 表。
> 同一份資料、不同存取介面、不同欄位可見度。

### 6.3 Cross-Schema Helper Functions

```sql
-- RLS policy 中跨 schema 呼叫 helper function 的範例
-- rag schema 的 policy 可以呼叫 shop schema 的 function

SET ROLE authenticated;
SET request.jwt.claims = '{
  "sub": "00000000-0000-0000-0000-000000000001",
  "role": "authenticated",
  "aud": "authenticated",
  "app_metadata": {"project_ids": ["demo-project"]}
}';

-- 同時查詢不同 schema，各自受其 RLS policy 保護
SELECT 'shop'    AS schema, count(*) FROM shop.orders
UNION ALL
SELECT 'crawler',          count(*) FROM crawler.sources
UNION ALL
SELECT 'rag',              count(*) FROM rag.collections;

RESET ROLE;
```

---

## RLS Pattern 速查表

| Pattern | 範例 | 特色 |
|---------|------|------|
| Owner-based | `orders.customer_id = get_user_id()` | 最常見，每人只看自己的 |
| Role-based | `shop.is_staff()` | 根據 profile 的 is_staff 欄位 |
| JWT Claims | `shop.is_super_admin()` | 讀取 app_metadata |
| Time-Window | `shop.can_cancel_order(id)` | 限時操作 |
| Multi-Tenant | `crawler.has_project_access(pid)` | JWT 裡的 project_ids 陣列 |
| Column-Level | `rag.chunks_safe` VIEW | 隱藏 embedding 欄位 |
| Visibility | `products.status = 'publish'` | 公開 vs 草稿 |
| service_role | `USING (true)` | 後端服務完整存取 |

---

## 驗收清單

完成以下所有項目，本 Lab 就算通過：

- [ ] Seed data 執行成功，5 個使用者存在
- [ ] SET ROLE anon → `shop.orders` 回傳空（0 筆）
- [ ] SET ROLE authenticated + JWT → 只看到自己的訂單
- [ ] service_role → 看到所有資料（orders = 3, sources = 3, chunks = 7）
- [ ] `is_staff()` 對 staff 回傳 true、對 customer 回傳 false
- [ ] `EXPLAIN` 顯示 RLS policy filter 條件
- [ ] 找出所有沒有 RLS 的表（查詢結果應該為零）
- [ ] Time-window policy：24h 內可取消、超過不行

---

## 學到了什麼？

| Stage | 主題 | 關鍵技能 |
|-------|------|---------|
| 1 | 為什麼需要 Seed Data | 開發、測試、Demo 三大場景 |
| 2 | Seed Data 技巧 | trigger 管理、crypt、ON CONFLICT、MATVIEW 刷新 |
| 3 | SET ROLE 模擬 | anon / authenticated / service_role 角色切換 |
| 4 | Helper Function 驗證 | get_current_user_id、is_staff、has_project_access |
| 5 | RLS 偵錯 | pg_tables、pg_policies、EXPLAIN 三大工具 |
| 6 | 進階安全 | Time-Window、Column-Level、Cross-Schema |

---

*最後更新：2026-03*

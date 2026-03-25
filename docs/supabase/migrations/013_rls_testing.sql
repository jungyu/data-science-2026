-- ============================================================
-- 013: RLS Testing & Debugging — 驗證 Policy 是否正確生效
-- ============================================================
-- 這不是 migration，是教學用的 RLS 驗證腳本。
-- 在 SQL Editor 逐段執行，觀察不同角色看到的資料差異。
--
-- 教學重點：
--   1. SET ROLE 模擬不同角色
--   2. auth.uid() / auth.jwt() 模擬
--   3. 驗證 policy 拒絕/允許的效果
--   4. EXPLAIN 查看 policy 是否被加入查詢計畫
--   5. 常見 RLS 陷阱與除錯技巧
-- ============================================================


-- ============================================================
-- 1. 查看所有 RLS 狀態 + Policy 清單
-- ============================================================

-- 1a. 哪些表啟用了 RLS？
SELECT
  schemaname,
  tablename,
  rowsecurity AS rls_enabled,
  forcerowsecurity AS rls_forced
FROM pg_tables
WHERE schemaname IN ('shop', 'crawler', 'rag', 'analytics')
ORDER BY schemaname, tablename;

-- 1b. 所有 Policy 一覽表
SELECT
  schemaname,
  tablename,
  policyname,
  permissive,    -- 'PERMISSIVE' = OR 邏輯, 'RESTRICTIVE' = AND 邏輯
  roles,
  cmd,           -- SELECT, INSERT, UPDATE, DELETE, ALL
  qual AS using_expression,
  with_check AS with_check_expression
FROM pg_policies
WHERE schemaname IN ('shop', 'crawler', 'rag', 'analytics')
ORDER BY schemaname, tablename, policyname;

-- 1c. 統計：每張表有幾條 policy？
SELECT schemaname, tablename, count(*) AS policy_count
FROM pg_policies
WHERE schemaname IN ('shop', 'crawler', 'rag', 'analytics')
GROUP BY schemaname, tablename
ORDER BY policy_count DESC;


-- ============================================================
-- 2. 模擬角色切換（SET ROLE）
-- ============================================================
-- 教學重點：
--   - Supabase 有三個預設角色：anon, authenticated, service_role
--   - SET ROLE 讓你以該角色的身份執行 SQL
--   - RESET ROLE 恢復為 superuser
--
-- ⚠️ 注意：SET ROLE 只改權限，不設 auth.uid()
--    要完整模擬需搭配 Section 3 的 request.jwt.claims

-- 2a. 以 anon 身份查詢（未登入用戶）
SET ROLE anon;

-- 應該能看到 published 商品
SELECT count(*) AS visible_products
FROM shop.products;
-- 預期：只有 status='publish' 且 deleted_at IS NULL 的商品

-- 應該看不到訂單
SELECT count(*) AS visible_orders
FROM shop.orders;
-- 預期：0（anon 沒有 orders 的 SELECT policy）

-- 應該看不到 crawler（需要 authenticated + project_id）
SELECT count(*) AS visible_sources
FROM crawler.sources;
-- 預期：ERROR 或 0（取決於是否有 anon policy）

RESET ROLE;

-- 2b. 以 authenticated 身份查詢（已登入但沒設 JWT）
SET ROLE authenticated;

SELECT count(*) FROM shop.products;
-- 預期：可以看到更多（包含自己的 draft）

SELECT count(*) FROM shop.orders;
-- 預期：0（因為 auth.uid() 是 NULL，customer_id 匹配不到）

RESET ROLE;

-- 2c. 以 service_role 身份查詢（後端服務）
SET ROLE service_role;

SELECT count(*) FROM shop.orders;
-- 預期：所有訂單（service_role policy 是 USING (true)）

SELECT count(*) FROM crawler.sources;
-- 預期：所有 sources

RESET ROLE;


-- ============================================================
-- 3. 完整模擬：SET ROLE + JWT Claims
-- ============================================================
-- 教學重點：
--   - 要模擬特定用戶，必須同時設定：
--     1. SET ROLE authenticated（角色）
--     2. SET request.jwt.claims（JWT payload，包含 sub = user UUID）
--   - 這樣 auth.uid() 和 auth.jwt() 才會回傳正確的值

-- 3a. 模擬 Alice（一般顧客）
SET ROLE authenticated;
SET request.jwt.claims = '{
  "sub": "00000000-0000-0000-0000-000000000003",
  "role": "authenticated",
  "aud": "authenticated",
  "app_metadata": {}
}';

-- Alice 應該只看到自己的訂單
SELECT id, status, total FROM shop.orders;
-- 預期：SEED_ORD_001（Alice 的訂單）

-- Alice 應該看不到 Bob 的訂單
-- （不需要額外查詢，上面的結果就不會包含 Bob 的）

-- Alice 應該能看到自己的地址
SELECT id, label, city FROM shop.addresses;
-- 預期：SEED_ADR_001

-- Alice 應該看到自己的點數
SELECT * FROM shop.point_balances;
-- 預期：balance = 416

RESET ROLE;

-- 3b. 模擬 Staff（店員小明）
SET ROLE authenticated;
SET request.jwt.claims = '{
  "sub": "00000000-0000-0000-0000-000000000002",
  "role": "authenticated",
  "aud": "authenticated",
  "app_metadata": {}
}';

-- Staff 應該看到所有訂單
SELECT count(*) AS total_orders FROM shop.orders;
-- 預期：3（所有 seed 訂單）

-- Staff 應該能看到所有商品（包含 draft）
SELECT id, title, status FROM shop.products;

-- Staff 應該能看到公司資料
SELECT id, name FROM shop.companies;
-- 預期：SEED_CMP_001

RESET ROLE;

-- 3c. 模擬 Super Admin（JWT claims pattern）
SET ROLE authenticated;
SET request.jwt.claims = '{
  "sub": "00000000-0000-0000-0000-000000000001",
  "role": "authenticated",
  "aud": "authenticated",
  "app_metadata": {"role": "super_admin"}
}';

-- Super Admin 應該看到所有訂單（透過 is_super_admin()）
SELECT count(*) AS total_orders FROM shop.orders;
-- 預期：3

RESET ROLE;

-- 3d. 模擬 Crawler 用戶（Multi-tenant pattern）
SET ROLE authenticated;
SET request.jwt.claims = '{
  "sub": "00000000-0000-0000-0000-000000000001",
  "role": "authenticated",
  "aud": "authenticated",
  "app_metadata": {"project_ids": ["demo-project"]}
}';

-- 應該看到 demo-project 的 sources
SELECT id, code, name FROM crawler.sources;
-- 預期：3 個 seed sources（都是 demo-project）

-- 應該看到 demo-project 的 articles
SELECT count(*) FROM crawler.articles;
-- 預期：3

RESET ROLE;

-- 3e. 模擬「沒有 project 權限」的用戶
SET ROLE authenticated;
SET request.jwt.claims = '{
  "sub": "00000000-0000-0000-0000-000000000003",
  "role": "authenticated",
  "aud": "authenticated",
  "app_metadata": {"project_ids": ["other-project"]}
}';

-- 應該看不到 demo-project 的資料
SELECT count(*) FROM crawler.sources;
-- 預期：0

SELECT count(*) FROM crawler.articles;
-- 預期：0

RESET ROLE;


-- ============================================================
-- 4. Time-Window Policy 測試
-- ============================================================

SET ROLE authenticated;
SET request.jwt.claims = '{
  "sub": "00000000-0000-0000-0000-000000000004",
  "role": "authenticated",
  "aud": "authenticated",
  "app_metadata": {}
}';

-- Bob 有一筆 pending 訂單（SEED_ORD_002，1 小時前建立）
-- 應該能取消（在 24 小時內）
UPDATE shop.orders
SET status = 'cancelled'
WHERE id = 'SEED_ORD_002';
-- 預期：1 row updated

-- 驗證
SELECT id, status FROM shop.orders WHERE id = 'SEED_ORD_002';
-- 預期：status = 'cancelled'

-- 恢復（用 service_role）
RESET ROLE;
UPDATE shop.orders SET status = 'pending' WHERE id = 'SEED_ORD_002';

-- Alice 的訂單是 20 天前建立的（超過 24 小時）
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
-- 預期：0 rows updated（已超過取消期限 + 狀態已是 delivered）

RESET ROLE;


-- ============================================================
-- 5. Column-Level Security 測試（RAG embedding 遮蔽）
-- ============================================================

SET ROLE authenticated;

-- 直接查 chunks → 包含 embedding 欄位
SELECT id, left(content, 50), embedding IS NOT NULL AS has_embedding
FROM rag.chunks
LIMIT 3;
-- 預期：has_embedding = false（seed 沒有真正的 vector）

-- 查 chunks_safe VIEW → 沒有 embedding 欄位
SELECT * FROM rag.chunks_safe LIMIT 3;
-- 預期：欄位列表中沒有 embedding

-- 驗證：嘗試從 VIEW 取 embedding → 報錯
-- SELECT embedding FROM rag.chunks_safe LIMIT 1;
-- 預期：ERROR: column "embedding" does not exist

RESET ROLE;


-- ============================================================
-- 6. EXPLAIN 驗證 Policy 注入
-- ============================================================
-- 教學重點：
--   - EXPLAIN 可以看到 RLS policy 被加入查詢計畫的 Filter 條件
--   - 如果 Filter 太複雜，可能造成效能問題

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
-- → 可以看到 policy 被注入為 Filter 條件

EXPLAIN (COSTS OFF)
SELECT * FROM shop.products;
-- 預期：
--   Filter: ((status = 'publish' AND deleted_at IS NULL) OR ...)

RESET ROLE;


-- ============================================================
-- 7. 常見 RLS 陷阱與除錯技巧
-- ============================================================

-- 7a. 陷阱：忘記 ENABLE RLS
-- 查找「有表但沒開 RLS」的漏洞
SELECT schemaname, tablename
FROM pg_tables
WHERE schemaname IN ('shop', 'crawler', 'rag', 'analytics')
  AND rowsecurity = FALSE;
-- 預期：空（所有表都應該開了 RLS）

-- 7b. 陷阱：有 RLS 但沒有 Policy → 所有人都看不到資料
SELECT t.schemaname, t.tablename
FROM pg_tables t
LEFT JOIN pg_policies p ON t.schemaname = p.schemaname AND t.tablename = p.tablename
WHERE t.schemaname IN ('shop', 'crawler', 'rag', 'analytics')
  AND t.rowsecurity = TRUE
  AND p.policyname IS NULL;
-- 預期：空（所有開了 RLS 的表都應該有 policy）

-- 7c. 陷阱：service_role 沒有 bypass policy
-- 確認所有表都有 service_role policy
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
-- 預期：空（所有表都有 service_role policy）

-- 7d. 技巧：查看特定表的所有 policy 詳情
SELECT policyname, permissive, roles, cmd,
  qual AS using_expr,
  with_check AS check_expr
FROM pg_policies
WHERE schemaname = 'shop' AND tablename = 'orders'
ORDER BY policyname;

-- 7e. 技巧：測試 helper function 回傳值
SET ROLE authenticated;
SET request.jwt.claims = '{
  "sub": "00000000-0000-0000-0000-000000000003",
  "role": "authenticated",
  "aud": "authenticated",
  "app_metadata": {"project_ids": ["demo-project"]}
}';

SELECT shop.get_current_user_id() AS my_user_id;
SELECT shop.is_staff() AS am_i_staff;
SELECT shop.is_super_admin() AS am_i_super_admin;
SELECT crawler.get_my_project_ids() AS my_projects;
SELECT crawler.has_project_access('demo-project') AS can_access_demo;
SELECT crawler.has_project_access('other-project') AS can_access_other;

RESET ROLE;


-- ============================================================
-- 8. RLS Pattern 總覽（快速參考）
-- ============================================================
--
-- | Pattern              | 範例                                | 檔案  |
-- |----------------------|-------------------------------------|-------|
-- | Owner-based          | orders.customer_id = get_user_id()  | 002   |
-- | Role-based           | shop.is_staff()                     | 002   |
-- | JWT Claims           | shop.is_super_admin()               | 002   |
-- | Time-Window          | shop.can_cancel_order(id)           | 002   |
-- | Inherited (FK)       | shop.is_order_owner(order_id)       | 002   |
-- | Visibility Filter    | products.status = 'publish'         | 002   |
-- | Store-Level Staff    | shop.is_store_staff(store_id)       | 002   |
-- | Multi-Tenant (JWT)   | crawler.has_project_access(pid)     | 003   |
-- | Owner + Active       | rag.is_collection_active(cid)       | 004   |
-- | Column-Level (View)  | rag.chunks_safe                     | 004   |
-- | Cross-Schema Helper  | rag.can_read_collection(cid)        | 004   |
-- | Compound Condition   | coupons: active + date range        | 002   |
-- | Storage Bucket       | bucket_id + shop.is_staff()         | 008   |
-- | service_role Bypass  | USING (true) WITH CHECK (true)      | all   |

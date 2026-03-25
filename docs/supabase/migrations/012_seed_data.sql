-- ============================================================
-- 012: Seed Data — 教學用範例資料
-- ============================================================
-- 讓學生執行完 001-011 後，立刻有資料可以查詢和測試。
--
-- 注意：
--   - 這不是 migration，是 seed script（只在開發環境跑）
--   - 所有 ID 用固定 ULID 前綴，方便辨識是 seed data
--   - ON CONFLICT DO NOTHING 確保可重複執行
--   - 先 seed 獨立表，再 seed 有 FK 的表
-- ============================================================


-- ============================================================
-- 固定 ID 前綴說明：
--   SEED_USR_  = users
--   SEED_PRF_  = profiles
--   SEED_CMP_  = companies
--   SEED_STR_  = stores
--   SEED_PRD_  = products
--   SEED_IMG_  = product_images
--   SEED_ORD_  = orders
--   SEED_OIT_  = order_items
--   SEED_SRC_  = crawler sources
--   SEED_RUN_  = crawl_runs
--   SEED_ART_  = articles
--   SEED_COL_  = rag collections
--   SEED_DOC_  = rag documents
--   SEED_CHK_  = rag chunks
-- ============================================================


-- ============================================================
-- 1. SHOP — Users & Profiles
-- ============================================================
-- 先 INSERT auth.users（滿足 FK），再讓 trigger 自動建 shop.users + profiles。
-- 但 seed 需要固定 ID，所以：暫停 trigger → 手動 INSERT → 恢復 trigger。

-- Step 1: 暫停 auth trigger（避免 handle_new_user 自動建 shop.users）
ALTER TABLE auth.users DISABLE TRIGGER on_auth_user_created;

-- Step 2: 建立 auth.users seed（滿足 FK 約束）
INSERT INTO auth.users (id, email, encrypted_password, email_confirmed_at, created_at, updated_at, instance_id, aud, role)
VALUES
  ('00000000-0000-0000-0000-000000000001', 'admin@seed.local',  crypt('seed-password', gen_salt('bf')), NOW() - INTERVAL '90 days', NOW() - INTERVAL '90 days', NOW(), '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated'),
  ('00000000-0000-0000-0000-000000000002', 'staff@seed.local',  crypt('seed-password', gen_salt('bf')), NOW() - INTERVAL '60 days', NOW() - INTERVAL '60 days', NOW(), '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated'),
  ('00000000-0000-0000-0000-000000000003', 'alice@seed.local',  crypt('seed-password', gen_salt('bf')), NOW() - INTERVAL '45 days', NOW() - INTERVAL '45 days', NOW(), '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated'),
  ('00000000-0000-0000-0000-000000000004', 'bob@seed.local',    crypt('seed-password', gen_salt('bf')), NOW() - INTERVAL '30 days', NOW() - INTERVAL '30 days', NOW(), '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated'),
  ('00000000-0000-0000-0000-000000000005', 'carol@seed.local',  crypt('seed-password', gen_salt('bf')), NOW() - INTERVAL '15 days', NOW() - INTERVAL '15 days', NOW(), '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated')
ON CONFLICT (id) DO NOTHING;

-- Step 3: 手動建 shop.users（用固定 SEED ID）
INSERT INTO shop.users (id, auth_user_id, created_at) VALUES
  ('SEED_USR_ADMIN001', '00000000-0000-0000-0000-000000000001', NOW() - INTERVAL '90 days'),
  ('SEED_USR_STAFF001', '00000000-0000-0000-0000-000000000002', NOW() - INTERVAL '60 days'),
  ('SEED_USR_CUST0001', '00000000-0000-0000-0000-000000000003', NOW() - INTERVAL '45 days'),
  ('SEED_USR_CUST0002', '00000000-0000-0000-0000-000000000004', NOW() - INTERVAL '30 days'),
  ('SEED_USR_CUST0003', '00000000-0000-0000-0000-000000000005', NOW() - INTERVAL '15 days')
ON CONFLICT (id) DO NOTHING;

-- Step 4: 手動建 profiles
INSERT INTO shop.profiles (id, username, full_name, display_name, is_staff) VALUES
  ('SEED_USR_ADMIN001', 'admin',    '管理員',     'Admin',   TRUE),
  ('SEED_USR_STAFF001', 'staff01',  '店員小明',   '小明',    TRUE),
  ('SEED_USR_CUST0001', 'alice',    'Alice Wang', 'Alice',   FALSE),
  ('SEED_USR_CUST0002', 'bob',      'Bob Chen',   'Bob',     FALSE),
  ('SEED_USR_CUST0003', 'carol',    'Carol Liu',  'Carol',   FALSE)
ON CONFLICT (id) DO NOTHING;

-- Step 5: 恢復 trigger
ALTER TABLE auth.users ENABLE TRIGGER on_auth_user_created;


-- ============================================================
-- 2. SHOP — Company & Store
-- ============================================================

INSERT INTO shop.companies (id, name, type, supervisor_id, description) VALUES
  ('SEED_CMP_001', '範例科技有限公司', 'retailer', 'SEED_USR_ADMIN001', '教學用範例公司')
ON CONFLICT (id) DO NOTHING;

INSERT INTO shop.stores (id, company_id, name, supervisor_id, city, address, is_active) VALUES
  ('SEED_STR_001', 'SEED_CMP_001', '台北旗艦店', 'SEED_USR_STAFF001', '台北市', '信義區松仁路 100 號', TRUE),
  ('SEED_STR_002', 'SEED_CMP_001', '線上商店',   'SEED_USR_ADMIN001', '',       '',                    TRUE)
ON CONFLICT (id) DO NOTHING;

INSERT INTO shop.store_staff (id, store_id, staff_id, roles) VALUES
  ('SEED_STF_001', 'SEED_STR_001', 'SEED_USR_STAFF001', ARRAY['staff', 'cashier']),
  ('SEED_STF_002', 'SEED_STR_002', 'SEED_USR_ADMIN001', ARRAY['admin', 'staff'])
ON CONFLICT (id) DO NOTHING;


-- ============================================================
-- 3. SHOP — Products
-- ============================================================

INSERT INTO shop.products (id, author_id, title, slug, description, excerpt, status, type, sku, price, compare_at_price, currency) VALUES
  ('SEED_PRD_001', 'SEED_USR_STAFF001',
   'PostgreSQL 實戰手冊', 'postgresql-handbook',
   '從零開始學 PostgreSQL，涵蓋 Schema 設計、效能調校、RLS 安全機制。適合後端工程師與資料科學家。',
   '從零開始學 PostgreSQL', 'publish', 'digital',
   'BOOK-PG-001', 680.00, 880.00, 'TWD'),

  ('SEED_PRD_002', 'SEED_USR_STAFF001',
   'Supabase 開發者 T-Shirt', 'supabase-tshirt',
   '100% 純棉，印有 Supabase logo。尺寸：S/M/L/XL。',
   'Supabase 官方 T-Shirt', 'publish', 'physical',
   'MERCH-TS-001', 590.00, NULL, 'TWD'),

  ('SEED_PRD_003', 'SEED_USR_STAFF001',
   'AI 爬蟲工具包', 'ai-crawler-toolkit',
   '包含 Playwright 自動化腳本、反封鎖策略、資料清洗 pipeline。一次購買永久更新。',
   'Playwright + AI 爬蟲完整方案', 'publish', 'digital',
   'TOOL-CW-001', 1280.00, 1680.00, 'TWD'),

  ('SEED_PRD_004', 'SEED_USR_STAFF001',
   'RAG 實戰課程', 'rag-course',
   '從 chunking 策略到 hybrid search，完整的 RAG pipeline 建置教學。含 Supabase pgvector 實作。',
   'RAG Pipeline 完整教學', 'publish', 'digital',
   'COURSE-RAG-001', 2480.00, 3200.00, 'TWD'),

  ('SEED_PRD_005', 'SEED_USR_STAFF001',
   '機械鍵盤（開發者版）', 'dev-keyboard',
   'Cherry MX 茶軸，PBT 鍵帽，自定義 macro。為程式設計師打造。',
   '程式設計師專用鍵盤', 'publish', 'physical',
   'HW-KB-001', 3200.00, NULL, 'TWD')
ON CONFLICT (id) DO NOTHING;

-- Product images
INSERT INTO shop.product_images (id, product_id, storage_path, alt_text, sort_order, is_primary) VALUES
  ('SEED_IMG_001', 'SEED_PRD_001', 'SEED_PRD_001/cover.jpg',    'PostgreSQL 手冊封面', 0, TRUE),
  ('SEED_IMG_002', 'SEED_PRD_002', 'SEED_PRD_002/front.jpg',    'T-Shirt 正面',        0, TRUE),
  ('SEED_IMG_003', 'SEED_PRD_003', 'SEED_PRD_003/cover.jpg',    '爬蟲工具包封面',      0, TRUE),
  ('SEED_IMG_004', 'SEED_PRD_004', 'SEED_PRD_004/cover.jpg',    'RAG 課程封面',        0, TRUE),
  ('SEED_IMG_005', 'SEED_PRD_005', 'SEED_PRD_005/keyboard.jpg', '鍵盤產品照',          0, TRUE)
ON CONFLICT (id) DO NOTHING;


-- ============================================================
-- 4. SHOP — Stocks
-- ============================================================

INSERT INTO shop.stocks (id, store_id, product_id, quantity, low_stock_threshold) VALUES
  ('SEED_STK_001', 'SEED_STR_001', 'SEED_PRD_002', 50, 10),   -- T-Shirt 實體庫存
  ('SEED_STK_002', 'SEED_STR_001', 'SEED_PRD_005', 15, 5),    -- 鍵盤庫存
  ('SEED_STK_003', 'SEED_STR_002', 'SEED_PRD_001', 9999, NULL), -- 數位商品無限
  ('SEED_STK_004', 'SEED_STR_002', 'SEED_PRD_003', 9999, NULL),
  ('SEED_STK_005', 'SEED_STR_002', 'SEED_PRD_004', 9999, NULL)
ON CONFLICT (id) DO NOTHING;


-- ============================================================
-- 5. SHOP — Coupons
-- ============================================================

INSERT INTO shop.coupons (id, code, description, discount_type, discount_value, min_order_amount, starts_at, expires_at, is_active, created_by) VALUES
  ('SEED_CPN_001', 'WELCOME10',  '新會員 10% 折扣',     'percentage', 10.00,   0,       NOW() - INTERVAL '30 days', NOW() + INTERVAL '60 days', TRUE,  'SEED_USR_ADMIN001'),
  ('SEED_CPN_002', 'SAVE100',    '滿千折百',            'fixed',      100.00,  1000.00, NOW() - INTERVAL '7 days',  NOW() + INTERVAL '30 days', TRUE,  'SEED_USR_ADMIN001'),
  ('SEED_CPN_003', 'FREESHIP',   '免運費',              'free_shipping', 0,     500.00,  NOW(),                      NOW() + INTERVAL '14 days', TRUE,  'SEED_USR_ADMIN001'),
  ('SEED_CPN_004', 'EXPIRED99',  '已過期的優惠券',       'fixed',      99.00,   0,       NOW() - INTERVAL '60 days', NOW() - INTERVAL '1 day',   TRUE,  'SEED_USR_ADMIN001')
ON CONFLICT (id) DO NOTHING;


-- ============================================================
-- 6. SHOP — Orders & Payments
-- ============================================================

INSERT INTO shop.addresses (id, customer_id, label, recipient, phone, city, address_1, zip_code, is_default) VALUES
  ('SEED_ADR_001', 'SEED_USR_CUST0001', 'home',   'Alice Wang', '0912-345-678', '台北市', '大安區忠孝東路四段 100 號', '106', TRUE),
  ('SEED_ADR_002', 'SEED_USR_CUST0002', 'office', 'Bob Chen',   '0923-456-789', '新竹市', '東區光復路二段 200 號',     '300', TRUE)
ON CONFLICT (id) DO NOTHING;

-- Order 1: Alice 買了書 + 課程
INSERT INTO shop.orders (id, customer_id, status, num_items_sold, subtotal, total, currency, shipping_address_id, created_at, created_by) VALUES
  ('SEED_ORD_001', 'SEED_USR_CUST0001', 'delivered', 2, 3160.00, 3160.00, 'TWD', 'SEED_ADR_001', NOW() - INTERVAL '20 days', 'SEED_USR_CUST0001')
ON CONFLICT (id) DO NOTHING;

INSERT INTO shop.order_items (id, order_id, product_id, product_title, sku, quantity, unit_price, gross_revenue, net_revenue) VALUES
  ('SEED_OIT_001', 'SEED_ORD_001', 'SEED_PRD_001', 'PostgreSQL 實戰手冊', 'BOOK-PG-001', 1, 680.00,  680.00,  680.00),
  ('SEED_OIT_002', 'SEED_ORD_001', 'SEED_PRD_004', 'RAG 實戰課程',       'COURSE-RAG-001', 1, 2480.00, 2480.00, 2480.00)
ON CONFLICT (id) DO NOTHING;

INSERT INTO shop.payments (id, order_id, customer_id, amount, method, status, paid_at, created_by) VALUES
  ('SEED_PAY_001', 'SEED_ORD_001', 'SEED_USR_CUST0001', 3160.00, 'credit_card', 'paid', NOW() - INTERVAL '20 days', 'SEED_USR_CUST0001')
ON CONFLICT (id) DO NOTHING;

-- Order 2: Bob 買了 T-Shirt + 鍵盤（pending 狀態，用來測試 Realtime）
INSERT INTO shop.orders (id, customer_id, status, num_items_sold, subtotal, total, currency, shipping_address_id, created_at, created_by) VALUES
  ('SEED_ORD_002', 'SEED_USR_CUST0002', 'pending', 2, 3790.00, 3790.00, 'TWD', 'SEED_ADR_002', NOW() - INTERVAL '1 hour', 'SEED_USR_CUST0002')
ON CONFLICT (id) DO NOTHING;

INSERT INTO shop.order_items (id, order_id, product_id, product_title, sku, quantity, unit_price, gross_revenue, net_revenue) VALUES
  ('SEED_OIT_003', 'SEED_ORD_002', 'SEED_PRD_002', 'Supabase 開發者 T-Shirt', 'MERCH-TS-001', 1, 590.00,  590.00,  590.00),
  ('SEED_OIT_004', 'SEED_ORD_002', 'SEED_PRD_005', '機械鍵盤（開發者版）',     'HW-KB-001',   1, 3200.00, 3200.00, 3200.00)
ON CONFLICT (id) DO NOTHING;

-- Order 3: Carol 買了爬蟲工具包（cancelled，用來測試取消流程）
INSERT INTO shop.orders (id, customer_id, status, num_items_sold, subtotal, total, currency, created_at, created_by) VALUES
  ('SEED_ORD_003', 'SEED_USR_CUST0003', 'cancelled', 1, 1280.00, 1280.00, 'TWD', NOW() - INTERVAL '5 days', 'SEED_USR_CUST0003')
ON CONFLICT (id) DO NOTHING;

INSERT INTO shop.order_items (id, order_id, product_id, product_title, sku, quantity, unit_price, gross_revenue, net_revenue) VALUES
  ('SEED_OIT_005', 'SEED_ORD_003', 'SEED_PRD_003', 'AI 爬蟲工具包', 'TOOL-CW-001', 1, 1280.00, 1280.00, 0)
ON CONFLICT (id) DO NOTHING;


-- ============================================================
-- 7. SHOP — Reviews
-- ============================================================

INSERT INTO shop.reviews (id, product_id, customer_id, rating, title, body, is_verified, is_visible) VALUES
  ('SEED_REV_001', 'SEED_PRD_001', 'SEED_USR_CUST0001', 5, '很棒的 PostgreSQL 教材',
   '從 Schema 設計到 RLS 都講得很清楚，特別是 ULID 和 moddatetime 的部分。', TRUE, TRUE),
  ('SEED_REV_002', 'SEED_PRD_004', 'SEED_USR_CUST0001', 4, 'RAG 課程內容扎實',
   'hybrid search 的部分很實用，但希望能多一些 evaluation 的範例。', TRUE, TRUE),
  ('SEED_REV_003', 'SEED_PRD_002', 'SEED_USR_CUST0002', 5, '衣服質感很好',
   '純棉穿起來很舒服，Logo 印刷品質也很好。', TRUE, TRUE)
ON CONFLICT (id) DO NOTHING;


-- ============================================================
-- 8. SHOP — Points
-- ============================================================

INSERT INTO shop.point_rewards (id, customer_id, order_id, points, description) VALUES
  ('SEED_PTS_001', 'SEED_USR_CUST0001', 'SEED_ORD_001', 316, '訂單回饋 10%'),
  ('SEED_PTS_002', 'SEED_USR_CUST0001', NULL,            100, '新會員註冊禮')
ON CONFLICT (id) DO NOTHING;


-- ============================================================
-- 9. CRAWLER — Sources
-- ============================================================

INSERT INTO crawler.sources (id, project_id, code, name, description, base_url, domain, crawler_url, is_enabled) VALUES
  ('SEED_SRC_001', 'demo-project', 'hn-best',
   'Hacker News Best', 'Hacker News 精選文章',
   'https://news.ycombinator.com', 'news.ycombinator.com',
   'https://news.ycombinator.com/best', TRUE),

  ('SEED_SRC_002', 'demo-project', 'pg-blog',
   'PostgreSQL Blog', 'PostgreSQL 官方部落格',
   'https://www.postgresql.org', 'www.postgresql.org',
   'https://www.postgresql.org/about/news/', TRUE),

  ('SEED_SRC_003', 'demo-project', 'supabase-blog',
   'Supabase Blog', 'Supabase 官方部落格',
   'https://supabase.com', 'supabase.com',
   'https://supabase.com/blog', TRUE)
ON CONFLICT (id) DO NOTHING;


-- ============================================================
-- 10. CRAWLER — Crawl Runs & Articles
-- ============================================================

INSERT INTO crawler.crawl_runs (id, project_id, source_id, run_status, started_at, finished_at, pages_found, pages_fetched, articles_extracted, error_count) VALUES
  ('SEED_RUN_001', 'demo-project', 'SEED_SRC_001', 'success',
   NOW() - INTERVAL '2 hours', NOW() - INTERVAL '1 hour 50 minutes',
   30, 28, 25, 2),
  ('SEED_RUN_002', 'demo-project', 'SEED_SRC_002', 'success',
   NOW() - INTERVAL '3 hours', NOW() - INTERVAL '2 hours 45 minutes',
   15, 15, 12, 0),
  ('SEED_RUN_003', 'demo-project', 'SEED_SRC_003', 'failed',
   NOW() - INTERVAL '1 hour', NOW() - INTERVAL '55 minutes',
   10, 3, 0, 7)
ON CONFLICT (id) DO NOTHING;

INSERT INTO crawler.articles (id, project_id, source_id, title, source_url, author_name, published_at, abstract, content_text, is_published) VALUES
  ('SEED_ART_001', 'demo-project', 'SEED_SRC_001',
   'Show HN: Building a RAG pipeline with Supabase pgvector',
   'https://news.ycombinator.com/item?id=12345',
   'pg_hacker', NOW() - INTERVAL '2 days',
   'A practical guide to building RAG with Supabase...',
   'Full article content here about building RAG pipelines using Supabase pgvector and Edge Functions...',
   TRUE),

  ('SEED_ART_002', 'demo-project', 'SEED_SRC_002',
   'PostgreSQL 17 Released',
   'https://www.postgresql.org/about/news/postgresql-17-released/',
   'PostgreSQL Global Development Group', NOW() - INTERVAL '5 days',
   'The PostgreSQL Global Development Group announces PostgreSQL 17...',
   'PostgreSQL 17 brings significant performance improvements including incremental backup support...',
   TRUE),

  ('SEED_ART_003', 'demo-project', 'SEED_SRC_001',
   'Why I switched from Firebase to Supabase',
   'https://news.ycombinator.com/item?id=12346',
   'dev_nomad', NOW() - INTERVAL '3 days',
   'After 2 years on Firebase, here is why I made the switch...',
   'The main reasons were: 1) PostgreSQL instead of NoSQL, 2) Row Level Security, 3) Self-hosting option...',
   TRUE)
ON CONFLICT (id) DO NOTHING;


-- ============================================================
-- 11. CRAWLER — Tags
-- ============================================================

INSERT INTO crawler.tags (id, project_id, taxonomy, name, slug) VALUES
  ('SEED_TAG_001', 'demo-project', 'topic', 'PostgreSQL',  'postgresql'),
  ('SEED_TAG_002', 'demo-project', 'topic', 'Supabase',    'supabase'),
  ('SEED_TAG_003', 'demo-project', 'topic', 'RAG',         'rag'),
  ('SEED_TAG_004', 'demo-project', 'topic', 'AI',          'ai'),
  ('SEED_TAG_005', 'demo-project', 'topic', 'Web Scraping', 'web-scraping')
ON CONFLICT (id) DO NOTHING;

INSERT INTO crawler.article_tags (article_id, tag_id) VALUES
  ('SEED_ART_001', 'SEED_TAG_002'),  -- RAG article → Supabase
  ('SEED_ART_001', 'SEED_TAG_003'),  -- RAG article → RAG
  ('SEED_ART_002', 'SEED_TAG_001'),  -- PG 17 → PostgreSQL
  ('SEED_ART_003', 'SEED_TAG_002'),  -- Firebase vs Supabase → Supabase
  ('SEED_ART_003', 'SEED_TAG_001')   -- Firebase vs Supabase → PostgreSQL
ON CONFLICT DO NOTHING;


-- ============================================================
-- 12. RAG — Embedding Model & Collection
-- ============================================================
-- NOTE: embedding_models 已在 004_rag_schema.sql 的 INSERT 中建立

INSERT INTO rag.collections (id, name, code, description, embedding_model_id, owner_id, is_active) VALUES
  ('SEED_COL_001', '技術文章知識庫', 'tech-articles',
   '從 Hacker News 和技術部落格抓取的文章，用於 RAG 問答。',
   (SELECT id FROM rag.embedding_models WHERE name = 'text-embedding-3-small' LIMIT 1),
   NULL, TRUE),

  ('SEED_COL_002', 'PostgreSQL 文件', 'pg-docs',
   'PostgreSQL 官方文件的 RAG 索引。',
   (SELECT id FROM rag.embedding_models WHERE name = 'text-embedding-3-small' LIMIT 1),
   NULL, TRUE)
ON CONFLICT (id) DO NOTHING;


-- ============================================================
-- 13. RAG — Documents & Chunks
-- ============================================================

INSERT INTO rag.documents (id, collection_id, title, source_type, source_url, source_ref_type, source_ref_id, content_text, process_status, chunk_count) VALUES
  ('SEED_DOC_001', 'SEED_COL_001',
   'Show HN: Building a RAG pipeline with Supabase pgvector',
   'crawler', 'https://news.ycombinator.com/item?id=12345',
   'crawler.articles', 'SEED_ART_001',
   'Full article content here about building RAG pipelines using Supabase pgvector and Edge Functions...',
   'ready', 3),

  ('SEED_DOC_002', 'SEED_COL_001',
   'PostgreSQL 17 Released',
   'crawler', 'https://www.postgresql.org/about/news/postgresql-17-released/',
   'crawler.articles', 'SEED_ART_002',
   'PostgreSQL 17 brings significant performance improvements including incremental backup support...',
   'ready', 2),

  ('SEED_DOC_003', 'SEED_COL_002',
   'PostgreSQL RLS 完全指南',
   'text', NULL, NULL, NULL,
   'Row Level Security (RLS) 是 PostgreSQL 的行級安全機制。啟用 RLS 後，每個 SELECT/INSERT/UPDATE/DELETE 都會經過 policy 檢查。這讓你可以在資料庫層面實現存取控制，不依賴應用層邏輯。',
   'ready', 2)
ON CONFLICT (id) DO NOTHING;

-- Chunks（沒有真正的 embedding vector，用 NULL）
-- 學生需要自己跑 embedding pipeline 才會有向量
INSERT INTO rag.chunks (id, document_id, collection_id, content, chunk_index, token_count, embedding) VALUES
  ('SEED_CHK_001', 'SEED_DOC_001', 'SEED_COL_001',
   'Building a RAG pipeline with Supabase pgvector requires three components: document ingestion, chunk embedding, and similarity search.',
   0, 22, NULL),
  ('SEED_CHK_002', 'SEED_DOC_001', 'SEED_COL_001',
   'For embedding generation, use OpenAI text-embedding-3-small model. It produces 1536-dimensional vectors that work well with pgvector cosine similarity.',
   1, 25, NULL),
  ('SEED_CHK_003', 'SEED_DOC_001', 'SEED_COL_001',
   'The hybrid search approach combines semantic similarity (pgvector) with full-text search (tsvector) for better retrieval accuracy.',
   2, 20, NULL),
  ('SEED_CHK_004', 'SEED_DOC_002', 'SEED_COL_001',
   'PostgreSQL 17 introduces incremental backup support, allowing faster backup and restore operations for large databases.',
   0, 18, NULL),
  ('SEED_CHK_005', 'SEED_DOC_002', 'SEED_COL_001',
   'Performance improvements in PostgreSQL 17 include better query planning for partitioned tables and improved parallel query execution.',
   1, 17, NULL),
  ('SEED_CHK_006', 'SEED_DOC_003', 'SEED_COL_002',
   'Row Level Security (RLS) 是 PostgreSQL 的行級安全機制。啟用 RLS 後，每個 SELECT/INSERT/UPDATE/DELETE 都會經過 policy 檢查。',
   0, 35, NULL),
  ('SEED_CHK_007', 'SEED_DOC_003', 'SEED_COL_002',
   '這讓你可以在資料庫層面實現存取控制，不依賴應用層邏輯。Supabase 的每張表都建議啟用 RLS。',
   1, 30, NULL)
ON CONFLICT (id) DO NOTHING;


-- ============================================================
-- 14. ANALYTICS — Funnel Events（模擬購物漏斗）
-- ============================================================

INSERT INTO analytics.funnel_events (id, session_id, customer_id, step, step_order, product_id, order_id) VALUES
  -- Session A: 完整漏斗（view → cart → checkout → payment → completed）
  ('SEED_FNL_001', 'session-aaa', 'SEED_USR_CUST0001', 'view',         1, 'SEED_PRD_001', NULL),
  ('SEED_FNL_002', 'session-aaa', 'SEED_USR_CUST0001', 'add_to_cart',  2, 'SEED_PRD_001', NULL),
  ('SEED_FNL_003', 'session-aaa', 'SEED_USR_CUST0001', 'checkout',     3, NULL,           'SEED_ORD_001'),
  ('SEED_FNL_004', 'session-aaa', 'SEED_USR_CUST0001', 'payment',      4, NULL,           'SEED_ORD_001'),
  ('SEED_FNL_005', 'session-aaa', 'SEED_USR_CUST0001', 'completed',    5, NULL,           'SEED_ORD_001'),
  -- Session B: 中斷在 checkout（Bob 還沒付款）
  ('SEED_FNL_006', 'session-bbb', 'SEED_USR_CUST0002', 'view',         1, 'SEED_PRD_005', NULL),
  ('SEED_FNL_007', 'session-bbb', 'SEED_USR_CUST0002', 'add_to_cart',  2, 'SEED_PRD_005', NULL),
  ('SEED_FNL_008', 'session-bbb', 'SEED_USR_CUST0002', 'checkout',     3, NULL,           'SEED_ORD_002'),
  -- Session C: 只瀏覽（Carol 看了就走）
  ('SEED_FNL_009', 'session-ccc', 'SEED_USR_CUST0003', 'view',         1, 'SEED_PRD_003', NULL),
  -- Session D: 匿名瀏覽
  ('SEED_FNL_010', 'session-ddd', NULL,                 'view',         1, 'SEED_PRD_002', NULL),
  ('SEED_FNL_011', 'session-ddd', NULL,                 'view',         1, 'SEED_PRD_004', NULL)
ON CONFLICT (id) DO NOTHING;


-- ============================================================
-- 15. ANALYTICS — 手動觸發快照（讓學生有 analytics 資料可查）
-- ============================================================
-- 刷新 MATVIEW（需要先有資料才能刷新）
REFRESH MATERIALIZED VIEW analytics.mv_system_health;
REFRESH MATERIALIZED VIEW analytics.mv_product_ranking;
REFRESH MATERIALIZED VIEW analytics.mv_source_health;


-- ============================================================
-- 16. 驗證 Seed Data
-- ============================================================
-- 執行以下查詢確認 seed 成功：
--
-- -- Shop
-- SELECT count(*) AS users FROM shop.users;           -- 5
-- SELECT count(*) AS products FROM shop.products;     -- 5
-- SELECT count(*) AS orders FROM shop.orders;         -- 3
-- SELECT count(*) AS reviews FROM shop.reviews;       -- 3
-- SELECT * FROM shop.point_balances;                  -- Alice: 416 points
--
-- -- Crawler
-- SELECT count(*) AS sources FROM crawler.sources;    -- 3
-- SELECT count(*) AS runs FROM crawler.crawl_runs;    -- 3
-- SELECT count(*) AS articles FROM crawler.articles;  -- 3
--
-- -- RAG
-- SELECT count(*) AS collections FROM rag.collections; -- 2
-- SELECT count(*) AS documents FROM rag.documents;     -- 3
-- SELECT count(*) AS chunks FROM rag.chunks;           -- 7
--
-- -- Analytics
-- SELECT count(*) FROM analytics.funnel_events;        -- 11
-- SELECT * FROM analytics.mv_system_health;            -- 1 row
-- SELECT * FROM analytics.mv_product_ranking;          -- 5 products
--
-- -- 測試 Public API
-- SELECT * FROM public.api_shop_list_products(p_limit := 3);
-- SELECT * FROM public.api_crawler_stats();
-- SELECT * FROM public.api_rag_list_collections();
-- SELECT * FROM public.api_analytics_funnel();

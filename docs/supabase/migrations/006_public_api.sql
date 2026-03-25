-- ============================================================
-- Public API Functions — PostgREST Gateway Layer
-- ============================================================
--
-- 設計原則：
--   - PostgREST 只暴露 public schema
--   - 業務邏輯在各自 schema（shop/crawler/rag/analytics）
--   - public function = API endpoint，薄包裝 + 存取控制
--   - 前端統一用 supabase.rpc('function_name', params) 呼叫
--   - SECURITY DEFINER：用 function owner 權限執行（繞過 RLS）
--   - SET search_path：防止 search_path injection
--
-- 命名慣例：
--   api_{domain}_{action}  例如 api_shop_list_products
--   這樣在 API Docs 裡會按 domain 自然分組
--
-- 前端呼叫方式：
--   const { data } = await supabase.rpc('api_shop_list_products', {
--     p_limit: 20, p_offset: 0
--   })
--
-- Prerequisites:
--   - shop, crawler, rag, analytics schema 已建立
-- ============================================================


-- ============================================================
-- SHOP — 商品（Public / Anonymous 可讀）
-- ============================================================

-- 商品列表（分頁 + 排序）
CREATE OR REPLACE FUNCTION public.api_shop_list_products(
  p_limit    INTEGER DEFAULT 20,
  p_offset   INTEGER DEFAULT 0,
  p_sort_by  TEXT DEFAULT 'created_at',  -- 'created_at', 'price', 'title'
  p_sort_dir TEXT DEFAULT 'desc'         -- 'asc', 'desc'
)
RETURNS TABLE (
  id          TEXT,
  title       TEXT,
  slug        TEXT,
  excerpt     TEXT,
  price       NUMERIC,
  compare_at_price NUMERIC,
  currency    TEXT,
  status      TEXT,
  type        TEXT,
  image_url   TEXT,
  avg_rating  NUMERIC,
  review_count BIGINT,
  created_at  TIMESTAMPTZ
)
LANGUAGE SQL
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT
    p.id, p.title, p.slug, p.excerpt,
    p.price, p.compare_at_price, p.currency,
    p.status::TEXT, p.type::TEXT,
    pi.storage_path AS image_url,
    round(avg(r.rating)::NUMERIC, 1) AS avg_rating,
    count(DISTINCT r.id) AS review_count,
    p.created_at
  FROM shop.products p
  LEFT JOIN shop.product_images pi ON pi.product_id = p.id AND pi.is_primary = TRUE
  LEFT JOIN shop.reviews r ON r.product_id = p.id AND r.is_visible = TRUE
  WHERE p.status = 'publish' AND p.deleted_at IS NULL AND p.parent_id IS NULL
  GROUP BY p.id, p.title, p.slug, p.excerpt, p.price, p.compare_at_price,
           p.currency, p.status, p.type, pi.storage_path, p.created_at
  ORDER BY
    CASE WHEN p_sort_by = 'price'      AND p_sort_dir = 'asc'  THEN p.price END ASC,
    CASE WHEN p_sort_by = 'price'      AND p_sort_dir = 'desc' THEN p.price END DESC,
    CASE WHEN p_sort_by = 'title'      AND p_sort_dir = 'asc'  THEN p.title END ASC,
    CASE WHEN p_sort_by = 'title'      AND p_sort_dir = 'desc' THEN p.title END DESC,
    CASE WHEN p_sort_by = 'created_at' AND p_sort_dir = 'asc'  THEN p.created_at END ASC,
    CASE WHEN p_sort_by = 'created_at' AND p_sort_dir = 'desc' THEN p.created_at END DESC
  LIMIT p_limit OFFSET p_offset;
$$;

-- 商品詳情（含變體 + 圖片 + 評價統計）
CREATE OR REPLACE FUNCTION public.api_shop_get_product(p_slug TEXT)
RETURNS TABLE (
  id               TEXT,
  title            TEXT,
  slug             TEXT,
  description      TEXT,
  excerpt          TEXT,
  price            NUMERIC,
  compare_at_price NUMERIC,
  currency         TEXT,
  sku              TEXT,
  type             TEXT,
  is_taxable       BOOLEAN,
  metadata         JSONB,
  images           JSONB,
  variants         JSONB,
  avg_rating       NUMERIC,
  review_count     BIGINT,
  created_at       TIMESTAMPTZ
)
LANGUAGE SQL
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT
    p.id, p.title, p.slug, p.description, p.excerpt,
    p.price, p.compare_at_price, p.currency, p.sku,
    p.type::TEXT, p.is_taxable, p.metadata,
    -- 圖片 JSON array
    coalesce((
      SELECT jsonb_agg(jsonb_build_object(
        'id', pi.id,
        'url', pi.storage_path,
        'alt', pi.alt_text,
        'is_primary', pi.is_primary
      ) ORDER BY pi.sort_order)
      FROM shop.product_images pi WHERE pi.product_id = p.id
    ), '[]'::JSONB) AS images,
    -- 變體 JSON array
    coalesce((
      SELECT jsonb_agg(jsonb_build_object(
        'id', v.id,
        'title', v.title,
        'sku', v.sku,
        'price', v.price,
        'metadata', v.metadata
      ))
      FROM shop.products v
      WHERE v.parent_id = p.id AND v.deleted_at IS NULL
    ), '[]'::JSONB) AS variants,
    round(avg(r.rating)::NUMERIC, 1) AS avg_rating,
    count(DISTINCT r.id) AS review_count,
    p.created_at
  FROM shop.products p
  LEFT JOIN shop.reviews r ON r.product_id = p.id AND r.is_visible = TRUE
  WHERE p.slug = p_slug AND p.status = 'publish' AND p.deleted_at IS NULL
  GROUP BY p.id;
$$;

-- 商品搜尋（trigram + full-text）
CREATE OR REPLACE FUNCTION public.api_shop_search_products(
  p_query  TEXT,
  p_limit  INTEGER DEFAULT 20
)
RETURNS TABLE (
  id         TEXT,
  title      TEXT,
  slug       TEXT,
  excerpt    TEXT,
  price      NUMERIC,
  currency   TEXT,
  image_url  TEXT,
  relevance  REAL
)
LANGUAGE SQL
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT
    p.id, p.title, p.slug, p.excerpt, p.price, p.currency,
    pi.storage_path AS image_url,
    ts_rank(
      to_tsvector('simple', coalesce(p.title, '') || ' ' || coalesce(p.description, '')),
      plainto_tsquery('simple', p_query)
    ) AS relevance
  FROM shop.products p
  LEFT JOIN shop.product_images pi ON pi.product_id = p.id AND pi.is_primary = TRUE
  WHERE p.status = 'publish' AND p.deleted_at IS NULL
    AND (
      p.title % p_query                   -- trigram similarity
      OR to_tsvector('simple', coalesce(p.title, '') || ' ' || coalesce(p.description, ''))
         @@ plainto_tsquery('simple', p_query)
    )
  ORDER BY relevance DESC, p.title % p_query DESC
  LIMIT p_limit;
$$;

-- 商品評論列表
CREATE OR REPLACE FUNCTION public.api_shop_list_reviews(
  p_product_id TEXT,
  p_limit      INTEGER DEFAULT 20,
  p_offset     INTEGER DEFAULT 0
)
RETURNS TABLE (
  id           TEXT,
  rating       SMALLINT,
  title        TEXT,
  body         TEXT,
  is_verified  BOOLEAN,
  customer_name TEXT,
  created_at   TIMESTAMPTZ
)
LANGUAGE SQL
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT
    r.id, r.rating, r.title, r.body, r.is_verified,
    coalesce(nullif(pr.display_name, ''), pr.username) AS customer_name,
    r.created_at
  FROM shop.reviews r
  JOIN shop.profiles pr ON pr.id = r.customer_id
  WHERE r.product_id = p_product_id AND r.is_visible = TRUE
  ORDER BY r.created_at DESC
  LIMIT p_limit OFFSET p_offset;
$$;

-- 門市列表
CREATE OR REPLACE FUNCTION public.api_shop_list_stores()
RETURNS TABLE (
  id      TEXT,
  name    TEXT,
  phone   TEXT,
  city    TEXT,
  address TEXT,
  is_active BOOLEAN
)
LANGUAGE SQL
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT id, name, phone, city, address, is_active
  FROM shop.stores
  WHERE deleted_at IS NULL AND is_active = TRUE
  ORDER BY name;
$$;


-- ============================================================
-- SHOP — 顧客（Authenticated 限定）
-- ============================================================

-- 我的訂單
CREATE OR REPLACE FUNCTION public.api_shop_my_orders(
  p_limit  INTEGER DEFAULT 20,
  p_offset INTEGER DEFAULT 0
)
RETURNS TABLE (
  id          TEXT,
  status      TEXT,
  total       NUMERIC,
  currency    TEXT,
  num_items   INTEGER,
  items       JSONB,
  created_at  TIMESTAMPTZ
)
LANGUAGE SQL
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT
    o.id, o.status::TEXT, o.total, o.currency, o.num_items_sold,
    coalesce((
      SELECT jsonb_agg(jsonb_build_object(
        'product_title', oi.product_title,
        'sku', oi.sku,
        'quantity', oi.quantity,
        'unit_price', oi.unit_price,
        'net_revenue', oi.net_revenue
      ))
      FROM shop.order_items oi WHERE oi.order_id = o.id
    ), '[]'::JSONB) AS items,
    o.created_at
  FROM shop.orders o
  JOIN shop.users u ON u.id = o.customer_id
  WHERE u.auth_user_id = (SELECT auth.uid())
    AND o.deleted_at IS NULL
  ORDER BY o.created_at DESC
  LIMIT p_limit OFFSET p_offset;
$$;

-- 我的地址簿
CREATE OR REPLACE FUNCTION public.api_shop_my_addresses()
RETURNS TABLE (
  id         TEXT,
  label      TEXT,
  recipient  TEXT,
  phone      TEXT,
  city       TEXT,
  address_1  TEXT,
  address_2  TEXT,
  zip_code   TEXT,
  is_default BOOLEAN
)
LANGUAGE SQL
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT
    a.id, a.label::TEXT, a.recipient, a.phone,
    a.city, a.address_1, a.address_2, a.zip_code, a.is_default
  FROM shop.addresses a
  JOIN shop.users u ON u.id = a.customer_id
  WHERE u.auth_user_id = (SELECT auth.uid())
  ORDER BY a.is_default DESC, a.created_at DESC;
$$;

-- 我的點數餘額
CREATE OR REPLACE FUNCTION public.api_shop_my_points()
RETURNS TABLE (balance BIGINT)
LANGUAGE SQL
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT coalesce(sum(pr.points), 0) AS balance
  FROM shop.point_rewards pr
  JOIN shop.users u ON u.id = pr.customer_id
  WHERE u.auth_user_id = (SELECT auth.uid());
$$;

-- 有效優惠券列表
CREATE OR REPLACE FUNCTION public.api_shop_active_coupons()
RETURNS TABLE (
  id             TEXT,
  code           TEXT,
  description    TEXT,
  discount_type  TEXT,
  discount_value NUMERIC,
  min_order_amount NUMERIC,
  expires_at     TIMESTAMPTZ
)
LANGUAGE SQL
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT
    c.id, c.code, c.description, c.discount_type::TEXT,
    c.discount_value, c.min_order_amount, c.expires_at
  FROM shop.coupons c
  WHERE c.is_active = TRUE AND c.deleted_at IS NULL
    AND (c.starts_at IS NULL OR c.starts_at <= NOW())
    AND (c.expires_at IS NULL OR c.expires_at > NOW())
    AND (c.max_uses IS NULL OR c.used_count < c.max_uses)
  ORDER BY c.expires_at ASC NULLS LAST;
$$;


-- ============================================================
-- CRAWLER — 爬蟲狀態（Authenticated 限定）
-- ============================================================

-- 爬蟲統計總覽
CREATE OR REPLACE FUNCTION public.api_crawler_stats()
RETURNS TABLE (
  total_sources    BIGINT,
  active_sources   BIGINT,
  total_articles   BIGINT,
  runs_today       BIGINT,
  failed_today     BIGINT,
  queue_pending    BIGINT
)
LANGUAGE SQL
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT
    (SELECT count(*) FROM crawler.sources),
    (SELECT count(*) FROM crawler.sources WHERE is_enabled = TRUE),
    (SELECT count(*) FROM crawler.articles),
    (SELECT count(*) FROM crawler.crawl_runs WHERE created_at >= CURRENT_DATE),
    (SELECT count(*) FROM crawler.crawl_runs
     WHERE created_at >= CURRENT_DATE AND run_status = 'failed'),
    (SELECT count(*) FROM crawler.crawl_queue WHERE status = 'pending');
$$;

-- 最新文章列表
CREATE OR REPLACE FUNCTION public.api_crawler_latest_articles(
  p_source_code TEXT DEFAULT NULL,
  p_limit       INTEGER DEFAULT 20,
  p_offset      INTEGER DEFAULT 0
)
RETURNS TABLE (
  id           TEXT,
  title        TEXT,
  source_name  TEXT,
  source_url   TEXT,
  author_name  TEXT,
  published_at TIMESTAMPTZ,
  abstract     TEXT,
  tags         JSONB
)
LANGUAGE SQL
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT
    a.id, a.title, s.name AS source_name,
    a.source_url, a.author_name, a.published_at,
    left(a.abstract, 300) AS abstract,
    coalesce((
      SELECT jsonb_agg(t.name)
      FROM crawler.article_tags at
      JOIN crawler.tags t ON t.id = at.tag_id
      WHERE at.article_id = a.id
    ), '[]'::JSONB) AS tags
  FROM crawler.articles a
  JOIN crawler.sources s ON s.id = a.source_id
  WHERE a.is_published = TRUE AND a.is_available = TRUE
    AND (p_source_code IS NULL OR s.code = p_source_code)
  ORDER BY a.published_at DESC NULLS LAST
  LIMIT p_limit OFFSET p_offset;
$$;

-- 各來源健康度
CREATE OR REPLACE FUNCTION public.api_crawler_source_health()
RETURNS TABLE (
  source_code      TEXT,
  source_name      TEXT,
  is_enabled       BOOLEAN,
  total_runs_7d    BIGINT,
  success_rate_pct NUMERIC,
  articles_7d      BIGINT,
  last_run_at      TIMESTAMPTZ
)
LANGUAGE SQL
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT
    s.code, s.name, s.is_enabled,
    count(cr.id) AS total_runs_7d,
    CASE WHEN count(cr.id) = 0 THEN 0
         ELSE round(
           count(cr.id) FILTER (WHERE cr.run_status = 'success')::NUMERIC
           / count(cr.id) * 100, 1)
    END AS success_rate_pct,
    coalesce(sum(cr.articles_extracted), 0) AS articles_7d,
    max(cr.finished_at) AS last_run_at
  FROM crawler.sources s
  LEFT JOIN crawler.crawl_runs cr ON cr.source_id = s.id
    AND cr.created_at >= NOW() - INTERVAL '7 days'
  GROUP BY s.id, s.code, s.name, s.is_enabled
  ORDER BY s.name;
$$;


-- ============================================================
-- RAG — 語意搜尋（Public / Anonymous 可用）
-- ============================================================

-- 語意搜尋（bridge to rag.match_chunks_with_document）
CREATE OR REPLACE FUNCTION public.api_rag_search(
  query_embedding  vector(1536),
  p_collection_code TEXT,
  p_top_k          INTEGER DEFAULT 5,
  p_threshold      FLOAT8 DEFAULT 0.7
)
RETURNS TABLE (
  chunk_id        TEXT,
  document_title  TEXT,
  source_url      TEXT,
  content         TEXT,
  chunk_index     INTEGER,
  page_number     INTEGER,
  similarity      FLOAT8
)
LANGUAGE SQL
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT
    m.chunk_id, m.document_title, m.source_url,
    m.content, m.chunk_index, m.page_number, m.similarity
  FROM rag.match_chunks_with_document(
    query_embedding,
    (SELECT id FROM rag.collections WHERE code = p_collection_code AND is_active = TRUE),
    p_top_k,
    p_threshold
  ) m;
$$;

-- Hybrid 搜尋
CREATE OR REPLACE FUNCTION public.api_rag_hybrid_search(
  query_text       TEXT,
  query_embedding  vector(1536),
  p_collection_code TEXT,
  p_top_k          INTEGER DEFAULT 5,
  p_semantic_weight FLOAT8 DEFAULT 0.7
)
RETURNS TABLE (
  chunk_id        TEXT,
  document_id     TEXT,
  content         TEXT,
  semantic_score  FLOAT8,
  fulltext_score  FLOAT8,
  combined_score  FLOAT8
)
LANGUAGE SQL
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT h.chunk_id, h.document_id, h.content,
         h.semantic_score, h.fulltext_score, h.combined_score
  FROM rag.hybrid_search(
    query_text,
    query_embedding,
    (SELECT id FROM rag.collections WHERE code = p_collection_code AND is_active = TRUE),
    p_top_k,
    p_semantic_weight,
    0.5  -- default similarity threshold
  ) h;
$$;

-- 知識庫列表
CREATE OR REPLACE FUNCTION public.api_rag_list_collections()
RETURNS TABLE (
  code          TEXT,
  name          TEXT,
  description   TEXT,
  document_count BIGINT,
  chunk_count   BIGINT,
  is_active     BOOLEAN
)
LANGUAGE SQL
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT
    c.code, c.name, c.description,
    (SELECT count(*) FROM rag.documents d
     WHERE d.collection_id = c.id AND d.process_status = 'ready') AS document_count,
    (SELECT count(*) FROM rag.chunks ch
     WHERE ch.collection_id = c.id AND ch.embedding IS NOT NULL) AS chunk_count,
    c.is_active
  FROM rag.collections c
  WHERE c.is_active = TRUE
  ORDER BY c.name;
$$;


-- ============================================================
-- ANALYTICS — 儀表板（Authenticated 限定）
-- ============================================================

-- 全域儀表板（bridge to analytics.system_dashboard）
CREATE OR REPLACE FUNCTION public.api_analytics_dashboard(
  p_days_back INTEGER DEFAULT 1
)
RETURNS TABLE (
  domain        TEXT,
  metric        TEXT,
  value         NUMERIC,
  trend_vs_prev NUMERIC
)
LANGUAGE SQL
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT * FROM analytics.system_dashboard(p_days_back);
$$;

-- 營收趨勢
CREATE OR REPLACE FUNCTION public.api_analytics_revenue(
  p_granularity TEXT DEFAULT 'day',
  p_days_back   INTEGER DEFAULT 30
)
RETURNS TABLE (
  bucket          TIMESTAMPTZ,
  order_count     BIGINT,
  total_revenue   NUMERIC,
  avg_order_value NUMERIC
)
LANGUAGE SQL
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT * FROM analytics.revenue_time_series(p_granularity, p_days_back);
$$;

-- 漏斗轉換率
CREATE OR REPLACE FUNCTION public.api_analytics_funnel(
  p_days_back INTEGER DEFAULT 7
)
RETURNS TABLE (
  step           TEXT,
  step_order     SMALLINT,
  sessions       BIGINT,
  conversion_pct NUMERIC
)
LANGUAGE SQL
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT * FROM analytics.funnel_conversion(p_days_back);
$$;

-- RAG 品質趨勢
CREATE OR REPLACE FUNCTION public.api_analytics_rag_quality(
  p_collection_code TEXT DEFAULT NULL,
  p_weeks_back      INTEGER DEFAULT 12
)
RETURNS TABLE (
  week_start          DATE,
  query_count         BIGINT,
  avg_faithfulness    FLOAT8,
  avg_relevance       FLOAT8,
  avg_context_recall  FLOAT8,
  avg_context_precision FLOAT8,
  rated_count         BIGINT,
  avg_user_rating     FLOAT8
)
LANGUAGE SQL
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT * FROM analytics.rag_quality_trend(
    (SELECT id FROM rag.collections WHERE code = p_collection_code),
    p_weeks_back
  );
$$;

-- 資料新鮮度
CREATE OR REPLACE FUNCTION public.api_analytics_freshness()
RETURNS TABLE (
  schema_name      TEXT,
  entity           TEXT,
  latest_record_at TIMESTAMPTZ,
  minutes_ago      NUMERIC,
  is_stale         BOOLEAN
)
LANGUAGE SQL
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  SELECT * FROM analytics.data_freshness();
$$;


-- ============================================================
-- GRANTS
-- ============================================================

-- Shop: public APIs (anon + authenticated)
GRANT EXECUTE ON FUNCTION public.api_shop_list_products(INTEGER, INTEGER, TEXT, TEXT) TO anon, authenticated;
GRANT EXECUTE ON FUNCTION public.api_shop_get_product(TEXT) TO anon, authenticated;
GRANT EXECUTE ON FUNCTION public.api_shop_search_products(TEXT, INTEGER) TO anon, authenticated;
GRANT EXECUTE ON FUNCTION public.api_shop_list_reviews(TEXT, INTEGER, INTEGER) TO anon, authenticated;
GRANT EXECUTE ON FUNCTION public.api_shop_list_stores() TO anon, authenticated;
GRANT EXECUTE ON FUNCTION public.api_shop_active_coupons() TO anon, authenticated;

-- Shop: authenticated-only APIs
GRANT EXECUTE ON FUNCTION public.api_shop_my_orders(INTEGER, INTEGER) TO authenticated;
GRANT EXECUTE ON FUNCTION public.api_shop_my_addresses() TO authenticated;
GRANT EXECUTE ON FUNCTION public.api_shop_my_points() TO authenticated;

-- Crawler: authenticated-only APIs
GRANT EXECUTE ON FUNCTION public.api_crawler_stats() TO authenticated;
GRANT EXECUTE ON FUNCTION public.api_crawler_latest_articles(TEXT, INTEGER, INTEGER) TO authenticated;
GRANT EXECUTE ON FUNCTION public.api_crawler_source_health() TO authenticated;

-- RAG: public APIs (anon + authenticated)
GRANT EXECUTE ON FUNCTION public.api_rag_search(vector, TEXT, INTEGER, FLOAT8) TO anon, authenticated;
GRANT EXECUTE ON FUNCTION public.api_rag_hybrid_search(TEXT, vector, TEXT, INTEGER, FLOAT8) TO anon, authenticated;
GRANT EXECUTE ON FUNCTION public.api_rag_list_collections() TO anon, authenticated;

-- Analytics: authenticated-only APIs
GRANT EXECUTE ON FUNCTION public.api_analytics_dashboard(INTEGER) TO authenticated;
GRANT EXECUTE ON FUNCTION public.api_analytics_revenue(TEXT, INTEGER) TO authenticated;
GRANT EXECUTE ON FUNCTION public.api_analytics_funnel(INTEGER) TO authenticated;
GRANT EXECUTE ON FUNCTION public.api_analytics_rag_quality(TEXT, INTEGER) TO authenticated;
GRANT EXECUTE ON FUNCTION public.api_analytics_freshness() TO authenticated;

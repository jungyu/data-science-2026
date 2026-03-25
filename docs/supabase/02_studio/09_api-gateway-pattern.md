# Head First API Gateway — 用 Database Function 當 API

> **_"最好的 API 是讓前端工程師感覺不到資料庫的存在。"_**
>
> 你的大腦在想：「Supabase 不是自動產生 REST API 嗎？為什麼還要自己寫 Function？」
>
> 自動產生的 API 適合 CRUD。但真實世界需要分頁、排序、搜尋、JSONB 聚合、跨 Schema JOIN。
> 直接暴露 table + RLS 做這些事 = 效能災難 + 前端地獄。
>
> 解法：用 `public.api_*` function 當 **API Gateway** — 薄包裝、高效能、安全可控。

---

## 前置要求

- 已完成 `04_auth-and-rls.md`（理解 RLS、SECURITY DEFINER）
- 已完成 `05_api-storage-functions.md`（PostgREST 基礎）
- Docker 跑著（`supabase start`）
- 已執行 `../migrations/002_shop_schema.sql` ~ `005` 的 migration
- 瀏覽器打開 Studio `http://localhost:54323`

> 本章對應的完整 SQL：`../migrations/006_public_api.sql`

---

## Part 1: 為什麼不直接 SELECT？

PostgREST 自動幫每張 table 產生 REST API，對吧？

```
GET /rest/v1/products?select=*&status=eq.publish
```

簡單 CRUD 很方便。但真實需求長這樣：

```
「給我前 20 個上架商品，按價格排序，
  每個商品要附帶主圖、平均評分、評論數。」
```

### 用自動 API 的痛點

```
前端需要打 N+1 個 request：

1. GET /products?status=eq.publish&limit=20&order=price.asc
   → 拿到 20 個商品 id

2. GET /product_images?product_id=in.(id1,id2,...id20)&is_primary=eq.true
   → 拿到主圖

3. GET /reviews?product_id=in.(id1,id2,...id20)
   → 拿到評論，前端自己算平均

總共 3 次 API call + 前端 merge 資料 = 😵
```

### 你的大腦在想：「用 PostgREST 的 embed 語法不行嗎？」

可以，但遇到這些就卡住了：

| 需求 | PostgREST 自動 API | Database Function |
|------|-------------------|-------------------|
| 簡單 CRUD | 完美 | 殺雞用牛刀 |
| 分頁 + 動態排序 | 勉強（URL 參數複雜） | 乾淨的參數介面 |
| JSONB 聚合 | 不支援 | 原生 SQL 強項 |
| 跨 Schema JOIN | 不行（只暴露 public） | SECURITY DEFINER 繞過 |
| 全文搜尋 + trigram | 不行 | 原生 SQL |
| 複雜權限檢查 | RLS 效能差 | Function 內部控制 |

### 解法：Database Function = API Endpoint

```
┌─────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   前端 App   │────▶│  PostgREST       │────▶│  public.api_*   │
│             │     │  (API Gateway)    │     │  (thin wrapper) │
│ supabase    │◀────│                  │◀────│                 │
│ .rpc(...)   │     │  /rest/v1/rpc/   │     │  SECURITY       │
│             │     │  api_shop_*      │     │  DEFINER        │
└─────────────┘     └──────────────────┘     └────────┬────────┘
                                                      │
                                              ┌───────▼────────┐
                                              │  Domain Schemas │
                                              │  shop.*         │
                                              │  crawler.*      │
                                              │  rag.*          │
                                              │  analytics.*    │
                                              └────────────────┘
```

一次 API call，拿到完整資料。前端不用做任何 merge。

---

## Part 2: 設計原則

### 原則 1: PostgREST 只暴露 `public` schema

這是 Supabase 的設計：PostgREST 只看 `public`。你的業務邏輯在 `shop`、`crawler`、`rag`、`analytics` schema 裡，前端碰不到。

### 原則 2: 命名慣例 `api_{domain}_{action}`

```
api_shop_list_products       ← 商品列表
api_shop_get_product         ← 商品詳情
api_shop_search_products     ← 商品搜尋
api_shop_my_orders           ← 我的訂單
api_crawler_latest_articles  ← 最新文章
api_rag_search               ← 語意搜尋
api_analytics_dashboard      ← 儀表板
```

好處：在 Supabase Studio 的 **API Docs** 裡會按 domain 自然分組。
`api_shop_*` 全部排在一起，一目了然。

### 原則 3: SECURITY DEFINER + SET search_path

```sql
CREATE OR REPLACE FUNCTION public.api_shop_list_products(...)
RETURNS TABLE (...)
LANGUAGE SQL
STABLE                          -- ① 只讀 function
SECURITY DEFINER                -- ② 用 function owner 的權限執行
SET search_path = public        -- ③ 防止 search_path injection
AS $$
  SELECT ... FROM shop.products ...  -- ④ 可以讀 shop schema
$$;
```

> **腦筋急轉彎：「SECURITY DEFINER 跟 SECURITY INVOKER 差在哪？」**
>
> - **INVOKER**（預設）：用「呼叫者」的權限。anon 角色呼叫 → 用 anon 權限 → 碰不到 shop schema。
> - **DEFINER**：用「建立 function 的人」的權限。你用 superuser 建的 → 可以讀任何 schema。
>
> 所以 API function 用 DEFINER，讓 anon 也能透過 function 間接讀 shop 的資料。
> 但同時用 `SET search_path = public` 防止惡意的 search_path 注入攻擊。

### 原則 4: STABLE vs VOLATILE

| 標記 | 意義 | 用途 |
|------|------|------|
| `STABLE` | 同一 transaction 內，同參數回傳同結果 | 所有 SELECT（讀取）|
| `VOLATILE` | 每次呼叫可能不同結果 | INSERT/UPDATE/DELETE（寫入）|

PostgreSQL 可以對 STABLE function 做更多最佳化。**讀取用 STABLE，寫入用 VOLATILE**。

### 原則 5: GRANT 選擇性授權

```sql
-- 公開 API：匿名 + 登入者都能用
GRANT EXECUTE ON FUNCTION public.api_shop_list_products(...) TO anon, authenticated;

-- 私人 API：只有登入者能用
GRANT EXECUTE ON FUNCTION public.api_shop_my_orders(...) TO authenticated;

-- 管理 API：只有後端 service_role 能用
GRANT EXECUTE ON FUNCTION public.api_admin_something(...) TO service_role;
```

### 原則 6: 前端呼叫方式

```typescript
// 一行搞定 — 不用組 URL、不用 merge 資料
const { data, error } = await supabase.rpc('api_shop_list_products', {
  p_limit: 20,
  p_offset: 0,
  p_sort_by: 'price',
  p_sort_dir: 'asc'
})
```

---

## Part 3: Shop API — 商品與訂單

### api_shop_list_products — 分頁列表

這是最常見的 pattern：分頁 + 動態排序。

```sql
-- 重點：CASE WHEN 實現動態排序
CREATE OR REPLACE FUNCTION public.api_shop_list_products(
  p_limit    INTEGER DEFAULT 20,
  p_offset   INTEGER DEFAULT 0,
  p_sort_by  TEXT DEFAULT 'created_at',  -- 'created_at' | 'price' | 'title'
  p_sort_dir TEXT DEFAULT 'desc'         -- 'asc' | 'desc'
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
  image_url   TEXT,        -- 主圖（LEFT JOIN 一次搞定）
  avg_rating  NUMERIC,     -- 平均評分（GROUP BY 聚合）
  review_count BIGINT,     -- 評論數
  created_at  TIMESTAMPTZ
)
LANGUAGE SQL STABLE SECURITY DEFINER SET search_path = public
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
  LEFT JOIN shop.product_images pi
    ON pi.product_id = p.id AND pi.is_primary = TRUE
  LEFT JOIN shop.reviews r
    ON r.product_id = p.id AND r.is_visible = TRUE
  WHERE p.status = 'publish'
    AND p.deleted_at IS NULL
    AND p.parent_id IS NULL        -- 排除變體（variant）
  GROUP BY p.id, p.title, p.slug, p.excerpt,
           p.price, p.compare_at_price, p.currency,
           p.status, p.type, pi.storage_path, p.created_at
  ORDER BY
    -- 動態排序的 CASE WHEN pattern
    CASE WHEN p_sort_by = 'price'      AND p_sort_dir = 'asc'  THEN p.price END ASC,
    CASE WHEN p_sort_by = 'price'      AND p_sort_dir = 'desc' THEN p.price END DESC,
    CASE WHEN p_sort_by = 'title'      AND p_sort_dir = 'asc'  THEN p.title END ASC,
    CASE WHEN p_sort_by = 'title'      AND p_sort_dir = 'desc' THEN p.title END DESC,
    CASE WHEN p_sort_by = 'created_at' AND p_sort_dir = 'asc'  THEN p.created_at END ASC,
    CASE WHEN p_sort_by = 'created_at' AND p_sort_dir = 'desc' THEN p.created_at END DESC
  LIMIT p_limit OFFSET p_offset;
$$;
```

### 你的大腦在想：「CASE WHEN 排序看起來很冗長？」

是的，但這是 **純 SQL 動態排序**的標準做法。不用動態拼 SQL 字串（有 SQL injection 風險），不用 PL/pgSQL。每個 CASE WHEN 不匹配時回傳 NULL，NULL 在 ORDER BY 裡被忽略，所以只有匹配的那個 CASE 生效。

---

### api_shop_get_product — 商品詳情 + JSONB 聚合

```sql
-- 重點：用 correlated subquery + jsonb_agg 把圖片和變體包成 JSON
CREATE OR REPLACE FUNCTION public.api_shop_get_product(p_slug TEXT)
RETURNS TABLE (
  id               TEXT,
  title            TEXT,
  slug             TEXT,
  description      TEXT,
  price            NUMERIC,
  compare_at_price NUMERIC,
  currency         TEXT,
  images           JSONB,     -- [{id, url, alt, is_primary}, ...]
  variants         JSONB,     -- [{id, title, sku, price, metadata}, ...]
  avg_rating       NUMERIC,
  review_count     BIGINT,
  created_at       TIMESTAMPTZ
)
LANGUAGE SQL STABLE SECURITY DEFINER SET search_path = public
AS $$
  SELECT
    p.id, p.title, p.slug, p.description,
    p.price, p.compare_at_price, p.currency,
    -- 圖片 → JSONB array（correlated subquery）
    coalesce((
      SELECT jsonb_agg(jsonb_build_object(
        'id', pi.id,
        'url', pi.storage_path,
        'alt', pi.alt_text,
        'is_primary', pi.is_primary
      ) ORDER BY pi.sort_order)
      FROM shop.product_images pi WHERE pi.product_id = p.id
    ), '[]'::JSONB) AS images,
    -- 變體 → JSONB array
    coalesce((
      SELECT jsonb_agg(jsonb_build_object(
        'id', v.id, 'title', v.title,
        'sku', v.sku, 'price', v.price,
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
  WHERE p.slug = p_slug
    AND p.status = 'publish'
    AND p.deleted_at IS NULL
  GROUP BY p.id;
$$;
```

> **腦筋急轉彎：「為什麼用 JSONB 聚合，而不是讓前端打多次 API？」**
>
> 三個理由：
>
> 1. **效能**：一次 SQL query vs 3 次 HTTP roundtrip。延遲差 10 倍以上。
> 2. **原子性**：資料在同一個 snapshot，不會有 race condition。
> 3. **前端簡單**：`data.images[0].url` 直接用，不用 merge。
>
> 代價：SQL 寫起來比較複雜。但這是一次性的成本，前端每天省時間。

---

### api_shop_search_products — 混合搜尋

```sql
-- 重點：trigram（模糊比對）+ full-text（全文搜尋）雙管齊下
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
  relevance  REAL        -- 搜尋相關度分數
)
LANGUAGE SQL STABLE SECURITY DEFINER SET search_path = public
AS $$
  SELECT
    p.id, p.title, p.slug, p.excerpt, p.price, p.currency,
    pi.storage_path AS image_url,
    ts_rank(
      to_tsvector('simple', coalesce(p.title,'') || ' ' || coalesce(p.description,'')),
      plainto_tsquery('simple', p_query)
    ) AS relevance
  FROM shop.products p
  LEFT JOIN shop.product_images pi
    ON pi.product_id = p.id AND pi.is_primary = TRUE
  WHERE p.status = 'publish' AND p.deleted_at IS NULL
    AND (
      p.title % p_query                    -- trigram: 打錯字也能找到
      OR to_tsvector('simple',
           coalesce(p.title,'') || ' ' || coalesce(p.description,''))
         @@ plainto_tsquery('simple', p_query)  -- full-text: 詞幹比對
    )
  ORDER BY relevance DESC, p.title % p_query DESC
  LIMIT p_limit;
$$;
```

### api_shop_my_orders — 登入者限定

```sql
-- 重點：auth.uid() 確認身份，JSONB 聚合訂單明細
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
  items       JSONB,       -- [{product_title, sku, quantity, unit_price}, ...]
  created_at  TIMESTAMPTZ
)
LANGUAGE SQL STABLE SECURITY DEFINER SET search_path = public
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
  WHERE u.auth_user_id = (SELECT auth.uid())  -- ← 關鍵：只拿自己的
    AND o.deleted_at IS NULL
  ORDER BY o.created_at DESC
  LIMIT p_limit OFFSET p_offset;
$$;
```

注意 `auth.uid()` — 這是 Supabase 內建的 function，回傳目前 JWT 裡的 user UUID。搭配 SECURITY DEFINER，function 可以跨 schema 查詢，但只回傳該使用者自己的資料。

---

## Part 4: Crawler & RAG API — 薄包裝模式

這兩組 API 展示另一種 pattern：**薄包裝 (thin wrapper)**。

Function 本身不寫複雜邏輯，只做三件事：
1. 驗證輸入
2. 委派給 domain schema 的 function
3. 回傳結果

### api_crawler_latest_articles — 文章列表

```sql
CREATE OR REPLACE FUNCTION public.api_crawler_latest_articles(
  p_source_code TEXT DEFAULT NULL,   -- 篩選特定來源（NULL = 全部）
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
  tags         JSONB                 -- ["AI", "Python", "Data"]
)
LANGUAGE SQL STABLE SECURITY DEFINER SET search_path = public
AS $$
  SELECT
    a.id, a.title, s.name AS source_name,
    a.source_url, a.author_name, a.published_at,
    left(a.abstract, 300) AS abstract,   -- 截斷，不傳整篇
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
```

### api_rag_search — 語意搜尋橋接

```sql
-- 薄包裝：把 collection code 轉成 id，然後委派給 rag.match_chunks_with_document
CREATE OR REPLACE FUNCTION public.api_rag_search(
  query_embedding   vector(1536),      -- 前端先透過 Edge Function 產生 embedding
  p_collection_code TEXT,
  p_top_k           INTEGER DEFAULT 5,
  p_threshold       FLOAT8 DEFAULT 0.7
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
LANGUAGE SQL STABLE SECURITY DEFINER SET search_path = public
AS $$
  SELECT m.chunk_id, m.document_title, m.source_url,
         m.content, m.chunk_index, m.page_number, m.similarity
  FROM rag.match_chunks_with_document(
    query_embedding,
    (SELECT id FROM rag.collections       -- ← code → id 轉換
     WHERE code = p_collection_code AND is_active = TRUE),
    p_top_k,
    p_threshold
  ) m;
$$;
```

### api_rag_hybrid_search — Hybrid 搜尋橋接

```sql
-- 同樣薄包裝，委派給 rag.hybrid_search
CREATE OR REPLACE FUNCTION public.api_rag_hybrid_search(
  query_text        TEXT,
  query_embedding   vector(1536),
  p_collection_code TEXT,
  p_top_k           INTEGER DEFAULT 5,
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
LANGUAGE SQL STABLE SECURITY DEFINER SET search_path = public
AS $$
  SELECT h.chunk_id, h.document_id, h.content,
         h.semantic_score, h.fulltext_score, h.combined_score
  FROM rag.hybrid_search(
    query_text, query_embedding,
    (SELECT id FROM rag.collections
     WHERE code = p_collection_code AND is_active = TRUE),
    p_top_k, p_semantic_weight, 0.5
  ) h;
$$;
```

**Pattern 觀察**：RAG API 幾乎沒有自己的邏輯，只做「code → id 轉換」再轉手。這就是薄包裝的精髓 — public function 是 **門面**，不是 **引擎**。

---

## Part 5: Analytics API — 儀表板

Analytics API 展示第三種 pattern：**跨域聚合**。一個 function 彙整多個 schema 的指標。

### api_analytics_dashboard — 全域 KPI

```sql
-- 極薄包裝：直接委派給 analytics.system_dashboard
CREATE OR REPLACE FUNCTION public.api_analytics_dashboard(
  p_days_back INTEGER DEFAULT 1
)
RETURNS TABLE (
  domain        TEXT,      -- 'shop', 'crawler', 'rag'
  metric        TEXT,      -- 'total_revenue', 'article_count', ...
  value         NUMERIC,
  trend_vs_prev NUMERIC   -- 跟前一期比較（正 = 成長）
)
LANGUAGE SQL STABLE SECURITY DEFINER SET search_path = public
AS $$
  SELECT * FROM analytics.system_dashboard(p_days_back);
$$;
```

### api_analytics_revenue — 營收時序

```sql
CREATE OR REPLACE FUNCTION public.api_analytics_revenue(
  p_granularity TEXT DEFAULT 'day',    -- 'hour' | 'day' | 'week' | 'month'
  p_days_back   INTEGER DEFAULT 30
)
RETURNS TABLE (
  bucket          TIMESTAMPTZ,
  order_count     BIGINT,
  total_revenue   NUMERIC,
  avg_order_value NUMERIC
)
LANGUAGE SQL STABLE SECURITY DEFINER SET search_path = public
AS $$
  SELECT * FROM analytics.revenue_time_series(p_granularity, p_days_back);
$$;
```

### api_analytics_funnel — 轉換漏斗

```sql
CREATE OR REPLACE FUNCTION public.api_analytics_funnel(
  p_days_back INTEGER DEFAULT 7
)
RETURNS TABLE (
  step           TEXT,        -- 'view_product', 'add_to_cart', 'checkout', 'purchase'
  step_order     SMALLINT,
  sessions       BIGINT,
  conversion_pct NUMERIC     -- 相對上一步的轉換率
)
LANGUAGE SQL STABLE SECURITY DEFINER SET search_path = public
AS $$
  SELECT * FROM analytics.funnel_conversion(p_days_back);
$$;
```

### api_analytics_freshness — 資料新鮮度

```sql
-- 用途：前端儀表板顯示「資料最後更新：3 分鐘前」
CREATE OR REPLACE FUNCTION public.api_analytics_freshness()
RETURNS TABLE (
  schema_name      TEXT,          -- 'shop', 'crawler', 'rag'
  entity           TEXT,          -- 'orders', 'articles', 'chunks'
  latest_record_at TIMESTAMPTZ,
  minutes_ago      NUMERIC,
  is_stale         BOOLEAN        -- 超過閥值 = true
)
LANGUAGE SQL STABLE SECURITY DEFINER SET search_path = public
AS $$
  SELECT * FROM analytics.data_freshness();
$$;
```

---

## Part 6: GRANT 策略 — 誰能呼叫什麼

GRANT 是最後一道防線。就算 function 用了 SECURITY DEFINER，沒有 GRANT EXECUTE 的角色根本呼叫不了。

### 三種授權層級

```
┌─────────────────────────────────────────────────────────┐
│                    GRANT 層級                            │
├─────────────────────┬───────────────────────────────────┤
│  Public API         │  GRANT TO anon, authenticated     │
│  (商品、文章、搜尋)  │  → 任何人都能呼叫                  │
├─────────────────────┼───────────────────────────────────┤
│  Private API        │  GRANT TO authenticated           │
│  (我的訂單、地址、點數)│  → 要登入才能呼叫                 │
├─────────────────────┼───────────────────────────────────┤
│  Admin API          │  GRANT TO service_role            │
│  (管理操作)          │  → 只有後端 server 能呼叫          │
└─────────────────────┴───────────────────────────────────┘
```

### 完整 GRANT Block 範例

```sql
-- ============================================================
-- GRANTS — 完整授權區塊
-- ============================================================

-- ── Shop: 公開 API（匿名 + 登入者）──
GRANT EXECUTE ON FUNCTION public.api_shop_list_products(INTEGER, INTEGER, TEXT, TEXT)
  TO anon, authenticated;
GRANT EXECUTE ON FUNCTION public.api_shop_get_product(TEXT)
  TO anon, authenticated;
GRANT EXECUTE ON FUNCTION public.api_shop_search_products(TEXT, INTEGER)
  TO anon, authenticated;
GRANT EXECUTE ON FUNCTION public.api_shop_list_reviews(TEXT, INTEGER, INTEGER)
  TO anon, authenticated;
GRANT EXECUTE ON FUNCTION public.api_shop_list_stores()
  TO anon, authenticated;
GRANT EXECUTE ON FUNCTION public.api_shop_active_coupons()
  TO anon, authenticated;

-- ── Shop: 私人 API（僅登入者）──
GRANT EXECUTE ON FUNCTION public.api_shop_my_orders(INTEGER, INTEGER)
  TO authenticated;
GRANT EXECUTE ON FUNCTION public.api_shop_my_addresses()
  TO authenticated;
GRANT EXECUTE ON FUNCTION public.api_shop_my_points()
  TO authenticated;

-- ── Crawler: 僅登入者 ──
GRANT EXECUTE ON FUNCTION public.api_crawler_stats()
  TO authenticated;
GRANT EXECUTE ON FUNCTION public.api_crawler_latest_articles(TEXT, INTEGER, INTEGER)
  TO authenticated;
GRANT EXECUTE ON FUNCTION public.api_crawler_source_health()
  TO authenticated;

-- ── RAG: 公開 API（語意搜尋開放給所有人）──
GRANT EXECUTE ON FUNCTION public.api_rag_search(vector, TEXT, INTEGER, FLOAT8)
  TO anon, authenticated;
GRANT EXECUTE ON FUNCTION public.api_rag_hybrid_search(TEXT, vector, TEXT, INTEGER, FLOAT8)
  TO anon, authenticated;
GRANT EXECUTE ON FUNCTION public.api_rag_list_collections()
  TO anon, authenticated;

-- ── Analytics: 僅登入者（儀表板資料敏感）──
GRANT EXECUTE ON FUNCTION public.api_analytics_dashboard(INTEGER)
  TO authenticated;
GRANT EXECUTE ON FUNCTION public.api_analytics_revenue(TEXT, INTEGER)
  TO authenticated;
GRANT EXECUTE ON FUNCTION public.api_analytics_funnel(INTEGER)
  TO authenticated;
GRANT EXECUTE ON FUNCTION public.api_analytics_freshness()
  TO authenticated;
```

> **腦筋急轉彎：「為什麼不用 REVOKE ALL 先清掉再 GRANT？」**
>
> 好問題！在 production 環境中，最佳實踐是：
>
> ```sql
> -- Defense in depth: 先撤銷，再精準授權
> REVOKE ALL ON FUNCTION public.api_shop_my_orders(INTEGER, INTEGER) FROM PUBLIC;
> GRANT EXECUTE ON FUNCTION public.api_shop_my_orders(INTEGER, INTEGER) TO authenticated;
> ```
>
> `FROM PUBLIC` 撤銷預設的全域權限。這樣即使有人改了 PostgreSQL 的預設 GRANT 設定，你的 function 也不會被意外暴露。

---

## Part 7: 動手做 — 測試 API

### Step 1: 執行 Migration

```bash
# 確認 Supabase 跑著
supabase status

# 在 SQL Editor 執行（或直接用 psql）
psql postgresql://postgres:postgres@localhost:54322/postgres \
  -f docs/supabase/migrations/006_public_api.sql
```

### Step 2: cURL 測試公開 API

```bash
# 取得 anon key（supabase start 時會顯示）
ANON_KEY="eyJhbGciOiJIUzI1NiIs..."

# 商品列表（預設排序）
curl -s "http://localhost:54321/rest/v1/rpc/api_shop_list_products" \
  -H "apikey: $ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{"p_limit": 5}' | jq .

# 商品搜尋
curl -s "http://localhost:54321/rest/v1/rpc/api_shop_search_products" \
  -H "apikey: $ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{"p_query": "手機殼", "p_limit": 10}' | jq .

# 商品詳情
curl -s "http://localhost:54321/rest/v1/rpc/api_shop_get_product" \
  -H "apikey: $ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{"p_slug": "classic-tee"}' | jq .
```

### Step 3: cURL 測試私人 API（需要 JWT）

```bash
# 先登入取得 access_token
ACCESS_TOKEN=$(curl -s "http://localhost:54321/auth/v1/token?grant_type=password" \
  -H "apikey: $ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"testtest"}' | jq -r '.access_token')

# 我的訂單
curl -s "http://localhost:54321/rest/v1/rpc/api_shop_my_orders" \
  -H "apikey: $ANON_KEY" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"p_limit": 5}' | jq .

# 儀表板
curl -s "http://localhost:54321/rest/v1/rpc/api_analytics_dashboard" \
  -H "apikey: $ANON_KEY" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"p_days_back": 7}' | jq .
```

### Step 4: Python SDK 測試

```python
from supabase import create_client

supabase = create_client(
    "http://localhost:54321",
    "eyJhbGciOiJIUzI1NiIs..."  # anon key
)

# 公開 API — 不用登入
products = supabase.rpc('api_shop_list_products', {
    'p_limit': 10,
    'p_sort_by': 'price',
    'p_sort_dir': 'asc'
}).execute()

print(products.data)

# 私人 API — 先登入
supabase.auth.sign_in_with_password({
    'email': 'test@test.com',
    'password': 'testtest'
})

orders = supabase.rpc('api_shop_my_orders', {
    'p_limit': 5
}).execute()

print(orders.data)
```

### Step 5: 在 Studio 查看 API Docs

1. 打開 `http://localhost:54323`
2. 左側選單 → **API Docs**
3. 搜尋 `api_shop` → 看到所有 Shop API 排在一起
4. 點進去看參數說明和回傳格式

> 這就是命名慣例 `api_{domain}_{action}` 的好處 — API Docs 自動按 domain 分群。

---

## 搭配檔案

| 檔案 | 用途 |
|------|------|
| `../migrations/006_public_api.sql` | 完整 API 函數定義（本章所有 function 的原始碼）|
| `05_api-storage-functions.md` | PostgREST 基礎（前置技能）|

---

## 自我檢查清單

```
□ 我能解釋 SECURITY DEFINER vs SECURITY INVOKER 的差別
□ 我知道 SET search_path = public 的安全意義（防止 search_path injection）
□ 我能區分 STABLE（讀取）和 VOLATILE（寫入）的使用時機
□ 我理解 GRANT TO anon vs authenticated 的差別，以及何時用哪個
□ 我會用 supabase.rpc('function_name', params) 呼叫 API function
□ 我理解 CASE WHEN dynamic sort pattern 的運作原理
□ 我能寫出 JSONB aggregation 來組合巢狀資料（images、variants、items）
□ 我知道 auth.uid() 如何在 SECURITY DEFINER function 中識別使用者
□ 我理解「薄包裝」pattern — public function 只做轉譯和委派
□ 我能用 cURL 測試 PostgREST 的 /rpc/ endpoint
□ 我知道 REVOKE ALL + GRANT 的 defense-in-depth 策略
□ 我會在 Studio API Docs 中查看自動產生的 API 文件
```

---

## 下一步

API Gateway 建好了，你的資料庫現在有乾淨的 API 介面。接下來學習 Realtime 和 Storage — 讓你的應用程式能即時更新和管理檔案。

> 繼續前進 → [`../labs/06_lab-realtime-storage.md`](../labs/06_lab-realtime-storage.md)

# Head First Shop API — 商城的前門

> **"顧客不需要知道倉庫在幾樓。他只要走進店裡，看到商品、選好結帳。API 就是那扇門。"**

這份指南涵蓋 [`006_public_api.sql`](../migrations/006_public_api.sql) 的 **第 27–345 行**——
9 個 Shop API function，分成兩區：**商品瀏覽**（任何人）和**顧客專區**（登入後）。

---

## 搭配閱讀

| 你在讀的 | SQL 行號 | 學什麼 |
|----------|----------|--------|
| 商品列表 | 32–80 | 分頁 + 動態排序 |
| 商品詳情 | 83–141 | 子查詢 JSON 打包 |
| 商品搜尋 | 144–180 | trigram + full-text 雙模式 |
| 評論列表 | 183–211 | 跨表 JOIN + 暱名處理 |
| 門市列表 | 214–232 | 最簡單的 API |
| 有效優惠券 | 321–345 | 時間條件 + 使用次數限制 |
| 我的訂單 | 240–277 | auth.uid() + 訂單明細 JSON |
| 我的地址簿 | 280–304 | auth.uid() + 預設地址排序 |
| 我的點數 | 307–318 | 聚合函數 + NULL 處理 |

---

# Part 1：商品瀏覽 API（anon + authenticated）

這區的 API 任何人都能呼叫——包括沒登入的訪客。

---

## 1.1 `api_shop_list_products` — 商品列表

> **📖 SQL 第 32–80 行**

這是最常被呼叫的 API。首頁、分類頁、搜尋結果——都靠它。

### 參數

| 參數 | 型別 | 預設值 | 說明 |
|------|------|--------|------|
| `p_limit` | INTEGER | 20 | 每頁幾筆 |
| `p_offset` | INTEGER | 0 | 跳過幾筆（分頁用） |
| `p_sort_by` | TEXT | `'created_at'` | 排序欄位：`created_at` / `price` / `title` |
| `p_sort_dir` | TEXT | `'desc'` | 排序方向：`asc` / `desc` |

### 回傳欄位

| 欄位 | 型別 | 說明 |
|------|------|------|
| `id` | TEXT | 商品 ULID |
| `title` | TEXT | 商品名稱 |
| `slug` | TEXT | URL slug |
| `excerpt` | TEXT | 簡短摘要 |
| `price` | NUMERIC | 售價 |
| `compare_at_price` | NUMERIC | 原價（劃線價） |
| `currency` | TEXT | 幣別 |
| `status` | TEXT | 狀態 |
| `type` | TEXT | 商品類型 |
| `image_url` | TEXT | 主圖 URL |
| `avg_rating` | NUMERIC | 平均評分（1 位小數） |
| `review_count` | BIGINT | 評論數 |
| `created_at` | TIMESTAMPTZ | 建立時間 |

### 前端呼叫

```ts
// 預設：最新 20 筆
const { data } = await supabase.rpc('api_shop_list_products')

// 第 2 頁，依價格低到高
const { data } = await supabase.rpc('api_shop_list_products', {
  p_limit: 20,
  p_offset: 20,
  p_sort_by: 'price',
  p_sort_dir: 'asc'
})
```

### 裡面在幹嘛？

```sql
FROM shop.products p
LEFT JOIN shop.product_images pi ON pi.product_id = p.id AND pi.is_primary = TRUE
LEFT JOIN shop.reviews r ON r.product_id = p.id AND r.is_visible = TRUE
WHERE p.status = 'publish' AND p.deleted_at IS NULL AND p.parent_id IS NULL
GROUP BY ...
```

拆解每一行：

| 邏輯 | 為什麼 |
|------|--------|
| `LEFT JOIN product_images ... is_primary = TRUE` | 只抓主圖，沒有主圖也不影響商品顯示 |
| `LEFT JOIN reviews ... is_visible = TRUE` | 計算平均分和評論數，只算通過審核的 |
| `status = 'publish'` | 只顯示已上架商品 |
| `deleted_at IS NULL` | 軟刪除過濾 |
| `parent_id IS NULL` | 排除變體（variant），只顯示父商品 |
| `GROUP BY` | 因為 LEFT JOIN reviews 會展開，需要聚合回來 |

> ### 🧠 你的大腦在想…
>
> 「動態排序那段 CASE WHEN 好醜，為什麼不用 `ORDER BY p_sort_by`？」
>
> 因為 SQL 不允許用參數值當欄位名。`ORDER BY 'price'` 不會按 price 欄位排序，
> 它只是按一個字串常數排——等於沒排。
>
> CASE WHEN 是 SQL 裡唯一安全的動態排序方式。
> 另一種做法是用 PL/pgSQL 的 `EXECUTE format(...)` 拼 SQL，
> 但那就要處理 SQL injection 風險。CASE WHEN 醜但安全。

---

## 1.2 `api_shop_get_product` — 商品詳情

> **📖 SQL 第 83–141 行**

點進商品頁時呼叫。比列表 API 多了：description、sku、metadata、**全部圖片**、**全部變體**。

### 參數

| 參數 | 型別 | 說明 |
|------|------|------|
| `p_slug` | TEXT | 商品的 URL slug（不是 ID） |

### 回傳欄位

| 欄位 | 型別 | 說明 |
|------|------|------|
| `id` | TEXT | 商品 ULID |
| `title` | TEXT | 商品名稱 |
| `slug` | TEXT | URL slug |
| `description` | TEXT | 完整描述（列表 API 沒有這個） |
| `excerpt` | TEXT | 簡短摘要 |
| `price` | NUMERIC | 售價 |
| `compare_at_price` | NUMERIC | 原價（劃線價） |
| `currency` | TEXT | 幣別 |
| `sku` | TEXT | 商品編號 |
| `type` | TEXT | 商品類型 |
| `is_taxable` | BOOLEAN | 是否含稅 |
| `metadata` | JSONB | 商品自訂屬性 |
| `images` | JSONB | 圖片陣列 `[{id, url, alt, is_primary}]` |
| `variants` | JSONB | 變體陣列 `[{id, title, sku, price, metadata}]` |
| `avg_rating` | NUMERIC | 平均評分（1 位小數） |
| `review_count` | BIGINT | 評論數 |
| `created_at` | TIMESTAMPTZ | 建立時間 |

### 前端呼叫

```ts
const { data } = await supabase.rpc('api_shop_get_product', {
  p_slug: 'organic-green-tea-500g'
})

// data[0].images → [{id: '...', url: '...', alt: '有機綠茶', is_primary: true}]
// data[0].variants → [{id: '...', title: '250g', sku: 'TEA-250', price: 350}]
```

### JSONB 子查詢拆解

```sql
coalesce((
  SELECT jsonb_agg(jsonb_build_object(
    'id', pi.id,
    'url', pi.storage_path,
    'alt', pi.alt_text,
    'is_primary', pi.is_primary
  ) ORDER BY pi.sort_order)
  FROM shop.product_images pi WHERE pi.product_id = p.id
), '[]'::JSONB) AS images
```

| 技巧 | 作用 |
|------|------|
| `jsonb_agg()` | 把多行結果聚合成一個 JSON array |
| `jsonb_build_object()` | 把欄位組成 JSON object |
| `ORDER BY pi.sort_order` | 圖片按排序順序排列 |
| `coalesce(..., '[]')` | 沒有圖片時回傳空陣列，不是 NULL |

> ### 💡 為什麼用 slug 不用 ID？
>
> SEO。URL 裡放 `organic-green-tea-500g` 比 `01HXY8Z3K4ABCDEF` 好看，
> 搜尋引擎也能從 URL 理解頁面內容。slug 有 UNIQUE 約束，可以安全當查詢條件。

---

## 1.3 `api_shop_search_products` — 商品搜尋

> **📖 SQL 第 144–180 行**

這個 function 同時用了兩種搜尋技術：**trigram similarity** 和 **full-text search**。

### 參數

| 參數 | 型別 | 預設值 | 說明 |
|------|------|--------|------|
| `p_query` | TEXT | — | 搜尋關鍵字 |
| `p_limit` | INTEGER | 20 | 最多幾筆 |

### 前端呼叫

```ts
const { data } = await supabase.rpc('api_shop_search_products', {
  p_query: '綠茶',
  p_limit: 10
})
```

### 雙引擎搜尋

```sql
WHERE p.status = 'publish' AND p.deleted_at IS NULL
  AND (
    p.title % p_query                   -- trigram：模糊比對
    OR to_tsvector('simple', ...) @@ plainto_tsquery('simple', p_query)
                                         -- full-text：精確搜尋
  )
ORDER BY relevance DESC, p.title % p_query DESC
```

**Trigram（`%` 運算子）**：把字串切成三字母一組，比較相似度。
打錯字也能找到：`grean tea` → 還是能匹配 `green tea`。

**Full-text（`@@` 運算子）**：把文字解析成詞彙，做精確的語意匹配。
搜 `綠茶` 能找到 description 裡提到「高山綠茶」的商品。

**排序**：先按 `ts_rank` 的 relevance 分數，再按 trigram 相似度。兩種引擎的結果 merge 在一起，最相關的排最前面。

> ### 🧠 你的大腦在想…
>
> 「為什麼用 `'simple'` 語言而不是 `'english'` 或 `'chinese'`？」
>
> `'simple'` 不做 stemming（詞幹提取），對中文和混合語言最安全。
> 中文的 full-text search 在 PostgreSQL 裡需要額外的 parser（如 `zhparser`），
> 用 `'simple'` 至少能做到基本的字串匹配。
> 如果需要更好的中文搜尋，可以考慮搭配 RAG 的向量搜尋。

> ### ⚠️ Index 依賴
>
> 這個 function 的效能**高度依賴** `pg_trgm` 的 GIN index。
> 如果 `shop.products.title` 上沒有 trigram index，`%` 運算子會退化成 sequential scan。
> 確認 `002_shop_schema.sql` 裡有類似這樣的 index：
>
> ```sql
> CREATE INDEX idx_products_title_trgm ON shop.products USING gin (title gin_trgm_ops);
> ```
>
> 同理，full-text search 需要 `tsvector` 的 GIN index 才能高效運作。

---

## 1.4 `api_shop_list_reviews` — 商品評論列表

> **📖 SQL 第 183–211 行**

### 參數

| 參數 | 型別 | 預設值 | 說明 |
|------|------|--------|------|
| `p_product_id` | TEXT | — | 商品 ID |
| `p_limit` | INTEGER | 20 | 每頁幾筆 |
| `p_offset` | INTEGER | 0 | 跳過幾筆 |

### 回傳欄位

| 欄位 | 型別 | 說明 |
|------|------|------|
| `id` | TEXT | 評論 ULID |
| `rating` | SMALLINT | 評分（1–5） |
| `title` | TEXT | 評論標題 |
| `body` | TEXT | 評論內容 |
| `is_verified` | BOOLEAN | 是否已驗證購買 |
| `customer_name` | TEXT | 顧客顯示名稱（隱私處理後） |
| `created_at` | TIMESTAMPTZ | 評論時間 |

### 前端呼叫

```ts
const { data } = await supabase.rpc('api_shop_list_reviews', {
  p_product_id: '01HXY8Z3K4...',
  p_limit: 10,
  p_offset: 0
})
```

### 匿名處理

```sql
coalesce(nullif(pr.display_name, ''), pr.username) AS customer_name
```

這行做了什麼：
1. 如果 `display_name` 是空字串 → `nullif` 把它變成 NULL
2. 如果是 NULL → `coalesce` 改用 `username`
3. 結果：優先顯示暱稱，沒暱稱就顯示帳號名

**注意**：只回傳 `customer_name`，不回傳 `customer_id`。這是隱私保護——別人不能透過評論反查使用者。

---

## 1.5 `api_shop_list_stores` — 門市列表

> **📖 SQL 第 214–232 行**

最簡單的 API。沒有參數，沒有 JOIN，沒有分頁。

```ts
const { data } = await supabase.rpc('api_shop_list_stores')
// [{id, name, phone, city, address, is_active}]
```

只列出 `is_active = TRUE AND deleted_at IS NULL` 的門市，按名稱排序。

---

## 1.6 `api_shop_active_coupons` — 有效優惠券

> **📖 SQL 第 321–345 行**

回傳目前可以使用的優惠券。雖然位於 SQL 的「顧客」區塊附近，但 GRANT 是 `anon, authenticated`——**未登入也能看**。

```ts
const { data } = await supabase.rpc('api_shop_active_coupons')
```

### 回傳欄位

| 欄位 | 型別 | 說明 |
|------|------|------|
| `id` | TEXT | 優惠券 ULID |
| `code` | TEXT | 優惠碼 |
| `description` | TEXT | 說明 |
| `discount_type` | TEXT | 折扣類型（百分比 / 固定金額） |
| `discount_value` | NUMERIC | 折扣值 |
| `min_order_amount` | NUMERIC | 最低消費門檻 |
| `expires_at` | TIMESTAMPTZ | 到期時間 |

### 四重過濾條件

```sql
WHERE c.is_active = TRUE AND c.deleted_at IS NULL        -- 基本：啟用且未刪除
  AND (c.starts_at IS NULL OR c.starts_at <= NOW())       -- 已經開始
  AND (c.expires_at IS NULL OR c.expires_at > NOW())      -- 還沒過期
  AND (c.max_uses IS NULL OR c.used_count < c.max_uses)   -- 還有剩餘次數
```

| 條件 | NULL 語意 |
|------|----------|
| `starts_at IS NULL` | 沒設開始時間 = 立即生效 |
| `expires_at IS NULL` | 沒設到期時間 = 永不過期 |
| `max_uses IS NULL` | 沒設使用上限 = 無限次 |

### 排序

```sql
ORDER BY c.expires_at ASC NULLS LAST
```

快到期的排前面（鼓勵使用者趕快用），永不過期的排最後。

> ### 🧠 你的大腦在想…
>
> 「優惠券不是應該登入才能看嗎？為什麼給 anon？」
>
> 這是行銷策略——讓未登入的訪客也看到「現在有優惠」，促使他們註冊/登入。
> 至於「使用」優惠券，那是結帳流程的事，會有另一個 authenticated-only 的 function。

---

# Part 2：顧客專區 API（authenticated only）

這區的 API 需要登入。它們都用 `auth.uid()` 取得「我是誰」。

---

## 2.1 `api_shop_my_orders` — 我的訂單

> **📖 SQL 第 240–277 行**

### 參數

| 參數 | 型別 | 預設值 | 說明 |
|------|------|--------|------|
| `p_limit` | INTEGER | 20 | 每頁幾筆 |
| `p_offset` | INTEGER | 0 | 跳過幾筆 |

### 回傳欄位

| 欄位 | 型別 | 說明 |
|------|------|------|
| `id` | TEXT | 訂單 ULID |
| `status` | TEXT | 訂單狀態 |
| `total` | NUMERIC | 訂單總額 |
| `currency` | TEXT | 幣別 |
| `num_items` | INTEGER | 商品數量（底層欄位為 `num_items_sold`） |
| `items` | JSONB | 訂單明細 `[{product_title, sku, quantity, unit_price, net_revenue}]` |
| `created_at` | TIMESTAMPTZ | 下單時間 |

### 前端呼叫

```ts
const { data } = await supabase.rpc('api_shop_my_orders', {
  p_limit: 10, p_offset: 0
})

// data[0].items → [{product_title: '有機綠茶', quantity: 2, unit_price: 450, ...}]
```

### 身份驗證鏈

```sql
FROM shop.orders o
JOIN shop.users u ON u.id = o.customer_id
WHERE u.auth_user_id = (SELECT auth.uid())
```

```
Supabase Auth (JWT)
   ↓ auth.uid() = '550e8400-...'
shop.users (auth_user_id = '550e8400-...')
   ↓ u.id = '01HXY...'
shop.orders (customer_id = '01HXY...')
   ↓ 只拿到自己的訂單
```

**為什麼多一層 `shop.users`？** 因為 `auth.users` 是 Supabase 管的，我們的業務表用自己的 ULID 主鍵。`shop.users` 是橋接表，把 Supabase UUID 對應到我們的 ULID。

---

## 2.2 `api_shop_my_addresses` — 我的地址簿

> **📖 SQL 第 280–304 行**

無參數。回傳當前使用者的所有地址。

```ts
const { data } = await supabase.rpc('api_shop_my_addresses')
```

### 排序邏輯

```sql
ORDER BY a.is_default DESC, a.created_at DESC
```

預設地址排第一（`is_default DESC`），其餘按建立時間倒序。
前端可以直接把 `data[0]` 當預設地址用。

---

## 2.3 `api_shop_my_points` — 我的點數餘額

> **📖 SQL 第 307–318 行**

最精簡的 API——回傳一個數字。

```ts
const { data } = await supabase.rpc('api_shop_my_points')
// data[0].balance → 1250
```

### NULL 防禦

```sql
SELECT coalesce(sum(pr.points), 0) AS balance
```

`coalesce(..., 0)`：如果使用者沒有任何點數紀錄，`sum()` 會回傳 NULL。
`coalesce` 把 NULL 轉成 0——前端不用處理 null case。

---

## 延伸閱讀

**底層 schema 文件**（這些 API 背後的表結構）：

| 文件 | 涵蓋內容 |
|------|----------|
| [03_shop/01_foundation-identity.md](../03_shop/01_foundation-identity.md) | ULID、Auth bridge、profiles |
| [03_shop/02_organization-catalog.md](../03_shop/02_organization-catalog.md) | 組織層級、商品建模 |
| [03_shop/04_coupons-commerce.md](../03_shop/04_coupons-commerce.md) | 折扣券、訂單、付款 |
| [03_shop/05_security-rls.md](../03_shop/05_security-rls.md) | RLS Policy（與 API GRANT 互補） |
| [`002_shop_schema.sql`](../migrations/002_shop_schema.sql) | 完整 SQL schema |

---

## 接下來

- [03_crawler-api.md](03_crawler-api.md)——爬蟲 API
- [04_rag-api.md](04_rag-api.md)——RAG 語意搜尋 API
- [05_analytics-api.md](05_analytics-api.md)——Analytics 儀表板 API

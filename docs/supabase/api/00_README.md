# Head First Public API Layer — PostgREST Gateway

> **"前端不該知道你的 schema 長什麼樣。它只需要知道：呼叫哪個 function、傳什麼參數、拿回什麼資料。"**

歡迎來到 Public API 指南。我們要搞懂 [`006_public_api.sql`](../migrations/006_public_api.sql) 裡的 **20 個 RPC function**——它們是你的前端唯一碰得到的「窗口」。

不是直接 SELECT table。不是暴露整個 schema。是一道精心設計的 **薄包裝層**。

---

## 這份指南適合誰？

你如果符合以下任一條件：

- 想用 `supabase.rpc()` 呼叫 API 但搞不懂後端怎麼接
- 聽過 SECURITY DEFINER 但不確定為什麼要用
- 想理解「把 function 當 API endpoint」這個 PostgREST 模式
- 需要一份完整的 API 參考手冊來對接前端

---

## 搭配檔案

| 檔案 | 用途 |
|------|------|
| [`006_public_api.sql`](../migrations/006_public_api.sql) | 完整可執行的 SQL（683 行） |
| [`01_design-patterns.md`](01_design-patterns.md) | 設計模式：SECURITY DEFINER、命名慣例、Gateway 架構 |
| [`02_shop-api.md`](02_shop-api.md) | Shop 商城 API（商品、搜尋、訂單、地址、點數） |
| [`03_crawler-api.md`](03_crawler-api.md) | Crawler 爬蟲 API（統計、文章、來源健康度） |
| [`04_rag-api.md`](04_rag-api.md) | RAG 語意搜尋 API（向量搜尋、Hybrid、知識庫） |
| [`05_analytics-api.md`](05_analytics-api.md) | Analytics 儀表板 API（營收、漏斗、品質、新鮮度） |

**使用方式**：邊讀章節，邊打開 `.sql` 檔案對照。每個 function 都標註了 SQL 行號。

---

## 全景地圖

先看大局。20 個 function 分成 4 個 domain，兩種存取等級：

```
            ┌────────────────────────────────────────────────┐
            │            public schema (PostgREST)           │
            ├────────────┬───────────┬──────────┬────────────┤
            │   SHOP     │  CRAWLER  │   RAG    │ ANALYTICS  │
            │  9 funcs   │  3 funcs  │ 3 funcs  │  5 funcs   │
            ├────────────┼───────────┼──────────┼────────────┤
  anon ✓    │ 6 (瀏覽)   │     —     │ 3 (搜尋) │     —      │
  auth ✓    │ 6+3 (全部) │ 3 (狀態)  │ 3 (搜尋) │ 5 (儀表板) │
            └────────────┴───────────┴──────────┴────────────┘
                  ↓              ↓          ↓           ↓
              shop.*       crawler.*     rag.*    analytics.*
            (業務邏輯)      (業務邏輯)   (業務邏輯)   (業務邏輯)
```

> `6+3` 表示 authenticated 使用者可用全部 9 個 Shop API（6 個公開 + 3 個專屬）。

---

## API 完整目錄

### 🛒 Shop — 商品（Public）

| Function | 說明 | 權限 | SQL 行號 |
|----------|------|------|----------|
| `api_shop_list_products` | 商品列表（分頁 + 排序） | anon, auth | 32–80 |
| `api_shop_get_product` | 商品詳情（含變體、圖片、評價） | anon, auth | 83–141 |
| `api_shop_search_products` | 商品搜尋（trigram + full-text） | anon, auth | 144–180 |
| `api_shop_list_reviews` | 商品評論列表 | anon, auth | 183–211 |
| `api_shop_list_stores` | 門市列表 | anon, auth | 214–232 |
| `api_shop_active_coupons` | 有效優惠券列表 | anon, auth | 321–345 |

### 🛒 Shop — 顧客（Authenticated）

| Function | 說明 | 權限 | SQL 行號 |
|----------|------|------|----------|
| `api_shop_my_orders` | 我的訂單（含明細 JSON） | auth | 240–277 |
| `api_shop_my_addresses` | 我的地址簿 | auth | 280–304 |
| `api_shop_my_points` | 我的點數餘額 | auth | 307–318 |

### 🕷️ Crawler（Authenticated）

| Function | 說明 | 權限 | SQL 行號 |
|----------|------|------|----------|
| `api_crawler_stats` | 爬蟲統計總覽 | auth | 353–375 |
| `api_crawler_latest_articles` | 最新文章列表 | auth | 378–414 |
| `api_crawler_source_health` | 各來源健康度（7 日） | auth | 417–447 |

### 🔍 RAG（Public）

| Function | 說明 | 權限 | SQL 行號 |
|----------|------|------|----------|
| `api_rag_search` | 語意搜尋（cosine similarity） | anon, auth | 455–484 |
| `api_rag_hybrid_search` | Hybrid 搜尋（語意 + 全文） | anon, auth | 487–517 |
| `api_rag_list_collections` | 知識庫列表 | anon, auth | 520–544 |

### 📊 Analytics（Authenticated）

| Function | 說明 | 權限 | SQL 行號 |
|----------|------|------|----------|
| `api_analytics_dashboard` | 全域儀表板 | auth | 552–567 |
| `api_analytics_revenue` | 營收趨勢 | auth | 570–586 |
| `api_analytics_funnel` | 漏斗轉換率 | auth | 589–604 |
| `api_analytics_rag_quality` | RAG 品質趨勢 | auth | 607–630 |
| `api_analytics_freshness` | 資料新鮮度 | auth | 633–647 |

---

## 前端呼叫速查

所有 API 的呼叫方式都一樣——`supabase.rpc()`：

```ts
// 未登入也能用（anon）
const { data } = await supabase.rpc('api_shop_list_products', {
  p_limit: 20, p_offset: 0
})

// 需要登入（authenticated）
const { data } = await supabase.rpc('api_shop_my_orders', {
  p_limit: 10, p_offset: 0
})
```

> ### 🧠 你的大腦在想…
>
> 「為什麼不直接 `supabase.from('products').select('*')`？」
>
> 因為我們的表不在 `public` schema 裡。PostgREST 預設只暴露 `public`。
> 把業務表藏在 `shop.*`、`crawler.*` 等 schema 裡，再透過 `public` function
> 提供精確控制的存取窗口——這就是 **Gateway Pattern**。
>
> 好處：前端碰不到原始 table、JOIN 邏輯封裝在 function 裡、
> 改 schema 不影響 API 介面。壞處：要多寫一層 function。值得。

---

## 接下來

1. **先讀 [01_design-patterns.md](01_design-patterns.md)**——理解為什麼每個 function 都長那個樣子
2. 再依你負責的 domain 讀對應章節
3. 邊讀邊對照 SQL 原始碼

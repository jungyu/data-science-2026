# Head First Analytics API — 儀表板的資料引擎

> **"數據不會自己說話。你要問對問題，它才回答。這 5 個 API 就是你問問題的方式。"**

這份指南涵蓋 [`006_public_api.sql`](../migrations/006_public_api.sql) 的 **第 547–647 行**——
5 個 Analytics API function。全部都是 **authenticated only**。

---

## 搭配閱讀

| 你在讀的 | SQL 行號 | 學什麼 |
|----------|----------|--------|
| 全域儀表板 | 552–567 | 最薄的 bridge function |
| 營收趨勢 | 570–586 | 時間序列 + 粒度切換 |
| 漏斗轉換率 | 589–604 | 漏斗分析模型 |
| RAG 品質趨勢 | 607–630 | 多維品質指標 |
| 資料新鮮度 | 633–647 | 跨 schema 監控 |

---

## 這 5 個 API 的共同特色

它們全部都是 **bridge function**——自己幾乎不寫邏輯，直接呼叫 `analytics.*` schema 裡的對應函數：

```sql
-- 每個都長這樣
AS $$
  SELECT * FROM analytics.some_function(params);
$$;
```

**為什麼還需要 public wrapper？**

```
前端 → PostgREST → public schema → analytics schema
         ↑                              ↑
   只能看到 public            業務邏輯在這裡
```

PostgREST 看不到 `analytics` schema。所以需要在 `public` 建一個「窗口」。
同時，GRANT 和 SECURITY DEFINER 也在 public 層控制，analytics 層不用管權限。

---

## 1. `api_analytics_dashboard` — 全域儀表板

> **📖 SQL 第 552–567 行**

一個 API 拿到所有 domain 的關鍵指標。適合管理後台首頁。

### 參數

| 參數 | 型別 | 預設值 | 說明 |
|------|------|--------|------|
| `p_days_back` | INTEGER | 1 | 往回看幾天 |

### 回傳欄位

| 欄位 | 型別 | 說明 |
|------|------|------|
| `domain` | TEXT | 領域（shop / crawler / rag） |
| `metric` | TEXT | 指標名稱 |
| `value` | NUMERIC | 當前值 |
| `trend_vs_prev` | NUMERIC | 與前期比較（正數 = 成長） |

### 前端呼叫

```ts
const { data } = await supabase.rpc('api_analytics_dashboard', {
  p_days_back: 1
})

// data →
// [
//   { domain: 'shop', metric: 'orders', value: 42, trend_vs_prev: 12.5 },
//   { domain: 'shop', metric: 'revenue', value: 158000, trend_vs_prev: -3.2 },
//   { domain: 'crawler', metric: 'articles', value: 230, trend_vs_prev: 8.7 },
//   { domain: 'rag', metric: 'queries', value: 1500, trend_vs_prev: 25.0 },
//   ...
// ]
```

### 為什麼用「long format」而不是「wide format」？

回傳的是 `(domain, metric, value)` 的長格式，而不是 `{orders: 42, revenue: 158000}` 的寬格式。

| | Long Format | Wide Format |
|---|---|---|
| **新增指標** | 多一行資料，不改 API 簽名 | 要改 RETURNS TABLE |
| **前端迭代** | `data.map(row => ...)` 動態渲染 | 每個欄位寫死在 template |
| **跨 domain** | 統一結構，方便比較 | 每個 domain 結構不同 |

Long format 的好處：analytics 團隊加新指標，不需要改 API、不需要改前端 card component——自動出現。

---

## 2. `api_analytics_revenue` — 營收趨勢

> **📖 SQL 第 570–586 行**

時間序列資料。適合折線圖。

### 參數

| 參數 | 型別 | 預設值 | 說明 |
|------|------|--------|------|
| `p_granularity` | TEXT | `'day'` | 時間粒度：`hour` / `day` / `week` / `month` |
| `p_days_back` | INTEGER | 30 | 往回看幾天 |

### 回傳欄位

| 欄位 | 型別 | 說明 |
|------|------|------|
| `bucket` | TIMESTAMPTZ | 時間桶（依粒度） |
| `order_count` | BIGINT | 訂單數 |
| `total_revenue` | NUMERIC | 總營收 |
| `avg_order_value` | NUMERIC | 平均客單價 |

### 前端呼叫

```ts
// 過去 30 天，按日
const { data } = await supabase.rpc('api_analytics_revenue', {
  p_granularity: 'day',
  p_days_back: 30
})

// 過去 90 天，按週
const { data } = await supabase.rpc('api_analytics_revenue', {
  p_granularity: 'week',
  p_days_back: 90
})
```

> ### 🧠 你的大腦在想…
>
> 「p_granularity 是怎麼變成 `date_trunc` 的？」
>
> 這個邏輯在 `analytics.revenue_time_series()` 裡。
> 通常會用類似這樣的 SQL：
>
> ```sql
> SELECT date_trunc(p_granularity, o.created_at) AS bucket,
>        count(*) AS order_count,
>        sum(o.total) AS total_revenue,
>        avg(o.total) AS avg_order_value
> FROM shop.orders o
> WHERE o.created_at >= NOW() - (p_days_back || ' days')::INTERVAL
> GROUP BY bucket
> ORDER BY bucket;
> ```
>
> `date_trunc('day', timestamp)` → 截斷到日
> `date_trunc('week', timestamp)` → 截斷到週一
> `date_trunc('month', timestamp)` → 截斷到月初

---

## 3. `api_analytics_funnel` — 漏斗轉換率

> **📖 SQL 第 589–604 行**

電商最經典的分析：「有多少人瀏覽 → 加入購物車 → 結帳 → 完成付款」。

### 參數

| 參數 | 型別 | 預設值 | 說明 |
|------|------|--------|------|
| `p_days_back` | INTEGER | 7 | 往回看幾天 |

### 回傳欄位

| 欄位 | 型別 | 說明 |
|------|------|------|
| `step` | TEXT | 漏斗步驟名稱 |
| `step_order` | SMALLINT | 步驟序號（用來排序） |
| `sessions` | BIGINT | 到達此步驟的 session 數 |
| `conversion_pct` | NUMERIC | 轉換率 %（相對於上一步） |

### 前端呼叫

```ts
const { data } = await supabase.rpc('api_analytics_funnel', {
  p_days_back: 7
})

// data →
// [
//   { step: 'page_view',    step_order: 1, sessions: 10000, conversion_pct: 100.0 },
//   { step: 'add_to_cart',  step_order: 2, sessions: 3200,  conversion_pct: 32.0 },
//   { step: 'checkout',     step_order: 3, sessions: 1800,  conversion_pct: 56.3 },
//   { step: 'payment_done', step_order: 4, sessions: 1500,  conversion_pct: 83.3 },
// ]
```

### 怎麼讀這個資料？

```
page_view (10,000)  ──100%──→  所有人
     ↓ 32% 轉換
add_to_cart (3,200)  ────────→  3,200 / 10,000 = 32%
     ↓ 56.3% 轉換
checkout (1,800)     ────────→  1,800 / 3,200 = 56.3%
     ↓ 83.3% 轉換
payment_done (1,500) ────────→  1,500 / 1,800 = 83.3%

整體轉換率：1,500 / 10,000 = 15%
```

`conversion_pct` 是**步驟間轉換率**（相對於前一步），不是整體轉換率。
前端可以自己算整體轉換率：`sessions / data[0].sessions * 100`。

> ### 💡 為什麼要回傳 step_order？
>
> 前端的漏斗圖需要步驟順序，但 SQL 的 `ORDER BY` 可能不夠保險
>（如果步驟名改了，字母排序就亂了）。
> `step_order` 是明確的序號，保證前端永遠按正確順序排列。

---

## 4. `api_analytics_rag_quality` — RAG 品質趨勢

> **📖 SQL 第 607–630 行**

追蹤 RAG 系統的搜尋品質隨時間的變化。適合 RAG 運維人員。

### 參數

| 參數 | 型別 | 預設值 | 說明 |
|------|------|--------|------|
| `p_collection_code` | TEXT | NULL | 知識庫代碼（NULL = 全部） |
| `p_weeks_back` | INTEGER | 12 | 往回看幾週 |

### 回傳欄位

| 欄位 | 型別 | 說明 |
|------|------|------|
| `week_start` | DATE | 週起始日 |
| `query_count` | BIGINT | 該週查詢次數 |
| `avg_faithfulness` | FLOAT8 | 平均忠實度（LLM 有沒有亂說） |
| `avg_relevance` | FLOAT8 | 平均相關性（回傳的 chunk 是否相關） |
| `avg_context_recall` | FLOAT8 | 平均上下文召回率 |
| `avg_context_precision` | FLOAT8 | 平均上下文精確度 |
| `rated_count` | BIGINT | 使用者有評分的查詢數 |
| `avg_user_rating` | FLOAT8 | 使用者平均評分 |

### 前端呼叫

```ts
// 全部知識庫，過去 12 週
const { data } = await supabase.rpc('api_analytics_rag_quality')

// 特定知識庫
const { data } = await supabase.rpc('api_analytics_rag_quality', {
  p_collection_code: 'help-center',
  p_weeks_back: 24
})
```

### 品質指標說明

| 指標 | 衡量什麼 | 好的範圍 |
|------|----------|----------|
| **faithfulness** | LLM 的回答是否忠於 context？（沒有幻覺） | > 0.85 |
| **relevance** | 回傳的 chunk 跟問題有關嗎？ | > 0.80 |
| **context_recall** | 該找到的 chunk 都找到了嗎？ | > 0.75 |
| **context_precision** | 找到的 chunk 裡，有多少是真正有用的？ | > 0.80 |
| **user_rating** | 使用者主觀滿意度 | > 4.0 / 5.0 |

> ### 🧠 你的大腦在想…
>
> 「這些品質指標是怎麼算出來的？」
>
> 這通常需要一個 **evaluation pipeline**：
> 1. 使用者發問 → RAG 回答
> 2. 背景任務拿 (question, answer, context) 去跑 RAGAS 評估框架
> 3. 評估結果存進 `rag.evaluation_logs`
> 4. `analytics.rag_quality_trend()` 按週聚合
>
> 這個 API 只是把結果拿出來，不負責計算。

---

## 5. `api_analytics_freshness` — 資料新鮮度

> **📖 SQL 第 633–647 行**

監控各個 schema 的資料是否新鮮。如果某個 table 太久沒有新資料，可能代表 pipeline 壞了。

### 參數

無。

### 回傳欄位

| 欄位 | 型別 | 說明 |
|------|------|------|
| `schema_name` | TEXT | schema 名稱 |
| `entity` | TEXT | table / 實體名稱 |
| `latest_record_at` | TIMESTAMPTZ | 最新一筆資料的時間 |
| `minutes_ago` | NUMERIC | 距今幾分鐘 |
| `is_stale` | BOOLEAN | 是否過期（超過預設門檻） |

### 前端呼叫

```ts
const { data } = await supabase.rpc('api_analytics_freshness')

// data →
// [
//   { schema_name: 'shop', entity: 'orders',
//     latest_record_at: '2026-03-26T14:30:00Z',
//     minutes_ago: 15, is_stale: false },
//   { schema_name: 'crawler', entity: 'articles',
//     latest_record_at: '2026-03-26T08:00:00Z',
//     minutes_ago: 405, is_stale: true },     // ⚠️ 超過 6 小時沒新文章
//   { schema_name: 'rag', entity: 'chunks',
//     latest_record_at: '2026-03-25T22:00:00Z',
//     minutes_ago: 1005, is_stale: true },    // ⚠️ 超過 16 小時沒新 chunk
// ]
```

### 使用場景

```
✅ minutes_ago < 60    → 綠燈：資料新鮮
⚠️ minutes_ago < 360   → 黃燈：稍微落後
🚨 minutes_ago >= 360  → 紅燈：可能有問題

is_stale = true → 後台亮紅燈，通知 on-call
```

這個 API 適合放在管理後台的「系統健康」頁面，搭配自動告警。

> ### 💡 is_stale 的門檻在哪裡定義？
>
> 在 `analytics.data_freshness()` 裡面。不同的 entity 可能有不同的門檻：
> - `shop.orders`：1 小時沒新訂單可能正常（半夜）
> - `crawler.articles`：6 小時沒新文章就該告警
> - `rag.chunks`：24 小時沒新 chunk 可能是 embedding pipeline 掛了
>
> 門檻的設定需要根據你的業務節奏來調整。

---

## GRANT 總覽

```sql
-- Analytics：全部 authenticated-only
GRANT EXECUTE ON FUNCTION public.api_analytics_dashboard(INTEGER) TO authenticated;
GRANT EXECUTE ON FUNCTION public.api_analytics_revenue(TEXT, INTEGER) TO authenticated;
GRANT EXECUTE ON FUNCTION public.api_analytics_funnel(INTEGER) TO authenticated;
GRANT EXECUTE ON FUNCTION public.api_analytics_rag_quality(TEXT, INTEGER) TO authenticated;
GRANT EXECUTE ON FUNCTION public.api_analytics_freshness() TO authenticated;
```

Analytics API 全部限 authenticated。這些是**運營數據**，不對外公開。

如果你需要更細的權限控制（例如只有 admin 能看），可以在 function 內部加判斷：

```sql
-- 範例：只允許 admin 角色
IF NOT EXISTS (
  SELECT 1 FROM shop.users u
  WHERE u.auth_user_id = auth.uid() AND u.role = 'admin'
) THEN
  RAISE EXCEPTION 'Forbidden';
END IF;
```

但這需要把 `LANGUAGE SQL` 改成 `LANGUAGE plpgsql`，因為 `IF` 是 PL/pgSQL 語法。

---

## 延伸閱讀

**底層 schema 文件**（這些 API bridge 的目標函數定義在這裡）：

| 文件 | 涵蓋內容 |
|------|----------|
| [`005_analytics_schema.sql`](../migrations/005_analytics_schema.sql) | Analytics schema + 底層函數定義 |
| [studio/07_analytics-and-matview.md](../studio/07_analytics-and-matview.md) | Materialized View 與分析策略 |

> **注意**：本文中 `analytics.revenue_time_series()` 等底層函數的參數說明（如 granularity 的合法值 `hour/day/week/month`）是根據常見模式推斷。實際白名單請以 `005_analytics_schema.sql` 為準。

---

## 回到目錄

- [00_README.md](00_README.md)——全景地圖 + API 完整目錄
- [01_design-patterns.md](01_design-patterns.md)——設計模式

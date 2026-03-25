# Head First Materialized View + 漏斗追蹤 — Chapter 2

> **對應 SQL**：`migrations/005_analytics_schema.sql` 第 128–149 行（Funnel）、第 153–238 行（MATVIEW）
>
> **前置閱讀**：[Chapter 1 — Event Log + Daily Snapshots](01_event-bus-design.md)

## 搭配閱讀

| 你在讀的 | SQL 行號 | 學什麼 |
|----------|----------|--------|
| Part 1：mv_system_health | 160–183 | WITH NO DATA、UNIQUE INDEX、CONCURRENTLY |
| Part 1：mv_product_ranking | 185–205 | LEFT JOIN 時間條件放 ON、count(DISTINCT) |
| Part 1：mv_source_health | 207–234 | FILTER (WHERE ...)、::NUMERIC 轉型 |
| Part 2：funnel_events | 128–149 | 漏斗步驟 CHECK、partial index、安全模型分離 |

---

## Part 1：Materialized View — 預先計算的查詢快照

> **📖 SQL 第 153–238 行**

### 🤔 動腦時間

> 你的即時儀表板需要顯示「今日訂單數 + 今日營收 + 今日爬蟲失敗數 + RAG 平均分數」。
>
> 這個查詢要 JOIN 三個 schema 的表，每次載入 Dashboard 都跑一次。
>
> 問題：如果同時有 50 個人在看 Dashboard，資料庫會怎樣？

### 答案：每個人都觸發一次跨 schema 查詢，資料庫會被打爆

解法：**Materialized View**。

```
普通 VIEW：          每次 SELECT 都重新計算（虛擬表）
Materialized VIEW：  REFRESH 時計算一次，結果存在磁碟，SELECT 直接讀快取
```

| | VIEW | Materialized View |
|---|---|---|
| 儲存 | 不存資料，存查詢定義 | 存資料在磁碟上 |
| SELECT 速度 | 等同跑原始查詢 | 等同讀一張表 |
| 資料新鮮度 | 永遠最新 | REFRESH 時才更新 |
| 索引 | 不能建 index | 可以建 index |
| 適合場景 | 簡單查詢、即時性需求高 | 複雜聚合、可接受延遲 |

---

### 5a. 跨域健康總覽

> **📖 SQL 第 160–183 行**

```sql
CREATE MATERIALIZED VIEW IF NOT EXISTS analytics.mv_system_health AS
  SELECT
    NOW() AS snapshot_at,
    -- shop
    (SELECT count(*) FROM shop.orders
     WHERE created_at >= CURRENT_DATE) AS today_orders,
    (SELECT coalesce(sum(total), 0) FROM shop.orders
     WHERE created_at >= CURRENT_DATE AND status != 'cancelled') AS today_revenue,
    -- crawler
    (SELECT count(*) FROM crawler.crawl_runs
     WHERE created_at >= CURRENT_DATE) AS today_crawl_runs,
    (SELECT count(*) FROM crawler.crawl_runs
     WHERE created_at >= CURRENT_DATE AND run_status = 'failed') AS today_failed_runs,
    -- rag
    (SELECT count(*) FROM rag.query_logs
     WHERE created_at >= CURRENT_DATE) AS today_rag_queries,
    (SELECT avg(eval_faithfulness) FROM rag.query_logs
     WHERE created_at >= CURRENT_DATE
       AND eval_faithfulness IS NOT NULL) AS today_avg_faithfulness
WITH NO DATA;
```

### 🧠 你的大腦在想…

> 「`WITH NO DATA` 是什麼意思？不是要建快取嗎？」
>
> `WITH NO DATA` 表示「建立 MATVIEW 的結構，但不馬上跑查詢填資料」。
> 這樣 `CREATE` 瞬間完成，不用等跨 schema 查詢跑完。
>
> 但有個陷阱：**如果沒有先 REFRESH，SELECT 會報錯！**
>
> 所以 SQL 第 237 行馬上補了 `REFRESH MATERIALIZED VIEW analytics.mv_system_health;`

---

### UNIQUE INDEX — CONCURRENTLY 刷新的門票

> **📖 SQL 第 182–183 行**

```sql
CREATE UNIQUE INDEX IF NOT EXISTS uq_mv_system_health
  ON analytics.mv_system_health(snapshot_at);
```

### 🤔 動腦時間

> 為什麼 MATVIEW 需要 UNIQUE INDEX？它又不是 table，不需要 PK 吧？

### 答案：為了 `REFRESH MATERIALIZED VIEW CONCURRENTLY`

普通的 `REFRESH` 會這樣做：

```
1. 鎖住整個 MATVIEW（讀也不行）
2. 清空舊資料
3. 重新計算
4. 解鎖
```

在 REFRESH 期間，所有 SELECT 都被擋住。如果查詢要跑 3 秒，你的 Dashboard 就卡 3 秒。

`REFRESH ... CONCURRENTLY` 的做法不同：

```
1. 在背景重新計算
2. 比對新舊資料的差異（需要 UNIQUE INDEX 來比對）
3. 原子替換
4. 讀取完全不受影響
```

**代價**：CONCURRENTLY 比普通 REFRESH 慢 2-3 倍（要做 diff），但不鎖讀。

> **規矩**：任何會被 Dashboard 讀取的 MATVIEW，一律建 UNIQUE INDEX，一律用 CONCURRENTLY 刷新。

---

### 5b. 商品銷售排行（rolling 30 天）

> **📖 SQL 第 185–205 行**

```sql
CREATE MATERIALIZED VIEW IF NOT EXISTS analytics.mv_product_ranking AS
  SELECT
    p.id AS product_id,
    p.title,
    p.price,
    count(DISTINCT oi.order_id)    AS order_count,
    coalesce(sum(oi.quantity), 0)  AS total_sold,
    coalesce(sum(oi.net_revenue), 0) AS total_revenue,
    avg(r.rating)                  AS avg_rating,
    count(DISTINCT r.id)           AS review_count
  FROM shop.products p
  LEFT JOIN shop.order_items oi ON oi.product_id = p.id
    AND oi.created_at >= CURRENT_DATE - INTERVAL '30 days'
  LEFT JOIN shop.reviews r ON r.product_id = p.id AND r.is_visible = TRUE
  WHERE p.status = 'publish' AND p.deleted_at IS NULL
  GROUP BY p.id, p.title, p.price
WITH NO DATA;
```

**教學重點**：

1. **`LEFT JOIN` + 時間條件在 `ON` 裡**：為什麼不放在 `WHERE`？
   - 如果放 `WHERE oi.created_at >= ...`，沒有訂單的商品會被過濾掉
   - 放在 `ON` 裡，沒有訂單的商品仍然會出現（`total_sold = 0`）

2. **`count(DISTINCT oi.order_id)`**：一筆訂單買了同商品 3 件，算 1 個 order，不是 3

3. **`coalesce(sum(...), 0)`**：LEFT JOIN 沒匹配到的 row，SUM 會是 NULL。`coalesce` 把 NULL 轉成 0。

---

### 5c. Crawler 來源健康度

> **📖 SQL 第 207–233 行**

```sql
CREATE MATERIALIZED VIEW IF NOT EXISTS analytics.mv_source_health AS
  SELECT
    s.id AS source_id,
    s.name AS source_name,
    s.code AS source_code,
    count(cr.id) AS total_runs_30d,
    count(cr.id) FILTER (WHERE cr.run_status = 'success') AS success_runs,
    count(cr.id) FILTER (WHERE cr.run_status = 'failed')  AS failed_runs,
    coalesce(sum(cr.articles_extracted), 0) AS articles_30d,
    coalesce(sum(cr.error_count), 0) AS errors_30d,
    max(cr.finished_at) AS last_run_at,
    CASE
      WHEN count(cr.id) = 0 THEN 0
      ELSE round(
        count(cr.id) FILTER (WHERE cr.run_status = 'success')::NUMERIC
        / count(cr.id) * 100, 1
      )
    END AS success_rate_pct
  FROM crawler.sources s
  LEFT JOIN crawler.crawl_runs cr ON cr.source_id = s.id
    AND cr.created_at >= CURRENT_DATE - INTERVAL '30 days'
  WHERE s.is_enabled = TRUE
  GROUP BY s.id, s.name, s.code
WITH NO DATA;
```

### 新技巧：`FILTER (WHERE ...)`

這是 PostgreSQL 9.4+ 的語法，比 `CASE WHEN` 更乾淨：

```sql
-- 舊寫法（醜）
count(CASE WHEN cr.run_status = 'success' THEN 1 END) AS success_runs

-- 新寫法（美）
count(cr.id) FILTER (WHERE cr.run_status = 'success') AS success_runs
```

功能完全一樣，但 `FILTER` 的可讀性高很多。特別是當你有 5-6 個條件聚合時，差異更明顯。

### 成功率計算的防禦

```sql
CASE
  WHEN count(cr.id) = 0 THEN 0       -- 沒有任何 run → 0%（不是 NULL）
  ELSE round(
    count(cr.id) FILTER (WHERE cr.run_status = 'success')::NUMERIC
    / count(cr.id) * 100, 1           -- 注意 ::NUMERIC 轉型
  )
END AS success_rate_pct
```

**為什麼要 `::NUMERIC`？** 因為 `count()` 返回 `BIGINT`。`BIGINT / BIGINT` 是整數除法，`5 / 7 = 0`。轉成 `NUMERIC` 才能得到 `71.4`。

---

### 初始化 MATVIEW

> **📖 SQL 第 237–239 行**

```sql
REFRESH MATERIALIZED VIEW analytics.mv_system_health;
REFRESH MATERIALIZED VIEW analytics.mv_product_ranking;
REFRESH MATERIALIZED VIEW analytics.mv_source_health;
```

`WITH NO DATA` 建出來的 MATVIEW 是空殼。第一次必須用普通 REFRESH（不加 CONCURRENTLY），因為 CONCURRENTLY 需要「已經有資料」才能做 diff。

---

## Part 2：Funnel Events — 購買漏斗追蹤

> **📖 SQL 第 128–149 行**

### 🤔 動腦時間

> 你的電商有五個步驟：瀏覽商品 → 加入購物車 → 進入結帳 → 付款 → 完成。
>
> 你想知道：「有多少人走到了第三步？從第三步到第四步流失了多少？」
>
> 這些資料要存在哪裡？直接從 `shop.orders` 查得到嗎？

### 答案：查不到

`shop.orders` 只記錄「成功建立的訂單」。那些「看了商品但沒加入購物車」的人，orders 表裡根本沒有他們。

你需要一張專門的**漏斗事件表**，前端每一步都推送一筆 event：

```sql
CREATE TABLE IF NOT EXISTS analytics.funnel_events (
  id          TEXT PRIMARY KEY DEFAULT public.generate_ulid(),
  session_id  TEXT        NOT NULL,
  customer_id TEXT,                    -- 未登入就是 NULL
  step        TEXT        NOT NULL,
  step_order  SMALLINT    NOT NULL,
  product_id  TEXT,
  order_id    TEXT,
  metadata    JSONB       NOT NULL DEFAULT '{}'::JSONB,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  CONSTRAINT ck_funnel_step
    CHECK (step IN ('view', 'add_to_cart', 'checkout', 'payment', 'completed'))
);
```

### 設計解析

| 欄位 | 為什麼這樣設計 |
|------|--------------|
| `session_id` | 漏斗以 session 為單位。同一個人可以有多個 session |
| `customer_id` 可 NULL | 未登入的訪客也要追蹤。很多人在 `view` 步驟還沒登入 |
| `step_order SMALLINT` | 數字化步驟順序，方便 `ORDER BY` 和 window function |
| `CHECK (step IN (...))` | 這裡用硬編碼的 IN——漏斗步驟很少改變，而且錯誤的步驟名會造成分析混亂 |

### 🧠 你的大腦在想…

> 「等等，Chapter 1 的 `events` 表也能記事件。為什麼漏斗要獨立一張表？」
>
> 好問題。兩個原因：
>
> 1. **安全模型不同**：`events` 只有 service_role 能寫（後端推送）。
>    `funnel_events` 允許 authenticated 用戶寫入（前端推送）。混在一起會讓 RLS 很複雜。
>
> 2. **查詢模式不同**：漏斗分析的 WHERE 條件是 `session_id` + `step_order`，
>    而 events 的查詢模式是 `schema_name` + `event_type`。索引策略完全不同。

---

### Funnel Index 策略

> **📖 SQL 第 143–149 行**

```sql
-- 漏斗分析的主要查詢：按 session 排步驟
CREATE INDEX idx_funnel_session
  ON analytics.funnel_events(session_id, step_order);

-- 按顧客查（找 VIP 的購買路徑）
CREATE INDEX idx_funnel_customer
  ON analytics.funnel_events(customer_id)
  WHERE customer_id IS NOT NULL;

-- 按時間查（最近 7 天的漏斗）
CREATE INDEX idx_funnel_created
  ON analytics.funnel_events(created_at DESC);
```

又一個 partial index（`WHERE customer_id IS NOT NULL`）。未登入的訪客不需要被 customer 索引覆蓋。

---

## Part 1 + Part 2 合在一起看

現在你有了完整的資料收集層：

```
前端用戶行為                     後端系統事件
    │                               │
    ▼                               ▼
funnel_events                   events
(前端推送，authenticated 可寫)   (trigger 推送，service_role 寫)
    │                               │
    └───────────┬───────────────────┘
                │
    ┌───────────┼───────────────┐
    ▼           ▼               ▼
mv_*        daily_*_stats    functions
(即時快取)   (歷史趨勢)      (分析查詢)
```

---

### ❓ 沒有笨問題

**Q：MATVIEW 可以做 INSERT / UPDATE 嗎？**
A：不行。MATVIEW 是唯讀的。唯一更新它的方式是 `REFRESH MATERIALIZED VIEW`。它不是表，是「預先計算的快取」。

**Q：為什麼 `mv_system_health` 只有一行資料，卻需要 UNIQUE INDEX？**
A：因為 `REFRESH CONCURRENTLY` 的演算法需要 UNIQUE INDEX 來做 diff。即使只有一行，規則就是規則。沒有 UNIQUE INDEX，加 `CONCURRENTLY` 會直接報錯。

**Q：`funnel_events` 的 `step_order` 為什麼是 `SMALLINT` 不是 `INTEGER`？**
A：漏斗最多 5 步，`SMALLINT`（-32768 到 32767）綽綽有餘。省 2 bytes/row。在高流量的漏斗表裡，幾百萬 row 省下來的空間很可觀。

---

### 🛠️ 動手做

1. 執行 `005_analytics_schema.sql` 的第 160–239 行建立三個 MATVIEW
2. 嘗試不加 `CONCURRENTLY` 的 REFRESH：
   ```sql
   REFRESH MATERIALIZED VIEW analytics.mv_system_health;
   SELECT * FROM analytics.mv_system_health;
   ```
3. 再試加 `CONCURRENTLY`（需要 UNIQUE INDEX 已存在）：
   ```sql
   REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.mv_system_health;
   ```
4. 插入一筆漏斗事件，觀察 CHECK constraint：
   ```sql
   INSERT INTO analytics.funnel_events (session_id, step, step_order)
   VALUES ('sess_abc123', 'view', 1);

   -- 試試不合法的 step：
   INSERT INTO analytics.funnel_events (session_id, step, step_order)
   VALUES ('sess_abc123', 'browse', 1);  -- 會怎樣？
   ```

---

## 本章重點回顧

| 概念 | 學到什麼 |
|------|---------|
| VIEW vs MATVIEW | VIEW 每次重算；MATVIEW 存磁碟，REFRESH 才更新 |
| `WITH NO DATA` | 建結構不填資料，CREATE 瞬間完成 |
| UNIQUE INDEX on MATVIEW | `REFRESH CONCURRENTLY` 的必要條件，不鎖讀 |
| `FILTER (WHERE ...)` | 比 `CASE WHEN` 更乾淨的條件聚合 |
| `LEFT JOIN` 時間條件放 `ON` | 放 `WHERE` 會過濾掉沒匹配到的 row |
| `::NUMERIC` 轉型 | 整數除法 → 浮點除法的關鍵 |
| Funnel vs Events | 安全模型不同 + 查詢模式不同 = 獨立表 |
| Partial index | `WHERE ... IS NOT NULL` 讓索引更小 |

---

← [Chapter 1 — Event Log + Daily Snapshots](01_event-bus-design.md) | [Chapter 3 — 時間序列聚合](03_time-series-aggregation.md) →

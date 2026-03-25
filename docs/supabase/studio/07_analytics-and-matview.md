# Head First Analytics — 跨域觀測與 Materialized View

> ***「你不能改善你無法衡量的東西。但如果衡量的成本太高，你根本不會去量。」***

### 本章你會學到

| 主題 | 內容 |
|------|------|
| Event Log | append-only 事件匯流排設計、GIN index、regex CHECK |
| Daily Snapshots | UPSERT pattern（`ON CONFLICT DO UPDATE`）、歷史趨勢保存 |
| Materialized View | VIEW vs MATVIEW、`WITH NO DATA`、`REFRESH CONCURRENTLY` |
| SQL 分析函數 | `generate_series` 時間軸、`LAG` 漏斗、`FILTER` 條件聚合、Cohort Retention、Z-score |
| Cross-Schema Triggers | `SECURITY DEFINER` + `SET search_path` 的跨 schema 事件推送 |

**預計時間**：閱讀 30 分鐘 + 動手做 20 分鐘

---

> ### 你的大腦在想 🧠
>
> 「我有 shop、crawler、rag 三個 schema，老闆問『今天生意如何？』我要開三個 query tab，
> 各自跑一次，然後自己在腦子裡合併結果……有沒有更好的方式？」
>
> 有。建一個 **analytics schema**，讓它當你的跨域觀測層。
> 一個 function call，三個領域的數據一次到位。

---

## 前置要求

- 已完成 `03_sql-editor-mastery.md`（會用 SQL Editor、會寫 Function）
- 已**依序**執行以下 migration（順序很重要，後面的依賴前面的 schema 和表）：
  1. `../migrations/001_extensions.sql` — schema 建立 + `generate_ulid` function
  2. `../migrations/002_shop_schema.sql` — shop schema 完整表結構
  3. `../migrations/003_crawler_schema.sql` — crawler schema 完整表結構
  4. `../migrations/004_rag_schema.sql` — rag schema 完整表結構
- Docker 跑著（`supabase start`）
- 瀏覽器打開 Studio `http://localhost:54323`

> ⚠️ **migration 依賴警告**：`005_analytics_schema.sql` 的 MATVIEW 和 trigger
> 直接引用 `shop.orders`、`shop.products`、`shop.order_items`、`shop.reviews`、
> `crawler.crawl_runs`、`rag.query_logs` 等表。
> 如果你只做了 `02_schema-strategy.md` 的簡化版練習（只有基礎表），
> REFRESH MATVIEW 和建立 trigger 時會報 `relation does not exist` 錯誤。
> **請先跑完 001-004 的完整 migration。**

> 本章所有 SQL 來自 `../migrations/005_analytics_schema.sql`。
> 建議先執行完整 migration，再回來對照本章解說。

---

## Part 1: 為什麼需要 Analytics Schema

### 問題：三個王國，沒有外交官

你的系統有三個獨立的領域：

```
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   shop       │  │  crawler     │  │    rag       │
│  電商訂單     │  │  爬蟲排程     │  │  向量搜尋    │
│  商品庫存     │  │  文章抓取     │  │  LLM 查詢    │
└──────────────┘  └──────────────┘  └──────────────┘
       │                 │                 │
       │    各自為政、互不往來              │
       │                 │                 │
       ▼                 ▼                 ▼
   「今天賣了      「今天爬了        「今天查了
     多少？」       多少？」          多少？」
```

老闆問一句「今天狀況如何？」，你要：

1. `SELECT count(*) FROM shop.orders WHERE created_at >= CURRENT_DATE;`
2. `SELECT count(*) FROM crawler.crawl_runs WHERE created_at >= CURRENT_DATE;`
3. `SELECT avg(eval_faithfulness) FROM rag.query_logs WHERE created_at >= CURRENT_DATE;`

三條 query，三個 tab，然後自己做心算。**這不是工程，這是手工藝。**

### 解法：建一個跨域觀測層

```
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   shop       │  │  crawler     │  │    rag       │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                 │                 │
       │    trigger      │    trigger      │    trigger
       │                 │                 │
       ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────┐
│                 analytics schema                     │
│                                                      │
│  events        ← 統一事件匯流排（append-only log）   │
│  daily_*_stats ← 每日聚合快照（UPSERT pattern）      │
│  mv_*          ← Materialized View（即時儀表板）     │
│  functions     ← 分析函數（時間序列、漏斗、Z-score） │
└─────────────────────────────────────────────────────┘
```

**設計原則**：

- analytics **不存原始資料**，只存聚合、事件、快照
- Event log 是 **append-only**：永遠不 UPDATE / DELETE，只 INSERT
- Snapshot table 用 **UPSERT** 保留歷史
- Materialized View 用 **REFRESH CONCURRENTLY** 刷新，不鎖讀取

> ### 你的大腦在想 🧠
>
> 「append-only 不會一直長大嗎？」
>
> 會。但這就是 event log 的本質——它是你的**唯一真相來源**。
> 刪掉一筆 event 就等於竄改歷史紀錄。空間不夠？用 partition + 歸檔。
> 不要用 DELETE。

---

## Part 2: Event Log — 統一事件匯流排

### analytics.events 表結構

```sql
CREATE TABLE IF NOT EXISTS analytics.events (
  id            TEXT PRIMARY KEY DEFAULT public.generate_ulid(),
  schema_name   TEXT        NOT NULL,   -- 來源 schema：'shop', 'crawler', 'rag'
  event_type    TEXT        NOT NULL,   -- 事件類型：'order.created', 'crawl.completed'
  entity_type   TEXT        NOT NULL,   -- 實體類型：'order', 'crawl_run', 'query_log'
  entity_id     TEXT,                   -- 實體 ID（可選）
  actor_id      TEXT,                   -- 操作者 ID（可選）
  payload       JSONB       NOT NULL DEFAULT '{}'::JSONB,  -- 額外資料
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  -- 格式驗證：schema_name 只允許小寫英文 + 底線
  CONSTRAINT ck_events_schema
    CHECK (schema_name ~ '^[a-z_]+$'),
  -- event_type 格式為 entity.action（例如 order.created）
  CONSTRAINT ck_events_type
    CHECK (event_type ~ '^[a-z_]+\.[a-z_]+$')
);
```

### 關鍵設計解讀

**1. regex CHECK constraint**

為什麼用正則而不是 `IN ('shop', 'crawler', 'rag')`？

因為 `IN` 列表會隨著系統成長一直改。regex `'^[a-z_]+$'` 允許未來擴充新 schema，
不用每次改 migration。但它仍然防止亂寫（不能有大寫、空格、特殊符號）。

**2. GIN index on JSONB payload**

```sql
CREATE INDEX IF NOT EXISTS idx_events_payload
  ON analytics.events USING GIN(payload);
```

GIN（Generalized Inverted Index）讓你可以直接查 JSONB 內容：

```sql
-- 找所有 total > 1000 的訂單事件
SELECT * FROM analytics.events
WHERE payload @> '{"status": "confirmed"}'::JSONB;
```

**3. 複合索引 for 常見查詢**

```sql
-- 「某 schema + 某事件類型 + 最近時間」是最常見的查詢模式
CREATE INDEX IF NOT EXISTS idx_events_schema_type
  ON analytics.events(schema_name, event_type, created_at DESC);
```

### analytics.log_event() — 寫入介面

```sql
-- 通用事件寫入 function
SELECT analytics.log_event(
  'shop',              -- p_schema：來源 schema
  'order.created',     -- p_type：事件類型
  'order',             -- p_entity：實體類型
  'ord_01HX...',       -- p_entity_id：實體 ID
  'usr_01HX...',       -- p_actor_id：操作者
  '{"total": 1299, "status": "pending"}'::JSONB  -- p_payload
);
-- 回傳新建 event 的 id
```

這個 function 是 `SECURITY DEFINER`，意味著無論誰呼叫，都用定義者的權限執行。
這讓 trigger 可以跨 schema 寫入 analytics.events。

> ⚠️ **`SECURITY DEFINER` + `SET search_path` 安全須知**
>
> 你會注意到 trigger function 同時設定了 `SET search_path = analytics`。這不是裝飾：
>
> | 設定 | 為什麼需要 |
> |------|-----------|
> | `SECURITY DEFINER` | 讓 trigger 用 owner 權限執行，才能跨 schema 寫入 analytics |
> | `SET search_path` | **防止 search_path 注入攻擊**。如果不鎖定，攻擊者可以在 `public` 建一個同名的 `log_event` function，讓 trigger 執行惡意程式碼 |
>
> **最佳實踐**：每個 `SECURITY DEFINER` function 都應該搭配 `SET search_path`，
> 明確指定只搜尋需要的 schema。

> ### 腦筋急轉彎 🧠
>
> **Q：為什麼 event log 要 append-only？不能 UPDATE 嗎？**
>
> A：三個原因：
> 1. **審計追蹤**：你需要知道「什麼時候發生了什麼」。修改 event 就是竄改紀錄。
> 2. **效能**：INSERT-only 的表可以用 BRIN index、partition、WAL 優化。
>    UPDATE 會產生 dead tuple，需要 VACUUM。
> 3. **並發安全**：多個 trigger 同時寫入不會互相衝突（沒有 row lock 問題）。
>
> 如果需要「更正」，就再 INSERT 一筆 correction event。

---

## Part 3: Daily Snapshots — 每日聚合快照

### 為什麼不用 Materialized View 就好？

這是初學者最常問的問題。答案很簡單：

```
MATVIEW REFRESH = 整張砍掉重建
```

如果你的 MATVIEW 是「今天的統計」，REFRESH 之後昨天的數字就消失了。
你無法做趨勢分析（「上週比這週好嗎？」），因為歷史不見了。

```
Materialized View:
  ┌──────────┐  REFRESH  ┌──────────┐
  │ 3/24 資料 │ ───────→ │ 3/25 資料 │   ← 3/24 的數字不見了！
  └──────────┘           └──────────┘

Snapshot Table:
  ┌──────────┐  UPSERT   ┌──────────┐
  │ 3/24 資料 │           │ 3/24 資料 │   ← 還在！
  │          │  ───────→  │ 3/25 資料 │   ← 新增一行
  └──────────┘           └──────────┘
```

### 三張 Snapshot Table

migration 建立了三張每日快照表：

| 表名 | 追蹤什麼 | 關鍵欄位 |
|------|---------|---------|
| `daily_shop_stats` | 電商每日銷售 | total_orders, total_revenue, avg_order_value, new_customers |
| `daily_crawler_stats` | 爬蟲每日執行 | total_runs, successful_runs, failed_runs, pages_fetched |
| `daily_rag_stats` | RAG 每日品質 | total_queries, avg_faithfulness, total_prompt_tokens |

每張表都有 `CONSTRAINT uq_daily_*_date UNIQUE (stat_date)`，這是 UPSERT 的關鍵。

### UPSERT Pattern：ON CONFLICT DO UPDATE

```sql
-- build_daily_shop_stats(p_date) 的核心邏輯
INSERT INTO analytics.daily_shop_stats (
  stat_date, total_orders, total_revenue, avg_order_value, ...
)
SELECT
  p_date,
  count(*),
  coalesce(sum(total), 0),
  coalesce(avg(total), 0),
  ...
FROM shop.orders
WHERE created_at::DATE = p_date
  AND status NOT IN ('cancelled', 'refunded')
  AND deleted_at IS NULL
ON CONFLICT (stat_date) DO UPDATE SET         -- ← 關鍵！
  total_orders    = EXCLUDED.total_orders,    -- EXCLUDED = 新插入的值
  total_revenue   = EXCLUDED.total_revenue,
  avg_order_value = EXCLUDED.avg_order_value,
  created_at      = NOW();                    -- 更新時間戳
```

**UPSERT 的好處**：

- 第一次執行：INSERT 新行
- 第二次執行同一天：UPDATE 覆蓋（不會報錯、不會重複）
- **冪等（idempotent）**：執行幾次結果都一樣

> ### 你的大腦在想 🧠
>
> 「`EXCLUDED` 是什麼？」
>
> 在 `ON CONFLICT ... DO UPDATE` 語法中，`EXCLUDED` 代表**原本要 INSERT 的那筆資料**。
> 因為衝突了沒能 INSERT，但你仍然可以透過 `EXCLUDED` 取到那些值，用來 UPDATE。

---

## Part 4: Materialized View — 預算好的查詢快照

### VIEW vs MATVIEW：一張圖搞懂

```
普通 VIEW（虛擬表）：
  SELECT * FROM my_view;
  ───→ 每次都重新計算 ───→ 結果（即時但慢）

Materialized View（實體化視圖）：
  REFRESH MATERIALIZED VIEW my_matview;
  ───→ 計算一次，存到磁碟 ───→ 快照

  SELECT * FROM my_matview;
  ───→ 直接讀磁碟快照 ───→ 結果（快，但可能不是最新）
```

**比喻**：VIEW 像每次點餐現做的餐廳；MATVIEW 像便當店，早上做好放著，客人來直接拿。

### mv_system_health：跨域健康總覽

```sql
CREATE MATERIALIZED VIEW IF NOT EXISTS analytics.mv_system_health AS
  SELECT
    NOW() AS snapshot_at,
    -- shop 子查詢
    (SELECT count(*) FROM shop.orders
     WHERE created_at >= CURRENT_DATE) AS today_orders,
    (SELECT coalesce(sum(total), 0) FROM shop.orders
     WHERE created_at >= CURRENT_DATE AND status != 'cancelled') AS today_revenue,
    -- crawler 子查詢
    (SELECT count(*) FROM crawler.crawl_runs
     WHERE created_at >= CURRENT_DATE) AS today_crawl_runs,
    (SELECT count(*) FROM crawler.crawl_runs
     WHERE created_at >= CURRENT_DATE AND run_status = 'failed') AS today_failed_runs,
    -- rag 子查詢
    (SELECT count(*) FROM rag.query_logs
     WHERE created_at >= CURRENT_DATE) AS today_rag_queries,
    (SELECT avg(eval_faithfulness) FROM rag.query_logs
     WHERE created_at >= CURRENT_DATE
       AND eval_faithfulness IS NOT NULL) AS today_avg_faithfulness
WITH NO DATA;    -- ← 建立時不填資料，等手動 REFRESH
```

**設計重點**：用子查詢（subquery）而不是 JOIN，因為三個 schema 之間沒有共同的 key 可以 JOIN。

### mv_product_ranking：商品銷售排行

```sql
CREATE MATERIALIZED VIEW IF NOT EXISTS analytics.mv_product_ranking AS
  SELECT
    p.id AS product_id,
    p.title,
    p.price,
    count(DISTINCT oi.order_id) AS order_count,
    coalesce(sum(oi.quantity), 0) AS total_sold,
    coalesce(sum(oi.net_revenue), 0) AS total_revenue,
    avg(r.rating) AS avg_rating,
    count(DISTINCT r.id) AS review_count
  FROM shop.products p
  LEFT JOIN shop.order_items oi ON oi.product_id = p.id
    AND oi.created_at >= CURRENT_DATE - INTERVAL '30 days'   -- Rolling 30 天
  LEFT JOIN shop.reviews r ON r.product_id = p.id AND r.is_visible = TRUE
  WHERE p.status = 'publish' AND p.deleted_at IS NULL
  GROUP BY p.id, p.title, p.price
WITH NO DATA;
```

**設計重點**：LEFT JOIN 確保沒有訂單的商品也會出現（排行值為 0）。

### mv_source_health：爬蟲來源健康度

```sql
-- 核心計算：成功率 = 成功次數 / 總次數 * 100
CASE
  WHEN count(cr.id) = 0 THEN 0
  ELSE round(
    count(cr.id) FILTER (WHERE cr.run_status = 'success')::NUMERIC
    / count(cr.id) * 100, 1
  )
END AS success_rate_pct
```

注意 `FILTER` clause 的用法——這是 PostgreSQL 的條件聚合語法，
比用 `CASE WHEN ... THEN 1 ELSE 0 END` 乾淨得多。

### WITH NO DATA + UNIQUE INDEX = REFRESH CONCURRENTLY

```sql
-- 1. 建立時不填資料
CREATE MATERIALIZED VIEW ... WITH NO DATA;

-- 2. 建立 UNIQUE INDEX（REFRESH CONCURRENTLY 的必要條件）
CREATE UNIQUE INDEX IF NOT EXISTS uq_mv_system_health
  ON analytics.mv_system_health(snapshot_at);

-- 3. 初次填入資料（必須先做這步，否則 SELECT 會報錯）
REFRESH MATERIALIZED VIEW analytics.mv_system_health;

-- 4. 後續刷新用 CONCURRENTLY（不鎖讀取）
REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.mv_system_health;
```

> ### 設計陷阱 ⚠️：`snapshot_at` 當 UNIQUE INDEX 的問題
>
> `mv_system_health` 用 `NOW() AS snapshot_at` 當唯一欄位。
> 但每次 REFRESH 時 `NOW()` 會產生新值，這表示：
>
> - MATVIEW 永遠只有**一行**（因為整個 view 就是一筆 summary）
> - `CONCURRENTLY` 做 diff 時，舊行的 `snapshot_at` ≠ 新行的 `snapshot_at`，
>   所以 PostgreSQL 會「刪舊 + 插新」而不是「更新」，跟普通 REFRESH 效果一樣
>
> **這是一個合理的取捨**：mv_system_health 只有一行，REFRESH 成本極低（<1ms），
> 用 `CONCURRENTLY` 純粹是為了**不鎖讀取**。但如果你的 MATVIEW 有多行資料
> （如 `mv_product_ranking`），UNIQUE INDEX 就必須選一個**穩定不變的欄位**
> （如 `product_id`），CONCURRENTLY 才能真正做差異更新。

> ### 腦筋急轉彎 🧠
>
> **Q：為什麼 REFRESH CONCURRENTLY 需要 UNIQUE INDEX？**
>
> A：因為 `CONCURRENTLY` 的工作原理是：
> 1. 在背景計算新版本的資料
> 2. 比對新舊版本，找出差異（diff）
> 3. 只更新有變化的行
>
> 要「比對」就需要一個唯一識別欄位。沒有 UNIQUE INDEX，
> PostgreSQL 不知道怎麼把新行對應到舊行。
>
> 普通 `REFRESH`（不加 CONCURRENTLY）則是直接砍掉重建，不需要比對。
> 但它會**鎖住整個 MATVIEW**，刷新期間所有 SELECT 都得等。

### MATVIEW 效能與空間須知

MATVIEW 不是免費的午餐——它用**磁碟空間換查詢速度**：

| 注意事項 | 說明 |
|---------|------|
| **佔磁碟空間** | MATVIEW 是一份完整的資料副本。`mv_product_ranking` 有 1 萬筆商品 = 磁碟上多一份 1 萬行的表 |
| **REFRESH 成本** | 資料量越大，REFRESH 越慢。`CONCURRENTLY` 比普通 REFRESH 慢約 2 倍（因為要 diff），但不鎖讀取 |
| **離峰排程** | 生產環境應用 `pg_cron` 在離峰時段刷新（下一章會教），不要讓使用者等 |
| **不會自動更新** | 跟普通 VIEW 不同，MATVIEW **不會隨底層資料自動更新**。你不 REFRESH 它就永遠是舊的 |
| **查看大小** | `SELECT pg_size_pretty(pg_total_relation_size('analytics.mv_product_ranking'));` |

```sql
-- 查看所有 MATVIEW 的大小和最後刷新時間
SELECT
  schemaname || '.' || matviewname AS matview,
  pg_size_pretty(pg_total_relation_size(schemaname || '.' || matviewname)) AS size,
  ispopulated AS has_data  -- false = WITH NO DATA 尚未 REFRESH
FROM pg_matviews
WHERE schemaname = 'analytics';
```

---

## Part 5: SQL 分析函數大全

### generate_series + date_trunc：完整時間軸

為什麼需要 `generate_series`？因為如果某天沒有訂單，`GROUP BY` 不會產生那天的行。
圖表上會出現**斷點**。`generate_series` 產生完整的時間軸，再 LEFT JOIN 實際資料。

```sql
-- revenue_time_series() 的核心模式
WITH series AS (
  -- 產生連續的時間桶（例如 30 天）
  SELECT generate_series(
    date_trunc('day', NOW() - INTERVAL '30 days'),
    date_trunc('day', NOW()),
    '1 day'::INTERVAL
  ) AS bucket
),
agg AS (
  -- 實際資料的聚合
  SELECT
    date_trunc('day', created_at) AS bucket,
    count(*)   AS order_count,
    sum(total) AS total_revenue
  FROM shop.orders
  WHERE status NOT IN ('cancelled', 'refunded')
    AND created_at >= NOW() - INTERVAL '30 days'
  GROUP BY 1
)
-- LEFT JOIN 確保沒資料的日期也出現（值為 0）
SELECT
  s.bucket,
  coalesce(a.order_count, 0),
  coalesce(a.total_revenue, 0)
FROM series s
LEFT JOIN agg a ON a.bucket = s.bucket
ORDER BY s.bucket;
```

### LAG() Window Function：漏斗流失率

`LAG()` 取得「上一行」的值，用來計算相鄰步驟之間的變化。

```sql
-- funnel_dropoff() 的核心模式
SELECT
  step,
  step_order,
  sessions,
  -- LAG 取得前一步的 session 數
  lag(sessions) OVER (ORDER BY step_order) AS prev_sessions,
  -- 流失率 = (1 - 當前/前一步) * 100
  CASE
    WHEN lag(sessions) OVER (ORDER BY step_order) IS NULL THEN 0
    WHEN lag(sessions) OVER (ORDER BY step_order) = 0 THEN 0
    ELSE round(
      (1 - sessions::NUMERIC / lag(sessions) OVER (ORDER BY step_order)) * 100,
      2
    )
  END AS dropoff_pct
FROM step_counts
ORDER BY step_order;
```

### FILTER Clause：條件聚合

`FILTER` 是 PostgreSQL 的進階聚合語法，比 `CASE WHEN` 更清晰：

```sql
-- 傳統寫法（冗長）
count(CASE WHEN run_status = 'success' THEN 1 END) AS success_runs,
count(CASE WHEN run_status = 'failed'  THEN 1 END) AS failed_runs

-- FILTER 寫法（清爽）
count(*) FILTER (WHERE run_status = 'success') AS success_runs,
count(*) FILTER (WHERE run_status = 'failed')  AS failed_runs
```

`FILTER` 可以用在所有聚合函數：`count`, `sum`, `avg`, `min`, `max`。

### Cohort Retention：世代留存分析

```sql
-- monthly_cohort_retention() 的 CTE 鏈
WITH first_order AS (
  -- Step 1: 每位顧客的首次下單月份 = 他的 cohort
  SELECT
    customer_id,
    date_trunc('month', min(created_at))::DATE AS cohort_month
  FROM shop.orders
  WHERE deleted_at IS NULL
  GROUP BY customer_id
),
activity AS (
  -- Step 2: 每位顧客每月是否有活動
  SELECT DISTINCT
    o.customer_id,
    fo.cohort_month,
    date_trunc('month', o.created_at)::DATE AS activity_month
  FROM shop.orders o
  JOIN first_order fo ON fo.customer_id = o.customer_id
  WHERE o.deleted_at IS NULL
),
cohort_size AS (
  -- Step 3: 每個 cohort 的人數
  SELECT cohort_month, count(DISTINCT customer_id) AS size
  FROM first_order
  GROUP BY cohort_month
),
retention AS (
  -- Step 4: 每個 cohort × 每個月份的活躍人數
  SELECT
    a.cohort_month,
    -- 月份差距：activity_month 距離 cohort_month 幾個月
    (EXTRACT(YEAR FROM a.activity_month) - EXTRACT(YEAR FROM a.cohort_month)) * 12
      + (EXTRACT(MONTH FROM a.activity_month) - EXTRACT(MONTH FROM a.cohort_month))
      AS months_since,
    count(DISTINCT a.customer_id) AS active_users
  FROM activity a
  GROUP BY a.cohort_month, months_since
)
-- Step 5: 合併計算留存率
SELECT
  r.cohort_month,
  r.months_since,
  cs.size AS cohort_size,
  r.active_users,
  round(r.active_users::NUMERIC / nullif(cs.size, 0) * 100, 2) AS retention_pct
FROM retention r
JOIN cohort_size cs ON cs.cohort_month = r.cohort_month
ORDER BY r.cohort_month, r.months_since;
```

**讀法**：「2024-01 的 cohort 有 100 人，3 個月後還有 45 人活躍 = 45% 留存率」

### Z-score 異常偵測

```sql
-- detect_anomalies() 的核心邏輯
WITH daily AS (
  -- 每天的事件數
  SELECT created_at::DATE AS day, count(*) AS event_count
  FROM analytics.events
  WHERE schema_name = 'shop' AND event_type = 'order.created'
  GROUP BY 1
),
stats AS (
  -- 計算平均值和標準差
  SELECT avg(event_count) AS mean_count, stddev(event_count) AS stddev_count
  FROM daily
)
SELECT
  d.day,
  d.event_count,
  -- Z-score = (觀測值 - 平均值) / 標準差
  CASE WHEN s.stddev_count = 0 THEN 0
       ELSE (d.event_count - s.mean_count) / s.stddev_count
  END AS z_score,
  -- |Z| > 2.0 = 異常（95% 信賴區間外）
  CASE WHEN s.stddev_count = 0 THEN FALSE
       ELSE abs((d.event_count - s.mean_count) / s.stddev_count) > 2.0
  END AS is_anomaly
FROM daily d CROSS JOIN stats s;
```

**白話解釋**：Z-score 告訴你「這個值離平均有多少個標準差」。
Z-score = 2.5 代表比平均高出 2.5 個標準差，大概只有 1% 的日子會出現這種數字。

---

## Part 6: Funnel 漏斗分析

### 漏斗的五個步驟

```
view → add_to_cart → checkout → payment → completed
 瀏覽      加購物車       結帳       付款       完成

1000       450          280        250        230
  100%      45%         28%        25%        23%
                ↘ 55% 流失  ↘ 38% 流失
```

### funnel_events 表

```sql
CREATE TABLE IF NOT EXISTS analytics.funnel_events (
  id          TEXT PRIMARY KEY DEFAULT public.generate_ulid(),
  session_id  TEXT        NOT NULL,   -- 同一個 session 的事件串在一起
  customer_id TEXT,                   -- 已登入的用戶
  step        TEXT        NOT NULL,   -- 漏斗步驟
  step_order  SMALLINT    NOT NULL,   -- 步驟順序（1-5）
  product_id  TEXT,
  order_id    TEXT,
  metadata    JSONB       NOT NULL DEFAULT '{}'::JSONB,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  CONSTRAINT ck_funnel_step
    CHECK (step IN ('view', 'add_to_cart', 'checkout', 'payment', 'completed'))
);
```

### 轉換率計算：funnel_conversion()

```sql
-- 概念：每步的 session 數 / 第一步的 session 數 * 100
SELECT analytics.funnel_conversion(7);

--  step         | step_order | sessions | conversion_pct
-- --------------+------------+----------+---------------
--  view         |          1 |     1000 |        100.00
--  add_to_cart  |          2 |      450 |         45.00
--  checkout     |          3 |      280 |         28.00
--  payment      |          4 |      250 |         25.00
--  completed    |          5 |      230 |         23.00
```

### 逐步流失率：funnel_dropoff()

```sql
-- 概念：用 LAG() 取前一步的值，計算 (1 - 當前/前一步) * 100
SELECT analytics.funnel_dropoff(7);

--  step         | step_order | sessions | prev_sessions | dropoff_pct
-- --------------+------------+----------+---------------+------------
--  view         |          1 |     1000 |        (null) |        0.00
--  add_to_cart  |          2 |      450 |          1000 |       55.00
--  checkout     |          3 |      280 |           450 |       37.78
--  payment      |          4 |      250 |           280 |       10.71
--  completed    |          5 |      230 |           250 |        8.00
```

看到了嗎？最大的流失在「瀏覽 → 加購物車」（55%）。這就是你該優先改善的地方。

---

## Part 7: Cross-Schema Triggers — 事件驅動分析

### 設計原則：不要輪詢，要推送

```
❌ 錯誤做法：Analytics 每 5 分鐘去 shop.orders 掃一次新訂單
   → 浪費資源、有延遲、漏單

✅ 正確做法：shop.orders 有新訂單 → trigger 主動推送到 analytics.events
   → 即時、不漏、不浪費
```

### 三個 Cross-Schema Trigger

**1. Shop 訂單 → analytics.events**

```sql
CREATE OR REPLACE FUNCTION analytics.trg_shop_order_event()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER          -- ← 用 function owner 的權限，才能寫到 analytics schema
SET search_path = analytics
AS $$
BEGIN
  IF TG_OP = 'INSERT' THEN
    -- 新訂單 → log order.created
    PERFORM analytics.log_event(
      'shop', 'order.created', 'order', NEW.id, NEW.customer_id,
      jsonb_build_object('total', NEW.total, 'status', NEW.status)
    );
  ELSIF TG_OP = 'UPDATE' AND OLD.status IS DISTINCT FROM NEW.status THEN
    -- 狀態變更 → log 對應事件
    PERFORM analytics.log_event(
      'shop',
      CASE NEW.status
        WHEN 'confirmed' THEN 'order.paid'
        WHEN 'shipped'   THEN 'order.shipped'
        WHEN 'cancelled' THEN 'order.cancelled'
        ELSE 'order.created'
      END,
      'order', NEW.id, NEW.customer_id,
      jsonb_build_object('old_status', OLD.status, 'new_status', NEW.status, 'total', NEW.total)
    );
  END IF;
  RETURN NEW;
END;
$$;

-- 綁定到 shop.orders：INSERT 或 status 欄位 UPDATE 時觸發
CREATE TRIGGER trg_order_analytics
  AFTER INSERT OR UPDATE OF status ON shop.orders
  FOR EACH ROW EXECUTE FUNCTION analytics.trg_shop_order_event();
```

**2. Crawler 執行完成 → analytics.events**

```sql
-- 只在 run_status 從非終態變成終態時觸發
CREATE TRIGGER trg_crawl_run_analytics
  AFTER UPDATE OF run_status ON crawler.crawl_runs
  FOR EACH ROW EXECUTE FUNCTION analytics.trg_crawler_run_event();
```

**3. RAG 查詢 → analytics.events**

```sql
-- 每次新查詢都記錄
CREATE TRIGGER trg_rag_query_analytics
  AFTER INSERT ON rag.query_logs
  FOR EACH ROW EXECUTE FUNCTION analytics.trg_rag_query_event();
```

### Trigger Pattern 總結

```
┌─────────────────┐          ┌──────────────────────────┐
│  shop.orders    │─ INSERT ─→│ trg_shop_order_event()  │
│                 │─ UPDATE ─→│   → analytics.log_event │
├─────────────────┤          ├──────────────────────────┤
│ crawler.        │          │ trg_crawler_run_event() │
│   crawl_runs    │─ UPDATE ─→│   → analytics.log_event │
├─────────────────┤          ├──────────────────────────┤
│ rag.query_logs  │─ INSERT ─→│ trg_rag_query_event()  │
│                 │          │   → analytics.log_event  │
└─────────────────┘          └──────────────────────────┘
                                      │
                                      ▼
                             analytics.events
                             （統一事件匯流排）
```

---

## Part 8: 動手做 — 在 Studio 驗證

### Step 1：執行 Migration

打開 SQL Editor，執行完整的 `005_analytics_schema.sql`。

### Step 2：確認表和 MATVIEW 已建立

```sql
-- 列出 analytics schema 的所有物件
SELECT
  schemaname,
  tablename AS name,
  'table' AS type
FROM pg_tables
WHERE schemaname = 'analytics'
UNION ALL
SELECT
  schemaname,
  matviewname,
  'matview'
FROM pg_matviews
WHERE schemaname = 'analytics'
ORDER BY type, name;
```

你應該看到：

| name | type |
|------|------|
| events | table |
| daily_shop_stats | table |
| daily_crawler_stats | table |
| daily_rag_stats | table |
| funnel_events | table |
| mv_system_health | matview |
| mv_product_ranking | matview |
| mv_source_health | matview |

### Step 3：手動寫入一筆 event 並驗證

```sql
-- 手動寫入
SELECT analytics.log_event(
  'shop', 'order.created', 'order', 'test_001', NULL,
  '{"total": 599, "items": 3}'::JSONB
);

-- 驗證
SELECT * FROM analytics.events ORDER BY created_at DESC LIMIT 5;
```

### Step 4：手動刷新 MATVIEW

```sql
-- 方法 1：逐一刷新
REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.mv_system_health;
REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.mv_product_ranking;
REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.mv_source_health;

-- 方法 2：用 refresh_all() 一鍵刷新（同時產生快照）
SELECT analytics.refresh_all();
```

### Step 4.5：砍掉重練 MATVIEW

MATVIEW 不是表，不能用 `DROP TABLE`：

```sql
-- ❌ 這會報錯
DROP TABLE analytics.mv_system_health;
-- ERROR: "mv_system_health" is not a table

-- ✅ 正確做法
DROP MATERIALIZED VIEW analytics.mv_system_health;

-- 如果有其他物件依賴（例如 index），加 CASCADE
DROP MATERIALIZED VIEW analytics.mv_system_health CASCADE;

-- 重建：重新執行 CREATE MATERIALIZED VIEW ... + CREATE UNIQUE INDEX ...
-- 然後 REFRESH 填入資料
```

> **提示**：如果你用 `DROP SCHEMA analytics CASCADE` 重建整個 schema，
> MATVIEW 會跟著一起被刪掉（因為它存在於 analytics schema 下）。

### Step 5：查看系統儀表板

```sql
-- 跨域健康總覽
SELECT * FROM analytics.mv_system_health;

-- 全域儀表板（含趨勢比較）
SELECT * FROM analytics.system_dashboard(1);
```

### Step 6：查看資料新鮮度

```sql
-- 每個 schema 的最新資料時間
SELECT * FROM analytics.data_freshness();

-- schema_name | entity     | latest_record_at        | minutes_ago | is_stale
-- ------------+------------+-------------------------+-------------+---------
-- shop        | orders     | 2026-03-25 14:30:00+08  |        12.5 | false
-- crawler     | crawl_runs | 2026-03-25 08:00:00+08  |       402.5 | true   ← 超過 6 小時
-- rag         | documents  | 2026-03-24 20:00:00+08  |      1122.5 | true
```

`is_stale = true` 代表該資料源太久沒有新紀錄，可能需要檢查。

### Step 7：插入 Funnel 測試資料並驗證

Part 6 講了漏斗分析，但你需要先有測試資料才能呼叫 `funnel_conversion()` 和 `funnel_dropoff()`：

```sql
-- 模擬 3 個 session 的漏斗行為
INSERT INTO analytics.funnel_events (session_id, customer_id, step, step_order, product_id) VALUES
  -- Session A：完成購買
  ('sess_A', 'cust_01', 'view',        1, 'prod_01'),
  ('sess_A', 'cust_01', 'add_to_cart', 2, 'prod_01'),
  ('sess_A', 'cust_01', 'checkout',    3, NULL),
  ('sess_A', 'cust_01', 'payment',     4, NULL),
  ('sess_A', 'cust_01', 'completed',   5, NULL),
  -- Session B：加了購物車就離開
  ('sess_B', 'cust_02', 'view',        1, 'prod_02'),
  ('sess_B', 'cust_02', 'add_to_cart', 2, 'prod_02'),
  -- Session C：只瀏覽
  ('sess_C', NULL,       'view',        1, 'prod_03');

-- 驗證漏斗轉換率（過去 30 天）
SELECT * FROM analytics.funnel_conversion(30);
-- 預期：view=3, add_to_cart=2, checkout=1, payment=1, completed=1

-- 驗證逐步流失率
SELECT * FROM analytics.funnel_dropoff(30);
-- 預期：view→add_to_cart 流失 33.33%，add_to_cart→checkout 流失 50%
```

### 📝 驗證清單

```
□ analytics schema 存在，包含 5 張表 + 3 個 MATVIEW
□ analytics.log_event() 可以寫入事件
□ events 表的 CHECK constraint 有效（試試寫入不合規的 schema_name）
□ MATVIEW 可以 REFRESH CONCURRENTLY
□ system_dashboard() 回傳六個領域的指標
□ data_freshness() 回傳各 schema 的新鮮度
□ Trigger 有效：INSERT 一筆 shop.orders，analytics.events 自動多一筆
□ funnel_conversion() 和 funnel_dropoff() 回傳正確的漏斗數據
□ DROP MATERIALIZED VIEW 可以刪除 MATVIEW（不是 DROP TABLE）
```

---

## 搭配檔案

| 檔案 | 用途 |
|------|------|
| `../migrations/001_extensions.sql` | 前置：schema 建立 + `generate_ulid` |
| `../migrations/002_shop_schema.sql` | 前置：shop schema 完整表結構 |
| `../migrations/003_crawler_schema.sql` | 前置：crawler schema 完整表結構 |
| `../migrations/004_rag_schema.sql` | 前置：rag schema 完整表結構 |
| `../migrations/005_analytics_schema.sql` | **本章的程式碼來源**（完整 SQL） |
| `03_sql-editor-mastery.md` | SQL Editor 操作（前置技能） |
| `02_schema-strategy.md` | Schema 分區策略（前置觀念） |
| `08_cron-webhook-vault.md` | 排程刷新 MATVIEW（下一章） |

---

## 自我檢查清單

讀完本章，你應該能回答以下問題：

- [ ] **MATVIEW vs VIEW 的差別**：VIEW 每次 SELECT 重新計算；MATVIEW 存在磁碟，需要手動 REFRESH
- [ ] **REFRESH CONCURRENTLY 為什麼需要 UNIQUE INDEX**：因為它需要比對新舊版本的差異，UNIQUE INDEX 是比對的依據
- [ ] **Snapshot table vs MATVIEW 的使用時機**：需要保留歷史趨勢用 snapshot；只需要「最新狀態」用 MATVIEW
- [ ] **UPSERT pattern (ON CONFLICT DO UPDATE)**：INSERT 遇到衝突時改成 UPDATE，保證冪等性
- [ ] **generate_series 時間序列**：產生連續日期，LEFT JOIN 避免圖表斷點
- [ ] **LAG window function**：取得前一行的值，用於計算逐步變化率
- [ ] **FILTER clause**：條件聚合語法，比 CASE WHEN 更清晰
- [ ] **Cross-schema trigger pattern**：SECURITY DEFINER 讓 trigger 可以跨 schema 寫入
- [ ] **Z-score anomaly detection**：Z = (觀測值 - 平均) / 標準差，|Z| > 2 為異常

---

## 下一步

→ `08_cron-webhook-vault.md`：用 pg_cron 排程自動刷新 MATVIEW、Webhook 通知、Vault 密鑰管理

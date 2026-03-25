# Head First 時間序列聚合 — Chapter 3

> **對應 SQL**：`migrations/005_analytics_schema.sql` 第 242–374 行
>
> **前置閱讀**：[Chapter 2 — Materialized View + 漏斗追蹤](02_matview-and-funnel.md)

## 搭配閱讀

| 你在讀的 | SQL 行號 | 學什麼 |
|----------|----------|--------|
| Part 1：log_event | 247–263 | LANGUAGE SQL、SECURITY DEFINER、RETURNING |
| Part 1：count_events | 266–284 | STABLE 標記、時間範圍查詢 |
| Part 2：event_time_series | 293–329 | generate_series、date_trunc、動態粒度 |
| Part 2：revenue_time_series | 332–374 | 跨 schema 查詢、多指標聚合 |

---

## 你在學什麼？

這一章教你兩件事：

1. **Event Helpers**：通用的事件寫入和計數函數
2. **Time-Series Aggregation**：用 `generate_series` + `date_trunc` 產生完整時間軸

這是整個 analytics schema 裡**最實用的 SQL 技巧**。學會之後，你可以拿去做任何領域的時間序列分析。

---

## Part 1：Event Helper Functions

> **📖 SQL 第 242–284 行**

### 6a. 通用事件寫入

```sql
CREATE OR REPLACE FUNCTION analytics.log_event(
  p_schema    TEXT,
  p_type      TEXT,
  p_entity    TEXT,
  p_entity_id TEXT DEFAULT NULL,
  p_actor_id  TEXT DEFAULT NULL,
  p_payload   JSONB DEFAULT '{}'::JSONB
)
RETURNS TEXT
LANGUAGE SQL
SECURITY DEFINER
SET search_path = analytics
AS $$
  INSERT INTO analytics.events
    (schema_name, event_type, entity_type, entity_id, actor_id, payload)
  VALUES (p_schema, p_type, p_entity, p_entity_id, p_actor_id, p_payload)
  RETURNING id;
$$;
```

### 🤔 動腦時間

> 為什麼這個 function 用 `LANGUAGE SQL` 而不是 `LANGUAGE plpgsql`？

### 答案：因為它只有一個 INSERT 語句

| | `LANGUAGE SQL` | `LANGUAGE plpgsql` |
|---|---|---|
| 適合 | 單一或少數 SQL 語句 | 需要變數、IF/ELSE、LOOP |
| 執行 | 可被 inline 進呼叫者的查詢計劃 | 每次獨立執行 |
| 效能 | 通常更快（optimizer 可以看穿） | 有 overhead |
| 可讀性 | 純 SQL，簡潔 | 像寫程式語言 |

**規矩**：能用 `LANGUAGE SQL` 就用。只有需要變數、流程控制時才升級到 `plpgsql`。

### SECURITY DEFINER + SET search_path

```sql
SECURITY DEFINER           -- 用 function owner 的權限執行（不是呼叫者的）
SET search_path = analytics -- 鎖定 search_path，防止 schema 注入
```

為什麼需要 `SECURITY DEFINER`？因為 trigger function 會從 `shop` schema 呼叫這個函數，寫入 `analytics.events`。如果用 `SECURITY INVOKER`（預設），trigger 的權限是觸發它的用戶——authenticated 用戶沒有寫入 `analytics.events` 的權限。

> **安全鐵律**：所有 `SECURITY DEFINER` function 必須加 `SET search_path`。
> 否則攻擊者可以操控 `search_path`，讓你的函數存取到意想不到的表。

---

### 6b. 事件計數

```sql
CREATE OR REPLACE FUNCTION analytics.count_events(
  p_schema     TEXT,
  p_event_type TEXT,
  p_since      TIMESTAMPTZ DEFAULT CURRENT_DATE::TIMESTAMPTZ,
  p_until      TIMESTAMPTZ DEFAULT NOW()
)
RETURNS BIGINT
LANGUAGE SQL
STABLE
SECURITY DEFINER
SET search_path = analytics
AS $$
  SELECT count(*)
  FROM analytics.events
  WHERE schema_name = p_schema
    AND event_type  = p_event_type
    AND created_at >= p_since
    AND created_at <  p_until;
$$;
```

### 新概念：`STABLE`

```sql
STABLE    -- 這個 function 不修改資料庫，且在同一個 transaction 內，
          -- 對相同參數會返回相同結果
```

| 標記 | 意思 | 例子 |
|------|------|------|
| `VOLATILE`（預設） | 每次呼叫可能返回不同結果 | `random()`, `now()`, INSERT |
| `STABLE` | 同一 transaction 內結果一致 | 純 SELECT（沒有 `now()`） |
| `IMMUTABLE` | 永遠返回相同結果 | `abs(-5)`, 數學函數 |

**為什麼重要？** PostgreSQL 的 optimizer 會根據這個標記決定是否快取結果。標錯了會影響效能（標太寬）或正確性（標太窄）。

> **等等，`count_events` 的 `p_until` 預設值是 `NOW()`，那不是會變嗎？**
>
> 是的，但 `NOW()` 在 Postgres 裡是 transaction 開始時間，
> 在同一個 transaction 內不會變。所以 `STABLE` 是正確的。

---

## Part 2：時間序列聚合 — 完整時間軸的秘密

> **📖 SQL 第 293–374 行**

### 🤔 動腦時間

> 你要畫一張「過去 7 天每日訂單數」的折線圖。資料如下：
>
> | 日期 | 訂單數 |
> |------|--------|
> | 3/20 | 12 |
> | 3/21 | 8 |
> | 3/23 | 15 |
> | 3/25 | 20 |
>
> 問題：3/22、3/24、3/26 呢？
>
> 如果你只用 `GROUP BY created_at::DATE`，這三天不會出現在結果裡。
> 折線圖會直接從 3/21 跳到 3/23，看起來像少了兩天。

### 答案：`generate_series` 產生完整時間軸

```
步驟 1：用 generate_series 產生 3/20 ~ 3/26 的完整日期序列
步驟 2：LEFT JOIN 實際資料
步驟 3：沒有資料的日期 → coalesce(0)

結果：
  3/20  12
  3/21  8
  3/22  0    ← 補零
  3/23  15
  3/24  0    ← 補零
  3/25  20
  3/26  0    ← 補零
```

---

### 7a. 通用事件時間序列

> **📖 SQL 第 293–329 行**

```sql
CREATE OR REPLACE FUNCTION analytics.event_time_series(
  p_schema      TEXT,
  p_event_type  TEXT,
  p_granularity TEXT DEFAULT 'day',    -- 'hour', 'day', 'week', 'month'
  p_days_back   INTEGER DEFAULT 30
)
RETURNS TABLE (
  bucket      TIMESTAMPTZ,
  event_count BIGINT
)
LANGUAGE SQL
STABLE
SECURITY DEFINER
SET search_path = analytics
AS $$
  WITH series AS (
    SELECT generate_series(
      date_trunc(p_granularity, NOW() - (p_days_back || ' days')::INTERVAL),
      date_trunc(p_granularity, NOW()),
      ('1 ' || p_granularity)::INTERVAL
    ) AS bucket
  ),
  counts AS (
    SELECT
      date_trunc(p_granularity, created_at) AS bucket,
      count(*) AS cnt
    FROM analytics.events
    WHERE schema_name = p_schema
      AND event_type  = p_event_type
      AND created_at >= NOW() - (p_days_back || ' days')::INTERVAL
    GROUP BY 1
  )
  SELECT s.bucket, coalesce(c.cnt, 0) AS event_count
  FROM series s
  LEFT JOIN counts c ON c.bucket = s.bucket
  ORDER BY s.bucket;
$$;
```

讓我們把這個 function 拆解開來看：

### Step 1：generate_series — 產生時間骨架

```sql
WITH series AS (
  SELECT generate_series(
    date_trunc('day', NOW() - INTERVAL '30 days'),   -- 起點
    date_trunc('day', NOW()),                         -- 終點
    INTERVAL '1 day'                                  -- 步長
  ) AS bucket
)
```

`generate_series` 是 PostgreSQL 的「數列產生器」。它不只能產生數字（1,2,3...），也能產生時間序列：

```
bucket
─────────────────────
2024-02-25 00:00:00
2024-02-26 00:00:00
2024-02-27 00:00:00
... （每天一筆，共 31 筆）
2024-03-26 00:00:00
```

**為什麼要 `date_trunc`？**

```sql
-- 不用 date_trunc
NOW() - INTERVAL '30 days'
→ 2024-02-25 14:37:22.123456

-- 用 date_trunc('day', ...)
→ 2024-02-25 00:00:00.000000
```

`date_trunc` 把時間截斷到指定的粒度。如果你要按「天」聚合，起點必須是 00:00:00，否則 JOIN 不上。

### Step 2：聚合實際資料

```sql
counts AS (
  SELECT
    date_trunc(p_granularity, created_at) AS bucket,
    count(*) AS cnt
  FROM analytics.events
  WHERE schema_name = p_schema
    AND event_type  = p_event_type
    AND created_at >= NOW() - (p_days_back || ' days')::INTERVAL
  GROUP BY 1
)
```

把 `created_at` 也 `date_trunc` 到同粒度，然後 GROUP BY。

### Step 3：LEFT JOIN + coalesce

```sql
SELECT s.bucket, coalesce(c.cnt, 0) AS event_count
FROM series s
LEFT JOIN counts c ON c.bucket = s.bucket
ORDER BY s.bucket;
```

- **LEFT JOIN**：series 是左表，所有時間格都會出現
- **coalesce(c.cnt, 0)**：沒有資料的格子 → 0（不是 NULL）

### 動態粒度的秘密

```sql
p_granularity TEXT DEFAULT 'day'    -- 參數
...
date_trunc(p_granularity, ...)      -- 用參數控制截斷粒度
('1 ' || p_granularity)::INTERVAL   -- 動態產生步長
```

`('1 ' || 'day')::INTERVAL` = `INTERVAL '1 day'`
`('1 ' || 'hour')::INTERVAL` = `INTERVAL '1 hour'`
`('1 ' || 'month')::INTERVAL` = `INTERVAL '1 month'`

一個 function 支援四種粒度（hour / day / week / month），不用寫四個 function。

### ❓ 沒有笨問題

**Q：`(p_days_back || ' days')::INTERVAL` 為什麼要字串拼接？不能直接用 `p_days_back * INTERVAL '1 day'`？**
A：可以，兩種寫法結果一樣。字串拼接是風格偏好。`p_days_back * INTERVAL '1 day'` 更 type-safe，但拼接版在跟 `p_granularity` 共用時更統一。

**Q：`GROUP BY 1` 是什麼？**
A：`GROUP BY` 第一個 SELECT 欄位的簡寫。等同 `GROUP BY date_trunc(p_granularity, created_at)`。在 SELECT 欄位名很長時特別方便。

---

### 7b. Shop 營收時間序列 — 跨 Schema 查詢示範

> **📖 SQL 第 332–374 行**

```sql
CREATE OR REPLACE FUNCTION analytics.revenue_time_series(
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
SET search_path = analytics
AS $$
  WITH series AS (
    SELECT generate_series(
      date_trunc(p_granularity, NOW() - (p_days_back || ' days')::INTERVAL),
      date_trunc(p_granularity, NOW()),
      ('1 ' || p_granularity)::INTERVAL
    ) AS bucket
  ),
  agg AS (
    SELECT
      date_trunc(p_granularity, created_at) AS bucket,
      count(*)   AS order_count,
      sum(total) AS total_revenue,
      avg(total) AS avg_order_value
    FROM shop.orders                            -- ← 跨 schema！
    WHERE status NOT IN ('cancelled', 'refunded')
      AND deleted_at IS NULL
      AND created_at >= NOW() - (p_days_back || ' days')::INTERVAL
    GROUP BY 1
  )
  SELECT
    s.bucket,
    coalesce(a.order_count, 0),
    coalesce(a.total_revenue, 0),
    coalesce(a.avg_order_value, 0)
  FROM series s
  LEFT JOIN agg a ON a.bucket = s.bucket
  ORDER BY s.bucket;
$$;
```

### 跟 7a 的差異

| | event_time_series | revenue_time_series |
|---|---|---|
| 資料來源 | `analytics.events`（自己的表） | `shop.orders`（跨 schema） |
| 聚合指標 | 只有 count | count + sum + avg |
| 過濾條件 | schema_name + event_type | status + deleted_at |

**跨 schema 查詢**是 analytics 的核心能力。`SECURITY DEFINER` 確保函數有權限讀取 `shop.orders`，即使呼叫者只是普通的 authenticated 用戶。

### 🧠 你的大腦在想…

> 「在 agg CTE 裡，`coalesce` 為什麼不放在 `sum(total)` 和 `avg(total)` 裡面？」
>
> 因為如果某一天有訂單，`sum(total)` 不會是 NULL（至少是 0+）。
> `coalesce` 放在最後的 SELECT 是為了處理 LEFT JOIN 沒匹配到的情況——
> 那些「完全沒有訂單的天」在 agg CTE 裡根本沒有 row。

---

### ❓ 沒有笨問題

**Q：`generate_series` 產生的時間序列存在哪裡？會佔磁碟空間嗎？**
A：不會。`generate_series` 是 set-returning function，結果只在查詢執行期間存在記憶體裡。查詢結束就消失了。它不是表，不佔磁碟。

**Q：如果 `p_granularity` 傳入 `'year'`，會怎樣？**
A：`date_trunc('year', ...)` 和 `INTERVAL '1 year'` 都是合法的，所以會產生年級的時間序列。但我們的 function 沒有做參數驗證——如果有人傳 `'banana'`，PostgreSQL 會報 `invalid input syntax for type interval`。Production 環境可以加 CHECK。

**Q：`RETURNS TABLE (...)` 跟 `RETURNS SETOF record` 有什麼差別？**
A：`RETURNS TABLE` 明確定義了回傳的欄位名稱和型別，呼叫者可以直接 `SELECT bucket, event_count FROM analytics.event_time_series(...)`。`SETOF record` 是匿名的，呼叫者必須每次都手動指定欄位型別，很不方便。

---

## 模式總結：時間序列三部曲

所有時間序列函數都遵循相同的模式：

```sql
-- 1. 產生時間骨架
WITH series AS (
  SELECT generate_series(起點, 終點, 步長) AS bucket
),
-- 2. 聚合實際資料
agg AS (
  SELECT date_trunc(粒度, 時間欄位) AS bucket, 聚合函數
  FROM 資料表
  WHERE 篩選條件
  GROUP BY 1
)
-- 3. LEFT JOIN + coalesce
SELECT s.bucket, coalesce(a.指標, 0)
FROM series s
LEFT JOIN agg a ON a.bucket = s.bucket
ORDER BY s.bucket;
```

記住這個模式。Chapter 5 的 RAG token 消耗統計也用一模一樣的結構。

---

### 🛠️ 動手做

1. 先用 `analytics.log_event` 插入幾筆測試事件：
   ```sql
   SELECT analytics.log_event('shop', 'order.created', 'order', '01TEST001', NULL,
     '{"total": 500}');
   SELECT analytics.log_event('shop', 'order.created', 'order', '01TEST002', NULL,
     '{"total": 1200}');
   SELECT analytics.log_event('crawler', 'crawl.completed', 'crawl_run');
   ```
2. 用 `count_events` 查詢今天的事件數：
   ```sql
   SELECT analytics.count_events('shop', 'order.created');
   ```
3. 試試不同粒度的時間序列：
   ```sql
   SELECT * FROM analytics.event_time_series('shop', 'order.created', 'hour', 1);
   SELECT * FROM analytics.event_time_series('shop', 'order.created', 'day', 7);
   ```
4. 觀察「補零」效果——大部分時間格應該是 0（因為你只插了幾筆）

---

## 本章重點回顧

| 概念 | 學到什麼 |
|------|---------|
| `LANGUAGE SQL` vs `plpgsql` | 純 SQL 能被 inline，效能更好 |
| `SECURITY DEFINER` | 用 owner 權限執行，搭配 `SET search_path` |
| `STABLE` / `VOLATILE` / `IMMUTABLE` | 告訴 optimizer 是否可以快取結果 |
| `generate_series` | 產生完整時間軸，避免折線圖斷線 |
| `date_trunc` | 截斷時間到指定粒度 |
| 動態粒度 | `('1 ' \|\| p_granularity)::INTERVAL` 一個函數多種粒度 |
| LEFT JOIN + coalesce | 沒資料的時間格補零 |
| `GROUP BY 1` | SELECT 第一欄的簡寫 |

---

← [Chapter 2 — Materialized View + 漏斗追蹤](02_matview-and-funnel.md) | [Chapter 4 — 漏斗轉換 + Cohort 留存](04_funnel-cohort-analysis.md) →

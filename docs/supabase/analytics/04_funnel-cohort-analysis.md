# Head First 漏斗轉換 + Cohort 留存 — Chapter 4

> **對應 SQL**：`migrations/005_analytics_schema.sql` 第 377–521 行
>
> **前置閱讀**：[Chapter 3 — 時間序列聚合](03_time-series-aggregation.md)

## 搭配閱讀

| 你在讀的 | SQL 行號 | 學什麼 |
|----------|----------|--------|
| Part 1：funnel_conversion | 383–420 | CROSS JOIN 基準值、整體轉換率 |
| Part 2：funnel_dropoff | 422–462 | LAG window function、step-over-step 流失 |
| Part 3：monthly_cohort_retention | 470–521 | CTE 三層、age() 月差、nullif 防禦 |

---

## 你在學什麼？

這一章教你三個進階 SQL 分析技巧：

1. **漏斗轉換率**：`CROSS JOIN` + 條件比較
2. **漏斗流失率**：`LAG` window function
3. **月份 Cohort 留存**：CTE 分群 + `age()` 計算

這三個技巧是商業分析的核心。學會之後，你不需要 Mixpanel、Amplitude 這些工具，純 SQL 就能做。

---

## Part 1：漏斗轉換率

> **📖 SQL 第 383–420 行**

### 🤔 動腦時間

> 過去 7 天，你的電商漏斗數據如下：
>
> | Step | Sessions |
> |------|----------|
> | view | 1000 |
> | add_to_cart | 400 |
> | checkout | 200 |
> | payment | 150 |
> | completed | 120 |
>
> 「轉換率」要怎麼算？是跟上一步比，還是跟第一步比？

### 答案：兩種都有用，但「跟第一步比」更常用

- **Overall conversion**（跟第一步比）：`completed / view = 120/1000 = 12%`
- **Step-over-step**（跟上一步比）：`completed / payment = 120/150 = 80%`

第一種告訴你「整體漏斗效率」，第二種告訴你「哪一步流失最嚴重」。

我們先做第一種。

---

### 8a. 漏斗轉換率

```sql
CREATE OR REPLACE FUNCTION analytics.funnel_conversion(
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
SET search_path = analytics
AS $$
  WITH step_counts AS (
    SELECT
      step,
      step_order,
      count(DISTINCT session_id) AS sessions
    FROM analytics.funnel_events
    WHERE created_at >= NOW() - (p_days_back || ' days')::INTERVAL
    GROUP BY step, step_order
  ),
  first_step AS (
    SELECT sessions FROM step_counts WHERE step_order = 1
  )
  SELECT
    sc.step,
    sc.step_order,
    sc.sessions,
    CASE
      WHEN fs.sessions = 0 THEN 0
      ELSE round(sc.sessions::NUMERIC / fs.sessions * 100, 2)
    END AS conversion_pct
  FROM step_counts sc
  CROSS JOIN first_step fs
  ORDER BY sc.step_order;
$$;
```

### 拆解

**Step 1：計算每一步的 session 數**

```sql
WITH step_counts AS (
  SELECT step, step_order,
    count(DISTINCT session_id) AS sessions
  FROM analytics.funnel_events
  WHERE created_at >= NOW() - INTERVAL '7 days'
  GROUP BY step, step_order
)
```

`count(DISTINCT session_id)` — 一個 session 在同一步觸發多次事件（比如重複瀏覽），只算一次。

**Step 2：取出第一步的 session 數作為基準**

```sql
first_step AS (
  SELECT sessions FROM step_counts WHERE step_order = 1
)
```

**Step 3：CROSS JOIN 讓每一行都能看到基準值**

```sql
FROM step_counts sc
CROSS JOIN first_step fs
```

### 🤔 動腦時間

> `CROSS JOIN` 是什麼？跟 `INNER JOIN` 有什麼差別？

### 答案：CROSS JOIN 是笛卡爾積

```
INNER JOIN：A 和 B 有匹配條件，只保留匹配的 row
CROSS JOIN：A 的每一行 × B 的每一行（沒有條件）
```

但這裡 `first_step` 只有 **1 行**（第一步的 session 數）。所以 CROSS JOIN 的效果是：

```
step_counts（5 行）× first_step（1 行）= 5 行
每一行都帶上了 first_step.sessions 這個基準值
```

這是 SQL 裡**「把常數附加到每一行」** 的經典手法。

| 替代寫法 | 為什麼不用 |
|---------|----------|
| subquery in SELECT | `(SELECT sessions FROM ...)` 每行都執行一次，效率差 |
| 變數 | `LANGUAGE SQL` 不支援變數 |
| CROSS JOIN | 查詢計劃只執行一次 first_step，效率最好 |

---

## Part 2：漏斗流失率 — LAG Window Function

> **📖 SQL 第 422–462 行**

### 8b. 每步流失率

```sql
CREATE OR REPLACE FUNCTION analytics.funnel_dropoff(
  p_days_back INTEGER DEFAULT 7
)
RETURNS TABLE (
  step            TEXT,
  step_order      SMALLINT,
  sessions        BIGINT,
  prev_sessions   BIGINT,
  dropoff_pct     NUMERIC
)
LANGUAGE SQL
STABLE
SECURITY DEFINER
SET search_path = analytics
AS $$
  WITH step_counts AS (
    SELECT
      step,
      step_order,
      count(DISTINCT session_id) AS sessions
    FROM analytics.funnel_events
    WHERE created_at >= NOW() - (p_days_back || ' days')::INTERVAL
    GROUP BY step, step_order
  )
  SELECT
    sc.step,
    sc.step_order,
    sc.sessions,
    lag(sc.sessions) OVER (ORDER BY sc.step_order) AS prev_sessions,
    CASE
      WHEN lag(sc.sessions) OVER (ORDER BY sc.step_order) IS NULL THEN 0
      WHEN lag(sc.sessions) OVER (ORDER BY sc.step_order) = 0 THEN 0
      ELSE round(
        (1 - sc.sessions::NUMERIC
             / lag(sc.sessions) OVER (ORDER BY sc.step_order)) * 100,
        2
      )
    END AS dropoff_pct
  FROM step_counts sc
  ORDER BY sc.step_order;
$$;
```

### 新技巧：`LAG` Window Function

```sql
lag(sc.sessions) OVER (ORDER BY sc.step_order) AS prev_sessions
```

`LAG(欄位)` 取得「上一行」的值。`OVER (ORDER BY step_order)` 定義「上一行」的排序。

```
step_order | sessions | lag(sessions) | 意思
1          | 1000     | NULL          | 第一步沒有「上一步」
2          | 400      | 1000          | 上一步有 1000
3          | 200      | 400           | 上一步有 400
4          | 150      | 200           | 上一步有 200
5          | 120      | 150           | 上一步有 150
```

### 流失率公式

```
流失率 = (1 - 本步 / 上一步) × 100

step 2: (1 - 400/1000) × 100 = 60%    ← 60% 的人在「加入購物車」流失
step 3: (1 - 200/400)  × 100 = 50%    ← 50% 的人在「結帳」流失
step 4: (1 - 150/200)  × 100 = 25%
step 5: (1 - 120/150)  × 100 = 20%
```

### 防禦性程式碼

```sql
CASE
  WHEN lag(...) IS NULL THEN 0     -- 第一步：沒有上一步
  WHEN lag(...) = 0 THEN 0         -- 上一步是零：避免除以零
  ELSE round(...)
END
```

**三層防禦**：NULL → 0 → 正常計算。永遠不會爆 division by zero。

### 🧠 你的大腦在想…

> 「Window function 跟 GROUP BY 有什麼差別？」
>
> - `GROUP BY` 把多行**壓縮**成一行（聚合）
> - Window function 保留所有行，但每行可以**看到其他行**的資料
>
> ```sql
> -- GROUP BY：10 行 → 5 行（壓縮）
> SELECT step, count(*) FROM ... GROUP BY step
>
> -- Window function：10 行 → 10 行（每行多帶一個計算值）
> SELECT step, sessions, lag(sessions) OVER (ORDER BY step_order) FROM ...
> ```

---

## Part 3：月份 Cohort 留存 — 最強的分析技巧

> **📖 SQL 第 466–521 行**

### 🤔 動腦時間

> 老闆問：「我們 1 月份獲得的新客戶，到 3 月份還有多少人回來消費？」
>
> 這不是一個簡單的 `WHERE created_at BETWEEN ...` 可以解決的問題。
>
> 你需要：
> 1. 找出每位客戶的**首次下單月份**（= 他的 cohort）
> 2. 追蹤他在**之後每個月**是否有活動
> 3. 按 cohort 分組，算出留存率
>
> 這叫 **Cohort Retention Analysis**。

---

### 9a. 月份 Cohort 留存率

```sql
CREATE OR REPLACE FUNCTION analytics.monthly_cohort_retention(
  p_months_back INTEGER DEFAULT 6
)
RETURNS TABLE (
  cohort_month   DATE,
  months_since   INTEGER,
  cohort_size    BIGINT,
  active_users   BIGINT,
  retention_pct  NUMERIC
)
LANGUAGE SQL
STABLE
SECURITY DEFINER
SET search_path = analytics
AS $$
  WITH first_order AS (
    -- 每位顧客的首次下單月份 = cohort
    SELECT
      customer_id,
      date_trunc('month', min(created_at))::DATE AS cohort_month
    FROM shop.orders
    WHERE deleted_at IS NULL
      AND created_at >= (date_trunc('month', NOW())
                         - (p_months_back || ' months')::INTERVAL)
    GROUP BY customer_id
  ),
  activity AS (
    -- 每位顧客每月是否有活動
    SELECT DISTINCT
      o.customer_id,
      fo.cohort_month,
      date_trunc('month', o.created_at)::DATE AS activity_month
    FROM shop.orders o
    JOIN first_order fo ON fo.customer_id = o.customer_id
    WHERE o.deleted_at IS NULL
  )
  SELECT
    a.cohort_month,
    (EXTRACT(YEAR FROM age(a.activity_month, a.cohort_month)) * 12
     + EXTRACT(MONTH FROM age(a.activity_month, a.cohort_month)))::INTEGER
      AS months_since,
    count(DISTINCT fo2.customer_id) AS cohort_size,
    count(DISTINCT a.customer_id)   AS active_users,
    round(
      count(DISTINCT a.customer_id)::NUMERIC
      / nullif(count(DISTINCT fo2.customer_id), 0) * 100,
      2
    ) AS retention_pct
  FROM activity a
  JOIN first_order fo2 ON fo2.cohort_month = a.cohort_month
  GROUP BY a.cohort_month, a.activity_month
  ORDER BY a.cohort_month, months_since;
$$;
```

### 拆解：三層 CTE

**CTE 1：first_order — 確定每個客戶的 Cohort**

```sql
WITH first_order AS (
  SELECT
    customer_id,
    date_trunc('month', min(created_at))::DATE AS cohort_month
  FROM shop.orders
  WHERE deleted_at IS NULL
  GROUP BY customer_id
)
```

```
customer_id | cohort_month
C001        | 2024-01-01   ← 1 月份首次下單
C002        | 2024-01-01   ← 也是 1 月份
C003        | 2024-02-01   ← 2 月份首次下單
```

**CTE 2：activity — 每個客戶每月的活動記錄**

```sql
activity AS (
  SELECT DISTINCT
    o.customer_id,
    fo.cohort_month,
    date_trunc('month', o.created_at)::DATE AS activity_month
  FROM shop.orders o
  JOIN first_order fo ON fo.customer_id = o.customer_id
  WHERE o.deleted_at IS NULL
)
```

```
customer_id | cohort_month | activity_month
C001        | 2024-01-01   | 2024-01-01     ← 首月（一定有）
C001        | 2024-01-01   | 2024-03-01     ← 3 月回來了
C002        | 2024-01-01   | 2024-01-01     ← 首月
(C002 之後就沒出現了 —— 流失)
C003        | 2024-02-01   | 2024-02-01
C003        | 2024-02-01   | 2024-03-01
```

`DISTINCT` 很重要——一個客戶在同一個月下了 5 筆訂單，只算一次活動。

**最終 SELECT：計算留存**

```sql
(EXTRACT(YEAR FROM age(a.activity_month, a.cohort_month)) * 12
 + EXTRACT(MONTH FROM age(a.activity_month, a.cohort_month)))::INTEGER
  AS months_since
```

### 🤔 動腦時間

> `age('2024-03-01', '2024-01-01')` 返回什麼？

### 答案：`2 mons`

```sql
age('2024-03-01', '2024-01-01')
→ '2 mons'（PostgreSQL 的 interval 格式）

EXTRACT(YEAR FROM '2 mons'::interval) → 0
EXTRACT(MONTH FROM '2 mons'::interval) → 2

0 * 12 + 2 = 2    ← months_since = 2
```

為什麼不直接用月份相減？因為跨年的情況（12月 → 1月）會出問題。`age()` 函數幫你處理了。

---

### Cohort 留存表的樣子

最終結果像這樣：

```
cohort_month | months_since | cohort_size | active_users | retention_pct
2024-01-01   | 0            | 100         | 100          | 100.00
2024-01-01   | 1            | 100         | 45           | 45.00
2024-01-01   | 2            | 100         | 30           | 30.00
2024-02-01   | 0            | 80          | 80           | 100.00
2024-02-01   | 1            | 80          | 40           | 50.00
```

轉成三角矩陣（經典的 cohort 表格）：

```
         Month 0   Month 1   Month 2   Month 3
Jan      100%      45%       30%       22%
Feb      100%      50%       35%
Mar      100%      48%
Apr      100%
```

每個 cohort 的 Month 0 一定是 100%（首月嘛）。之後的數字就是留存率。

### `nullif` 防禦

```sql
/ nullif(count(DISTINCT fo2.customer_id), 0) * 100
```

`nullif(x, 0)` 的效果：如果 `x = 0`，返回 `NULL`（避免除以零）。

比 `CASE WHEN` 短很多：
```sql
-- 長版
CASE WHEN count(...) = 0 THEN NULL ELSE ... / count(...) END

-- 短版
... / nullif(count(...), 0)
```

---

### ❓ 沒有笨問題

**Q：如果一個 session 跳過步驟（直接從 view 到 checkout），漏斗分析會出問題嗎？**
A：不會出問題，但數據會「看起來怪」——checkout 的 session 數可能比 add_to_cart 多。這通常表示你的前端埋點有遺漏，或是使用者透過書籤直接進入結帳頁。漏斗分析的前提是步驟嚴格遞進。

**Q：Cohort 分析裡，如果客戶在 1 月和 3 月都下單，但 2 月沒有，Month 1 的留存率會怎麼算？**
A：Month 1（2 月）那個客戶不會被計入 `active_users`。留存率反映的是「該月是否有活動」，不是「是否最終回來了」。所以 Month 1 可能是 40%，Month 2 反而是 45%——這表示有些客戶跳過一個月後回來了。

**Q：`LAG` 只能看上一行嗎？能看上兩行嗎？**
A：可以。`LAG(sessions, 2)` 看上兩行，`LAG(sessions, 3)` 看上三行。對應的還有 `LEAD` 看下一行。

---

## 漏斗 vs Cohort 的差異

| | 漏斗分析 | Cohort 分析 |
|---|---|---|
| 問的問題 | 「哪一步流失最多？」 | 「客戶幾個月後還會回來？」 |
| 時間維度 | 單次旅程（分鐘到小時） | 長期追蹤（週到月） |
| 分群方式 | 按步驟（step_order） | 按首次行為月份 |
| 資料來源 | `funnel_events` | `shop.orders`（跨 schema） |
| 核心技巧 | `LAG`, `CROSS JOIN` | `age()`, `EXTRACT`, CTE |

---

### 🛠️ 動手做

1. 插入模擬漏斗數據（同一個 session 走完五步）：
   ```sql
   INSERT INTO analytics.funnel_events (session_id, customer_id, step, step_order) VALUES
     ('sess_demo', 'cust_001', 'view', 1),
     ('sess_demo', 'cust_001', 'add_to_cart', 2),
     ('sess_demo', 'cust_001', 'checkout', 3),
     ('sess_demo', 'cust_001', 'payment', 4),
     ('sess_demo', 'cust_001', 'completed', 5);
   -- 再插一個半途流失的 session
   INSERT INTO analytics.funnel_events (session_id, step, step_order) VALUES
     ('sess_drop', 'view', 1),
     ('sess_drop', 'add_to_cart', 2);
   ```
2. 呼叫漏斗分析：
   ```sql
   SELECT * FROM analytics.funnel_conversion(30);
   SELECT * FROM analytics.funnel_dropoff(30);
   ```
3. 觀察：step 3-5 的 conversion_pct 應該是多少？dropoff_pct 呢？

---

## 本章重點回顧

| 概念 | 學到什麼 |
|------|---------|
| `CROSS JOIN` | 把單行常數附加到每一行的手法 |
| `LAG` window function | 取得上一行的值，保留所有行 |
| Window vs GROUP BY | GROUP BY 壓縮行數；Window 保留行數但能看其他行 |
| 三層防禦 | `IS NULL` → `= 0` → 正常計算，永不 division by zero |
| Cohort CTE 三層 | first_order（分群）→ activity（活動）→ 留存計算 |
| `age()` + `EXTRACT` | 計算兩個日期之間的月數差 |
| `nullif(x, 0)` | 比 `CASE WHEN` 更短的除零防禦 |
| `count(DISTINCT ...)` | 去重計算（同一客戶多筆訂單只算一次） |

---

← [Chapter 3 — 時間序列聚合](03_time-series-aggregation.md) | [Chapter 5 — 監控儀表板 + 異常偵測](05_monitoring-anomaly.md) →

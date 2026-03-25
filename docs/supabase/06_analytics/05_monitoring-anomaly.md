# Head First 監控儀表板 + 異常偵測 — Chapter 5

> **對應 SQL**：`migrations/005_analytics_schema.sql` 第 524–912 行
>
> **前置閱讀**：[Chapter 4 — 漏斗轉換 + Cohort 留存](04_funnel-cohort-analysis.md)

## 搭配閱讀

| 你在讀的 | SQL 行號 | 學什麼 |
|----------|----------|--------|
| Part 1：rag_quality_trend | 529–562 | 週粒度聚合、NULL OR 可選過濾 |
| Part 1：low_quality_chunks | 565–600 | HAVING 門檻、left() 預覽、多表 JOIN |
| Part 1：rag_token_usage | 603–650 | 時間序列三部曲（複習） |
| Part 2：crawler_source_ranking | 658–697 | EXTRACT(EPOCH FROM interval) |
| Part 2：crawler_queue_health | 700–720 | 極簡聚合、min() 找最老任務 |
| Part 3：system_dashboard | 728–805 | Period-over-Period、隱式 CROSS JOIN |
| Part 4：detect_anomalies | 814–863 | Z-score、stddev()、abs() |
| Part 5：data_freshness | 872–912 | 每表不同閾值、EXTRACT / 60 換算 |

---

## 你在學什麼？

這一章涵蓋五個 function，分成三個主題：

1. **領域監控**：RAG 品質趨勢、低品質 Chunk、Token 消耗、Crawler 來源排行、佇列健康
2. **跨域儀表板**：一個 function call 看全系統
3. **異常偵測**：Z-score 統計方法 + 資料新鮮度檢查

---

## Part 1：RAG 品質監控

> **📖 SQL 第 524–650 行**

### 10a. RAG 評估指標趨勢（週維度）

```sql
CREATE OR REPLACE FUNCTION analytics.rag_quality_trend(
  p_collection_id TEXT DEFAULT NULL,
  p_weeks_back    INTEGER DEFAULT 12
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
```

### 🤔 動腦時間

> 為什麼 RAG 品質用「週」而不是「天」？

### 答案：統計穩定性

如果一天只有 5 筆 RAG 查詢，一筆低分就讓平均值暴跌 20%。以週為單位（假設 35 筆），單筆異常值的影響只有 3%。

```
每日粒度：  ∿∿∿∿∿∿  （劇烈波動，看不出趨勢）
每週粒度：  ╲──╱──   （平滑曲線，趨勢清楚）
```

> **經驗法則**：指標量少（<50/天）用週或月；量大（>1000/天）可以用天甚至小時。

### 選擇性過濾的技巧

```sql
WHERE ql.created_at >= NOW() - (p_weeks_back || ' weeks')::INTERVAL
  AND (p_collection_id IS NULL OR ql.collection_id = p_collection_id)
```

`(p_collection_id IS NULL OR ql.collection_id = p_collection_id)` 這個模式是「可選過濾」：

- 傳 `NULL` → 看全部 collection
- 傳值 → 只看特定 collection

一個 function 兼顧兩種需求，不用寫兩個。

---

### 10b. 低品質 Chunk 排行

> **📖 SQL 第 565–600 行**

```sql
CREATE OR REPLACE FUNCTION analytics.low_quality_chunks(
  p_collection_id TEXT,
  p_min_hits      INTEGER DEFAULT 3,
  p_limit         INTEGER DEFAULT 20
)
RETURNS TABLE (
  chunk_id      TEXT,
  document_id   TEXT,
  content_preview TEXT,
  hit_count     BIGINT,
  avg_score     FLOAT8,
  avg_rank      FLOAT8,
  avg_query_faithfulness FLOAT8
)
```

這個 function 找出「經常被檢索但品質低」的 chunk——它們被向量搜尋選中了，但附帶的查詢卻得到低分。

```sql
  FROM rag.query_log_results r
  JOIN rag.chunks c ON c.id = r.chunk_id
  JOIN rag.query_logs ql ON ql.id = r.query_id
  WHERE c.collection_id = p_collection_id
  GROUP BY r.chunk_id, c.document_id, c.content
  HAVING count(*) >= p_min_hits        -- 至少被檢索 N 次
  ORDER BY avg(r.score) ASC            -- 按平均分數排序（低分在前）
  LIMIT p_limit;
```

### 重要技巧

```sql
left(c.content, 120) AS content_preview
```

`left(text, n)` 取前 N 個字元。Chunk 的 content 可能有幾千字元，在結果表裡只需要預覽。比 `substring(c.content, 1, 120)` 更簡潔。

`HAVING count(*) >= p_min_hits` — 被檢索一兩次的 chunk 可能只是運氣不好。`p_min_hits` 設門檻，只看有統計意義的結果。

---

### 10c. RAG Token 消耗統計

> **📖 SQL 第 603–650 行**

又是 Chapter 3 學過的**時間序列三部曲**：

```sql
WITH series AS (
  SELECT generate_series(...) AS bucket
),
agg AS (
  SELECT date_trunc(...) AS bucket,
    count(*) AS query_count,
    sum(prompt_tokens) AS total_prompt_tokens,
    sum(completion_tokens) AS total_completion_tokens,
    ...
  FROM rag.query_logs
  GROUP BY 1
)
SELECT s.bucket, coalesce(...)
FROM series s LEFT JOIN agg a ON ...;
```

看到了嗎？跟 `event_time_series` 和 `revenue_time_series` 一模一樣的結構。

新的欄位：

```sql
CASE WHEN coalesce(a.query_count, 0) = 0 THEN 0
     ELSE round(a.total_tokens::NUMERIC / a.query_count, 1)
END AS avg_tokens_per_query
```

每次查詢平均消耗多少 token。這是 LLM 成本控制的關鍵指標。

---

## Part 2：Crawler 監控

> **📖 SQL 第 653–720 行**

### 11a. 各來源成功率排行

```sql
CREATE OR REPLACE FUNCTION analytics.crawler_source_ranking(
  p_days_back INTEGER DEFAULT 30
)
RETURNS TABLE (
  source_id        TEXT,
  source_name      TEXT,
  total_runs       BIGINT,
  success_runs     BIGINT,
  success_rate_pct NUMERIC,
  total_articles   BIGINT,
  total_errors     BIGINT,
  avg_duration_s   NUMERIC,
  last_run_at      TIMESTAMPTZ
)
```

跟 Chapter 2 的 `mv_source_health` MATVIEW 很像，但這是**即時計算**的 function。

| | mv_source_health | crawler_source_ranking |
|---|---|---|
| 資料新鮮度 | REFRESH 時更新 | 即時 |
| 效能 | 快（讀快取） | 慢（每次計算） |
| 使用場景 | Dashboard 展示 | 深度排查 |

```sql
round(avg(EXTRACT(EPOCH FROM (cr.finished_at - cr.started_at)))::NUMERIC, 1)
  AS avg_duration_s
```

### 新技巧：`EXTRACT(EPOCH FROM interval)`

```sql
cr.finished_at - cr.started_at
→ '00:02:35'::interval（2 分 35 秒）

EXTRACT(EPOCH FROM '00:02:35'::interval)
→ 155.0（秒數）
```

`EXTRACT(EPOCH FROM interval)` 把任何 interval 轉成**總秒數**，方便計算平均值。

---

### 11b. 爬蟲佇列健康

> **📖 SQL 第 700–720 行**

```sql
CREATE OR REPLACE FUNCTION analytics.crawler_queue_health()
RETURNS TABLE (
  status    TEXT,
  count     BIGINT,
  oldest_at TIMESTAMPTZ,
  avg_retry NUMERIC
)
```

```sql
SELECT
  status,
  count(*)                 AS count,
  min(created_at)          AS oldest_at,
  round(avg(retry_count)::NUMERIC, 1) AS avg_retry
FROM crawler.crawl_queue
GROUP BY status
ORDER BY count DESC;
```

這個 function 只有 6 行 SQL，但資訊密度很高：

- **count by status**：多少 pending / running / failed / dead？
- **oldest_at**：最早的 pending 任務是什麼時候入隊的？（太久 = 卡住了）
- **avg_retry**：平均重試次數？（太高 = 來源可能壞了）

---

## Part 3：跨域儀表板

> **📖 SQL 第 723–805 行**

### 12a. 全域健康摘要

```sql
CREATE OR REPLACE FUNCTION analytics.system_dashboard(
  p_days_back INTEGER DEFAULT 1
)
RETURNS TABLE (
  domain        TEXT,
  metric        TEXT,
  value         NUMERIC,
  trend_vs_prev NUMERIC
)
```

### 🤔 動腦時間

> 這個 function 返回 6 行資料：3 個 domain × 2 個 metric。
> 每個 metric 都帶「跟前一個同等週期比」的 trend。
>
> 如果 `p_days_back = 1`：
> - current = 今天
> - prev = 昨天
> - trend = 今天 - 昨天
>
> 如果 `p_days_back = 7`：
> - current = 最近 7 天
> - prev = 再前 7 天
> - trend = 最近 7 天 - 再前 7 天
>
> 這叫什麼？

### 答案：Period-over-Period 比較

```sql
WITH params AS (
  SELECT
    NOW() - (p_days_back || ' days')::INTERVAL AS since,
    NOW() - (p_days_back * 2 || ' days')::INTERVAL AS prev_since,
    NOW() - (p_days_back || ' days')::INTERVAL AS prev_until
),
shop_current AS (
  SELECT count(*) AS orders, coalesce(sum(total), 0) AS revenue
  FROM shop.orders, params
  WHERE created_at >= params.since AND ...
),
shop_prev AS (
  SELECT count(*) AS orders, coalesce(sum(total), 0) AS revenue
  FROM shop.orders, params
  WHERE created_at >= params.prev_since AND created_at < params.prev_until AND ...
)
```

**隱式 CROSS JOIN**：`FROM shop.orders, params` 等同 `FROM shop.orders CROSS JOIN params`。因為 `params` 只有一行，這把時間範圍參數「注入」到每個查詢裡。

然後 `UNION ALL` 把三個 domain 的結果拼在一起：

```sql
SELECT 'shop'::TEXT, 'orders'::TEXT,
  sc.orders::NUMERIC, sc.orders::NUMERIC - sp.orders::NUMERIC
FROM shop_current sc, shop_prev sp
UNION ALL
SELECT 'shop', 'revenue', sc.revenue, sc.revenue - sp.revenue
FROM shop_current sc, shop_prev sp
UNION ALL
SELECT 'crawler', 'runs', ...
UNION ALL
...
```

結果像這樣：

```
domain  | metric          | value   | trend_vs_prev
shop    | orders          | 42      | +5
shop    | revenue         | 12580   | -320
crawler | runs            | 15      | +2
crawler | failed_runs     | 1       | -1
rag     | queries         | 230     | +45
rag     | avg_faithfulness| 0.8523  | +0.0112
```

一個 RPC call，全系統一覽無遺。

---

## Part 4：Z-score 異常偵測

> **📖 SQL 第 808–863 行**

### 🤔 動腦時間

> 你的 event log 過去 30 天，平均每天 100 筆事件。
> 突然某一天跳到 300 筆。這是異常嗎？
>
> 「看起來很多」不是答案。需要一個**數學定義**。

### 答案：Z-score

```
Z-score = (觀察值 - 平均值) / 標準差

如果 mean = 100, stddev = 20：
  Z(300) = (300 - 100) / 20 = 10    ← 超級異常
  Z(130) = (130 - 100) / 20 = 1.5   ← 正常波動
  Z(80)  = (80 - 100)  / 20 = -1.0  ← 略低但正常
```

**Z-score 的經驗法則**：

| |Z| | 意思 | 機率 |
|------|------|------|
| < 1 | 正常波動 | 68% |
| 1-2 | 有點異常 | 27% |
| > 2 | 顯著異常 | 5% |
| > 3 | 極端異常 | 0.3% |

---

### 13a. 通用 Z-score 異常偵測

```sql
CREATE OR REPLACE FUNCTION analytics.detect_anomalies(
  p_schema      TEXT,
  p_event_type  TEXT,
  p_days_back   INTEGER DEFAULT 30,
  p_z_threshold FLOAT8 DEFAULT 2.0
)
RETURNS TABLE (
  day          DATE,
  event_count  BIGINT,
  mean_count   FLOAT8,
  stddev_count FLOAT8,
  z_score      FLOAT8,
  is_anomaly   BOOLEAN
)
LANGUAGE SQL
STABLE
SECURITY DEFINER
SET search_path = analytics
AS $$
  WITH daily AS (
    SELECT
      created_at::DATE AS day,
      count(*) AS event_count
    FROM analytics.events
    WHERE schema_name = p_schema
      AND event_type  = p_event_type
      AND created_at >= NOW() - (p_days_back || ' days')::INTERVAL
    GROUP BY 1
  ),
  stats AS (
    SELECT
      avg(event_count) AS mean_count,
      stddev(event_count) AS stddev_count
    FROM daily
  )
  SELECT
    d.day,
    d.event_count,
    s.mean_count,
    s.stddev_count,
    CASE WHEN s.stddev_count = 0 THEN 0
         ELSE (d.event_count - s.mean_count) / s.stddev_count
    END AS z_score,
    CASE WHEN s.stddev_count = 0 THEN FALSE
         ELSE abs((d.event_count - s.mean_count) / s.stddev_count) > p_z_threshold
    END AS is_anomaly
  FROM daily d
  CROSS JOIN stats s
  ORDER BY d.day;
$$;
```

### 拆解

**CTE 1：daily — 每日事件數**

```sql
WITH daily AS (
  SELECT created_at::DATE AS day, count(*) AS event_count
  FROM analytics.events
  WHERE ...
  GROUP BY 1
)
```

`created_at::DATE` 是 `date_trunc('day', created_at)::DATE` 的簡寫。

**CTE 2：stats — 全期的統計值**

```sql
stats AS (
  SELECT
    avg(event_count) AS mean_count,
    stddev(event_count) AS stddev_count
  FROM daily
)
```

PostgreSQL 內建 `stddev()` 函數（樣本標準差）。不用手算。

**最終 SELECT：Z-score 計算**

```sql
CASE WHEN s.stddev_count = 0 THEN 0     -- 如果所有天數值都相同，stddev=0
     ELSE (d.event_count - s.mean_count) / s.stddev_count
END AS z_score
```

又是 `CROSS JOIN stats s`——單行 stats 附加到每一天的資料上。

```sql
abs(z_score) > p_z_threshold AS is_anomaly
```

`abs()` 取絕對值——異常可以是「太多」也可以是「太少」。`p_z_threshold` 預設 2.0，你可以調成 3.0（更嚴格）或 1.5（更敏感）。

### 🧠 你的大腦在想…

> 「Z-score 假設資料是常態分布。如果不是呢？」
>
> 好問題。如果你的資料有明顯的週末效應（週末流量低），
> Z-score 會把每個週末都標成異常。
>
> 進階做法：
> 1. 按星期幾分組，各自算 Z-score
> 2. 用中位數代替平均值（更抗離群值）
> 3. 用 IQR（四分位距）代替標準差
>
> 但作為第一版，Z-score 已經很夠用了。

---

## Part 5：資料新鮮度

> **📖 SQL 第 866–912 行**

### 14a. 各 Schema 最新資料時間

```sql
CREATE OR REPLACE FUNCTION analytics.data_freshness()
RETURNS TABLE (
  schema_name      TEXT,
  entity           TEXT,
  latest_record_at TIMESTAMPTZ,
  minutes_ago      NUMERIC,
  is_stale         BOOLEAN
)
```

```sql
  -- Shop
  SELECT 'shop'::TEXT, 'orders'::TEXT,
    max(created_at),
    round(EXTRACT(EPOCH FROM (NOW() - max(created_at))) / 60, 1),
    max(created_at) < NOW() - INTERVAL '24 hours'
  FROM shop.orders
  UNION ALL
  -- Crawler
  SELECT 'crawler', 'crawl_runs',
    max(created_at),
    round(EXTRACT(EPOCH FROM (NOW() - max(created_at))) / 60, 1),
    max(created_at) < NOW() - INTERVAL '6 hours'
  FROM crawler.crawl_runs
  UNION ALL
  ...
```

每個 entity 有不同的「過期」定義：

| Entity | 過期閾值 | 原因 |
|--------|---------|------|
| `shop.orders` | 24 hours | 電商不一定每小時都有訂單 |
| `crawler.crawl_runs` | 6 hours | Crawler 應該每幾小時跑一次 |
| `crawler.articles` | 12 hours | 有跑就應該有新文章 |
| `rag.documents` | 24 hours | 文件不是每天都新增 |
| `rag.query_logs` | 24 hours | 查詢量看使用者多不多 |

### `EXTRACT(EPOCH FROM ...) / 60`

```sql
NOW() - max(created_at)
→ '03:45:22'::interval

EXTRACT(EPOCH FROM '03:45:22'::interval)
→ 13522.0（秒）

13522.0 / 60
→ 225.4（分鐘）
```

一步步轉換：interval → 秒數 → 分鐘數。

### ❓ 沒有笨問題

**Q：`system_dashboard` 回傳的 `trend_vs_prev` 是正數好還是負數好？**
A：看指標。`orders` 和 `revenue` 的正數 = 成長（好）。`failed_runs` 的正數 = 失敗變多（壞）。`avg_faithfulness` 的正數 = AI 品質提升（好）。你的 Dashboard 應該根據指標名稱決定顏色（綠/紅）。

**Q：Z-score 的 `p_z_threshold` 設多少比較好？**
A：看你的容忍度。2.0 是常見起始值（抓到 ~5% 的異常日）。如果你的 event 量大、波動自然也大，可以調高到 2.5 或 3.0。如果是關鍵指標（營收、錯誤率），可以調低到 1.5 提高敏感度。建議先用 2.0 跑一陣子，看 false positive 比率再調整。

**Q：`data_freshness` 的閾值硬編碼在 SQL 裡，想改怎麼辦？**
A：目前確實是硬編碼。Production 環境可以把閾值抽成參數（加一個 `p_thresholds JSONB` 參數），或存在一張 `analytics.freshness_config` 設定表裡。但作為教學版本，硬編碼更清楚地表達了「不同 entity 有不同期望」的概念。

---

## 五個 Function 的設計模式總結

| Function | 查詢模式 | 核心技巧 |
|----------|---------|---------|
| rag_quality_trend | 時間序列 + 可選過濾 | `GROUP BY date_trunc`, `NULL OR` pattern |
| low_quality_chunks | 多表 JOIN + HAVING | `left()`, `HAVING count(*) >= N` |
| rag_token_usage | 時間序列三部曲 | 同 Chapter 3 |
| crawler_source_ranking | 聚合 + 條件計算 | `FILTER`, `EXTRACT(EPOCH)` |
| crawler_queue_health | 簡單聚合 | `min()` 找最老任務 |
| system_dashboard | Period-over-Period | 隱式 CROSS JOIN, `UNION ALL` |
| detect_anomalies | 統計計算 | Z-score, `abs()`, CROSS JOIN |
| data_freshness | 跨表最新時間 | `UNION ALL`, 每表不同閾值 |

### 🛠️ 動手做

1. 呼叫全域儀表板，看三個域的健康狀態：
   ```sql
   SELECT * FROM analytics.system_dashboard(7);
   ```
2. 跑異常偵測（需要 events 表有足夠資料）：
   ```sql
   SELECT * FROM analytics.detect_anomalies('shop', 'order.created', 30, 2.0);
   ```
3. 檢查資料新鮮度：
   ```sql
   SELECT * FROM analytics.data_freshness();
   ```
4. 思考題：如果 `is_stale = TRUE`，你的自動化系統應該做什麼？（提示：pg_notify + Edge Function）

---

## 本章重點回顧

| 概念 | 學到什麼 |
|------|---------|
| 粒度選擇 | 量少用週/月，量大用天/小時 |
| `NULL OR` pattern | 一個 function 支援「全部」和「過濾」兩種模式 |
| `left(text, n)` | 取前 N 字元做預覽 |
| `HAVING` | 在 GROUP BY 之後過濾，設定統計門檻 |
| `EXTRACT(EPOCH FROM ...)` | interval → 秒數，方便計算 |
| Period-over-Period | current - prev 看趨勢 |
| Z-score | (值 - 平均) / 標準差，\|Z\| > 2 就是異常 |
| `stddev()` | PostgreSQL 內建的標準差函數 |
| 隱式 CROSS JOIN | `FROM table, params` 注入參數 |
| `is_stale` 每表不同閾值 | 不同 entity 有不同的「正常頻率」 |

---

← [Chapter 4 — 漏斗轉換 + Cohort 留存](04_funnel-cohort-analysis.md) | [Chapter 6 — 自動化 + Trigger + RLS + GRANT](06_automation-security.md) →

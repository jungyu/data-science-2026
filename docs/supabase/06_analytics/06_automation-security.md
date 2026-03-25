# Head First 自動化 + Trigger + RLS + GRANT — Chapter 6

> **對應 SQL**：`migrations/005_analytics_schema.sql` 第 915–1296 行
>
> **前置閱讀**：[Chapter 5 — 監控儀表板 + 異常偵測](05_monitoring-anomaly.md)

## 搭配閱讀

| 你在讀的 | SQL 行號 | 學什麼 |
|----------|----------|--------|
| Part 1：build_daily_shop_stats | 922–982 | plpgsql DECLARE、ON CONFLICT UPSERT |
| Part 1：build_daily_crawler_stats | 985–1022 | LANGUAGE SQL snapshot builder |
| Part 1：build_daily_rag_stats | 1025–1066 | 多 subquery 聚合 |
| Part 1：refresh_all + pg_cron | 1069–1107 | PERFORM、format()、排程配置 |
| Part 2：trg_shop_order_event | 1116–1152 | TG_OP、IS DISTINCT FROM、UPDATE OF |
| Part 2：trg_crawl_run_event | 1155–1185 | Crawler trigger 模式 |
| Part 2：trg_rag_query_event | 1188–1211 | INSERT-only trigger |
| Part 3：RLS + Policy | 1217–1246 | DO $$ LOOP 批次建立 policy |
| Part 3：GRANT | 1249–1296 | function 分級授權、%I vs %s |

---

## 你在學什麼？

最後一章收尾三件大事：

1. **Snapshot Builders**：每日自動聚合 + UPSERT 冪等 + pg_cron 排程
2. **Cross-Schema Triggers**：從 shop / crawler / rag 自動推送事件到 analytics
3. **Security**：RLS + Policy + GRANT 三層安全

---

## Part 1：Snapshot Builders — 每日自動聚合

> **📖 SQL 第 915–1107 行**

### 🤔 動腦時間

> 你有 Chapter 1 的三張 `daily_*_stats` snapshot 表。
> 誰負責往裡面填資料？什麼時候填？如果跑了兩次會怎樣？

### 答案：Build function + pg_cron + UPSERT

```
每天 00:15 UTC
    │
    ▼
pg_cron 觸發 analytics.refresh_all()
    │
    ├─→ build_daily_shop_stats(昨天)     → INSERT ... ON CONFLICT DO UPDATE
    ├─→ build_daily_crawler_stats(昨天)  → INSERT ... ON CONFLICT DO UPDATE
    ├─→ build_daily_rag_stats(昨天)      → INSERT ... ON CONFLICT DO UPDATE
    │
    ├─→ REFRESH MATVIEW CONCURRENTLY mv_system_health
    ├─→ REFRESH MATVIEW CONCURRENTLY mv_product_ranking
    └─→ REFRESH MATVIEW CONCURRENTLY mv_source_health
```

---

### 15a. Shop 每日快照產生器

> **📖 SQL 第 922–982 行**

```sql
CREATE OR REPLACE FUNCTION analytics.build_daily_shop_stats(
  p_date DATE DEFAULT CURRENT_DATE - 1
)
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = analytics
AS $$
DECLARE
  v_top_product_id TEXT;
  v_top_product_rev NUMERIC;
BEGIN
  -- 找出當日最暢銷商品
  SELECT oi.product_id, sum(oi.net_revenue)
  INTO v_top_product_id, v_top_product_rev
  FROM shop.order_items oi
  JOIN shop.orders o ON o.id = oi.order_id
  WHERE o.created_at::DATE = p_date
    AND o.status NOT IN ('cancelled', 'refunded')
    AND o.deleted_at IS NULL
  GROUP BY oi.product_id
  ORDER BY sum(oi.net_revenue) DESC
  LIMIT 1;

  INSERT INTO analytics.daily_shop_stats (
    stat_date, total_orders, total_revenue, avg_order_value,
    total_items_sold, new_customers, returning_orders,
    top_product_id, top_product_revenue
  )
  SELECT
    p_date,
    count(*),
    coalesce(sum(total), 0),
    coalesce(avg(total), 0),
    coalesce(sum(num_items_sold), 0),
    (SELECT count(DISTINCT customer_id)
     FROM shop.orders
     WHERE created_at::DATE = p_date AND deleted_at IS NULL
       AND customer_id NOT IN (
         SELECT DISTINCT customer_id FROM shop.orders
         WHERE created_at::DATE < p_date AND deleted_at IS NULL
       )),
    count(*) FILTER (WHERE returning_customer = TRUE),
    v_top_product_id,
    v_top_product_rev
  FROM shop.orders
  WHERE created_at::DATE = p_date
    AND status NOT IN ('cancelled', 'refunded')
    AND deleted_at IS NULL
  ON CONFLICT (stat_date) DO UPDATE SET
    total_orders       = EXCLUDED.total_orders,
    total_revenue      = EXCLUDED.total_revenue,
    avg_order_value    = EXCLUDED.avg_order_value,
    total_items_sold   = EXCLUDED.total_items_sold,
    new_customers      = EXCLUDED.new_customers,
    returning_orders   = EXCLUDED.returning_orders,
    top_product_id     = EXCLUDED.top_product_id,
    top_product_revenue = EXCLUDED.top_product_revenue,
    created_at         = NOW();
END;
$$;
```

### 為什麼用 plpgsql 而不是 SQL？

因為需要 `DECLARE` 變數。先查「最暢銷商品」存進 `v_top_product_id`，再用在 INSERT 裡。

`LANGUAGE SQL` 不支援變數宣告，遇到這種「先查再插」的兩步驟操作，就升級到 `plpgsql`。

### UPSERT — `ON CONFLICT DO UPDATE`

```sql
INSERT INTO analytics.daily_shop_stats (...)
SELECT ...
ON CONFLICT (stat_date) DO UPDATE SET
  total_orders = EXCLUDED.total_orders,
  ...
```

### 🤔 動腦時間

> `EXCLUDED` 是什麼？為什麼不用 `NEW`？

### 答案：`EXCLUDED` 是 INSERT 試圖插入但被 CONFLICT 擋下的那筆 row

```
INSERT 嘗試插入 (stat_date='2024-03-25', total_orders=42, ...)
    │
    ├─ 如果 stat_date='2024-03-25' 不存在 → 正常 INSERT
    │
    └─ 如果已存在 → CONFLICT！
         │
         └─ DO UPDATE SET total_orders = EXCLUDED.total_orders
            （用新值覆蓋舊值）
```

`EXCLUDED` 引用的是「那筆被攔下來的新資料」。`NEW` 是 trigger 用的，這裡不適用。

**冪等性保證**：跑一次 = 插入。跑第二次 = 更新成相同值。跑 N 次 = 結果一樣。所以 pg_cron 重跑不怕。

### 新客戶計算的 subquery

```sql
(SELECT count(DISTINCT customer_id)
 FROM shop.orders
 WHERE created_at::DATE = p_date AND deleted_at IS NULL
   AND customer_id NOT IN (
     SELECT DISTINCT customer_id FROM shop.orders
     WHERE created_at::DATE < p_date AND deleted_at IS NULL
   ))
```

邏輯：「今天下單的客戶」中，排除「今天之前已經下過單的客戶」= 新客戶。

> **效能提醒**：`NOT IN` + subquery 在大表上會慢。production 可以改成 `NOT EXISTS` 或用 `LEFT JOIN ... IS NULL` 模式。但在每日快照（一天的資料量有限）裡夠用。

---

### 15b. Crawler 每日快照

> **📖 SQL 第 985–1022 行**

這個用 `LANGUAGE SQL`（不需要變數），結構更簡潔。

注意 `busiest_source_id` 用 subquery 找：

```sql
(SELECT source_id FROM crawler.crawl_runs
 WHERE created_at::DATE = p_date
 GROUP BY source_id ORDER BY count(*) DESC LIMIT 1)
```

---

### 15c. RAG 每日快照

> **📖 SQL 第 1025–1066 行**

也是 `LANGUAGE SQL`。六個 subquery 分別查不同的 RAG 指標：

```sql
(SELECT count(*) FROM rag.query_logs WHERE created_at::DATE = p_date),
(SELECT count(*) FROM rag.documents WHERE process_status = 'ready'),
(SELECT count(*) FROM rag.documents WHERE created_at::DATE = p_date),
(SELECT count(*) FROM rag.chunks WHERE embedding IS NOT NULL
   AND created_at::DATE = p_date),
...
```

### 🧠 你的大腦在想…

> 「六個 subquery 效率好嗎？為什麼不用 JOIN？」
>
> 因為這些 subquery 各自查不同的表（`query_logs`、`documents`、`chunks`），
> 沒辦法 JOIN 在一起。而且每日快照只跑一次（凌晨），效率不是首要考量。
>
> 可讀性 > 效能，在這個場景下。

---

### 15d. 一鍵刷新所有快照 + MATVIEW

> **📖 SQL 第 1069–1092 行**

```sql
CREATE OR REPLACE FUNCTION analytics.refresh_all(
  p_date DATE DEFAULT CURRENT_DATE - 1
)
RETURNS TEXT
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = analytics
AS $$
BEGIN
  PERFORM analytics.build_daily_shop_stats(p_date);
  PERFORM analytics.build_daily_crawler_stats(p_date);
  PERFORM analytics.build_daily_rag_stats(p_date);

  REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.mv_system_health;
  REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.mv_product_ranking;
  REFRESH MATERIALIZED VIEW CONCURRENTLY analytics.mv_source_health;

  PERFORM analytics.log_event(
    'analytics', 'snapshot.refreshed', 'daily_stats', p_date::TEXT
  );

  RETURN format('analytics.refresh_all(%s) completed', p_date);
END;
$$;
```

### 新技巧

**`PERFORM`**：plpgsql 裡呼叫不需要返回值的 function。等同 `SELECT function(...)` 但丟掉結果。

**`format('... %s ...', p_date)`**：PostgreSQL 的 `sprintf`。比字串拼接 `'...' || p_date::TEXT || '...'` 更可讀。

**自我記錄**：`refresh_all` 最後會把自己的執行結果寫進 `analytics.events`。這樣你可以查「上次 refresh 是什麼時候」。

---

### pg_cron 排程

> **📖 SQL 第 1095–1107 行**

```sql
-- 在 Supabase Dashboard 的 SQL Editor 執行（不是 migration 裡）
SELECT cron.schedule(
  'analytics-daily-refresh',
  '15 0 * * *',              -- 每天 00:15 UTC
  $$SELECT analytics.refresh_all()$$
);

-- 確認排程
SELECT * FROM cron.job;

-- 移除排程
SELECT cron.unschedule('analytics-daily-refresh');
```

**為什麼 00:15 而不是 00:00？** 因為 00:00 可能有其他排程在跑（backup、vacuum 等）。錯開 15 分鐘避免資源競爭。

**為什麼這段是註解？** 因為 `cron.schedule` 是 runtime 操作，不適合放在 migration 裡。Migration 是 DDL（結構），排程是配置。

---

## Part 2：Cross-Schema Triggers

> **📖 SQL 第 1110–1211 行**

### 🤔 動腦時間

> 你有 `analytics.log_event()` function，但誰來呼叫它？
>
> **方案 A**：應用層每次建立訂單時，多一個 API call 去寫 event
>
> **方案 B**：在 `shop.orders` 上建 trigger，INSERT/UPDATE 自動推送
>
> 哪個更可靠？

### 答案：方案 B，trigger 更可靠

應用層可能忘記呼叫、網路斷線、或有其他入口（admin panel、migration script）繞過 API。

Trigger 在資料庫層面保證：**只要 shop.orders 有變化，analytics.events 一定收到通知。**

---

### 16a. Shop 訂單狀態變更

```sql
CREATE OR REPLACE FUNCTION analytics.trg_shop_order_event()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = analytics
AS $$
BEGIN
  IF TG_OP = 'INSERT' THEN
    PERFORM analytics.log_event(
      'shop', 'order.created', 'order', NEW.id, NEW.customer_id,
      jsonb_build_object('total', NEW.total, 'status', NEW.status)
    );
  ELSIF TG_OP = 'UPDATE' AND OLD.status IS DISTINCT FROM NEW.status THEN
    PERFORM analytics.log_event(
      'shop',
      CASE NEW.status
        WHEN 'confirmed'  THEN 'order.paid'
        WHEN 'shipped'    THEN 'order.shipped'
        WHEN 'cancelled'  THEN 'order.cancelled'
        ELSE 'order.created'
      END,
      'order', NEW.id, NEW.customer_id,
      jsonb_build_object(
        'old_status', OLD.status,
        'new_status', NEW.status,
        'total', NEW.total
      )
    );
  END IF;
  RETURN NEW;
END;
$$;
```

### Trigger 的特殊變數

| 變數 | 意思 |
|------|------|
| `TG_OP` | 操作類型：`'INSERT'`, `'UPDATE'`, `'DELETE'` |
| `NEW` | INSERT/UPDATE 後的新 row |
| `OLD` | UPDATE/DELETE 前的舊 row（INSERT 時不存在） |

### `IS DISTINCT FROM` vs `!=`

```sql
OLD.status IS DISTINCT FROM NEW.status
```

| | `!=` | `IS DISTINCT FROM` |
|---|---|---|
| `'a' vs 'b'` | TRUE | TRUE |
| `'a' vs 'a'` | FALSE | FALSE |
| `NULL vs 'a'` | NULL（不是 TRUE！） | TRUE |
| `NULL vs NULL` | NULL | FALSE |

`IS DISTINCT FROM` 是 NULL-safe 的比較。在 trigger 裡 `OLD.status` 可能是 NULL（首次狀態），用 `!=` 會漏掉。

### `jsonb_build_object`

```sql
jsonb_build_object('total', NEW.total, 'status', NEW.status)
→ {"total": 1299.00, "status": "confirmed"}
```

比手寫 JSON 字串安全——自動處理 escaping 和型別轉換。

---

### Trigger 綁定

```sql
DROP TRIGGER IF EXISTS trg_order_analytics ON shop.orders;
CREATE TRIGGER trg_order_analytics
  AFTER INSERT OR UPDATE OF status ON shop.orders
  FOR EACH ROW EXECUTE FUNCTION analytics.trg_shop_order_event();
```

### 新技巧：`UPDATE OF status`

```sql
AFTER INSERT OR UPDATE OF status ON shop.orders
                       ^^^^^^^^^^
```

只有 `status` 欄位變化時才觸發。如果只是更新 `updated_at` 或 `metadata`，trigger 不會跑。這大幅減少不必要的 event 產生。

**`DROP TRIGGER IF EXISTS` 先刪後建**：migration 的冪等性。如果 trigger 已存在，先刪掉再重建，不會報錯。

---

### 16b + 16c. Crawler 和 RAG Trigger

> **📖 SQL 第 1154–1211 行**

結構跟 16a 一樣，只是：

| Trigger | 監聽表 | 監聽事件 | 產生的 event_type |
|---------|--------|---------|------------------|
| trg_order_analytics | shop.orders | INSERT, UPDATE OF status | order.created, order.paid, ... |
| trg_crawl_run_analytics | crawler.crawl_runs | UPDATE OF run_status | crawl.completed, crawl.failed |
| trg_rag_query_analytics | rag.query_logs | INSERT | query.executed |

注意 RAG 只監聽 INSERT（查詢建立後不會改），Crawler 只監聽 UPDATE（run 完成時才有意義的狀態變化）。

---

## Part 3：RLS + Policy + GRANT

> **📖 SQL 第 1214–1296 行**

### 安全三層

```
Layer 1: RLS Enable           ← 開啟 Row Level Security
Layer 2: Policy               ← 定義誰能做什麼
Layer 3: GRANT                ← 授予基礎的 table/function 權限
```

**三層缺一不可**：

- 只有 RLS 沒有 Policy → 所有人被擋住（包括 authenticated）
- 只有 Policy 沒有 RLS → Policy 不生效（形同虛設）
- 只有 GRANT 沒有 RLS → 有權限但沒有行級過濾

---

### Layer 1：RLS Enable

```sql
ALTER TABLE analytics.events ENABLE ROW LEVEL SECURITY;
ALTER TABLE analytics.daily_shop_stats ENABLE ROW LEVEL SECURITY;
ALTER TABLE analytics.daily_crawler_stats ENABLE ROW LEVEL SECURITY;
ALTER TABLE analytics.daily_rag_stats ENABLE ROW LEVEL SECURITY;
ALTER TABLE analytics.funnel_events ENABLE ROW LEVEL SECURITY;
```

### Layer 2：批次建立 Policy

```sql
DO $$
DECLARE
  tbl TEXT;
BEGIN
  FOREACH tbl IN ARRAY ARRAY[
    'events', 'daily_shop_stats', 'daily_crawler_stats',
    'daily_rag_stats', 'funnel_events'
  ]
  LOOP
    EXECUTE format('
      CREATE POLICY "%1$s_select" ON analytics.%1$s
        FOR SELECT TO authenticated USING (TRUE);
      CREATE POLICY "%1$s_service" ON analytics.%1$s
        FOR ALL TO service_role USING (TRUE) WITH CHECK (TRUE);
    ', tbl);
  END LOOP;
END;
$$;
```

### 新技巧：`DO $$ ... LOOP ... EXECUTE format() ...`

這是 PostgreSQL 的**動態 DDL**——用 plpgsql 迴圈批次產生 SQL 語句。

`format('%1$s_select', tbl)` — `%1$s` 引用第 1 個參數（`tbl`），`$s` 表示字串格式。

**為什麼不手寫 10 個 CREATE POLICY？** 因為每張表的 policy 結構完全一樣。手寫容易漏寫一張表。迴圈確保一致性。

### Analytics 的安全模型

| Role | events | daily_*_stats | funnel_events |
|------|--------|---------------|---------------|
| authenticated | SELECT | SELECT | SELECT + INSERT |
| service_role | ALL | ALL | ALL |
| anon | (無) | (無) | (無) |

```sql
-- funnel_events 額外：允許前端推送漏斗事件
CREATE POLICY "funnel_events_insert" ON analytics.funnel_events
  FOR INSERT TO authenticated WITH CHECK (TRUE);
```

**為什麼 events 表不讓 authenticated INSERT？** 因為 events 由 trigger（在 service_role 下執行的 `SECURITY DEFINER` function）寫入。讓前端直接寫 events 會被濫用。

---

### Layer 3：GRANT

```sql
DO $$
DECLARE
  tbl TEXT;
BEGIN
  FOREACH tbl IN ARRAY ARRAY[...] LOOP
    EXECUTE format('GRANT SELECT ON analytics.%I TO authenticated;', tbl);
    EXECUTE format('GRANT ALL ON analytics.%I TO service_role;', tbl);
  END LOOP;
END;
$$;

-- funnel_events: 前端可寫入
GRANT INSERT ON analytics.funnel_events TO authenticated;
```

**`%I` vs `%s`**：`%I` 是 identifier quoting（加雙引號），防止 SQL injection。用在表名、欄位名。`%s` 是字串，用在值。

### Function GRANT

```sql
-- 前端可呼叫的分析函數
GRANT EXECUTE ON FUNCTION analytics.count_events(...) TO authenticated;
GRANT EXECUTE ON FUNCTION analytics.funnel_conversion(...) TO authenticated;
...

-- 只有後端（service_role）能呼叫的管理函數
GRANT EXECUTE ON FUNCTION analytics.build_daily_shop_stats(...) TO service_role;
GRANT EXECUTE ON FUNCTION analytics.refresh_all(...) TO service_role;
```

### 🧠 你的大腦在想…

> 「為什麼 `build_daily_shop_stats` 只給 service_role？」
>
> 因為 snapshot builder 是管理操作，不是用戶操作。
> 如果 authenticated 用戶可以呼叫 `refresh_all()`，
> 他可以瘋狂呼叫來消耗 DB 資源（DoS 攻擊）。
>
> 前端能呼叫的只有「讀取」類的分析函數。

### Materialized View GRANT

```sql
GRANT SELECT ON analytics.mv_system_health TO authenticated;
GRANT SELECT ON analytics.mv_product_ranking TO authenticated;
GRANT SELECT ON analytics.mv_source_health TO authenticated;
```

MATVIEW 的 GRANT 跟 table 一樣。但 MATVIEW 不需要 RLS——它的資料已經是聚合後的，沒有行級敏感資訊。

---

### ❓ 沒有笨問題

**Q：如果 pg_cron 凌晨跑 `refresh_all()` 失敗了，怎麼知道？**
A：`pg_cron` 有自己的 job log：`SELECT * FROM cron.job_run_details ORDER BY start_time DESC LIMIT 10;`。你也可以搭配 `pg_notify` 或 Supabase Edge Function 在失敗時發 Slack 通知。另外，`data_freshness()` function（Chapter 5）也能偵測到——如果 snapshot 沒更新，`is_stale` 就會亮起來。

**Q：為什麼 trigger 用 `AFTER` 不用 `BEFORE`？**
A：`BEFORE` trigger 在 row 寫入之前執行，可以修改 row 或阻止寫入。`AFTER` trigger 在 row 已經寫入之後執行，適合「旁觀記錄」的場景。我們的 analytics trigger 只是記錄事件，不需要干預原始操作，所以用 `AFTER`。

**Q：`DO $$ ... LOOP` 裡的 `EXECUTE format(...)` 為什麼不直接寫 SQL？**
A：因為 `CREATE POLICY` 的表名是動態的（來自 LOOP 變數 `tbl`）。SQL 的 DDL 語句不能用參數綁定（`$1`），只能用字串拼接。`format()` + `%I` 是安全的做法——`%I` 自動加 identifier quoting，防止 SQL injection。

### 🛠️ 動手做

1. 手動執行一次每日快照：
   ```sql
   SELECT analytics.build_daily_shop_stats(CURRENT_DATE - 1);
   SELECT * FROM analytics.daily_shop_stats;
   ```
2. 再跑一次同一天——觀察 UPSERT 的冪等性（不會產生重複 row）
3. 執行全部刷新：
   ```sql
   SELECT analytics.refresh_all(CURRENT_DATE - 1);
   ```
4. 驗證 RLS 是否生效——切換到 `anon` role 嘗試讀取：
   ```sql
   SET ROLE anon;
   SELECT * FROM analytics.events;  -- 應該看不到任何資料
   RESET ROLE;
   ```
5. 查看 events 表裡是否自動多了一筆 `snapshot.refreshed` 事件

---

## 全章回顧：Analytics Schema 的完整畫面

```
                    ┌─────────────────────────────┐
                    │       Security Layer         │
                    │  RLS + Policy + GRANT        │
                    └──────────────┬──────────────┘
                                   │
                    ┌──────────────▼──────────────┐
                    │      Automation Layer        │
                    │  pg_cron → refresh_all()     │
                    │  Triggers → log_event()      │
                    └──────────────┬──────────────┘
                                   │
           ┌───────────────────────┼───────────────────────┐
           │                       │                       │
    ┌──────▼──────┐    ┌───────────▼───────────┐   ┌──────▼──────┐
    │   Storage   │    │      Functions        │   │  MATVIEW    │
    │             │    │                       │   │             │
    │  events     │    │  Time-Series (Ch.3)   │   │  mv_system  │
    │  daily_*    │    │  Funnel (Ch.4)        │   │  mv_product │
    │  funnel_*   │    │  Cohort (Ch.4)        │   │  mv_source  │
    │             │    │  Monitoring (Ch.5)    │   │             │
    │  Ch.1       │    │  Anomaly (Ch.5)       │   │  Ch.2       │
    └─────────────┘    └───────────────────────┘   └─────────────┘
```

| Chapter | 核心概念 | SQL 行號 |
|---------|---------|----------|
| 1 | Event Bus + Daily Snapshots | 29–122 |
| 2 | Materialized View + Funnel Events | 125–239 |
| 3 | Time-Series + generate_series | 242–374 |
| 4 | Funnel Analysis + Cohort Retention | 377–521 |
| 5 | Monitoring + Z-score Anomaly | 524–912 |
| 6 | Snapshot Builders + Triggers + RLS + GRANT | 915–1296 |

---

## 本章重點回顧

| 概念 | 學到什麼 |
|------|---------|
| plpgsql `DECLARE` + `INTO` | 先查再插的兩步驟操作 |
| `ON CONFLICT DO UPDATE` | UPSERT 冪等性，重複執行不產生重複資料 |
| `EXCLUDED` | 引用被 CONFLICT 攔下的新資料 |
| `PERFORM` | plpgsql 裡呼叫不需要返回值的 function |
| `format()` | PostgreSQL 的 sprintf，比字串拼接更可讀 |
| `TG_OP`, `NEW`, `OLD` | Trigger 的特殊變數 |
| `IS DISTINCT FROM` | NULL-safe 的比較運算子 |
| `UPDATE OF column` | 只在特定欄位變化時觸發 trigger |
| `jsonb_build_object` | 安全地建構 JSONB |
| `DO $$ ... LOOP` | 動態 DDL，批次建立 Policy/GRANT |
| `%I` vs `%s` | identifier quoting vs string formatting |
| 安全三層 | RLS enable + Policy + GRANT 缺一不可 |
| function GRANT 分級 | 讀取函數給 authenticated，管理函數給 service_role |

---

## 恭喜完成！

你已經從頭到尾理解了 `005_analytics_schema.sql` 的 1,296 行 SQL。

學會了什麼：
- **資料建模**：Event Bus、Snapshot、MATVIEW、Funnel 四種儲存模式
- **SQL 分析**：時間序列、漏斗、Cohort、Z-score 四種分析技巧
- **自動化**：pg_cron + Trigger + UPSERT 的生產級自動化
- **安全**：SECURITY DEFINER + RLS + GRANT 的三層防護

**下一步建議**：
1. 在 Supabase Studio 裡跑 `005_analytics_schema.sql`
2. 插入一些測試資料（`012_seed_data.sql`）
3. 呼叫 `analytics.system_dashboard(7)` 看效果
4. 試著修改 `detect_anomalies` 加入星期幾的分組邏輯

---

← [Chapter 5 — 監控儀表板 + 異常偵測](05_monitoring-anomaly.md) | [返回目錄](00_README.md) →

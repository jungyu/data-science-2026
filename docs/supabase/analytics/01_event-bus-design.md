# Head First 事件匯流排 + 每日快照 — Chapter 1

> **對應 SQL**：`migrations/005_analytics_schema.sql` 第 29–121 行
>
> **閱讀方式**：這不是 API 文件。請從頭讀到尾，跟著「動腦時間」思考，
> 答案就在下一段。跳著讀會少掉 80% 的收穫。

---

## 搭配閱讀

| 你在讀的 | SQL 行號 | 學什麼 |
|----------|----------|--------|
| Part 1：Event Log | 29–62 | Append-only 事件表、regex CHECK、GIN index |
| Part 2：Shop 每日快照 | 65–87 | NUMERIC 金額、UNIQUE UPSERT、snapshot 設計 |
| Part 2：Crawler 每日快照 | 89–104 | NULL vs DEFAULT 0 的語意差異 |
| Part 2：RAG 每日快照 | 106–121 | FLOAT8 vs NUMERIC 型別選擇、BIGINT token 計數 |

---

## 你在蓋什麼？

想像你是一家公司的 CTO。手下有三個團隊：

- **Shop 團隊**：管訂單、商品、金流
- **Crawler 團隊**：管新聞抓取、來源健康度
- **RAG 團隊**：管文件索引、語意搜尋、AI 品質

每個團隊都有自己的資料庫 schema，各過各的。

某天老闆問：「**昨天系統整體狀況如何？**」

你要怎麼回答？

```
方案 A：開三個 SQL tab，各跑一次查詢，用 Excel 拼在一起
方案 B：建一個觀測層，一個 function call 搞定
```

我們要蓋的就是方案 B。

```
┌──────────┐  ┌──────────┐  ┌──────────┐
│  shop    │  │ crawler  │  │   rag    │
│  訂單事件 │  │ 爬蟲完成 │  │ 查詢記錄 │
└────┬─────┘  └────┬─────┘  └────┬─────┘
     │             │             │
     │   trigger   │   trigger   │   trigger
     │             │             │
     └─────────────┼─────────────┘
                   ▼
        ┌─────────────────────┐
        │  analytics.events   │  ← 統一事件匯流排
        │  (append-only)      │
        └─────────────────────┘
                   │
                   │  pg_cron 每日聚合
                   ▼
        ┌─────────────────────┐
        │  daily_*_stats      │  ← 每日快照（保留歷史）
        └─────────────────────┘
```

---

## Part 1：Event Log — 統一事件匯流排

> **📖 SQL 第 29–62 行**

### 🤔 動腦時間

> 你要記錄「shop 有一筆新訂單」和「crawler 完成一次抓取」這兩種事件。
>
> **方案 A**：在 analytics schema 裡建兩張表 —— `shop_events` 和 `crawler_events`
>
> **方案 B**：建一張統一的 `events` 表，用欄位區分來源
>
> 先想 30 秒：如果未來加了第四個 schema（比如 `cms`），哪種方案改動最小？

### 答案：選 B，統一事件表

```sql
CREATE TABLE IF NOT EXISTS analytics.events (
  id            TEXT PRIMARY KEY DEFAULT public.generate_ulid(),
  schema_name   TEXT        NOT NULL,     -- 'shop', 'crawler', 'rag'
  event_type    TEXT        NOT NULL,     -- 'order.created', 'crawl.completed'
  entity_type   TEXT        NOT NULL,     -- 'order', 'crawl_run'
  entity_id     TEXT,                     -- 關聯到來源表的 PK
  actor_id      TEXT,                     -- 誰觸發的
  payload       JSONB       NOT NULL DEFAULT '{}'::JSONB,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

**為什麼只有一張表？**

| 多表方案 | 統一表方案 |
|---------|----------|
| 新增 schema → 新增表 + 新索引 + 新 RLS | 新增 schema → 多一個 `schema_name` 值 |
| 跨域查詢要 `UNION ALL` 多張表 | 一個 `WHERE schema_name = ...` |
| 每張表的結構可能微妙不同 | 結構統一，`payload` JSONB 彈性擴充 |

### Append-only 的紀律

注意這張表**沒有** `updated_at`。這是刻意的。

```
規矩：events 表永遠只 INSERT，絕不 UPDATE、絕不 DELETE。
```

為什麼？因為事件是**已發生的事實**。訂單建立了就是建立了。你不會回去改「2024 年 3 月 5 日那筆訂單其實沒建立」。

這叫 **append-only log**（僅追加日誌），跟 Kafka 的 topic、銀行的帳本是同一個概念。

### 🧠 你的大腦在想…

> 「那 payload 裡面放什麼？為什麼不把資料打平成欄位？」
>
> 因為每種事件的附帶資料不同。訂單事件帶 `total` 和 `status`，
> 爬蟲事件帶 `articles_extracted` 和 `error_count`。
> 如果全打平，你會有 50 個 nullable 欄位，大部分永遠是 NULL。
>
> JSONB 讓你「結構化但彈性」。而且 PostgreSQL 的 GIN index
> 可以索引 JSONB 內的 key，查詢速度不差。

---

### CHECK Constraint — DB 層的資料衛兵

> **📖 SQL 第 47–51 行**

```sql
-- schema_name: 允許已知 schema + 未來擴充
CONSTRAINT ck_events_schema
  CHECK (schema_name ~ '^[a-z_]+$'),

-- event_type: 格式為 entity.action（例如 order.created）
CONSTRAINT ck_events_type
  CHECK (event_type ~ '^[a-z_]+\.[a-z_]+$')
```

### 🤔 動腦時間

> 為什麼 `ck_events_schema` 不寫成 `CHECK (schema_name IN ('shop', 'crawler', 'rag'))`？
>
> 那樣不是更嚴格嗎？

### 答案：擴充性

如果用硬編碼的 `IN` 列表，每次新增 schema 就要跑 `ALTER TABLE ... DROP CONSTRAINT` + `ADD CONSTRAINT`。在有幾百萬筆資料的表上改 CHECK constraint 不是開玩笑的。

用 regex `'^[a-z_]+$'` 是一個聰明的折衷：
- 防止垃圾資料（空字串、特殊字元、大寫混入）
- 不用改 constraint 就能支援新 schema
- `event_type` 的 `'^[a-z_]+\.[a-z_]+$'` 強制 `entity.action` 格式，命名規範靠 DB 守護

> **命名規範**：Named constraint（`ck_events_schema`）而非匿名 CHECK。
> 出錯時錯誤訊息會顯示 constraint 名稱，debug 快 10 倍。

---

### Index 策略 — 想清楚你的查詢模式

> **📖 SQL 第 54–62 行**

```sql
-- 1. 按 schema + event_type + 時間排序查詢
CREATE INDEX idx_events_schema_type
  ON analytics.events(schema_name, event_type, created_at DESC);

-- 2. 按 entity 查詢（找某個訂單的所有事件）
CREATE INDEX idx_events_entity
  ON analytics.events(entity_type, entity_id)
  WHERE entity_id IS NOT NULL;    -- ← partial index

-- 3. 按時間排序（最新事件）
CREATE INDEX idx_events_created
  ON analytics.events(created_at DESC);

-- 4. JSONB payload 全文搜尋
CREATE INDEX idx_events_payload
  ON analytics.events USING GIN(payload);
```

四個 index，四種查詢模式：

| Index | 服務的查詢 | 為什麼這樣設計 |
|-------|----------|--------------|
| `idx_events_schema_type` | 「show 過去 7 天的 `order.created` 事件」 | 複合索引，三欄位都在 WHERE/ORDER |
| `idx_events_entity` | 「找訂單 `01HXY...` 的所有事件」 | Partial index 排除 NULL，省空間 |
| `idx_events_created` | 「最新 100 筆事件」 | 單欄 DESC，倒序掃描最快 |
| `idx_events_payload` | 「payload 裡有 `error_count > 5` 的事件」 | GIN 索引支援 JSONB 操作符 |

### ❓ 沒有笨問題

**Q：Partial index 是什麼？**
A：就是加了 `WHERE` 條件的 index。只有符合條件的 row 才會進 index。
`entity_id` 有時候是 NULL（系統事件沒有對應的 entity），這些 row 不需要被索引。
Partial index 讓索引更小、INSERT 更快。

**Q：GIN index 跟普通 B-Tree 差在哪？**
A：B-Tree 索引一個「值」，GIN（Generalized Inverted Index）索引多個「元素」。
JSONB 裡面有多個 key-value pair，GIN 會把每個 key 都建進索引裡。
所以你可以用 `payload @> '{"status": "cancelled"}'` 來查詢，而且有 index 加速。

---

## Part 2：Daily Snapshots — 為什麼不用 Materialized View 就好？

> **📖 SQL 第 65–121 行**

### 🤔 動腦時間

> 你想看「過去 30 天每天的訂單數和營收」。有兩種做法：
>
> **方案 A**：建一個 Materialized View，每天 REFRESH，它會自動重新計算
>
> **方案 B**：建一張 snapshot table，每天用 function 往裡面 INSERT 一筆聚合
>
> 哪個可以做「上個月 vs 上上個月的營收趨勢比較」？

### 答案：只有方案 B 可以

```
Materialized View REFRESH 的問題：

  Day 1:  今日訂單=50   ← REFRESH → MATVIEW 顯示 50
  Day 2:  今日訂單=80   ← REFRESH → MATVIEW 顯示 80（Day 1 的資料被覆蓋）
  Day 30: 你想看 Day 1 的數據…… 🤷 已經不見了
```

```
Snapshot Table 的做法：

  Day 1:  INSERT (stat_date='2024-03-01', total_orders=50)
  Day 2:  INSERT (stat_date='2024-03-02', total_orders=80)
  Day 30: SELECT * WHERE stat_date BETWEEN '2024-03-01' AND '2024-03-30'
          → 完整 30 天趨勢 ✅
```

**Materialized View 適合「當前狀態」，Snapshot Table 適合「歷史趨勢」。**

> 我們兩個都用。MATVIEW 給即時儀表板（Chapter 2），Snapshot 給趨勢分析（這裡）。

---

### Shop 每日快照

> **📖 SQL 第 72–87 行**

```sql
CREATE TABLE IF NOT EXISTS analytics.daily_shop_stats (
  id              TEXT PRIMARY KEY DEFAULT public.generate_ulid(),
  stat_date       DATE        NOT NULL,
  total_orders    INTEGER     NOT NULL DEFAULT 0,
  total_revenue   NUMERIC(14,2) NOT NULL DEFAULT 0,
  avg_order_value NUMERIC(12,2) NOT NULL DEFAULT 0,
  total_items_sold INTEGER    NOT NULL DEFAULT 0,
  new_customers   INTEGER     NOT NULL DEFAULT 0,
  returning_orders INTEGER    NOT NULL DEFAULT 0,
  top_product_id  TEXT,
  top_product_revenue NUMERIC(12,2),
  metadata        JSONB       NOT NULL DEFAULT '{}'::JSONB,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  CONSTRAINT uq_daily_shop_stats_date UNIQUE (stat_date)
);
```

**關鍵設計決策：**

| 決策 | 原因 |
|------|------|
| `NUMERIC(14,2)` 而非 `FLOAT` | 金額不能有浮點誤差。`14,2` 最大支援 999,999,999,999.99 |
| `UNIQUE (stat_date)` | 確保每天只有一筆快照。同時是 `ON CONFLICT` UPSERT 的基礎 |
| `metadata JSONB` | 預留欄位。如果未來要加「退款金額」「優惠券使用數」，不用改表結構 |
| `DEFAULT 0` | 沒有資料的日子也要有 record（全零），趨勢圖才不會斷 |

### 🧠 你的大腦在想…

> 「為什麼 `stat_date` 是 `DATE` 不是 `TIMESTAMPTZ`？」
>
> 因為這是**日級**聚合。一天只有一筆。用 `DATE` 省空間（4 bytes vs 8 bytes），
> 而且 `UNIQUE` constraint 比較的是日期不是時間，更直覺。

---

### Crawler 每日快照

> **📖 SQL 第 89–104 行**

```sql
CREATE TABLE IF NOT EXISTS analytics.daily_crawler_stats (
  id                  TEXT PRIMARY KEY DEFAULT public.generate_ulid(),
  stat_date           DATE        NOT NULL,
  total_runs          INTEGER     NOT NULL DEFAULT 0,
  successful_runs     INTEGER     NOT NULL DEFAULT 0,
  failed_runs         INTEGER     NOT NULL DEFAULT 0,
  pages_fetched       INTEGER     NOT NULL DEFAULT 0,
  articles_extracted  INTEGER     NOT NULL DEFAULT 0,
  error_count         INTEGER     NOT NULL DEFAULT 0,
  avg_run_duration_s  NUMERIC(10,2),
  busiest_source_id   TEXT,
  metadata            JSONB       NOT NULL DEFAULT '{}'::JSONB,
  created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  CONSTRAINT uq_daily_crawler_stats_date UNIQUE (stat_date)
);
```

注意 `avg_run_duration_s` 沒有 `DEFAULT 0`——如果當天沒有任何 crawl run，平均時長應該是 `NULL` 而非 `0`。`0` 表示「有跑但瞬間完成」，`NULL` 表示「根本沒跑」。語意不同。

---

### RAG 每日快照

> **📖 SQL 第 106–121 行**

```sql
CREATE TABLE IF NOT EXISTS analytics.daily_rag_stats (
  id                    TEXT PRIMARY KEY DEFAULT public.generate_ulid(),
  stat_date             DATE        NOT NULL,
  total_queries         INTEGER     NOT NULL DEFAULT 0,
  total_documents       INTEGER     NOT NULL DEFAULT 0,
  new_documents         INTEGER     NOT NULL DEFAULT 0,
  chunks_embedded       INTEGER     NOT NULL DEFAULT 0,
  avg_faithfulness      FLOAT8,
  avg_answer_relevance  FLOAT8,
  avg_context_precision FLOAT8,
  total_prompt_tokens   BIGINT      NOT NULL DEFAULT 0,
  total_completion_tokens BIGINT    NOT NULL DEFAULT 0,
  metadata              JSONB       NOT NULL DEFAULT '{}'::JSONB,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  CONSTRAINT uq_daily_rag_stats_date UNIQUE (stat_date)
);
```

### 🤔 動腦時間

> 為什麼 `avg_faithfulness` 用 `FLOAT8` 而 `total_revenue` 用 `NUMERIC(14,2)`？

### 答案：精度需求不同

- **營收**是錢——差 0.01 就是差一分錢。必須用精確的 `NUMERIC`。
- **faithfulness** 是 AI 評估分數——0.8523 和 0.8524 沒有實質差異。`FLOAT8`（雙精度浮點）夠用，而且計算效率更高。

> **規律**：金額用 `NUMERIC`，分數 / 評分用 `FLOAT8`，計數用 `INTEGER` / `BIGINT`。

---

### ❓ 沒有笨問題

**Q：為什麼 snapshot table 沒有 `updated_at`？**
A：Snapshot 是「快照」，代表某一天的聚合結果。如果需要修正，用 UPSERT 覆蓋整筆（Chapter 6 會教）。`updated_at` 暗示「部分更新」，在 snapshot 語境下語意不對。

**Q：如果某天完全沒有訂單，daily_shop_stats 會有那天的 record 嗎？**
A：不會自動產生。Chapter 6 的 snapshot builder function 只在有資料時 INSERT。如果你的趨勢圖需要零值日期，要在 application 層用 `generate_series` 補零（Chapter 3 會教這個技巧）。

---

### 三張表的共同設計模式

回頭看，三張 snapshot table 都遵循相同的模式：

```
┌─────────────────────────────────────────────┐
│  daily_*_stats 共同模式                       │
│                                             │
│  id          TEXT PK (ULID)                 │
│  stat_date   DATE UNIQUE    ← UPSERT 的 key │
│  [聚合欄位]   各自不同                        │
│  metadata    JSONB          ← 彈性擴充       │
│  created_at  TIMESTAMPTZ                    │
│                                             │
│  沒有 updated_at（snapshot 是快照，不該修改）    │
│  沒有 project_id（analytics 是全域的）         │
└─────────────────────────────────────────────┘
```

**為什麼沒有 `project_id`？** 因為 analytics 是跨域的觀測層。它看的是整個系統的健康狀況，不是單一租戶。如果需要租戶級分析，在各自的 schema 裡做，不要在觀測層混入業務邏輯。

---

### 🛠️ 動手做

1. 在 SQL Editor 裡執行 `005_analytics_schema.sql` 的第 36–62 行（events 表 + 索引）
2. 手動插入一筆事件：
   ```sql
   INSERT INTO analytics.events (schema_name, event_type, entity_type, payload)
   VALUES ('shop', 'order.created', 'order', '{"total": 999}');
   ```
3. 試試看故意違反 CHECK constraint：
   ```sql
   INSERT INTO analytics.events (schema_name, event_type, entity_type)
   VALUES ('SHOP', 'order.created', 'order');  -- 大寫會怎樣？
   ```
4. 查詢 GIN index 是否生效：
   ```sql
   EXPLAIN ANALYZE
   SELECT * FROM analytics.events
   WHERE payload @> '{"total": 999}';
   ```

---

## 本章重點回顧

| 概念 | 學到什麼 |
|------|---------|
| 統一事件表 | 一張 `events` 表 + `schema_name` 區分來源，比多張表更好擴充 |
| Append-only | 事件是已發生的事實，永不修改、永不刪除 |
| Regex CHECK | `'^[a-z_]+\.[a-z_]+$'` 比 `IN (...)` 更好擴充 |
| Partial index | `WHERE entity_id IS NOT NULL` 讓索引更小、INSERT 更快 |
| GIN on JSONB | 支援 `@>` 操作符的全文搜尋 |
| Snapshot vs MATVIEW | MATVIEW 給「當前」，Snapshot 給「歷史趨勢」 |
| 型別選擇 | 金額 `NUMERIC`，分數 `FLOAT8`，計數 `INTEGER` |
| UNIQUE (stat_date) | UPSERT 的基礎，一天一筆 |

---

← [00_README.md](00_README.md) | [Chapter 2 — Materialized View + 漏斗追蹤](02_matview-and-funnel.md) →

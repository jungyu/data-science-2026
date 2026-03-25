# Head First Analytics — 跨域觀測與商業智慧

> **"你不能改善你無法衡量的東西。但如果衡量工具本身太複雜，你根本不會去用。"**

歡迎來到 Analytics Schema 教學。我們要用 6 個 Chapter，學會怎麼在 PostgreSQL 裡蓋出一個**跨域觀測層**——一個 function call，三個領域（shop / crawler / rag）的數據一次到位。

不是玩具 Dashboard。是你真的可以拿去接 pg_cron、跑 Z-score 異常偵測、做月份 cohort 留存分析的那種。

---

## 這份指南適合誰？

你如果符合以下任一條件，這份指南就是為你寫的：

- 有 shop / crawler / rag 三個 schema，但老闆問「今天生意如何？」你要開三個 tab
- 聽過 Materialized View 但不確定跟普通 View 差在哪
- 想學 SQL 分析技巧：時間序列、漏斗分析、cohort 留存、Z-score 異常偵測
- 想把每日聚合快照自動化（pg_cron + UPSERT）

---

## 搭配檔案

| 檔案 | 用途 |
|------|------|
| [`005_analytics_schema.sql`](../migrations/005_analytics_schema.sql) | 完整可執行的 SQL schema（v1.0, 1,296 行） |
| [`01_event-bus-design.md`](01_event-bus-design.md) | Chapter 1：Event Log + Daily Snapshots |
| [`02_matview-and-funnel.md`](02_matview-and-funnel.md) | Chapter 2：Materialized View + 漏斗追蹤 |
| [`03_time-series-aggregation.md`](03_time-series-aggregation.md) | Chapter 3：時間序列聚合函數 |
| [`04_funnel-cohort-analysis.md`](04_funnel-cohort-analysis.md) | Chapter 4：漏斗轉換 + Cohort 留存 |
| [`05_monitoring-anomaly.md`](05_monitoring-anomaly.md) | Chapter 5：監控儀表板 + Z-score 異常偵測 |
| [`06_automation-security.md`](06_automation-security.md) | Chapter 6：自動化 + Trigger + RLS + GRANT |

**使用方式**：邊讀章節，邊打開 `.sql` 檔案對照。每個 Chapter 都標註了對應的 SQL 行號。

> **重要**：所有表和函數都建在 `analytics` schema 底下。這個 schema 是**觀測層**——不存原始資料，只存聚合、事件、快照。

---

## 全景地圖

先看大局。整個 analytics schema 分成 6 層概念：

```
Chapter 1   Event Bus          ── 統一事件匯流排（append-only）
            Daily Snapshots    ── 每日聚合快照（shop / crawler / rag）

Chapter 2   Materialized Views ── 即時儀表板快取（跨 schema JOIN）
            Funnel Events      ── 購買漏斗追蹤

Chapter 3   Time-Series        ── generate_series 時間軸 + 營收趨勢

Chapter 4   Funnel Analysis    ── 漏斗轉換率 + 流失率
            Cohort Retention   ── 月份世代留存分析

Chapter 5   Monitoring         ── RAG 品質 / Crawler 健康 / 全域儀表板
            Anomaly Detection  ── Z-score 統計異常偵測 + 資料新鮮度

Chapter 6   Automation         ── Snapshot builders + pg_cron
            Security           ── Trigger 事件推送 + RLS + GRANT
```

它們的依賴關係長這樣：

```
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   shop       │  │  crawler     │  │    rag       │
│  (orders,    │  │  (crawl_runs,│  │  (query_logs,│
│   products)  │  │   sources)   │  │   chunks)    │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                 │                 │
       └─────────────────┼─────────────────┘
                         │
              ┌──────────▼──────────┐
              │  analytics schema   │
              │                     │
              │  events (事件匯流排) │ ← trigger 自動推送
              │  daily_*_stats      │ ← pg_cron 每日快照
              │  funnel_events      │ ← 前端推送
              │  mv_* (MATVIEW)     │ ← 跨 schema JOIN
              │  14 functions       │ ← SQL 分析技巧
              └─────────────────────┘
```

---

## 設計原則速查表

| # | 原則 | 做法 |
|---|------|------|
| 1 | 觀測層不存原始資料 | 只存聚合、事件、快照；原始資料在各自的 schema |
| 2 | Append-only Event Log | `events` 表永遠不 UPDATE / DELETE，只 INSERT |
| 3 | Snapshot 保留歷史 | MATVIEW 會整張重建丟歷史；snapshot table 保留每天的快照 |
| 4 | UPSERT 冪等性 | snapshot builder 用 `ON CONFLICT DO UPDATE`，重複執行不產生重複資料 |
| 5 | SECURITY DEFINER | 所有跨 schema 函數都用 `SECURITY DEFINER` + `SET search_path` |
| 6 | 後端為主的安全模型 | authenticated 只能 SELECT；寫入靠 trigger / service_role |
| 7 | PK 一致性 | `TEXT DEFAULT public.generate_ulid()` — 與其他 schema 一致 |
| 8 | pg_cron 驅動自動化 | 每日快照 + MATVIEW REFRESH 由排程完成 |

---

## SQL 技巧索引

這份教學涵蓋的 PostgreSQL / SQL 分析技巧一覽：

| 技巧 | 章節 | SQL 行號 | 用在哪 |
|------|------|----------|--------|
| Append-only + regex CHECK | Ch.1 | 36–62 | Event Log 設計 |
| GIN index on JSONB | Ch.1 | 62 | 事件 payload 查詢 |
| UNIQUE constraint for UPSERT | Ch.1 | 86, 103, 121 | 每日快照去重 |
| `WITH NO DATA` + `REFRESH CONCURRENTLY` | Ch.2 | 161–239 | Materialized View |
| 跨 schema subquery | Ch.2 | 161–180 | 系統健康總覽 |
| `FILTER (WHERE ...)` 條件聚合 | Ch.2 | 215–216 | 來源健康度 |
| `generate_series` 完整時間軸 | Ch.3 | 308–329 | 時間序列（含零值日期） |
| `date_trunc` 多粒度聚合 | Ch.3 | 296, 317 | hour / day / week / month |
| `LAG` window function | Ch.4 | 451 | 漏斗流失率 |
| `CROSS JOIN` 基準值 | Ch.4 | 418 | 漏斗轉換率 |
| CTE + `date_trunc` 分群 | Ch.4 | 486–521 | Cohort 留存分析 |
| `EXTRACT(EPOCH FROM ...)` | Ch.5 | 689, 887 | 執行時間計算 |
| Z-score 統計方法 | Ch.5 | 813–863 | 異常偵測 |
| `UNION ALL` 跨域合併 | Ch.5 | 728–805 | 全域儀表板 |
| plpgsql `DECLARE` + `INTO` | Ch.6 | 930–944 | Snapshot builder |
| `ON CONFLICT DO UPDATE` | Ch.6 | 971–980 | UPSERT 冪等 |
| `AFTER INSERT OR UPDATE OF` trigger | Ch.6 | 1150–1152 | 欄位級 trigger |
| `DO $$ ... LOOP` 動態 DDL | Ch.6 | 1225–1242 | 批次建立 RLS policy |

---

## 前置要求

- 已**依序**執行以下 migration（順序很重要）：
  1. `001_extensions.sql` — schema 建立 + `generate_ulid` function
  2. `002_shop_schema.sql` — shop schema 完整表結構
  3. `003_crawler_schema.sql` — crawler schema 完整表結構
  4. `004_rag_schema.sql` — rag schema 完整表結構
- Docker 跑著（`supabase start`）
- 瀏覽器打開 Studio `http://localhost:54323`

> **migration 依賴警告**：`005_analytics_schema.sql` 的 MATVIEW 和 trigger 直接引用
> `shop.orders`、`shop.products`、`crawler.crawl_runs`、`rag.query_logs` 等表。
> 請先跑完 001–004 的完整 migration，再執行 005。

---

## 參考資源

- **Schema SQL**：[`005_analytics_schema.sql`](../migrations/005_analytics_schema.sql)
- **Studio 實操教學**：[`../studio/07_analytics-and-matview.md`](../studio/07_analytics-and-matview.md) — 用 Studio 跑 analytics 的操作指南
- **Supabase 設計規範**：`../../agent-init/skills/supabase/` 目錄

# Head First Crawler API — 爬蟲控制台

> **"爬蟲跑得好不好，你不用去看 log。打一個 API 就知道。"**

這份指南涵蓋 [`006_public_api.sql`](../migrations/006_public_api.sql) 的 **第 348–447 行**——
3 個 Crawler API function。全部都是 **authenticated only**。

---

## 搭配閱讀

| 你在讀的 | SQL 行號 | 學什麼 |
|----------|----------|--------|
| 爬蟲統計總覽 | 353–375 | 多表 count 子查詢 |
| 最新文章列表 | 378–414 | 可選過濾 + tags JSON |
| 來源健康度 | 417–447 | FILTER 子句 + 成功率計算 |

---

## 1. `api_crawler_stats` — 爬蟲統計總覽

> **📖 SQL 第 353–375 行**

一個 API 拿到整個爬蟲系統的健康快照。適合放在管理後台的首頁卡片。

### 參數

無。

### 回傳欄位

| 欄位 | 型別 | 說明 |
|------|------|------|
| `total_sources` | BIGINT | 全部來源數 |
| `active_sources` | BIGINT | 啟用中的來源數 |
| `total_articles` | BIGINT | 全部文章數 |
| `runs_today` | BIGINT | 今天跑了幾次 |
| `failed_today` | BIGINT | 今天失敗幾次 |
| `queue_pending` | BIGINT | 佇列中待處理數 |

### 前端呼叫

```ts
const { data } = await supabase.rpc('api_crawler_stats')

// data[0] →
// {
//   total_sources: 15,
//   active_sources: 12,
//   total_articles: 48230,
//   runs_today: 36,
//   failed_today: 2,
//   queue_pending: 5
// }
```

### 裡面在幹嘛？

```sql
SELECT
  (SELECT count(*) FROM crawler.sources),
  (SELECT count(*) FROM crawler.sources WHERE is_enabled = TRUE),
  (SELECT count(*) FROM crawler.articles),
  (SELECT count(*) FROM crawler.crawl_runs WHERE created_at >= CURRENT_DATE),
  (SELECT count(*) FROM crawler.crawl_runs
   WHERE created_at >= CURRENT_DATE AND run_status = 'failed'),
  (SELECT count(*) FROM crawler.crawl_queue WHERE status = 'pending');
```

6 個獨立的 scalar subquery，各自去不同的 table count 一下。
沒有 FROM、沒有 JOIN——因為每個數字來自不同的表，沒有共同的 JOIN 條件。

> ### 🧠 你的大腦在想…
>
> 「6 個 subquery 不會很慢嗎？」
>
> 每個都是簡單的 `count(*)` 搭配 index 過濾。
> `crawl_runs.created_at` 和 `crawl_queue.status` 應該有 index，
> 所以每個 subquery 都是 index scan，不是 seq scan。
> 6 個加起來通常 <10ms。
>
> 如果資料量大到效能不行，可以用 materialized view 或快取。
> 但在百萬級以下，這個寫法完全夠用。

---

## 2. `api_crawler_latest_articles` — 最新文章列表

> **📖 SQL 第 378–414 行**

列出已發布的文章，可選擇只看特定來源。

### 參數

| 參數 | 型別 | 預設值 | 說明 |
|------|------|--------|------|
| `p_source_code` | TEXT | NULL | 來源代碼（NULL = 全部） |
| `p_limit` | INTEGER | 20 | 每頁幾筆 |
| `p_offset` | INTEGER | 0 | 跳過幾筆 |

### 回傳欄位

| 欄位 | 型別 | 說明 |
|------|------|------|
| `id` | TEXT | 文章 ULID |
| `title` | TEXT | 文章標題 |
| `source_name` | TEXT | 來源名稱 |
| `source_url` | TEXT | 原始網址 |
| `author_name` | TEXT | 作者 |
| `published_at` | TIMESTAMPTZ | 發布時間 |
| `abstract` | TEXT | 摘要（截斷至 300 字） |
| `tags` | JSONB | 標籤陣列 `["AI", "Machine Learning"]` |

### 前端呼叫

```ts
// 全部來源的最新文章
const { data } = await supabase.rpc('api_crawler_latest_articles')

// 只看特定來源
const { data } = await supabase.rpc('api_crawler_latest_articles', {
  p_source_code: 'techcrunch',
  p_limit: 10,
  p_offset: 0
})
```

### 三個值得注意的技巧

**1. 可選過濾（Optional Filter）**

```sql
WHERE a.is_published = TRUE AND a.is_available = TRUE
  AND (p_source_code IS NULL OR s.code = p_source_code)
```

`(p_source_code IS NULL OR s.code = p_source_code)` 這個模式：
- 傳 NULL → 條件恆為 TRUE → 不過濾（顯示全部）
- 傳值 → 按那個值過濾

這是 SQL 裡「可選參數」的標準寫法。一個 function 就能同時處理「全部」和「特定來源」兩種需求。

**2. 摘要截斷**

```sql
left(a.abstract, 300) AS abstract
```

`left()` 截取前 300 個字元。列表頁不需要完整摘要，省頻寬。

**3. Tags JSON 子查詢**

```sql
coalesce((
  SELECT jsonb_agg(t.name)
  FROM crawler.article_tags at
  JOIN crawler.tags t ON t.id = at.tag_id
  WHERE at.article_id = a.id
), '[]'::JSONB) AS tags
```

透過多對多中間表 `article_tags` 抓出所有 tag name，聚合成 JSON array。
`coalesce(..., '[]')` 確保沒有 tag 時回傳空陣列而不是 NULL。

---

## 3. `api_crawler_source_health` — 各來源健康度

> **📖 SQL 第 417–447 行**

這是爬蟲管理最重要的 API。一次看到所有來源的健康狀況——過去 7 天的成功率、文章數、最後執行時間。

### 參數

無。

### 回傳欄位

| 欄位 | 型別 | 說明 |
|------|------|------|
| `source_code` | TEXT | 來源代碼 |
| `source_name` | TEXT | 來源名稱 |
| `is_enabled` | BOOLEAN | 是否啟用 |
| `total_runs_7d` | BIGINT | 近 7 天執行次數 |
| `success_rate_pct` | NUMERIC | 成功率 %（1 位小數） |
| `articles_7d` | BIGINT | 近 7 天抓到的文章數 |
| `last_run_at` | TIMESTAMPTZ | 最後一次完成時間 |

### 前端呼叫

```ts
const { data } = await supabase.rpc('api_crawler_source_health')

// data →
// [
//   { source_code: 'techcrunch', source_name: 'TechCrunch',
//     is_enabled: true, total_runs_7d: 21, success_rate_pct: 95.2,
//     articles_7d: 156, last_run_at: '2026-03-26T...' },
//   { source_code: 'ithome', source_name: 'iThome',
//     is_enabled: true, total_runs_7d: 14, success_rate_pct: 100.0,
//     articles_7d: 89, last_run_at: '2026-03-26T...' },
//   ...
// ]
```

### 成功率計算拆解

```sql
CASE WHEN count(cr.id) = 0 THEN 0
     ELSE round(
       count(cr.id) FILTER (WHERE cr.run_status = 'success')::NUMERIC
       / count(cr.id) * 100, 1)
END AS success_rate_pct
```

| 步驟 | 說明 |
|------|------|
| `CASE WHEN count = 0 THEN 0` | 避免除以零（7 天內沒跑過的來源） |
| `FILTER (WHERE cr.run_status = 'success')` | 只 count 成功的 run |
| `::NUMERIC / count * 100` | 轉成百分比 |
| `round(..., 1)` | 保留一位小數 |

> ### 💡 FILTER 子句 vs CASE WHEN
>
> `count(*) FILTER (WHERE condition)` 是 PostgreSQL 的標準 SQL 語法，
> 等同於 `count(CASE WHEN condition THEN 1 END)`，但更簡潔好讀。
>
> 什麼時候用？當你需要在同一個 GROUP BY 裡，對不同條件做不同的聚合時。

### 7 天滑動窗口

```sql
LEFT JOIN crawler.crawl_runs cr ON cr.source_id = s.id
  AND cr.created_at >= NOW() - INTERVAL '7 days'
```

`LEFT JOIN` + 時間條件寫在 `ON` 裡（不是 `WHERE`）。

為什麼？因為如果寫在 WHERE 裡：
- 7 天內沒有 run 的來源會被 `WHERE cr.created_at >= ...` 過濾掉
- 那些來源就不會出現在結果裡

寫在 ON 裡：
- LEFT JOIN 保證所有 source 都出現
- 沒有 run 的來源，cr.* 欄位全部是 NULL
- `count(cr.id)` = 0，success_rate = 0

> ### 🧠 你的大腦在想…
>
> 「這些 crawler API 為什麼都是 authenticated only？」
>
> 因為爬蟲資料是**內部運營資料**，不是面向客戶的。
> 成功率、失敗數、佇列狀態——這些是管理員/運營人員需要看的。
> 即使文章本身是公開的，爬蟲的**運行狀態**不應該對外暴露。

---

## 延伸閱讀

**底層 schema 文件**（這些 API 背後的表結構）：

| 文件 | 涵蓋內容 |
|------|----------|
| [crawler/01_HEAD-FIRST-crawler-db.md](../crawler/01_HEAD-FIRST-crawler-db.md) | Crawler 資料庫全景 |
| [crawler/05_worker-architecture.md](../crawler/05_worker-architecture.md) | Worker 架構 |
| [crawler/04_data-flow-overview.md](../crawler/04_data-flow-overview.md) | 資料流總覽 |
| [`003_crawler_schema.sql`](../migrations/003_crawler_schema.sql) | 完整 SQL schema |

---

## 接下來

- [04_rag-api.md](04_rag-api.md)——RAG 語意搜尋 API
- [05_analytics-api.md](05_analytics-api.md)——Analytics 儀表板 API

# 03 — 一個 URL 如何流過這 10 張表？

> **接橋文件**：讀完 [01_HEAD-FIRST-crawler-db.md](01_HEAD-FIRST-crawler-db.md) 之後，你知道每張表長什麼樣。
> 這篇用一個具體的例子，讓你看清楚資料如何從「一個 URL」走到「一篇存好的文章」。

---

## 起點：你想爬 Hacker News

假設你想每天抓 Hacker News 的熱門文章，存到自己的資料庫。你需要：

1. 告訴系統「我要爬這個站」
2. 給它幾個起點 URL
3. 讓 Worker 自動跑

就這樣。下面我們一步一步看，每個步驟動了哪張表、資料長什麼樣。

---

## Step 1：設定來源站 → `sources`

你執行一次設定，告訴系統「hacker-news 是這樣的站」：

```python
# 這筆資料寫進 crawler.sources
{
    "project_id": "my-project",
    "code": "hacker-news",
    "name": "Hacker News",
    "base_url": "https://news.ycombinator.com",
    "crawler_url": "https://news.ycombinator.com/",
    "config": {
        "wait_until": "domcontentloaded",
        "block_resources": ["image", "font", "media", "stylesheet"]
    },
    "extractor_schema": {
        "list": {
            "item_selector": "tr.athing",
            "link_selector": "td.title span.titleline > a"
        }
    }
}
```

`sources` 表是整個系統的設定中心。它記錄「要爬什麼、怎麼爬、怎麼擷取」。**只需設定一次**，之後的爬取都參照這筆設定。

---

## Step 2：種子 URL 進佇列 → `crawl_queue`

你把 HN 首頁 URL 放進佇列：

```python
# 這筆資料寫進 crawler.crawl_queue
{
    "source_id": "src_01HNXXX",
    "url": "https://news.ycombinator.com/",
    "page_type": "list",
    "priority": 200,
    "status": "pending",          # 初始狀態
    "lease_token": null,          # 尚未被搶
    "retry_count": 0,
    "max_retries": 5
}
```

`crawl_queue` 是任務調度的核心。每一筆就是「一個待抓取的 URL」。

**為什麼有 `lease_token`？** 等等就知道了。

---

## Step 3：Worker 搶單 → `crawl_queue`（update）

Worker 呼叫 `lease_next_crawl_job()` RPC，系統幫它原子性地「搶」一筆任務：

```sql
-- 這是 RPC 內部做的事（你不用手寫）
UPDATE crawler.crawl_queue
SET
    status = 'leased',
    lease_token = gen_random_uuid()::text,   -- 這個 Worker 的「令牌」
    lease_expires_at = now() + '5 minutes',  -- 5 分鐘內沒完成，自動釋放
    worker_id = 'worker-a3f2'
WHERE id = (
    SELECT id FROM crawler.crawl_queue
    WHERE status = 'pending'
    ORDER BY priority DESC
    LIMIT 1
    FOR UPDATE SKIP LOCKED    -- 多個 Worker 不搶同一筆
)
RETURNING *;
```

搶到之後，那筆資料變成：

```
status: "leased"
lease_token: "a3f2-..."    ← Worker 持有這個令牌
lease_expires_at: 5分鐘後  ← 過期就讓別人接手
worker_id: "worker-a3f2"
```

**`lease_token` 的用途**：Worker 完成後，要用這個令牌才能更新狀態。如果 Worker 掛掉，令牌還在它那裡，其他 Worker 可以在 `lease_expires_at` 之後接手這個任務。

---

## Step 4：開始批次記錄 → `crawl_runs`

Worker 搶到任務後，建立一筆執行記錄：

```python
# 寫進 crawler.crawl_runs
{
    "source_id": "src_01HNXXX",
    "run_status": "running",
    "started_at": "2024-01-15T08:00:00Z",
    "pages_fetched": 0,      # 執行完成後更新
    "articles_extracted": 0  # 執行完成後更新
}
```

`crawl_runs` 是「這次執行的日誌」。讓你知道每次爬了幾頁、擷取了幾篇、有沒有錯誤。

---

## Step 5：抓頁面、存 HTML → `source_pages`

Playwright 開瀏覽器，`page.goto("https://news.ycombinator.com/")`，拿到 HTML：

```python
# upsert 進 crawler.source_pages
{
    "source_id": "src_01HNXXX",
    "crawl_run_id": "run_01XXXX",
    "url": "https://news.ycombinator.com/",
    "page_type": "list",
    "raw_html": "<html>...</html>",   # 完整 HTML
    "http_status": 200,
    "fetched_at": "2024-01-15T08:00:05Z",
    "snapshot_json": {
        "title": "Hacker News",
        "links": ["https://...", "https://..."]  # 頁面上的連結
    }
}
```

`source_pages` 保存**原始資料**。不管後續擷取邏輯怎麼改，原始 HTML 都還在，可以重新解析。

**Upsert key：`(source_id, url)`** — 同一個 URL 再抓一次，更新現有的紀錄而非新增。

---

## Step 6：擷取文章列表（in-memory）

Worker 對抓到的頁面執行擷取邏輯，從 HTML 裡找出所有文章連結：

```python
# 這步在記憶體裡，不寫資料庫
articles_found = [
    {"title": "Why Go is Great", "url": "https://..."},
    {"title": "Rust 2024 Edition", "url": "https://..."},
    # ... 30 篇文章
]
```

這步對應 `extractor_schema.list` 的設定（item_selector、link_selector）。

---

## Step 7：文章 upsert 到 `articles`

每篇文章用 `content_hash` 去重後寫入：

```python
# upsert 進 crawler.articles（on_conflict: source_id, source_url）
{
    "source_id": "src_01HNXXX",
    "source_page_id": "pg_01XXXX",
    "title": "Why Go is Great",
    "source_url": "https://...",
    "author_name": "johndoe",
    "content_hash": "sha256:abc123...",   # ← 關鍵：同內容不重寫
    "is_published": true
}
```

**`content_hash` 去重邏輯**：

```
新 hash == 舊 hash？
  → 是：跳過，不更新（節省資料庫寫入）
  → 否：upsert（內容有變，更新）
```

這讓你可以每天重複跑，只有真正變更的文章才會更新。

---

## Step 8：把發現的文章 URL 塞回佇列 → `crawl_queue`

列表頁裡找到的 30 個文章 URL，塞回 `crawl_queue`，等待後續處理：

```python
# 每個文章 URL 都會新增一筆到 crawl_queue
{
    "url": "https://...",
    "page_type": "article",   # 這次是文章頁，不是列表頁
    "priority": 50,           # 優先度較低
    "payload": {
        "discovered_from": "list",
        "referrer_url": "https://news.ycombinator.com/"
    }
}
```

**Partial unique index 防重複**：`(source_id, url) WHERE status='pending'`。同一個 URL 已經在佇列裡的話，這次 insert 會被靜默忽略（`ignore_duplicates=True`）。

---

## Step 9：任務完成，更新佇列狀態

Worker 完成後，用 `lease_token` 更新狀態：

```python
# UPDATE crawl_queue WHERE id=X AND lease_token='a3f2-...'
{
    "status": "done",
    "finished_at": "2024-01-15T08:00:30Z"
}
```

**為什麼要同時比對 `lease_token`？** 防「殭屍更新」：如果 Worker 因為太慢導致 lease 過期，並被另一個 Worker 接手，原本的 Worker 醒來後的更新會因 `lease_token` 不符而**靜默失效**，不會覆蓋新 Worker 的工作。

---

## Step 10：更新執行記錄 → `crawl_runs`

最後更新這次執行的統計：

```python
{
    "run_status": "success",
    "finished_at": "2024-01-15T08:00:31Z",
    "pages_fetched": 1,
    "articles_extracted": 28,  # 有 2 篇 hash 沒變，跳過了
    "error_count": 0
}
```

---

## 10 張表的職責一覽

```
sources          你說「要爬哪個站、怎麼爬」
crawl_queue      待抓 URL 的佇列（有 lease 保護）
crawl_runs       每次執行的日誌與統計
source_pages     原始 HTML 快照（可重新解析）
articles         正規化的文章（有 content_hash 去重）
article_assets   文章附帶的圖片/媒體
tags             文章分類標籤
article_tags     文章↔標籤的多對多關係
publish_targets  要發布到哪些外部系統
article_publications 哪篇文章已發布到哪個系統
```

---

## 常見問題

**Q：Worker 掛掉，任務會消失嗎？**

不會。`lease_expires_at` 到期後，其他 Worker 在下次呼叫 `lease_next_crawl_job()` 時會撿走這個任務（SQL 裡有 `OR (status='leased' AND lease_expires_at < now())`）。

**Q：同一篇文章被多個 Worker 同時搶到怎麼辦？**

`FOR UPDATE SKIP LOCKED` 讓這件事不會發生。已被某個 Worker 鎖住的列，其他 Worker 在同一個 transaction 裡直接跳過。

**Q：Partial unique index 是什麼意思？**

普通 unique index 對整個表生效。Partial index 只對 `WHERE status='pending'` 的列生效。所以同一個 URL 可以有多筆 `done` 或 `failed` 的歷史紀錄，但在 `pending` 狀態下只能有一筆。

---

## 動手做：跑出剛才說的每一步

理解了流程，現在用真實程式碼跑一遍。每支腳本對應上面的步驟：

```bash
cd project-playwright

# Step 1+2：設定來源站 → sources 表
python ch08-supabase/02_seed_source.py

# Step 2：種子 URL 進佇列 → crawl_queue 表
python ch08-supabase/03_enqueue_urls.py

# Step 3-10：Worker 跑一筆完整流程
python ch08-supabase/04_single_job_worker.py
```

跑完後在 Supabase Table Editor 打開 `crawler` schema，對照上面每個 Step 看資料長什麼樣。

還沒設好環境？先看 [00_quickstart.md](00_quickstart.md)。

---

## 下一步

現在你知道一個 URL 如何走完整個 pipeline，也跑過一次真實的資料。

接下來讀 [04_data-flow-overview.md](04_data-flow-overview.md)，會看到每個步驟更完整的技術細節：
- `lease_next_crawl_job` RPC 的完整 SQL 逐行解析
- `project_id` 多租戶隔離的實作方式
- `moddatetime` trigger 如何自動更新 `updated_at`
- 可以直接在 Supabase SQL Editor 執行的「動手做」練習

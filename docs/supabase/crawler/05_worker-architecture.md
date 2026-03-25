# Playwright + Supabase Worker 架構（Python）

## 整體架構

```text
Scheduler / Cron
   |
queue producer
   |
Supabase crawl_queue
   |
worker coordinator
   |
Playwright worker (Python)
   |
page fetch / extract / asset download
   |
Supabase:
  - crawl_runs
  - source_pages
  - articles
  - article_assets
  - crawl_queue
```

### 部署建議

| 元件 | 執行環境 | 原因 |
| ---------------- | ---------------------------------------- | ----------------------------------------- |
| Queue 後端 | Supabase `crawl_queue` | 已有現成資料表 |
| Worker 執行環境 | Cloud Run container（Python） | Playwright 需要真實瀏覽器 |
| 排程器 | Cloud Run Job / cron / GitHub Actions | 觸發 enqueue + dispatch |
| 輕量 API | Supabase Edge Function | 僅負責 enqueue / dispatch / callback |

> Playwright 會執行真實瀏覽器——不要放在 serverless edge runtime 中。

---

## 角色分工

### 1. Producer（生產者）

將 URL 放入佇列。來源包括：

- 種子 URL / sitemap
- 列表頁翻頁
- 從文章頁發現的連結
- 手動重新爬取
- 重試回填

### 2. Dispatcher / Coordinator（調度器）

從佇列取出任務，分配給 Worker。

**簡化版**：每個 Worker 直接呼叫 `lease_next_job()`。
日後可擴充為獨立的 Coordinator。

### 3. Worker（工作者）

執行實際爬取：

- 開啟瀏覽器 / context
- `page.goto()`
- 等待 + 抽取
- 儲存頁面快照
- Upsert 文章
- 將子 URL 加入佇列
- 更新佇列狀態

### 4. Persistence Layer（持久層）

Supabase 資料表：`crawl_queue`、`crawl_runs`、`source_pages`、`articles`、`article_assets`

---

## 部署選項

### 方案 A：Cloud Run Worker + Supabase Queue（從這裡開始）

```text
Cron --> enqueue seeds --> Supabase crawl_queue --> Cloud Run workers --> Playwright --> Supabase
```

優點：穩定、易除錯、可控制並行度、容器友善。

### 方案 B：Edge Function Coordinator + Cloud Run Worker（長期方案）

```text
Scheduler --> Edge Function (enqueue) --> Supabase queue --> Cloud Run worker --> DB write
```

Edge Function：輕量 API、排程、驗證、狀態控制。
Cloud Run Worker：負責實際 Playwright 執行。

---

## 建議模組結構

```text
worker/
  __init__.py
  main.py                # 進入點，consume loop
  consumer.py            # SupabaseQueueConsumer（QueueConsumer protocol）
  browser_pool.py        # BrowserPool, BrowserPoolConfig
  page_runner.py         # PageRunner（WorkerProcessor protocol）
  db_types.py            # 所有 DB row/insert/update dataclass + enum
  types.py               # Worker 專用型別（LeasedJob, WorkerError 等）
  service_inputs.py      # EnqueueUrlInput, SaveFetchedPageInput 等
  extractors/
    __init__.py
    list_extractor.py    # 實作 PageExtractor.extract_list
    article_extractor.py # 實作 PageExtractor.extract_article
  persistence/
    __init__.py
    source_repo.py       # SupabaseSourceRepo
    source_page_repo.py  # SupabaseSourcePageRepo
    article_repo.py      # SupabaseArticleRepo
  policies/
    __init__.py
    retry_policy.py      # decide_retry, _calculate_backoff
    rate_limit_policy.py # DomainLimiter, SourceHealthTracker
    robots_policy.py
```

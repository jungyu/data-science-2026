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

**簡化版**：每個 Worker 直接呼叫 `lease_next_crawl_job()`。
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

## 模組結構

### Repo 實際位置

```text
project-playwright/
  ch08-supabase/
    01_connect_supabase.py    # 驗證連線
    02_seed_source.py         # 建立來源設定（sources）
    03_enqueue_urls.py        # 種子 URL 入佇列（crawl_queue）
    04_single_job_worker.py   # 單次 Worker（完整 pipeline，同步版）

  utils/
    supabase_client.py        # get_supabase() / get_crawler_table()
    db_types.py               # Layer 1：DB Row/Insert/Update dataclass
    worker/
      types.py                # Layer 2：LeasedJob, ProcessResult, WorkerError 等
      service_inputs.py       # Layer 3：Protocol 介面 + ServiceInput dataclass
      retry.py                # decide_retry(), SourceHealthTracker, DomainLimiter（核心邏輯）
      browser_pool.py         # BrowserPool（async Playwright 瀏覽器池）
      main.py                 # 持續消費迴圈入口（async）
      consumer.py             # SupabaseQueueConsumer（實作 QueueConsumer Protocol）
      page_runner.py          # PageRunner（實作 WorkerProcessor Protocol）
      extractors/
        list_extractor.py     # 實作 PageExtractor.extract_list
        article_extractor.py  # 實作 PageExtractor.extract_article
      persistence/
        source_repo.py        # SupabaseSourceRepo（實作 SourceRepository）
        source_page_repo.py   # SupabaseSourcePageRepo
        article_repo.py       # SupabaseArticleRepo
      policies/
        retry_policy.py       # 薄封裝：re-export retry.py 的 decide_retry()
        rate_limit_policy.py  # 薄封裝：re-export retry.py 的 DomainLimiter, SourceHealthTracker
```

> 型別定義（`db_types.py`、`types.py`、`service_inputs.py`）與 ch08 同步版共用，路徑不依賴部署方式。

---

## 下一步：看實作如何對應這份設計

上面定義了「誰做什麼」。接下來 [06_worker-consume-loop-python.md](06_worker-consume-loop-python.md) 會展示完整的 Python 實作，你可以對照：

| 這份文件（設計）| 06（實作）|
|---------------|---------|
| Consumer / Dispatcher | `SupabaseQueueConsumer.lease_next_job()` |
| Worker | `PageRunner.process()` |
| Persistence Layer | `SupabaseSourcePageRepo`, `SupabaseArticleRepo` |
| Browser Pool | `BrowserPool.new_context()` |

07 則說明 Consumer 在拿到 `ProcessResult` 之後，如何決定重試、失敗或停用。

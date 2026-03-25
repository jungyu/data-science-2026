# Playwright + Supabase Crawler — 資料流總覽

## Pipeline

```text
sources
  |
crawl_queue
  |
crawl_runs
  |
source_pages
  |
articles
  |
article_assets
  |
tags / article_tags
  |
publish_targets / article_publications
```

## 資料表職責對照

| 階段 | 資料表 | 角色 |
| ------------ | ----------------------------------------- | ------------------------------------------------- |
| 來源設定 | `sources` | 站台定義、規則、排程、Extractor schema |
| 佇列 | `crawl_queue` | 待處理 URL / 列表頁任務（lease-based） |
| 執行批次 | `crawl_runs` | 每次執行的批次紀錄 |
| 原始頁面 | `source_pages` | 原始 HTML、快照、頁面 metadata |
| 文章 | `articles` | 正規化文章實體，供搜尋／發布／AI 使用 |
| 附件 | `article_assets` | 圖片／檔案，對應 Supabase Storage |
| 標籤 | `tags`, `article_tags` | 分類與標籤系統 |
| 發布 | `publish_targets`, `article_publications` | 同步至 WP、Notion、Ghost、自訂 CMS |

## Playwright Pipeline 對照表

| 步驟 | 動作 | 寫入目標 | 主要 Python 型別 |
| ---- | ------------------------- | ---------------------------------- | --------------------------------------------------------------------- |
| 1 | 建立來源站台設定 | `sources` | `SourceInsert` |
| 2 | 放入種子 URL | `crawl_queue` | `EnqueueUrlInput`, `CrawlQueueInsert` |
| 3 | Worker 搶單（lease） | `crawl_queue` (status -> leased) | `LeasedJob` |
| 4 | 開始爬取批次 | `crawl_runs` | `StartCrawlRunInput`, `CrawlRunInsert` |
| 5 | 抓取列表頁／文章頁 | `source_pages` | `SaveFetchedPageInput`, `SourcePageInsert` |
| 6 | 抽出文章草稿 | 記憶體內處理 | `ExtractedArticleDraft` |
| 7 | Upsert 正規化文章 | `articles` | `UpsertArticleInput`, `ArticleInsert` |
| 8 | 下載媒體附件 | `article_assets` + Storage | `ArticleAssetInsert` |
| 9 | 指派標籤／分類 | `tags`, `article_tags` | `TagInsert`, `ArticleTagRow` |
| 10 | 對外發布 | `article_publications` | `ArticlePublicationInsert` |

## 型別策略

型別分為**三層**，全部以 Python 撰寫：

### 1. DB Row 型別（`db_types` 模組）

直接對應資料庫 row。詳見 `08_db-types-python.md`。

- `SourceRow`, `SourceInsert`, `SourceUpdate`
- `CrawlQueueRow`, `CrawlQueueInsert`
- `CrawlRunRow`, `CrawlRunInsert`
- `SourcePageRow`, `SourcePageInsert`
- `ArticleRow`, `ArticleInsert`
- `ArticleAssetRow`, `ArticleAssetInsert`
- `TagRow`, `TagInsert`, `ArticleTagRow`
- `PublishTargetRow`, `ArticlePublicationRow`

### 2. Worker／領域型別（`types` 模組）

Pipeline 專用型別。詳見 `09_worker-types-python.md`。

- `LeasedJob` — 帶有 lease token 的佇列任務
- `ExtractedArticleDraft` — Playwright 抽取結果，尚未寫入資料庫
- `WorkerError`, `ProcessResult`, `RetryDecision`
- `SourceHealth`, `SourceCrawlPolicy`, `ResponseSignal`
- `ArticleAggregate` — 文章連同附件、標籤、發布紀錄的聚合物件

### 3. Service Input 型別（`service_inputs` 模組）

用於 Repository／Worker 介面的型別。詳見 `10_worker-interfaces-python.md`。

- `EnqueueUrlInput`
- `StartCrawlRunInput`
- `SaveFetchedPageInput`
- `UpsertArticleInput`

## Supabase Codegen 整合

**Repository 層**可使用 Supabase 自動產生的型別或 `db_types`：

```python
# 將 Supabase 回應的 dict 轉為 db_types dataclass
source = SourceRow(**response.data[0])
```

**領域／服務層**使用手寫型別，以與 DB schema 變更解耦。

## 檔案結構（Python）

```text
worker/
  __init__.py
  main.py                # 進入點，consume loop
  consumer.py            # SupabaseQueueConsumer（QueueConsumer protocol）
  browser_pool.py        # BrowserPool, BrowserPoolConfig
  page_runner.py         # PageRunner（WorkerProcessor protocol）
  db_types.py            # 所有 DB row/insert/update dataclass
  types.py               # Worker 專用型別（LeasedJob, WorkerError 等）
  service_inputs.py      # EnqueueUrlInput, SaveFetchedPageInput 等
  extractors/
    __init__.py
    list_extractor.py    # 實作 PageExtractor.extract_list
    article_extractor.py # 實作 PageExtractor.extract_article
  persistence/
    __init__.py
    source_repo.py
    queue_repo.py
    source_page_repo.py
    article_repo.py
  policies/
    __init__.py
    retry_policy.py      # decide_retry, _calculate_backoff
    rate_limit_policy.py # DomainLimiter, SourceHealthTracker
    robots_policy.py
```

## 文件索引

| 檔案 | 內容 |
|------|---------|
| `03_playwright_crawler_schema.sql` | 權威 DB schema（含 lease 欄位） |
| `08_db-types-python.md` | Python DB row/insert/update 型別 |
| `09_worker-types-python.md` | Worker 專用型別（LeasedJob、錯誤、結果） |
| `10_worker-interfaces-python.md` | Protocol 介面、Service Input、聚合物件 |
| `05_worker-architecture.md` | 部署選項、角色分工 |
| `07_worker-retry-and-anti-ban.md` | 重試策略、健康追蹤器、反封鎖策略 |
| `06_worker-consume-loop-python.md` | 主迴圈、BrowserPool、PageRunner、Consumer 實作、Lease SQL |
| `12_typescript-types.md` | TypeScript 參考（已由 Python 版本取代） |
| `11_domain-types-and-repositories.md` | TypeScript 參考（已由 Python 版本取代） |

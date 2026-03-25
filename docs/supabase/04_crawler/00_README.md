# Playwright + Supabase Crawler

Supabase 資料庫驅動的網頁爬蟲系統。使用 Playwright (Python) 抓取頁面，Supabase 負責佇列、持久化與發布。

## Architecture

```
Scheduler / Cron
     |
  enqueue seed URLs
     |
  Supabase crawl_queue        ← lease-based，支援多 worker
     |
  Playwright Worker (Python)  ← Cloud Run container
     |
  fetch → extract → normalize
     |
  Supabase:
    source_pages   (raw HTML / snapshot)
    articles       (正規化文章)
    article_assets (媒體 → Storage)
    tags           (分類)
    article_publications (發布到外部 CMS)
```

## Pipeline

| Step | Action | Table | Direction |
|------|--------|-------|-----------|
| 1 | 設定來源站 | `sources` | write |
| 2 | 放入種子 URL | `crawl_queue` | write |
| 3 | Worker 搶單 (lease) | `crawl_queue` | update |
| 4 | 開始批次 | `crawl_runs` | write |
| 5 | 抓取頁面 | `source_pages` | write |
| 6 | 抽出文章草稿 | in-memory | — |
| 7 | 寫入正規化文章 | `articles` | upsert |
| 8 | 下載媒體 | `article_assets` + Storage | write |
| 9 | 標籤分類 | `tags` / `article_tags` | write |
| 10 | 對外發布 | `article_publications` | write |

## File Index

### Database

| File | Description |
|------|-------------|
| [003_crawler_schema.sql](../migrations/003_crawler_schema.sql) | SQL schema（10 tables + lease RPC + RLS） |
| [02_AUDIT-vs-guidelines.md](02_AUDIT-vs-guidelines.md) | Schema 對照 Supabase guidelines 的 29 項 audit |
| [01_HEAD-FIRST-crawler-db.md](01_HEAD-FIRST-crawler-db.md) | Head First 風格教學：Stage by Stage 學會 Supabase schema 設計 |

### Python Types（三層分離）

| File | Layer | Content |
|------|-------|---------|
| [08_db-types-python.md](08_db-types-python.md) | DB Row | 所有 table 的 dataclass（Row / Insert / Update） |
| [09_worker-types-python.md](09_worker-types-python.md) | Worker | LeasedJob, WorkerError, ProcessResult, RetryDecision, SourceHealth |
| [10_worker-interfaces-python.md](10_worker-interfaces-python.md) | Service | Protocol interfaces, service inputs, ArticleAggregate |

### Worker Design

| File | Content |
|------|---------|
| [05_worker-architecture.md](05_worker-architecture.md) | 部署方案、角色分離、模組結構 |
| [06_worker-consume-loop-python.md](06_worker-consume-loop-python.md) | main loop, BrowserPool, PageRunner, SupabaseQueueConsumer |
| [07_worker-retry-and-anti-ban.md](07_worker-retry-and-anti-ban.md) | 重試策略、backoff、source health、anti-ban 原則 |
| [04_data-flow-overview.md](04_data-flow-overview.md) | Pipeline mapping、type strategy、file structure |

### TypeScript Reference (archived)

已移至 `_archived/`，由 Python 版本取代：
- `_archived/12_typescript-types.md` → 由 `08_db-types-python.md` 取代
- `_archived/11_domain-types-and-repositories.md` → 由 `10_worker-interfaces-python.md` 取代

## Type Strategy

```
Layer 1: DB Row Types (db_types.py)
  SourceRow, ArticleRow, CrawlQueueRow ...
  → 直接對應 table，給 repository 用

Layer 2: Worker Types (types.py)
  LeasedJob, WorkerError, ExtractedArticleDraft ...
  → pipeline 專用，不綁 DB schema

Layer 3: Service Inputs (service_inputs.py)
  EnqueueUrlInput, SaveFetchedPageInput, UpsertArticleInput ...
  → 給 repository / worker interface 用
```

## Worker Module Structure

```
worker/
  main.py                  # consume loop entry point
  consumer.py              # SupabaseQueueConsumer
  browser_pool.py          # BrowserPool + restart policy
  page_runner.py           # PageRunner (single job processor)
  db_types.py              # DB row/insert/update dataclasses
  types.py                 # worker-specific types
  service_inputs.py        # EnqueueUrlInput, etc.
  extractors/
    list_extractor.py      # extract_list(page, source)
    article_extractor.py   # extract_article(page, source)
  persistence/
    source_repo.py
    source_page_repo.py
    article_repo.py
  policies/
    retry_policy.py        # exponential backoff + jitter
    rate_limit_policy.py   # DomainLimiter + SourceHealthTracker
    robots_policy.py
```

## Queue Design

Lease-based concurrency control（不是簡單的 status=running）：

```
pending → leased → running → done
                          → failed → pending (retry)
                          → dead (max retries exceeded)
                          → skipped (policy denied)
```

- `FOR UPDATE SKIP LOCKED`：多 worker 不搶同一筆
- `lease_expires_at`：worker 掛掉後，過期的 lease 被其他 worker 接手
- Exponential backoff + jitter：429/403 自動降速

## Anti-Ban Principles

| Principle | Implementation |
|-----------|---------------|
| 遵守 robots.txt | 先檢查再抓 |
| Domain 限流 | 每個 domain concurrency = 1 |
| 只抓必要資源 | block image/font/media/stylesheet |
| 偵測異常就退 | 429/403/captcha → source cooldown |
| 不繞過防護 | 禁止 CAPTCHA bypass、proxy rotation for evasion |

## Schema Status

Schema v3.0 (post-audit)。所有 29 項 audit violation 已修正，包括：
ULID PK、project_id 多租戶、RLS + JWT policy、moddatetime trigger、named constraint、partial index。

- **Head First 教學**：[01_HEAD-FIRST-crawler-db.md](01_HEAD-FIRST-crawler-db.md) — 從零學 schema 設計邏輯
- **歷史 Audit 報告**：[02_AUDIT-vs-guidelines.md](02_AUDIT-vs-guidelines.md) — 原始 29 項 violation 紀錄（歷史參考）

## Implementation Phases

| Phase | Scope | Status |
|-------|-------|--------|
| Phase 1 | crawl_queue + lease RPC + consume loop + basic retry | Design complete |
| Phase 2 | heartbeat, browser pool restart, source health, structured logging | Design complete |
| Phase 3 | source-specific policies, circuit breaker, metrics dashboard, dead-letter review | Planned |

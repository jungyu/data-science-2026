# Playwright + Supabase Crawler

> **你在讀這份文件，可能是因為你想知道：爬下來的資料要存哪、怎麼避免重複爬、多個 Worker 同時跑會不會打架。**
> 這個系統回答這三個問題。

---

## 這個系統解決什麼問題？

寫爬蟲不難。難的是：

- **重複爬**：同一篇文章被爬了三次，都進了資料庫
- **Worker 打架**：兩個 Worker 同時搶到同一個 URL，互相覆蓋
- **掛掉沒人知**：Worker 死了，任務永遠卡在「處理中」
- **被封鎖沒反應**：429 一直打，最後整個 IP 被擋

這套系統的設計，就是為了正面解決這四件事。

---

## 一分鐘大圖

```
你設定一個「來源站」（sources）
  ↓
把種子 URL 放進佇列（crawl_queue）
  ↓
Worker 從佇列「搶單」── 原子操作，不會兩人搶同一筆
  ↓
Playwright 開瀏覽器抓頁面
  ↓
存原始 HTML（source_pages）
  ↓
擷取文章、計算 content_hash
  ↓
Upsert 到 articles── hash 沒變就不寫，不重複
  ↓
發現的新 URL 再塞回佇列
```

這就是整個 pipeline。10 張表、每張表只做一件事。

---

## 學習路徑

### 路線 A：先動手，再理解設計（推薦新手）

| 步驟 | 文件 | 你會做到什麼 |
|------|------|------------|
| 0 | [**00_quickstart.md**](00_quickstart.md) | **30 分鐘跑出第一個 crawler，看到資料存進 Supabase** |
| 1 | [03_schema-to-pipeline.md](03_schema-to-pipeline.md) | 理解剛才每一步動了哪張表、為什麼 |
| 2 | [01_HEAD-FIRST-crawler-db.md](01_HEAD-FIRST-crawler-db.md) | Schema 是怎麼一步步設計出來的？ |
| 3 | [04_data-flow-overview.md](04_data-flow-overview.md) | lease 機制、content_hash、多租戶的完整技術細節 |

### 路線 B：先理解架構，再看實作（推薦有系統設計經驗者）

| 步驟 | 文件 | 你會學到 |
|------|------|---------|
| 1 | [01_HEAD-FIRST-crawler-db.md](01_HEAD-FIRST-crawler-db.md) | Schema 設計邏輯：一步步推導出 10 張表 |
| 2 | [03_schema-to-pipeline.md](03_schema-to-pipeline.md) | 一個 URL 如何流過這 10 張表 |
| 3 | [04_data-flow-overview.md](04_data-flow-overview.md) | Pipeline 完整技術細節 |
| 4 | [05_worker-architecture.md](05_worker-architecture.md) | Worker 部署方案與模組分工 |
| 5 | [06_worker-consume-loop-python.md](06_worker-consume-loop-python.md) | 消費迴圈 + BrowserPool 完整實作 |
| 6 | [07_worker-retry-and-anti-ban.md](07_worker-retry-and-anti-ban.md) | Retry 策略 + 反封鎖設計 |

### 查閱用（隨時翻）

| 文件 | 內容 |
|------|------|
| [08_db-types-python.md](08_db-types-python.md) | Layer 1：所有 DB Row/Insert/Update dataclass |
| [09_worker-types-python.md](09_worker-types-python.md) | Layer 2：LeasedJob, ProcessResult, WorkerError 等 |
| [10_worker-interfaces-python.md](10_worker-interfaces-python.md) | Layer 3：Protocol 介面 + ServiceInput |

> **附錄**：[02_AUDIT-vs-guidelines.md](02_AUDIT-vs-guidelines.md) — Schema 設計過程的 29 項審計記錄，初次學習可略過。

---

## 核心設計決策（各用一句話）

| 問題 | 決策 |
|------|------|
| 多 Worker 怎麼不打架？ | `FOR UPDATE SKIP LOCKED`：資料庫層的原子搶單 |
| Worker 掛掉任務怎麼辦？ | `lease_expires_at`：過期自動釋放，讓其他 Worker 接手 |
| 同一篇文章怎麼不重複寫？ | `content_hash`：內容沒變就不 upsert |
| 多個客戶的資料怎麼隔離？ | 每張表都有 `project_id`，RLS 強制隔離 |
| 被封鎖怎麼辦？ | 429/403 觸發 source cooldown，不硬打 |

---

## 型別系統三層架構

讀到後半段的型別文件（08-10）時，會看到三層分離：

```
Layer 1 (db_types.py)  — 對應資料表，給 repository 操作
  SourceRow, ArticleRow, CrawlQueueRow ...

Layer 2 (types.py)     — Pipeline 中間型別，不綁 DB
  LeasedJob, WorkerError, ProcessResult, ExtractedArticleDraft ...

Layer 3 (service_inputs.py) — 跨層的輸入規格，給 Protocol 介面用
  EnqueueUrlInput, UpsertArticleInput ...
```

分這三層的原因：DB 型別一變（例如加欄位），不應該影響 Worker 邏輯；Worker 邏輯的中間結果，也不應該直接耦合到 DB schema。

---

## 技術規格速查

| 項目 | 規格 |
|------|------|
| Primary Key | ULID（`text DEFAULT generate_ulid()`），非 UUID |
| 多租戶隔離 | `project_id` 欄位 + RLS policy + JWT `app_metadata` |
| 自動更新時間 | `moddatetime` trigger，套用在 8 張有 `updated_at` 的表 |
| 佇列 PK 去重 | Partial unique index：`(source_id, url) WHERE status='pending'` |
| 文章去重 | `content_hash` SHA-256 |
| Schema 版本 | v3.0（所有 29 項 audit violation 已修正） |

---

## Repo 實際模組位置

```
project-playwright/
  ch08-supabase/                  ← 可直接執行的學習腳本
    01_connect_supabase.py        # 驗證連線與 schema 存取
    02_seed_source.py             # 建立來源設定
    03_enqueue_urls.py            # 種子 URL 入佇列
    04_single_job_worker.py       # 單次完整 Worker（同步版）

  utils/
    supabase_client.py            # Supabase 連線工具
    db_types.py                   # Layer 1：DB 型別
    worker/
      types.py                    # Layer 2：Worker 型別
      service_inputs.py           # Layer 3：Protocol 介面
      retry.py                    # Retry 策略 + 健康追蹤
      browser_pool.py             # async BrowserPool（Phase 2）
```

> 生產架構（`consumer.py`、`page_runner.py`、`persistence/`、`extractors/`）見 [05_worker-architecture.md](05_worker-architecture.md) Phase 2+ 規劃。

---

## 實作階段

| Phase | 範圍 | 狀態 |
|-------|------|------|
| Phase 1 | crawl_queue + lease RPC + 消費迴圈 + 基本 retry | 設計完成 |
| Phase 2 | heartbeat、browser pool 重啟、source health、結構化日誌 | 設計完成 |
| Phase 3 | 來源專屬政策、circuit breaker、metrics dashboard、dead-letter 審查 | 規劃中 |

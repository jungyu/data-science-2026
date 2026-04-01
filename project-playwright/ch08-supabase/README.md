# Ch08 — Playwright × Supabase 整合

## 定位

本章是 ch01–ch07 的**整合終點**，也是 `docs/supabase/04_crawler/` 架構文件的**可執行實作**。

```
ch01-ch07                         ch08
瀏覽器自動化技能         ──→      Playwright × Supabase Pipeline
（Browser / Selector /            （Queue → Fetch → Extract → Persist）
  Interaction / Extraction）
```

## 學習目標

1. 將 Playwright 爬取結果寫入 Supabase（`crawler` schema）
2. 理解 lease-based 佇列設計（`crawl_queue` + `lease_next_crawl_job()`）
3. 掌握 content_hash 去重機制（避免重複更新未變更的文章）
4. 看懂 `docs/supabase/04_crawler/` 文件與程式碼的對應關係

## 前置需求

### 1. 環境設定

```bash
# 安裝含 supabase 的依賴
pip install -e ".[all]"

# 複製並填入環境設定
cp .env.example .env
# 編輯 .env，填入 SUPABASE_URL / SUPABASE_SERVICE_KEY / PROJECT_ID
```

### 2. 取得 Supabase 金鑰

Supabase Dashboard → **Project Settings → API**：

| 環境變數 | 對應欄位 |
|---|---|
| `SUPABASE_URL` | Project URL |
| `SUPABASE_SERVICE_KEY` | `service_role` secret（非 anon key） |

> **安全提醒**：`service_role` key 擁有完整 DB 存取權，僅用於後端 worker，
> 絕對不要暴露於前端或提交至版控（`.env` 已在 `.gitignore` 中）。

### 3. 開放 `crawler` Schema

Supabase Dashboard → **Project Settings → API** → Extra schemas to expose via PostgREST：

加入 `crawler`，讓 `supabase.schema("crawler").table(...)` 可以正常運作。

### 4. 執行 Schema Migration

確認已在 Supabase SQL Editor 執行：
- `docs/supabase/migrations/001_extensions.sql`
- `docs/supabase/migrations/003_crawler_schema.sql`

## 範例檔案

| 檔案 | 說明 | 對應文件 |
|------|------|---------|
| `01_connect_supabase.py` | 驗證連線、列出 sources | — |
| `02_seed_source.py` | 建立 Hacker News 來源設定 | `crawler.sources` |
| `03_enqueue_urls.py` | 將種子 URL 塞入 `crawl_queue` | `04_data-flow-overview.md` Step 2 |
| `04_single_job_worker.py` | 完整單次工作流程（同步版） | `05_worker-architecture.md` |

## 執行順序

```bash
cd project-playwright

# 1. 驗證連線
python ch08-supabase/01_connect_supabase.py

# 2. 建立來源設定（只需執行一次）
python ch08-supabase/02_seed_source.py

# 3. 塞入種子 URL
python ch08-supabase/03_enqueue_urls.py

# 4. 執行單次 Worker（抓取一筆佇列任務）
python ch08-supabase/04_single_job_worker.py
```

## 資料流

```
crawler.sources          ← 02_seed_source.py 建立
       │
       ▼
crawler.crawl_queue      ← 03_enqueue_urls.py 塞入種子 URL
       │
       │ lease_next_crawl_job()
       ▼
04_single_job_worker.py
  │ BrowserManager.goto()
  ├─→ crawler.crawl_runs    （記錄執行批次）
  ├─→ crawler.source_pages  （存 raw HTML + snapshot）
  └─→ crawler.articles      （upsert 正規化文章，content_hash 去重）
```

## 與 docs 的對應

| 本章程式 | 對應 docs 文件 |
|---------|--------------|
| `utils/supabase_client.py` | `05_worker-architecture.md` Persistence Layer |
| `utils/db_types.py` | `08_db-types-python.md` 完整移植 |
| `03_enqueue_urls.py` | `04_data-flow-overview.md` Step 2 |
| `04_single_job_worker.py` | `06_worker-consume-loop-python.md` 同步簡化版 |
| `crawl_queue` lease 機制 | `04_data-flow-overview.md` crawl_queue 狀態機 |

## 進階（Phase 2）

Phase 1（本章）使用同步 Playwright，適合學習。
生產環境請參考 `docs/supabase/04_crawler/06_worker-consume-loop-python.md`，
該文件使用 `async_playwright` + `supabase.AsyncClient`，支援 BrowserPool 多工並行。

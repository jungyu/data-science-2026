# Quickstart：30 分鐘跑出第一個 Crawler

> **目標**：成功爬取 Hacker News 首頁一次，看到文章存進 Supabase。
> **你會動到**：`sources`、`crawl_queue`、`crawl_runs`、`source_pages`、`articles` 五張表。
> **不需要懂**：Cloud Run、lease 機制、multi-tenant RLS（之後再學）。

---

## 前置需求

| 項目 | 版本 / 規格 |
|------|-----------|
| Python | 3.11+ |
| Supabase 帳號 | 免費方案即可 |
| Supabase 專案 | 已建立（記下 Project URL 與 Service Role Key） |

---

## Step 1：建 Python 環境

```bash
cd project-playwright

# 建虛擬環境
python -m venv .venv
source .venv/bin/activate      # macOS/Linux
# .venv\Scripts\activate       # Windows

# 安裝全部依賴（含 supabase、playwright）
pip install -e ".[all]"

# 安裝 Playwright 瀏覽器
playwright install chromium
```

---

## Step 2：設定環境變數

```bash
cp .env.example .env
```

打開 `.env`，填入以下三個值（其他保持預設）：

```bash
# Supabase Dashboard → Project Settings → API
SUPABASE_URL=https://xxxxxxxxxxxx.supabase.co
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# 你的專案識別碼（任意字串，用來隔離資料）
PROJECT_ID=my-first-crawler
```

> ⚠️ 用 `service_role` key，不是 `anon` key。`service_role` 有完整寫入權限，適合後端 worker；永遠不要放在前端。

---

## Step 3：執行 Schema Migration

在 Supabase Dashboard → **SQL Editor** 依序執行：

```
docs/supabase/migrations/001_extensions.sql   ← ULID 產生器
docs/supabase/migrations/003_crawler_schema.sql ← 全部資料表 + RPC + RLS
```

執行後你會看到 10 張新的資料表出現在 `crawler` schema 下。

**開放 crawler schema 給 API 存取**：

Supabase Dashboard → **Project Settings → API → Extra schemas to expose via PostgREST**，加入 `crawler`。

---

## Step 4：驗證連線

```bash
python ch08-supabase/01_connect_supabase.py
```

成功輸出應該像這樣：

```
==================================================
Ch08 — Supabase 連線驗證
==================================================
[✓] Supabase 連線成功

[資料表存取檢查]
  [✓] crawler.sources                   （現有 0 筆）
  [✓] crawler.crawl_runs                （現有 0 筆）
  [✓] crawler.crawl_queue               （現有 0 筆）
  [✓] crawler.source_pages              （現有 0 筆）
  [✓] crawler.articles                  （現有 0 筆）

[Sources 清單] 共 0 筆
  （尚無資料，請執行 02_seed_source.py 建立來源設定）

[RPC 可用性檢查]
  [✓] lease_next_crawl_job() 可呼叫
  [i] 佇列目前為空（執行 03_enqueue_urls.py 加入任務）
```

如果看到 `[✗]`，最常見的原因是：
- `SUPABASE_URL` 或 `SUPABASE_SERVICE_KEY` 填錯
- migration SQL 尚未執行
- `crawler` schema 未加入 Extra schemas

---

## Step 5：設定來源站（只需執行一次）

```bash
python ch08-supabase/02_seed_source.py
```

這個指令在 `crawler.sources` 裡建立一筆 Hacker News 的設定。執行成功後：

```
[✓] 寫入成功
  source.id         : 01XXXXXXXXXXXXXXXXXXXXXXXXXX
  source.created_at : 2024-01-15T08:00:00+00:00
```

重複執行是安全的——使用 upsert，不會重複新增。

---

## Step 6：把種子 URL 放進佇列

```bash
python ch08-supabase/03_enqueue_urls.py
```

這個指令把 Hacker News 首頁（第 1、2 頁）放進 `crawler.crawl_queue`：

```
[✓] 寫入完成：新增 2 筆，跳過重複 0 筆

  [佇列狀態]
    pending     2 筆
```

重複執行也是安全的——Partial unique index 防止重複入列。

---

## Step 7：執行 Worker，抓取一筆任務

```bash
python ch08-supabase/04_single_job_worker.py
```

Worker 會：
1. 從佇列搶一筆任務（`crawl_queue` status: pending → leased → running → done）
2. 開 Chromium 瀏覽器，抓取 Hacker News 首頁
3. 存原始 HTML 到 `source_pages`
4. 擷取文章列表，upsert 到 `articles`
5. 把發現的文章 URL 再塞回 `crawl_queue`

成功輸出：

```
==================================================
執行摘要
==================================================
  source     : Hacker News
  url        : https://news.ycombinator.com/
  run_id     : 01XXXXXXXXXXXXXXXXXXXXXXXXXX
  pages      : 1
  articles   : 28 筆新增/更新
  errors     : 0
```

重複執行：消費佇列的下一筆任務。

---

## Step 8：在 Supabase 驗證結果

到 Supabase Dashboard → **Table Editor** → `crawler` schema，你應該看到：

| 資料表 | 預期資料 |
|-------|---------|
| `sources` | 1 筆（Hacker News 設定） |
| `crawl_queue` | 2 筆 seed（done）+ 最多 20 筆文章 URL（pending） |
| `crawl_runs` | 1 筆（status: success） |
| `source_pages` | 1 筆（HN 首頁的 raw HTML） |
| `articles` | ~28 筆（HN 熱門文章） |

---

## 下一步

成功看到資料了？恭喜，你完成了第一個 crawler 的完整 pipeline。

**接下來可以做的事：**

- 再跑一次 `04_single_job_worker.py`——消費一筆文章 URL 任務，看 `articles` 被補入 `content_text` 和 `abstract`
- 想觀察 **content_hash 去重**：先執行 `03_enqueue_urls.py` 重新塞入 seed URL，再跑 `04_single_job_worker.py`，舊文章的 `updated_at` 不會改變
- 讀 [03_schema-to-pipeline.md](03_schema-to-pipeline.md)——用圖解理解剛才每一步動了哪張表
- 讀 [04_data-flow-overview.md](04_data-flow-overview.md)——深入了解 lease 機制與 content_hash
- 修改 `02_seed_source.py`，換一個你自己想爬的網站試試

**想了解背後的設計：**

→ [01_HEAD-FIRST-crawler-db.md](01_HEAD-FIRST-crawler-db.md)：Schema 的設計邏輯是怎麼一步步推導出來的

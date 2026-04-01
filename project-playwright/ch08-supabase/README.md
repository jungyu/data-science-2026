# Ch08 — Playwright × Supabase 整合

## 定位

本章是 ch01–ch07 的**整合終點**：用 Playwright 爬取 Hacker News，
透過 lease-based 佇列（`crawl_queue`）管理任務，並將結果寫入 Supabase。

```
ch01-ch07                         ch08
瀏覽器自動化技能         -->      Playwright x Supabase Pipeline
（Browser / Selector /            （Queue -> Fetch -> Extract -> Persist）
  Interaction / Extraction）
```

## 學習目標

1. 將 Playwright 爬取結果寫入 Supabase（`crawler` schema）
2. 理解 lease-based 佇列設計（`crawl_queue` + `lease_next_crawl_job()`）
3. 掌握 content_hash 去重機制（避免重複更新未變更的文章）

---

## 前置需求

### 1. 安裝依賴

```bash
pip install -e ".[all]"
```

### 2. 設定環境變數

```bash
cp .env.example .env
```

編輯 `.env`，填入以下欄位：

```env
SUPABASE_URL=http://127.0.0.1:55421
SUPABASE_SERVICE_KEY=<本機 service_role JWT，見下方說明>
PROJECT_ID=local-dev
```

> **安全提醒**：`service_role` key 擁有完整 DB 存取權，僅用於後端 worker，
> 絕對不要提交至版控（`.env` 已在 `.gitignore`）。

---

## 本機 Supabase 設定（Docker）

### Windows — 下載 CLI

本專案已在 `.tools/supabase/` 放置 Windows 版 `supabase.exe`，
不需要 npm / winget / scoop。

```powershell
# 在 project-playwright 目錄下執行
.tools\supabase\supabase.exe start
```

### macOS / Linux — 使用 Homebrew

```bash
brew install supabase/tap/supabase
supabase start
```

### 啟動後取得 service_role key

```bash
supabase status
# 找到 service_role key 那行，複製貼入 .env
```

> **Port 衝突說明**：
> 本專案的 `supabase/config.toml` 使用非預設 port（55421–55427），
> 避免與其他本機 Supabase stack 衝突。
> 若仍有衝突，修改 `config.toml` 中的 `[api] port`、`[db] port`、
> `[studio] port`、`[inbucket] port`、`[analytics] port`，
> 再重新執行 `supabase start`。

### 套用 Migration

```bash
supabase db reset
```

這會自動套用 `supabase/migrations/` 下的所有 SQL，建立：
- `crawler.sources`
- `crawler.crawl_runs`
- `crawler.crawl_queue`（含 lease 索引）
- `crawler.source_pages`
- `crawler.articles`
- `crawler.lease_next_crawl_job()` RPC

> `crawler` schema 的 PostgREST expose 已設定在 `supabase/config.toml` 的
> `[api] schemas` 欄位，`supabase start` 後自動生效，**不需要** Dashboard 手動設定。

---

## 範例檔案

| 檔案 | 說明 |
|------|------|
| `01_connect_supabase.py` | 驗證連線、列出 sources、測試 RPC |
| `02_seed_source.py` | 建立 Hacker News 來源設定（upsert，可重複執行） |
| `03_enqueue_urls.py` | 將種子 URL 塞入 `crawl_queue` |
| `04_single_job_worker.py` | 完整單次工作流程（lease → fetch → persist） |

---

## 執行順序

```bash
cd project-playwright

# 1. 驗證連線與 schema
python ch08-supabase/01_connect_supabase.py

# 2. 建立來源設定（只需執行一次）
python ch08-supabase/02_seed_source.py

# 3. 塞入種子 URL
python ch08-supabase/03_enqueue_urls.py

# 4a. 單次執行（消費一筆佇列任務）
python ch08-supabase/04_single_job_worker.py

# 4b. 連續消費（自動跑完全部 pending 任務）
python ch08-supabase/04_single_job_worker.py --loop

# 4c. 連續消費，自訂空佇列等待時間
python ch08-supabase/04_single_job_worker.py --loop --idle-wait 5
```

**Windows PowerShell：**

```powershell
.venv\Scripts\activate
python ch08-supabase\01_connect_supabase.py
python ch08-supabase\02_seed_source.py
python ch08-supabase\03_enqueue_urls.py
python ch08-supabase\04_single_job_worker.py
python ch08-supabase\04_single_job_worker.py --loop
```

---

## 資料流

```
crawler.sources          <- 02_seed_source.py 建立
       |
       v
crawler.crawl_queue      <- 03_enqueue_urls.py 塞入種子 URL
       |
       | lease_next_crawl_job()
       v
04_single_job_worker.py
  | BrowserManager.goto()
  +-> crawler.crawl_runs    （記錄執行批次）
  +-> crawler.source_pages  （存 raw HTML + snapshot）
  +-> crawler.articles      （upsert 正規化文章，content_hash 去重）
  +-> crawler.crawl_queue   （發現的文章 URL 加入佇列）
```

---

## 常見問題

### Q: `SUPABASE_URL` 應該填什麼？

本機 Docker 預設為 `http://127.0.0.1:55421`（見 `supabase/config.toml`）。
雲端版填 Supabase Dashboard → Project Settings → API → Project URL。

### Q: `crawler` schema 的 API 打不到

確認 `supabase/config.toml` 的 `[api] schemas` 包含 `"crawler"`，
然後重新執行 `supabase start`（或 `supabase stop && supabase start`）。

### Q: `insert` 報 unique constraint 錯誤

種子 URL 已經在 `pending` 狀態。`03_enqueue_urls.py` 會自動跳過，
正常情況下不會報錯。若手動操作後出現，檢查 `crawl_queue` 的 status。

### Q: Worker 執行後找不到任務

確認 `crawl_queue` 中有 `status = 'pending'` 的資料：

```bash
supabase status   # 確認 DB port
```

```sql
select status, count(*) from crawler.crawl_queue group by status;
```

---

## 進階

Phase 1（本章）使用同步 Playwright，適合學習與驗證架構。
生產環境可改用 `async_playwright` + `supabase.AsyncClient`，
支援 BrowserPool 多工並行（見 `utils/worker/` 目錄）。

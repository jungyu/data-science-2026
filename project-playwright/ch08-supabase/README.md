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

編輯 `.env`，依「本機」或「雲端」二選一填入。

**本機 Supabase（Docker）：**

```env
SUPABASE_URL=http://127.0.0.1:55421
SUPABASE_SERVICE_KEY=<本機 service_role JWT，見「本機 Supabase 設定」>
PROJECT_ID=local-dev
```

**雲端 Supabase（supabase.com）：**

```env
SUPABASE_URL=https://你的-project-ref.supabase.co
SUPABASE_SERVICE_KEY=sb_secret_xxxxxxxxxxxxxxxxxxxx  # 或 legacy eyJ...
PROJECT_ID=demo-project
```

> **安全提醒**：`service_role` / `sb_secret_...` key 擁有完整 DB 存取權，
> 僅用於後端 worker，絕對不要提交至版控（`.env` 已在 `.gitignore`）。
>
> **不要用 publishable / anon / legacy public key**——那些前端用，被 RLS 擋。

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

## 雲端 Supabase 設定（supabase.com）

> 適合：要把資料留下來給 ch09 RAG / production demo / 多人協作。
> 若只是教學試跑，**用上面的本機 Docker 版更簡單**。

### Step 1 — 找到你的 project ref

到 Supabase Dashboard 點進專案，看瀏覽器網址：

```
https://supabase.com/dashboard/project/abcdefghijklmnop
                                      ^^^^^^^^^^^^^^^^
                                      這 20 字元就是 project ref
```

把它記下來；後續 `.env` 與 CLI 都會用到。

### Step 2 — 取得 service key 寫入 `.env`

到 Dashboard → Project Settings → API：

- **新系統「API Keys」區塊** → 複製 `secret` 開頭那個（`sb_secret_...`）
- **舊系統「Project API keys」區塊**（legacy） → 複製 `service_role` row（`eyJ...`）

兩者擇一填入 `.env` 的 `SUPABASE_SERVICE_KEY`（**不要用 `anon` / `publishable`**）：

```env
SUPABASE_URL=https://abcdefghijklmnop.supabase.co
SUPABASE_SERVICE_KEY=sb_secret_xxxxxxxxxxxxxxxxxxxx
PROJECT_ID=demo-project
```

### Step 3 — 安裝 CLI 並 link 專案

```bash
brew install supabase/tap/supabase
supabase login                                    # 開瀏覽器登入 Supabase 帳號

supabase link --project-ref abcdefghijklmnop      # 用你的 project ref
```

`link` 過程會：
1. 問是否 sync `local config differences` → 通常 **N**（保留本地 config.toml 的本機 port 設定）
2. 問 **Database password**（沒回顯，正常） → 這是建立專案時設的 DB 密碼，**不是** API key 也不是登入密碼

> 💡 忘記 DB 密碼？到 Dashboard → Project Settings → Database → **Reset database password**
> 換一個強密碼，等 30-60 秒同步後再 link。

### Step 4 — 套用 migrations 到雲端

```bash
supabase db push
```

期待輸出依序套三個 SQL 檔：

```
Applying migration 20260401130500_crawler_schema.sql...
Applying migration 20260401140000_lease_with_source.sql...
Applying migration 20260507000000_articles_rag_columns.sql...
Finished supabase db push.
```

### Step 5 — 把 `crawler` schema 暴露給 Data API（**雲端特有**）

> 本機版本由 `config.toml` 自動處理；雲端必須手動。

Supabase 2025 新版 UI 已把這項設定從 **Settings → API** 搬到
**Settings → Integrations → Data API**：

1. Dashboard 左側 sidebar → **Project Settings**（齒輪）
2. 找 **INTEGRATIONS** 區塊 → 點 **Data API**
3. 切到 **Settings** 分頁
4. 找到 **Exposed schemas** 區塊，點右邊的下拉選單
5. 勾選 `crawler`（連同預設的 `public` / `graphql_public`）
6. 應該顯示 **3 of 3 schemas exposed**（不需要按 Save，勾選即生效）

直接走網址也可以（會自動 redirect）：

```
https://supabase.com/dashboard/project/<你的-ref>/settings/api
```

> ⚠️ 跳過這步的話，[01_connect_supabase.py](01_connect_supabase.py) 會回
> `relation "crawler.sources" does not exist` —— 不是 schema 沒套用，是
> PostgREST（Data API）拒絕對外曝露。
>
> ℹ️ Supabase 2024 之前的舊版 UI 把這設定放在 **Settings → API → Exposed
> schemas** 的純文字輸入欄。網路教學若看到舊截圖對不上時，認準新位置：
> **Settings → Integrations → Data API → Settings 分頁**。

### Step 6 — 驗證

```bash
python ch08-supabase/01_connect_supabase.py
```

期待看到 `crawler.sources / crawl_queue / articles` 三個表都「可讀取（目前 0 筆）」。

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

### Q: `supabase db push` 報 `Cannot find project ref. Have you run supabase link?`

你跳過了 link 步驟。先：

```bash
supabase link --project-ref 你的-20字元-ref
```

ref 在 Dashboard 網址 `https://supabase.com/dashboard/project/<這裡>` 找。

### Q: link 時問 Database password 是什麼？

是你在建立專案時設定的 DB 密碼（**不是** API key，**不是** Supabase 帳號登入密碼）。
忘了就到 Dashboard → Project Settings → Database → Reset database password。

### Q: `crawler` schema 的 API 打不到

**本機（Docker）**：確認 `supabase/config.toml` 的 `[api] schemas` 包含 `"crawler"`，
然後重新執行 `supabase start`（或 `supabase stop && supabase start`）。

**雲端**：到 Dashboard → Settings → **Integrations → Data API → Settings**
分頁 → **Exposed schemas** 下拉勾選 `crawler`。
這是雲端特有的步驟，CLI 不會自動代勞。
（2024 前舊 UI 在 Settings → API，2025 起搬到 Data API；別找錯地方。）

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

## 自我檢核

完成本章後，你應該能回答：

1. Lease-based 佇列（`lease_next_crawl_job()`）和簡單的 `SELECT ... LIMIT 1` 取任務相比，解決了什麼問題？如果兩個 worker 同時跑，會發生什麼？
2. `content_hash`（SHA-256）在整個流程裡扮演什麼角色？如果文章更新了但 URL 沒變，系統如何知道要重新爬？
3. 本章用 sync Playwright；`utils/worker/` 裡的 `BrowserManager` 改用 async。兩者在「同時處理多個頁面」這件事上有什麼本質差異？

---

## 進階

Phase 1（本章）使用同步 Playwright，適合學習與驗證架構。
生產環境可改用 `async_playwright` + `supabase.AsyncClient`，
支援 BrowserPool 多工並行（見 `utils/worker/` 目錄）。

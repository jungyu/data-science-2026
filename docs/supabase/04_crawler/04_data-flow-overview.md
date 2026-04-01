# Playwright + Supabase Crawler — 資料流總覽

> **對應 SQL**：[`003_crawler_schema.sql`](../migrations/003_crawler_schema.sql)（v3.0, 565 行）
>
> **定位**：本文件是 Pipeline 的**權威資料流文件**。型別策略、檔案結構、文件索引 → 詳見 [00_README.md](00_README.md)。

---

## 全景 Pipeline

> **你的大腦在想**：「不就是抓網頁存起來嗎？」
>
> **沒那麼簡單。** 一個生產級爬蟲要處理：多租戶隔離、佇列搶單、Lease 超時回收、重試/死信、內容去重、多目標發布。10 張表 + 1 支 RPC + 2 個 Helper Function 把這些全包了。

```
                        ┌─────────────────────────────────────────────────────────┐
                        │              Multi-Tenant Crawler System                │
                        │          (所有資料以 project_id 隔離)                     │
                        │                                                         │
  Scheduler / Cron ─────┤                                                         │
    enqueue seed URLs   │   crawler.crawl_queue                                   │
                        │     │                                                   │
                        │     │ lease_next_crawl_job()                             │
                        │     │ (FOR UPDATE SKIP LOCKED)                           │
                        │     ▼                                                   │
                        │   Worker A ─────────┬──── Worker B ──── Worker C        │
                        │     │               │       (多 Worker 並行消費)          │
                        │     ▼               │                                   │
                        │   fetch page        │                                   │
                        │     │               │                                   │
                        │     ├─ list page? ──┘ → 抽出更多 URL → 回到 queue        │
                        │     │                                                   │
                        │     └─ article page? → extract                          │
                        │           │                                             │
                        │     ┌─────┼─────────────────┐                           │
                        │     ▼     ▼                 ▼                           │
                        │  source  articles        article_assets                 │
                        │  _pages  (content_hash    (→ Storage)                   │
                        │          去重)                                           │
                        │            │                                            │
                        │     ┌──────┼──────┐                                     │
                        │     ▼             ▼                                     │
                        │   tags/         article_publications                    │
                        │   article_tags  (→ WP / Notion / Ghost)                 │
                        └─────────────────────────────────────────────────────────┘
```

### Pipeline 步驟對照（SQL 行號）

| 步驟 | 動作 | 寫入目標 | SQL 行號 | 主要 Python 型別 |
|------|------|---------|----------|-----------------|
| 1 | 建立來源站台設定 | `crawler.sources` | 42-65 | `SourceInsert` |
| 2 | 放入種子 URL | `crawler.crawl_queue` | 98-131 | `EnqueueUrlInput`, `CrawlQueueInsert` |
| 3 | Worker 搶單（lease） | `crawler.crawl_queue` (status→leased) | **319-347** | `LeasedJob` |
| 4 | 開始爬取批次 | `crawler.crawl_runs` | 72-91 | `StartCrawlRunInput`, `CrawlRunInsert` |
| 5 | 抓取列表頁／文章頁 | `crawler.source_pages` | 138-165 | `SaveFetchedPageInput`, `SourcePageInsert` |
| 6 | 抽出文章草稿 | 記憶體內處理 | — | `ExtractedArticleDraft` |
| 7 | Upsert 正規化文章 | `crawler.articles` | 172-206 | `UpsertArticleInput`, `ArticleInsert` |
| 8 | 下載媒體附件 | `crawler.article_assets` + Storage | 213-238 | `ArticleAssetInsert` |
| 9 | 指派標籤／分類 | `crawler.tags`, `crawler.article_tags` | 245-270 | `TagInsert`, `ArticleTagRow` |
| 10 | 對外發布 | `crawler.article_publications` | 292-312 | `ArticlePublicationInsert` |

---

## crawl_queue 狀態機（完整）

> **你的大腦在想**：「status 不就是 pending → done 嗎？」
>
> **不是。** 有 7 種狀態，包含 lease 超時回收和死信機制。

```
                         ┌──────────────────────────────────┐
                         │          crawl_queue              │
                         │     (SQL lines 98-131)            │
                         └──────────────────────────────────┘

                                   pending
                                     │
                     lease_next_crawl_job() 搶單
                     (FOR UPDATE SKIP LOCKED)
                                     │
                                     ▼
                                   leased ─────── lease_expires_at < now()
                                     │               │
                              Worker 開始處理          │ (Worker 掛了，
                                     │                │  沒回報完成)
                                     ▼                │
                                  running              │
                                 ╱   │   ╲            │
                                ╱    │    ╲           ▼
                               ▼     ▼     ▼     回到 pending
                             done  failed  skipped   (其他 Worker 接手)
                                     │
                                     │ retry_count < max_retries?
                                     │
                              ┌──────┴──────┐
                              │ Yes         │ No
                              ▼             ▼
                           pending         dead
                        (retry_count++)  (死信，需人工檢視)
```

### 狀態定義

| 狀態 | 意義 | 可轉換至 | CHECK constraint |
|------|------|---------|-----------------|
| `pending` | 等待搶單 | `leased` | SQL line 121 |
| `leased` | 已被 Worker 鎖定，尚未開始 | `running`, 超時→`pending` | |
| `running` | Worker 正在處理 | `done`, `failed`, `skipped` | |
| `done` | 成功完成 | （終態） | |
| `failed` | 處理失敗 | `pending`（重試）, `dead`（超過上限） | |
| `skipped` | Policy 拒絕（robots.txt、rate limit） | （終態） | |
| `dead` | 超過 max_retries，需人工處理 | （終態） | |

### Lease 欄位（SQL lines 111-115）

```sql
-- crawler.crawl_queue 的 lease 欄位
lease_token      text,          -- 隨機 UUID，防止舊 Worker 誤操作
leased_at        timestamptz,   -- 搶單時間
lease_expires_at timestamptz,   -- 過期時間（預設 5 分鐘後）
worker_id        text,          -- 哪個 Worker 搶到的
```

> **沒有 Dumb Questions**
>
> **Q: 為什麼用 lease 而不是簡單的 `status = 'running'`？**
>
> A: 因為 Worker 可能掛掉。如果只改 status = running，Worker 死了這筆任務就永遠卡住。Lease 有**過期時間**，超時後其他 Worker 可以接手。
>
> **Q: lease_token 幹嘛用的？**
>
> A: 防止**殭屍 Worker**。假設 Worker A 搶了一筆，但 A 太慢，lease 過期，Worker B 搶走了。這時 A 處理完想回寫結果，lease_token 已經不對了 → 寫入被拒 → 不會覆蓋 B 的工作。
>
> **Q: 防重複塞入的 unique index 怎麼運作？**
>
> A: `uq_crawl_queue_pending_source_url` (SQL line 130-131) 限制同一個 `source_id + url` 在 `status = 'pending'` 時只能有一筆。Cron 重跑不會產生重複任務，但同一 URL 完成後（status = done）可以再次被排入。

---

## Lease RPC：`crawler.lease_next_crawl_job()`

> **這是整個佇列機制的心臟。**（SQL lines 319-347）

```sql
create or replace function crawler.lease_next_crawl_job(
  p_worker_id text,
  p_lease_duration interval default interval '5 minutes'
)
returns setof crawler.crawl_queue
language sql
security definer
set search_path = crawler
as $$
  update crawler.crawl_queue
  set
    status = 'leased',
    lease_token = gen_random_uuid()::text,
    leased_at = now(),
    lease_expires_at = now() + p_lease_duration,
    worker_id = p_worker_id
  where id = (
    select id
    from crawler.crawl_queue
    where (status = 'pending' and scheduled_at <= now())       -- 正常待處理
       or (status = 'leased' and lease_expires_at < now())     -- lease 過期回收
    order by priority desc, scheduled_at asc                   -- 高優先 + 先進先出
    limit 1
    for update skip locked                                     -- 多 Worker 不搶同一筆
  )
  returning *;
$$;
```

### 逐行解讀

| 機制 | SQL 片段 | 作用 |
|------|---------|------|
| 搶單原子性 | `UPDATE ... WHERE id = (SELECT ... FOR UPDATE SKIP LOCKED)` | SELECT + UPDATE 在同一個 transaction，不會有 race condition |
| 多 Worker 並行 | `FOR UPDATE SKIP LOCKED` | 如果某列已被另一個 transaction 鎖定，跳過它而不是等待 |
| Lease 過期回收 | `status = 'leased' AND lease_expires_at < now()` | Worker 掛了的任務自動回到可搶狀態 |
| 優先級排序 | `ORDER BY priority DESC, scheduled_at ASC` | 高優先的先做；同優先的先進先出 |
| 防殭屍覆蓋 | `lease_token = gen_random_uuid()::text` | 每次搶單產生新 token，舊 Worker 的 token 失效 |

> **動手做**
>
> 在 Supabase SQL Editor 模擬搶單：
> ```sql
> -- Worker A 搶單
> select * from crawler.lease_next_crawl_job('worker-A');
>
> -- 同時 Worker B 搶單（會拿到不同的任務）
> select * from crawler.lease_next_crawl_job('worker-B');
>
> -- 模擬 Worker A 掛了：手動讓 lease 過期
> update crawler.crawl_queue
> set lease_expires_at = now() - interval '1 minute'
> where worker_id = 'worker-A' and status = 'leased';
>
> -- Worker C 搶單 → 會接手 Worker A 的過期任務
> select * from crawler.lease_next_crawl_job('worker-C');
> ```

---

## Multi-Tenant：`project_id` + JWT 隔離

> **你的大腦在想**：「一個爬蟲系統為什麼需要多租戶？」
>
> **因為同一套系統可能服務多個專案。** 專案 A 抓科技新聞，專案 B 抓財經資訊。它們共用同一套 schema，但資料必須完全隔離。

### 架構設計（SQL lines 397-540）

這是 Crawler 與 Shop schema 最大的架構差異：

| | Shop schema | Crawler schema |
|---|---|---|
| 隔離單位 | 用戶（`user_id`） | **專案**（`project_id`） |
| 身分來源 | `shop.get_current_user_id()` | **JWT `app_metadata.project_ids`** |
| 誰設定權限 | profiles.is_staff | **後端設定 `raw_app_meta_data`** |

### 每張表都有 `project_id`

```sql
-- 10 張表全部有這個欄位
project_id text not null
```

### Helper Functions

```sql
-- 1. 從 JWT 取得當前用戶可存取的 project 列表（SQL lines 418-435）
create or replace function crawler.get_my_project_ids()
returns text[]
language sql stable security definer set search_path = crawler
as $$
  select coalesce(
    array(
      select jsonb_array_elements_text(
        (select auth.jwt()) -> 'app_metadata' -> 'project_ids'
      )
    ),
    '{}'::text[]
  );
$$;

-- 2. 檢查用戶是否可存取特定 project（SQL lines 438-448）
create or replace function crawler.has_project_access(p_project_id text)
returns boolean
language sql stable security definer set search_path = crawler
as $$
  select p_project_id = ANY(crawler.get_my_project_ids());
$$;
```

### RLS Policy 模式

所有有 `project_id` 的表，Policy 長這樣：

```sql
-- 以 crawler.sources 為例（SQL lines 451-464）
create policy "sources_select" on crawler.sources
  for select to authenticated
  using (crawler.has_project_access(project_id));    -- ← 只能看自己 project 的

create policy "sources_service_role" on crawler.sources
  for all to service_role using (true) with check (true);  -- ← 後端 pipeline 不受限
```

### 三種 Policy 策略

| 表類型 | 策略 | 範例 |
|--------|------|------|
| 有 `project_id` 的業務表 | 直接 `has_project_access(project_id)` | sources, crawl_runs, crawl_queue, source_pages, articles, article_assets |
| 有 `project_id` 的參考表 | 同上，但 SELECT 開放 anon | tags, publish_targets |
| 無 `project_id` 的 Junction 表 | `using (true)` — 透過 FK 間接繼承 | article_tags, article_publications |

> **沒有 Dumb Questions**
>
> **Q: 為什麼 article_tags 不檢查 project_id？**
>
> A: 因為它是 junction table，只有 `article_id` + `tag_id`。article 和 tag 本身已經被 project_id policy 保護了。如果你看不到 article，你也查不到它的 tags（因為 JOIN 會拿不到資料）。
>
> **Q: JWT `app_metadata` 和 `user_metadata` 有什麼差別？**
>
> A: `user_metadata` 可以被前端使用者自己改（`supabase.auth.updateUser()`）。`app_metadata` **只能由後端 service_role 設定**，前端無法竄改。所以租戶權限放 `app_metadata`，絕對安全。
>
> **Q: 一個用戶可以存取多個 project 嗎？**
>
> A: 可以。`app_metadata.project_ids` 是陣列：`["demo-project", "prod-project"]`。`get_my_project_ids()` 回傳整個陣列，`has_project_access()` 用 `= ANY(...)` 檢查。

---

## content_hash 去重機制

> **你的大腦在想**：「Cron 每小時跑一次，同一篇文章不會重複存嗎？」
>
> **不會，因為有兩道防線。**

### 防線 1：URL 唯一（SQL line 197）

```sql
constraint uq_articles_source_url unique (source_id, source_url)
```

同一個 source 的同一個 URL 只能有一筆 article。Upsert 時用 `ON CONFLICT (source_id, source_url) DO UPDATE`。

### 防線 2：content_hash 偵測內容變更（SQL lines 194, 205-206）

```sql
content_hash  text,   -- SHA-256 of content_text

create index if not exists idx_articles_hash on crawler.articles(content_hash)
  where content_hash is not null;
```

Worker 抓到文章後，算出 `content_hash`。如果 hash 和資料庫裡的一樣 → **跳過更新**（內容沒變，省 IO）。如果不同 → **更新文章**（內容有變動）。

```python
# Worker 偽碼
import hashlib

new_hash = hashlib.sha256(extracted.content_text.encode()).hexdigest()
existing = await article_repo.get_by_source_url(source_id, url)

if existing and existing.content_hash == new_hash:
    # 內容沒變，跳過
    return ProcessResult(status='skipped', reason='content_unchanged')

# 內容有變或是新文章，upsert
await article_repo.upsert(article_data, content_hash=new_hash)
```

> **為什麼不只靠 URL 唯一？**
>
> 因為同一個 URL 的文章**內容可能更新**（作者修改、網站改版）。URL 唯一只防重複插入，content_hash 才能偵測「內容有沒有真的變」。

---

## Triggers（SQL lines 354-374）

### moddatetime — 自動更新 `updated_at`

```sql
-- 8 張表套用 moddatetime（SQL lines 354-371）
foreach tbl in array array[
  'sources', 'crawl_runs', 'source_pages', 'articles',
  'article_assets', 'tags', 'publish_targets', 'article_publications'
]
```

### 不套用 moddatetime 的表

| 表 | 原因 |
|----|------|
| `crawl_queue` | Lease 狀態機用程式直接控制欄位，不需要 updated_at |
| `article_tags` | Junction table，只有 created_at，沒有 updated_at |

---

## GRANTs（SQL lines 542-564）

```sql
-- 所有 10 張表：
--   authenticated → SELECT, INSERT, UPDATE, DELETE
--   service_role  → ALL

-- 公開可讀（anon SELECT）：
--   tags, publish_targets, articles
```

> **為什麼 articles 開放 anon？**
>
> 因為爬蟲抓到的文章可能要在公開頁面展示（例如新聞聚合站）。如果你的應用不需要公開，可以移除 anon GRANT。

---

## 資料表職責速查

| 階段 | 資料表 | 角色 | SQL 行號 |
|------|--------|------|----------|
| 來源設定 | `crawler.sources` | 站台定義、規則、排程、Extractor schema | 42-65 |
| 佇列 | `crawler.crawl_queue` | 待處理 URL / 列表頁任務（lease-based） | 98-131 |
| 執行批次 | `crawler.crawl_runs` | 每次執行的批次紀錄（統計數） | 72-91 |
| 原始頁面 | `crawler.source_pages` | 原始 HTML、快照、頁面 metadata | 138-165 |
| 文章 | `crawler.articles` | 正規化文章實體（content_hash 去重） | 172-206 |
| 附件 | `crawler.article_assets` | 圖片／檔案，對應 Supabase Storage | 213-238 |
| 標籤 | `crawler.tags` / `crawler.article_tags` | 分類與標籤系統（hierarchical） | 245-270 |
| 發布目標 | `crawler.publish_targets` | WP / Notion / Ghost 等目標設定 | 277-290 |
| 發布紀錄 | `crawler.article_publications` | 每篇文章 × 每個目標的發布狀態 | 292-312 |
| 搶單 RPC | `crawler.lease_next_crawl_job()` | Lease-based 佇列消費函式 | 319-347 |
| 租戶 Helper | `crawler.get_my_project_ids()` / `has_project_access()` | JWT app_metadata 租戶隔離 | 418-448 |

---

## 重點子彈

- [ ] 所有表在 `crawler` schema，以 `project_id` 做多租戶隔離
- [ ] 租戶權限靠 JWT `app_metadata.project_ids`，前端無法竄改
- [ ] crawl_queue 有 7 種狀態，不是簡單的 pending → done
- [ ] `lease_next_crawl_job()` 用 `FOR UPDATE SKIP LOCKED` 實現多 Worker 並行搶單
- [ ] Lease 過期自動回收 — Worker 掛了不會卡死任務
- [ ] `uq_crawl_queue_pending_source_url` 防止 Cron 重複塞入相同任務
- [ ] articles 有兩道去重：URL 唯一（防重複插入）+ content_hash（偵測內容變更）
- [ ] Junction table（article_tags, article_publications）透過 FK 間接繼承租戶隔離
- [ ] moddatetime 套在 8 張表；crawl_queue 和 article_tags 不需要
- [ ] service_role policy 每張表都有 — 後端 pipeline 不受 RLS 限制

---

## 動手做

### A — 用真實程式碼觀察（推薦先做）

如果你已完成 [quickstart](00_quickstart.md)，資料庫裡已經有真實資料了。下面的練習讓你用程式碼直接驗證本文所說的機制：

**練習 1：觀察 lease 狀態機**

```bash
cd project-playwright

# 先確認佇列裡有 pending 任務
python -c "
from utils.supabase_client import get_crawler_table
rows = get_crawler_table('crawl_queue').select('url,status,lease_token').execute()
for r in rows.data: print(r['status'], r['url'][:60])
"

# 跑一次 Worker，觀察任務從 pending → leased → running → done
python ch08-supabase/04_single_job_worker.py

# 再查一次，確認狀態已更新
# 同時注意：發現的文章 URL 以 status='pending' 出現在佇列
```

**練習 2：觀察 content_hash 去重**

```bash
# 跑兩次 Worker，第二次跑同一個 URL 時，articles 的 updated_at 不變
python ch08-supabase/04_single_job_worker.py   # 第一次：新增
python ch08-supabase/04_single_job_worker.py   # 消費第二個 URL...

# 或手動再塞同一個 seed URL 回佇列，讓 Worker 重抓同一頁
python ch08-supabase/03_enqueue_urls.py
python ch08-supabase/04_single_job_worker.py
# → 在 Supabase 查 articles，比對 updated_at 時間
```

**練習 3：觀察 Partial unique index 防重複入列**

```bash
# 多次執行，佇列不會累積重複的 pending 任務
python ch08-supabase/03_enqueue_urls.py   # 第一次：新增 2 筆
python ch08-supabase/03_enqueue_urls.py   # 第二次：跳過 2 筆（輸出：新增 0 筆，跳過重複 2 筆）
```

---

### B — SQL Editor 模擬（深入理解底層）

> 以下練習需要在 `crawl_queue` 裡有資料。可先跑 quickstart 再做。

1. **模擬多 Worker 搶單**：開兩個 SQL Editor tab，同時執行 `select * from crawler.lease_next_crawl_job('worker-X')` 和 `select * from crawler.lease_next_crawl_job('worker-Y')`，觀察它們拿到**不同任務**（不重疊）。

2. **模擬 lease 過期回收**：搶單後手動執行：
   ```sql
   UPDATE crawler.crawl_queue
   SET lease_expires_at = now() - interval '1 second'
   WHERE status = 'leased';
   ```
   再用另一個 Worker 搶單，觀察它接手了剛才「過期」的任務。

3. **驗證 content_hash 去重**：
   ```sql
   -- 插入測試文章
   INSERT INTO crawler.articles (project_id, source_id, title, source_url, content_hash)
   VALUES ('test', 'src-xxx', 'Test', 'https://example.com', 'hash-abc');

   -- 用相同 hash upsert，觀察 updated_at 沒變
   INSERT INTO crawler.articles (project_id, source_id, title, source_url, content_hash)
   VALUES ('test', 'src-xxx', 'Test', 'https://example.com', 'hash-abc')
   ON CONFLICT (source_id, source_url) DO UPDATE SET content_hash = EXCLUDED.content_hash;
   ```
   （應用層在偵測到 hash 相同時根本不會觸發此 upsert；這個練習模擬萬一觸發了會怎樣）

4. **測試 Multi-Tenant 隔離**：用兩個不同 JWT（不同 `project_ids`）分別查 `crawler.sources`，確認看到不同的資料集。

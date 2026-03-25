# Head First Crawler 資料庫設計

> **對應 SQL**：`migrations/003_crawler_schema.sql` (v3.0 post-audit)
>
> **閱讀方式**：這不是 API 文件。請從頭讀到尾，跟著「動腦時間」思考，
> 答案就在下一段。跳著讀會少掉 80% 的收穫。

---

## 你在蓋什麼？

想像你要建一個**自動化新聞爬蟲系統**：

1. 你告訴系統：「去抓 TechCrunch、Hacker News、iThome 的文章」
2. 系統排隊、分配工作給多個 Worker
3. Worker 用 Playwright 打開瀏覽器、抓頁面、抽出文章
4. 文章存進資料庫、圖片傳到 Storage、標籤分類好
5. 最後推送到你的 WordPress / Notion / Ghost

整條 pipeline 需要 **10 張資料表 + 1 支 RPC 函式**。
這份教學會帶你從第一張表走到最後一行 RLS policy。

```
┌─────────────────────────────────────────────────────┐
│                    你的爬蟲系統                        │
│                                                     │
│  Scheduler ──enqueue──→ crawl_queue                 │
│                            │ lease                  │
│                            ▼                        │
│                     Playwright Worker               │
│                       │        │                    │
│                  fetch HTML   extract               │
│                       │        │                    │
│                       ▼        ▼                    │
│               source_pages  articles                │
│                            ╱   │   ╲                │
│                     assets  tags  publications      │
└─────────────────────────────────────────────────────┘
```

---

## Chapter 1：Convention —— 不先講規矩，後面全部重寫

### 🤔 動腦時間

> 你要設計 10 張表的 Primary Key。以下兩種方案，你選哪個？
>
> **A)** `id bigserial primary key` —— 自增整數，PostgreSQL 預設
>
> **B)** `id text primary key default generate_ulid()` —— 26 字元字串
>
> 先想 30 秒再往下看。

### 答案：選 B，而且沒有商量餘地

| 比較項目 | bigserial | ULID (text) |
|---------|-----------|-------------|
| 時間排序 | ❌ 無意義 | ✅ 內建時間戳，可排序 |
| 分散式安全 | ❌ 多節點會撞號 | ✅ 隨機成分，不撞號 |
| 可讀性 | `1234567` | `01H5K3J...` 看得出大概時間 |
| B-Tree 友善 | ✅ | ✅ 字典序 ≈ 時間序 |
| FK 型別一致 | 要用 `bigint` | 全部用 `text` |

**規矩 1**：所有 PK 都是 `text default generate_ulid()`。所有 FK 都是 `text`。

> `generate_ulid()` 定義在 `001_extensions.sql`，本檔不重複定義。

### 每張表都要有的欄位

```sql
-- 必備
created_at  timestamptz  not null default now()
updated_at  timestamptz  not null default now()
project_id  text         not null    -- 多租戶隔離用

-- 選配（人為產生的資料）
created_by  text                    -- 記錄是誰建的
```

**規矩 2**：`updated_at` 由 `moddatetime` trigger 自動維護，不靠應用層。

**規矩 3**：constraint 一律明確命名（`constraint ck_xxx check (...)`），不用匿名。

**規矩 4**：DDL 一律 `IF NOT EXISTS`，讓 migration 可重跑。

### ❓ 沒有笨問題

**Q：為什麼 `project_id` 不是 FK 到某個 projects 表？**
A：Crawler schema 是獨立 module。`project_id` 只是一個 tenant key，
由 JWT 的 `app_metadata.project_ids` 控制存取。
不做 FK 是為了解耦——projects 表可能在另一個 schema 裡。

**Q：`moddatetime` 是什麼？**
A：PostgreSQL extension。只要 UPDATE 觸發 trigger，就自動把指定欄位設成 `now()`。
比手寫 trigger function 簡潔，而且是 Supabase 內建支援的。

---

## Chapter 2：Sources —— 爬蟲從哪裡開始？

一切從「來源」開始。每個 source 代表一個網站或頻道。

```sql
create table if not exists crawler.sources (
  id                text primary key default public.generate_ulid(),
  project_id        text         not null,
  code              text         not null,       -- 'techcrunch', 'ithome'
  name              text         not null,       -- '科技新報'
  description       text,
  base_url          text,                        -- 'https://technews.tw'
  domain            text,                        -- 'technews.tw'
  crawler_url       text,                        -- 起始抓取 URL
  config            jsonb  not null default '{}', -- 瀏覽器設定
  extractor_schema  jsonb  not null default '{}', -- CSS selector 規則
  field_mapping     jsonb  not null default '{}', -- 欄位對應
  is_enabled        boolean not null default true,
  schedule_cron     text,                        -- '0 */6 * * *'
  last_run_at       timestamptz,
  created_by        text,
  created_at        timestamptz  not null default now(),
  updated_at        timestamptz  not null default now(),
  constraint uq_sources_code_per_project unique (project_id, code)
);
```

### 🤔 動腦時間

> `config`、`extractor_schema`、`field_mapping` 都是 JSONB。
> 為什麼不拆成獨立的關聯表？

### 答案：這些是「設定」不是「資料」

- 設定是**整塊讀、整塊寫**的。不需要 SQL 查詢 `WHERE config.timeout > 5000`。
- 每個 source 的設定結構可能不同（有的要登入、有的不用）。
- JSONB 在 PostgreSQL 裡有索引支援，但我們根本不需要查它——所以用 JSONB 最省事。

**黃金法則**：需要 WHERE/JOIN/GROUP BY 的欄位 → 獨立 column。
只需整塊讀寫的 → JSONB。

### config 長什麼樣？

```jsonc
{
  "user_agent": "Mozilla/5.0 ...",
  "headers": { "Accept-Language": "zh-TW" },
  "cookies": [{ "name": "session", "value": "abc", "domain": ".example.com" }],
  "wait_until": "networkidle",    // Playwright 等待策略
  "timeout_ms": 30000,
  "block_resources": ["image", "font", "media", "stylesheet"],
  "login_required": false
}
```

### Indexes

```sql
create index if not exists idx_sources_project
  on crawler.sources(project_id);

create index if not exists idx_sources_enabled
  on crawler.sources(project_id, is_enabled)
  where is_enabled = true;
```

為什麼 `idx_sources_enabled` 是 **partial index** (`WHERE is_enabled = true`)？

因為你幾乎只查啟用中的來源。停用的不進索引，省空間、更快。

---

## Chapter 3：Crawl Runs —— 這次跑了幾篇？

每次排程觸發（或手動觸發）就開一筆 `crawl_run`。
它追蹤的是「這次批次」的整體狀態。

```sql
create table if not exists crawler.crawl_runs (
  id                  text primary key default public.generate_ulid(),
  project_id          text         not null,
  source_id           text         not null
                      references crawler.sources(id) on delete cascade,
  run_status          text         not null default 'pending',
  started_at          timestamptz,
  finished_at         timestamptz,
  pages_found         integer      not null default 0,
  pages_fetched       integer      not null default 0,
  articles_extracted  integer      not null default 0,
  error_count         integer      not null default 0,
  logs                jsonb        not null default '[]'::jsonb,
  created_at          timestamptz  not null default now(),
  updated_at          timestamptz  not null default now(),
  constraint ck_crawl_runs_status
    check (run_status in ('pending','running','success','partial','failed'))
);
```

### ❓ 沒有笨問題

**Q：`run_status` 為什麼不用 ENUM type？**
A：PostgreSQL ENUM 修改很痛苦（加值要 `ALTER TYPE ... ADD VALUE`，無法在 transaction 裡做）。
用 `text` + `CHECK` constraint 更靈活——加新狀態只要 `ALTER TABLE ... DROP CONSTRAINT ... ADD CONSTRAINT`。

**Q：`partial` 狀態是什麼意思？**
A：部分成功。例如 100 頁抓了 80 頁，20 頁失敗。
不算 `success`（有失敗），也不算 `failed`（大部分成功）。

**Q：`logs` 為什麼用 JSONB array 而不是另開 log 表？**
A：一次 crawl run 的 log 量不大（幾十到幾百條），而且跟 run 是 1:1 綁定。
存成 JSONB array 在查詢時直接跟著 run 一起讀，不用 JOIN。

### 索引

```sql
create index if not exists idx_crawl_runs_project
  on crawler.crawl_runs(project_id);
create index if not exists idx_crawl_runs_source
  on crawler.crawl_runs(source_id, created_at desc);
```

第二個是 composite index：「查某個 source 最近的 runs」—— `WHERE source_id = ? ORDER BY created_at DESC` 一個索引搞定。

---

## Chapter 4：Crawl Queue —— Lease-Based 工作佇列

這是整個系統**最複雜、最有趣**的一張表。

### 🤔 動腦時間

> 假設你有 3 個 Worker 同時跑，每個都要從 queue 裡「搶一筆工作」。
> 如果只用 `status = 'running'` 來標記，會出什麼問題？
>
> 提示：Worker 2 搶到工作後掛掉了，再也不會回來…

### 問題：沒有「過期」機制

如果 Worker 掛掉，那筆工作就永遠卡在 `running`。
沒人會去接手它。你的 queue 裡會慢慢累積「殭屍任務」。

**解法：Lease-Based Concurrency Control**

```
pending ──lease──→ leased ──start──→ running ──→ done
                     │                  │
                     │ (expired)        ├──→ failed ──retry──→ pending
                     └──reclaim──→ pending    │
                                        └──→ dead (max retries)
                                        └──→ skipped (policy denied)
```

「Lease」就是租約。Worker 搶到工作時拿到一個 `lease_token` 和 `lease_expires_at`。
如果時間到了 Worker 沒回報完成，其他 Worker 可以接手。

### 完整 Schema

```sql
create table if not exists crawler.crawl_queue (
  id               text primary key default public.generate_ulid(),
  project_id       text         not null,
  source_id        text         not null
                   references crawler.sources(id) on delete cascade,
  url              text         not null,
  page_type        text         not null default 'article',
  priority         integer      not null default 100,     -- 越大越優先
  status           text         not null default 'pending',
  retry_count      integer      not null default 0,
  max_retries      integer      not null default 5,
  scheduled_at     timestamptz  not null default now(),
  locked_at        timestamptz,          -- legacy, 保留但不用
  finished_at      timestamptz,
  -- ⭐ lease 機制的核心欄位
  lease_token      text,                 -- UUID，每次 lease 重新產生
  leased_at        timestamptz,
  lease_expires_at timestamptz,
  worker_id        text,                 -- 是哪個 Worker 在處理
  error_code       text,
  error_message    text,
  payload          jsonb not null default '{}',
  created_at       timestamptz  not null default now(),
  constraint ck_crawl_queue_status
    check (status in ('pending','leased','running','done',
                      'failed','skipped','dead'))
);
```

### 索引：為 Lease Query 量身打造

```sql
-- 基礎索引
create index if not exists idx_crawl_queue_project
  on crawler.crawl_queue(project_id);
create index if not exists idx_crawl_queue_source
  on crawler.crawl_queue(source_id);
create index if not exists idx_crawl_queue_status
  on crawler.crawl_queue(status, priority desc);

-- ⭐ Lease query 專用 partial index
create index if not exists idx_crawl_queue_lease
  on crawler.crawl_queue(status, scheduled_at)
  where status = 'pending';

-- ⭐ 防重複：同一 source+url 不能有兩筆 pending
create unique index if not exists uq_crawl_queue_pending_source_url
  on crawler.crawl_queue(source_id, url)
  where status = 'pending';
```

### 🤔 動腦時間

> `uq_crawl_queue_pending_source_url` 這個 unique partial index 在做什麼？
> 為什麼不是全表 unique？

### 答案

同一個 URL 可能被抓很多次（retry、重新排程）。
我們只需要確保「此刻 pending 狀態裡」不會有重複的 source + url。
已經 done / failed 的可以重複出現——那是歷史紀錄。

全表 unique 會讓 retry 無法 enqueue，系統就壞了。

### ❓ 沒有笨問題

**Q：`crawl_queue` 為什麼沒有 `updated_at` 和 moddatetime trigger？**
A：它是 append-heavy 的狀態機。每次 lease / complete / fail 都會 UPDATE 特定欄位，
但語意上不需要通用的「最後更新時間」。`leased_at`、`finished_at` 已經紀錄了關鍵時間點。

**Q：`locked_at` 是什麼？**
A：舊設計的殘留。v3.0 保留了欄位但不再使用。未來清理時可以 DROP。

**Q：`priority` 越大越優先？不是越小嗎？**
A：這是設計選擇。`ORDER BY priority DESC` —— 100 是預設，
200 是高優先，50 是低優先。語意上「分數越高越重要」比較直覺。

---

## Chapter 5：Source Pages —— 原始 HTML 快照

Worker 抓到的每一頁都存在這裡。不管是列表頁還是文章頁，先存快照再說。

```sql
create table if not exists crawler.source_pages (
  id             text primary key default public.generate_ulid(),
  project_id     text         not null,
  source_id      text         not null
                 references crawler.sources(id) on delete cascade,
  crawl_run_id   text
                 references crawler.crawl_runs(id) on delete set null,
  page_type      text         not null default 'article',
  topic          text,
  url            text         not null,
  canonical_url  text,
  title          text,
  raw_html       text,                  -- ⚠️ 可能很大
  snapshot_json  jsonb,                 -- 結構化快照
  http_status    integer,
  fetched_at     timestamptz,
  last_seen_at   timestamptz,
  is_available   boolean      not null default true,
  created_at     timestamptz  not null default now(),
  updated_at     timestamptz  not null default now(),
  constraint uq_source_pages_source_url unique (source_id, url),
  constraint ck_source_pages_type
    check (page_type in ('list','article','detail','unknown'))
);
```

### 🤔 動腦時間

> `raw_html` 是 TEXT 欄位，一篇文章可能有 200KB。
> 10 萬頁 = 20GB 光是 HTML。
> 如果你執行 `SELECT * FROM source_pages WHERE source_id = ?`，會發生什麼事？

### 答案：TOAST 與查詢策略

PostgreSQL 會自動把大欄位 TOAST（壓縮 + 外部存儲），
但 `SELECT *` 還是會把它全部讀回來。

**正確做法**：
1. 查列表時永遠 `SELECT id, url, title, http_status, fetched_at ...`，不選 `raw_html`
2. 只有需要重新解析時才讀 `raw_html`
3. 未來可考慮搬到 Supabase Storage（存 .html 檔），表裡只存 `storage_path`

### 索引

```sql
create index if not exists idx_source_pages_project
  on crawler.source_pages(project_id);
create index if not exists idx_source_pages_source
  on crawler.source_pages(source_id);
create index if not exists idx_source_pages_crawl_run
  on crawler.source_pages(crawl_run_id)
  where crawl_run_id is not null;       -- partial: 不索引 NULL
create index if not exists idx_source_pages_fetched
  on crawler.source_pages(fetched_at desc);
```

`crawl_run_id` 的 partial index 很聰明——如果 run_id 是 NULL（手動匯入的頁面），
不需要進索引。省空間，而且 `WHERE crawl_run_id = ?` 查詢更快。

### snapshot_json 長什麼樣？

```jsonc
{
  "final_url": "https://example.com/article/123",  // 經過 redirect 後的真實 URL
  "title": "AI 改變世界",
  "meta": { "og:image": "https://..." },
  "links": ["https://example.com/related/1", "..."],
  "screenshots": ["storage://bucket/path/screenshot.png"],
  "extracted_selectors": { "h1": "AI 改變世界", ".author": "張三" }
}
```

---

## Chapter 6：Articles —— 正規化的成果

這是 pipeline 的**最終產物**。從 source_pages 的 raw HTML 中萃取、清洗、正規化後的文章。

```sql
create table if not exists crawler.articles (
  id                 text primary key default public.generate_ulid(),
  project_id         text         not null,
  source_id          text         not null
                     references crawler.sources(id) on delete cascade,
  source_page_id     text
                     references crawler.source_pages(id) on delete set null,
  external_id        text,               -- 來源網站的原始 ID
  title              text         not null,
  slug               text,
  author_name        text,
  author_url         text,
  abstract           text,
  content_html       text,               -- 清洗後的 HTML
  content_text       text,               -- 純文字版
  published_at       timestamptz,        -- 原文發布時間
  source_modified_at timestamptz,        -- 原文修改時間
  source_url         text         not null,
  canonical_url      text,
  lang               text,               -- 'zh-TW', 'en', 'ja'
  meta               jsonb  not null default '{}',
  extraction_data    jsonb  not null default '{}',
  is_published       boolean not null default true,
  is_available       boolean not null default true,
  content_hash       text,               -- 用於偵測內容是否更新
  created_at         timestamptz  not null default now(),
  updated_at         timestamptz  not null default now(),
  constraint uq_articles_source_url unique (source_id, source_url)
);
```

### 🤔 動腦時間

> `content_hash` 是做什麼用的？
> 提示：同一篇文章可能被抓很多次…

### 答案：冪等 Upsert

爬蟲可能每天重新抓同一篇文章。如果內容沒變，不需要更新。

```python
# 虛擬碼
new_hash = sha256(content_html)
if new_hash == existing_article.content_hash:
    skip()  # 沒變，不 UPDATE
else:
    upsert(content_html=..., content_hash=new_hash)
```

這避免了：
- 不必要的 UPDATE（觸發 trigger、寫 WAL）
- `updated_at` 被無意義地刷新
- Downstream 系統收到假的「內容更新」通知

### 兩個 JSONB 欄位的分工

**`meta`** —— 文章本身的 metadata：

```jsonc
{
  "categories": ["AI", "科技"],
  "tags": ["ChatGPT", "LLM"],
  "og_image": "https://...",
  "section": "Technology",
  "keywords": ["artificial intelligence"],
  "byline_raw": "By 張三 and 李四",
  "source_labels": ["Premium", "Exclusive"]
}
```

**`extraction_data`** —— 萃取過程的 metadata（debug 用）：

```jsonc
{
  "extractor_version": "1.2.0",
  "raw_published_at": "2024-03-15T10:00:00+08:00",
  "raw_author": "張三",
  "selector_matches": { "h1": true, ".author": true, ".date": false },
  "extraction_warnings": ["date selector missed, using og:published_time"],
  "language_confidence": 0.95,
  "ai_normalized": false
}
```

分開存的好處：`meta` 給前端用、`extraction_data` 給 debug 用。
前端永遠不需要知道 `selector_matches`。

### 索引

```sql
create index if not exists idx_articles_project
  on crawler.articles(project_id);
create index if not exists idx_articles_source
  on crawler.articles(source_id);
create index if not exists idx_articles_source_page
  on crawler.articles(source_page_id)
  where source_page_id is not null;
create index if not exists idx_articles_published
  on crawler.articles(published_at desc);
create index if not exists idx_articles_hash
  on crawler.articles(content_hash)
  where content_hash is not null;
```

`content_hash` 的 partial index 讓 upsert 的「查重」非常快。

---

## Chapter 7：配角群 —— Assets, Tags, Publishing

### Article Assets（文章附件）

圖片、影片、檔案。存到 Supabase Storage 後，這裡記錄 metadata。

```sql
create table if not exists crawler.article_assets (
  id             text primary key default public.generate_ulid(),
  project_id     text         not null,
  article_id     text         not null
                 references crawler.articles(id) on delete cascade,
  source_page_id text
                 references crawler.source_pages(id) on delete set null,
  asset_type     text         not null default 'image',
  original_url   text,
  storage_bucket text,
  storage_path   text,
  mime_type      text,
  alt_text       text,
  caption        text,
  width          integer,
  height         integer,
  checksum       text,
  sort_order     integer      not null default 0,
  created_at     timestamptz  not null default now(),
  updated_at     timestamptz  not null default now(),
  constraint ck_article_assets_type
    check (asset_type in ('image','video','file','audio'))
);
```

`sort_order` 控制顯示順序——文章裡第一張圖 `sort_order=0`，第二張 `sort_order=1`。

### Tags（標籤系統）

```sql
create table if not exists crawler.tags (
  id          text primary key default public.generate_ulid(),
  project_id  text         not null,
  taxonomy    text         not null default 'tag',
  name        text         not null,
  slug        text,
  description text,
  parent_id   text references crawler.tags(id) on delete set null,
  meta        jsonb        not null default '{}',
  created_at  timestamptz  not null default now(),
  updated_at  timestamptz  not null default now(),
  constraint uq_tags_taxonomy_name unique (taxonomy, name)
);
```

### 🤔 動腦時間

> `taxonomy` 欄位有什麼用？為什麼不直接叫 tags 表就好？

### 答案：一表多用

`taxonomy` 可以是 `'tag'`、`'category'`、`'topic'`、`'series'`。
這樣一張表就能管所有分類系統，不用開 4 張表。

`parent_id` 是自引用 FK —— 可以做出巢狀分類：
```
Technology (category)
  └── AI (category)
      └── LLM (topic)
```

### Article Tags（多對多關聯）

```sql
create table if not exists crawler.article_tags (
  article_id text not null references crawler.articles(id) on delete cascade,
  tag_id     text not null references crawler.tags(id) on delete cascade,
  created_at timestamptz not null default now(),
  primary key (article_id, tag_id)
);
```

經典的 junction table。PK 就是複合鍵 `(article_id, tag_id)`，天然防重複。

### Publish Targets & Article Publications

```sql
-- 發布目標（WordPress、Notion 等）
create table if not exists crawler.publish_targets (
  id          text primary key default public.generate_ulid(),
  project_id  text         not null,
  code        text         not null unique,   -- 'wp-main', 'notion-tech'
  name        text         not null,
  target_type text         not null,           -- 'wordpress', 'notion', etc.
  config      jsonb  not null default '{}',    -- endpoint, auth 設定
  is_enabled  boolean not null default true,
  created_by  text,
  created_at  timestamptz  not null default now(),
  updated_at  timestamptz  not null default now()
);

-- 文章 × 目標 的發布紀錄
create table if not exists crawler.article_publications (
  id                text primary key default public.generate_ulid(),
  project_id        text         not null,
  article_id        text         not null
                    references crawler.articles(id) on delete cascade,
  target_id         text         not null
                    references crawler.publish_targets(id) on delete cascade,
  remote_id         text,                -- 對方系統的 ID
  remote_url        text,                -- 對方系統的 URL
  publish_status    text not null default 'pending',
  last_published_at timestamptz,
  payload           jsonb not null default '{}',  -- 送出去的資料
  result            jsonb not null default '{}',  -- 回傳的結果
  created_at        timestamptz  not null default now(),
  updated_at        timestamptz  not null default now(),
  constraint uq_article_publications unique (article_id, target_id),
  constraint ck_article_publications_status
    check (publish_status in ('pending','published','failed','deleted'))
);
```

`payload` 存「你送出去的」，`result` 存「對方回傳的」。
出問題時可以完整重現：是我送錯了，還是對方回錯了？

---

## Chapter 8：Lease RPC —— 原子搶單

這支 RPC 是整個佇列系統的心臟。

```sql
create or replace function crawler.lease_next_crawl_job(
  p_worker_id      text,
  p_lease_duration interval default interval '5 minutes'
)
returns setof crawler.crawl_queue
language sql
security definer
set search_path = crawler
as $$
  update crawler.crawl_queue
  set
    status           = 'leased',
    lease_token      = gen_random_uuid()::text,
    leased_at        = now(),
    lease_expires_at = now() + p_lease_duration,
    worker_id        = p_worker_id
  where id = (
    select id
    from crawler.crawl_queue
    where (status = 'pending' and scheduled_at <= now())
       or (status = 'leased' and lease_expires_at < now())
    order by priority desc, scheduled_at asc
    limit 1
    for update skip locked
  )
  returning *;
$$;
```

### 逐行拆解

**`security definer`** + **`set search_path`**：
函式以「定義者」的權限執行，不是「呼叫者」。
這樣 authenticated user 可以呼叫它，但實際操作用的是 owner 權限。
`set search_path` 防止 search_path injection（安全規範要求）。

**`for update skip locked`**：
這是 PostgreSQL 的行級鎖。多個 Worker 同時呼叫時：
- `FOR UPDATE`：鎖定選到的那一行
- `SKIP LOCKED`：如果某行已被別人鎖了，跳過它找下一個

效果：**N 個 Worker 同時搶單，每個都拿到不同的工作，零衝突。**

**subquery 的 WHERE 條件**：

```sql
where (status = 'pending' and scheduled_at <= now())   -- 正常的待處理
   or (status = 'leased' and lease_expires_at < now())  -- 過期的租約回收
```

這兩行就是整個「lease 過期自動回收」的實現——不需要另外的 cron job。

### 🤔 動腦時間

> 為什麼 `lease_token` 要用 `gen_random_uuid()` 每次重新產生？
> 為什麼不用 worker_id 就好？

### 答案：防止過期後的誤操作

場景：
1. Worker-A 搶到 job-1，拿到 token-abc
2. Worker-A 掛了，lease 過期
3. Worker-B 搶到同一筆 job-1，拿到新的 token-xyz
4. Worker-A 復活了，嘗試用 token-abc 回報完成

如果只用 worker_id 驗證，Worker-A 的回報會被接受（因為它曾經是 owner）。
用 lease_token 驗證，token-abc ≠ token-xyz，回報被拒——**正確行為**。

### ❓ 沒有笨問題

**Q：`returning *` 不是在 audit 裡被標為 violation 嗎？**
A：是的，audit (V-25) 建議改為明確列出欄位。
v3.0 保留了 `returning *` 是為了簡化，但在生產環境建議改為：
`returning id, source_id, url, page_type, lease_token, ...`

**Q：`p_lease_duration` 預設 5 分鐘夠嗎？**
A：對大多數頁面抓取夠了。如果某些 source 需要更久（例如要等 JavaScript render），
呼叫時可以傳 `interval '15 minutes'`。

---

## Chapter 9：Triggers —— moddatetime 自動更新

不要手動管 `updated_at`。讓 trigger 做。

```sql
do $$
declare
  tbl text;
begin
  foreach tbl in array array[
    'sources', 'crawl_runs', 'source_pages', 'articles',
    'article_assets', 'tags', 'publish_targets', 'article_publications'
  ]
  loop
    execute format('
      drop trigger if exists trg_%1$s_updated_at on crawler.%1$s;
      create trigger trg_%1$s_updated_at
        before update on crawler.%1$s
        for each row execute function moddatetime(updated_at);
    ', tbl);
  end loop;
end;
$$;
```

注意 `crawl_queue` **不在列表裡**——因為它是狀態機，不需要通用的 `updated_at`。

### 為什麼用 DO $$ 迴圈？

8 張表 × 2 行 SQL = 16 行重複代碼。
用迴圈 = 3 行邏輯 + 1 個 array。DRY。

而且 `drop trigger if exists` + `create trigger` 確保重跑 migration 不會報錯。

---

## Chapter 10：RLS —— 多租戶安全，不是選配

這是整份 SQL 裡**最重要但最容易跳過**的部分。

### 🤔 動腦時間

> 如果你忘了在某張表上 `ENABLE ROW LEVEL SECURITY`，
> 而且你用 `anon` key 從前端呼叫 Supabase…會怎樣？

### 答案：全部資料都看得到

沒有 RLS 的表 = 所有人都能讀寫所有 row。
Supabase 的 `anon` key 是公開的（寫在前端 JS 裡）。
**忘了開 RLS = 資料完全裸奔。**

### Step 1：全部開啟 RLS

```sql
do $$
declare
  tbl text;
begin
  foreach tbl in array array[
    'sources', 'crawl_runs', 'crawl_queue', 'source_pages',
    'articles', 'article_assets', 'tags', 'article_tags',
    'publish_targets', 'article_publications'
  ]
  loop
    execute format(
      'alter table crawler.%I enable row level security;', tbl
    );
  end loop;
end;
$$;
```

10 張表，一個都不能少。

### Step 2：Helper Function —— JWT 裡的 project_ids

```sql
create or replace function crawler.get_my_project_ids()
returns text[]
language sql stable security definer
set search_path = crawler
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
```

這個函式從 JWT 的 `app_metadata` 裡取出 `project_ids` 陣列。

JWT 長這樣：
```jsonc
{
  "sub": "user-uuid",
  "app_metadata": {
    "project_ids": ["demo-project", "prod-project"]
  }
}
```

設定方式（在 Supabase Dashboard 或 SQL）：
```sql
update auth.users
set raw_app_meta_data =
  raw_app_meta_data || '{"project_ids":["demo-project"]}'::jsonb
where id = 'user-uuid';
```

### Step 3：Access Check Helper

```sql
create or replace function crawler.has_project_access(p_project_id text)
returns boolean
language sql stable security definer
set search_path = crawler
as $$
  select p_project_id = ANY(crawler.get_my_project_ids());
$$;
```

### Step 4：Policy 模式

**有 `project_id` 欄位的表**（sources, crawl_runs, crawl_queue, source_pages, articles, article_assets, tags, publish_targets）：

```sql
-- 以 sources 為例（其他表用迴圈批量套用）
create policy "sources_select" on crawler.sources
  for select to authenticated
  using (crawler.has_project_access(project_id));

create policy "sources_insert" on crawler.sources
  for insert to authenticated
  with check (crawler.has_project_access(project_id));

create policy "sources_update" on crawler.sources
  for update to authenticated
  using (crawler.has_project_access(project_id));

create policy "sources_delete" on crawler.sources
  for delete to authenticated
  using (crawler.has_project_access(project_id));

-- 後端 pipeline 用 service_role，不受限
create policy "sources_service_role" on crawler.sources
  for all to service_role using (true) with check (true);
```

**沒有 `project_id` 的 junction table**（article_tags, article_publications）：

```sql
-- 透過 FK 繼承安全性（JOIN 時 parent 表的 RLS 會擋）
create policy "article_tags_select" on crawler.article_tags
  for select to authenticated, anon using (true);
create policy "article_tags_insert" on crawler.article_tags
  for insert to authenticated with check (true);
-- ... update, delete 類似
```

### 🤔 動腦時間

> article_tags 的 policy 是 `using (true)`——任何人都能讀？
> 那安全性在哪裡？

### 答案：透過 JOIN 繼承

前端不會直接查 `article_tags`。它會：
```sql
select t.name
from crawler.article_tags at
join crawler.articles a on a.id = at.article_id
join crawler.tags t on t.id = at.tag_id
where a.id = 'some-article-id'
```

`articles` 表有 RLS（只能看自己 project 的）。
如果使用者沒有那篇文章的權限，JOIN 就不會回傳任何東西。
article_tags 本身的 `using(true)` 只是「不額外擋」——安全性由 parent 表保證。

### Step 5：GRANTs

```sql
-- 所有 crawler 表：authenticated 可 SELECT/INSERT/UPDATE/DELETE
-- service_role 可 ALL
-- 特定表（tags, publish_targets, articles）：anon 可 SELECT
```

RLS policy 定義了「哪些 row 看得到」，GRANT 定義了「有沒有這個操作權限」。
兩者缺一不可：

| | 沒有 GRANT | 有 GRANT |
|---|---|---|
| **沒有 RLS policy** | ❌ 無法操作 | ⚠️ 看到全部（危險） |
| **有 RLS policy** | ❌ 無法操作 | ✅ 只看到有權限的 row |

---

## Chapter 11：完整 ER 關係圖

```
crawler.sources ─────────────┬──────────────────────────────────┐
  │ PK: id                   │                                  │
  │                          │                                  │
  ├──< crawler.crawl_runs    │                                  │
  │     FK: source_id        │                                  │
  │     │                    │                                  │
  │     └──< crawler.source_pages                               │
  │           FK: source_id, crawl_run_id                       │
  │           │                                                 │
  │           └──< crawler.articles ──< crawler.article_assets  │
  │                 FK: source_id,       FK: article_id,        │
  │                     source_page_id       source_page_id     │
  │                 │                                           │
  │                 ├──< crawler.article_tags                   │
  │                 │     FK: article_id, tag_id                │
  │                 │                                           │
  │                 └──< crawler.article_publications           │
  │                       FK: article_id, target_id             │
  │                                                            │
  ├──< crawler.crawl_queue                                     │
  │     FK: source_id                                          │
  │                                                            │
  └── crawler.tags (self-ref via parent_id)                    │
       FK: parent_id                                           │
                                                               │
  crawler.publish_targets ─────────────────────────────────────┘
    FK: (article_publications.target_id)
```

**所有 FK 都是 `text`（ULID）**。型別一致，JOIN 不需要 cast。

---

## Chapter 12：重點摘要（撕下來貼冰箱）

### Convention Checklist

- [ ] PK: `text default generate_ulid()`
- [ ] FK: `text references ...`
- [ ] 每張表都有 `project_id`, `created_at`, `updated_at`
- [ ] `updated_at` 由 moddatetime trigger 維護
- [ ] Constraint 明確命名：`constraint ck_xxx check (...)`
- [ ] DDL 一律 `if not exists`
- [ ] RLS 每張表都開
- [ ] 每張表都有 service_role + authenticated policy
- [ ] 所有 FK 欄位都有索引
- [ ] RPC function: `security definer` + `set search_path`

### 表職責速查

| 表名 | 職責 | 資料量趨勢 |
|------|------|-----------|
| sources | 來源定義、爬蟲設定 | 低（幾十筆） |
| crawl_runs | 批次執行紀錄 | 中（每天幾筆） |
| crawl_queue | 待處理 URL 佇列 | 高（需清理策略） |
| source_pages | 原始 HTML 快照 | 高（需 partition 規劃） |
| articles | 正規化文章 | 中（主要查詢對象） |
| article_assets | 圖片/檔案 metadata | 中 |
| tags | 標籤/分類 | 低 |
| article_tags | 文章 ↔ 標籤 | 中 |
| publish_targets | 發布目標設定 | 低 |
| article_publications | 發布紀錄 | 中 |

### 索引策略速查

| 索引類型 | 用途 | 範例 |
|---------|------|------|
| FK index | 加速 JOIN 和 CASCADE DELETE | `idx_articles_source(source_id)` |
| Partial index | 只索引有意義的子集 | `WHERE status = 'pending'` |
| Composite index | 一個索引服務 WHERE + ORDER BY | `(source_id, created_at DESC)` |
| Unique partial | 只在特定狀態下防重複 | `(source_id, url) WHERE status='pending'` |

### RLS 模式速查

| 表類型 | Policy 邏輯 |
|--------|------------|
| 有 project_id 的業務表 | `has_project_access(project_id)` |
| junction table（無 project_id） | `using(true)` + 透過 JOIN 繼承 |
| 所有表 | `service_role` policy: `using(true) with check(true)` |

---

## 下一步

讀完 schema 後，建議按以下順序繼續：

1. **[04_data-flow-overview.md](04_data-flow-overview.md)** — pipeline 資料流與 Python 型別對應
2. **[05_worker-architecture.md](05_worker-architecture.md)** — 部署方案與模組結構
3. **[06_worker-consume-loop-python.md](06_worker-consume-loop-python.md)** — 消費迴圈實作
4. **[07_worker-retry-and-anti-ban.md](07_worker-retry-and-anti-ban.md)** — 重試策略與反封鎖

---

> **歷史紀錄**：本 schema 從 v1.0（bigserial PK、無 RLS）經過 29 項 audit violation 修正，
> 演進到 v3.0。完整 audit 報告見 [02_AUDIT-vs-guidelines.md](02_AUDIT-vs-guidelines.md)（歷史參考）。

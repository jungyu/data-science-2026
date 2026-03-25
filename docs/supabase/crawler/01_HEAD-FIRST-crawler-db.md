# Head First: Crawler Database Design with Supabase

> 用你手上「有 29 個違規」的爬蟲 Schema，一步一步改成生產級架構。
> 每個 Stage 先看「錯在哪」，再學「為什麼」，最後動手「改成對的」。

---

## 你會學到什麼

```
Stage 1  為什麼 ID 不能用 bigserial？                    (PK & FK 型別)
Stage 2  每張表少了哪些「必備零件」？                      (欄位紀律)
Stage 3  為什麼 CREATE TABLE 後面還有一堆東西？            (Index 策略)
Stage 4  RLS 是什麼？為什麼你「以為沒開」其實更危險？       (安全層)
Stage 5  如果不處理，三個月後你的 DB 會怎麼死？             (規模化)
Stage 6  完成品長什麼樣子？                               (Corrected SQL)
```

---

## 在開始之前：你現在的 Schema 長這樣

打開 `03_playwright_crawler_schema.sql`，你會看到 10 張表：

```
sources ──→ crawl_runs
        ──→ crawl_queue
        ──→ source_pages ──→ articles ──→ article_assets
                                     ──→ article_tags ──→ tags
                                     ──→ article_publications ──→ publish_targets
```

看起來結構清楚對吧？

**但是這份 SQL 拿去 code review，會被打回來 29 次。**

別擔心——這正是我們要用來學習的素材。

---

# Stage 1: 地基搞錯，整棟歪掉

## 你的 ID 用錯了

打開你的 `sources` 表定義：

```sql
create table public.sources (
  id bigserial primary key,    -- ← 這行就是問題
  ...
);
```

然後看所有 FK：

```sql
source_id bigint not null references public.sources(id)    -- ← bigint 配 bigserial
```

### 想一想：bigserial 有什麼問題？

`bigserial` 就是 `BIGINT` + 自動遞增。看起來很直覺，但在 Supabase 資料科學專案裡：

```
bigserial 的問題：

  1. 不可排序 by 時間         你拿到 id=42，不知道它是今天還是去年
  2. B-Tree 效能還 OK         但比不上 ULID 的順序寫入
  3. 跟 Supabase Auth 打架    auth.users 用 UUID → 你的表用 BIGINT → 型別不一致
  4. FK 型別混亂              有些表 bigint，以後接 Auth 又變 UUID，炸了
```

### 正確做法：ULID (TEXT)

```
ULID = 時間戳 (48 bit) + 隨機 (80 bit)
     = 26 字元 Crockford Base32
     = 例如 01HXYZ3ABCDEFGHJKMNPQRSTV

特性：
  - 按時間排序 ✅ (前 10 字元是 timestamp)
  - 全球唯一 ✅
  - B-Tree 友善 ✅ (順序寫入，不會頁分裂)
  - 存成 TEXT ✅ (跟 FK 型別統一)
```

### 看看正確版本長什麼樣（e-Commerce 的做法）

```sql
-- e-Commerce schema 的做法
create table if not exists public.users (
  id text primary key default generate_ulid(),    -- TEXT，不是 BIGINT
  ...
);
```

所有 FK 也統一用 TEXT：

```sql
source_id text not null references public.sources(id)    -- TEXT 配 TEXT
```

### 還沒完——你需要 generate_ulid() 函式

你的 schema 載入了 `pgcrypto` 和 `uuid-ossp`，但 `generate_ulid()` 不會從天上掉下來。你必須自己定義它。

```sql
-- 這個函式必須在所有 CREATE TABLE 之前
create or replace function public.generate_ulid()
returns text
language plpgsql
volatile
as $$
declare
  timestamp  bigint;
  output     text := '';
  unix_ts    bigint;
  encoding   char[] := string_to_array('0123456789ABCDEFGHJKMNPQRSTVWXYZ', null);
  i          int;
  rand_bytes bytea;
begin
  unix_ts := (extract(epoch from clock_timestamp()) * 1000)::bigint;
  for i in reverse 9..0 loop
    output := output || encoding[1 + (unix_ts % 32)::int];
    unix_ts := unix_ts >> 5;
  end loop;
  rand_bytes := gen_random_bytes(10);
  for i in 0..9 loop
    output := output || encoding[1 + (get_byte(rand_bytes, i) % 32)];
  end loop;
  return output;
end;
$$;
```

### `uuid-ossp`？拿掉

你的 schema 載入了 `uuid-ossp`，但：
- `generate_ulid()` 用的是 `pgcrypto`（`gen_random_bytes`）
- lease RPC 的 `gen_random_uuid()` 也來自 `pgcrypto`
- 業務表不用 UUID

所以 `uuid-ossp` 是多餘的，拿掉。

---

### 動動腦：為什麼 FK 型別不一致會炸？

假設你有：

```sql
-- 表 A 用 BIGINT
create table sources (id bigserial primary key);

-- 表 B 用 TEXT（因為未來要接 ULID）
create table articles (id text primary key default generate_ulid());

-- 然後你想 JOIN：
select * from articles a
join sources s on a.source_id = s.id;
-- ❌ ERROR: operator does not exist: text = bigint
```

**型別不一致 = JOIN 爆炸。整個系統的 PK/FK 必須統一。**

---

### Stage 1 自我檢查

```
□ generate_ulid() 函式已定義
□ 所有表的 PK 改成 id text primary key default generate_ulid()
□ 所有 FK 改成 text（不是 bigint）
□ 移除 uuid-ossp extension
□ 只保留 pgcrypto extension
```

---

# Stage 2: 每張表少了什麼零件？

## 一張表的「必備組件」

根據 guidelines，每張「業務表」必須有：

```sql
-- === 必備零件 ===
id          text primary key default generate_ulid(),  -- PK
created_at  timestamptz not null default now(),         -- 何時建立
updated_at  timestamptz not null default now(),         -- 何時更新
```

如果有多租戶需求，加：
```sql
project_id  text not null references projects(id) on delete cascade,
```

如果是使用者操作產生的資料，加：
```sql
created_by  text not null references users(id),
```

## 你的表少了什麼？

```
表名                 | updated_at | trigger | project_id | 判定
---------------------|------------|---------|------------|------
sources              | ✅          | ✅       | ❌          | 少 project_id
crawl_runs           | ❌          | ❌       | ❌          | 少 updated_at + trigger
crawl_queue          | ❌*         | ❌       | ❌          | 少 updated_at + trigger
source_pages         | ✅          | ✅       | ❌          | 少 project_id
articles             | ✅          | ✅       | ❌          | 少 project_id
article_assets       | ✅          | ✅       | ❌          | OK（結構完整）
tags                 | ❌          | ❌       | ❌          | 少 updated_at
publish_targets      | ❌          | ❌       | ❌          | 少 updated_at + trigger
article_publications | ❌          | ❌       | ❌          | 少 created_at + updated_at
article_tags         | ❌          | ❌       | ❌          | 聯結表，可以不要
```

### 為什麼 updated_at 這麼重要？

```
沒有 updated_at 的後果：

  1. 你不知道一筆 crawl_run 最後更新是什麼時候
  2. 你不知道一個 publish_target 的 config 何時被改過
  3. 你做 cache invalidation 沒有依據
  4. 你做 ETL sync 沒辦法做 incremental update
  5. debug 的時候你只知道「建立時間」，不知道「最後異動時間」
```

### 修復：加上 updated_at + trigger

trigger 函式的名稱，guidelines 建議用 `update_updated_at_column()`。
但其實你也可以用 `moddatetime` extension（跟 e-Commerce schema 一樣），更簡潔：

```sql
-- 方法 A：手寫 trigger function（你現在的做法，但名字要改）
create or replace function public.update_updated_at_column()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

-- 方法 B：用 moddatetime extension（更簡潔）
create extension if not exists moddatetime;
-- 然後 trigger 寫法：
create trigger trg_sources_updated_at
  before update on public.sources
  for each row execute function moddatetime(updated_at);
```

### UNIQUE 約束：一定要命名

你的 schema：
```sql
unique (source_id, url)           -- ← 沒名字
```

六個月後你要改這個約束，你得這樣找：
```sql
-- 你必須先查出系統自動產生的名字
select constraint_name from information_schema.table_constraints
where table_name = 'source_pages' and constraint_type = 'UNIQUE';
-- 結果可能是 source_pages_source_id_url_key  ← 自動命名，不直覺
```

正確做法——命名它：
```sql
constraint uq_source_pages_source_url unique (source_id, url)
```

以後修改就很明確：
```sql
alter table source_pages drop constraint uq_source_pages_source_url;
```

### 還有一個死掉的欄位

`crawl_queue` 有個 `locked_at` 欄位（line 88），但整個系統都用 `leased_at` 做 lease。`locked_at` 從來沒被使用過。

**規則：不會用的欄位，不要留。它會困擾每個讀 schema 的人。**

---

### project_id：要不要加？

這是一個架構決策，不是程式 bug。

```
場景 A: 這個 crawler 只給一個專案用
  → 不加 project_id，但在文件裡說明「此模組為 single-tenant」

場景 B: 未來可能多個專案共用同一套 crawler
  → 每張表加 project_id
  → 所有查詢加上 WHERE project_id = $1
  → RLS policy 走 is_project_member(project_id)
```

**現在先做的建議**：在 `sources` 加上 `project_id`（來源站歸屬哪個專案），其他表透過 FK 間接繼承。

---

### Stage 2 自我檢查

```
□ 所有表有 created_at + updated_at（除 article_tags 聯結表）
□ 所有有 updated_at 的表有對應 trigger
□ trigger function 用統一名稱
□ 所有 UNIQUE 約束有明確命名
□ 所有 CHECK 約束有明確命名
□ 移除 locked_at 死欄位
□ DDL 全部加上 IF NOT EXISTS（冪等）
□ publish_targets.target_type 加上 CHECK 約束
```

---

# Stage 3: 沒有 Index，你的查詢在裸奔

## 你知道 FK 欄位沒 index 會怎樣嗎？

當你 `DELETE FROM sources WHERE id = 'xxx'` 時：
PostgreSQL 必須檢查所有引用 `sources(id)` 的表，確認沒有 orphan row。

**如果 FK 欄位沒 index → 全表掃描。**

```
你的 7 個 FK 欄位缺 index：

  crawl_queue.source_id          ← 每次刪 source 都掃描整張 queue
  source_pages.crawl_run_id      ← 刪 crawl_run 時掃描所有 pages
  articles.source_page_id        ← 刪 source_page 時掃描所有 articles
  article_assets.source_page_id  ← 同上
  article_tags.tag_id            ← 刪 tag 時掃描所有 article_tags
  article_publications.target_id ← 刪 publish_target 時掃描所有 publications
  tags.parent_id                 ← 刪 parent tag 時掃描所有 tags
```

### 修復：Tier 1 Index（每個 FK 一個）

```sql
create index if not exists idx_crawl_queue_source     on public.crawl_queue(source_id);
create index if not exists idx_source_pages_run       on public.source_pages(crawl_run_id);
create index if not exists idx_articles_source_page   on public.articles(source_page_id);
create index if not exists idx_assets_source_page     on public.article_assets(source_page_id);
create index if not exists idx_article_tags_tag       on public.article_tags(tag_id);
create index if not exists idx_publications_target    on public.article_publications(target_id);
create index if not exists idx_tags_parent            on public.tags(parent_id);
```

## 你的 Lease 查詢也在裸奔

lease RPC 的 WHERE 子句：

```sql
WHERE (status = 'pending' AND scheduled_at <= now())
   OR (status = 'leased' AND lease_expires_at < now())
ORDER BY priority DESC, scheduled_at ASC
```

你現在只有 `idx_crawl_queue_status(status, priority desc)`。

**問題**：
```
PostgreSQL 看到 OR 條件，通常放棄用 index，改成 seq scan。
即使用了 index，也只能先按 status 篩選，再逐一比 scheduled_at。
```

**正確做法——Partial Index（只索引你在意的子集）**：

```sql
-- 待處理的工作：按優先級和排程時間排序
create index if not exists idx_crawl_queue_pending
  on public.crawl_queue(priority desc, scheduled_at asc)
  where status = 'pending';

-- 過期的 lease：按過期時間排序
create index if not exists idx_crawl_queue_expired_lease
  on public.crawl_queue(lease_expires_at asc)
  where status = 'leased';
```

**Partial Index 的好處**：
```
1. 只索引符合 WHERE 條件的 row → index 更小
2. 查詢時直接命中 → 不掃描 done/failed/dead 的垃圾
3. 寫入時只有 pending/leased 的 row 需要維護 index → 寫入更快
```

## Composite Index：常見查詢模式

你的 API 一定會做這些查詢：

```sql
-- 「列出某 source 下最新的 articles」
SELECT id, title, published_at FROM articles
WHERE source_id = $1 ORDER BY published_at DESC LIMIT 50;

-- 「列出某 source 下的 pages，按類型分」
SELECT id, url, page_type FROM source_pages
WHERE source_id = $1 AND page_type = 'article' ORDER BY fetched_at DESC LIMIT 50;
```

沒有 composite index → seq scan + sort。加上：

```sql
create index if not exists idx_articles_source_published
  on public.articles(source_id, published_at desc);

create index if not exists idx_source_pages_source_type
  on public.source_pages(source_id, page_type, fetched_at desc);
```

---

### Index 決策快速流程

```
新增表時問自己：
  Q1: 有 FK 欄位？       → Tier 1 單欄 index（每個 FK 一個）
  Q2: 有 list API？      → Tier 3 composite index（scope + sort）
  Q3: 有特定狀態高頻查？  → Tier 4 partial index（WHERE status = 'xxx'）
  Q4: 要查 JSONB 內容？  → Tier 5 GIN index（慎用，確定需要才加）
```

---

### Stage 3 自我檢查

```
□ 所有 FK 欄位有單欄 index
□ crawl_queue 有 partial index 給 lease 查詢
□ articles、source_pages 有 composite index 給 list 查詢
□ 沒有多餘的 index（同一表不超過 5 個 composite）
```

---

# Stage 4: RLS——你以為門沒鎖，其實是門拆了

## 先理解：RLS 沒開 = 任何 authenticated 使用者可以讀寫所有資料

你的 schema：

```sql
-- 只有 3 張表開了 RLS
alter table public.sources enable row level security;
alter table public.articles enable row level security;
alter table public.article_assets enable row level security;

-- 剩下 7 張表：完全沒有 RLS
-- crawl_runs, crawl_queue, source_pages, tags, article_tags,
-- publish_targets, article_publications
```

### 為什麼沒開 RLS 比開了但寫錯更危險？

```
                  RLS 沒開         RLS 開了但 policy 寫錯
                  ──────────       ─────────────────────
authenticated     可讀寫全部 ❌     可能讀到不該看的 ❌
anon              可讀寫全部 ❌❌    看 policy 設定
service_role      可讀寫全部 ✅     可讀寫全部 ✅

結論：RLS 沒開 = 大門拆掉了。
     RLS 開了 = 至少有門，policy 是鎖頭。
```

### 規則：所有 public 表必須啟用 RLS，無例外

```sql
alter table public.crawl_runs enable row level security;
alter table public.crawl_queue enable row level security;
alter table public.source_pages enable row level security;
alter table public.tags enable row level security;
alter table public.article_tags enable row level security;
alter table public.publish_targets enable row level security;
alter table public.article_publications enable row level security;
```

## Policy 怎麼寫？

你現在的 policy：

```sql
create policy "dev_all_access" on public.sources for all using (true);
```

**問題**：
1. `for all` 沒指定 role → 所有 role 都適用（包含 anon）
2. `using (true)` → 任何人都能讀
3. 沒有 `WITH CHECK` → 任何人都能寫
4. 沒有 service_role 專屬 policy

### 正確做法：最小權限 Policy

對 crawler 來說，大部分操作是 ETL（service_role），少部分是 Dashboard 讀取（authenticated）：

```sql
-- ===== 每張表都要這兩個 policy =====

-- 1. service_role：ETL pipeline 完整存取
create policy "sources_service_role"
  on public.sources for all to service_role
  using (true) with check (true);

-- 2. authenticated：Dashboard 唯讀
create policy "sources_read_access"
  on public.sources for select to authenticated
  using (true);   -- 如果有 project_id，改成 is_project_member(project_id)
```

### 特殊考量：publish_targets 有敏感資料

`publish_targets.config` 可能包含 API token、OAuth credentials。
即使是 authenticated 使用者，也不應該看到所有 target 的 config。

```sql
-- 不要讓 authenticated 直接看 config
create policy "publish_targets_read_access"
  on public.publish_targets for select to authenticated
  using (true);
-- 但查詢時不要 SELECT config，只選需要的欄位
```

## Lease RPC 也要修

你的 RPC function：

```sql
create or replace function public.lease_next_crawl_job(...)
language sql
as $$
  ...
  returning *;       -- ❌ SELECT *
$$;
```

**三個問題**：

```
1. RETURNING *       → 回傳所有欄位（包含不需要的）
2. 沒有 SET search_path = public  → 安全風險
3. 沒有 statement_timeout         → 可能永遠卡住
```

修復：

```sql
create or replace function public.lease_next_crawl_job(
  p_worker_id text,
  p_lease_duration interval default interval '5 minutes'
)
returns table (
  id text, source_id text, url text, page_type text,
  lease_token text, retry_count int, max_retries int, payload jsonb
)
language sql
set search_path = public
set statement_timeout = '5s'
as $$
  update public.crawl_queue
  set
    status = 'leased',
    lease_token = gen_random_uuid()::text,
    leased_at = now(),
    lease_expires_at = now() + p_lease_duration,
    worker_id = p_worker_id
  where id = (
    select id from public.crawl_queue
    where (status = 'pending' and scheduled_at <= now())
       or (status = 'leased' and lease_expires_at < now())
    order by priority desc, scheduled_at asc
    limit 1
    for update skip locked
  )
  returning
    id, source_id, url, page_type,
    lease_token, retry_count, max_retries, payload;
$$;
```

## GRANT：別忘了權限

沒有 GRANT，即使 RLS policy 寫了也沒用：

```sql
-- 對每張表：
grant select on public.sources to authenticated;
grant all on public.sources to service_role;

-- 對 RPC function：
grant execute on function public.lease_next_crawl_job(text, interval) to service_role;
```

---

### Stage 4 自我檢查

```
□ 所有 10 張表都有 ALTER TABLE ... ENABLE ROW LEVEL SECURITY
□ 每張表至少有 service_role policy（for all using (true) with check (true))
□ 每張表有 authenticated 的 read policy（至少 SELECT）
□ publish_targets 的敏感欄位有額外保護
□ lease RPC function 有 SET search_path + statement_timeout
□ lease RPC 回傳明確欄位（不是 RETURNING *）
□ 所有表有 GRANT 語句
□ RPC function 有 GRANT EXECUTE
```

---

# Stage 5: 三個月後你的 DB 會怎麼死

## 死法一：source_pages 表膨脹到爆

`source_pages` 存了 `raw_html`（每筆 100KB~1MB），而且是 append-heavy（每次爬就新增）。

```
假設：
  - 10 個 source，每個每天抓 100 頁
  - 1000 頁/天 × 30 天 = 30,000 頁/月
  - 30,000 × 平均 200KB = 6GB/月
  - 一年後：72GB

沒有 partition → PostgreSQL 每次 VACUUM 都掃描 72GB
沒有 retention → 資料永遠不刪
沒有 autovacuum tuning → dead tuple 追不上
```

### 修復：Partition + Retention + Autovacuum

```sql
-- 1. Partition by 月（PK 必須包含 partition key）
create table if not exists public.source_pages (
  id text not null default generate_ulid(),
  ...
  created_at timestamptz not null default now(),
  primary key (id, created_at)       -- ← 必須包含 created_at
) partition by range (created_at);

-- 2. 建立 partition（每月一張）
create table if not exists source_pages_2026_03
  partition of source_pages
  for values from ('2026-03-01') to ('2026-04-01');

-- 3. Autovacuum 調校
alter table public.source_pages
  set (autovacuum_vacuum_scale_factor = 0.05);

-- 4. Retention：90 天後 archive + delete
-- （用 cron job 執行）
```

### 重要限制：Partition 表的 PK 必須包含 partition key

```
❌ primary key (id)                    → PostgreSQL 拒絕
✅ primary key (id, created_at)        → OK，因為包含 partition key

為什麼？因為 PostgreSQL 要確保 PK 的 uniqueness，
但每個 partition 是獨立的表，跨 partition 無法保證 uniqueness。
包含 partition key 後，每個 partition 內部就能保證了。
```

## 死法二：crawl_queue 無限增長

完成的 job 留在 queue 裡永遠不刪：

```
一個月後：
  pending: 50
  leased: 5
  done: 29,000    ← 垃圾
  failed: 500     ← 垃圾
  dead: 200       ← 垃圾

lease 查詢必須掃描 29,755 筆才能找到那 50 筆 pending。
（即使有 partial index 也會有 bloat 問題）
```

### 修復：設計 Retention Policy

```
crawl_queue 的生命週期：

  status=done    → 7 天後刪除
  status=failed  → 30 天後刪除（保留用於分析錯誤模式）
  status=dead    → 30 天後 archive → 刪除
  status=skipped → 7 天後刪除
```

實作（cron job）：

```sql
-- 每天跑一次
delete from crawl_queue where ctid in (
  select ctid from crawl_queue
  where status in ('done', 'skipped')
    and finished_at < now() - interval '7 days'
  limit 50000
);
```

## 死法三：raw_html 拖垮所有查詢

`source_pages.raw_html` 是 TEXT 型別，平均 200KB。
即使 PostgreSQL 會用 TOAST 壓縮，每次 `SELECT *` 還是會 detoast。

```sql
-- ❌ 你的 Python code 如果這樣寫：
result = supabase.table('source_pages').select('*').execute()
-- → 每筆都拉出 200KB raw_html

-- ✅ 正確：明確選欄位
result = supabase.table('source_pages') \
  .select('id, url, title, http_status, fetched_at') \
  .execute()
```

**更好的做法**：把 `raw_html` 搬到 Supabase Storage：

```
source_pages 表只存：
  raw_html_path text    → 'raw_pages/2026/03/01HXYZ....html.gz'

Storage 存：
  bucket: raw-pages
  path:   raw_pages/2026/03/01HXYZ....html.gz
```

---

### Stage 5 自我檢查

```
□ source_pages 已 partition by range (created_at)
□ append-heavy 表設定 autovacuum_vacuum_scale_factor = 0.05
□ crawl_queue 有 retention policy（cron job 定期清理）
□ raw_html 考慮搬到 Storage（或至少永遠不 SELECT *）
□ 所有查詢 source_pages 時都包含 created_at 時間範圍（觸發 partition pruning）
```

---

# Stage 6: 完成品——一份 Migration 該有的所有東西

把上面所有修復組合起來，一張表（以 `sources` 為例）的完整 migration 應該長這樣：

```sql
-- ============================================================
-- Migration: 20260325120000_public_sources.sql
-- ============================================================

-- 1. Table
create table if not exists public.sources (
  id                text primary key default generate_ulid(),
  project_id        text not null references projects(id) on delete cascade,
  code              text not null,
  name              text not null,
  description       text,
  base_url          text,
  domain            text,
  crawler_url       text,
  config            jsonb not null default '{}'::jsonb,
  extractor_schema  jsonb not null default '{}'::jsonb,
  field_mapping     jsonb not null default '{}'::jsonb,
  is_enabled        boolean not null default true,
  schedule_cron     text,
  last_run_at       timestamptz,
  created_by        text references users(id),
  created_at        timestamptz not null default now(),
  updated_at        timestamptz not null default now(),

  constraint uq_sources_project_code unique (project_id, code)
);

-- 2. Indexes
create index if not exists idx_sources_project
  on public.sources(project_id);
create index if not exists idx_sources_project_enabled
  on public.sources(project_id, is_enabled)
  where is_enabled = true;

-- 3. Trigger
create trigger trg_sources_updated_at
  before update on public.sources
  for each row execute function moddatetime(updated_at);

-- 4. RLS
alter table public.sources enable row level security;

-- 5. Policies
create policy "sources_service_role"
  on public.sources for all to service_role
  using (true) with check (true);

create policy "sources_read_access"
  on public.sources for select to authenticated
  using (true);

-- 6. Grants
grant select on public.sources to authenticated;
grant all on public.sources to service_role;
```

### 對照你原本的版本

```
原本的 sources：
  ✅ 有 created_at, updated_at, trigger
  ❌ bigserial PK
  ❌ bigint FK
  ❌ 沒有 project_id
  ❌ 沒有 IF NOT EXISTS
  ❌ UNIQUE 沒命名
  ❌ RLS policy 太寬鬆
  ❌ 沒有 GRANT
  ❌ 沒有 created_by

改好的 sources：
  ✅ ULID PK (text)
  ✅ project_id (text FK)
  ✅ IF NOT EXISTS
  ✅ 命名的 UNIQUE constraint
  ✅ service_role + authenticated policies
  ✅ GRANT 語句
  ✅ created_by
  ✅ moddatetime trigger
```

---

# 總結：一張圖看完所有規則

```
┌─────────────────────────────────────────────────────┐
│                一張表的完整生命                        │
│                                                     │
│  CREATE TABLE IF NOT EXISTS                         │
│    id text primary key default generate_ulid()      │
│    project_id text not null references projects(id) │
│    created_at timestamptz not null default now()    │
│    updated_at timestamptz not null default now()    │
│    CHECK constraints 有名字                          │
│    UNIQUE constraints 有名字                         │
│                                                     │
│  CREATE INDEX IF NOT EXISTS                         │
│    每個 FK 一個 index                                │
│    每個 list query 一個 composite index              │
│    高頻狀態查詢用 partial index                      │
│                                                     │
│  CREATE TRIGGER trg_<table>_updated_at              │
│                                                     │
│  ALTER TABLE ... ENABLE ROW LEVEL SECURITY          │
│                                                     │
│  CREATE POLICY service_role (for all, using true)   │
│  CREATE POLICY authenticated (for select)           │
│                                                     │
│  GRANT SELECT TO authenticated                      │
│  GRANT ALL TO service_role                          │
│                                                     │
│  如果是 append-heavy (>1M rows)：                    │
│    PARTITION BY RANGE (created_at)                   │
│    SET autovacuum_vacuum_scale_factor = 0.05         │
│    設計 retention policy                             │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

# 附錄：完整自我檢查清單

## 每張新表

```
□ PK: id text primary key default generate_ulid()
□ FK: 全部 text（不是 bigint、不是 uuid）
□ created_at + updated_at
□ updated_at trigger（moddatetime 或手寫）
□ project_id（如果需要多租戶）
□ created_by（如果是使用者操作產生的）
□ CHECK 約束有名字
□ UNIQUE 約束有名字
□ DDL 全部 IF NOT EXISTS
```

## 每張表的 Index

```
□ 每個 FK 欄位有單欄 index
□ 常見 list query 有 composite index
□ 高頻狀態查詢有 partial index
□ 同一表 composite index 不超過 5 個
```

## 每張表的安全

```
□ RLS enabled
□ service_role policy (for all)
□ authenticated policy (至少 select)
□ GRANT SELECT to authenticated
□ GRANT ALL to service_role
```

## 每張 append-heavy 表

```
□ PARTITION BY RANGE (created_at)
□ PK 包含 created_at
□ autovacuum_vacuum_scale_factor = 0.05
□ 有 retention policy
□ 查詢包含 created_at 時間範圍
□ 不用 soft delete
□ DELETE 加 LIMIT（batch 50,000）
```

## 每個 RPC function

```
□ SET search_path = public
□ SET statement_timeout = '5s'（或合理值）
□ 不用 RETURNING *
□ GRANT EXECUTE to 需要的 role
```

---

> **下一步**：拿著這份 checklist，重寫 `03_playwright_crawler_schema.sql`。
> 每改一張表，回來對照一次。
> 改完之後，跑一次 `02_AUDIT-vs-guidelines.md` 的 29 項，確認全部 pass。

---

## 在 Studio 中驗證你的爬蟲 Schema

> **前置要求**：已讀完 [01_supabase-studio.md](../01_supabase-studio.md)

跑完 `03_playwright_crawler_schema.sql`（v3.0）後，打開 `http://localhost:54323` 驗證：

### Table Editor 驗證

```
📝 驗證清單
1. public schema → 確認 10 張表全部出現
2. 點進 sources → 確認 id 是 TEXT 型別（不是 bigint）
3. 點進 crawl_queue → 檢查 FK
   - source_id → sources(id) ✅
4. 點進 articles → 確認 project_id 欄位存在
5. 檢查 article_tags → 確認是複合 PK (article_id, tag_id)，都是 TEXT
```

### SQL Editor 驗證

```sql
-- 確認 ULID 正常
SELECT generate_ulid();

-- 確認所有 PK 都是 TEXT
SELECT table_name, column_name, data_type
FROM information_schema.columns
WHERE table_schema = 'public'
  AND column_name = 'id'
  AND data_type != 'text';
-- 理想結果：空（全部都是 text）

-- 確認 updated_at trigger
SELECT tgname, tgrelid::regclass
FROM pg_trigger
WHERE tgname LIKE 'trg_%_updated';

-- 測試 Queue 的 lease 機制
EXPLAIN ANALYZE
SELECT * FROM crawl_queue
WHERE status = 'pending' AND leased_until < NOW()
ORDER BY priority DESC, created_at ASC
LIMIT 10;
```

### RLS 驗證

```sql
-- 確認 RLS 狀態
SELECT tablename, rowsecurity
FROM pg_tables
WHERE schemaname = 'public';

-- 用 anon 角色測試
SET ROLE anon;
SELECT count(*) FROM articles;  -- 應為 0 或被拒絕
RESET ROLE;
```

### 監控查詢（上線後常用）

```sql
-- Queue 健康度
SELECT status, count(*) FROM crawl_queue GROUP BY status;

-- 最近 24 小時的爬蟲執行
SELECT source_id, run_status, pages_fetched, error_count
FROM crawl_runs
WHERE created_at > NOW() - INTERVAL '24 hours'
ORDER BY created_at DESC;
```

# Ch 01：Supabase Schema 與向量索引

> 核心檔案：[`supabase/schema.sql`](../../supabase/schema.sql)、[`functions.sql`](../../supabase/functions.sql)、[`observability_schema.sql`](../../supabase/observability_schema.sql)、[`seed.sql`](../../supabase/seed.sql)
>
> Variant 適用性：**全部三個** — basic / selfrag / reflection 都需要這層

---

## 本章節奏

| Step | 你會做 |
|------|--------|
| 1 | 套用 schema.sql，看建出哪幾張表 |
| 2 | 讀懂 `ai_skills`，照範例加一個自己的 skill |
| 3 | 讀懂 `private_knowledge`，照範例加一個自訂欄位 |
| 4 | 認識 HNSW 索引，知道何時要換 |
| 5 | 套用 functions.sql，直接用 SQL 打 RPC |
| 6 | 把 RPC 從純向量切到 hybrid (0.7, 0.3) |
| 7 | 認識輔助表（messages / logs） |
| 8 | 認識 opt-in 表（HITL / cache / observability） |

---

## Step 1：套用 schema，看建了什麼

```bash
# 從專案根目錄
export SUPABASE_DB_URL='postgresql://postgres:[YOUR-PASSWORD]@db.[REF].supabase.co:5432/postgres'

psql "$SUPABASE_DB_URL" -f supabase/schema.sql
```

預期看到一連串 `CREATE EXTENSION`、`CREATE TABLE`、`CREATE INDEX`、`CREATE TRIGGER` 訊息，沒有 ERROR。

列出建好的表：

```bash
psql "$SUPABASE_DB_URL" -c '\dt'
```

```
            List of relations
 Schema |          Name           | Type  |
--------+-------------------------+-------+
 public | ai_skills               | table |
 public | hitl_pending_reviews    | table |
 public | line_messages           | table |
 public | private_knowledge       | table |
 public | prompt_cache            | table |
 public | retrieval_logs          | table |
```

各表用途速覽：

| 表 | 角色 | 後續章節 |
|----|------|---------|
| `ai_skills` | 你的 prompt 倉庫 | Step 2 + [Ch 04](ch04-router-skills.md) |
| `private_knowledge` | 你的知識庫主表 | Step 3 + [Ch 06](ch06-multi-seed-retrieval.md) |
| `line_messages` | 對話歷史 | Step 7 + [Ch 03](ch03-channel-webhook.md) |
| `retrieval_logs` | 檢索日誌 | Step 7 + [Ch 06](ch06-multi-seed-retrieval.md) |
| `hitl_pending_reviews` | 人工審核佇列 (opt-in) | Step 8 + [Ch 08](ch08-judge-hitl.md) |
| `prompt_cache` | LLM 回應快取 (opt-in) | Step 8 + [Ch 10](ch10-deployment-pitfalls.md) |

`schema.sql` 第一段是三個 extension：

```sql
create extension if not exists vector;     -- pgvector，向量檢索用
create extension if not exists pg_trgm;    -- 模糊比對保留
create extension if not exists unaccent;   -- 去重音正規化
```

Supabase 預設這三個都能 CREATE，自架 PostgreSQL 可能要 superuser。

---

## Step 2：讀懂 `ai_skills`，加一個自己的 skill

### 2-1 看欄位

打開 [`supabase/schema.sql:15-30`](../../supabase/schema.sql#L15-L30)：

```sql
create table if not exists ai_skills (
  skill_id text primary key,            -- 唯一識別碼，例如 'medical_consult'
  name text not null,                   -- 顯示名稱
  description text not null,            -- 簡述用途
  category text not null,               -- 對應 KB 的 category，用於 RAG filter
  system_prompt text not null,          -- LLM 的 system message
  use_when text[] default '{}',         -- 給 router 看的「適用條件」
  avoid_when text[] default '{}',       -- 給 router 看的「不該用」條件
  output_style jsonb default '{}'::jsonb, -- 輸出規範（段落、語氣）
  default_temperature numeric default 0.4,
  default_top_p numeric default 0.9,
  version text default '0.1.0',
  enabled boolean default true,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);
```

### 2-2 看 seed 範例

[`supabase/seed.sql`](../../supabase/seed.sql) 預設裝一個 `general_chat` 當 fallback：

```sql
insert into ai_skills (skill_id, name, description, category, system_prompt, version, enabled)
values ('general_chat', '一般對話', '一般閒聊與安全 fallback。', 'general', '保持簡潔、誠實、可讀。', '0.1.0', true)
on conflict (skill_id) do update
set name = excluded.name,
    description = excluded.description,
    category = excluded.category,
    system_prompt = excluded.system_prompt,
    version = excluded.version,
    enabled = excluded.enabled;
```

`on conflict do update` 是 PostgreSQL 的 UPSERT 語法——重跑 seed.sql 會更新成最新版而非報錯。

### 2-3 ✏️ 改成你的需求：加一個「自我介紹」skill

假設你想加一個叫 `self_intro` 的 skill。**不要改 schema**，只需在 `seed.sql` 末尾加一段 INSERT：

```sql
-- 在 seed.sql 末尾加
insert into ai_skills (
  skill_id, name, description, category, system_prompt,
  use_when, avoid_when, default_temperature, version, enabled
) values (
  'self_intro',
  '自我介紹',
  '當使用者問「你是誰」時回應 bot 身份',
  'general',
  '你是一個 LINE 上的 RAG 助理。回答時請維持友善但簡短，1-2 句話即可。',
  array['你是誰', '介紹自己', 'who are you'],   -- router 看到這些 pattern 會選你
  array['醫療', '法律'],                          -- 看到這些 keyword 不選你
  0.5,
  '0.1.0',
  true
)
on conflict (skill_id) do update
set name = excluded.name,
    description = excluded.description,
    system_prompt = excluded.system_prompt,
    use_when = excluded.use_when,
    avoid_when = excluded.avoid_when,
    default_temperature = excluded.default_temperature,
    enabled = excluded.enabled;
```

跑：

```bash
psql "$SUPABASE_DB_URL" -f supabase/seed.sql
psql "$SUPABASE_DB_URL" -c "select skill_id, name, enabled from ai_skills;"
```

預期看到兩筆：`general_chat` 與 `self_intro`。

### 2-4 ✏️ 進階修改：把 skill 暫時停用

不用改任何程式碼，直接：

```bash
psql "$SUPABASE_DB_URL" -c "update ai_skills set enabled = false where skill_id = 'self_intro';"
```

router（[`app/router/intent_router.py`](../../app/router/intent_router.py)）下次讀 skill 時就會跳過。完整流程在 [Ch 04](ch04-router-skills.md) 講。

---

## Step 3：讀懂 `private_knowledge`，加一個自訂欄位

### 3-1 看欄位

打開 [`supabase/schema.sql:32-49`](../../supabase/schema.sql#L32-L49)：

```sql
create table if not exists private_knowledge (
  id uuid primary key default gen_random_uuid(),
  source_id text,                                -- 原始來源識別（檔名、URL）
  source_type text not null default 'markdown', -- markdown / pdf / web / csv
  title text,
  content text not null,                         -- chunk 內文
  content_hash text not null unique,             -- 去重用，SHA-256
  category text not null,                        -- RAG filter 的 key
  tags text[] default '{}',
  metadata jsonb default '{}'::jsonb,            -- 自由結構欄位
  embedding vector(1536),                        -- OpenAI text-embedding-3-small 維度
  search_vector tsvector generated always as (   -- 自動算的全文索引
    to_tsvector('simple', coalesce(title, '') || ' ' || coalesce(content, ''))
  ) stored,
  knowledge_version integer default 1,           -- 給 cache 失效用（Ch 10 詳述）
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);
```

幾個容易誤會的欄位：

- **`content_hash` UNIQUE**：同一份內容只進一次。ingest pipeline 在算 embedding 前先檢查 hash，避免重複付 OpenAI 錢。
- **`search_vector generated`**：generated column 由 DB 自動算。**Python 端從不寫這個欄位**，每次更新 `title` 或 `content` 它會自動重算。
- **`embedding vector(1536)`**：1536 對應 OpenAI `text-embedding-3-small`。換 model 要改維度（見下方 ✏️）。

> 📌 **`knowledge_version` 預告**：這個欄位是後面 [Ch 10 §Step 3 prompt cache 失效機制](ch10-deployment-pitfalls.md#step-3啟用-prompt-cachespec-05) 的核心錨點——ingest 新資料時 `+1`，把舊 `cache_key` 自動打掉。先記在這裡，[Ch 02 §5-3](ch02-repo-pattern.md#5-3-get_knowledge_version-的-60-秒-ttl-cache) 與 [Ch 10 §Step 3](ch10-deployment-pitfalls.md#step-3啟用-prompt-cachespec-05) 會完整解說流程。

### 3-2 ✏️ 改成你的需求一：換 embedding 模型維度

假設你要從 OpenAI 換到本機 BGE-M3（1024 維）：

```sql
-- 改 schema.sql 第 42 行
embedding vector(1024),
```

如果是新環境，直接套用 schema.sql 即可。如果已經有資料：

```bash
psql "$SUPABASE_DB_URL" <<'SQL'
-- 1. 把舊 column drop 掉（資料會清空）
alter table private_knowledge drop column embedding;

-- 2. 加新維度的 column
alter table private_knowledge add column embedding vector(1024);

-- 3. 重建索引
drop index if exists private_knowledge_embedding_idx;
create index private_knowledge_embedding_idx
on private_knowledge using hnsw (embedding vector_cosine_ops);
SQL
```

然後跑 ingest pipeline 重算所有 embedding。

### 3-3 ✏️ 改成你的需求二：加「資料來源語言」欄位

假設你的 KB 混了中英文，想記錄每筆是哪種語言、之後 filter 時用。

**Step A：改 schema 加欄位**

```sql
-- 套用一次即可（不影響既有資料）
alter table private_knowledge
add column if not exists language text;

-- 給已存在的列補預設值
update private_knowledge
set language = 'zh-TW'
where language is null;
```

**Step B：改 ingest pipeline 寫入時帶這個欄位**

打開 [`app/ingest/pipeline.py`](../../app/ingest/pipeline.py)（如果你有自己的 ingest），找到塞 `private_knowledge` 那段，補上 `language` 欄位。

或者更乾淨的做法——透過 metadata：

```sql
-- 不加欄位，直接塞進 metadata jsonb
update private_knowledge
set metadata = jsonb_set(metadata, '{language}', '"zh-TW"');
```

**Step C：filter 時用**

```sql
-- 只查中文資料
select id, title
from private_knowledge
where metadata->>'language' = 'zh-TW';
```

jsonb 路線的好處：**不用每次新需求都 ALTER TABLE**。代價是 query 要寫 `->>`。如果這個 filter 很頻繁，再考慮提升成獨立欄位 + index。

---

## Step 4：認識 HNSW 索引，知道何時要換

### 4-1 看索引宣告

[`supabase/schema.sql:105-108`](../../supabase/schema.sql#L105-L108)：

```sql
drop index if exists private_knowledge_embedding_idx;
create index if not exists private_knowledge_embedding_idx
on private_knowledge
using hnsw (embedding vector_cosine_ops);
```

`drop ... if exists` 是為了讓既有 IVFFlat 環境能順利切到 HNSW。

### 4-2 HNSW vs IVFFlat 速覽

| 維度 | HNSW | IVFFlat |
|------|------|---------|
| 適合資料量 | 1K ~ 10M | 100K 起跳才划算 |
| 是否需要重 tune | 否 | 是（資料量變要重算 lists） |
| 記憶體 | 大 | 小 |
| 查詢精度 | 高 (recall > 95%) | 中 |
| pgvector 版本 | ≥ 0.5.0 | 0.4.0+ |

**結論**：本專案目標 < 1M 筆，HNSW 永遠對。

### 4-3 ✏️ 改成你的需求：超大資料量時換 IVFFlat

只有當你的資料 > 10M 且記憶體吃緊時才考慮：

```sql
drop index if exists private_knowledge_embedding_idx;
create index private_knowledge_embedding_idx
on private_knowledge
using ivfflat (embedding vector_cosine_ops)
with (lists = 1000);   -- 經驗值：lists ≈ sqrt(rows)

-- 查詢時要調 probes（precision/speed trade-off）
set ivfflat.probes = 10;
```

`lists` 與 `probes` 需要你根據實際資料量重新 tune。對絕大多數教學專案，**不要走這條路**。

---

## Step 5：套用 functions.sql，用 SQL 打 RPC

### 5-1 套用

```bash
psql "$SUPABASE_DB_URL" -f supabase/functions.sql
psql "$SUPABASE_DB_URL" -c '\df match_private_knowledge'
```

預期看到 RPC 簽名：6 個參數，回傳 8 欄。

### 5-2 看 RPC 在做什麼

打開 [`supabase/functions.sql`](../../supabase/functions.sql)。它做三件事：

```sql
with vector_matches as (...)    -- 第 1 步：算向量相似度 + rank
   , keyword_matches as (...)    -- 第 2 步：算全文相似度 + rank
   , fused as (...)              -- 第 3 步：weighted RRF 合併
select * from fused order by combined_score desc limit match_count;
```

合併公式（RRF）：

```
combined_score = vector_weight × (1 / (60 + vector_rank))
               + keyword_weight × (1 / (60 + keyword_rank))
```

`60` 是 RRF 論文的經驗值，讓「前段排名差距」比「後段排名差距」重要。

### 5-3 ✏️ 直接打 RPC 測試

先塞一筆假資料：

```bash
psql "$SUPABASE_DB_URL" <<'SQL'
insert into private_knowledge (source_type, title, content, content_hash, category, embedding)
values (
  'test', '中醫脈象', '浮數脈通常代表表熱證',
  md5(random()::text), 'tcm',
  array_fill(0.1, array[1536])::vector
);
SQL
```

打 RPC（純向量模式）：

```bash
psql "$SUPABASE_DB_URL" <<'SQL'
select id, title, vector_score, keyword_score, combined_score
from match_private_knowledge(
  query_embedding := array_fill(0.1, array[1536])::vector,
  query_text := '脈象',
  match_count := 5,
  category_filter := array['tcm'],
  vector_weight := 1.0,
  keyword_weight := 0.0
);
SQL
```

預期看到 1 筆，`vector_score ≈ 1.0`、`combined_score > 0`。

清掉：

```bash
psql "$SUPABASE_DB_URL" -c "delete from private_knowledge where category = 'tcm';"
```

---

## Step 6：切到 hybrid mode（vector + keyword）

### 6-1 在 SQL 直接切

把 `vector_weight` / `keyword_weight` 改成 `(0.7, 0.3)`：

```sql
select * from match_private_knowledge(
  query_embedding := <你的 embedding>,
  query_text := '浮數脈',
  match_count := 5,
  category_filter := array['tcm'],
  vector_weight := 0.7,    -- ← 改這裡
  keyword_weight := 0.3    -- ← 改這裡
);
```

### 6-2 ✏️ 在 Python 應用層永久切換

在 [`app/storage/knowledge_repo.py`](../../app/storage/knowledge_repo.py) 裡 RPC 呼叫處會根據 `settings.hybrid_enabled` 決定權重。要永久開 hybrid，改 `.env`：

```bash
# .env
HYBRID_ENABLED=true
HYBRID_VECTOR_WEIGHT=0.7
HYBRID_KEYWORD_WEIGHT=0.3
```

完整流程在 [Ch 06](ch06-multi-seed-retrieval.md) 講。

### 6-3 怎麼挑權重？

經驗起點：

| 你的資料特性 | 建議權重 |
|--------------|---------|
| 中文 / 縮寫多 / 同義詞多 | `(0.5, 0.5)` 全均衡 |
| 技術文件 / 關鍵字精確 | `(0.4, 0.6)` 偏關鍵字 |
| 對話 / 口語 / 意圖模糊 | `(0.8, 0.2)` 偏向量 |
| 不確定 | `(0.7, 0.3)` 安全預設 |

跑幾組 query 比對召回結果，看哪組撈到你預期的 chunk。

---

## Step 7：認識輔助表（你不太需要動）

### 7-1 `line_messages` — 對話歷史

[`supabase/schema.sql:70-79`](../../supabase/schema.sql#L70-L79)：

```sql
create table if not exists line_messages (
  id uuid primary key default gen_random_uuid(),
  line_user_id text not null,
  direction text not null check (direction in ('inbound', 'outbound')),
  message_text text not null,
  skill_id text,
  router_result jsonb default '{}'::jsonb,
  rag_used boolean default false,
  created_at timestamptz default now()
);
```

兩個欄位特別說明：

- `direction` 有 CHECK constraint——寫入 `'INBOUND'`（大寫）或 typo 都會被擋
- `router_result jsonb`——router 完整輸出 dump，欄位演進不用 ALTER TABLE

寫入方在 [`app/storage/messages_repo.py`](../../app/storage/messages_repo.py)，[Ch 03](ch03-channel-webhook.md) 詳述。

### 7-2 `retrieval_logs` — 檢索日誌

[`supabase/schema.sql:81-90`](../../supabase/schema.sql#L81-L90)：

```sql
create table if not exists retrieval_logs (
  id uuid primary key default gen_random_uuid(),
  line_user_id text,
  query text not null,
  skill_id text,
  category_filter text[],
  retrieved_ids uuid[],
  scores jsonb default '{}'::jsonb,
  created_at timestamptz default now()
);
```

寫入方在 [`app/storage/logs_repo.py`](../../app/storage/logs_repo.py)，[Ch 06](ch06-multi-seed-retrieval.md) 詳述。

### 7-3 ✏️ 改成你的需求：定期清理舊 log

預設沒有 TTL，會無限累積。建議排程：

```sql
-- 刪 90 天前的 log
delete from retrieval_logs where created_at < now() - interval '90 days';
delete from line_messages where created_at < now() - interval '90 days';
```

用 cron 或 Supabase scheduled function 跑。

---

## Step 8：認識 opt-in 表（後續章節才用）

這三張表預設**不**在 `schema.sql` 套用後生效（前兩張在 schema.sql 裡但用不到不影響，第三張在獨立檔）。需要時才套用。

### 8-1 `hitl_pending_reviews` — 人工審核佇列

詳見 [Ch 08](ch08-judge-hitl.md)。如果你不用 HITL，可以從 schema.sql 刪掉 `:51-68`。

### 8-2 `prompt_cache` — LLM 回應快取

詳見 [Ch 10](ch10-deployment-pitfalls.md)。預設不啟用，啟用後可省 ~50% LLM 成本（命中時）。

### 8-3 `graph_traces` — 跨 session trace（獨立檔）

[`supabase/observability_schema.sql`](../../supabase/observability_schema.sql) — 詳見 [Ch 09](ch09-observability-security.md)。

要啟用：

```bash
psql "$SUPABASE_DB_URL" -f supabase/observability_schema.sql
```

不啟用的話，trace 會落到本機 `.traces/*.json`，學生階段足夠。

---

## 🎯 本章驗收

### Step 0：環境準備

```bash
# .env 至少要有
SUPABASE_URL=https://[REF].supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJ...
SUPABASE_DB_URL=postgresql://postgres:[PASSWORD]@db.[REF].supabase.co:5432/postgres
```

> 💡 Lesson 1 已詳述 Supabase 建立流程；本章只關心 schema 套用。

### Step 1：套用必要 schema

```bash
psql "$SUPABASE_DB_URL" -f supabase/schema.sql
psql "$SUPABASE_DB_URL" -f supabase/functions.sql
psql "$SUPABASE_DB_URL" -f supabase/seed.sql
```

預期：0 錯誤，看到一堆 `CREATE TABLE` / `CREATE FUNCTION` / `INSERT` 訊息。

### Step 2：確認 6 張表存在

```bash
psql "$SUPABASE_DB_URL" -c '\dt' | grep -E 'ai_skills|private_knowledge|line_messages|retrieval_logs|prompt_cache|hitl_pending'
```

預期 6 行。

### Step 3：確認 RPC 存在

```bash
psql "$SUPABASE_DB_URL" -c '\df match_private_knowledge'
```

預期看到 6 參數、8 回傳欄。

### Step 4：確認 HNSW 索引

```bash
psql "$SUPABASE_DB_URL" -c '\d private_knowledge' | grep hnsw
```

預期看到 `private_knowledge_embedding_idx ... USING hnsw`。

### Step 5：RPC 煙霧測試

跑 [Step 5-3 的測試 SQL](#5-3-️-直接打-rpc-測試)，確認能撈回。

### Step 6：trigger 運作

```bash
psql "$SUPABASE_DB_URL" <<'SQL'
update ai_skills set name = '一般對話（測試）' where skill_id = 'general_chat';
select skill_id, updated_at from ai_skills where skill_id = 'general_chat';
update ai_skills set name = '一般對話' where skill_id = 'general_chat';
SQL
```

預期 `updated_at` 變成剛剛的時間。

### Step 7：（選擇性）套用 observability schema

```bash
psql "$SUPABASE_DB_URL" -f supabase/observability_schema.sql
```

七步全通，資料層就 production-ready 了。下一章把這些 SQL 包成 Python 介面。

---

## 下一章

[Ch 02：Repo Pattern 與 DB 實務操作](ch02-repo-pattern.md) — 把 schema 包成 Python 介面（[`app/storage/`](../../app/storage/)），並學會 psql / Supabase CLI / migration 的日常操作流程。

# task-db-schema · 資料庫 Schema 實作

> **使用時機**：套用新 schema 變更，或驗證現有 schema 是否完整。

---

請在這個 repo 的 `supabase/` 目錄下，產出可直接套用的 SQL 檔案。

## 現行檔案結構

```
supabase/
├── schema.sql      # 資料表、索引、trigger
├── functions.sql   # match_private_knowledge RPC
└── seed.sql        # 初始 seed 資料
```

## 必要資料表與規格

### `ai_skills`

```sql
skill_id text PRIMARY KEY
name text NOT NULL
description text NOT NULL
category text NOT NULL
system_prompt text NOT NULL
use_when text[] DEFAULT '{}'
avoid_when text[] DEFAULT '{}'
output_style jsonb DEFAULT '{}'
default_temperature numeric DEFAULT 0.4
default_top_p numeric DEFAULT 0.9
version text DEFAULT '0.1.0'
enabled boolean DEFAULT true
created_at / updated_at timestamptz
```

### `private_knowledge`

```sql
id uuid PRIMARY KEY DEFAULT gen_random_uuid()
source_id text
source_type text DEFAULT 'markdown'
title text
content text NOT NULL
content_hash text NOT NULL UNIQUE   -- UNIQUE 必須有，ingest upsert 依賴此 constraint
category text NOT NULL
tags text[] DEFAULT '{}'
metadata jsonb DEFAULT '{}'
embedding vector(1536)              -- text-embedding-3-small 維度
search_vector tsvector GENERATED ALWAYS AS (
  to_tsvector('simple', coalesce(title,'') || ' ' || coalesce(content,''))
) STORED
knowledge_version integer DEFAULT 1
created_at / updated_at timestamptz
```

### `line_messages`

```sql
id uuid PRIMARY KEY
line_user_id text NOT NULL
direction text CHECK (direction IN ('inbound','outbound'))
message_text text NOT NULL
skill_id text
router_result jsonb DEFAULT '{}'
rag_used boolean DEFAULT false
created_at timestamptz
```

### `retrieval_logs`

```sql
id uuid PRIMARY KEY
line_user_id text
query text NOT NULL
skill_id text
category_filter text[]
retrieved_ids uuid[]
scores jsonb DEFAULT '{}'
created_at timestamptz
```

### `prompt_cache`

```sql
id uuid PRIMARY KEY
cache_key text UNIQUE NOT NULL
user_input text NOT NULL
skill_id text
knowledge_version integer
response_text text NOT NULL
created_at timestamptz
```

## 必要索引

```sql
-- 向量搜尋（IVFFlat）
private_knowledge ON embedding USING ivfflat (vector_cosine_ops) WITH (lists=100)
-- 全文搜尋
private_knowledge ON search_vector USING gin
-- category 篩選
private_knowledge ON category
-- 對話歷史查詢
line_messages ON (line_user_id, created_at DESC)
retrieval_logs ON (line_user_id, created_at DESC)
```

## 必要 Trigger

```sql
-- updated_at 自動更新
ai_skills: BEFORE UPDATE → set_updated_at()
private_knowledge: BEFORE UPDATE → set_updated_at()
```

## 請輸出

1. 完整的 `schema.sql`（idempotent，使用 `CREATE TABLE IF NOT EXISTS`、`CREATE INDEX IF NOT EXISTS`）
2. 確認 `content_hash` 欄位有 `UNIQUE` constraint
3. 若有變更，給出對應的 rollback SQL

## 驗收指令

```bash
psql "$SUPABASE_DB_URL" -v ON_ERROR_STOP=1 -f supabase/schema.sql
# 期望：全部 CREATE / ALTER 成功，無 ERROR
```

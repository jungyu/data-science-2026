# Ch 02：`schema.sql` 解剖

> 核心檔案：[`supabase/schema.sql`](../../supabase/schema.sql)
>
> 每一行都有理由存在。讀完這章你會知道為什麼。

---

## 開始之前：建立 Schema

第一次使用這個專案，先確認環境已設定好：

```bash
# 1. 複製 .env（還沒做的話）
cp .env.example .env
# 填入 OPENAI_API_KEY、SUPABASE_URL、SUPABASE_SERVICE_ROLE_KEY
# 詳細說明：docs/.env.GUIDE.md

# 2. 把 schema.sql 和 functions.sql 套用到你的 Supabase 專案
bash scripts/apply_supabase_sql.sh
```

`apply_supabase_sql.sh` 會依序執行 `supabase/schema.sql` 和 `supabase/functions.sql`，
建立 `private_knowledge` 表格、extension、index 和 RPC 函式。
**這一步只需要做一次**；之後重新執行是 no-op（所有語句都有 `if not exists`）。

---

## 2-1  三個必要的 Extension

```sql
-- supabase/schema.sql 第 1–3 行
create extension if not exists vector;     -- pgvector：存和查向量
create extension if not exists pg_trgm;   -- 三元組索引：加速 LIKE 和 similarity
create extension if not exists unaccent;  -- 去除口音符號（搜尋 "cafe" 能找到 "café"）
```

`vector` extension 讓 PostgreSQL 新增了一個欄位型別：`vector(N)`。
沒有它，`embedding vector(1536)` 這行就會報錯。

---

## 2-2  `private_knowledge`：每個欄位的作用

```sql
-- supabase/schema.sql 第 32–49 行
create table if not exists private_knowledge (
  id            uuid primary key default gen_random_uuid(),
  source_id     text,           -- 來源識別（URL 或檔案路徑）
  source_type   text not null default 'markdown',  -- 'markdown'|'pdf'|'csv'|'web'
  title         text,
  content       text not null,  -- chunk 的實際文字（這是 bot 會看到的）
  content_hash  text not null unique,  -- SHA-256 前 16 碼，用來去重
  category      text not null,  -- 技能路由的 filter key（必須和 skill 的 rag_categories 一致）
  tags          text[] default '{}',
  metadata      jsonb default '{}'::jsonb,  -- page_number / source_url 等附加資訊
  embedding     vector(1536),   -- 文字的向量表示，1536 維
  search_vector tsvector generated always as (   -- 全文搜尋用的預計算欄位
    to_tsvector('simple', coalesce(title, '') || ' ' || coalesce(content, ''))
  ) stored,
  ...
);
```

**最重要的三個欄位**：

| 欄位 | 誰寫入 | 誰讀取 |
|------|--------|--------|
| `content` | IngestionPipeline | generate node（給 LLM 的 context） |
| `embedding` | OpenAIEmbedder | ivfflat index（向量搜尋） |
| `category` | ingest script | retriever（用 `SearchFilters.categories` 過濾） |

---

## 2-3  `content_hash`：去重的關鍵

```sql
content_hash  text not null unique,
```

`IngestionPipeline` 把每個 chunk 的 SHA-256 存進這個欄位（[`app/ingest/pipeline.py:56`](../../app/ingest/pipeline.py)）。

**upsert 時的行為**：

```python
# app/storage/stores/supabase_store.py 第 44–51 行
await self._client.upsert(
    "private_knowledge",
    rows,
    on_conflict="content_hash"   # ← 同樣的 hash 就更新，不新增
)
```

實際效果：
```
第一次 ingest：  content_hash = "a3f9b2c1" → INSERT
第二次 ingest（同樣的文字）：同樣的 hash → UPDATE（不重複）
文字有改動：    content_hash = "d7e4a8f2" → INSERT（新的 chunk）
```

---

## 2-4  `ivfflat` Index：向量搜尋的速度保證

```sql
-- supabase/schema.sql 第 83–86 行
create index if not exists private_knowledge_embedding_idx
on private_knowledge
using ivfflat (embedding vector_cosine_ops)
with (lists = 100);
```

**沒有這個 index** 的向量搜尋：PostgreSQL 要一個個算每個 row 的餘弦距離 → O(n)，10 萬個 chunk 要幾秒。

**有了 ivfflat**：把向量空間切成 100 個「桶」（lists），搜尋時只看最近的桶 → O(log n)，毫秒級。

```
lists = 100  適合 chunk 數量在 10K–1M 之間
lists = 50   適合 < 10K（本課程範圍）
```

> 💡 `vector_cosine_ops` 是說用「餘弦距離」計算相似度，而不是歐氏距離。
> 文字 embedding 用餘弦距離更準確（因為向量的「方向」比「長度」更重要）。

---

## 2-5  `search_vector`：全文搜尋免費送

```sql
search_vector tsvector generated always as (
  to_tsvector('simple', coalesce(title, '') || ' ' || coalesce(content, ''))
) stored,
```

這是 PostgreSQL 的 **generated column**——寫入 `content` 時自動更新，不需要手動維護。

`functions.sql` 裡的 `match_private_knowledge` 同時用到它（Ch 04 會看）。

---

## 🎯 本章里程碑

執行完 `bash scripts/apply_supabase_sql.sh` 後，打開 Supabase Dashboard → Table Editor → `private_knowledge`，確認：
- 表格已存在
- 有 `embedding` 欄位（型別 `vector`）
- 有 `category` 欄位
- SQL Editor 執行 `select * from private_knowledge limit 1;` 不報錯（空表格是正常的）

下一章 → [Ch 03：Embed + 存入](ch03-embed-and-store.md)

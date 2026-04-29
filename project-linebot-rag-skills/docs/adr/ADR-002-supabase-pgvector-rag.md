# ADR-002：使用 Supabase + pgvector 做輕量私人 RAG

## 狀態

已採納

## 背景

系統需要一個統一的儲存層，同時承擔：skill 元資料、私人知識庫、對話歷史、檢索 log、prompt cache。若分散到多個服務（向量 DB + RDBMS + Cache），維護成本會超過 MVP 所需。

## 決策

採用 Supabase Hosted PostgreSQL，搭配以下擴充：

| 擴充 | 用途 |
|------|------|
| `pgvector` | 向量語意搜尋（1536 維，text-embedding-3-small） |
| `pg_trgm` | 全文關鍵字搜尋 |
| `unaccent` | 搜尋去除重音符號 |

所有資料表統一在同一個 Postgres 實例，檢索、篩選、logging 不需跨服務呼叫。

### 實作細節

**連線設定**

Supabase 的 Direct Connection 字串格式為：
```
postgresql://postgres:[YOUR-PASSWORD]@db.<project-ref>.supabase.co:5432/postgres
```

密碼若含 `@`、`#`、`^` 等特殊字元，psql 會誤解析 host 部分。正確做法是將密碼從 URL 移除，改用 `PGPASSWORD` 環境變數分離存放：

```bash
export SUPABASE_DB_URL='postgresql://postgres@db.<project-ref>.supabase.co:5432/postgres'
export PGPASSWORD='你的原始密碼'
```

**知識庫 Upsert**

`private_knowledge.content_hash` 必須設定 UNIQUE constraint，Supabase 的 upsert（`on_conflict`）才能正常運作。若初始 schema 缺少此 constraint，ingestion 會出現 `400 Bad Request`：

```sql
ALTER TABLE private_knowledge
  ADD CONSTRAINT private_knowledge_content_hash_key UNIQUE (content_hash);
```

當前 `schema.sql` 已包含此 constraint，不需手動補。

**向量索引**

使用 IVFFlat，適合 MVP 規模（< 10 萬筆）：

```sql
CREATE INDEX ON private_knowledge
  USING ivfflat (embedding vector_cosine_ops)
  WITH (lists = 100);
```

## 後果

### 正面

- 單一服務，部署面最小
- 免費 Hosted 方案已足夠 MVP 使用
- 搜尋、元資料篩選、logging 不需跨服務呼叫
- Supabase Dashboard 可直接查看資料與執行 SQL

### 負面

- IVFFlat 在大規模多租戶下效能不如專屬向量 DB
- 密碼含特殊字元時連線設定較繁瑣
- embedding 維度固定後不易遷移（需重建索引與重新 embed 所有資料）

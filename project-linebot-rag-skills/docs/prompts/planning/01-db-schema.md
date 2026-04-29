# 01 · 資料庫 Schema 審查（Planning Prompt）

> **使用時機**：Schema 變更前的設計審查，或新增資料表時的評估。

---

你是資深資料庫工程師。請審查這個 LINE Bot RAG 系統的資料庫設計，並直接給出可執行的 SQL patch。

## 現行 Schema（已套用至 Supabase）

```sql
-- 擴充
create extension if not exists vector;    -- 向量搜尋
create extension if not exists pg_trgm;   -- 全文搜尋
create extension if not exists unaccent;  -- 搜尋去重音

-- 資料表
ai_skills           -- skill 元資料與 system prompt
private_knowledge   -- 知識庫（embedding + tsvector + content_hash UNIQUE）
line_messages       -- inbound/outbound 對話紀錄
retrieval_logs      -- 每次 RAG 檢索的記錄
prompt_cache        -- 回覆快取（目前未啟用）

-- 索引
private_knowledge: IVFFlat (lists=100), GIN(search_vector), btree(category)
line_messages: (line_user_id, created_at DESC)
retrieval_logs: (line_user_id, created_at DESC)
```

**已確認的設計決策：**

- `private_knowledge.content_hash` 有 `UNIQUE` constraint，ingest upsert（`on_conflict=content_hash`）才能正常運作，缺少時 Supabase 回 400
- `private_knowledge.embedding` 維度固定為 1536（text-embedding-3-small），修改需重建索引與重新 embed 所有資料
- `private_knowledge.search_vector` 是 generated always as tsvector，不需手動維護
- `line_messages.router_result` 存完整 RouterResult JSON，用於除錯與分析
- `retrieval_logs.scores` 存 vector_score、keyword_score、combined_score

## 請評估以下變更：

{在此填入你要審查的 schema 變更，例如：「新增 user_preferences 資料表」}

請輸出：
1. 現行 schema 對此需求的支援程度
2. 需要新增或修改的欄位 / 資料表
3. 索引建議
4. 可能影響的現有查詢
5. 直接可執行的 SQL patch（含 migration 順序）
6. rollback 方式

**注意事項：**
- 任何 upsert 使用的 conflict target 欄位必須有 UNIQUE constraint
- IVFFlat 索引在 `lists` 數量遠大於實際資料量時 recall 下降，小資料量可考慮移除索引改用全表掃描

# Lab：從零操作 Supabase RAG 資料庫

> 透過 7 個漸進式練習，從建表到語意搜尋，完整走過 RAG Pipeline 的資料層操作。
>
> Schema v3.0 — 符合 `agent-init/skills/supabase/*.md` 全部規範。

---

## 前置準備

- Supabase 專案（免費版即可）
- 開啟 SQL Editor（Dashboard → SQL Editor）
- 執行 `05_rag_supabase_schema.sql` 建立所有表

```sql
-- 確認 pgvector 已啟用
SELECT extversion FROM pg_extension WHERE extname = 'vector';
-- 應回傳 '0.7.0' 或更高版本

-- 確認 ULID 生成器可用
SELECT generate_ulid();
-- 應回傳 26 字元的 ULID，例如 '01JQXYZ...'
```

---

## Stage 1：理解 ULID 主鍵與模型設定

> 學習重點：PK 慣例、TEXT vs BIGINT、embedding 模型維度限制

### 1.1 觀察 ULID 主鍵

```sql
-- 生成幾個 ULID，觀察其結構
SELECT generate_ulid() AS ulid_1,
       generate_ulid() AS ulid_2,
       generate_ulid() AS ulid_3;
```

**觀察**：
- 26 字元 Crockford Base32
- 前 10 字元 = 時間戳（可排序）
- 後 16 字元 = 隨機（唯一性）

**思考**：為什麼不用 UUID 或 BIGINT？（提示：看 pk-convention.md）

### 1.2 查看 embedding 模型

```sql
SELECT id, name, provider, dimensions FROM embedding_models;
```

**觀察**：所有 `id` 都是 ULID（TEXT），不是數字。dimensions 全部是 1536。

```sql
-- 嘗試插入 3072 維模型 → 會失敗！
INSERT INTO embedding_models (name, provider, dimensions)
VALUES ('test-3072', 'test', 3072);
-- ERROR: violates check constraint "ck_embedding_models_dimensions"
```

---

## Stage 2：建立知識庫

> 學習重點：collection 作為 tenant scope、owner_id、chunking 策略

### 2.1 建立知識庫

```sql
INSERT INTO collections (name, code, description, embedding_model_id, owner_id)
SELECT
  '台灣美食指南',
  'tw-food',
  '收集台灣各地美食介紹，用於 AI 問答',
  id,
  'demo-owner-001'  -- 教學用 owner ID
FROM embedding_models
WHERE name = 'text-embedding-3-small'
RETURNING id, name, code, owner_id;
```

**觀察**：
- `id` 自動生成 ULID
- `embedding_model_id` 是 TEXT FK（不是 BIGINT）
- `owner_id` 用於 RLS 隔離

### 2.2 查看 chunking 預設策略

```sql
SELECT code, chunking_strategy FROM collections WHERE code = 'tw-food';
```

**觀察**：`chunking_strategy` JSONB 包含 method、chunk_size、chunk_overlap、separators。

---

## Stage 3：文件入庫與 Ingestion Pipeline

> 學習重點：Ingestion 狀態機、CHECK constraint、owner_id 自動傳播

### 3.1 新增文件

```sql
-- 取得 collection id
DO $$
DECLARE v_collection_id TEXT;
BEGIN
  SELECT id INTO v_collection_id FROM collections WHERE code = 'tw-food';

  INSERT INTO documents (collection_id, title, source_type, content_text, lang, created_by)
  VALUES
    (v_collection_id, '台北牛肉麵完全攻略', 'text',
     '台北牛肉麵是台灣最具代表性的麵食之一。紅燒牛肉麵以醬油和豆瓣醬為基底，湯頭濃郁。清燉牛肉麵則以清湯慢燉，湯色清澈但味道醇厚。永康街的「永康牛肉麵」創立於1963年，被認為是紅燒牛肉麵的代表。林東芳牛肉麵則以清燉聞名，經常排隊超過一小時。建宏牛肉麵提供半筋半肉的經典配置。判斷牛肉麵好壞的關鍵：湯頭是否有層次、牛肉是否燉到入口即化、麵條是否有嚼勁。',
     'zh-TW', 'demo-owner-001'),
    (v_collection_id, '台南小吃地圖', 'text',
     '台南是台灣的美食之都，以小吃聞名。度小月擔仔麵是最經典的台南小吃，以肉燥和蝦湯為特色。安平豆花綿密滑順，搭配糖水或薑汁。赤崁棺材板是台南獨創，將厚片吐司炸酥後填入海鮮濃湯。阿堂鹹粥是在地人的早餐首選，以虱目魚和油條為主角。再發號肉粽已有百年歷史，餡料豐富。',
     'zh-TW', 'demo-owner-001'),
    (v_collection_id, '台中美食精選', 'text',
     '台中以創意美食著稱。宮原眼科是日治時代眼科改建的冰淇淋店，提供超過60種口味。第四信用合作社延續同一概念，在銀行建築裡吃冰。逢甲夜市是台灣最大的夜市之一，以大腸包小腸、章魚小丸子聞名。台中太陽餅是最受歡迎的伴手禮，外皮酥脆內餡甜而不膩。春水堂是珍珠奶茶的發源地，1983年首創這款現在風靡全球的飲料。',
     'zh-TW', 'demo-owner-001');
END $$;
```

### 3.2 驗證 owner_id 自動傳播

```sql
SELECT id, title, process_status, owner_id FROM documents
WHERE collection_id = (SELECT id FROM collections WHERE code = 'tw-food');
```

**觀察**：`owner_id` 自動從 collection 傳播過來（trigger），不需手動設定。

### 3.3 走過 Ingestion Pipeline 狀態機

```sql
-- 查看當前狀態
SELECT id, title, process_status FROM documents
WHERE collection_id = (SELECT id FROM collections WHERE code = 'tw-food');
-- 全部是 'uploaded'

-- 模擬解析完成
UPDATE documents SET process_status = 'parsed'
WHERE collection_id = (SELECT id FROM collections WHERE code = 'tw-food');

-- 嘗試非法狀態 → 失敗
UPDATE documents SET process_status = 'invalid_status'
WHERE collection_id = (SELECT id FROM collections WHERE code = 'tw-food');
-- ERROR: violates check constraint "ck_documents_process_status"
```

---

## Stage 4：Chunking（文件切分）

> 學習重點：chunk 與 document 的關係、trigger 強制 collection_id 一致性

### 4.1 手動切分文件

```sql
DO $$
DECLARE
  v_doc_id TEXT;
BEGIN
  -- 取得第一份文件 ID
  SELECT id INTO v_doc_id FROM documents
  WHERE title = '台北牛肉麵完全攻略';

  -- 注意：collection_id 由 trigger 自動填入
  -- 即使你填了錯的值，trigger 也會覆蓋成正確的
  INSERT INTO chunks (document_id, content, chunk_index, token_count, chunking_method)
  VALUES
    (v_doc_id,
     '台北牛肉麵是台灣最具代表性的麵食之一。紅燒牛肉麵以醬油和豆瓣醬為基底，湯頭濃郁。清燉牛肉麵則以清湯慢燉，湯色清澈但味道醇厚。',
     0, 45, 'recursive'),
    (v_doc_id,
     '永康街的「永康牛肉麵」創立於1963年，被認為是紅燒牛肉麵的代表。林東芳牛肉麵則以清燉聞名，經常排隊超過一小時。建宏牛肉麵提供半筋半肉的經典配置。',
     1, 50, 'recursive'),
    (v_doc_id,
     '判斷牛肉麵好壞的關鍵：湯頭是否有層次、牛肉是否燉到入口即化、麵條是否有嚼勁。',
     2, 30, 'recursive');

  UPDATE documents SET process_status = 'chunked', chunk_count = 3
  WHERE id = v_doc_id;
END $$;
```

### 4.2 驗證 trigger 一致性

```sql
-- collection_id 和 owner_id 都自動填入
SELECT id, document_id, collection_id, owner_id, chunk_index
FROM chunks ORDER BY created_at;
```

### 4.3 切分其他文件

```sql
DO $$
DECLARE v_doc_id TEXT;
BEGIN
  -- 台南
  SELECT id INTO v_doc_id FROM documents WHERE title = '台南小吃地圖';
  INSERT INTO chunks (document_id, content, chunk_index, token_count, chunking_method)
  VALUES
    (v_doc_id, '台南是台灣的美食之都，以小吃聞名。度小月擔仔麵是最經典的台南小吃，以肉燥和蝦湯為特色。安平豆花綿密滑順，搭配糖水或薑汁。', 0, 42, 'recursive'),
    (v_doc_id, '赤崁棺材板是台南獨創，將厚片吐司炸酥後填入海鮮濃湯。阿堂鹹粥是在地人的早餐首選，以虱目魚和油條為主角。再發號肉粽已有百年歷史，餡料豐富。', 1, 48, 'recursive');
  UPDATE documents SET process_status = 'chunked', chunk_count = 2 WHERE id = v_doc_id;

  -- 台中
  SELECT id INTO v_doc_id FROM documents WHERE title = '台中美食精選';
  INSERT INTO chunks (document_id, content, chunk_index, token_count, chunking_method)
  VALUES
    (v_doc_id, '台中以創意美食著稱。宮原眼科是日治時代眼科改建的冰淇淋店，提供超過60種口味。第四信用合作社延續同一概念，在銀行建築裡吃冰。', 0, 40, 'recursive'),
    (v_doc_id, '逢甲夜市是台灣最大的夜市之一，以大腸包小腸、章魚小丸子聞名。台中太陽餅是最受歡迎的伴手禮，外皮酥脆內餡甜而不膩。', 1, 38, 'recursive'),
    (v_doc_id, '春水堂是珍珠奶茶的發源地，1983年首創這款現在風靡全球的飲料。', 2, 22, 'recursive');
  UPDATE documents SET process_status = 'chunked', chunk_count = 3 WHERE id = v_doc_id;
END $$;
```

---

## Stage 5：Embedding 與語意搜尋

> 學習重點：向量生成、HNSW 索引、cosine similarity、hybrid search

### 5.1 生成模擬 embedding

```sql
-- 教學用隨機向量生成器
CREATE OR REPLACE FUNCTION public.random_embedding()
RETURNS vector(1536)
LANGUAGE plpgsql
AS $$
DECLARE
  arr FLOAT8[];
BEGIN
  arr := '{}';
  FOR i IN 1..1536 LOOP
    arr := arr || (random() * 2 - 1)::FLOAT8;
  END LOOP;
  RETURN arr::vector(1536);
END;
$$;

-- 為所有 chunks 生成 embedding
UPDATE chunks SET embedding = public.random_embedding()
WHERE embedding IS NULL;

-- 更新 pipeline 狀態
UPDATE documents SET process_status = 'ready'
WHERE process_status = 'chunked';
```

### 5.2 基本語意搜尋

```sql
SELECT id, left(content, 50) || '...' AS preview,
  round(similarity::NUMERIC, 4) AS similarity
FROM match_chunks(
  public.random_embedding(),
  (SELECT id FROM collections WHERE code = 'tw-food'),
  5, 0.0  -- threshold = 0 看全部結果
);
```

### 5.3 帶文件資訊的搜尋

```sql
SELECT document_title, left(content, 40) || '...' AS preview,
  round(similarity::NUMERIC, 4) AS sim
FROM match_chunks_with_document(
  public.random_embedding(),
  (SELECT id FROM collections WHERE code = 'tw-food'),
  5, 0.0
);
```

### 5.4 混合搜尋（語意 + 全文）

```sql
SELECT left(content, 40) || '...' AS preview,
  round(semantic_score::NUMERIC, 4) AS semantic,
  round(fulltext_score::NUMERIC, 4) AS fulltext,
  round(combined_score::NUMERIC, 4) AS combined
FROM hybrid_search(
  '牛肉麵',
  public.random_embedding(),
  (SELECT id FROM collections WHERE code = 'tw-food'),
  5, 0.3, 0.0  -- 降低 semantic_weight 讓全文效果更明顯
);
```

**觀察**：包含「牛肉麵」的 chunk 有較高的 `fulltext` 分數。

### 5.5 驗證 FTS 索引生效

```sql
EXPLAIN ANALYZE
SELECT id, left(content, 40)
FROM chunks
WHERE to_tsvector('simple', content) @@ plainto_tsquery('simple', '牛肉麵')
  AND collection_id = (SELECT id FROM collections WHERE code = 'tw-food');
-- 應看到 Bitmap Index Scan on idx_chunks_fts
```

---

## Stage 6：查詢紀錄與 Ragas 評估

> 學習重點：query_logs + query_log_results（正規化）、Ragas 四大指標

### 6.1 記錄一次查詢

```sql
INSERT INTO query_logs (
  collection_id, query_text, query_embedding,
  top_k, generated_answer, llm_model,
  prompt_tokens, completion_tokens, created_by
)
SELECT
  (SELECT id FROM collections WHERE code = 'tw-food'),
  '台北哪裡的牛肉麵最好吃？',
  public.random_embedding(),
  5,
  '台北最知名的牛肉麵店：1. 永康牛肉麵（紅燒代表）、2. 林東芳（清燉聞名）、3. 建宏（半筋半肉）。',
  'gpt-4o', 1200, 150, 'demo-owner-001'
RETURNING id;
```

### 6.2 記錄檢索結果（正規化表）

```sql
-- 假設上一步回傳的 query_log id 為 $query_id
-- 實際操作時替換為真實 id
DO $$
DECLARE
  v_query_id TEXT;
  v_chunk_ids TEXT[];
BEGIN
  SELECT id INTO v_query_id FROM query_logs ORDER BY created_at DESC LIMIT 1;
  SELECT array_agg(id ORDER BY chunk_index) INTO v_chunk_ids
  FROM chunks WHERE document_id = (SELECT id FROM documents WHERE title = '台北牛肉麵完全攻略');

  INSERT INTO query_log_results (query_id, chunk_id, rank, score) VALUES
    (v_query_id, v_chunk_ids[2], 1, 0.92),
    (v_query_id, v_chunk_ids[1], 2, 0.88),
    (v_query_id, v_chunk_ids[3], 3, 0.75);
END $$;
```

### 6.3 填入 Ragas 評估指標

```sql
UPDATE query_logs SET
  eval_faithfulness = 0.95,
  eval_answer_relevance = 0.90,
  eval_context_recall = 0.80,
  eval_context_precision = 1.0
WHERE id = (SELECT id FROM query_logs ORDER BY created_at DESC LIMIT 1);
```

### 6.4 填入使用者回饋

```sql
UPDATE query_logs SET
  user_rating = 4,
  user_feedback = '資訊正確，但希望有更多價格資訊'
WHERE id = (SELECT id FROM query_logs ORDER BY created_at DESC LIMIT 1);
```

### 6.5 追加更多查詢（用於 Stage 7 分析）

```sql
DO $$
DECLARE
  v_col_id TEXT;
  v_q_id TEXT;
  v_chunk_tainan_1 TEXT;
  v_chunk_tainan_2 TEXT;
BEGIN
  SELECT id INTO v_col_id FROM collections WHERE code = 'tw-food';
  SELECT id INTO v_chunk_tainan_1 FROM chunks
    WHERE document_id = (SELECT id FROM documents WHERE title = '台南小吃地圖') AND chunk_index = 0;
  SELECT id INTO v_chunk_tainan_2 FROM chunks
    WHERE document_id = (SELECT id FROM documents WHERE title = '台南小吃地圖') AND chunk_index = 1;

  -- 查詢 2
  INSERT INTO query_logs (collection_id, query_text, query_embedding, top_k, generated_answer, llm_model, created_by)
  VALUES (v_col_id, '台南有什麼必吃的小吃？', random_embedding(), 5,
    '台南必吃：度小月擔仔麵、安平豆花、赤崁棺材板、阿堂鹹粥。', 'gpt-4o', 'demo-owner-001')
  RETURNING id INTO v_q_id;

  INSERT INTO query_log_results (query_id, chunk_id, rank, score) VALUES
    (v_q_id, v_chunk_tainan_1, 1, 0.91),
    (v_q_id, v_chunk_tainan_2, 2, 0.85);

  -- 查詢 3（再次命中台南 chunk）
  INSERT INTO query_logs (collection_id, query_text, query_embedding, top_k, generated_answer, llm_model, created_by)
  VALUES (v_col_id, '擔仔麵是什麼？', random_embedding(), 3,
    '擔仔麵是台南最經典的小吃，由度小月創始，以肉燥和蝦湯為特色。', 'gpt-4o', 'demo-owner-001')
  RETURNING id INTO v_q_id;

  INSERT INTO query_log_results (query_id, chunk_id, rank, score) VALUES
    (v_q_id, v_chunk_tainan_1, 1, 0.95);
END $$;
```

---

## Stage 7：分析與監控

> 學習重點：命中率分析、冗餘偵測、知識庫健康度

### 7.1 知識庫統計

```sql
SELECT * FROM collection_stats(
  (SELECT id FROM collections WHERE code = 'tw-food')
);
```

### 7.2 哪些 chunk 最常被命中？

```sql
SELECT * FROM top_hit_chunks(
  (SELECT id FROM collections WHERE code = 'tw-food'), 10
);
```

### 7.3 沒被命中過的 chunk（潛在冗餘）

```sql
SELECT c.id, left(c.content, 50) || '...' AS content
FROM chunks c
LEFT JOIN query_log_results r ON r.chunk_id = c.id
WHERE c.collection_id = (SELECT id FROM collections WHERE code = 'tw-food')
  AND r.id IS NULL;
```

### 7.4 Ragas 評估總覽

```sql
SELECT
  count(*) AS total_queries,
  round(avg(eval_faithfulness)::NUMERIC, 2) AS avg_faithfulness,
  round(avg(eval_answer_relevance)::NUMERIC, 2) AS avg_relevance,
  round(avg(user_rating)::NUMERIC, 1) AS avg_rating
FROM query_logs
WHERE collection_id = (SELECT id FROM collections WHERE code = 'tw-food')
  AND eval_faithfulness IS NOT NULL;
```

### 7.5 Pipeline 狀態總覽

```sql
SELECT process_status, count(*) AS doc_count
FROM documents
WHERE collection_id = (SELECT id FROM collections WHERE code = 'tw-food')
GROUP BY process_status
ORDER BY CASE process_status
  WHEN 'uploaded' THEN 1 WHEN 'parsed' THEN 2 WHEN 'chunked' THEN 3
  WHEN 'embedded' THEN 4 WHEN 'ready' THEN 5
  WHEN 'failed' THEN 6 WHEN 'stale' THEN 7
END;
```

---

## 挑戰題

### 挑戰 1：標籤系統

```sql
-- 建立城市標籤，然後為 chunks 加標籤
-- 最後查詢：所有標記為「台南」的 chunks
```

### 挑戰 2：Agentic RAG 多輪對話

```sql
-- 第 1 輪：session_id = 'session-001', iteration = 1, agent_action = 'initial'
-- 第 2 輪：parent_query_id = 第 1 輪 id, iteration = 2, agent_action = 'reformulate'
```

### 挑戰 3：文件更新流程

```sql
-- 1. UPDATE documents SET process_status = 'stale'
-- 2. DELETE FROM chunks WHERE document_id = ?
-- 3. INSERT 新的 chunks
-- 4. 走完 pipeline: uploaded → parsed → chunked → embedded → ready
```

---

## 清理

```sql
DROP FUNCTION IF EXISTS public.random_embedding();
DELETE FROM collections WHERE code = 'tw-food';
-- CASCADE 自動清除所有關聯資料
```

---

## 學到了什麼？

| Stage | 主題 | Skill 規範對應 |
|-------|------|---------------|
| 1 | ULID 主鍵 + 模型維度限制 | pk-convention, schema-design |
| 2 | Collection 作為 tenant scope | schema-design (project_id 等價) |
| 3 | Ingestion Pipeline + CHECK constraint | anti-patterns D3, migration-guidelines |
| 4 | Chunking + trigger 一致性 | performance-linter (data integrity) |
| 5 | 語意搜尋 + FTS 索引驗證 | query-patterns, performance-linter |
| 6 | 正規化查詢紀錄 + Ragas | anti-patterns P5 (no N+1) |
| 7 | 分析查詢 + 健康度監控 | scaling-guidelines, large-table-management |

---

*最後更新：2026-03*

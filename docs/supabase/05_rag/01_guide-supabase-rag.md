# 把 RAG 搬進 Supabase：資料庫實戰指南

## 當你的向量資料庫開始鬧脾氣

---

> 「我已經用 Qdrant 跑起來了，為什麼還要搬到 Supabase？」
>
> ——一位工程師，在被要求同時維護 PostgreSQL、Qdrant、Redis 三個資料庫之後

---

你在 [RAG 課程](../../RAG/README.md) 裡學了很多東西：[Embedding](../../RAG/ch03-vectors-embeddings.md)、[Chunking](../../RAG/ch02-etl-chunking.md)、向量搜尋、[Agentic RAG](../../RAG/ch05-agentic-rag.md)。你甚至做出了一個能回答問題的 AI 系統。

**恭喜。**

但現在，你的架構長這樣：

```
你的「能跑就好」架構
═══════════════════════════════════════

  PostgreSQL          Qdrant            Redis
  ┌──────────┐       ┌──────────┐     ┌──────────┐
  │ 文件元資料│       │ 向量儲存  │     │ Session  │
  │ 使用者    │       │ 語意搜尋  │     │ 快取     │
  └──────────┘       └──────────┘     └──────────┘
       ↑                  ↑                ↑
       └──────────────────┴────────────────┘
                   你的應用程式
                （三個連線、三個帳號、三份帳單）
```

每次部署要啟動三個服務。每次 debug 要查三個 log。每次加新功能要改三份設定。

**你的 CTO 看著雲端帳單，問了一句話：**

> 「這些不能用同一個資料庫嗎？」

---

## 腦力激盪 🧠

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│  問題 1：PostgreSQL 可以儲存向量嗎？                    │
│          如果可以，需要什麼 extension？                 │
│                                                         │
│  你的答案：___________________________________________   │
│                                                         │
│  問題 2：如果文件元資料和向量在同一個資料庫，           │
│          搜尋時可以同時用「語意」和「全文」嗎？         │
│                                                         │
│  你的答案：___________________________________________   │
│                                                         │
│  問題 3：Supabase 的 RLS 可以做到什麼？                │
│          如果有 10 個團隊共用一個 RAG 系統，            │
│          怎麼確保 A 團隊看不到 B 團隊的知識庫？         │
│                                                         │
│  你的答案：___________________________________________   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 一個資料庫統治它們

安裝 `pgvector` 之後，PostgreSQL 就能做向量搜尋。而 Supabase 已經幫你裝好了。

```
你的「合體」架構
═══════════════════════════════════════

  Supabase（PostgreSQL + pgvector）
  ┌──────────────────────────────────┐
  │ 文件元資料    → documents 表     │
  │ 向量儲存      → chunks 表        │
  │ 語意搜尋      → pgvector 函數    │
  │ 全文搜尋      → tsvector + GIN   │
  │ 使用者權限    → RLS + policies   │
  │ 檔案儲存      → Supabase Storage │
  │ API           → 自動生成 REST    │
  └──────────────────────────────────┘
            ↑
        你的應用程式
      （一個連線、一個帳號、一份帳單）
```

**這就是我們要做的事。**

### 但等等——全部塞進 public schema？

把所有 RAG 表都堆在 PostgreSQL 預設的 `public` schema，就像把所有書都堆在客廳地板上。能用？能用。找得到？……看運氣。

**我們的做法：建一個專屬的 `rag` schema。**

```
Schema 命名空間
═══════════════════════════════════════

  PostgreSQL 預設
  ┌─────────────────────────────────┐
  │ public                          │
  │ ├── users（認證相關）            │
  │ ├── profiles（使用者資料）       │
  │ └── generate_ulid()（公用函式）  │
  └─────────────────────────────────┘

  RAG 專屬
  ┌─────────────────────────────────┐
  │ rag                             │
  │ ├── collections                 │
  │ ├── documents                   │
  │ ├── chunks  /  chunks_safe      │
  │ ├── tags  /  chunk_tags         │
  │ ├── query_logs                  │
  │ ├── query_log_results           │
  │ └── embedding_models            │
  └─────────────────────────────────┘

  好處：
  ✅ 不污染 public schema
  ✅ 一眼就知道哪些表屬於 RAG
  ✅ 可以用 GRANT ON SCHEMA 統一管權限
  ✅ 未來整合其他系統時不會撞名
```

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│  📌 本指南的 SQL 範例都在 rag schema 下。               │
│  開始操作前，請先執行：                                  │
│                                                         │
│    SET search_path = rag, public;                       │
│                                                         │
│  或者在每個表名前加上 rag. 前綴（如 rag.chunks）。      │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 開始之前：你需要知道的三個觀念

### 觀念 1：ULID — 你的新 ID 格式

在這個課程裡，你可能習慣了 `id = 1, 2, 3...`（自動遞增的整數）。

但在 Supabase 的世界裡，我們用 **ULID**。

```
ULID 長什麼樣？
═══════════════════════════════

  01JQXYZ1234ABCDEFGHIJK56789
  ├──────────┤├──────────────┤
   時間戳部分    隨機部分

  特性：
  ✅ 26 個字元（比 UUID 的 36 字元短）
  ✅ 按時間排序（前半段是時間戳）
  ✅ 全球唯一（後半段是隨機值）
  ✅ 不需要中央序號產生器
```

**為什麼不用 1, 2, 3？**

想像你有兩台伺服器同時在寫入資料。如果用自動遞增，它們會搶同一個號碼。ULID 就像身分證號碼——每個人自己生成，不可能重複。

```sql
-- 每張表的 ID 都長這樣
id TEXT PRIMARY KEY DEFAULT generate_ulid()

-- 生成一個看看
SELECT generate_ulid();
-- → '01JQXYZ...'（每次都不一樣）
```

### 觀念 2：Collection = 你的知識庫

在 Qdrant 裡你有 Collection。在 Supabase 裡也是——但它是一張表。

```
RAG 資料層級
═══════════════════════════════

  Collection（知識庫）
  ├── Document（原始文件）
  │   ├── Chunk 0（切片 + embedding）
  │   ├── Chunk 1
  │   └── Chunk 2
  ├── Document（原始文件）
  │   ├── Chunk 0
  │   └── Chunk 1
  └── ...

  一個 Collection = 一個完整的知識庫
  不同 Collection 之間完全隔離
```

**類比**：Collection 就像 Google Drive 裡的「共用資料夾」。每個專案有自己的資料夾，裡面放文件，文件被切成段落後可以被搜尋。

### 觀念 3：Ingestion Pipeline — 文件不是一步到位

你不能把 PDF 丟進去就開始搜尋。文件需要經過一條生產線：

```
文件的旅程
═══════════════════════════════

  上傳          解析          切分          嵌入          就緒
  ┌───┐       ┌───┐       ┌───┐       ┌───┐       ┌───┐
  │ 📄 │ ───→ │ 📝 │ ───→ │ ✂️ │ ───→ │ 🔢 │ ───→ │ ✅ │
  └───┘       └───┘       └───┘       └───┘       └───┘
  uploaded     parsed      chunked     embedded     ready

  在資料庫裡，每份文件都有一個 process_status 欄位
  告訴你它走到哪一步了
```

**為什麼要分這麼多步？**

因為每一步都可能失敗。如果你只有「處理中」和「完成」兩個狀態，文件卡住了你根本不知道它死在哪裡。

---

## 七個 Stage，從零到搜尋

接下來，我們會用 SQL 一步一步建立完整的 RAG 資料庫。

每個 Stage 都是**獨立的學習單元**，你可以跟著 [04_lab-rag-pipeline.md](04_lab-rag-pipeline.md) 動手做。

```
學習路線圖
═══════════════════════════════════════════════════

  Stage 1        Stage 2        Stage 3
  ULID 主鍵      建立知識庫     文件入庫
  ┌─────┐       ┌─────┐       ┌─────┐
  │ 🔑  │ ───→ │ 📦  │ ───→ │ 📄  │
  └─────┘       └─────┘       └─────┘
  理解 PK 慣例   collection     pipeline

        Stage 4        Stage 5
        文件切分       語意搜尋
       ┌─────┐       ┌─────┐
  ───→ │ ✂️  │ ───→ │ 🔍  │
       └─────┘       └─────┘
       chunking       vector search

              Stage 6        Stage 7
              查詢紀錄       分析監控
             ┌─────┐       ┌─────┐
        ───→ │ 📊  │ ───→ │ 🏥  │
             └─────┘       └─────┘
             evaluation     analytics
```

---

## Stage 1：ULID — 為什麼 ID 不能是 1, 2, 3

### 問題場景

你的爬蟲同時在三台機器上抓資料，同時寫入 `chunks` 表。

```
機器 A：INSERT ... id = 1001
機器 B：INSERT ... id = 1001  ← 💥 衝突！
機器 C：INSERT ... id = 1002  ← 跳號！
```

自動遞增在分散式環境是災難。ULID 解決了這個問題：每台機器自己生成 ID，時間戳在前面確保大致有序。

### 動手試

```sql
-- 連續生成三個 ULID，觀察時間順序
SELECT generate_ulid() AS id_1;
-- 等一秒
SELECT generate_ulid() AS id_2;

-- 比較：id_2 的前幾個字元一定 >= id_1
-- 因為時間在前進
```

### 關鍵規則

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│  ✅ 所有表的 PK：TEXT DEFAULT generate_ulid()           │
│  ✅ 所有 FK：TEXT（不是 BIGINT、不是 UUID）              │
│  ❌ 禁止 SERIAL / BIGINT 當主鍵                         │
│  ❌ 禁止 UUID 和 ULID 混用                              │
│                                                         │
│  這不是建議，是規則。                                    │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

> **Stage 1 收穫**：所有 PK 用 `TEXT + generate_ulid()`，所有 FK 用 `TEXT`。不混用 BIGINT 和 UUID。

---

## Stage 2：建立你的第一個知識庫

### 類比時間

Collection 就像一個圖書館的「特藏室」：

```
台北市立圖書館
├── 一般閱覽室    → 公開
├── 兒童閱覽室    → 公開
├── 台灣文獻特藏室 → 需要申請 ← 這就是一個 Collection
└── 日治時期檔案室 → 需要申請 ← 這是另一個 Collection
```

每個特藏室有自己的主題、自己的文件分類方式，而且**不是所有人都能進去**。

### SQL 時間

```sql
INSERT INTO collections (name, code, embedding_model_id, owner_id)
SELECT
  '台灣美食指南', 'tw-food', id, 'my-owner-id'
FROM embedding_models
WHERE name = 'text-embedding-3-small';
```

### 等等，embedding_model_id 是什麼？

每個知識庫在建立時就要決定用哪個 embedding 模型。**一旦決定就不能換**，因為不同模型產生的向量無法互相比較。

```
類比：貨幣
═══════════════════════════════

  text-embedding-3-small  →  台幣
  text-embedding-ada-002  →  日圓

  你不能拿 100 台幣和 100 日圓直接比較大小。
  同理，不同模型的 embedding 也不能混在一起搜尋。
```

### 沒有笨問題 💡

> **問：為什麼維度鎖定 1536？不能支援 3072 嗎？**
>
> 答：可以，但代價很高。`vector(1536)` 讓 PostgreSQL 能建立 HNSW 索引，搜尋極快。如果改成動態維度，就**沒辦法建索引**，每次搜尋都要掃全表。在「靈活但慢」和「固定但快」之間，我們選擇後者。
>
> 如果真的需要 3072 維，`text-embedding-3-large` 支援 Matryoshka Embedding——它可以被**降維到 1536** 而只損失很少的精度。

> **Stage 2 收穫**：Collection = 知識庫 = tenant scope。建立時就要綁 embedding model，之後不能換。

---

## Stage 3：文件入庫與生產線

### 生產線思維

想像你經營一家出版社。一份稿件從收到到上架，需要經過：

```
出版社工作流程
═══════════════════════════════

  收到稿件 → 審稿校對 → 排版分頁 → 印刷裝訂 → 上架販售
  uploaded    parsed      chunked     embedded     ready

  每一步都可能出問題：
  • 稿件格式看不懂？          → failed（在 uploaded）
  • 文字萃取亂碼？            → failed（在 parsed）
  • 切分策略不適合這份文件？   → failed（在 chunked）
  • OpenAI API 額度用完？      → failed（在 embedded）
```

在資料庫裡，這叫做 **Ingestion Pipeline 狀態機**：

```sql
process_status IN (
  'uploaded',    -- 收到了
  'parsed',      -- 看懂了
  'chunked',     -- 切好了
  'embedded',    -- 向量化了
  'ready',       -- 可以搜尋了
  'failed',      -- 出事了（看 process_error）
  'stale'        -- 原文更新了，需要重做
)
```

### trigger 的魔法

當你把文件放進一個 collection 時，有一件事會自動發生：

```sql
INSERT INTO documents (collection_id, title, ...)
-- → trigger 自動執行：
--   documents.owner_id = collections.owner_id
```

你**不需要手動設定 owner_id**。trigger 會幫你從 collection 抄過來。

**為什麼？** 因為 owner_id 是 RLS（權限控制）用的。如果讓人手動設定，萬一設錯了，就會出現**跨租戶資料洩漏**——A 團隊能看到 B 團隊的文件。

### 還有一個 trigger：moddatetime

每張表都有 `updated_at` 欄位。你**不需要手動更新它**——Supabase 內建的 `moddatetime` extension 會幫你：

```sql
-- Schema 裡為每張表建了這個 trigger
CREATE TRIGGER trg_documents_updated_at
  BEFORE UPDATE ON rag.documents
  FOR EACH ROW EXECUTE FUNCTION moddatetime(updated_at);

-- 效果：每次 UPDATE 都自動把 updated_at 設為 NOW()
-- 你只需要 UPDATE ... SET title = '新標題'
-- updated_at 會自己變
```

```
RAG Schema 裡的三類 trigger
═══════════════════════════════════════

  1. moddatetime       → 自動更新 updated_at（6 張表都有）
  2. sync_document_owner → documents.owner_id ← collections.owner_id
  3. sync_chunk_from_document → chunks.collection_id + owner_id ← documents
```

### 沒有笨問題 💡

> **問：process_status 可以跳級嗎？比如直接從 uploaded 跳到 ready？**
>
> 答：資料庫不會阻止你（CHECK constraint 只驗證值是否合法，不驗證順序）。但這是壞主意——如果你跳過 chunked 直接設 ready，代表沒有 chunks 卻可被搜尋，搜尋結果會是空的。狀態機的順序是邏輯約束，由你的應用程式保證。
>
> **問：stale 狀態是誰設的？**
>
> 答：通常是你的應用程式。例如 Crawler 重新抓取了一份文件，發現 `content_hash` 和原本不同，就把舊文件標為 stale，觸發重新 chunking。

> **Stage 3 收穫**：文件有 7 個狀態（uploaded → ready / failed / stale）。`owner_id` 永遠讓 trigger 填，不要手動設。

---

## Stage 4：切分 — 把大象裝進冰箱（Supabase 版）

### 你已經學過 Chunking

在 [RAG Ch02](../../RAG/ch02-etl-chunking.md)，你學會了把文件切成小塊。在 Supabase 版本裡，每個 chunk 多了一個重要的安全機制。

```sql
INSERT INTO chunks (document_id, content, chunk_index, ...)
-- → trigger 自動執行：
--   chunks.collection_id = documents.collection_id  ← 強制！
--   chunks.owner_id = documents.owner_id            ← 強制！
```

**即使你手動填了錯的 collection_id，trigger 也會覆蓋成正確的值。**

### 為什麼這麼嚴格？

```
安全性比方便性更重要
═══════════════════════════════

  如果 chunk 的 collection_id 和 document 不一致：

  Document（在 Collection A）
  └── Chunk（collection_id = B）  ← 💣

  搜尋 Collection B 的時候，會搜到 Collection A 的文件。
  → 跨租戶資料洩漏
  → 這是安全性 bug，不是程式錯誤
```

> **Stage 4 收穫**：chunks 的 `collection_id` 和 `owner_id` 永遠不要手動填——trigger 會強制覆蓋成正確值。

### 補充：給 Chunk 貼標籤

切完之後，你可能想分類。Schema 裡有 `tags` + `chunk_tags` 兩張表：

```
標籤系統（N:M 多對多）
═══════════════════════════════════════

  tags 表                      chunk_tags（關聯表）
  ┌──────────────────────┐     ┌─────────────────────┐
  │ id: ULID             │     │ chunk_id ← chunks   │
  │ taxonomy: 'city'     │◄────│ tag_id   ← tags     │
  │ name: '台南'         │     │ PK = (chunk_id, tag_id)
  │ parent_id: (自我參照)│     └─────────────────────┘
  └──────────────────────┘

  taxonomy 分類範例：
  ├── 'city'   → 台北、台南、台中
  ├── 'topic'  → 小吃、飲料、夜市
  └── 'source' → 官方、部落格、維基
```

**為什麼不用 JSONB array？** 因為你想問「所有標記為台南的 chunks」——用正規化表可以建 index，用 JSONB array 要全表掃描。

```sql
-- 建立標籤
INSERT INTO tags (taxonomy, name, slug) VALUES
  ('city', '台北', 'taipei'),
  ('city', '台南', 'tainan'),
  ('city', '台中', 'taichung');

-- 幫 chunk 貼標籤
INSERT INTO chunk_tags (chunk_id, tag_id)
SELECT c.id, t.id
FROM chunks c, tags t
WHERE c.content LIKE '%台南%' AND t.slug = 'tainan';

-- 搜尋：所有台南相關的 chunks
SELECT c.id, left(c.content, 50) || '...' AS preview
FROM chunks c
JOIN chunk_tags ct ON ct.chunk_id = c.id
JOIN tags t ON t.id = ct.tag_id
WHERE t.slug = 'tainan';
```

> 在 [04_lab](04_lab-rag-pipeline.md) 的挑戰題 1 有完整練習。

---

## Stage 5：語意搜尋 — 「牛肉麵」也能找到「紅燒麵」

### 三種搜尋，一次滿足

Supabase RAG 提供三個搜尋函數：

```
搜尋函數功能比較
═══════════════════════════════

  match_chunks()
  ├── 純語意搜尋
  ├── 用 embedding 向量比較
  └── 適合：「這段文字的意思最接近什麼？」

  match_chunks_with_document()
  ├── 語意搜尋 + 文件資訊
  ├── 回傳結果包含文件標題、來源 URL
  └── 適合：需要引用來源的 RAG 系統

  hybrid_search()
  ├── 語意搜尋 + 全文搜尋（混合）
  ├── 關鍵字搜尋 + 意思搜尋的結合
  └── 適合：使用者可能會用精確的專有名詞搜尋
```

### Hybrid Search 為什麼厲害？

```
使用者問：「永康牛肉麵的歷史」

純語意搜尋（只看意思）：
  ✅ 找到：「台北有許多歷史悠久的麵店...」
  ❌ 可能漏掉：完全沒提到「歷史」這個字的段落

純全文搜尋（只看字面）：
  ✅ 找到：包含「永康」和「牛肉麵」的段落
  ❌ 可能漏掉：「這家 1963 年創立的紅燒麵店」

混合搜尋（兩者結合）：
  ✅ 找到以上所有結果
  → 用權重 (p_semantic_weight) 控制哪邊更重要
```

### 重要：FTS 索引

全文搜尋**必須有 GIN 索引**，否則每次搜尋都要掃全表：

```sql
-- 這個索引已經在 schema 裡了
CREATE INDEX idx_chunks_fts ON chunks
  USING GIN (to_tsvector('simple', content));
```

你可以用 `EXPLAIN ANALYZE` 驗證索引有在運作。如果看到 `Seq Scan` 而不是 `Bitmap Index Scan`，表示索引沒生效。

### 為什麼有這麼多 Index？

打開 `004_rag_schema.sql`，你會看到 **22 個 index**。「不就一張表嗎，為什麼要這麼多？」

```
Index 分類與用途
═══════════════════════════════════════

  🔑 FK Index（每個外鍵都要）
  ├── idx_documents_collection    → WHERE collection_id = ?
  ├── idx_chunks_document         → WHERE document_id = ?
  ├── idx_query_log_results_query → WHERE query_id = ?
  └── ...等 10 個
  沒有 FK index → JOIN 時全表掃描 → 效能災難

  👤 RLS 用 Index
  ├── idx_collections_owner   → owner_id 比對
  ├── idx_documents_owner     → owner_id 比對
  └── idx_chunks_owner        → owner_id 比對
  每次查詢都要過 RLS → 這些 index 攸關每一次讀取速度

  🔍 搜尋用特殊 Index
  ├── idx_chunks_embedding_hnsw  → HNSW 向量搜尋（cosine）
  ├── idx_chunks_fts             → GIN 全文搜尋
  └── idx_chunks_metadata        → GIN JSONB 查詢

  📊 分析用複合 Index
  ├── idx_query_logs_collection  → (collection_id, created_at DESC)
  └── idx_query_log_results_chunk_score → (chunk_id, score DESC)
  複合 index：一次 index 回答兩個條件
```

### Partial Index：只索引需要的列

你會注意到很多 index 長這樣：

```sql
CREATE INDEX idx_documents_hash ON documents(content_hash)
  WHERE content_hash IS NOT NULL;
--    ^^^^^^^^^^^^^^^^^^^^^^^^^ 只索引非 NULL 的列
```

**為什麼？** 如果 80% 的 `content_hash` 是 NULL，全部索引就浪費 80% 的空間。加上 `WHERE ... IS NOT NULL`，index 只存有值的列——又小又快。

> **Stage 5 收穫**：三種搜尋函數各有用途——純語意用 `match_chunks`、要來源資訊用 `match_chunks_with_document`、關鍵字 + 語意用 `hybrid_search`。

---

## Stage 6：記錄每次查詢 — 未來你會感謝自己

### 為什麼要記錄查詢？

大多數人做 RAG，搜尋完就結束了。但三個月後，你老闆問：

> 「我們的 RAG 系統回答品質怎麼樣？使用者滿意嗎？哪些文件最常被引用？」

如果你沒記錄，你只能回答：「呃......好像還行？」

### query_logs + query_log_results

```
一次 RAG 查詢的完整紀錄
═══════════════════════════════

  query_logs（主表）
  ┌──────────────────────────────────┐
  │ query_text: "台北牛肉麵推薦"     │
  │ top_k: 5                         │
  │ generated_answer: "推薦永康..."   │
  │ llm_model: "gpt-4o"              │
  │ eval_faithfulness: 0.95          │  ← Ragas 評估
  │ user_rating: 4                   │  ← 使用者回饋
  └──────────────────────────────────┘
          │
          │ 1:N
          ▼
  query_log_results（明細表）
  ┌──────────────────────────────────┐
  │ chunk_id: "01JQX..." rank: 1     │  ← 最相關
  │ chunk_id: "01JQY..." rank: 2     │
  │ chunk_id: "01JQZ..." rank: 3     │
  └──────────────────────────────────┘
```

### 為什麼不用 Array？

v1.0 的設計用 `bigint[]` 存 chunk IDs。這很直覺，但——

```
v1.0（Array）                       v3.0（正規化表）
─────────────                       ─────────────────
retrieved_chunk_ids: [1, 2, 3]      query_log_results:
retrieved_scores: [0.92, 0.88, 0.75]  chunk_id | rank | score
                                      ---------|------|------
                                      01JQX... |    1 | 0.92
                                      01JQY... |    2 | 0.88
                                      01JQZ... |    3 | 0.75

Array 版本做不到的事：
  ❌ "哪個 chunk 被搜尋到最多次？" → 要 unnest，很慢
  ❌ "平均相似度分數是多少？"       → 要 unnest + aggregate
  ❌ 建 index                       → array 不支援

正規化版本：
  ✅ SELECT chunk_id, count(*) GROUP BY chunk_id → 秒出
  ✅ SELECT avg(score)                           → 直接算
  ✅ 有 index，查詢飛快
```

### 沒有笨問題 💡

> **問：query_embedding 佔多少空間？每次查詢都存一份向量，不會爆炸嗎？**
>
> 答：`vector(1536)` 大約 6KB。一天 1,000 次查詢 = 6MB/天 = 2GB/年。對 PostgreSQL 來說不算多。好處是分析查詢模式時不需要重新呼叫 OpenAI API（省錢 + 版本一致性）。如果空間真的吃緊，可以把 `query_embedding` 改成 nullable，只在需要分析時才存。
>
> **問：Ragas 四個指標都要填嗎？**
>
> 答：不一定。`eval_faithfulness` 和 `eval_answer_relevance` 是最重要的兩個——前者衡量答案是否忠於 context，後者衡量答案是否切題。其他兩個（`context_recall`、`context_precision`）需要 ground truth，不一定有。全部都是 nullable，填多少算多少。

> **Stage 6 收穫**：查詢紀錄用正規化表（`query_log_results`）而非 array。記錄 Ragas 四大指標 + 使用者回饋，未來才能優化。

---

## Stage 7：你的知識庫健康嗎？

### 三個必看指標

```
知識庫健康度儀表板
═══════════════════════════════

  📊 collection_stats()
  ├── total_documents: 3        全部文件數
  ├── total_chunks: 8           全部切片數
  ├── chunks_with_embedding: 8  有 embedding 的切片
  ├── avg_chunk_tokens: 37.25   平均 chunk 大小
  ├── total_queries: 3          總查詢次數
  └── avg_faithfulness: 0.95    平均 Ragas 信度分數

  🎯 top_hit_chunks()
  ├── chunk "台南小吃..." hit_count: 2   ← 高價值內容
  ├── chunk "永康牛肉..." hit_count: 1
  └── chunk "台中宮原..." hit_count: 0   ← 從未被搜尋到！

  🕳️ 零命中 chunks
  └── 有些 chunk 從來沒被任何查詢命中
      → 可能是內容太冷門
      → 可能是切分方式不對
      → 也可能只是還沒有人問到
```

### 定期健檢

```sql
-- 每週跑一次
SELECT * FROM collection_stats('你的 collection id');

-- 找出從未被命中的 chunk
SELECT c.id, left(c.content, 50)
FROM chunks c
LEFT JOIN query_log_results r ON r.chunk_id = c.id
WHERE r.id IS NULL;
```

> **Stage 7 收穫**：`collection_stats()` 看整體健康、`top_hit_chunks()` 找高價值內容、零命中 chunks 是潛在的優化目標。

---

## 安全三層防線：RLS → GRANT → VIEW

學完七個 Stage，你的 RAG 資料庫已經能運作了。但如果不設定安全性，**任何人都能看到所有資料**。

接下來的三個章節是一組安全防線，缺一不可：

```
安全三層防線
═══════════════════════════════════════

  第一層：RLS（Row Level Security）
  ├── 決定「你能看到哪些列」
  └── 用 helper function 實現，不用 JOIN

  第二層：GRANT
  ├── 決定「你能不能進這張表」
  └── 忘記 GRANT = 有 RLS 也進不了門

  第三層：chunks_safe VIEW（Column Level）
  ├── 決定「你能看到哪些欄位」
  └── 隱藏 embedding 向量，防止智慧資產外洩

  三層缺一不可：
  ❌ 只有 RLS → 忘了 GRANT，進不了門
  ❌ 只有 GRANT → 沒有 RLS，看到所有人的資料
  ❌ 只有前兩層 → embedding 6KB 白傳 + 可被複製
```

### 為什麼需要 RLS？

想像你經營一個 SaaS RAG 平台，有三個客戶：

```
客戶 A：法律事務所（法律文件知識庫）
客戶 B：醫院（醫療指南知識庫）
客戶 C：餐廳（菜單和食譜知識庫）

如果客戶 A 搜尋時看到了客戶 B 的病歷... 💣
```

RLS（Row Level Security）確保每個使用者**只能看到自己的資料**。

### 我們的 RLS 策略

```
權限層級
═══════════════════════════════

  1. Owner（知識庫擁有者）
     → 可讀、可寫、可刪除
     → 用 owner_id 直接比對（O(1)，不查別的表）

  2. Public（公開知識庫）
     → 只能讀取 is_active = true 的 collection
     → 用 helper function 檢查（避免 subquery）

  3. Service Role（系統管道）
     → ETL pipeline、Cron Job 使用
     → 完全繞過 RLS（但只在後端使用）
```

### 絕對不能做的事

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│  ❌ 在 RLS policy 裡寫 JOIN                             │
│     → 每一筆 row 都跑一次 JOIN = CPU 爆炸               │
│                                                         │
│  ❌ 直接用 auth.uid()                                   │
│     → 每一筆 row 都重新計算                              │
│                                                         │
│  ✅ 用 helper function                                  │
│     → PostgreSQL 可以快取結果                            │
│                                                         │
│  ✅ 用 (SELECT auth.uid())                              │
│     → initPlan：整個查詢只算一次                         │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 我們的四個 helper function

Schema 裡定義了四個 `SECURITY DEFINER` + `STABLE` 函數，讓 RLS policy 保持乾淨：

```sql
-- 取得當前使用者 ID（包裝 auth.uid()，只算一次）
rag.get_current_owner_id()

-- 是否為該 collection 的擁有者？
rag.is_collection_owner(p_collection_id TEXT)

-- 該 collection 是否公開（is_active = true）？
rag.is_collection_active(p_collection_id TEXT)

-- 擁有者 OR 公開 → 可讀
rag.can_read_collection(p_collection_id TEXT)
```

RLS policy 全部呼叫這些函數，不寫 inline 查詢：

```sql
-- documents / chunks 的 SELECT policy 長這樣：
USING (
  owner_id = rag.get_current_owner_id()        -- O(1) 直接比對
  OR rag.is_collection_active(collection_id)    -- helper function
)

-- query_logs 的 SELECT policy：
USING (rag.can_read_collection(collection_id))  -- 一個函數搞定
```

```
為什麼不直接寫 auth.uid()？
═══════════════════════════════════════

  ❌  owner_id = auth.uid()::TEXT
      → 每一列都呼叫 auth.uid()
      → 100K 列 = 100K 次呼叫

  ✅  owner_id = rag.get_current_owner_id()
      → 函數內用 (SELECT auth.uid())
      → PostgreSQL initPlan，整個查詢只算一次
      → 100K 列 = 1 次呼叫
```

---

## GRANT：別忘了打開門

RLS 是鎖，GRANT 是鑰匙。你可以把 RLS 設得完美，但如果忘記 GRANT，使用者連門都進不去。

```sql
-- 每張表都需要（schema 裡已經寫好了）
GRANT SELECT ON rag.chunks TO authenticated, anon;
GRANT INSERT, UPDATE, DELETE ON rag.chunks TO authenticated;
GRANT ALL ON rag.chunks TO service_role;
```

**新手最常忘記的兩件事：**

1. 忘記 `GRANT EXECUTE ON FUNCTION` → 使用者無法呼叫搜尋函數
2. 忘記 `service_role` policy → ETL pipeline 寫入失敗

### 沒有笨問題 💡

> **問：`service_role` 不就是繞過 RLS 嗎？那設 RLS 還有什麼意義？**
>
> 答：`service_role` 只在後端（ETL pipeline、Cron Job）使用，**前端永遠拿不到 service_role key**。前端用 `anon` 或 `authenticated` 角色，這兩個角色受 RLS 約束。所以 RLS 保護的是前端使用者，service_role 是給你的後端管線用的「員工通道」。
>
> **問：`anon` 角色有 SELECT 權限，不是很危險嗎？**
>
> 答：`anon` + RLS = 只能看到公開資料（`is_active = true` 的 collection）。沒有 GRANT SELECT 的話，未登入使用者連公開知識庫都搜不到。GRANT 是「可以進門」，RLS 才決定「進門後能看到什麼」。

---

## 欄位級安全：你的前端不需要 6KB 的向量

### 問題

每個 chunk 的 `embedding` 欄位是 1536 個浮點數，大約佔 **6KB**。

如果前端執行 `SELECT * FROM chunks`，每一筆結果都帶著 6KB 的向量回來。查 100 筆就是 600KB 的**無用資料**——前端根本不做向量計算。

```
前端用 SELECT * 的代價
═══════════════════════════════════════

  100 筆 chunks × 6KB embedding = 600KB 白傳
  1000 筆 × 6KB = 6MB 白傳

  更糟的是：embedding 是你的「智慧資產」
  暴露給前端 = 任何人都能複製你的知識庫向量
```

### 解法：chunks_safe VIEW

```sql
-- Schema 裡已經定義好了
CREATE OR REPLACE VIEW rag.chunks_safe
  WITH (security_invoker = true)
  AS
  SELECT
    id, document_id, collection_id,
    content, chunk_index, token_count,
    -- ⚠️ embedding 欄位被排除！
    start_char, end_char, page_number,
    chunking_method, overlap_prev, overlap_next,
    owner_id, metadata, created_at, updated_at
  FROM rag.chunks;
```

```
類比：醫院病歷系統
═══════════════════════════════════════

  護理站螢幕（chunks_safe VIEW）：
  ├── 病人姓名 ✅
  ├── 房號 ✅
  ├── 用藥時間 ✅
  └── 完整病歷 ❌（看不到）

  醫生工作站（chunks 原始表）：
  ├── 所有護理站資訊 ✅
  └── 完整病歷 ✅（有權限）

  搜尋函數（SECURITY DEFINER）＝ 醫生
  前端 REST API              ＝ 護理站
```

**規則**：前端查詢一律用 `chunks_safe`，只有搜尋函數（`match_chunks` 等，以 `SECURITY DEFINER` 執行）才能存取 `chunks` 裡的 `embedding`。

### security_invoker = true 是什麼？

一般 VIEW 用**建立者**的權限執行查詢。加上 `security_invoker = true` 後改為用**查詢者**的權限。效果：

- `chunks_safe` 自動繼承 `chunks` 表的 RLS 規則
- 不需要對 VIEW 單獨設 RLS
- 使用者 A 查 `chunks_safe`，只看到自己有權存取的資料

### 沒有笨問題 💡

> **問：為什麼不直接在 RLS 裡擋 embedding 欄位？**
>
> 答：PostgreSQL 的 RLS 是 **Row-Level**（列層級），不是 Column-Level（欄位層級）。RLS 只能決定「你能不能看到這一整列」，沒辦法說「這列你可以看，但 embedding 欄位除外」。所以我們用 VIEW 來遮蔽欄位——這是 PostgreSQL 實現欄位級安全的標準做法。

---

## 完整流程回顧

```
從文件到答案的完整旅程
═══════════════════════════════════════════════════

  使用者上傳 PDF
       │
       ▼
  ┌─ documents ─┐
  │ uploaded     │ ← 收到檔案
  │ parsed       │ ← 文字萃取完成
  │ chunked      │ ← 切分完成
  │ embedded     │ ← embedding 完成
  │ ready        │ ← 可以被搜尋
  └──────────────┘
       │
       ▼
  ┌─ chunks ────────────────────┐
  │ content + embedding(1536)   │
  │ collection_id ← trigger     │ ← 安全護欄
  │ owner_id ← trigger          │ ← RLS 用
  └──────────────────────────────┘
       │
       ├── chunks_safe (VIEW)   │ ← 前端用，不含 embedding
       │
       ▼ 使用者提問
  ┌─ match_chunks() ───────────┐
  │ 語意搜尋：向量距離比較      │
  │ hybrid_search()：+ 全文搜尋 │
  └────────────────────────────┘
       │
       ▼
  ┌─ query_logs ───────────────┐
  │ 查詢文字 + 生成的答案       │
  │ Ragas 四大指標              │
  │ 使用者回饋                  │
  └────────────────────────────┘
       │
       ▼
  ┌─ query_log_results ────────┐
  │ 哪些 chunk 被命中？         │
  │ 排名和分數是多少？          │
  └────────────────────────────┘
       │
       ▼
  分析 → top_hit_chunks() → 優化知識庫
```

---

## 動手做

現在你理解了整個架構，是時候動手了。

打開 [04_lab-rag-pipeline.md](04_lab-rag-pipeline.md)，跟著 7 個 Stage 做一遍。

你會用「台灣美食」作為主題，從建立知識庫開始，一路做到語意搜尋和品質分析。

每個 Stage 結束後，回來這裡重讀對應的章節——你會發現第二次讀的時候，理解完全不一樣。

> **Head First 的讀法**
> 1. 先讀這份指南，建立整體印象
> 2. 動手做 Lab，遇到不懂的再回來查
> 3. 做完後，用自己的話解釋每個 Stage 的目的
> 4. 試著不看任何文件，畫出完整的資料流程圖

---

## 快速參考卡

### 資料表一覽

| 表 | 用途 | 對應 RAG 階段 |
|---|------|--------------|
| `embedding_models` | 模型註冊（1536 only） | Ch03 |
| `collections` | 知識庫 / tenant scope | 管理 |
| `documents` | 文件 + pipeline 狀態 | Ch02 Extract |
| `chunks` | 切片 + embedding | Ch02 + Ch03 |
| `tags` / `chunk_tags` | 語意標籤 | Ch02 Metadata |
| `query_logs` | 查詢紀錄 + 評估 | Ch06 |
| `query_log_results` | 命中明細 | Ch06 |
| `chunks_safe` (VIEW) | chunks 去除 embedding（前端用） | 安全 |

### 搜尋函數

| 函數 | 使用場景 |
|------|---------|
| `match_chunks()` | 基本語意搜尋 |
| `match_chunks_with_document()` | 語意搜尋 + 文件來源 |
| `hybrid_search()` | 語意 + 全文混合 |
| `collection_stats()` | 知識庫統計 |
| `top_hit_chunks()` | 命中率分析 |
| `chunks_safe` (VIEW) | 前端安全查詢（不含 embedding） |

### 狀態機

```
uploaded → parsed → chunked → embedded → ready
                                          ↑
                              任何階段 → failed
                              來源更新 → stale
```

---

---

## 在 Studio 中驗證你的 RAG Schema

> **前置要求**：已讀完 [01_supabase-studio.md](../01_supabase-studio.md)

跑完 `004_rag_schema.sql`（v3.0）後，打開 `http://localhost:54323` 驗證：

### Table Editor 驗證

```
📝 驗證清單
1. rag schema → 確認核心 8 張表出現
   (embedding_models, collections, documents, chunks, tags, chunk_tags, query_logs, query_log_results)
2. 點進 chunks → 確認有 embedding VECTOR(1536) 欄位
3. 點進 documents → 確認 process_status 欄位（7 態 FSM）
4. 確認 collections → documents → chunks 的 FK 鏈
5. 確認 chunks_safe VIEW 存在（不含 embedding 欄位）
6. 點進 collections 的設定 → 開啟 Realtime
   （讓前端即時顯示 ingestion 進度）
```

### SQL Editor 驗證

```sql
-- ⚠️ 先切換 search_path（或在表名前加 rag. 前綴）
SET search_path = rag, public;

-- 確認 pgvector 已啟用
SELECT * FROM pg_extension WHERE extname = 'vector';

-- 確認 ULID 正常
SELECT generate_ulid();

-- 確認 HNSW index 存在
SELECT indexname, indexdef
FROM pg_indexes
WHERE schemaname = 'rag' AND tablename = 'chunks' AND indexdef LIKE '%hnsw%';

-- 確認 chunks_safe VIEW 存在且不含 embedding
SELECT column_name FROM information_schema.columns
WHERE table_schema = 'rag' AND table_name = 'chunks_safe'
ORDER BY ordinal_position;
-- 應該看不到 embedding 欄位

-- 測試語意搜尋函數（需要先有 embedding 資料）
SELECT * FROM match_chunks(
  '[0.1, 0.2, ...]'::vector(1536),
  'YOUR_COLLECTION_ID',
  5, 0.7
);

-- 查看 ingestion pipeline 狀態分佈
SELECT process_status, count(*)
FROM documents
GROUP BY process_status;
```

### RLS 驗證

```sql
-- 確認 RLS 已啟用（8 張表都應該為 true）
SELECT tablename, rowsecurity
FROM pg_tables
WHERE schemaname = 'rag' AND tablename IN
  ('embedding_models','collections','documents','chunks',
   'tags','chunk_tags','query_logs','query_log_results');

-- 測試 collection 隔離
SET ROLE anon;
SELECT count(*) FROM rag.collections;  -- 應只看到 is_active=true 的
RESET ROLE;

-- 測試 helper function
SELECT rag.get_current_owner_id();  -- 無登入時應為 NULL
```

### 健康監控（上線後常用）

```sql
-- 知識庫統計
SELECT * FROM collection_stats('YOUR_COLLECTION_ID');

-- 命中率分析
SELECT * FROM top_hit_chunks('YOUR_COLLECTION_ID', 10);

-- 找出卡住的文件（超過 1 小時未完成）
SELECT id, title, process_status, updated_at
FROM documents
WHERE process_status NOT IN ('ready', 'failed')
  AND updated_at < NOW() - INTERVAL '1 hour';
```

---

## 下一步

```
學完 Supabase RAG 後，你有兩條路
═══════════════════════════════════════════════

  想繼續 RAG 理論？             想整合上線？
  ┌─────────────────┐          ┌─────────────────┐
  │ Ch04 LlamaIndex │          │ Module Pre-A    │
  │ Ch05 Agentic RAG│          │ Module A (MCP)  │
  │ Ch06 Evaluation │          │ Module B (UI)   │
  └─────────────────┘          └─────────────────┘
  回到 RAG 課程繼續              用 Supabase 當後端
```

- [回到 RAG 課程主頁](../../RAG/README.md)
- [Ch04 LlamaIndex](../../RAG/ch04-llamaindex.md)（支援 `PGVectorStore` 對接 Supabase）
- [Module A MCP Server](../../RAG/module-a-mcp-server.md)（用 `match_chunks()` 取代 Qdrant 搜尋）
- [動手做 Lab](04_lab-rag-pipeline.md)（7 階段實操，邊做邊學）

---

*最後更新：2026-03*

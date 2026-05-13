# ch09 — RAG Bridge：爬蟲資料對接知識庫

![ch09 RAG Bridge](ch09.png)

## 定位

本章是 project-playwright **教學的收口章**。  
ch01–ch08 帶你從零學會 Playwright、Supabase Pipeline、內容抽取與去重。  
本章把成果接上 **project-linebot-rag-skills**，讓爬下來的文章進入 RAG 知識庫，
由 LINE Bot 直接回答問題。

```
ch01–ch07                ch08                        ch09
瀏覽器自動化技能  →  Playwright × Supabase  →  RAG Bridge
（選擇器/互動/       Pipeline（Job Queue /          （embed → 向量庫
  抽取/等待）          Fetch / Persist）              → LINE Bot）
```

---

## 學習目標

1. 理解**兩個專案共用同一個 Supabase 實例**的設計模式
2. 掌握 `crawler.articles` → `KnowledgeChunkInsert` 的欄位對應關係
3. 實際執行跨專案的 Embedding Pipeline（chunk → embed → upsert）
4. 理解 `content_hash` 在去重與增量更新中的角色
5. 完成「爬蟲 → 知識庫 → LINE Bot 回答」的端對端驗收

---

## 前置需求

### 1. 兩個專案都已設定完成

| 專案 | 驗收指令 |
|------|---------|
| project-playwright | `python ch08-supabase/04_single_job_worker.py`（有文章入庫） |
| project-linebot-rag-skills | `uv run pytest tests/ -q`（287+ passed） |

確認 Ch08 確實寫入文章（至少 1 筆），可在 Supabase SQL Editor 執行：

```sql
select count(*), min(created_at), max(created_at)
from crawler.articles;
```

或用 psql / TablePlus 直接查。若 count = 0，請先跑 Ch08 爬蟲：

```bash
python ch08-supabase/02_seed_source.py
python ch08-supabase/03_enqueue_urls.py
python ch08-supabase/04_single_job_worker.py --loop
```

### 2. 共用同一個 Supabase 實例

兩個專案的 `.env` 必須填入**相同的** `SUPABASE_URL`。

```
# project-playwright/.env
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_SERVICE_KEY=<service_role_key>

# project-linebot-rag-skills/.env
SUPABASE_URL=https://xxxx.supabase.co       ← 同一個
SUPABASE_SERVICE_ROLE_KEY=<service_role_key>
```

> 本機 Docker 用 `http://127.0.0.1:55421`（見 ch08 說明）。

### 3. Embedding API 金鑰

`ingest.py articles` 會呼叫 Embedding API（預設 OpenAI），
需在 project-linebot-rag-skills 的 `.env` 填入：

```env
OPENAI_API_KEY=sk-...
```

或改用 Gemini：

```env
EMBEDDING_PROVIDER=gemini
GEMINI_API_KEY=...
```

---

## 範例檔案

| 檔案 | 說明 |
|------|------|
| `01_apply_migration.py` | 驗證 `category` / `source_type` 欄位是否已建立；未建立則印 SQL |
| `02_verify_rag_schema.py` | 從 Supabase 撈樣本，印出欄位對照表，確認資料格式正確 |
| `03_trigger_ingest.py` | 跨專案橋接：呼叫 linebot-rag-skills 的 `ingest.py articles` |
| `04_end_to_end_demo.py` | 最終驗收：統計文章數、確認 category/source_type 齊全 |

---

## 執行順序

```bash
cd project-playwright

# Step 1：套用 Migration（第一次執行才需要）
python ch09-rag-bridge/01_apply_migration.py

# Step 2：驗證欄位對應
python ch09-rag-bridge/02_verify_rag_schema.py

# Step 3：觸發 IngestionPipeline（dry-run 預覽，不動資料）
python ch09-rag-bridge/03_trigger_ingest.py --category nextjs

# Step 3：確認無誤後實際執行
python ch09-rag-bridge/03_trigger_ingest.py --category nextjs --run

# Step 4：端對端驗收
python ch09-rag-bridge/04_end_to_end_demo.py --category nextjs
```

**Windows PowerShell：**

```powershell
.venv\Scripts\activate
python ch09-rag-bridge\01_apply_migration.py
python ch09-rag-bridge\02_verify_rag_schema.py
python ch09-rag-bridge\03_trigger_ingest.py --category nextjs
python ch09-rag-bridge\03_trigger_ingest.py --category nextjs --run
python ch09-rag-bridge\04_end_to_end_demo.py --category nextjs
```

---

## 資料流

```
[project-playwright]
  crawler.sources          ← ch08 02_seed_source.py 建立
         |
  crawler.crawl_queue      ← ch08 03_enqueue_urls.py 入列
         |
  04_single_job_worker.py（ch08）
    └─ BrowserManager → ArticleExtractor
         |
  crawler.articles
    ├─ source_url           (= source_id in linebot)
    ├─ title
    ├─ content_text         (待 chunk)
    ├─ content_hash         (SHA-256，去重 key)
    ├─ category             ← ch09 新增欄位
    └─ source_type = 'web'  ← ch09 新增欄位

         │  共用 Supabase 實例
         │  Accept-Profile: crawler
         ▼

[project-linebot-rag-skills]
  SupabaseArticleIngester   ← ch09 新增元件
    └─ yield Document
         |
  IngestionPipeline
    ├─ source_hash()  →  如果 content_hash 相同 → unchanged（跳過）
    ├─ Chunker        →  切分 content_text
    ├─ EmbedBackend   →  呼叫 Embedding API
    └─ KnowledgeStore.upsert()
         |
  private_knowledge（向量庫）
         |
  LINE Bot → 回答爬下來的內容 ✅
```

---

## 欄位對照表

| `crawler.articles` | `KnowledgeChunkInsert` | 說明 |
|--------------------|------------------------|------|
| `source_url` | `source_id` | URL 作為文件唯一識別（去重 key） |
| `source_url` | `source_url` | |
| `title` | `title` | |
| `content_text` | `content` | 由 Chunker 切分後逐 chunk 寫入 |
| `content_hash` | `content_hash` | hash 不變 → pipeline 跳過 embed |
| `category` | `category` | ← ch09 新增欄位 |
| `source_type` | `source_type` | ← ch09 新增欄位，固定 `'web'` |
| `meta → tags` | `tags` | JSONB 內的 tags 陣列 |
| *(EmbedBackend 產生)* | `embedding` | 由 linebot-rag-skills 的 EmbedBackend 計算 |

---

## 增量更新機制

`IngestionPipeline` 在 embed 前會呼叫 `store.source_hash(source_id)`，
比對 `private_knowledge` 裡已存的 `content_hash`。

```
第一次執行：
  source_hash("https://nextjs.org/docs/...") → None（不在 store）
  → 正常 embed → upsert

第二次執行（文章未更新）：
  source_hash("https://nextjs.org/docs/...") → "a1b2c3..."（相同）
  → unchanged += 1，跳過，節省 Embedding API 費用

文章更新後執行：
  source_hash("https://nextjs.org/docs/...") → "old_hash"（不同）
  → 重新 embed → upsert（覆蓋舊向量）
```

執行輸出範例：

```
[supabase_articles] docs=35 chunks=280 skipped=0 unchanged=7
                                                  ↑
                                          7 篇內容未變，已跳過
```

---

## 常見問題

### Q: `01_apply_migration.py` 說欄位不存在

執行 `supabase db push`（CLI 方法），或把 migration SQL 貼入 Supabase Dashboard → SQL Editor。

若使用本機 Docker，確認已執行 `supabase start`（ch08 前置需求）。

### Q: `02_verify_rag_schema.py` 顯示「crawler.articles 目前沒有資料」

請先執行 ch08 的爬蟲流程：

```bash
python ch08-supabase/02_seed_source.py
python ch08-supabase/03_enqueue_urls.py
python ch08-supabase/04_single_job_worker.py --loop
```

### Q: `03_trigger_ingest.py` 找不到 linebot-rag-skills 專案

確認目錄結構：

```
data-science-2026/
├── project-playwright/        ← 目前所在
└── project-linebot-rag-skills/ ← 自動偵測此路徑
```

或手動指定：

```bash
python ch09-rag-bridge/03_trigger_ingest.py \
  --linebot-path /your/path/to/project-linebot-rag-skills \
  --category nextjs --run
```

### Q: `category` 欄位全部是 `(空)`，pipeline 補了 `general`

爬蟲抓的文章如果 `draft.categories` 是空的，`article_repo.py` 就會寫入 `None`，
pipeline 再補預設值 `"general"`。

解法：在 `ch08-supabase/02_seed_source.py` 的 `extractor_schema` 加入 `categories` 選擇器，
或在 `utils/worker/extractors/article_extractor.py` 手動指定分類。

### Q: Embedding 很慢或費用擔憂

加 `--limit` 限制每次處理數量：

```bash
python ch09-rag-bridge/03_trigger_ingest.py --category nextjs --limit 10 --run
```

第二次執行（`unchanged` 計數）不會重複呼叫 Embedding API。

### Q: 如何確認 LINE Bot 已讀到新知識？

對 Bot 提問一個只有剛爬下來的文章才能回答的問題。
或查 `private_knowledge`：

```sql
select source_id, title, category
from private_knowledge
where source_type = 'web'
order by id desc
limit 10;
```

---

## 進階

### 自動化排程

設定 cron 讓爬蟲 + embed 每日自動執行：

```bash
# crontab -e
# 每天 02:00 爬蟲
0 2 * * * cd /path/to/project-playwright && python utils/worker/main.py

# 每天 04:00 embed（等爬蟲完成）
0 4 * * * cd /path/to/project-linebot-rag-skills && \
  python scripts/ingest.py articles --since $(date -v-1d +%Y-%m-%d)
```

### 支援多個分類

分別入列、分別 embed：

```bash
# 爬蟲端（ch08）
python ch08-supabase/03_enqueue_urls.py --source nextjs
python ch08-supabase/03_enqueue_urls.py --source react

# embed 端（ch09）
python ch09-rag-bridge/03_trigger_ingest.py --category nextjs --run
python ch09-rag-bridge/03_trigger_ingest.py --category react --run
```

### KnowledgeStore backend 切換

`ingest.py articles` 支援所有 backend：

```bash
# sqlite-vec（本機零依賴）
KNOWLEDGE_STORE_BACKEND=sqlite_vec \
  python scripts/ingest.py articles --category nextjs

# Pinecone（生產）
KNOWLEDGE_STORE_BACKEND=pinecone \
  python scripts/ingest.py articles --category nextjs
```

---

## 自我檢核

完成本章（整個課程）後，你應該能回答：

1. 兩個專案（project-playwright、project-linebot-rag-skills）共用同一個 Supabase 實例，但資料互不干擾。這是怎麼做到的？（提示：`Accept-Profile` header、schema 隔離）
2. 第二次執行 `03_trigger_ingest.py --run` 時，`unchanged` 計數增加、`docs` 計數相同。如果你修改了某篇文章的內容再跑，這兩個數字會怎麼變？
3. 從「爬蟲抓到一篇文章」到「LINE Bot 能用它回答問題」，完整的資料流經過哪些步驟？請不看文件，自己畫出來。

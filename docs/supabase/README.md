# 資料科學 × Supabase × PostgreSQL — 7-Stage 學習路線圖

> 從 Notebook → API → 可部署資料系統
> 從 分析者 → 系統型資料科學家

---

## 課程定位

給懂 Python / 資料分析，但對資料庫與雲端後端不熟的學生。
目標：讓學生能夠把資料分析專案，從「Jupyter Notebook」升級成「可部署、可查詢、可控權限的資料系統」。

### 前置要求

- Python 基礎（pandas, numpy）
- SQL SELECT 基本語法
- 基本命令列操作

---

## 7-Stage 學習路線圖

```
                    ┌─────────────────┐
                    │  Stage 1 (2h)   │
                    │  資料庫入門      │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  Stage 2 (6h)   │
                    │  Studio 觀念+實操│
                    └──┬─────┬─────┬──┘
                       │     │     │
            ┌──────────▼┐ ┌─▼──────────┐ ┌▼──────────┐
            │ Stage 3   │ │ Stage 4    │ │ Stage 5   │
            │ 電商 (4h) │ │ 爬蟲 (3h) │ │ RAG (3h)  │
            └─────┬─────┘ └─────┬──────┘ └─────┬─────┘
                  └─────────────┼───────────────┘
                       ┌────────▼────────┐
                       │  Stage 6 (4h)   │
                       │  跨域分析        │
                       └────────┬────────┘
                       ┌────────▼────────┐
                       │  Stage 7 (3h)   │
                       │  Public API     │
                       └─────────────────┘

  Stage 1 → Stage 2 → (Stage 3 | Stage 4 | Stage 5) → Stage 6 → Stage 7
  Stage 3、4、5 彼此獨立，皆需完成 Stage 1 + 2
  Stage 6、7 需完成 Stage 3 + 4 + 5（跨越三個領域）
```

---

### Stage 1：資料庫入門 — 正規化與關聯式思維

| 項目 | 說明 |
|------|------|
| **核心問題** | 資料為什麼不能只存 CSV？正規化到底在做什麼？ |
| **前置條件** | Python 基礎、SQL SELECT |
| **教材** | [00_database-fundamentals.md](00_database-fundamentals.md) |
| **預估時數** | ~2h |

---

### Stage 2：Supabase Studio — 觀念 + 實操

| 項目 | 說明 |
|------|------|
| **核心問題** | Supabase Studio 怎麼用？五大模組各自負責什麼？ |
| **前置條件** | Stage 1 完成 |
| **觀念教材** | [01_supabase-studio.md](01_supabase-studio.md)（原理 + 架構，~2h） |
| **實操教材** | [02_studio/00_README.md](02_studio/00_README.md)（9 章 step-by-step，~4h） |
| **預估時數** | ~6h（觀念 2h + 實操 4h） |

---

### Stage 3：電商資料庫設計（Head First 風格）

| 項目 | 說明 |
|------|------|
| **核心問題** | 真實電商系統的資料庫怎麼設計？訂單、庫存、RLS 如何搭配？ |
| **前置條件** | Stage 1 + 2 完成 |
| **教材** | [03_shop/00_README.md](03_shop/00_README.md)（6 章） |
| **SQL Schema** | [migrations/002_shop_schema.sql](migrations/002_shop_schema.sql) |
| **預估時數** | ~4h |

---

### Stage 4：爬蟲 ETL 資料庫設計

| 項目 | 說明 |
|------|------|
| **核心問題** | 爬蟲系統的資料怎麼收、怎麼存、怎麼追蹤狀態？ |
| **前置條件** | Stage 1 + 2 完成 |
| **教材** | [04_crawler/00_README.md](04_crawler/00_README.md)（10 章） |
| **SQL Schema** | [migrations/003_crawler_schema.sql](migrations/003_crawler_schema.sql) |
| **預估時數** | ~3h |

---

### Stage 5：RAG 向量資料庫設計

| 項目 | 說明 |
|------|------|
| **核心問題** | LLM 應用的向量搜尋怎麼做？Embedding 怎麼存進 PostgreSQL？ |
| **前置條件** | Stage 1 + 2 完成 |
| **教材** | [05_rag/00_README.md](05_rag/00_README.md)（4 章） |
| **SQL Schema** | [migrations/004_rag_schema.sql](migrations/004_rag_schema.sql) |
| **預估時數** | ~3h |

---

### Stage 6：跨域觀測與商業智慧（Analytics）

| 項目 | 說明 |
|------|------|
| **核心問題** | 三個領域的數據怎麼整合觀測？時間序列、漏斗、Cohort 怎麼做？ |
| **前置條件** | Stage 3 + 4 + 5 完成 |
| **教材** | [06_analytics/00_README.md](06_analytics/00_README.md)（6 章） |
| **SQL Schema** | [migrations/005_analytics_schema.sql](migrations/005_analytics_schema.sql) |
| **預估時數** | ~4h |

---

### Stage 7：Public API Layer — PostgREST Gateway

| 項目 | 說明 |
|------|------|
| **核心問題** | 前端怎麼安全地呼叫後端？SECURITY DEFINER 的 RPC 模式怎麼設計？ |
| **前置條件** | Stage 3 + 4 + 5 完成 |
| **教材** | [07_api/00_README.md](07_api/00_README.md)（5 章） |
| **SQL Schema** | [migrations/006_public_api.sql](migrations/006_public_api.sql) |
| **預估時數** | ~3h |

---

## SQL Migrations 完整清單

| 檔案 | 用途 | 對應 Stage |
|------|------|-----------|
| [001_extensions.sql](migrations/001_extensions.sql) | 啟用 pgvector、pgcrypto 等擴充 | 基礎 |
| [002_shop_schema.sql](migrations/002_shop_schema.sql) | 電商 schema | Stage 3 |
| [003_crawler_schema.sql](migrations/003_crawler_schema.sql) | 爬蟲 schema | Stage 4 |
| [004_rag_schema.sql](migrations/004_rag_schema.sql) | RAG 向量 schema | Stage 5 |
| [005_analytics_schema.sql](migrations/005_analytics_schema.sql) | 跨域分析 schema | Stage 6 |
| [006_public_api.sql](migrations/006_public_api.sql) | Public RPC API | Stage 7 |
| [007_realtime.sql](migrations/007_realtime.sql) | Realtime 訂閱設定 | 進階 |
| [008_storage_buckets.sql](migrations/008_storage_buckets.sql) | Storage 檔案管理 | 進階 |
| [009_webhooks.sql](migrations/009_webhooks.sql) | Webhook 設定 | 進階 |
| [010_cron_jobs.sql](migrations/010_cron_jobs.sql) | pg_cron 排程 | 進階 |
| [011_vault_secrets.sql](migrations/011_vault_secrets.sql) | Vault 機密管理 | 進階 |
| [012_seed_data.sql](migrations/012_seed_data.sql) | 種子資料 | 測試 |
| [013_rls_testing.sql](migrations/013_rls_testing.sql) | RLS 驗證測試 | 測試 |

---

## 實驗講義

| 實驗 | 主題 | 對應 Stage | 時數 |
|------|------|-----------|------|
| [實驗 1](labs/00_lab-supabase-architecture.md) | 理解 Supabase 與 PostgreSQL 的關係 | Stage 1-2 | 1.5h |
| [實驗 2](labs/01_lab-postgresql-core.md) | PostgreSQL 核心操作（資料科學場景） | Stage 1 | 2h |
| [實驗 3](labs/02_lab-python-connection.md) | Python 連接 Supabase | Stage 2 | 1.5h |
| [實驗 4](labs/03_lab-rls.md) | RLS（資料科學最重要的一課） | Stage 2-3 | 1h |
| [實驗 5](labs/04_lab-api.md) | 建立簡易資料科學 API | Stage 7 | 1h |
| [Docker 實驗](labs/05_lab-docker-supabase.md) | Docker + Supabase 本地開發環境 | Stage 2（前置） | 3h |
| [實驗 6](labs/06_lab-realtime-storage.md) | Realtime 即時訂閱 + Storage 檔案管理 | 進階 | 2h |
| [實驗 7](labs/07_lab-seed-and-testing.md) | Seed Data 策略 + RLS 驗證方法 | 進階 | 1.5h |

## 作業與評量

| 作業 | 主題 | 分數 |
|------|------|------|
| [作業一](assignments/00_hw-sql-basics.md) | 基礎 SQL — 電商訂單資料庫 | 20 分 |
| [作業二](assignments/01_hw-jsonb.md) | JSONB 應用 — AI 模型結果資料庫 | 20 分 |
| [作業三](assignments/02_hw-python-supabase.md) | Supabase + Python 整合 | 20 分 |
| [作業四](assignments/03_hw-rls-advanced.md) | RLS 進階 — 多租戶設計 | 20 分 |
| [期末專題](assignments/04_final-project.md) | 整合專題 | 40 分 |

---

## 課程時數建議

### 精簡版（6-9 小時）

適合工作坊或密集營：Stage 1 → Stage 2（觀念） → 任選一個 Stage 3/4/5

### 標準版（18 小時）

Stage 1 → Stage 2 → Stage 3 + 4 + 5

### 完整版（25 小時）

七個 Stage 全部完成 + 實驗 + 作業

### 18 週學期版（完整排程）

| 週次 | 主題 | 對應教材 |
|------|------|---------|
| 1 | 資料科學全貌與產品化思維 | 課程導論 |
| 2 | SQL 基礎與資料建模 | Stage 1：[00_database-fundamentals.md](00_database-fundamentals.md) |
| 3 | PostgreSQL 進階（Index、JSONB、Window Function） | Stage 1 + [作業一](assignments/00_hw-sql-basics.md) |
| 4 | Pandas × SQL 整合 | [實驗 2](labs/01_lab-postgresql-core.md) |
| 5 | 特徵工程與模型輸出設計 | [作業二](assignments/01_hw-jsonb.md) |
| 6 | Supabase 架構與 Studio 觀念 | Stage 2：[01_supabase-studio.md](01_supabase-studio.md) |
| 7 | Docker 本地開發環境 | [Docker 實驗](labs/05_lab-docker-supabase.md) |
| 8 | Studio 實操 + Migration 版控 | Stage 2：[02_studio/](02_studio/00_README.md) |
| 9 | RLS 與多租戶設計 | [實驗 4](labs/03_lab-rls.md) + [作業四](assignments/03_hw-rls-advanced.md) |
| 10 | Python API 整合 | [實驗 3](labs/02_lab-python-connection.md) + [作業三](assignments/02_hw-python-supabase.md) |
| 11 | 電商資料庫設計 | Stage 3：[03_shop/](03_shop/00_README.md) |
| 12 | 爬蟲 ETL 資料庫設計 | Stage 4：[04_crawler/](04_crawler/00_README.md) |
| 13 | RAG 向量資料庫設計 | Stage 5：[05_rag/](05_rag/00_README.md) |
| 14 | 跨域分析與 Materialized View | Stage 6：[06_analytics/](06_analytics/00_README.md) |
| 15 | Public API Layer + 部署 | Stage 7：[07_api/](07_api/00_README.md) |
| 16 | 期末專題啟動（選題 + Schema 設計） | [期末專題](assignments/04_final-project.md) |
| 17 | 期末專題實作 | Python API + RLS + 測試 |
| 18 | 期末專題發表 | 簡報 10 分鐘 + Demo + Q&A |

---

## 目錄結構

```
docs/supabase/
├── README.md                      ← 你在這裡
├── 00_database-fundamentals.md    # Stage 1：正規化與關聯式思維
├── 01_supabase-studio.md          # Stage 2：Studio 觀念（原理 + 架構）
├── 02_studio/                     # Stage 2：Studio 實操（9 章 step-by-step）
├── 03_shop/                       # Stage 3：電商資料庫（6 章）
├── 04_crawler/                    # Stage 4：爬蟲 ETL（10 章）
├── 05_rag/                        # Stage 5：RAG 向量資料庫（4 章）
├── 06_analytics/                  # Stage 6：跨域觀測與商業智慧（6 章）
├── 07_api/                        # Stage 7：Public API Layer（5 章）
├── migrations/                    # SQL Schema（001-013）
├── labs/                          # 實驗講義（8 份）
└── assignments/                   # 作業與評量（5 份）
```

---

## 教學核心哲學

這門課不是教 Supabase。它在教：**系統型資料科學思維**。

### 為什麼這門課重要？

| 只會 Pandas | 會 Supabase |
|-------------|-------------|
| 分析型 | 系統型 |
| 做報告 | 做產品 |
| Notebook | API |
| 無權限 | RLS |
| 無部署 | 雲端化 |

### 三種層次的資料科學家

| 層次 | 工具 | 產出 | 能力邊界 |
|------|------|------|----------|
| **分析者** | Pandas、Jupyter | 報告、圖表 | 無法部署、無法協作 |
| **資料工程師** | PostgreSQL、SQL、Index | 結構化資料模型 | 資料建模、查詢優化 |
| **產品型資料科學家** | Supabase、REST API、RLS | 可部署的資料系統 | API 設計、權限控制、系統架構 |

### 這門課培養的職場能力

學生畢業後會具備：資料庫設計、權限控制、API 設計、部署流程、Migration 管理、版本控制。

**這些能力比多會一個模型重要。**

> PostgreSQL 是資料科學的「資料引擎」
> Supabase 是資料科學的「產品化引擎」

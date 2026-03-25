# 資料科學 × Supabase × PostgreSQL — 5-Stage 學習路線圖

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

## 5-Stage 學習路線圖

```
                    ┌─────────────────┐
                    │  Stage 1 (2h)   │
                    │  資料庫入門      │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  Stage 2 (2h)   │
                    │  Studio 操作    │
                    └──┬─────┬─────┬──┘
                       │     │     │
            ┌──────────▼┐ ┌─▼──────────┐ ┌▼──────────┐
            │ Stage 3   │ │ Stage 4    │ │ Stage 5   │
            │ 電商 (4h) │ │ 爬蟲 (3h) │ │ RAG (3h)  │
            └───────────┘ └────────────┘ └───────────┘

  Stage 1 → Stage 2 → (Stage 3 | Stage 4 | Stage 5)
  Stage 3、4、5 彼此獨立，皆需完成 Stage 1 + 2
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

### Stage 2：Supabase Studio 五大模組操作

| 項目 | 說明 |
|------|------|
| **核心問題** | Supabase Studio 怎麼用？五大模組各自負責什麼？ |
| **前置條件** | Stage 1 完成 |
| **教材** | [01_supabase-studio.md](01_supabase-studio.md) |
| **預估時數** | ~2h |

---

### Stage 3：電商資料庫設計（Head First 風格）

| 項目 | 說明 |
|------|------|
| **核心問題** | 真實電商系統的資料庫怎麼設計？訂單、庫存、RLS 如何搭配？ |
| **前置條件** | Stage 1 + 2 完成 |
| **教材** | [e-Commerce/00_README.md](e-Commerce/00_README.md) |
| **SQL Schema** | [e-Commerce/01_shop_supabase_native_schema.sql](e-Commerce/01_shop_supabase_native_schema.sql) |
| **預估時數** | ~4h |

---

### Stage 4：爬蟲 ETL 資料庫設計

| 項目 | 說明 |
|------|------|
| **核心問題** | 爬蟲系統的資料怎麼收、怎麼存、怎麼追蹤狀態？ |
| **前置條件** | Stage 1 + 2 完成 |
| **教材** | [crawler/00_README.md](crawler/00_README.md) |
| **SQL Schema** | [crawler/03_playwright_crawler_schema.sql](crawler/03_playwright_crawler_schema.sql) |
| **預估時數** | ~3h |

---

### Stage 5：RAG 向量資料庫設計

| 項目 | 說明 |
|------|------|
| **核心問題** | LLM 應用的向量搜尋怎麼做？Embedding 怎麼存進 PostgreSQL？ |
| **前置條件** | Stage 1 + 2 完成 |
| **教材** | [RAG/01_guide-supabase-rag.md](RAG/01_guide-supabase-rag.md) |
| **SQL Schema** | [RAG/05_rag_supabase_schema.sql](RAG/05_rag_supabase_schema.sql) |
| **預估時數** | ~3h |

---

## 補充教材

| 文件 | 說明 |
|------|------|
| [02_why-postgresql.md](02_why-postgresql.md) | PostgreSQL 基礎：為什麼資料科學需要它？ |
| [03_what-is-supabase.md](03_what-is-supabase.md) | Supabase 架構概述 |
| [04_supabase-hands-on.md](04_supabase-hands-on.md) | Supabase 實作（從 0 到完成） |
| [05_project-practice.md](05_project-practice.md) | 資料科學專案實戰 |
| [06_strategic-significance.md](06_strategic-significance.md) | Supabase 在資料科學的戰略意義 |

---

## 實驗講義

| 實驗 | 主題 | 時數 |
|------|------|------|
| [實驗 1](labs/00_lab-supabase-architecture.md) | 理解 Supabase 與 PostgreSQL 的關係 | 1.5h |
| [實驗 2](labs/01_lab-postgresql-core.md) | PostgreSQL 核心操作（資料科學場景） | 2h |
| [實驗 3](labs/02_lab-python-connection.md) | Python 連接 Supabase | 1.5h |
| [實驗 4](labs/03_lab-rls.md) | RLS（資料科學最重要的一課） | 1h |
| [實驗 5](labs/04_lab-api.md) | 建立簡易資料科學 API | 1h |
| [Docker 實驗](labs/05_lab-docker-supabase.md) | Docker + Supabase 本地開發環境 | 3h |

## 作業與評量

| 作業 | 主題 | 分數 |
|------|------|------|
| [作業一](assignments/00_hw-sql-basics.md) | 基礎 SQL — 電商訂單資料庫 | 20 分 |
| [作業二](assignments/01_hw-jsonb.md) | JSONB 應用 — AI 模型結果資料庫 | 20 分 |
| [作業三](assignments/02_hw-python-supabase.md) | Supabase + Python 整合 | 20 分 |
| [作業四](assignments/03_hw-rls-advanced.md) | RLS 進階 — 多租戶設計 | 20 分 |
| [期末專題](assignments/04_final-project.md) | 整合專題 | 40 分 |

## 課程藍圖

| 文件 | 說明 |
|------|------|
| [18 週課程藍圖](course-blueprint-18weeks.md) | 完整學期規劃 |

---

## 課程時數建議

### 精簡版（6-9 小時）

適合工作坊或密集營：Stage 1 → Stage 2 → 任選一個 Stage 3/4/5

### 標準版（14 小時）

Stage 1 → Stage 2 → Stage 3 + Stage 4 或 Stage 5

### 完整版（18 週）

五個 Stage 全部完成 + 實驗 + 作業，詳見 [18 週課程藍圖](course-blueprint-18weeks.md)

---

## 教學核心哲學

這門課不是教 Supabase。它在教：**系統型資料科學思維**。

三層能力：
1. **分析能力** — Pandas、統計、模型
2. **資料建模能力** — PostgreSQL、Schema、Index
3. **系統設計能力** — API、RLS、部署、Migration

> 只會 Pandas 是分析者
> 會 PostgreSQL 是資料工程師
> 會 Supabase 是產品型資料科學家

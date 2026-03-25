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
| **教材** | [shop/00_README.md](shop/00_README.md) |
| **SQL Schema** | [migrations/002_shop_schema.sql](migrations/002_shop_schema.sql) |
| **預估時數** | ~4h |

---

### Stage 4：爬蟲 ETL 資料庫設計

| 項目 | 說明 |
|------|------|
| **核心問題** | 爬蟲系統的資料怎麼收、怎麼存、怎麼追蹤狀態？ |
| **前置條件** | Stage 1 + 2 完成 |
| **教材** | [crawler/00_README.md](crawler/00_README.md) |
| **SQL Schema** | [migrations/003_crawler_schema.sql](migrations/003_crawler_schema.sql) |
| **預估時數** | ~3h |

---

### Stage 5：RAG 向量資料庫設計

| 項目 | 說明 |
|------|------|
| **核心問題** | LLM 應用的向量搜尋怎麼做？Embedding 怎麼存進 PostgreSQL？ |
| **前置條件** | Stage 1 + 2 完成 |
| **教材** | [RAG/01_guide-supabase-rag.md](RAG/01_guide-supabase-rag.md) |
| **SQL Schema** | [migrations/004_rag_schema.sql](migrations/004_rag_schema.sql) |
| **預估時數** | ~3h |

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
| [實驗 6](labs/06_lab-realtime-storage.md) | Realtime 即時訂閱 + Storage 檔案管理 | 2h |
| [實驗 7](labs/07_lab-seed-and-testing.md) | Seed Data 策略 + RLS 驗證方法 | 1.5h |

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

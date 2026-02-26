# 資料科學 × Supabase × PostgreSQL — 完整教案

> 從 Notebook → API → 可部署資料系統
> 從 分析者 → 系統型資料科學家

---

## 課程定位

給懂 Python / 資料分析，但對資料庫與雲端後端不熟的學生。
目標：讓學生能夠把資料分析專案，從「Jupyter Notebook」升級成「可部署、可查詢、可控權限的資料系統」。

---

## 課程目標

學生完成後應具備能力：

1. 理解 PostgreSQL 核心資料模型
2. 理解 Supabase 與 PostgreSQL 的關係
3. 能設計資料表、建立索引、寫 SQL
4. 能用 Python 連接 Supabase 查詢資料
5. 能設計 RLS（Row Level Security）
6. 能建構一個小型資料科學 API 專案

---

## 前置要求

- Python 基礎（pandas, numpy）
- SQL SELECT 基本語法
- 基本命令列操作

---

## 教材結構

### 章節教材

| 章節 | 主題 | 核心問題 |
|------|------|----------|
| [第一章](chapter-01-why-postgresql.md) | 資料科學為什麼需要 PostgreSQL？ | 只用 CSV / Pandas 為什麼不夠？ |
| [第二章](chapter-02-what-is-supabase.md) | Supabase 是什麼？與 PostgreSQL 的關係？ | Supabase 如何讓 PostgreSQL 產品化？ |
| [第三章](chapter-03-supabase-hands-on.md) | Supabase 實作（從 0 到完成） | 如何建表、連線、設定權限？ |
| [第四章](chapter-04-project-practice.md) | 資料科學專案實戰 | 如何建立模型預測平台？ |
| [第五章](chapter-05-strategic-significance.md) | Supabase 在資料科學的戰略意義 | 從分析者到產品型資料科學家 |

### 實驗講義

| 實驗 | 主題 | 時數 |
|------|------|------|
| [實驗 1](labs/lab-01-supabase-architecture.md) | 理解 Supabase 與 PostgreSQL 的關係 | 1.5h |
| [實驗 2](labs/lab-02-postgresql-core.md) | PostgreSQL 核心操作（資料科學場景） | 2h |
| [實驗 3](labs/lab-03-python-connection.md) | Python 連接 Supabase | 1.5h |
| [實驗 4](labs/lab-04-rls.md) | RLS（資料科學最重要的一課） | 1h |
| [實驗 5](labs/lab-05-api.md) | 建立簡易資料科學 API | 1h |
| [Docker 實驗](labs/lab-docker-supabase.md) | Docker + Supabase 本地開發環境 | 3h |

### 作業與評量

| 作業 | 主題 | 分數 |
|------|------|------|
| [作業一](assignments/hw-01-sql-basics.md) | 基礎 SQL — 電商訂單資料庫 | 20 分 |
| [作業二](assignments/hw-02-jsonb.md) | JSONB 應用 — AI 模型結果資料庫 | 20 分 |
| [作業三](assignments/hw-03-python-supabase.md) | Supabase + Python 整合 | 20 分 |
| [作業四](assignments/hw-04-rls-advanced.md) | RLS 進階 — 多租戶設計 | 20 分 |
| [期末專題](assignments/final-project.md) | 整合專題 | 40 分 |

### 完整課程藍圖

| 文件 | 說明 |
|------|------|
| [18 週課程藍圖](course-blueprint-18weeks.md) | 完整學期規劃 |

---

## 課程核心觀念

> PostgreSQL 是資料科學的「資料引擎」
> Supabase 是資料科學的「產品化引擎」

| 只會 Pandas | 會 Supabase |
|-------------|-------------|
| 分析型 | 系統型 |
| 做報告 | 做產品 |
| Notebook | API |
| 無權限 | RLS |
| 無部署 | 雲端化 |

---

## 課程時數建議

### 精簡版（6–9 小時）

適合工作坊或密集營

1. PostgreSQL 基礎 + JSONB（2h）
2. Supabase 架構 + Python 連線（2h）
3. RLS + API + 實作（2–3h）
4. 專案發表（2h）

### 標準版（18 小時）

適合一學期課程模組

- 第一階段：基礎（6h）— PostgreSQL、SQL、JSONB
- 第二階段：Supabase（6h）— 架構、Auth、RLS
- 第三階段：實戰（6h）— Python API、專案、發表

### 完整版（18 週）

適合獨立開課，詳見 [18 週課程藍圖](course-blueprint-18weeks.md)

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

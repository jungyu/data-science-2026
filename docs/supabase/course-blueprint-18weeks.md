# 18 週完整課程藍圖

課名：資料科學實務與系統落地

核心目標：
- 從 Notebook → API → 可部署資料系統
- 從 分析者 → 系統型資料科學家

---

## 第一階段：資料科學核心（Week 1–5）

> 目標：確保學生不是只有工具，而是理解資料

### Week 1 — 資料科學全貌與產品化思維

- 資料科學流程
- CRISP-DM
- 分析 vs 系統
- 真實世界資料流

**作業**：畫出「資料 → 模型 → API → 使用者」流程圖

---

### Week 2 — SQL 基礎與資料建模

- 關聯式資料庫
- ER Diagram
- Primary Key / Foreign Key
- 正規化

**練習**：設計一個電商資料庫

---

### Week 3 — PostgreSQL 進階（資料科學必備）

- Index
- Query Plan
- JSONB
- Aggregate
- Window Function

**練習**：使用 `EXPLAIN ANALYZE` 比較有無 Index 的查詢效能

---

### Week 4 — Pandas × SQL 整合

- SQL vs Pandas
- 何時用 DB
- 何時用 DataFrame
- 大資料處理策略

**練習**：同一個分析任務，分別用 SQL 和 Pandas 完成，比較差異

---

### Week 5 — 特徵工程與模型訓練

- sklearn
- 評估指標
- Cross Validation
- 模型輸出設計

**練習**：訓練模型並設計結構化的輸出格式（JSON）

---

## 第二階段：Supabase × PostgreSQL 系統化（Week 6–10）

### Week 6 — Supabase 架構與 PostgreSQL 關係

- Supabase 本質
- API 自動生成
- Auth
- RLS
- 為什麼它是 PostgreSQL

**對應教材**：[第二章](chapter-02-what-is-supabase.md)、[實驗 1](labs/lab-01-supabase-architecture.md)

---

### Week 7 — Docker 本地 Supabase 開發環境

這是課程升級的關鍵。

#### 安裝 Docker

```bash
docker --version
```

#### 安裝 Supabase CLI

```bash
npm install -g supabase
```

#### 初始化專案

```bash
supabase init
```

#### 啟動本地 Supabase

```bash
supabase start
```

這會建立：
- PostgreSQL container
- Auth container
- Realtime container
- Studio UI

#### 本地連線資訊

```
Host: localhost
Port: 54322
User: postgres
Password: postgres
```

**為什麼教 Docker 版本？**

- 不被 SaaS 綁架
- 可長期維運
- 可 Migration
- 可備份

**對應教材**：[Docker 實驗講義](labs/lab-docker-supabase.md)

---

### Week 8 — Migration 與版本控制

```bash
supabase migration new create_videos
```

產生 SQL Migration。

優點：
- DB 結構可版控
- 不靠 UI
- 可 CI/CD

**對應教材**：[Docker 實驗講義](labs/lab-docker-supabase.md)

---

### Week 9 — RLS 與多租戶設計

```sql
ALTER TABLE predictions ENABLE ROW LEVEL SECURITY;
```

設計：
- `user_id`
- `auth.uid()`

講解：
- SaaS 隔離
- 資料責任
- 法規思維

**對應教材**：[實驗 4](labs/lab-04-rls.md)、[作業四](assignments/hw-04-rls-advanced.md)

---

### Week 10 — Python API 整合

```python
from supabase import create_client
```

學生實作：
- Insert
- Select
- Update
- Filter

**對應教材**：[實驗 3](labs/lab-03-python-connection.md)、[作業三](assignments/hw-03-python-supabase.md)

---

## 第三階段：AI × JSONB × 產品化（Week 11–15）

### Week 11 — JSONB 與 AI 輸出設計

- 模型 Metadata
- 可追蹤設計
- 可重現設計

**對應教材**：[作業二](assignments/hw-02-jsonb.md)

---

### Week 12 — 建立預測 API

- REST
- 權限控制
- Token

**對應教材**：[實驗 5](labs/lab-05-api.md)

---

### Week 13 — 資料科學專案架構設計

學生必須畫出：
- DB Schema
- API Flow
- 使用者流程

**對應教材**：[第四章](chapter-04-project-practice.md)

---

### Week 14 — 效能與 Index 設計

- `EXPLAIN`
- Query Plan
- Index Tradeoff

---

### Week 15 — 部署（本地 → 雲端）

```bash
supabase link
supabase deploy
```

- 雲端與本地差異
- 環境變數管理
- 部署流程自動化

---

## 第四階段：期末專題（Week 16–18）

### Week 16 — 專題啟動

- 選題
- 設計資料模型
- 建立 Migration

### Week 17 — 專題實作

- 實作 Python API
- 設定 RLS
- 撰寫測試

### Week 18 — 專題發表

- 簡報（10 分鐘）
- 展示 Demo
- Q&A

**對應教材**：[期末專題](assignments/final-project.md)

---

## 專題要求

必須包含：

| 項目 | 必須 |
|------|------|
| PostgreSQL 設計 | ✔ |
| JSONB 使用 | ✔ |
| 至少 1 個 Index | ✔ |
| RLS | ✔ |
| Python API | ✔ |
| Docker 本地開發 | ✔ |
| Migration | ✔ |
| Git 版本控制 | ✔ |

---

## 評量設計

### 平時成績（60 分）

| 項目 | 分數 | 週次 |
|------|------|------|
| [作業一：基礎 SQL](assignments/hw-01-sql-basics.md) | 20 | Week 3 |
| [作業二：JSONB 應用](assignments/hw-02-jsonb.md) | 20 | Week 5 |
| [作業三：Python + Supabase](assignments/hw-03-python-supabase.md) | 20 | Week 10 |
| [作業四：RLS 進階](assignments/hw-04-rls-advanced.md) | 20 | Week 12 |

（取最高 3 份，共 60 分）

### 期末專題（40 分）

詳見 [期末專題評分](assignments/final-project.md)

---

## 課程核心哲學

這門課不是教 Supabase。它在教：

**系統型資料科學思維**

三層能力：
1. **分析能力** — Pandas、統計、模型
2. **資料建模能力** — PostgreSQL、Schema、Index
3. **系統設計能力** — API、RLS、部署、Migration

---

## 這門課的真正價值

學生畢業後會：

- 懂資料庫
- 懂權限
- 懂 API
- 懂部署
- 懂 Migration
- 懂版本控制

這些能力比多會一個模型重要。

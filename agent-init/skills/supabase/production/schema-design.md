---
name: supabase-schema-design-production
description: "生產級 Schema 設計：ULID 強制、資料分層、多租戶模型、資料科學表範例"
triggers:
  - "schema design"
  - "新增表"
  - "資料模型"
  - "多租戶"
  - "project_id"
finish_conditions:
  - "所有表使用 ULID (TEXT PK)"
  - "業務表包含 project_id"
  - "JSONB 僅用於非結構化資料"
  - "表名符合模組前綴慣例"
references:
  - docs/supabase/e-Commerce/README.md
  - docs/supabase/crawler/HEAD-FIRST-crawler-db.md
---

# Schema Design（生產級）

> ⚠️ **前置條件**：已完成 `foundations/schema-basics.md` 的學習。
> 本文件對應 e-Commerce Stage 1-10 和 Crawler HEAD-FIRST 的進階規範。

---

## 目的

強制分層架構、ULID 統一、多租戶模型、表結構一致性。避免 AI 在進階專案中產生不合規的 schema。

## Repo Reality

- `docs/supabase/e-Commerce/README.md` — 20 張表的完整電商 schema（ULID、Auth Bridge、RLS）
- `docs/supabase/e-Commerce/shop_supabase_native_schema.sql` — 電商 schema SQL
- `docs/supabase/crawler/HEAD-FIRST-crawler-db.md` — 10 張表，29 個違規修正

---

## 核心原則

### 1. 資料分層架構

```
Raw Layer       = 原始資料（爬蟲抓取、API 匯入、CSV 上傳）
Staging Layer   = 清理 / 轉換後的中繼資料
Analytics Layer = 聚合、特徵、模型輸入/輸出
Metadata Layer  = 實驗追蹤、資料集註冊
```

**不可違反**：
- 不要在 Raw 表直接做分析查詢 → 先 ETL 到 Staging/Analytics
- 不要在 DB 存大型二進位（模型權重、圖片原檔）→ 放 Storage，DB 只存 path
- 原始資料盡量 append-only（方便回溯）

### 2. 多租戶模型

使用 **single database + shared tables + tenant scoping**（e-Commerce Stage 2 教的模式）：

```sql
-- 所有業務表必須有 project_id
project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE
```

權限查詢走 helper functions，不在每張表重寫 JOIN。

### 3. 表結構必備欄位（ULID 版）

```sql
id TEXT PRIMARY KEY DEFAULT generate_ulid(),
created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
```

使用者操作的資料加：`created_by TEXT NOT NULL REFERENCES users(id)`

updated_at trigger：

```sql
CREATE TRIGGER trg_<table>_updated_at
  BEFORE UPDATE ON public.<table>
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

### 4. JSONB 使用原則

**黃金法則**（e-Commerce Stage 4）：
> 會被 `WHERE`、`ORDER BY`、`JOIN` 的欄位 → 獨立 column。其他 → JSONB。

**適合 JSONB**：爬蟲原始 payload、模型超參數、實驗配置、外部 API 回應。
**禁止 JSONB**：`project_id`、`status`、`name`、任何 filter/sort 欄位。

### 5. 模組表命名建議

| 模組 | 前綴 | 範例（來自 repo） |
|------|------|-----------------|
| 爬蟲 | `sources`, `crawl_*`, `articles` | Crawler: `sources`, `crawl_runs`, `articles` |
| 電商 | 無前綴 / 業務名 | e-Commerce: `products`, `orders`, `stocks` |
| 資料集 | `datasets`, `dataset_*` | 建議：`datasets`, `dataset_versions` |
| 實驗 | `experiments`, `experiment_*` | 建議：`experiments`, `experiment_runs` |
| ETL | `jobs_*` | 建議：`jobs_etl`, `jobs_training` |

---

## 實際範例：Crawler 的 sources 表（修正後）

來自 `HEAD-FIRST-crawler-db.md` Stage 2：

```sql
CREATE TABLE IF NOT EXISTS public.sources (
  id TEXT PRIMARY KEY DEFAULT generate_ulid(),
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  base_url TEXT NOT NULL,
  crawl_config JSONB DEFAULT '{}',
  status TEXT NOT NULL DEFAULT 'active'
    CHECK (status IN ('active', 'paused', 'archived')),
  created_by TEXT NOT NULL REFERENCES users(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_sources_project ON sources(project_id);
CREATE TRIGGER trg_sources_updated_at
  BEFORE UPDATE ON public.sources
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

## 常見錯誤

- ❌ 原始爬蟲資料和分析結果混同一表 → 分層：raw → staging → analytics
- ❌ 模型權重塞 DB → 放 Storage，DB 只存 metadata + path
- ❌ 超參數拆 100 個欄位 → JSONB
- ❌ 可篩選欄位放 JSONB → 拉出為獨立 column

## 參考來源

- `docs/supabase/e-Commerce/README.md` — Stage 1-10 完整架構
- `docs/supabase/crawler/HEAD-FIRST-crawler-db.md` — 29 違規修正

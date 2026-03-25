---
name: supabase-data-versioning-production
description: "資料版本化：資料集追蹤、實驗可重現性、模型產出記錄"
triggers:
  - "版本"
  - "versioning"
  - "實驗追蹤"
  - "dataset version"
  - "model version"
finish_conditions:
  - "資料集變更有版本紀錄"
  - "實驗結果可追溯到使用的資料版本"
references:
  - docs/supabase/chapter-04-project-practice.md
  - docs/supabase/e-Commerce/README.md
---

# Data Versioning（生產級）

> ⚠️ **前置條件**：已完成 foundations/ + `schema-design.md`。
> 🏷️ **進階**：適用於需要實驗可重現性的期末專題。

## Repo Reality

- `docs/supabase/chapter-04-project-practice.md` — predictions 表（基礎版，無版本化）
- `docs/supabase/e-Commerce/README.md` — Stage 6: Snapshot + Ledger 模式（概念相近）

---

## 為什麼需要版本化

ch04 的 `predictions` 表直接 INSERT：

```sql
-- ch04 模式：只有結果，沒有版本
CREATE TABLE predictions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID,
  input_data JSONB,
  output_data JSONB,
  created_at TIMESTAMP DEFAULT NOW()
);
```

**問題**：
- 換了資料集重新訓練，無法比較前後差異
- 不知道這個預測結果用了哪版資料、哪組超參數
- 無法重現過去的實驗

---

## 核心概念：Identity / Version 分離

```
datasets          → identity（名稱、描述、指標）
dataset_versions  → 不可變歷史（每次變更一筆）
```

### 資料集 Identity 表

```sql
CREATE TABLE IF NOT EXISTS public.datasets (
  id TEXT PRIMARY KEY DEFAULT generate_ulid(),
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  description TEXT,
  source_type TEXT NOT NULL
    CHECK (source_type IN ('csv', 'api', 'crawler', 'manual')),
  current_version_id TEXT,      -- 指向最新版本
  row_count INTEGER,
  status TEXT DEFAULT 'active'
    CHECK (status IN ('active', 'archived')),
  created_by TEXT NOT NULL REFERENCES users(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT uq_dataset_name UNIQUE(project_id, name)
);
```

### 資料集 Version 表（append-only）

```sql
CREATE TABLE IF NOT EXISTS public.dataset_versions (
  id TEXT PRIMARY KEY DEFAULT generate_ulid(),
  dataset_id TEXT NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
  version_no INTEGER NOT NULL,
  storage_path TEXT NOT NULL,           -- Storage 中的實際檔案
  file_format TEXT DEFAULT 'csv'
    CHECK (file_format IN ('csv', 'parquet', 'json')),
  row_count INTEGER,
  schema_snapshot JSONB DEFAULT '{}',   -- 欄位名與型別
  checksum TEXT,                        -- SHA-256
  created_by TEXT NOT NULL REFERENCES users(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT uq_dataset_version UNIQUE(dataset_id, version_no)
);
```

**規則**：Version 表 **不可 UPDATE**（append-only）。

### 實驗追蹤表

```sql
CREATE TABLE IF NOT EXISTS public.experiment_runs (
  id TEXT PRIMARY KEY DEFAULT generate_ulid(),
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  dataset_version_id TEXT REFERENCES dataset_versions(id), -- 用了哪版資料
  hyperparameters JSONB DEFAULT '{}',
  metrics JSONB DEFAULT '{}',     -- {accuracy: 0.92, f1: 0.89, rmse: 1.23}
  model_path TEXT,                 -- Storage 中的模型檔案
  status TEXT DEFAULT 'completed'
    CHECK (status IN ('running', 'completed', 'failed')),
  created_by TEXT NOT NULL REFERENCES users(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

---

## 可重現性鏈

```
experiment_run
  → dataset_version_id  → 用了哪版資料（可回溯 storage_path）
  → hyperparameters     → 超參數完整記錄
  → metrics             → 結果指標
  → model_path          → 模型檔案位置
```

**任何實驗結果都能透過這條鏈完整重現。**

---

## 工作流程

```
上傳 CSV / ETL 完成
  → INSERT dataset_versions (version_no + 1, storage_path, checksum)
  → UPDATE datasets.current_version_id = new_version_id

執行實驗
  → INSERT experiment_runs (dataset_version_id = 使用的版本)
  → 訓練完成後 UPDATE metrics + model_path
```

---

## 常見錯誤

| 錯誤 | 後果 | 修正 |
|------|------|------|
| 資料集直接覆蓋 | 無法重現過去的實驗 | 建立新 version |
| 沒有 dataset_version_id | 不知道用了哪版資料 | experiment_run 必須關聯 |
| 模型權重存 DB | DB 膨脹 | 存 Storage，DB 存 path |
| 沒有 checksum | 無法驗證完整性 | 加 SHA-256 |

---

## 從 ch04 升級

如果你的期末專題從 ch04 的 `predictions` 表出發，升級路徑：

1. 建立 `datasets` 表（記錄你的訓練資料 metadata）
2. 建立 `dataset_versions` 表（每次更新資料建新版本）
3. 在 `predictions` / `experiment_runs` 加 `dataset_version_id`
4. 模型檔案存 Storage，DB 存 path

## 參考來源

- `docs/supabase/chapter-04-project-practice.md` — predictions 表（起點）
- `docs/supabase/e-Commerce/README.md` — Stage 6: Snapshot/Ledger 概念
- 設計靈感：MLflow, DVC, W&B 的版本追蹤思路

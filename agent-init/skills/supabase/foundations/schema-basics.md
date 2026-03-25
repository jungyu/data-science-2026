---
name: supabase-schema-basics
description: "Schema 基礎規範：必備欄位、命名慣例、JSONB 使用原則"
triggers:
  - "CREATE TABLE"
  - "schema"
  - "欄位"
  - "JSONB"
  - "表設計"
finish_conditions:
  - "新表包含 id, created_at, updated_at"
  - "JSONB 僅用於非結構化資料"
references:
  - docs/supabase/chapter-03-supabase-hands-on.md
  - docs/supabase/assignments/hw-01-sql-basics.md
  - docs/supabase/assignments/hw-02-jsonb.md
---

# Schema Basics（基礎）

> 一張表的「必備零件」清單。

---

## 快速開始

任何新表都應包含這些基礎欄位：

```sql
CREATE TABLE my_table (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  -- ... 業務欄位 ...
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

---

## 目的 / 能解決什麼問題

確保每張表結構一致、可追蹤、可維護。避免遺漏時間戳、型別不一致等常見問題。

## 何時該用 / 何時不該用

| 該用 | 不該用 |
|------|--------|
| 新增任何表 | 純查詢（不涉及 DDL）|
| 修改表結構 | 讀取/分析資料 |

## Repo Reality

- `docs/supabase/chapter-03-supabase-hands-on.md` — videos 表基礎範例
- `docs/supabase/chapter-04-project-practice.md` — predictions 表範例
- `docs/supabase/assignments/hw-01-sql-basics.md` — 電商四表範例（customers, products, orders, order_items）
- `docs/supabase/assignments/hw-02-jsonb.md` — JSONB 應用範例
- `docs/supabase/labs/lab-02-postgresql-core.md` — videos + channels 表

---

## 核心規則

### 1. 必備欄位

| 欄位 | 型別 | 說明 |
|------|------|------|
| `id` | UUID / TEXT | 主鍵（見 pk-convention.md）|
| `created_at` | `TIMESTAMPTZ NOT NULL DEFAULT NOW()` | 建立時間 |
| `updated_at` | `TIMESTAMPTZ NOT NULL DEFAULT NOW()` | 更新時間 |

**注意**：用 `TIMESTAMPTZ`（有時區），不要用 `TIMESTAMP`（無時區）。

### 2. 命名慣例

| 類型 | 規則 | 範例 |
|------|------|------|
| 表名 | 複數、snake_case | `customers`, `order_items` |
| 欄位名 | 單數、snake_case | `user_id`, `created_at` |
| FK 欄位 | `<被引用表單數>_id` | `customer_id`, `product_id` |
| Index | `idx_<table>_<columns>` | `idx_orders_customer` |
| Constraint | `uq_<table>_<desc>` 或描述性命名 | `uq_products_sku` |

### 3. FK 基礎寫法

```sql
-- hw-01 風格：電商訂單
CREATE TABLE orders (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  customer_id UUID NOT NULL REFERENCES customers(id),
  status TEXT NOT NULL DEFAULT 'pending',
  total_amount NUMERIC(10,2),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

**FK 必須加 index**（提升 JOIN 效能）：

```sql
CREATE INDEX idx_orders_customer ON orders(customer_id);
```

### 4. JSONB 使用原則

來自 hw-02 的核心教學：

**適合放 JSONB**：
- 模型輸入/輸出（`input_data`, `output_data`）
- 設定/偏好（schema 不穩定時）
- 外部 API 回應 payload

**不該放 JSONB**：
- 會被 `WHERE` 過濾的欄位 → 拉出為獨立 column
- 會被 `ORDER BY` 排序的欄位 → 拉出為獨立 column
- 會被 `JOIN` 的欄位 → 必須是獨立 column

```sql
-- ✅ 正確：filterable 欄位獨立，非結構化用 JSONB
CREATE TABLE predictions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID NOT NULL,
  model_name TEXT NOT NULL,      -- 會被 WHERE 過濾 → 獨立欄位
  score NUMERIC,                  -- 會被 ORDER BY → 獨立欄位
  input_data JSONB,              -- 非結構化 → JSONB OK
  output_data JSONB,             -- 非結構化 → JSONB OK
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ❌ 錯誤：把 model_name 塞進 JSONB
-- WHERE metadata->>'model_name' = 'xgboost'  ← 無法用 index，超慢
```

### 5. Status 欄位加 CHECK

```sql
status TEXT NOT NULL DEFAULT 'pending'
  CHECK (status IN ('pending', 'processing', 'completed', 'failed'))
```

避免無效狀態值進入資料庫。

---

## 完整範例：hw-01 風格的電商表

```sql
CREATE TABLE customers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  email TEXT UNIQUE NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE products (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  sku TEXT UNIQUE NOT NULL,
  price NUMERIC(10,2) NOT NULL,
  stock INTEGER NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE orders (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  customer_id UUID NOT NULL REFERENCES customers(id),
  status TEXT NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending', 'confirmed', 'shipped', 'delivered', 'cancelled')),
  total_amount NUMERIC(10,2),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- FK index
CREATE INDEX idx_orders_customer ON orders(customer_id);
```

---

## 常見錯誤與排除

| 錯誤 | 原因 | 解決方式 |
|------|------|---------|
| `TIMESTAMP` 時區混亂 | 用了 `TIMESTAMP` 而非 `TIMESTAMPTZ` | 改用 `TIMESTAMPTZ` |
| FK 欄位沒有 index | JOIN 查詢走 seq scan | 加 `CREATE INDEX` |
| JSONB 欄位被 WHERE 過濾 | 無法走 index | 拉出為獨立 column |
| Status 允許任意值 | 缺少 CHECK constraint | 加 `CHECK (status IN (...))` |

## 進階學習

完成基礎後，進入 `production/schema-design.md` 學習：
- ULID 強制（TEXT PK）
- 資料分層架構（Raw → Staging → Analytics）
- 多租戶模型（project_id scoping）

## 參考來源

- `docs/supabase/chapter-03-supabase-hands-on.md`
- `docs/supabase/assignments/hw-01-sql-basics.md`
- `docs/supabase/assignments/hw-02-jsonb.md`

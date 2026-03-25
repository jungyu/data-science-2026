---
name: supabase-scaling-guidelines-production
description: "生產級規模化指南：瓶頸識別與紅線規範"
triggers:
  - "scaling"
  - "效能瓶頸"
  - "連線池"
  - "規模"
finish_conditions:
  - "無 OFFSET"
  - "RLS 用 helper function"
  - "大表有 partition"
  - "ETL 有分批"
references:
  - docs/supabase/e-Commerce/README.md
  - docs/supabase/crawler/HEAD-FIRST-crawler-db.md
---

# Scaling Guidelines（生產級）

> ⚠️ **前置條件**：已完成 foundations/ + 至少一份進階教材。
> 🏷️ **進階**：適用於期末專題規模化、或資料量開始增長的場景。

## Repo Reality

- `docs/supabase/e-Commerce/README.md` — Stage 8-10: 規模化考量
- `docs/supabase/crawler/HEAD-FIRST-crawler-db.md` — Stage 5: 大表管理

---

## 核心原則

資料庫不會因為「資料太多」而死，而是因為：
- ❌ 被要求做錯誤的事情（OFFSET, SELECT *, JSONB filter）
- ❌ 每個 request 都做過多計算（RLS JOIN, auth.uid() 每列重算）
- ❌ 沒有 lifecycle（資料沒有死亡機制）
- ❌ 鎖定機制破壞可用性（大表 CREATE INDEX 不加 CONCURRENTLY）

---

## 瓶頸層級

### Layer 1: RLS 計算過重

**紅線**：Policy 內 JOIN/EXISTS
**修正**：Helper function + composite index
**信號**：CPU 高、查詢時間隨資料量線性成長

### Layer 2: 連線耗盡

**紅線**：每 request 建立 connection、無 statement_timeout
**修正**：Connection pooler（Supavisor）+ statement_timeout

**連線池設定**（期末專題部署時需要）：

```toml
[db.pooler]
enabled = true
pool_mode = "transaction"
default_pool_size = 50
```

### Layer 3: 大表膨脹

**紅線**：append-heavy 表未 partition、用 Soft Delete
**修正**：`PARTITION BY RANGE (created_at)` + `autovacuum_vacuum_scale_factor = 0.05` + 硬刪除

### Layer 4: Index Bloat & JSONB

**紅線**：JSONB 做列表過濾、超過 5 個複合 index
**修正**：高頻欄位實體化為 column

### Layer 5: 查詢模式

**紅線**：OFFSET、無邊界聚合、單次 INSERT > 10K
**修正**：Cursor pagination + 時間邊界 + Batch chunk

### Layer 6: Migration 鎖表

**紅線**：大表 `CREATE INDEX` 不加 `CONCURRENTLY`、新增欄位帶 DEFAULT
**修正**：`CONCURRENTLY` + 先 NULL 後 backfill

### Layer 7: Realtime 過載

**紅線**：全表 Realtime 訂閱無 filter
**修正**：`filter: project_id=eq.${id}`

---

## Scaling Checklist

所有期末專題 / 進階專案應通過：

```
□ 無 OFFSET pagination
□ RLS 使用 helper function
□ Append 表有 partition 策略
□ 大表 Migration 安全（CONCURRENTLY）
□ JSONB 不做列表過濾
□ ETL 有 batch 截斷
□ 聚合查詢有時間邊界
□ Realtime 訂閱有 scope filter
```

---

## 最終原則

```
DB = source of truth + secure enclave
Storage = 大檔案 + 歷史資料
Workers = ETL + heavy jobs
```

**"不是資料庫慢，是查詢寫錯了。"**

## 參考來源

- `docs/supabase/e-Commerce/README.md` — Stage 8-10
- `docs/supabase/crawler/HEAD-FIRST-crawler-db.md` — Stage 5

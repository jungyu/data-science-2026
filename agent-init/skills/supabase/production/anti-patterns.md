---
name: supabase-anti-patterns-production
description: "生產級反模式清單：Schema/RLS/查詢/Migration 常見災難檢查表"
triggers:
  - "review"
  - "anti-pattern"
  - "反模式"
  - "code review"
finish_conditions:
  - "通過 Review Checklist"
references:
  - docs/supabase/e-Commerce/README.md
  - docs/supabase/crawler/HEAD-FIRST-crawler-db.md
---

# Anti-Patterns（生產級）

> ⚠️ **前置條件**：已完成 foundations/ 層級。

## Repo Reality

- `docs/supabase/crawler/HEAD-FIRST-crawler-db.md` — 29 個違規的完整修正過程
- `docs/supabase/e-Commerce/README.md` — Stage 4, 8, 9 的反模式說明

---

## 🚨 Critical — Schema

| # | 反模式 | 正確做法 | 出處 |
|---|--------|---------|------|
| S1 | BIGSERIAL 做 PK | `TEXT DEFAULT generate_ulid()` | Crawler Stage 1 |
| S2 | FK 型別混用（UUID + TEXT） | 統一 TEXT | Crawler Stage 1 |
| S3 | 缺 created_at / updated_at | 每張表必備 | Crawler Stage 2 |
| S4 | 缺 project_id | 業務表必有 tenant scoping | Crawler Stage 2 |
| S5 | 可篩選欄位放 JSONB | 拉出為獨立 column | e-Commerce Stage 4 |
| S6 | 大檔案塞 DB | Storage 存檔案，DB 存 path | 通用 |

## 🚨 Critical — RLS

| # | 反模式 | 正確做法 | 出處 |
|---|--------|---------|------|
| R1 | Policy 內多層 JOIN | Helper function | e-Commerce Stage 9 |
| R2 | Policy 欄位無 index | 加 composite index | Crawler Stage 4 |
| R3 | 直接用 `auth.uid()` | `(SELECT auth.uid())` 或 helper | e-Commerce Stage 9 |
| R4 | 忘記啟用 RLS | `ALTER TABLE ... ENABLE RLS` | Crawler Stage 4 |
| R5 | 缺 GRANT 語句 | 加 GRANT SELECT/INSERT/UPDATE/DELETE | Crawler Stage 4 |
| R6 | 缺 service_role policy | 加 `FOR ALL TO service_role USING (true)` | Crawler Stage 4 |

## ⚠️ High — 效能

| # | 反模式 | 正確做法 | 出處 |
|---|--------|---------|------|
| P1 | OFFSET 深度分頁 | Cursor pagination（keyset） | 通用 |
| P2 | SELECT * | 明確列出欄位 | 通用 |
| P3 | 缺複合 index | 加 `(project_id, status, created_at DESC)` | Crawler Stage 3 |
| P4 | N+1 查詢 | JOIN 或 batch | 通用 |
| P5 | 無邊界聚合 | 加時間範圍 + project scope | 通用 |
| P6 | ETL 無分批 | Chunk ≤ 10,000 筆 | 通用 |
| P7 | 大表無 partition | Partition by range (created_at) | Crawler Stage 5 |

### P1 詳解：Cursor Pagination

```python
# ❌ OFFSET（大資料量崩潰）
response = supabase.table('articles') \
    .select('id, title') \
    .range(100000, 100050)  # O(n) scan

# ✅ Cursor（keyset）
response = supabase.table('articles') \
    .select('id, title, created_at') \
    .lt('created_at', last_created_at) \
    .order('created_at', desc=True) \
    .limit(50)  # O(1) seek
```

## ⚠️ High — Migration

| # | 反模式 | 正確做法 |
|---|--------|---------|
| M1 | Migration 不含 RLS | 同檔案含 RLS + policies |
| M2 | Migration 不含 index | 同檔案含 index |
| M3 | 非冪等 DDL | `IF NOT EXISTS` |
| M4 | 隱式 constraint | 明確命名 |
| M5 | 大表 index 不加 CONCURRENTLY | 獨立 migration + CONCURRENTLY |
| M6 | 忘記 updated_at trigger | 加 `trg_<table>_updated_at` |

---

## Review Checklist（一分鐘版）

### 新 Migration

```
□ id TEXT PRIMARY KEY DEFAULT generate_ulid()
□ project_id + created_at + updated_at
□ updated_at trigger
□ 所有 FK 有 index
□ RLS enabled + policies + GRANT
□ 所有 DDL 冪等
□ 大表（>10M 列/年）有 partition 計畫
```

### 新查詢

```
□ 無 OFFSET
□ 無 SELECT *
□ 無 N+1
□ 聚合有時間邊界
□ ETL 有分批
```

## 參考來源

- `docs/supabase/crawler/HEAD-FIRST-crawler-db.md` — 29 個違規完整修正
- `docs/supabase/e-Commerce/README.md` — Stage 4, 8, 9 反模式說明

---
name: supabase-guidelines-index
description: "Supabase 與 PostgreSQL 資料科學專案治理規範總覽入口"
triggers:
  - "supabase"
  - "postgres"
  - "schema"
  - "migration"
  - "RLS"
  - "資料庫"
references:
  - docs/supabase/README.md
  - docs/supabase/e-Commerce/README.md
  - docs/supabase/crawler/HEAD-FIRST-crawler-db.md
---

# Supabase / PostgreSQL 資料科學治理系統

本目錄包含資料科學專案的 Supabase 與 PostgreSQL 規範。

## 受眾與分層

本 skill 分為兩層，**對應不同學習階段**：

| 層級 | 對應教材 | 適用時機 |
|------|---------|---------|
| **foundations/** | ch01-05, lab01-05, hw01-04 | 初學 PostgreSQL + Supabase |
| **production/** | e-Commerce Stage 1-10, Crawler HEAD-FIRST | 期末專題、進階架構設計 |

> **規則**：若學生仍在 ch01-05 階段，AI 應參照 `foundations/` 規範。
> 當進入 e-Commerce 或 Crawler 進階教材後，才啟用 `production/` 規範。

---

## 📗 Foundations — 基礎規範

適合正在學習 ch01-05、lab01-05、hw01-04 的學生。

- [PK Convention](./foundations/pk-convention.md) — UUID 入門 → ULID 演進路徑
- [Schema Basics](./foundations/schema-basics.md) — 必備欄位、命名慣例、JSONB 原則
- [RLS Basics](./foundations/rls-basics.md) — `auth.uid()` 基礎模式、Policy 寫法
- [Query Basics](./foundations/query-basics.md) — 明確欄位、禁止 SELECT *、基礎分頁

---

## 📕 Production — 生產級規範

適合進入 e-Commerce / Crawler 進階教材、或設計期末專題的學生。

**前置條件**：已完成 foundations 層級的學習。

### 核心效能與預防性規範
- [Scaling Guidelines](./production/scaling-guidelines.md) — 瓶頸識別與紅線
- [Performance Linter](./production/performance-linter.md) — 效能守門員
- [Query Patterns](./production/query-patterns.md) — Cursor Pagination、Batch ETL、聚合查詢

### 結構與設計指南
- [Schema Design](./production/schema-design.md) — ULID 強制、分層架構、多租戶模型
- [Large Table Management](./production/large-table-management.md) — Partition、Retention、Archival
- [RLS Patterns](./production/rls-patterns.md) — Helper Function 模式、Composite Index
- [Migration Guidelines](./production/migration-guidelines.md) — Migration 撰寫規範
- [Anti Patterns](./production/anti-patterns.md) — 常見反模式檢查表
- [Data Versioning](./production/data-versioning.md) — 資料集版本化與實驗追蹤

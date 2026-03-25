# RAG Schema Audit Report

> 依據 `agent-init/skills/supabase/*.md` 全面審查 v2.1 schema，產出違規清單與修正計畫。

---

## 審查依據

| Skill 文件 | 審查範圍 |
|-----------|---------|
| `pk-convention.md` | PK/FK 型別、ULID 慣例 |
| `schema-design.md` | 分層架構、必備欄位、JSONB 使用 |
| `rls-patterns.md` | Helper function、auth.uid() 優化、GRANT |
| `performance-linter.md` | 查詢效能、RLS 效能、migration safety |
| `anti-patterns.md` | 完整反模式清單 |
| `migration-guidelines.md` | 冪等性、必備元素、命名慣例 |
| `query-patterns.md` | 查詢模式合規 |
| `large-table-management.md` | Partition、retention、lifecycle |
| `scaling-guidelines.md` | 紅線規範 |
| `data-versioning.md` | 版本化架構 |

---

## 違規摘要

### 🚨 Critical — 必須修正

| # | 違規 | 規則來源 | v2.1 狀態 | v3.0 修正 |
|---|------|---------|----------|----------|
| C1 | PK 使用 `bigserial` 而非 `TEXT + generate_ulid()` | pk-convention U2 | 全部 7 張表 | 改為 TEXT + ULID |
| C2 | FK 使用 `bigint` 而非 `TEXT` | pk-convention U1 | 全部 FK 欄位 | 改為 TEXT |
| C3 | `owner_id UUID` 直接引用 `auth.users(id)` | pk-convention §5 | collections, documents, chunks | 改為教學簡化版 auth bridge |
| C4 | 無 `GRANT` 語句 | migration-guidelines §2, anti-patterns M7 | 完全缺失 | 加入所有表的 GRANT |
| C5 | 無 `service_role` policy | rls-patterns §6, migration-guidelines §2 | 完全缺失 | ETL pipeline 需要 service_role |
| C6 | `auth.uid()` 未包裝為 `(SELECT auth.uid())` | rls-patterns §4, scaling-guidelines L1 | helper function 內部 | 全面改為 `(SELECT auth.uid())` |

### ⚠️ High — 應修正

| # | 違規 | 規則來源 | v2.1 狀態 | v3.0 修正 |
|---|------|---------|----------|----------|
| H1 | 部分表缺 `updated_at` trigger | anti-patterns M6 | chunks, query_log_results | 補上 trigger |
| H2 | DDL 非冪等（無 `IF NOT EXISTS`） | migration-guidelines §5 | 大部分 CREATE TABLE | 加入 IF NOT EXISTS |
| H3 | 缺 `created_by` 欄位 | schema-design §3 | documents, query_logs | 加入 created_by |
| H4 | Index 未用 `IF NOT EXISTS` | migration-guidelines §5 | 全部 index | 加入 IF NOT EXISTS |
| H5 | Constraint 未明確命名 | anti-patterns M4 | 部分 constraint | 補上命名 |

### ℹ️ Medium — 紀錄為未來升級

| # | 項目 | 規則來源 | 說明 |
|---|------|---------|------|
| M1 | 無 `project_id` 多租戶 scoping | schema-design §2 | RAG 用 `collection_id` 作為等價的 scope 單位 |
| M2 | `query_logs` append-heavy 未規劃 partition | large-table-management | 10K+ 查詢後應考慮 partition |
| M3 | 無 document versioning | data-versioning | 文件更新時無法回溯歷史版本 |
| M4 | 無資料分層前綴 | schema-design §5 | RAG 表可考慮 `rag_` 前綴 |

---

## 關於 project_id vs collection_id 的設計決策

Skill 規範要求所有業務表有 `project_id` 做 tenant scoping。在 RAG 場景中：

```
標準 data-science 專案         RAG 專案
─────────────────────         ────────
projects                      collections
project_members               （owner_id 簡化版）
project_id 欄位               collection_id 欄位
```

RAG schema 的 `collection_id` 在功能上等同 `project_id`：
- 每個 collection 是獨立的知識庫（= 一個 project）
- RLS 按 collection 隔離
- 查詢必須 scope 到 collection

本次修正保留 `collection_id` 作為 RAG 的 tenant scope 欄位，不強制加入 `project_id`（避免與完整 data-science 平台耦合）。未來若整合到多租戶平台，可在 collections 表加入 `project_id` 外鍵。

---

## 關於 auth bridge 的簡化處理

Skill 規範要求業務表不直接引用 `auth.users(id)`，應透過 `users` bridge 表 + `get_current_user_id()` 函式。

在 RAG 教學 schema 中，我們做最小可行的合規：
- 加入 `generate_ulid()` 函式
- PK/FK 全面改為 TEXT + ULID
- `owner_id` 改為 TEXT 型別，不直接 FK 到 `auth.users`
- 提供 `get_current_owner_id()` helper（教學用簡化版，直接用 `auth.uid()::text`）
- 完整 bridge 架構留給 production 升級

---

*審查日期：2026-03-25*

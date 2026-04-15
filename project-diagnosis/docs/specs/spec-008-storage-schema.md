# Spec-008: 儲存 Schema

- Status: Draft
- Owner: DBA
- Last Updated: 2026-04-15

## 1. 目的

定義 PostgreSQL + pgvector 資料層，實現 [Spec-004](./spec-004-knowledge-atom-schema.md) / [Spec-005](./spec-005-rule-engine.md) / [Spec-006](./spec-006-retrieval-pipeline.md) / [Spec-007](./spec-007-generation-orchestrator.md) 所需的儲存、索引、觸發器。

權威檔案：[sql/tcm-rag.schema.sql](../../sql/tcm-rag.schema.sql)。本 spec 為設計敘述。

## 2. 執行環境

* PostgreSQL 15+
* 擴充：`vector`、`pg_trgm`、`unaccent`
* 部署目標：Supabase 或自管 PostgreSQL

## 3. 資料表

| 資料表 | 責任 | 估計列數（MVP） |
| --- | --- | --- |
| `source_documents` | 原始文件 | 10² |
| `knowledge_atoms` | 知識原子主表 | 10³ |
| `atom_relations` | 原子間邊 | 10⁴ |
| `diagnostic_rules` | 辨證規則 | 10² |
| `query_logs` | 查詢日誌 | 10⁴+ |
| `retrieval_logs` | 檢索與重排日誌 | 10⁵+ |

## 4. 索引策略

### 4.1 `knowledge_atoms`

| 索引 | 類型 | 用途 |
| --- | --- | --- |
| `idx_knowledge_atoms_atom_type` | btree | 類型過濾 |
| `idx_knowledge_atoms_canonical_name` | btree | 字典比對 |
| `idx_knowledge_atoms_domain` / `_category` | btree | metadata 過濾 |
| `idx_knowledge_atoms_metadata_gin` | gin | JSONB 查詢 |
| `idx_knowledge_atoms_aliases_gin` | gin | 異名比對 |
| `idx_knowledge_atoms_search_vector` | gin | FTS |
| `idx_knowledge_atoms_embedding_ivfflat` | ivfflat(vector_cosine_ops) | 向量檢索 |

**ivfflat 調優**：`lists = sqrt(row_count)`，MVP 設 100，超過 10⁴ 筆後重建。
升級到 HNSW 為 Phase 2 備選。

### 4.2 `atom_relations`

| 索引 | 用途 |
| --- | --- |
| `(from_atom_id, relation_type)` | 出邊查詢 |
| `(to_atom_id, relation_type)` | 入邊查詢 |
| unique `(from_atom_id, relation_type, to_atom_id)` | 防重複邊 |

## 5. 觸發器

| 觸發器 | 對象 | 行為 |
| --- | --- | --- |
| `trg_*_updated_at` | 所有主表 | 自動更新 `updated_at` |
| `trg_knowledge_atoms_search_vector` | `knowledge_atoms` | title / canonical_name / summary / body 任一變動時重建 `search_vector` |

## 6. Check Constraints

* `atom_type`、`relation_type`、`ingestion_status`、`rule_scope`、`rule_status`、`retrieval_logs.stage` 均以 CHECK 約束 enum 值
* `weight` ∈ `[0, 1]`；`authority_level`、`quality_score`、`completeness_score` ∈ `[0, 100]`
* `chk_atom_relations_not_self_loop`：禁止自環

## 7. Views

| View | 用途 |
| --- | --- |
| `v_pattern_atoms` | 僅 active pattern 的 Top-K 候選來源 |
| `v_symptom_to_pattern_edges` | 症狀 → 證型正向邊快速視圖 |

## 8. 未來擴充

* `pattern_atoms` 加入 partial unique index on `canonical_name where atom_type='pattern'`，強化 [Spec-004 §6](./spec-004-knowledge-atom-schema.md) 驗收
* `case_records` 表分離醫案（Phase 3）
* 讀寫分離：`query_logs` / `retrieval_logs` 轉 partitioning（> 10⁶ 列）

## 9. 資料治理

* 禁止 `DELETE`：改用 `is_active = false`
* `source_documents.raw_content` 儘量保留，避免重抓
* `ingestion_status` 只可單向推進：`pending → cleaned → parsed → embedded → failed`

## 10. 驗收要求

* `psql -f sql/tcm-rag.schema.sql` 在乾淨資料庫下可一次執行成功
* `psql -f sql/tcm-rag.seed.sql` 可在 schema 上成功載入 seed 且 idempotent
* pgvector + FTS 索引建立後，[rank_patterns.sql](../../sql/rank_patterns.sql) 在 seed 資料下 < 100ms

## 11. 依賴 ADR

* [ADR-001](../adr/ADR-001-tcm-rag-architecture.md) §Decision §2（統一 PostgreSQL）

# Spec-008: 儲存層與資料表

- Status: Draft
- Owner: Backend Engineer / Data Engineer
- Last Updated: 2026-04-14

## 1. 目的

定義系統的主要資料實體與資料表，以 PostgreSQL + pgvector 為主體。

## 2. 主要資料實體

| 資料表 | 說明 |
|--------|------|
| `bazi.knowledge_atoms` | 核心知識原子 |
| `bazi.knowledge_relations` | 原子間關係（輕量圖譜） |
| `bazi.rule_definitions` | 規則引擎定義 |
| `bazi.bazi_charts` | 排盤記錄 |
| `bazi.retrieval_logs` | 檢索過程記錄 |
| `bazi.generation_logs` | 生成過程記錄 |
| `bazi.evaluation_cases` | 黃金評估案例 |

## 3. 資料表設計

完整 DDL 請見 `migrations/001_initial_schema.sql`。

### bazi.knowledge_atoms
| 欄位 | 型別 | 說明 |
|------|------|------|
| id | bigserial PK | |
| atom_code | text UNIQUE | 全域唯一識別碼 |
| source_book | text | 來源著作 |
| source_priority | smallint | 1=最高權威 |
| chapter / section / title | text | 來源定位 |
| original_text | text | 古文原文 |
| modern_interpretation | text | 現代語意 |
| embedding_text | text | 向量化文本 |
| normalized_tags | jsonb | 標準化標籤陣列 |
| logic_type | jsonb | 邏輯類型陣列 |
| conditions | jsonb | 結構化條件陣列 |
| day_master_tags | text[] | 高頻過濾欄 |
| month_branch_tags | text[] | 高頻過濾欄 |
| pattern_tags | text[] | 高頻過濾欄 |
| seasonal_tags | text[] | 高頻過濾欄 |
| embedding | vector(1536) | pgvector 向量 |
| status | text | active/draft/deprecated |

### bazi.knowledge_relations
| 欄位 | 型別 | 說明 |
|------|------|------|
| from_atom_id | bigint FK | |
| relation_type | text | supports/contradicts/extends/cites |
| to_atom_id | bigint FK | |
| weight | numeric(6,4) | 關係強度 |

### bazi.rule_definitions
| 欄位 | 型別 | 說明 |
|------|------|------|
| rule_code | text | 規則識別碼 |
| version | integer | 版本號 |
| rule_type | text | strength/pattern/seasonal/conflict |
| conditions | jsonb | 觸發條件 |
| outputs | jsonb | 輸出結果 |
| priority | integer | 執行優先序 |

### bazi.retrieval_logs
| 欄位 | 型別 | 說明 |
|------|------|------|
| retrieval_code | text UNIQUE | |
| chart_id | bigint FK | |
| retrieval_input | jsonb | 查詢輸入 |
| symbolic_candidates | jsonb | Symbolic 路由結果 |
| metadata_candidates | jsonb | Metadata 路由結果 |
| vector_candidates | jsonb | Vector 路由結果 |
| fused_results | jsonb | 融合排序後結果 |

### bazi.evaluation_cases
| 欄位 | 型別 | 說明 |
|------|------|------|
| case_code | text UNIQUE | |
| input_payload | jsonb | 輸入出生資料 |
| expected_chart | jsonb | 期望命盤 |
| expected_features | jsonb | 期望規則輸出 |
| expected_atom_codes | jsonb | 期望命中 atom |
| expected_source_books | jsonb | 期望命中著作 |

## 4. 索引策略

### B-tree / Array GIN
```sql
-- 來源與狀態
CREATE INDEX ON bazi.knowledge_atoms (source_priority, source_book);
CREATE INDEX ON bazi.knowledge_atoms (status);

-- 高頻過濾欄 GIN
CREATE INDEX ON bazi.knowledge_atoms USING gin (day_master_tags);
CREATE INDEX ON bazi.knowledge_atoms USING gin (month_branch_tags);
CREATE INDEX ON bazi.knowledge_atoms USING gin (pattern_tags);

-- JSONB GIN
CREATE INDEX ON bazi.knowledge_atoms USING gin (normalized_tags);
CREATE INDEX ON bazi.knowledge_atoms USING gin (logic_type);
CREATE INDEX ON bazi.knowledge_atoms USING gin (conditions);
```

### pgvector HNSW
```sql
CREATE INDEX ON bazi.knowledge_atoms
  USING hnsw (embedding vector_cosine_ops);
```

## 5. 設計原則

- JSON 欄位保留彈性，高頻查詢欄位做 native column
- log 與核心資料分離
- embedding 維度固定為 1536（更換模型需 migration）

## 6. 依賴 ADR

- ADR-007：儲存架構決策

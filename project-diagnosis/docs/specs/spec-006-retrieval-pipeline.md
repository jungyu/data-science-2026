# Spec-006: 檢索管線

- Status: Draft
- Owner: RAG Engineer
- Last Updated: 2026-04-15

## 1. 目的

由 [Spec-002](./spec-002-feature-extractor.md) 輸出的結構化特徵，以三路混合檢索產生候選證型清單並重排。

## 2. 責任

* 執行 FTS、向量、關係展開三路召回
* 合併去重
* 依加權公式重排
* 輸出 Top-K 候選與證據原子 id

## 3. 非責任

* 規則評分（屬 Spec-005）
* 敘事生成（屬 Spec-007）

## 4. 三路召回

### 4.1 FTS（精確術語）

```sql
SELECT id, ts_rank_cd(search_vector, plainto_tsquery('simple', :q)) AS score
FROM knowledge_atoms
WHERE is_active = true
  AND atom_type = 'pattern'
  AND search_vector @@ plainto_tsquery('simple', :q)
ORDER BY score DESC
LIMIT :k
```

### 4.2 Vector（語義近似）

```sql
SELECT id, 1.0 - (embedding <=> :query_embedding) AS score
FROM knowledge_atoms
WHERE is_active = true
  AND atom_type = 'pattern'
  AND embedding IS NOT NULL
ORDER BY score DESC
LIMIT :k
```

### 4.3 Relation Expansion（結構展開）

由特徵原子沿以下關係走：

| 起點 atom_type | 關係 | 目標 atom_type |
| --- | --- | --- |
| symptom / tongue / pulse | `suggests` / `strengthens` / `strongly_strengthens` | pattern |
| symptom / tongue / pulse | `conflicts_with` | pattern（產生 penalty，不算 support） |

實作：[sql/rank_patterns.sql](../../sql/rank_patterns.sql)。

## 5. 重排公式

| 項 | 權重 | 說明 |
| --- | --- | --- |
| `support_score` | 0.55 | Σ(edge.weight × relation_multiplier) |
| `conflict_penalty` | -0.20 | Σ(conflicts_with.weight) |
| `vector_score` | 0.15 | normalized cosine similarity |
| `fts_score` | 0.10 | normalized `ts_rank_cd` |

**Relation multipliers**：

| relation_type | multiplier |
| --- | --- |
| `suggests` | 0.60 |
| `strengthens` | 0.80 |
| `strongly_strengthens` | 1.00 |
| `explained_by` | 0.50 |
| `supports` | 0.70 |
| `related_to` | 0.30 |

`vector_score` 與 `fts_score` 均在候選集合內做 min-max 正規化至 `[0,1]`，避免絕對量級傾斜公式。

## 6. 輸入契約

```json
{
  "feature_atom_ids": ["atm_symptom_dao_han", "atm_tongue_red_scanty_coat"],
  "query_embedding": [0.012, -0.034, ...],
  "query_fts": "午後潮熱 盜汗 舌紅少苔",
  "top_k": 5
}
```

`query_embedding` / `query_fts` 可為 null，對應權重自動為 0。

## 7. 輸出契約

```json
[
  {
    "pattern_id": "atm_pattern_yin_deficiency_heat",
    "pattern_name": "陰虛內熱",
    "pattern_family": "陰虛",
    "final_score": 0.812,
    "support_score": 1.2,
    "conflict_penalty": 0.0,
    "vector_score": 0.91,
    "fts_score": 0.77,
    "supporting_feature_ids": ["atm_symptom_dao_han", "atm_tongue_red_scanty_coat"],
    "conflicting_feature_ids": []
  }
]
```

## 8. 性能要求

* 單次查詢 < 200ms @ seed 資料量
* `knowledge_atoms.embedding` 採 `ivfflat(vector_cosine_ops)`，`lists` 依資料量調整
* FTS 採 GIN index on `search_vector`

## 9. 查詢型態路由（未來）

| 型態 | 建議路徑 |
| --- | --- |
| 症狀敘述 | 三路全開 |
| 術語查詢 | FTS 主導，向量補 |
| 鑑別診斷 | 關係展開主導 |
| 經典佐證 | FTS + authority_level 排序 |

MVP 不做路由，統一三路全開。

## 10. 驗收要求

* Case 1 在 seed 下首位候選為「陰虛內熱」
* Case 2 首位候選為「衛氣不固」
* Case 2「陰虛內熱」名次 ≥ 3（因舌淡 conflict）

## 11. 依賴 ADR

* [ADR-001](../adr/ADR-001-tcm-rag-architecture.md) §Decision §2 / §3

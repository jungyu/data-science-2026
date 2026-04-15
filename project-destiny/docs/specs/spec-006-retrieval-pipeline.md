# Spec-006: 檢索管線

- Status: Draft
- Owner: NLP Engineer / Backend Engineer
- Last Updated: 2026-04-14

## 1. 目的

定義 Retrieval Orchestrator 的輸入、路由策略、排序融合與輸出格式。

## 2. 輸入

- 命盤結構（來自 Bazi Engine）
- Rule Engine output（特徵 + query seeds）
- 使用者查詢上下文（可選）
- 檢索設定（top_k、source_scope、priority_filter）

## 3. 檢索路徑

### Route A: Symbolic Retrieval
依格局候選、條件、特殊關係，直接查對應規則與 atom。
主要使用 `conditions` 欄位做 structured match。

### Route B: Metadata Retrieval
依 `normalized_tags` 查詢候選 atom。
使用 PostgreSQL array / jsonb GIN index 過濾。

### Route C: Vector Retrieval
依 `retrieval_query_seeds` 生成 query embedding，
在候選池中做 pgvector cosine similarity 召回。

### Route D: Graph Retrieval（第二階段）
依關係邊展開近鄰節點與相關 atom。
使用 `knowledge_relations` 表做關係擴展。

## 4. 融合策略

最終分數由以下因子加權組成：

| 因子 | 預設權重 |
|------|---------|
| vector_similarity_score | 0.45 |
| source_priority_score | 0.20 |
| symbolic_match_score | 0.20 |
| metadata_overlap_score | 0.15 |

權重可依實驗結果調整，需記錄版本。

## 5. 輸出

```json
{
  "retrieval_id": "ret_001",
  "chart_id": "chart_xxx",
  "results": [
    {
      "atom_id": 1,
      "atom_code": "ziping-jia-001",
      "source_book": "子平真詮",
      "title": "甲木冬生調候",
      "original_text": "甲木參天，脫胎要火。",
      "modern_interpretation": "甲木若生寒冷季節，需火暖局。",
      "final_score": 0.94,
      "vector_score": 0.91,
      "source_priority_score": 1.00,
      "symbolic_match_score": 1.00,
      "metadata_overlap_score": 0.85,
      "route_hits": ["symbolic", "metadata", "vector"],
      "reason_codes": [
        "candidate_pattern_match",
        "high_priority_source",
        "day_master_tag_match"
      ]
    }
  ]
}
```

## 6. 排序原則

- 核心規則命中優先（symbolic match）
- 高權重文獻優先（source_priority）
- 多路同時命中的 atom 優先
- 描述性補充結果不得壓過骨架性結果

## 7. 驗收標準

- Top-K 應合理命中核心骨架文獻
- 多路檢索結果需可記錄與重現
- 排序結果需具 explainability（reason_codes）
- Retrieval log 需完整寫入 DB

## 8. 依賴 ADR

- ADR-001：混合式檢索策略
- ADR-002：文獻優先層級
- ADR-007：儲存架構

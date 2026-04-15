# Spec-002: 診斷特徵抽取器

- Status: Draft
- Owner: RAG Engineer
- Last Updated: 2026-04-15

## 1. 目的

把使用者自然語言敘述，轉為結構化、可被 [Spec-005](./spec-005-rule-engine.md) / [Spec-006](./spec-006-retrieval-pipeline.md) 直接消費的診斷特徵清單，並偵測關鍵缺失類別以觸發補問規則。

## 2. 責任

* 最長匹配字典比對，抽出 `symptom` / `sign` / `tongue_feature` / `pulse_feature` 原子命中
* 偵測時序詞（午後、夜間、經前⋯）與部位詞（脅、脘、腰⋯）
* 標示 `missing` 類別（tongue_feature / pulse_feature / time_feature）
* 保留原始輸入，供 [Spec-007](./spec-007-generation-orchestrator.md) 的症狀摘要段使用

## 3. 非責任

* 臨床補問決策（屬 Spec-005）
* 證型候選排序（屬 Spec-006）
* 改寫或修飾使用者輸入

## 4. 輸入契約

```json
{
  "query": "最近下午容易潮熱，晚上盜汗，口乾，舌紅少苔"
}
```

## 5. 輸出契約

```json
{
  "raw_query": "最近下午容易潮熱，晚上盜汗，口乾，舌紅少苔",
  "symptoms": [
    {"atom_id": "atm_symptom_chao_re", "canonical_name": "潮熱", "matched_surface": "潮熱", "match_type": "canonical"},
    {"atom_id": "atm_symptom_dao_han", "canonical_name": "盜汗", "matched_surface": "盜汗", "match_type": "canonical"}
  ],
  "signs": [],
  "tongue_features": [
    {"atom_id": "atm_tongue_red_scanty_coat", "canonical_name": "舌紅少苔", "matched_surface": "舌紅少苔", "match_type": "canonical"}
  ],
  "pulse_features": [],
  "time_features": ["午後", "夜間"],
  "location_hints": [],
  "missing": ["pulse_feature"]
}
```

## 6. 抽取規則

### 6.1 字典載入

* 來源：`knowledge_atoms` 中 `is_active = true` 且 `atom_type ∈ {symptom, sign, tongue_feature, pulse_feature}` 的 `canonical_name` + `aliases`
* 同一 surface form 對應多 atom 時，優先 `canonical_name`

### 6.2 最長匹配

* 所有 surface form 依長度降冪排序
* 避免「自汗」被短 token「汗」遮蔽
* 同一 atom_id 命中多次只保留首次

### 6.3 時序 / 部位 Lexicon

內建輕量清單（見 `scripts/extract_features.ts` `TIME_LEXICON` / `LOCATION_LEXICON`）。擴充需同步更新 Spec 與實作。

### 6.4 缺失偵測

| 類別 | 條件 |
| --- | --- |
| `tongue_feature` | 輸出中無 tongue 命中 |
| `pulse_feature` | 輸出中無 pulse 命中 |
| `time_feature` | 輸出中無時序詞命中 |

此清單會被傳入 [Spec-005](./spec-005-rule-engine.md) 的 `missing` 條件比對。

## 7. 實作

* TypeScript：`scripts/extract_features.ts`（供 Node / API）
* Python：`scripts/answer_query.py` 內的 `extract_features()`（供後端 pipeline）

兩實作需輸出等價結果；由 [Spec-009](./spec-009-evaluation-framework.md) Layer A 確保。

## 8. 驗收要求

* 給定 [docs/examples/sample-queries.md](../examples/sample-queries.md) 的 5 個案例，特徵抽取與 `missing` 偵測 100% 符合 expect 區塊
* 字典載入 < 100ms（seed 資料量）
* 單次抽取 < 20ms

## 9. 依賴 ADR

* [ADR-001](../adr/ADR-001-tcm-rag-architecture.md) §Decision §1（原子作為最小可索引單位）

# Spec-005: 辨證規則引擎

- Status: Draft
- Owner: Rule Author
- Last Updated: 2026-04-15

## 1. 目的

在 [Spec-006](./spec-006-retrieval-pipeline.md) 產出的候選證型上，套用可審核、可熱更新的規則，產生：

1. 分數調整（boost / penalty）
2. 歧義旗標（ambiguity flag）
3. 補問建議（question suggestion）

## 2. 責任

* 讀 `diagnostic_rules` 中 `status='active'` 的規則
* 依 `priority` 升冪執行
* 對 matched 規則觸發對應 action
* 不得直接刪除候選；只能調分或標記

## 3. 非責任

* 決定 top-K（屬 Spec-006）
* 產生最終敘事（屬 Spec-007）

## 4. 規則結構

### 4.1 Conditions

| 鍵 | 意義 |
| --- | --- |
| `all_of` | 陣列中每條 clause 都必須命中 |
| `any_of` | 陣列中至少一條 clause 命中 |
| `none_of` | 陣列中任一條命中則整體失敗 |
| `missing` | 傳入的 missing 類別必須**全部**出現（用於補問規則） |
| `any_candidate_patterns` | 候選清單中至少包含一個指定 pattern |

Clause 統一格式：`{"type": "<atom_type>", "value": "<canonical_name>"}`。

### 4.2 Actions

| action | 欄位 | 效果 |
| --- | --- | --- |
| `boost_pattern` | `pattern_id`, `boost` | `candidate.final_score += boost` |
| `flag_ambiguous` | `message`, `suggest_question?` | 回傳歧義訊息 |
| `suggest_question` | `message` | 回傳補問建議 |

### 4.3 Scope 與優先序

| rule_scope | 優先序建議區間 |
| --- | --- |
| `pattern_ranking` | 10–30 |
| `differential_diagnosis` | 20–40 |
| `contraindication` | 5–15（越早越好） |
| `question_suggestion` | 50–100 |

## 5. 範例

### 5.1 核心三症 boost

```json
{
  "rule_code": "TCM-RULE-001",
  "rule_scope": "pattern_ranking",
  "priority": 10,
  "conditions": {
    "all_of": [{"type": "symptom", "value": "盜汗"}],
    "any_of": [
      {"type": "symptom", "value": "潮熱"},
      {"type": "tongue_feature", "value": "舌紅少苔"}
    ]
  },
  "actions": {
    "action": "boost_pattern",
    "pattern_id": "atm_pattern_yin_deficiency_heat",
    "boost": 0.40
  }
}
```

### 5.2 矛盾偵測

```json
{
  "rule_code": "TCM-RULE-003",
  "rule_scope": "differential_diagnosis",
  "priority": 20,
  "conditions": {
    "all_of": [
      {"type": "symptom", "value": "盜汗"},
      {"type": "symptom", "value": "自汗"}
    ]
  },
  "actions": {
    "action": "flag_ambiguous",
    "message": "同時出現盜汗與自汗，需確認是否為氣陰兩虛",
    "suggest_question": "自汗與盜汗哪個較明顯？是否有五心煩熱？"
  }
}
```

## 6. 執行契約

### 6.1 輸入

```json
{
  "features": [{"atom_id": "...", "atom_type": "symptom", "canonical_name": "盜汗"}, ...],
  "candidates": [{"pattern_id": "...", "pattern_name": "陰虛內熱", "final_score": 0.72, ...}, ...],
  "missing_categories": ["pulse_feature"]
}
```

### 6.2 輸出

```json
{
  "adjusted_candidates": [/* 重新排序後的候選 */],
  "outcomes": [
    {"rule_code": "TCM-RULE-001", "matched": true, "score_delta": 0.40, "affected_pattern_id": "..."},
    {"rule_code": "TCM-RULE-003", "matched": false}
  ],
  "suggested_questions": ["脈象是細、數、虛、弦？"],
  "ambiguity_flags": []
}
```

## 7. 實作

* `scripts/apply_rules.py`（純函數，無 I/O）
* DB 讀取：`load_active_rules(conn)`

## 8. 演進路徑

* MVP：JSONB + Python evaluator
* Phase 2：規則數 > 50 時評估 DSL（見 [ADR-001](../adr/ADR-001-tcm-rag-architecture.md)）
* Phase 3：允許規則帶 query_embedding 條件（視效能）

## 9. 驗收要求

* [docs/examples/sample-queries.md](../examples/sample-queries.md) Case 1~3 對應的規則必須觸發
* 規則 matched 統計寫入 `retrieval_logs.stage='rule'`
* 規則變更後不需重建 index 或重啟服務

## 10. 依賴 ADR

* [ADR-001](../adr/ADR-001-tcm-rag-architecture.md) §Decision §4（JSONB rules, 非 DSL）

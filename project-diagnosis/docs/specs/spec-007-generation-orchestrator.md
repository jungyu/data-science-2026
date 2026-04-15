# Spec-007: 生成協調器

- Status: Draft
- Owner: RAG Engineer
- Last Updated: 2026-04-15

## 1. 目的

把 [Spec-005](./spec-005-rule-engine.md) 輸出的調整後候選、[Spec-006](./spec-006-retrieval-pipeline.md) 的證據 id、[Spec-002](./spec-002-feature-extractor.md) 的特徵，組裝成**兩階段**回答：

- **Stage 1**：確定性 Answer Contract（純程式）
- **Stage 2**：受限 LLM 敘事（可關閉）

## 2. 責任

* 組裝 Answer Contract JSON 結構（A~G 七段）
* 解析 feature_id → canonical_name
* 呼叫 LLM 產 Markdown 敘事，並以 prompt 限制其引用
* 將完整結果寫入 `query_logs.answer_contract`

## 3. 非責任

* 額外檢索（屬 Spec-006）
* 規則再評估（屬 Spec-005）

## 4. Stage 1：Answer Contract

### 4.1 結構（七段）

| 段 | 內容 |
| --- | --- |
| A | 症狀摘要（重構輸入 + 結構化特徵） |
| B | 候選證型（Top 3） |
| C | 支持證據（每候選逐項） |
| D | 鑑別重點（首位 vs 次位） |
| E | 尚缺資訊（missing 類別） |
| F | 治法方向（僅方向，無處方） |
| G | 引用來源 |

### 4.2 額外欄位

| 欄位 | 來源 |
| --- | --- |
| `rule_flags` | Spec-005 `ambiguity_flags` |
| `suggested_questions` | Spec-005 `suggested_questions` |
| `safety_note` | 固定字串 |
| `H_synthesized_markdown` | Stage 2 輸出（可缺） |

### 4.3 範例

見 [docs/examples/sample-queries.md](../examples/sample-queries.md) Case 1。

## 5. Stage 2：受限敘事

### 5.1 模型設定

| 參數 | 預設 |
| --- | --- |
| Model | `claude-sonnet-4-5`（可透過 `ANTHROPIC_MODEL` 覆寫） |
| `temperature` | 0.2 |
| `max_tokens` | 1500 |

### 5.2 Prompt

見 [scripts/prompts/synthesize_answer.txt](../../scripts/prompts/synthesize_answer.txt)。關鍵規則：

1. 只能使用 Answer Contract 中列出的事實
2. 禁止具體處方與劑量
3. 禁止絕對語氣（「確診」「必然」）
4. `ambiguity_flags` / `suggested_questions` 必須呈現
5. 候選為空時須誠實告知證據不足
6. 引用必對應 `G_citations`

### 5.3 降級策略

| 情境 | 行為 |
| --- | --- |
| 未設 `ANTHROPIC_API_KEY` | 跳過 Stage 2，僅輸出 JSON |
| `anthropic` 套件未裝 | 同上 |
| API 呼叫失敗 | log warning，不 raise |

## 6. 輸入契約

```json
{
  "raw_query": "...",
  "features": [...],
  "missing": [...],
  "candidates": [...],
  "ambiguity_flags": [...],
  "suggested_questions": [...]
}
```

## 7. 輸出契約

```json
{
  "A_symptom_summary": {...},
  "B_candidate_patterns": [...],
  "C_supporting_evidence": [...],
  "D_differential": {"first": "...", "second": "...", "score_gap": 0.12},
  "E_missing": ["pulse_feature"],
  "F_treatment_direction": "...",
  "G_citations": [...],
  "rule_flags": [],
  "suggested_questions": [...],
  "safety_note": "...",
  "H_synthesized_markdown": "## A. 症狀摘要 ..."
}
```

## 8. 實作

* Stage 1：`scripts/answer_query.py` 的 `assemble_answer()`
* Stage 2：`scripts/synthesize_answer.py` 的 `synthesize()`

## 9. 驗收要求

* Stage 1 對同一輸入輸出**完全一致**（hash 可驗）
* Stage 2 輸出不得引入 `features` / `candidates` / `citations` 外的名詞
* Stage 2 輸出不得含具體方劑名稱（除非 `candidates[i].metadata.formula_hint` 有列）
* 兩階段耦合解開：Stage 2 關閉時 Stage 1 輸出完整可用

## 10. 依賴 ADR

* [ADR-001](../adr/ADR-001-tcm-rag-architecture.md) §Decision §5（兩階段生成）

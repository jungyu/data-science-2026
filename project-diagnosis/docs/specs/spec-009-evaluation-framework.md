# Spec-009: 評估框架

- Status: Draft
- Owner: QA Engineer
- Last Updated: 2026-04-15

## 1. 目的

以四層評估覆蓋端到端 pipeline，建立可回放、可比較的基準。

## 2. 四層評估

| 層 | 目標 | 對應 Spec | 主要指標 |
| -- | ---- | --------- | -------- |
| A | 特徵抽取正確率 | Spec-002 | symptom / tongue / pulse precision & recall，missing 偵測準確率 |
| B | 規則觸發一致性 | Spec-005 | rule match precision, 分數調整合理性 |
| C | 檢索品質 | Spec-006 | Top-1 / Top-3 accuracy, MRR, conflict penalty 有效性 |
| D | 生成品質 | Spec-007 | faithfulness, answer relevancy, 幻覺率 |

## 3. 案例集（Golden Set）

### 3.1 MVP

[tests/cases.yaml](../../tests/cases.yaml)：3 個案例（陰虛內熱、衛氣不固、氣陰矛盾）。

### 3.2 Phase 2 擴充目標

| 類型 | 數量目標 |
| --- | --- |
| 單一典型證型 | 10 |
| 鑑別診斷（兩候選相近） | 5 |
| 矛盾訊號 | 3 |
| 資訊不足需補問 | 3 |
| 非中醫輸入（邊界測試） | 2 |

每個案例必須標註：`expected_top_pattern`、`acceptable_alternatives`、`must_trigger_rules`、`must_flag_missing`。

## 4. Layer A / B / C：斷言式（已實作）

實作：[scripts/eval_queries.py](../../scripts/eval_queries.py)
規格：[tests/cases.yaml](../../tests/cases.yaml)

支援斷言：

| 斷言鍵 | 對應層 |
| --- | --- |
| `extracted_symptoms_any_of` / `extracted_tongue_includes` | A |
| `missing_includes` | A |
| `rule_codes_triggered_any_of` | B |
| `has_ambiguity_flag` / `has_suggested_question` | B |
| `top_pattern` / `top3_includes_any_of` / `yin_heat_rank_min` | C |

退出碼：0（全過）/ 1（有失敗）/ 2（環境錯誤）。

## 5. Layer D：LLM 生成品質（待實作）

### 5.1 建議用 Ragas

| 指標 | 定義 | 門檻 |
| --- | --- | --- |
| `faithfulness` | 敘事內容是否全部可回溯到 retrieved context | ≥ 0.90 |
| `answer_relevancy` | 敘事是否切題 | ≥ 0.85 |
| `context_recall` | Golden 證據是否被檢索到 | ≥ 0.80 |
| `context_precision` | 檢索結果中相關比例 | ≥ 0.70 |

### 5.2 整合路徑

* 新增 `scripts/eval_ragas.py`
* 每個案例需提供 `ground_truth_answer` 與 `ground_truth_contexts`
* 結果寫入 `evaluation_runs` 表（Phase 2 schema 擴充）

## 6. 基準報告

每次 schema / seed / 規則變動，必須 re-run 並附：

* Layer A~C 通過率
* Layer D 指標（Phase 2 起）
* Diff vs. 上一版

## 7. 特殊指標

### 7.1 Safety Metrics

| 指標 | 定義 | 目標 |
| --- | --- | --- |
| `unsupported_assertion_rate` | 敘事含未在 contract 列出的名詞比例 | < 2% |
| `over_prescription_rate` | 敘事含具體方劑或劑量比例 | 0% |
| `missing_critical_question_rate` | 有缺失但未補問 | < 10% |

### 7.2 Determinism Check

對同一輸入連跑 5 次：

* Stage 1 輸出必須 hash 一致
* Stage 2 允許字面差異，但 `candidate_patterns` 順序與 `E_missing` 必須一致

## 8. 驗收要求

* `make eval` 可穩定跑出斷言報告
* Phase 2 前：Layer A ≥ 95%，Layer B ≥ 90%，Layer C Top-1 ≥ 80%
* Phase 2 後：Layer D 指標均達門檻

## 9. 依賴 ADR

* [ADR-001](../adr/ADR-001-tcm-rag-architecture.md) §負面影響與風險（召回率依賴資料量）

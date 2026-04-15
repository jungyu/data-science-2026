# Spec-011: 里程碑與交付

- Status: Draft
- Owner: Project Lead
- Last Updated: 2026-04-15

## 1. 目的

明訂四階段交付範圍與可驗證的完成條件，作為其他 spec 的排程依據。

## 2. 階段總表

| 階段 | 目標 | 完成條件 |
| ---- | ---- | -------- |
| Phase 0 | MVP 閉環 | [Spec-002](./spec-002-feature-extractor.md) / [005](./spec-005-rule-engine.md) / [006](./spec-006-retrieval-pipeline.md) / [007](./spec-007-generation-orchestrator.md) / [008](./spec-008-storage-schema.md) / [010](./spec-010-api-contracts.md) 可端到端跑通 seed 案例 |
| Phase 1 | 資料擴充 + 品質門檻 | 醫砭爬取 ≥ 200 條 symptom atoms；[Spec-009](./spec-009-evaluation-framework.md) Layer A~C 通過率達標 |
| Phase 2 | 進階辨證 + LLM 評估 | 規則 ≥ 30 條；Ragas 整合；多輪問診 |
| Phase 3 | 經典 + 醫案整合 | 《傷寒論》/《金匱要略》/ 醫案入庫；研究型查詢 |

## 3. Phase 0：MVP 閉環（已完成）

### 3.1 交付

| 項目 | 檔案 | 狀態 |
| --- | --- | --- |
| Schema | [sql/tcm-rag.schema.sql](../../sql/tcm-rag.schema.sql) | ✅ |
| Seed | [sql/tcm-rag.seed.sql](../../sql/tcm-rag.seed.sql) | ✅ |
| Atom JSON Schema | [schemas/knowledge-atom.schema.json](../../schemas/knowledge-atom.schema.json) | ✅ |
| Scrape / Parse / Embed | `scripts/scrape_yibian.py` / `parse_to_atoms.py` / `embed_atoms.py` | ✅ |
| Retrieval | [sql/rank_patterns.sql](../../sql/rank_patterns.sql) | ✅ |
| Rules | [scripts/apply_rules.py](../../scripts/apply_rules.py) | ✅ |
| Orchestrator | [scripts/answer_query.py](../../scripts/answer_query.py) + `synthesize_answer.py` | ✅ |
| Eval | [scripts/eval_queries.py](../../scripts/eval_queries.py) + [tests/cases.yaml](../../tests/cases.yaml) | ✅ |
| MCP Server | [mcp-server/server.py](../../mcp-server/server.py) | ✅ |

### 3.2 完成條件

* `make schema && make seed && make embed && make eval` 全過
* `make mcp` 啟動後 `/health` 回 200，`diagnose_tcm` 能回 Answer Contract

## 4. Phase 1：資料擴充 + 品質門檻

### 4.1 交付

* 醫砭 scrape 完整覆蓋《中醫症狀鑒別診斷學》內科部分（≥ 200 symptom atoms）
* 手工 curated pattern atoms ≥ 40（含常見氣血陰陽類）
* Relation seed ≥ 200 條
* [Spec-009](./spec-009-evaluation-framework.md) §3.2 完整案例集（23+ 案）

### 4.2 完成條件

| 指標 | 目標 |
| --- | --- |
| Layer A symptom recall | ≥ 95% |
| Layer B rule match precision | ≥ 90% |
| Layer C Top-1 accuracy | ≥ 80% |
| Layer C Top-3 accuracy | ≥ 95% |

### 4.3 已知風險

* 醫砭 parser 對「常見證候」段落的抽取可能需針對頁型別別調參
* Pattern atoms 數量是瓶頸，需領域專家投入

## 5. Phase 2：進階辨證 + LLM 評估

### 5.1 交付

* 規則數 ≥ 30，涵蓋氣 / 血 / 陰 / 陽 / 表裡 / 寒熱主軸
* 多輪問診：`suggested_questions` 回饋到下一輪輸入
* [Spec-009](./spec-009-evaluation-framework.md) §5 Ragas 整合
* `evaluation_runs` 表（結果永久化）

### 5.2 完成條件

| 指標 | 目標 |
| --- | --- |
| Faithfulness | ≥ 0.90 |
| Answer Relevancy | ≥ 0.85 |
| Context Recall | ≥ 0.80 |
| Over-prescription rate | 0% |

## 6. Phase 3：經典 + 醫案整合

### 6.1 交付

* 《傷寒論》條文 → `citation` atoms（≥ 100 條）
* 《金匱要略》條文 → `citation` atoms（≥ 80 條）
* 醫案 → `case` atoms（≥ 50 則）
* Source weighting 策略：教材 > 經典 > 醫案

### 6.2 完成條件

* 可回答「傷寒論對少陽證如何描述？」並附原文引用
* `case_lookup` 工具可依特徵組合回傳相似醫案

## 7. 里程碑依賴

```
Phase 0 (MVP)
  └── Phase 1 (資料擴充) 依賴 MVP 閉環
        └── Phase 2 (進階辨證) 依賴 Phase 1 案例集
              └── Phase 3 (經典醫案) 依賴 Phase 2 source weighting 機制
```

## 8. 驗收要求

* 每階段結束前交付 `reports/phaseN-release.md`，附：
  * 指標對比表（vs. 上階段）
  * 新增 atoms / rules / cases 數量
  * 已知問題與後階段排程

## 9. 依賴 ADR

* [ADR-001](../adr/ADR-001-tcm-rag-architecture.md) §後果（Phase 3 可考慮 Graph DB）

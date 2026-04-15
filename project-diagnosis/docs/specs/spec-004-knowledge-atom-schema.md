# Spec-004: 知識原子 Schema

- Status: Draft
- Owner: Ontology Lead
- Last Updated: 2026-04-15

## 1. 目的

定義系統內 11 種知識原子（knowledge atom）的欄位契約，作為 [Spec-003](./spec-003-knowledge-etl.md) 的輸出目標與 [Spec-006](./spec-006-retrieval-pipeline.md) 的輸入單元。

此 spec 與 [schemas/knowledge-atom.schema.json](../../schemas/knowledge-atom.schema.json) 一致，JSON Schema 為權威；本文件為敘述與設計原則。

## 2. 原子型別

| atom_type | 說明 | 必填 metadata |
| --- | --- | --- |
| `symptom` | 症狀 | `symptom_family` |
| `sign` | 體徵 | — |
| `tongue_feature` | 舌象 | `diagnostic_weight` |
| `pulse_feature` | 脈象 | `diagnostic_weight` |
| `pattern` | 證型 | `pattern_family` |
| `pathomechanism` | 病因病機 | `feature_signature` |
| `treatment_principle` | 治法 | — |
| `formula` | 方劑 | `formula_family` |
| `herb` | 藥物 | — |
| `citation` | 經典引文 | — |
| `case` | 醫案 | — |

## 3. 共用欄位

| 欄位 | 型別 | 說明 |
| --- | --- | --- |
| `id` | text (ULID-like) | 穩定識別符，pattern `^[A-Za-z0-9_\-]+$` |
| `source_document_id` | text, nullable | 對應 `source_documents.id` |
| `atom_type` | enum | 見 §2 |
| `title` | text | 顯示名稱 |
| `canonical_name` | text | 正規名稱（用於比對、關係邊） |
| `aliases` | text[] (JSONB) | 已知異名 |
| `domain` / `subdomain` / `category` / `subcategory` | text | 分類層級 |
| `body_markdown` | text | 主內容（含 Context Injection 標頭） |
| `summary_text` | text | UI / 重排用短摘要 |
| `embedding_text` | text | 送 embedding 的正規化文本 |
| `quality_score` / `completeness_score` | numeric(5,2) | 0~100 |
| `authority_level` | integer | 0~100，見 [Spec-003 §4](./spec-003-knowledge-etl.md) |
| `is_active` | boolean | 軟刪除用 |
| `metadata` | JSONB | 見 §4 |

## 4. Metadata 欄位

以下為常用欄位，`additionalProperties: true` 允許擴充：

| 欄位 | 適用 atom_type | 型別 | 說明 |
| --- | --- | --- | --- |
| `symptom_family` | symptom | text | 如 汗證 / 發熱 / 疼痛 |
| `pattern_family` | pattern | text | 如 陰虛 / 氣虛 / 血瘀 |
| `organ_bias` | pattern / pathomechanism | text[] | 肝 / 心 / 脾 / 肺 / 腎 |
| `time_bias` | symptom | text[] | 午後 / 夜間 / 晨起 |
| `related_patterns` | symptom / tongue / pulse | text[] | canonical_name 列表 |
| `feature_signature` | pathomechanism | text[] | 定義性特徵集合 |
| `diagnostic_weight` | tongue / pulse | number [0,1] | 重排分數用 |
| `treatment_hint` | pattern / pathomechanism | text[] | 治法方向 |
| `formula_family` | formula | text | 方劑家族 |
| `formula_hint` | pattern | text[] | 代表方 |
| `source_url` / `source_ref` | all | text | 來源回溯 |
| `tags` | all | text[] | 自由標籤 |

## 5. 設計原則

### 5.1 正規名稱與異名分離

`canonical_name` 是關係邊與規則比對的唯一鍵。異名進 `aliases`，不得直接進 `canonical_name`。

### 5.2 一原子一概念

拒絕把「盜汗 + 自汗」合併為單一 atom。若資料源混列，ETL 應拆為兩筆。

### 5.3 Context Injection 必備

`body_markdown` 與 `embedding_text` 開頭必須帶 `[Domain=...]` 類標頭（見 [Spec-003 §6](./spec-003-knowledge-etl.md)），否則 embedding 會漂。

### 5.4 L0 / L2 必人工

權威教材、經典原文的 atom 必須人工填寫 metadata。LLM 只輔助 L1 / L3。

## 6. 驗收要求

* 所有新 atom 必須通過 [schemas/knowledge-atom.schema.json](../../schemas/knowledge-atom.schema.json) 的 JSON Schema validation
* `canonical_name` 在同一 `atom_type` 內唯一（[Spec-008](./spec-008-storage-schema.md) §8 新增 partial unique index）
* `authority_level` 依來源層級落入 §4 表定範圍

## 7. 依賴 ADR

* [ADR-001](../adr/ADR-001-tcm-rag-architecture.md) §Decision §1

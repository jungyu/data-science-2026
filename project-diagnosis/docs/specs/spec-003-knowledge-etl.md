# Spec-003: 知識 ETL

- Status: Draft
- Owner: Data Engineer
- Last Updated: 2026-04-15

## 1. 目的

將外部中醫文獻（醫砭、教材、經典、醫案）轉為 [Spec-004](./spec-004-knowledge-atom-schema.md) 定義的知識原子與關係邊。

## 2. 責任

六階段管線，每階段有明確品質閘：

1. **Ingest** — 抓取來源 → `source_documents(ingestion_status='pending')`
2. **Clean** — HTML 去雜訊、正規化標點 → `clean_markdown`，狀態進入 `cleaned`
3. **Chunk** — 按語義邊界切成候選 atom 段落（非固定長度）
4. **Annotate** — LLM 輔助補 metadata（domain / category / pattern_family / diagnostic_weight⋯），見 [Spec-003a](./spec-003a-etl-prompt-template.md)
5. **Embed** — 由 `embedding_text` 產生 1536-dim vector
6. **Validate** — JSON Schema + 人工抽樣覆核 → 狀態進入 `embedded`

## 3. 非責任

* Ontology 擴充（屬 Spec-004 的 schema 演進流程）
* 規則撰寫（屬 Spec-005）
* 即時檢索（屬 Spec-006）

## 4. 來源分層（資料源策略）

| 層 | 類型 | authority_level | 用途 |
| -- | ---- | --------------- | ---- |
| L0 | 權威教材 | 90–100 | 定義標準證型、術語正規化 |
| L1 | 結構化百科 | 80–90 | RAG 主體資料 |
| L2 | 經典文獻 | 85–95 | 引文與理論依據 |
| L3 | 醫案 | 60–80 | 症狀 → 證型的實證映射 |

## 5. 階段契約

### 5.1 Ingest

| 輸入 | 輸出 |
| --- | --- |
| URL / 檔案 | `source_documents` row，`raw_content` 完整保留 |

實作：`scripts/scrape_yibian.py`（HTML）；Markdown 與純文本直接 upsert。

### 5.2 Clean

| 輸入 | 輸出 |
| --- | --- |
| `raw_content` | `clean_markdown`（保留標題層級 h1~h4，移除 script/style/nav） |

### 5.3 Chunk

切段服從 **知識結構** 而非字數：

* 單一症狀條目 → 1 atom（diagnostic chunk）
* 「概念 / 常見證候 / 鑑別分析」區段 → 可分拆為多個 atomic chunk
* 經典條文 → 每條為 1 atom

實作：`scripts/parse_to_atoms.py`（醫砭啟發式 parser）。

### 5.4 Annotate

由 [Spec-003a](./spec-003a-etl-prompt-template.md) 的 prompt 輔助，LLM 回填：

* `aliases`（已知異名）
* `metadata.symptom_family` / `pattern_family` / `diagnostic_weight`
* `metadata.related_patterns`（供後續 relation extraction 比對）

產出必須通過 [Spec-004](./spec-004-knowledge-atom-schema.md) 的 JSON Schema 驗證才得進下一階段。

### 5.5 Embed

* 模型：`text-embedding-3-small`（1536 dim），可透過 env 覆寫
* 輸入：`embedding_text` 欄位（非 `body_markdown`）
* 實作：`scripts/embed_atoms.py`

### 5.6 Validate

| 類型 | 內容 |
| ---- | ---- |
| 自動 | JSON Schema 通過 / embedding 非 null / search_vector 非 null |
| 人工 | L0 / L2 資料逐筆覆核；L1 / L3 抽樣 ≥ 10% |

狀態全數通過後，`source_documents.ingestion_status` 進入 `embedded`。

## 6. Context Injection

所有 atom 的 `body_markdown` 與 `embedding_text` 必須以結構化標頭開頭：

```
[Domain=內科症狀]
[Category=汗證]
[Symptom=盜汗]
[Source=中醫症狀鑒別診斷學]
```

這是 RAG 的關鍵設計，讓 embedding 同時編碼語義與分類層級。

## 7. 關係抽取（Relation Extraction）

MVP 範圍**不做自動 relation extraction**：

* `parse_to_atoms.py` 只抽「常見證候」列表文字，與**已存在**的 curated pattern atom 建立 `suggests` 關係（weight 0.50）
* 避免自動產生未經覆核的病機推論
* Phase 2 再研究規則式或 LLM 輔助的 strong/weak/conflict 關係推理

## 8. 驗收要求

* Seed 資料（[sql/tcm-rag.seed.sql](../../sql/tcm-rag.seed.sql)）必須能完整通過六階段而不報錯
* 醫砭前 10 頁抽樣：parser 成功率 ≥ 80%，metadata 完整度 ≥ 70%
* Re-run ETL 對同一來源必須 idempotent（`id` 衝突走 upsert）

## 9. 依賴 ADR

* [ADR-001](../adr/ADR-001-tcm-rag-architecture.md) §Decision §1（知識原子粒度）

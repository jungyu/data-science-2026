# Spec-003: 知識 ETL 流程

- Status: Draft
- Owner: Data Engineer / Knowledge Engineer
- Last Updated: 2026-04-14

## 1. 目的

定義古籍文本進入系統前的清洗、拆解、標註、驗證與入庫流程。

## 2. ETL 階段

### Stage 1: Ingestion
- 原始文本匯入（支援 txt / markdown / jsonl / csv）
- OCR 校正（若來源為掃描件）
- 章節邊界保留

### Stage 2: Cleaning
- 清除無意義換行
- 標準化異體字與標點
- 保留原始版本備查

### Stage 3: Atomic Chunking
- 以知識原子為單位切分
- 每個 chunk 應盡量單主題、單命題
- 參見 ADR-006

### Stage 4: Annotation
每個 chunk 需標註：

- `source_book`
- `chapter`
- `normalized_tags`
- `logic_type`
- `modern_interpretation`
- `conditions`
- `source_priority`

### Stage 5: Embedding
- 生成 `embedding_text`（不直接等於原文，適度拼接）
- 呼叫 Embedding API 取得向量
- 寫入 `knowledge_atoms.embedding`

### Stage 6: Validation
- schema 檢查（必填欄位）
- normalized_tags 字典化檢查
- conditions 語法與欄位名稱檢查
- 重複 chunk 偵測（atom_code 唯一性）

## 3. ETL 輸入格式

| 格式 | 說明 |
|------|------|
| `txt` | 純文字，章節用空行或標記分隔 |
| `markdown` | 標題作為章節邊界 |
| `jsonl` | 已初步結構化的資料 |
| `csv` | 僅限已有欄位對應的資料 |

## 4. ETL 輸出格式

每筆輸出為一個 knowledge atom JSON，符合 `schemas/knowledge-atom.schema.json`。

## 5. 質量要求

- 不允許把多個格局判定混進一筆 atom
- 不允許只保留白話而丟掉原文
- 不允許 metadata 缺失 `source_book` 與 `logic_type`

## 6. 人工覆核點

| 覆核項目 | 說明 |
|---------|------|
| 條件抽取 | 是否遺漏或抽錯條件 |
| 語意轉譯 | 現代語意是否偏離原義 |
| tag 覆蓋 | 是否過少或過度延伸 |
| chunk 粒度 | 同一概念是否切得過碎 |

## 7. 依賴 ADR

- ADR-002：文獻權重與權威層級
- ADR-004：文本多重表徵法
- ADR-006：知識原子化 chunking

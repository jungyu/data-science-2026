# Spec-003a: ETL Prompt 模板

- Status: Draft
- Owner: Data Engineer
- Last Updated: 2026-04-15

## 1. 目的

定義 [Spec-003](./spec-003-knowledge-etl.md) §5.4 Annotate 階段所用的 LLM 提示範本，確保 metadata 補全可重現、可覆核。

## 2. 使用時機

* 單一 atom `body_markdown` 已產生，但 `metadata` 缺關鍵欄位
* 需要從自由文本推論 `pattern_family` / `symptom_family` / `diagnostic_weight` 等

**不使用時機**：手工 curated 的 L0 / L2 atoms（必須全由領域審稿者填寫）。

## 3. Prompt 結構

```
[System]
你是中醫知識工程的結構化標註員。依提供的原始條目，輸出符合 schema 的 metadata JSON。
禁止：補充未在條目中出現的症狀 / 證型 / 方劑；禁止編造引用。
若條目資訊不足以推論欄位，對應欄位回 null 並在 reviewer_notes 說明原因。

[Context]
- Atom ID: {atom_id}
- Atom Type: {atom_type}
- Title: {title}
- Source: {source_title} ({source_tier})
- Body:
  {body_markdown}

[Schema Expected]
見 schemas/knowledge-atom.schema.json 中 `metadata` 子結構。
額外加入：
  "reviewer_notes": string (ambiguities, confidence: low/medium/high)

[Few-shot Examples]
(見 §5)

[Task]
請輸出 JSON，僅 metadata 與 reviewer_notes 兩個頂層鍵。
```

## 4. 輸出 Schema（擴充 Spec-004）

```json
{
  "metadata": {
    "symptom_family": "汗證",
    "pattern_family": null,
    "related_patterns": ["陰虛內熱", "心腎不交"],
    "diagnostic_weight": 0.85,
    "tags": ["夜間汗出"]
  },
  "reviewer_notes": {
    "confidence": "medium",
    "ambiguities": [
      "條目未明指舌脈，diagnostic_weight 係依『常見證候』段落推估"
    ]
  }
}
```

`reviewer_notes` 不寫回 atom，而是寫入獨立 `annotation_review` 表供人工覆核。

## 5. Few-shot 範例

### 5.1 症狀原子

**輸入**：

```
Atom Type: symptom
Title: 盜汗
Body: 睡中汗出，醒後汗止。常見陰虛內熱、肝腎陰虛、心腎不交。
```

**輸出**：

```json
{
  "metadata": {
    "symptom_family": "汗證",
    "time_bias": ["夜間", "睡中"],
    "related_patterns": ["陰虛內熱", "肝腎陰虛", "心腎不交"]
  },
  "reviewer_notes": {"confidence": "high"}
}
```

### 5.2 證型原子

**輸入**：

```
Atom Type: pattern
Title: 衛氣不固證
Body: 衛氣虛弱，腠理不固。常見自汗、惡風、舌淡、脈虛。治宜益氣固表。
```

**輸出**：

```json
{
  "metadata": {
    "pattern_family": "氣虛",
    "organ_bias": ["肺", "脾"],
    "treatment_hint": ["益氣固表"],
    "formula_hint": ["玉屏風散"]
  },
  "reviewer_notes": {"confidence": "high"}
}
```

### 5.3 舌象原子

**輸入**：

```
Atom Type: tongue_feature
Title: 舌紅少苔
Body: 陰液虧虛、虛熱內生之象。
```

**輸出**：

```json
{
  "metadata": {
    "diagnostic_weight": 0.90,
    "pattern_family": "陰虛",
    "related_patterns": ["陰虛內熱", "肝腎陰虛"]
  },
  "reviewer_notes": {
    "confidence": "medium",
    "ambiguities": ["diagnostic_weight 0.90 採業界常見設定，需領域審稿確認"]
  }
}
```

## 6. 人工覆核檢查清單

| 檢查項 | 必過 |
| --- | --- |
| JSON 合法，schema validator 通過 | ✅ |
| 未引入原文未出現的症狀 / 證型 | ✅ |
| `reviewer_notes.confidence` 為 `low` 時必須附 `ambiguities` 陣列 | ✅ |
| L0 / L2 來源 confidence 不得為 `low`（應改由人工填） | ✅ |

## 7. 驗收要求

* 對醫砭 10 個抽樣條目跑此 prompt，人工覆核後 `confidence=high` 比例 ≥ 70%
* 對模型未見過的生僻症狀，系統應輸出 `confidence=low` 而非強行填滿
* 不得有幻覺（無中生有的證型名稱）

## 8. 依賴 ADR

* [ADR-001](../adr/ADR-001-tcm-rag-architecture.md) §Decision §5（LLM 受限輸出）

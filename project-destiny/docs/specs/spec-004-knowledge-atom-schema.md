# Spec-004: Knowledge Atom Schema

- Status: Draft
- Owner: Knowledge Architect
- Last Updated: 2026-04-14

## 1. 目的

定義八字命理知識原子的標準資料結構。

## 2. Schema 原則

每個 atom 必須：

1. 可被單獨引用
2. 有明確來源
3. 有標準化特徵
4. 可被向量化
5. 盡可能可抽出條件

## 3. Schema 定義

```json
{
  "id": "atom_ziping_000001",
  "atom_code": "ziping-jia-001",
  "source_book": "子平真詮",
  "source_priority": 1,
  "chapter": "論甲木",
  "section": "甲木總論",
  "title": "甲木冬生調候",

  "original_text": "甲木參天，脫胎要火。",
  "modern_interpretation": "甲木若生寒冷季節，需火暖局，否則寒木難榮。",
  "embedding_text": "甲木 冬季 寒濕 調候 火 日主特性",

  "normalized_tags": ["甲木", "調候", "火", "冬季", "日主特性"],
  "logic_type": ["day_master_nature", "seasonal_adjustment"],
  "conditions": [
    {
      "field": "day_master",
      "operator": "eq",
      "value": "甲"
    },
    {
      "field": "season",
      "operator": "in",
      "value": ["winter", "late_autumn"]
    }
  ],

  "day_master_tags": ["甲"],
  "month_branch_tags": ["子", "亥"],
  "ten_god_tags": [],
  "pattern_tags": [],
  "seasonal_tags": ["winter", "late_autumn"],

  "citation_path": {
    "book": "子平真詮",
    "chapter": "論甲木",
    "line_range": "12-18"
  },

  "status": "active",
  "created_at": "2026-04-14T00:00:00Z",
  "updated_at": "2026-04-14T00:00:00Z"
}
```

## 4. 必填欄位

| 欄位 | 型別 | 說明 |
|------|------|------|
| `atom_code` | string | 全域唯一識別碼 |
| `source_book` | string | 來源著作名稱 |
| `source_priority` | integer | 1=最高權威 |
| `original_text` | string | 古文原文 |
| `normalized_tags` | array | 標準化標籤 |
| `logic_type` | array | 邏輯用途分類 |
| `embedding_text` | string | 向量化文本 |
| `status` | string | active / draft / deprecated |

## 5. 欄位說明

### original_text
保留原始古文，作為最終引用依據。不可被白話版本取代。

### normalized_tags
供 metadata retrieval 與 graph relation 使用。
應來自受控詞彙表（controlled vocabulary）。

### logic_type
標示此 atom 的邏輯用途，枚舉值包含：

| 值 | 說明 |
|----|------|
| `day_master_nature` | 日主性質描述 |
| `pattern_definition` | 格局定義與成立條件 |
| `strength_assessment` | 身強身弱判定 |
| `seasonal_adjustment` | 調候需求 |
| `ten_god_relation` | 十神關係 |
| `conflict_relation` | 刑沖合害 |
| `case_example` | 案例說明 |

### conditions
給 rule engine / symbolic retrieval 使用的硬條件表示。
欄位名稱需對應 Bazi Engine 輸出的欄位。

### embedding_text
不是原文直貼，而是為檢索優化過的拼接文本，建議包含：
- 核心術語
- 標準化標籤
- 現代語義關鍵詞

## 6. 驗收要求

- 同一 atom 不應同時承載多個互不相干命題
- `normalized_tags` 需可被字典化
- `logic_type` 必須來自枚舉值
- `citation_path` 必須可回溯

## 7. 依賴 ADR

- ADR-004：文本多重表徵法
- ADR-006：知識原子化 chunking

# Spec-003a: ETL Annotation Prompt Template

- Status: Draft
- Owner: Knowledge Engineer
- Last Updated: 2026-04-14
- 關聯：Spec-003, Spec-004, ADR-004, ADR-006

## 1. 目的

定義 **LLM 輔助標註** 古籍段落時使用的 prompt 範本，讓 ETL 階段能產出符合
`schemas/knowledge-atom.schema.json` 的結構化輸出。

此範本為 **半自動** 流程的核心：LLM 提供初稿，人工負責覆核條件抽取與標籤正確性。

## 2. 使用情境

| 階段 | 動作 | 使用本範本 |
|------|------|-----------|
| Stage 3 Chunking | 由人工或腳本初步切分段落 | ✗ |
| Stage 4 Annotation | LLM 對每個 chunk 輸出 atom JSON | ✓ |
| Stage 6 Validation | schema 驗證、人工覆核 | ✗ |

## 3. Prompt 範本

### System
```
你是一位熟稔八字子平命理與古籍訓詁的知識工程師。
你的任務是將一段古籍原文轉換為符合 knowledge-atom JSON Schema 的結構化資料。

嚴格規則：
1. original_text 必須完整保留原文，不得增刪字句。
2. 不得自行創造原文中不存在的論斷。
3. normalized_tags 必須從受控詞彙表中選擇（見下方）。
4. logic_type 必須從以下枚舉值選擇：
   day_master_nature | pattern_definition | strength_assessment |
   seasonal_adjustment | ten_god_relation | conflict_relation |
   case_example | general_principle
5. conditions 的 field 必須對應 Bazi Engine 輸出欄位，不可發明新欄位。
6. 若原文過於抽象無法抽出結構化條件，conditions 留空陣列即可，不可硬編條件。
7. 同一段原文若承載多個不相干命題，回報 "split_required": true 並建議切分點。

輸出格式：嚴格 JSON，無 markdown 標記。
```

### Context（填入每次呼叫）
```
【來源書目】{source_book}
【章節】{chapter} / {section}
【權威層級】{source_priority}
【原文片段】
{original_text}

【受控詞彙表（normalized_tags 可選項）】
天干：甲 乙 丙 丁 戊 己 庚 辛 壬 癸
地支：子 丑 寅 卯 辰 巳 午 未 申 酉 戌 亥
十神：比肩 劫財 食神 傷官 偏財 正財 七殺 正官 偏印 正印
格局：正官格 七殺格 正財格 偏財格 正印格 偏印格 食神格 傷官格 比劫格 建祿格 陽刃格
主題：調候 用神 身強 身弱 制化 破格 變格 秀氣 貴氣 日主性質
關係：沖 合 刑 害 破 三會 三合

【Bazi Engine 可用欄位（conditions.field 僅能從此選）】
day_master | month_commander | season | day_master_strength |
four_pillars | hidden_stems | visible_ten_gods | month_hidden_ten_god |
branches | pattern | risk_flags
```

### Output Schema（提示 LLM）
```json
{
  "atom_code": "{source_slug}-{topic}-{seq}",
  "source_book": "...",
  "source_priority": 1,
  "chapter": "...",
  "section": "...",
  "title": "一句話摘要，≤15 字",
  "original_text": "原文，一字不改",
  "modern_interpretation": "現代語意轉述，保留術語",
  "embedding_text": "術語 + 關鍵概念，空格分隔，約 20-40 字",
  "normalized_tags": ["..."],
  "logic_type": ["..."],
  "conditions": [
    {"field": "...", "operator": "eq|in|contains|...", "value": "..."}
  ],
  "day_master_tags": ["甲"],
  "month_branch_tags": [],
  "ten_god_tags": [],
  "pattern_tags": [],
  "seasonal_tags": [],
  "citation_path": {"book":"...","chapter":"...","line_range":"..."},
  "status": "draft",
  "split_required": false,
  "reviewer_notes": "若有不確定處請在此說明"
}
```

## 4. Few-shot 範例

### Input
```
【來源書目】子平真詮
【章節】論傷官 / 傷官總論
【原文片段】
傷官見官，為禍百端。唯有傷官佩印，或傷盡官星不見，方為貴格。
```

### Expected Output
```json
{
  "atom_code": "ziping-conflict-shangguan-jianguan-001",
  "source_book": "子平真詮",
  "source_priority": 1,
  "chapter": "論傷官",
  "section": "傷官總論",
  "title": "傷官見官為禍禁忌",
  "original_text": "傷官見官，為禍百端。唯有傷官佩印，或傷盡官星不見，方為貴格。",
  "modern_interpretation": "傷官剋制正官為命理大忌；解法有二：一為傷官佩印化傷，二為傷官極旺而完全剋盡官星不再出現。",
  "embedding_text": "傷官見官 為禍百端 傷官佩印 傷盡官星 貴格 禁忌",
  "normalized_tags": ["傷官", "正官", "傷官見官", "傷官佩印", "破格"],
  "logic_type": ["conflict_relation", "pattern_definition"],
  "conditions": [
    {"field": "visible_ten_gods", "operator": "contains_all", "value": ["傷官", "正官"]},
    {"field": "visible_ten_gods", "operator": "not_contains", "value": "正印"}
  ],
  "day_master_tags": [],
  "month_branch_tags": [],
  "ten_god_tags": ["傷官", "正官", "正印"],
  "pattern_tags": [],
  "seasonal_tags": [],
  "citation_path": {"book":"子平真詮","chapter":"論傷官","line_range":"30-38"},
  "status": "draft",
  "split_required": false,
  "reviewer_notes": ""
}
```

## 5. 人工覆核 Checklist

| 項目 | 檢查要點 |
|------|---------|
| 原文完整性 | `original_text` 與來源逐字比對 |
| 條件抽取 | `conditions.field` 是否僅使用允許欄位 |
| 標籤範圍 | `normalized_tags` 是否全部來自受控詞彙表 |
| 邏輯類型 | `logic_type` 是否與原文主旨相符 |
| 單一命題 | 是否應設 `split_required: true` |
| 引用定位 | `citation_path.line_range` 是否可驗證 |

## 6. 進版後切換為 active

- 覆核通過 → `status: active`，寫入正式表
- 覆核不通過 → 保留 `status: draft`，列入待修清單
- 發現多命題 → 由人工切分為多筆 draft atom，重新覆核

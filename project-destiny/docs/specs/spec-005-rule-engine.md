# Spec-005: 規則引擎

- Status: Draft
- Owner: System Architect / Backend Engineer
- Last Updated: 2026-04-14

## 1. 目的

定義 Rule Engine 如何從命盤資料產出可供檢索與生成使用的中介判斷。

## 2. 核心責任

Rule Engine 負責：

- 日主強弱初判
- 月令與季節影響分析
- 格局候選判定
- 調候需求推導
- 合沖刑害摘要
- 風險旗標建立
- Retrieval query seed 產生

## 3. 不負責內容

- 原文檢索
- 最終自然語言敘述
- 流派自由詮釋

## 4. Input

使用 `Bazi Engine` 的結構化輸出（見 Spec-002 Output Contract）。

## 5. Output Contract

```json
{
  "chart_id": "chart_xxx",
  "strength_assessment": {
    "day_master_strength": "moderately_strong",
    "supporting_elements": ["水", "木"],
    "draining_elements": ["火"],
    "controlling_elements": ["金"],
    "confidence": "medium"
  },
  "candidate_patterns": [
    {
      "pattern": "正官格",
      "confidence": "high",
      "basis": "申月庚金透干為正官"
    },
    {
      "pattern": "官印相生",
      "confidence": "medium",
      "basis": "官生印、印生身"
    }
  ],
  "seasonal_adjustment_needed": ["火"],
  "special_relations": [
    {
      "type": "沖",
      "from": "子",
      "to": "午",
      "impact": "moderate"
    }
  ],
  "risk_flags": ["傷官見官_possible"],
  "retrieval_query_seeds": [
    "甲木 申月 正官格",
    "官印相生 調候 火",
    "子午沖 格局影響"
  ]
}
```

## 6. 規則層級

### Level 1：硬規則（必執行）
- 四柱基礎關係
- 藏干展開
- 十神映射

### Level 2：骨架規則（主框架）
- 身強身弱初判
- 格局候選（以月令透干為主）
- 調候方向

### Level 3：高階規則（修正層）
- 破格條件
- 變格條件
- 優先序衝突處理

## 7. 設計原則

- 規則必須可單元測試
- 規則應可版本化管理
- 規則輸出應與生成層嚴格分離
- 不確定性需明示 confidence 等級

## 8. 驗收要求

- 能穩定產出候選格局（覆蓋主流格局）
- 能輸出 retrieval query seeds
- 能對特殊結構標示風險旗標
- 可回歸測試

## 9. 依賴 ADR

- ADR-005：規則引擎先於生成層

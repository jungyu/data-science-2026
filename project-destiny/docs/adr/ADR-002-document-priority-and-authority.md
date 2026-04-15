# ADR-002: 文獻權重與權威層級策略

- Status: Accepted
- Date: 2026-04-14
- Deciders: Product Architect, Knowledge Architect
- Tags: corpus, weighting, authority, knowledge-governance

## Context

八字命理文獻來源繁多，不同著作之間常存在語氣差異、取用角度差異，甚至理論重心不同。
若在 RAG 系統中將所有來源視為同權，模型在生成時容易拼接出互相衝突的判斷，導致解釋雖然流暢，但缺乏理論主軸。

例如：

- 某段《三命通會》重案例描述
- 某段《滴天髓》重氣象與神韻
- 《子平真詮》則更適合作為格局判定骨架

若沒有設定權重與知識層級，系統在遇到衝突時無法知道應優先相信誰。

## Decision

本系統建立明確的知識權威層級：

- **Priority 1**：`子平真詮`
  - 作為格局、強弱、用神邏輯的主骨架

- **Priority 1.5**：`滴天髓`
  - 作為高階修正、氣象與變格補充

- **Priority 2**：`三命通會`
  - 作為描述性擴展、案例對照與 lookup 補強

- **Priority 3**：`千里命稿`
  - 作為現代語境映射與敘述補充

- **Priority 4**：其他現代資料與網路資料
  - 僅作參考，不作核心依據

系統在召回融合與生成階段，需將來源優先級納入排序與證據評分。

## Alternatives Considered

### Option A: 所有來源平權
優點：
- 實作簡單
- 易於擴充資料量

缺點：
- 衝突難以處理
- 生成結果容易失去骨幹
- 很難做可解釋性治理

### Option B: 僅用單一著作
優點：
- 理論一致性高
- 管理簡單

缺點：
- 覆蓋範圍不足
- 描述與案例層太薄
- 難以處理邊緣情境

## Consequences

### Positive
- 降低多來源知識衝突
- 讓系統有穩定主幹
- 可做更清楚的 reranking
- 有利於人工審查與版本治理

### Negative
- 需要明確定義各文獻角色
- 當資料量增加時需持續維護權重策略
- 流派爭議仍可能存在

## Implementation Notes

每個知識原子需至少包含：

- `source_book`
- `source_priority`
- `knowledge_role`
- `citation_path`

Retrieval Orchestrator 在排序時，需將 `source_priority` 納入最終分數。

## Decision Drivers

- 需要避免多文獻混講造成的邏輯漂移
- 需要穩定的核心理論骨架
- 需要可維運的知識治理策略

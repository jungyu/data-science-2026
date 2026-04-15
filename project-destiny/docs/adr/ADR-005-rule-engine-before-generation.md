# ADR-005: 規則引擎先於生成層執行

- Status: Accepted
- Date: 2026-04-14
- Deciders: System Architect, NLP Engineer
- Tags: rules, orchestration, generation, reasoning

## Context

若直接將使用者命盤與文獻片段交給 LLM，模型很容易根據局部語意自行拼接敘事，導致：

- 忽略月令優先
- 忽略格局成立條件
- 混淆破格與成格
- 將描述當成規則
- 用話術掩蓋不確定性

換句話說，若不先做結構判定，LLM 很容易變成「很會講，但不一定講對」。

## Decision

本系統規定：

1. 先由 Rule Engine 解析命盤
2. 再由 Retrieval 根據規則結果做多路召回
3. 最後才由 LLM 進行受控生成

Rule Engine 的最低責任範圍包括：

- 日主強弱初判
- 格局候選判定
- 調候需求判定
- 刑沖合害摘要
- 特殊風險旗標
- 查詢特徵產生

LLM 不得自行取代這些核心邏輯。

## Alternatives Considered

### Option A: 先檢索後生成，規則只做補充
優點：
- 流程簡單

缺點：
- 會失去命盤的結構先驗
- 檢索可能偏題
- 生成階段難以約束

### Option B: 全部交給 LLM 自行推理
優點：
- 開發速度快

缺點：
- 不穩定
- 不可驗證
- 幻覺率高

### Option C: Rule Engine 優先
優點：
- 邏輯骨架穩定
- 檢索更準
- 生成更可控

缺點：
- 需維護規則引擎
- 初期設計成本較高

## Consequences

### Positive
- 降低 LLM 任意發揮空間
- 提高檢索精度
- 有利於可解釋性與測試

### Negative
- 需要設計與維護規則表
- 初期可能只能覆蓋主流格局

## Implementation Notes

Rule Engine 輸出應為中介資料層，不直接面向使用者。
其輸出將作為 Retrieval Orchestrator 與 Prompt Builder 的主要輸入。

## Decision Drivers

- 八字推理有明顯先後順序
- 結構正確性優先於語言表達
- 需要降低幻覺與錯誤敘事

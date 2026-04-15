# ADR-004: 文本表徵採多重表徵法

- Status: Accepted
- Date: 2026-04-14
- Deciders: Knowledge Architect, NLP Engineer
- Tags: text-representation, annotation, metadata, embedding

## Context

八字古籍多為文言文，其語言高度壓縮、術語密度高，單字背後經常代表複雜的條件邏輯。
若將原文完全白話化再做檢索，會造成術語精度下降與語義擴散。
若只保留原文，則不利於現代語義嵌入與最終對使用者的可讀性輸出。

因此，系統必須找到一種兼顧：

- 權威性
- 可計算性
- 可檢索性
- 可生成性

的文本表徵方式。

## Decision

每個知識原子採用 **多重表徵法**，至少包含以下欄位：

1. `original_text`
   - 保留古文原文

2. `normalized_tags`
   - 將日主、月令、十神、格局、五行、條件等標準化

3. `logic_type`
   - 標示此段在解決什麼問題，例如格局、調候、強弱、刑沖等

4. `modern_interpretation`
   - 以現代語言重述核心意思

5. `conditions`
   - 將可抽出的硬條件轉為結構化表示

6. `embedding_text`
   - 為向量化而設計的聚合文本

## Alternatives Considered

### Option A: 只保留原文
優點：
- 權威性高
- 不失真

缺點：
- 不利於 embedding
- 不利於最終生成
- 不利於標準化查詢

### Option B: 完全白話化
優點：
- 對一般模型較友善
- 容易閱讀

缺點：
- 資訊熵損失高
- 術語精度下降
- 易引入主觀詮釋偏差

### Option C: 原文 + 結構化標註 + 白話轉譯
優點：
- 同時兼顧三種需求
- 可支援多種檢索方式
- 有利於可追溯性

缺點：
- 前處理成本最高
- schema 設計要求高

## Consequences

### Positive
- 能提升 metadata 與 vector 雙路檢索品質
- 兼顧古文權威性與生成可讀性
- 有利於規則抽取與圖譜建模

### Negative
- ETL 流程較重
- 需要人工校對標註結果
- schema 版本管理需更嚴謹

## Implementation Notes

建議 `embedding_text` 不直接等於原文，而是將：

- 原文關鍵詞
- 標準化術語
- 現代語義描述

做適度拼接，以提高召回品質。

## Decision Drivers

- 八字古籍屬高密度 DSL
- 單一表徵無法同時滿足檢索與生成需求
- 系統需要可計算而非僅可閱讀的知識單元

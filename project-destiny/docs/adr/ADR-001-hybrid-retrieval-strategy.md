# ADR-001: 採用混合式檢索策略（Hybrid Retrieval）

- Status: Accepted
- Date: 2026-04-14
- Deciders: Product Architect, Knowledge Architect, NLP Engineer
- Tags: rag, retrieval, vector-search, graph, symbolic-rules

## Context

八字解盤不是一般 FAQ 或文件問答場景。

其查詢輸入本質上不是自然語言問題，而是由四柱、干支、藏干、十神、月令、刑沖合害、格局、調候等多維特徵構成的結構化命盤。
若僅使用向量檢索，系統容易因忽略干支之間的結構關係，而產生語義相似但邏輯錯誤的召回結果。

例如：

- 「甲木生於子月」與「甲木生於午月」語義上可能都接近甲木日主，但其命理判讀方向可能完全不同。
- 「傷官見官」不是單一詞匹配問題，而是條件組合成立後才有意義。
- 「沖合刑害」具有優先序與相互覆蓋關係，無法靠語意相似度單獨處理。

因此，本系統需要能同時處理：

1. 嚴格符號條件
2. 結構化標籤匹配
3. 語義近似描述
4. 關係鏈推展

## Decision

本系統採用 **Hybrid Retrieval** 架構，結合以下四種召回路徑：

1. **Symbolic Retrieval**
   - 根據命盤特徵、格局候選、刑沖合害條件，直接檢索規則與文獻對應節點。

2. **Metadata Retrieval**
   - 根據 normalized tags，例如日主、月令、十神、格局、調候元素等，進行精準過濾與查詢。

3. **Vector Retrieval**
   - 對原文、白話釋義與命盤語義摘要做嵌入，支援語義相似召回。

4. **Graph Retrieval**
   - 針對干支、十神、格局、喜忌與條件關係進行圖狀擴展查詢。

最終由 Retrieval Orchestrator 對多路結果進行合併、去重、加權與重排序。

## Alternatives Considered

### Option A: 單純向量檢索
優點：
- 實作簡單
- 初期開發快

缺點：
- 容易忽略符號關係
- 對格局條件與刑沖合害不敏感
- 幻覺風險高

### Option B: 單純規則引擎
優點：
- 邏輯可控
- 結果穩定

缺點：
- 難以吸收古籍中的描述性知識
- 對變格、邊緣情況與現代語義映射不夠彈性

### Option C: Vector + Metadata
優點：
- 比單純向量更準
- 實作成本較低

缺點：
- 仍不足以表達複雜關係鏈與條件推展

## Consequences

### Positive
- 提高召回準確率與穩定性
- 降低語義近似但命理錯誤的檢索結果
- 可逐步演進，不必一次把所有能力做完
- 有利於建立可追溯的推理流程

### Negative
- 架構較複雜
- 前處理成本提升
- 需要維護多種索引與查詢邏輯
- 評估與除錯成本上升

## Implementation Notes

第一階段可先實作：

1. Symbolic Retrieval
2. Metadata Retrieval
3. Vector Retrieval

Graph Retrieval 可作為第二階段增強項。

## Decision Drivers

- 八字知識屬於高結構化符號系統
- 幻覺控制比語言流暢度更重要
- 需要可追溯、可驗證的檢索行為

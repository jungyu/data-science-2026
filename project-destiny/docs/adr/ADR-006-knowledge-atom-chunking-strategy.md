# ADR-006: 採用知識原子化 Chunking 策略

- Status: Accepted
- Date: 2026-04-14
- Deciders: Knowledge Architect, Data Engineer
- Tags: chunking, knowledge-atom, corpus, ETL

## Context

一般 RAG 常採固定 token 長度、段落、頁面或章節切分。
但八字知識的有效檢索單位，通常不是頁，也不是段，而是「一個可獨立成立的命理命題」。

例如：

- 甲木生於子月的調候論
- 正官格成立條件
- 傷官見官的成局與為禍條件
- 身強財旺的判定邏輯

若使用通用段落切法，常會把多個邏輯單元混在同一 chunk 中，導致：

- 標籤污染
- 條件不純
- 向量主題混雜
- 難以建立規則映射

## Decision

系統採用 **Knowledge Atom Chunking**，以「最小可獨立引用的邏輯單元」作為 chunk 邊界。
每個 chunk 必須盡量滿足：

1. 主題單一
2. 邏輯邊界清楚
3. 可以被標註 tags
4. 可以抽出條件
5. 可以被獨立引用

## Alternatives Considered

### Option A: 固定 token chunking
優點：
- 實作容易
- 相容通用工具

缺點：
- 不符合命理文本結構
- 邏輯污染嚴重

### Option B: 章節 chunking
優點：
- 保留上下文

缺點：
- chunk 過大
- 查詢精度差
- 不利 reranking

### Option C: 知識原子 chunking
優點：
- 對齊命理知識結構
- 有利 metadata 與規則映射
- 更適合多路檢索

缺點：
- ETL 較複雜
- 需人工或半自動校正

## Consequences

### Positive
- 提高查詢精度
- 降低多主題混雜問題
- 有利於知識圖譜與規則引擎連結

### Negative
- 前處理複雜
- 需要一致的 chunking 規範
- 人工審核成本較高

## Implementation Notes

第一階段建議從《子平真詮》開始，因其文本較適合建立規則骨架與 chunking 規範。

## Decision Drivers

- 命理知識是邏輯單元，不是頁面單元
- 需要讓 chunk 變成可計算的知識原子
- 後續圖譜與規則層都依賴這種切法

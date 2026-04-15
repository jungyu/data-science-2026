# ADR-008: 生成結果必須具備可追溯性與評估機制

- Status: Accepted
- Date: 2026-04-14
- Deciders: Product Architect, NLP Engineer, QA Engineer
- Tags: evaluation, grounded-generation, hallucination, observability

## Context

八字解盤 RAG 的風險，不在於回答不流暢，而在於回答很流暢但沒有根據。
若系統產出的結論無法回溯到規則、文獻與命盤特徵，則無法：

- 驗證正確性
- 人工校對
- 做錯誤分析
- 持續優化

在知識型系統中，「會說」不等於「可信」。

## Decision

本系統要求所有生成結果必須遵守 **Grounded Generation** 原則：

1. 每個主要結論需對應至少一項證據來源
2. 需區分以下三類內容：
   - 規則判定
   - 文獻引述
   - 模型解釋
3. 當證據不足時，系統必須顯示不確定性，而非自動補完

此外，系統需建立最小評估框架，至少覆蓋：

- 排盤正確率
- 規則命中率
- 檢索命中率
- 可追溯性完整度
- 幻覺率

## Alternatives Considered

### Option A: 僅做人工主觀驗收
優點：
- 初期簡單

缺點：
- 不可持續
- 無法回歸測試
- 難以定位問題

### Option B: 僅做一般 RAG 指標
優點：
- 可沿用通用框架

缺點：
- 無法反映命理系統核心風險
- 不能衡量結構正確性

### Option C: Grounded Generation + Domain Evaluation
優點：
- 可持續優化
- 可分析錯誤來源
- 更適合高風險知識系統

缺點：
- 評估設計成本較高
- 需要建立黃金資料集

## Consequences

### Positive
- 提高可信度
- 有利於除錯與模型治理
- 可支援回歸測試與版本比較

### Negative
- 初期需花時間設計評估集
- 產出流程較嚴格，回應可能較保守

## Implementation Notes

建議生成輸出採用顯式區段：

- 命盤摘要
- 核心判斷
- 依據文獻
- 規則說明
- 綜合解釋
- 不確定性聲明

## Decision Drivers

- 需要避免流暢型幻覺
- 需要能持續優化
- 需要支援人工審核與品質治理

# JR Pass RAG 系統：評估規格

## 概述
本規格定義如何使用 RAGAS 與 TruLens 框架評估 JR Pass RAG 系統的品質，特別是檢測幻覺（hallucination）、檢索準確性與回答可信度。評估涵蓋 retrieval、grounding、generation 三個階段。

## 評估框架
- **主要框架**：RAGAS（Retrieval-Augmented Generation Assessment）
- **輔助框架**：TruLens（LLM 應用可觀測性與評估）
- **評估範圍**：faithfulness、relevance、hallucination、attribution correctness

## 評估指標

### RAGAS 指標
- **Faithfulness**：回答是否忠實於檢索到的知識（不引入外部知識）
- **Relevance**：檢索結果與問題的相關性
- **Context Precision**：檢索 chunks 是否精確支援回答
- **Context Recall**：檢索結果是否涵蓋所有必要知識
- **Answer Correctness**：回答的準確性與完整性

### TruLens 指標
- **Attribution Correctness**：citations 是否正確對應到使用的 chunks
- **Hallucination Detection**：回答是否包含未經檢索支持的內容
- **Evidence Usage**：系統是否正確使用檢索 evidence
- **Grounding Gate Effectiveness**：gate 是否正確過濾不足 evidence 的回答

## 評估流程
1. **準備測試資料集**：建立包含問題、行程、期望回答的測試案例
2. **執行系統查詢**：對每個測試案例運行 RAG 系統
3. **收集輸出**：記錄檢索 chunks、grounding 狀態、生成回答、citations
4. **計算指標**：使用 RAGAS/TruLens 計算各項分數
5. **分析結果**：識別幻覺、檢索錯誤、grounding 失敗的模式

## 測試案例設計
- **Positive Cases**：行程符合 JR Pass 條件，期望正確檢索與回答
- **Negative Cases**：行程不符合任何條件，期望拒答或明確說明
- **Edge Cases**：部分符合、規則衝突、知識不足
- **Hallucination Triggers**：故意設計超出知識庫的問題，測試是否產生虛構回答

## 接受標準
- **Faithfulness Score**：≥ 0.85（回答忠實於檢索知識）
- **Relevance Score**：≥ 0.80（檢索結果相關）
- **Hallucination Rate**：< 5%（低幻覺發生率）
- **Grounding Gate Accuracy**：≥ 90%（正確區分 pass/fallback/block）
- **Citation Fidelity**：≥ 95%（citations 正確無虛構）

## 評估報告格式
- **總結指標表**：各項分數的平均值與標準差
- **案例分析**：每個測試案例的詳細 breakdown
- **錯誤模式**：常見幻覺類型、檢索失敗原因
- **改進建議**：基於評估結果的系統優化方向

## 驗收條件
- [ ] 成功設定 RAGAS 與 TruLens 評估環境
- [ ] 測試資料集涵蓋至少 50 個案例（positive/negative/edge）
- [ ] 評估指標計算正確並達到接受標準
- [ ] 產生詳細評估報告，識別系統弱點
- [ ] 基於評估結果提出具體改進措施
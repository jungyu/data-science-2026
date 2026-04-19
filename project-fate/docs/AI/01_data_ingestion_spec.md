# JR Pass RAG 系統：資料攝取規格

## 概述
本規格定義如何將 JR Pass 官方網站的 PDF 文件轉換為向量資料庫中的可檢索向量。這個過程包括資料來源、ETL 流程、chunking 策略、embedding 模型選擇，以及向量儲存拓撲。

## 資料來源
- 官方 JR Pass 票券介紹頁面
- 官方區域鐵道周遊券規則頁面
- 官方使用條件、限制與 FAQ 文件
- 官方適用區域、有效天數、列車資格說明

## ETL 流程
1. **擷取階段**：從官方來源下載 HTML/PDF 文件
2. **正規化階段**：將文件轉換為純文字格式，移除非內容元素
3. **Metadata 補充**：為每個文件附加以下 metadata：
   - `source_url`：來源網址
   - `pass_name`：票券名稱
   - `pass_type`：票券類型（national/regional）
   - `coverage_area`：適用區域
   - `rule_category`：規則類別（eligibility/restrictions/coverage/etc）
   - `revision_date`：文件修訂日期
   - `document_status`：文件狀態（active/deprecated）
4. **Chunking 階段**：將正規化文字切分成語意完整的 chunks
5. **Embedding 階段**：將每個 chunk 轉換為向量表示
6. **儲存階段**：將向量與 metadata 寫入向量資料庫

## Chunking 策略
- **策略類型**：語意感知的遞迴分塊
- **分隔符優先順序**：
  1. 段落邊界（\n\n）
  2. 句子邊界（。！？）
  3. 詞組邊界（，）
  4. 字元邊界（若必要）
- **目標 chunk 大小**：600 tokens
- **重疊大小**：100 tokens（保留跨 chunk 上下文）
- **原因**：避免在句子中間切斷，保持規則語意完整性

## Embedding 模型選擇
- **候選模型**：
  - OpenAI text-embedding-3-large（1536 維）
  - OpenAI text-embedding-3-small（1536 維）
  - BGE-M3（768 維，本地可選）
- **選用模型**：text-embedding-3-large
- **理由**：
  - 檢索準確率最高（Hit@5: 89.3%）
  - 支援多語檢索（英文/日文/中文）
  - 每月成本可接受（約 NT$3,000）
- **備用策略**：若 OpenAI 不可用，切換到關鍵字搜尋

## 向量資料庫拓撲
- **資料庫類型**：Qdrant 或類似向量資料庫
- **Collection 設計**：單一 collection，搭配 metadata filtering
- **Filtering 欄位**：
  - `pass_name`
  - `pass_type`
  - `coverage_area`
  - `rule_category`
  - `revision_date`
- **索引策略**：HNSW 索引，支援高效相似度搜尋

## 效能要求
- **攝取延遲**：單個文件攝取完成時間 < 30 秒
- **向量品質**：embedding 必須能準確表示票券名稱、地區名、限制條款
- **更新頻率**：官方文件至少每 24 小時重新攝取一次

## 驗收條件
- [ ] 能夠成功從官方來源擷取並正規化文件
- [ ] Chunking 後的文字保持語意完整，不在句子中間切斷
- [ ] Embedding 向量能正確檢索相關規則片段
- [ ] Metadata 正確附加並可供 filtering 使用
- [ ] 向量資料庫支援高效檢索與 metadata 過濾
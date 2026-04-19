# ADR-005：規則檢索必須採用 Revision-Aware Metadata

## 背景

JR Pass 規則會隨時間變動。購買資格、票價參考、可搭列車範圍、預約要求與 FAQ 說明都可能在官方更新後產生差異。

若 chunk 在索引時沒有帶 revision-aware metadata，系統可能會檢索到來自不同版本的規則片段，卻無法判斷哪一個才是目前有效版本。這會造成三種風險：

- 過期規則被當作現行規則引用
- 互相衝突的 chunks 在檢索時被視為同等有效
- 生成層無法辨識版本歧義

由於本系統是官方規則導向的諮詢系統，因此資料新鮮度與版本可追溯性是必要條件。

## 決策

每個被索引的 chunk 都必須攜帶 revision-aware metadata，至少包含：

- `source_url`
- `pass_name`
- `rule_category`
- `revision_date`
- `document_status`

當多個相關 chunks 同時存在時，retrieval 與 reranking 應優先考慮最新且有效的規則內容。  
若偵測到不同版本間存在衝突，系統必須顯示 warning，而不是靜默選擇其一。

## 狀態

Accepted

## 後果

### 正面影響

- 降低引用過期規則的風險
- 提升 citation 的可追溯性
- 支援 revision conflict detection
- 強化合規性回答的可信度

### 負面影響

- 增加 ingestion 與 metadata 管理複雜度
- 需要可靠地抽取 revision date 與 document status

### 後續影響

- 向量資料 schema 與 ETL pipeline 都必須保留 revision 欄位
- 評估流程必須納入「同一規則存在多個版本」的測試案例

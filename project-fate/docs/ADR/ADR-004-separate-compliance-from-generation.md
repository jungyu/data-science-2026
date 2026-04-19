# ADR-004：將合規判定與回答生成分離

## 背景

JR Pass 諮詢不只是一般文字問答。系統必須根據官方規則判定行程是否符合資格、是否受限，以及在證據不足時是否應保守回答。

如果讓單一生成步驟直接吃入 itinerary 與 retrieved chunks，很容易把三件不同的事混在一起：

- 檢索官方規則
- 根據規則進行合規判定
- 生成面向使用者的自然語言說明

這會讓系統更難測試、更難審計，也更容易把沒有證據支持的推論包裝成正式結論。

## 決策

系統採用三層邏輯結構：

1. `Rule Retrieval Layer`
   負責檢索官方規則證據。
2. `Compliance Assessment Layer`
   負責將行程對照規則並產生結構化判定。
3. `Answer Generation Layer`
   負責根據檢索證據與判定結果生成最終說明文字。

生成層不得自行編造未經判定層支持的合規結論。

## 狀態

Accepted

## 後果

### 正面影響

- 提升規則判定流程的可測試性
- 將證據檢索與邏輯判定分離
- 更容易解釋每個結論是由哪個系統層產生
- 降低 unsupported compliance claim 的風險

### 負面影響

- 架構比單純的 vector-RAG 更複雜
- 需要明確定義 retrieval、assessment、generation 之間的介面

### 後續影響

- 評估時可分開量測檢索品質與判定品質
- 未來若要導入 rule engine 或 deterministic validator，可替換 assessment layer 而不必重寫 generation layer

# JR Pass 官方規則與合規性 RAG 諮詢系統白皮書

## 1. 摘要

本白皮書描述一套以 `JR Pass 官方規則文件` 為核心知識來源的 Retrieval-Augmented Generation 系統，用於回答旅客對日本 JR Pass 與區域鐵道周遊券的適用條件、限制與基本選購判斷問題。  
系統強調三個目標：

- 可解釋性
- 高可信度檢索
- 降低 hallucination

---

## 2. 問題背景

JR Pass 與日本各區域鐵道周遊券具有高度結構化但分散的規則特性：
- 不同票券的適用範圍不同
- 有效天數、區域、搭乘車種限制不同
- 旅客資格與使用條件可能有例外
- 官方規則會隨時間更新

使用者面臨的困難不只是資訊查找，而是：
- 如何判斷 itinerary 是否符合某張票
- 如何理解限制條件
- 如何確認建議是否真的有規則依據

---

## 3. 知識表徵（Representation）難點

### 3.1 規則型知識不是單純事實型知識

本領域知識不是單一事實問答，而是條件式規則：

- 若在特定區域內移動，則某張 pass 適用
- 若搭乘某些列車，則可能需要額外費用
- 若不符合旅客資格，則不得使用

因此，知識不是單純的 `fact retrieval`，而是帶有條件、例外與限制的規則集合。

### 3.2 名詞對齊問題

同一概念可能有不同表示：
- JR Pass / Japan Rail Pass
- Kansai Area Pass / 關西地區鐵路周遊券
- Tokyo / 東京 / 東京都

若 embedding 與 retrieval 沒有處理這些對齊問題，容易造成召回錯誤。

### 3.3 時間敏感性

票券價格、限制與 FAQ 會更新，因此這是一個 `revision-sensitive domain`。  
若系統沒有版本意識，可能會把舊規則當成新規則引用。

---

## 4. 系統方法

### 4.1 官方規則導向知識庫

本系統第一版僅納入官方來源：
- 官方票券頁
- 官方使用條件
- 官方 FAQ
- 官方區域與限制說明

這樣做能提高 citations 的可信度，也讓 RAG 較適合處理「合規性諮詢」而不是旅遊閒聊。

### 4.2 Retrieval-First 架構

本系統採 retrieval-first：
1. 先根據 itinerary 與問題檢索相關 chunks
2. 再做 grounding gate
3. 再做 compliance assessment
4. 最後生成回答

此流程能避免模型直接依賴先驗知識亂答。

### 4.3 Compliance Assessment Layer

本系統將 `規則檢索` 與 `合規性判斷` 分開。  
這是本系統的重要創新點，因為它把：

- 官方規則依據
- eligibility judgment
- 回答生成

拆成不同層次，提升了可解釋性與測試性。

---

## 5. 幻覺（Hallucination）處理策略

### 5.1 來源限制

只使用官方文件可減少模型接觸到低可信度資料。

### 5.2 Grounding Gate

在生成前加上一層 gate，檢查：
- 是否檢索到足夠證據
- 是否存在規則衝突
- 是否超出系統支援範圍

若 evidence 不足，系統必須：
- 保守回答
- 拒答
- 或明示資料不足

### 5.3 引用式回答

所有最終答案都必須附 citations，使使用者能追溯答案依據。

---

## 6. 冷啟動（Cold Start）與專有名詞問題

### 6.1 冷啟動問題

當新票券、新價格版本或新 FAQ 出現時，系統若尚未 ingest 最新文件，就會出現知識缺口。

本系統的應對方法：
- 每 24 小時刷新規則資料
- 在 metadata 中保留 revision date
- 在回答中顯示 warnings when evidence may be stale

### 6.2 專有名詞對齊

對於票券名、地區名、車種名，系統需在 ingestion 與 retrieval 階段保留標準化 metadata，例如：
- pass_name
- coverage_area
- rule_category
- revision_date

這樣可以降低純語意檢索時的模糊匹配風險。

---

## 7. 創新性

本系統的創新點主要在三個方面：

### 7.1 從「推薦器」轉向「規則與合規性諮詢系統」

多數票券系統只回答哪張票比較划算，但本系統更進一步回答：
- 是否符合官方規則
- 哪些限制會影響使用
- 哪些條款支撐這個判斷

### 7.2 Compliance Assessment 與 Generation 分層

系統不是把 retrieval 結果直接交給 LLM，而是加入顯式判斷層，使回答更可解釋。

### 7.3 Revision-Aware Retrieval

系統將規則版本視為重要知識特徵，而不只是一般文字片段，這讓它更適合處理官方規則這種時間敏感型知識。

---

## 8. 結論

JR Pass 官方規則與合規性 RAG 諮詢系統是一個兼具：
- 檢索能力
- 可解釋性
- 合規性判斷
- 幻覺防護

的知識型 RAG 系統。

相較於一般問答或推薦系統，它更能展示：
- 如何將規則型知識轉成可檢索表示
- 如何將 retrieval 與 judgment 分層
- 如何在真實領域問題中抑制 hallucination

這也使它成為一個符合課程要求、且有明確理論與工程深度的 RAG 專題。

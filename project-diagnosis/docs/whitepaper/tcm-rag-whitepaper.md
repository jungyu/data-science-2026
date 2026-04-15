# 中醫診斷 RAG 系統白皮書

## 以「症狀 → 證型 → 治法」為主軸的可解釋檢索增強生成架構

## 1. 摘要

建構中醫診斷 RAG，不是把《黃帝內經》《傷寒論》《中醫診斷學》丟進向量資料庫就結束。
真正的難點在於：**中醫診斷不是單一關鍵字比對，而是多訊號、跨層級、帶有矛盾消解的辨證過程**。

它很像八字解盤 RAG 時遇到的問題：

* 八字有高維干支組合、刑沖剋害、格局與用神
* 中醫有四診訊號、臟腑經絡、寒熱虛實表裡、病因病機、證型轉換

兩者共同問題是：

1. **特徵不是平面的**
2. **推理不是線性的**
3. **單純向量相似度很容易抓到「像」，但抓不到「對」**
4. **答案必須附帶證據與排除邏輯，否則幻覺率高**

因此，本系統主張：
**中醫診斷 RAG 應採用「本體結構 + 混合檢索 + 可解釋推理鏈」的架構**，而不是只做 embedding search。

---

## 2. 問題定義

### 2.1 一般 RAG 為什麼不夠

假設使用者輸入：

> 最近下午容易潮熱，晚上盜汗，口乾，心煩，舌紅少苔。

如果只做一般向量檢索，系統可能抓到：

* 潮熱
* 盜汗
* 口乾
* 陰虛
* 更年期
* 虛火上炎

表面上看起來很合理，但真正臨床辨證還要問：

* 是不是午後潮熱？
* 有沒有五心煩熱？
* 舌是紅還是絳？
* 脈細數還是弦數？
* 是肝腎陰虛、肺陰虛、心腎不交，還是溫病後期餘熱未清？

也就是說，中醫不是「相似症狀 = 正確答案」，而是：

> **多個症狀與舌脈、時間性、部位性、伴隨症、病程，綜合形成一個證型候選集合，再做鑑別。**

---

## 3. 系統定位

本系統不是要做「替代醫師」的黑盒模型，而是做一個：

### 3.1 系統目標

* 用於 **中醫知識檢索**
* 用於 **症狀到證型的候選推定**
* 用於 **辨證論治的證據整理**
* 用於 **教學、研究、臨床知識輔助**
* 回答時必須能指出：

  * 為何傾向 A 證
  * 為何排除 B 證
  * 依據出自何書、何節、何知識單元

### 3.2 系統邊界

本系統應定位為：

* **知識檢索與決策輔助系統**
* **非自動醫療決策系統**
* **非直接取代臨床問診系統**

換句話說，它回答的是：

> 「依據已知輸入，哪些證型最符合？證據是什麼？還缺哪些關鍵訊號？」

而不是直接斷言：

> 「你就是某某病，請立刻服某方。」

---

## 4. 核心設計原則

### 4.1 原則一：以「證型」而非「段落」作為檢索核心

固定長度 chunk 很像把一本診斷學教材拿去切香腸。
切得很平均，但辨證邏輯會被切斷。

中醫更適合的最小單位不是 500 tokens，而是：

* 一個症狀條目
* 一個證候條目
* 一個舌象條目
* 一個脈象條目
* 一個治法條目
* 一個方劑對應條目
* 一個經典條文條目

也就是：
**chunk 的邊界應該服從知識結構，而不是服從字數。**

### 4.2 原則二：先結構化，再向量化

先把「自汗」「盜汗」「潮熱」「口苦」「弦脈」「舌紅少苔」變成結構化特徵，
再去做檢索。

這樣系統才知道：

* 「盜汗」是汗證
* 「午後潮熱」比「發熱」更精確
* 「舌紅少苔」屬陰虛內熱強訊號
* 「脈弦」會把候選偏向肝鬱、肝火、痛證、痰飲某些路徑

### 4.3 原則三：檢索必須混合式，不可只靠 embedding

`pgvector` 提供向量相似搜尋，支援 cosine、L2、inner product 等距離計算；
PostgreSQL 原生全文檢索可用 `tsvector` / `tsquery` 做關鍵詞與相關度排序。
這代表同一個系統可以把 **語義檢索** 和 **關鍵詞檢索** 放在同一個資料庫中完成。

對中醫來說，這非常重要。因為：

* 向量檢索擅長抓語意近似
* 全文檢索擅長抓術語精確命中
* 結構化欄位擅長做條件過濾
* 圖譜關聯擅長做上下游展開

真正可用的中醫 RAG，應該是四者並用。

---

## 5. 資料源策略

### 5.1 資料分層

建議將資料源分成四層：

#### L0：權威教材層

用於建立基礎 ontology 與定義穩定性。

例如：

* 《中醫基礎理論》
* 《中醫診斷學》
* 《中醫內科學》
* 《方劑學》

用途：

* 定義術語
* 建立標準證型
* 建立症狀、舌脈、病機、治法的正規映射

#### L1：結構化百科層

這一層最適合拿來做 RAG 主體。

以醫砭的《中醫症狀鑒別診斷學》為例，網站本身已呈現清楚的層級結構，
例如 **內科症狀、婦科症狀、兒科症狀** 等分類，且單篇條目可以進一步落到具體症狀頁，
如「健忘」「善恐」「呵欠」等。單頁內容常有「概念」「常見證候」等清楚段落，
這種資料形態比掃 PDF 更適合切成知識原子。

#### L2：經典文獻層

例如：

* 《黃帝內經》
* 《傷寒論》
* 《金匱要略》
* 《溫病條辨》

用途：

* 作為理論依據與引文證據
* 補足現代教材未保留的辨證脈絡
* 作為「經典論證層」

#### L3：醫案與案例層

用途：

* 提供 case-based retrieval
* 提供症狀組合到證型、方藥的真實映射
* 補足教材過於理想化的問題

---

## 6. 知識本體設計（Ontology）

這一段是整個系統的骨架。
沒有 ontology，RAG 只是在撈文字。
有 ontology，RAG 才是在跑診斷結構。

### 6.1 核心實體

建議至少定義以下實體：

* `symptom`：症狀
  例：自汗、盜汗、胸悶、口苦、腹脹

* `sign`：體徵
  例：面赤、肢冷、聲低、神疲

* `tongue_feature`：舌象
  例：舌紅、苔黃膩、舌淡胖、少苔

* `pulse_feature`：脈象
  例：浮、沉、弦、滑、細、數、遲

* `pattern`：證型 / 證候
  例：肺氣虛、自汗；肝火上炎；脾腎陽虛

* `pathomechanism`：病因病機
  例：陰虛火旺、痰熱內擾、肝鬱氣滯、氣虛不固

* `organ_system`：臟腑 / 經絡
  例：肝、心、脾、肺、腎、少陽、陽明

* `treatment_principle`：治法
  例：養陰清熱、疏肝解鬱、益氣固表

* `formula`：方劑
  例：知柏地黃丸、逍遙散、玉屏風散

* `herb`：藥物
  例：黃耆、白朮、浮小麥

* `citation`：經典或教材依據
  例：出處、章節、原文、現代譯解

* `case`：醫案
  例：病例摘要、辨證、處方、療效

### 6.2 核心關係

* symptom `suggests` pattern
* pattern `explained_by` pathomechanism
* pattern `belongs_to` organ_system
* pattern `treated_by` treatment_principle
* treatment_principle `implemented_by` formula
* formula `contains` herb
* citation `supports` pattern
* case `instantiates` pattern
* symptom `conflicts_with` pattern
* tongue_feature `strengthens` pattern
* pulse_feature `strengthens` pattern

#### 例子

不是只記：

> 盜汗 → 陰虛

而是記成：

* 盜汗 `suggests` 陰虛內熱
* 午後潮熱 `strengthens` 陰虛內熱
* 舌紅少苔 `strongly_strengthens` 陰虛內熱
* 脈細數 `strongly_strengthens` 陰虛內熱
* 畏寒肢冷 `conflicts_with` 陰虛內熱

這樣系統才有辦法做「支持證據」與「反證」。

---

## 7. Chunking 策略

### 7.1 不採固定長度主導

固定長度 chunk 可以當備援，但不應是主策略。

原因：中醫一個完整可用單元往往長這樣：

* 概念
* 常見證候
* 病因病機
* 鑑別要點
* 治法
* 方藥線索

如果硬切，就像把一個完整函式切成三段：

* 第一段只有參數
* 第二段只有邏輯
* 第三段只有 return

LLM 讀了也會斷線。

### 7.2 建議三層 chunk

#### A. Atomic Chunk

最小知識原子。

例：

* 症狀：盜汗
* 舌象：舌紅少苔
* 脈象：脈細數
* 證型：肝腎陰虛

#### B. Diagnostic Chunk

一個可獨立用於辨證的完整單元。

例：

* `[內科症狀 > 全身症狀 > 汗證] 盜汗`
* 內含：
  * 概念
  * 常見證候
  * 鑑別重點
  * 對應治法

#### C. Case Chunk

案例單位。

例：

* 某醫案：女性，45歲，午後潮熱、盜汗、心煩、失眠、舌紅少苔、脈細數 → 心腎不交 / 肝腎陰虛

### 7.3 Context Injection

每個 chunk 前面都要補上機器可讀的層級標頭。

例如：

```text
[Domain=內科症狀]
[Location=全身症狀]
[Symptom=盜汗]
[PatternCandidates=陰虛內熱, 心腎不交, 肝腎陰虛]
[Source=中醫症狀鑒別診斷學]
```

這樣 embedding 時，模型不是只讀正文，而是連分類也一起讀進去。

---

## 8. 檢索架構

### 8.1 為什麼一定要混合檢索

因為中醫查詢有四種典型型態：

#### 型態 A：症狀敘述型

> 最近午后潮熱、夜間盜汗、口乾。

這適合：

* symptom extraction
* 向量檢索
* pattern candidate ranking

#### 型態 B：術語查詢型

> 什麼是肝鬱氣滯？

這適合：

* keyword / FTS
* definition chunk retrieval

#### 型態 C：鑑別診斷型

> 自汗與盜汗怎麼分？
> 肝火上炎和陰虛火旺怎麼分？

這適合：

* relation graph expansion
* contrastive retrieval
* reranking

#### 型態 D：經典佐證型

> 傷寒論對少陽證如何描述？

這適合：

* citation retrieval
* source priority routing

### 8.2 建議檢索管線

#### 第一步：Query Normalization

把自然語言轉成結構特徵。

輸入：

> 白天容易出汗，風一吹就怕冷，講話有點沒力。

轉換成：

* symptom: 自汗
* sign: 畏風
* sign: 少氣懶言 / 語弱
* candidate pattern: 衛氣不固 / 肺氣虛 / 氣虛自汗

#### 第二步：Structured Filter

先用 metadata 過濾：

* domain = 汗證 / 全身症狀
* related organ = 肺 / 脾
* pattern family = 氣虛 / 表虛

#### 第三步：Hybrid Retrieval

並行做三路召回：

1. **FTS / BM25 路徑**：抓精確術語與近義詞
2. **Vector 路徑**：抓語意相似條目
3. **Graph Expansion 路徑**：從「自汗」展開到氣虛不固、肺衛不固、玉屏風散、表虛類證候

#### 第四步：Rerank

依下列權重重排：

* 症狀命中數
* 舌脈一致性
* 衝突特徵數
* 資料源權威度
* 條目完整度
* 經典支持度

#### 第五步：Evidence Assembly

不是只給一段文字，而是組成：

* 候選證型 1
* 支持證據
* 排除點
* 建議補問問題
* 參考治法 / 方藥方向
* 引用來源

---

## 9. 推理層設計：從「檢索」升級為「辨證輔助」

RAG 最容易失敗的地方，就是檢索完直接讓 LLM 自由發揮。
中醫場景尤其危險，因為模型會很自然地腦補。

所以建議把生成分成兩段。

### 9.1 Stage 1：候選證型生成（受限）

輸入是結構化訊號。
輸出只允許是：

* 候選證型列表
* 每個候選的支持特徵
* 每個候選的反證
* 缺失資訊

例如：

```json
{
  "candidate_patterns": [
    {
      "name": "陰虛內熱",
      "supporting_features": ["午後潮熱", "盜汗", "口乾", "舌紅少苔"],
      "conflicting_features": [],
      "missing_features": ["脈象", "五心煩熱是否存在"]
    },
    {
      "name": "肝腎陰虛",
      "supporting_features": ["潮熱", "盜汗", "舌紅少苔"],
      "conflicting_features": [],
      "missing_features": ["腰膝酸軟", "耳鳴", "脈細"]
    }
  ]
}
```

### 9.2 Stage 2：證據化回答生成

LLM 不可直接亂推方。
它只能根據已檢索出的 evidence chunks 來寫：

* 目前最可能的是什麼
* 為什麼
* 哪些點仍不確定
* 下一步該問什麼

這樣模型就像法官寫判決書，
不是像網紅直播即興猜答案。

---

## 10. PostgreSQL / Supabase 資料架構建議

以 **PostgreSQL + pgvector + JSONB + FTS** 為核心。

### 10.1 建議主要資料表

#### `knowledge_atoms`

最小知識原子表，欄位建議：

* `id`
* `atom_type`（symptom / sign / tongue / pulse / pattern / treatment / formula / herb / citation / case）
* `title`
* `canonical_name`
* `aliases` jsonb
* `domain`
* `subcategory`
* `body_markdown`
* `embedding_text`
* `embedding` vector
* `search_vector` tsvector
* `source_id`
* `source_ref`
* `metadata` jsonb
* `quality_score`
* `authority_level`
* `created_at`
* `updated_at`

#### `pattern_relations`

證型關係表：

* `from_atom_id`
* `relation_type`
* `to_atom_id`
* `weight`
* `evidence_ref`

#### `diagnostic_rules`

半結構化規則表：

* 若 `自汗 + 畏風 + 氣短 + 舌淡`，則 `衛氣不固` 權重 +0.25
* 若 `盜汗 + 舌紅少苔 + 脈細數`，則 `陰虛內熱` 權重 +0.35

#### `source_documents`

來源文件表：書名、章節、URL、出版資訊、權威度、版權標記

#### `case_records`

醫案表：case summary、extracted features、final pattern、formula、outcome、source

---

## 11. RAG 回答格式設計

### 11.1 建議回應骨架

#### A. 症狀摘要

把使用者輸入重新結構化

#### B. 候選證型

列出前 3 名，不超過 3 個

#### C. 支持依據

逐條列：哪個症狀支持、哪個舌脈支持、來自哪個知識單元

#### D. 鑑別重點

列出與次佳候選的差異

#### E. 尚缺資訊

例如：是否口苦？是否畏寒？舌苔厚膩或少苔？脈是弦、滑、細、數？

#### F. 參考治法方向

只給方向，不直接武斷處方

#### G. 來源引用

書名 / 條目 / URL

---

## 12. 評估指標

### 12.1 Retrieval 指標

* **Recall@k**：正確證型相關 chunk 是否能被召回
* **Evidence Coverage**：是否覆蓋主症、兼症、舌象、脈象、病機
* **Conflict Awareness**：模型是否有指出互斥訊號

### 12.2 Diagnostic Ranking 指標

* **Top-1 Pattern Accuracy**：第一名候選是否正確
* **Top-3 Pattern Coverage**：前三名是否包含正解
* **Differential Diagnosis Quality**：是否真的有說出「A 與 B 差在哪」

### 12.3 Safety 指標

* **Unsupported Assertion Rate**：回答中有多少句子沒有 evidence 支撐
* **Over-Prescription Rate**：在資訊不足時，是否過早推薦具體方藥
* **Missing-Critical-Question Rate**：是否漏問關鍵補充問題

---

## 13. 安全治理

### 13.1 禁止的行為

系統不應：

* 只靠單一症狀下定論
* 在資訊不足時直接下唯一證型
* 未檢索到支持證據時編造典籍說法
* 將模糊用語硬翻成明確病名
* 直接給高風險治療建議而不標示不確定性

### 13.2 必須的行為

系統應：

* 標示候選而非絕對診斷
* 顯示支持證據與反證
* 指出尚缺資料
* 區分「教材結論」與「醫案經驗」
* 區分「知識檢索」與「臨床決策」

---

## 14. 醫砭資料源的工程價值

從 RAG 工程角度看，醫砭的《中醫症狀鑒別診斷學》很有價值，
不是因為它「有名」，而是因為它 **可切、可標、可索引**。

### 14.1 它已有目錄層級

* 內科症狀、婦科症狀、兒科症狀、各部位分類
* 對 metadata 生成非常友善

### 14.2 單頁是單症狀

如「呵欠」「健忘」「善恐」這類條目，本身就接近一個 atomic diagnostic unit。

### 14.3 單頁內部結構清楚

許多頁面可見「概念」「常見證候」等標記，這很適合 parser 自動拆段。

換句話說，它不像一坨掃描 PDF，比較像已經幫你做過一半前處理的知識網站。

---

## 15. 建議實作路線

### Phase 1：最小可用版

目標：先做「症狀 → 候選證型 → 證據引用」

**內容**：

* 只接 L1 結構化資料源
* 先不碰全部經典
* 先做：symptom atoms / pattern atoms / tongue-pulse atoms / relations
* 檢索採：PostgreSQL FTS + pgvector + 簡單 rerank

**可交付**：

* 知識庫 schema
* scraper / parser
* embedding pipeline
* query API
* 基本診斷回答模板

### Phase 2：進階辨證版

目標：加入「反證」與「鑑別診斷」

**內容**：

* 增加 diagnostic_rules
* 增加 conflict logic
* 增加 top-3 pattern ranking
* 增加補問問題生成

### Phase 3：經典與醫案融合版

目標：從教材型 RAG 升級為研究型 RAG

**內容**：

* 接入《傷寒論》《金匱要略》
* 加入醫案
* 加入 source weighting
* 區分：教材共識 / 經典原文 / 醫案經驗

---

## 16. 一個具體範例

### 使用者輸入

> 容易自汗，吹風怕冷，精神疲倦，講話比較沒力，舌淡，脈虛。

### 系統流程

#### Step 1：特徵抽取

* symptom: 自汗
* sign: 畏風
* sign: 神疲
* sign: 語弱
* tongue: 舌淡
* pulse: 脈虛

#### Step 2：候選證型

* 衛氣不固
* 肺氣虛
* 脾肺氣虛

#### Step 3：證據裝配

* 自汗 + 畏風 → 表虛不固
* 神疲 + 語弱 + 舌淡 + 脈虛 → 氣虛傾向
* 無盜汗、無午後潮熱 → 不支持陰虛內熱

#### Step 4：輸出

系統回答不說：

> 你就是玉屏風散證。

而是說：

> 目前較符合「衛氣不固／肺氣虛」路徑。支持點是自汗、畏風、神疲、語弱、舌淡、脈虛。
> 若要與脾肺氣虛進一步區分，仍需補問食少、便溏、腹脹等訊號。

這就對了。因為它是在做 **可解釋辨證輔助**，不是在裝神醫。

---

## 17. 結論

中醫診斷 RAG 的核心不是「把古籍向量化」，而是：

> **把辨證過程轉成可檢索、可排序、可解釋、可反駁的知識系統。**

### 總架構一句話

**Ontology-first + Hybrid Retrieval + Evidence-based Generation**

也就是：

1. **先建立中醫知識本體**
2. **再把資料切成可診斷原子**
3. **用 PostgreSQL 同時承接結構化、全文檢索、向量檢索**
4. **用規則與反證機制約束 LLM**
5. **最後輸出帶來源、帶鑑別、帶不確定性的答案**

這樣做出來的系統，才不會只是「很會講中醫」，
而是比較接近：

**會整理中醫證據、會保留不確定性、會幫人縮小辨證範圍的知識引擎。**

---

## 18. 後續文件

1. `docs/adr/ADR-001-tcm-rag-architecture.md`
2. `spec/tcm-rag-system-spec.md`
3. `sql/tcm-rag.schema.sql`
4. `sql/tcm-rag.seed.sql`
5. `schemas/knowledge-atom.schema.json`
6. `scripts/embed_atoms.py`

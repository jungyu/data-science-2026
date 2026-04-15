# ADR-001: TCM Diagnostic RAG Architecture

**狀態**：Accepted
**日期**：2026-04-15
**決策者**：jungyu
**對應 Spec**：spec/tcm-rag-system-spec.md

---

## 脈絡與問題

建構中醫診斷輔助系統時，面臨的核心技術問題是：

**中醫辨證不是單一關鍵字比對，而是多訊號、跨層級、帶矛盾消解的推理過程。**

一般 RAG 架構（向量化文本 + LLM 生成）對中醫診斷場景有以下缺陷：

1. **語意相似 ≠ 辨證正確**：embedding 相似的症狀組合未必指向相同證型
2. **無法表達衝突訊號**：盜汗可支持陰虛，但若同時畏寒，則需鑑別
3. **生成幻覺率高**：LLM 在缺少結構約束時容易自由腦補診斷結論
4. **無可引用依據**：回答缺少可回溯的知識來源

---

## 決策

採用 **Ontology-first + Hybrid Retrieval + Evidence-based Generation** 三層架構。

### 核心決策點

#### 1. 知識原子（Knowledge Atom）為最小可索引單位

不採用固定長度 chunk，改以語義完整的知識單元作為基本粒度：

* symptom / sign / tongue_feature / pulse_feature
* pattern / pathomechanism
* treatment_principle / formula / herb
* citation / case

**原因**：中醫診斷單元的語義邊界不對齊字數邊界。固定長度切割會破壞辨證脈絡的完整性。

#### 2. PostgreSQL 作為唯一儲存後端

採用 PostgreSQL 15+ with pgvector，整合：

* `vector` column for embedding search（語義召回）
* `tsvector` / `tsquery` for FTS（術語精確命中）
* `JSONB` for metadata（結構化過濾）
* FK + `atom_relations` table for graph expansion（關聯展開）

**原因**：避免多資料庫維運成本。中醫查詢的四種型態（症狀敘述、術語查詢、鑑別診斷、經典佐證）可在同一個 PostgreSQL 執行個體中完整支援。

#### 3. 關係表承載辨證圖譜

`atom_relations` 表儲存如：

* `症狀 suggests 證型`（weight: 0.3~0.7）
* `舌象 strongly_strengthens 證型`（weight: 0.8~0.95）
* `症狀 conflicts_with 證型`（衝突扣分）

**原因**：讓系統能做「支持證據」與「反證排除」，而不只是找相似。

#### 4. 診斷規則以 JSONB 儲存（MVP 階段）

`diagnostic_rules` 表的 `conditions` / `actions` 欄位先採 JSONB，不急著設計 DSL。

**原因**：MVP 階段規則數量少，JSONB 彈性足夠。待規則數達 50~100 條後再考慮抽象 rule language。

#### 5. 生成分兩段進行

* **Stage 1**：結構化候選生成（受限輸出）
* **Stage 2**：基於 evidence chunks 的文字生成

**原因**：避免 LLM 在缺乏檢索支撐的情況下直接生成診斷斷言。模型扮演「法官寫判決書」而非「即興猜答案」。

---

## 被拒絕的方案

### 方案 A：純向量 RAG

* **問題**：無法表達衝突訊號，無法做鑑別診斷，幻覺率高
* **結論**：拒絕

### 方案 B：Neo4j + 向量混合

* **問題**：增加圖資料庫維運成本，且 PostgreSQL + atom_relations 可達到同等效果
* **結論**：Phase 3 後可考慮，MVP 不採用

### 方案 C：LangChain 標準 RAG Pipeline

* **問題**：對中醫結構化特徵的 query normalization 支援不足，reranking 邏輯無法自定義
* **結論**：可作為部分工具使用，但不作為主架構依賴

---

## 後果

### 正面影響

* 辨證結果可附帶引用來源，可回溯
* 支持衝突訊號偵測與鑑別診斷輸出
* PostgreSQL 統一儲存，Supabase 相容，維運簡單
* 知識原子結構可支援後續 rule engine 強化與 graph DB 遷移

### 負面影響與風險

* ingestion pipeline 較複雜（需 parser + atom extractor + relation extractor）
* 初期知識庫覆蓋率有限，召回率依賴資料量
* diagnostic_rules 的 JSONB 格式在規則複雜化後需要 migration

### 緩解措施

* Phase 1 限縮資料源至 L1 結構化百科層（醫砭）
* MVP 先不做 relation extraction，手工 seed 少量關係
* JSONB rules 預留 `rule_code` unique key，便於後期遷移

---

## 相關文件

* [白皮書](../whitepaper/tcm-rag-whitepaper.md)
* [System Spec](../../spec/tcm-rag-system-spec.md)
* [Schema SQL](../../sql/tcm-rag.schema.sql)
* [Knowledge Atom Schema](../../schemas/knowledge-atom.schema.json)

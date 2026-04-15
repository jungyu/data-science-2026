# 八字解盤 RAG 系統白皮書

## 以「命盤結構 → 規則先行 → 文獻接地」為主軸的可解釋檢索增強生成架構

- Version: 1.0
- Date: 2026-04-15
- Project: `project-destiny`

---

## 1. 摘要

建構八字解盤 RAG，不是把《子平真詮》《滴天髓》《三命通會》丟進向量資料庫就結束。
真正的難點在於：**八字推理不是自然語言問答，而是高維符號系統的結構化推導**。

八字查詢的輸入不是一段話，而是由四柱、干支、藏干、十神、月令、刑沖合害、格局、調候等多個維度構成的結構化命盤。它的問題長得更像一個**邏輯程式的執行 trace**，而不是一段 FAQ 檢索。

如果照著通用 RAG 教科書做，很快會遇到四個症狀：

1. **向量相似但命理錯誤**：「甲木生於子月」與「甲木生於午月」語意相近，命理判讀方向卻完全不同
2. **條件組合被切碎**：「傷官見官」不是單一詞彙匹配，而是條件組合成立才有意義；chunking 時常被切到兩個片段
3. **規則與描述混為一談**：古籍中「論正官」同一章夾雜定義、條件、案例、反例，embedding 難以區分
4. **LLM 流暢但沒根據**：沒有結構化先驗，模型很容易拼接出「讀起來像命理分析」但經不起核對的敘事

因此，本系統主張：

> **八字 RAG 必須採「確定性排盤 + 規則先行 + 知識原子化 + 混合檢索 + 可追溯生成」的五層架構**，而不是只做 embedding search。

---

## 2. 問題定義

### 2.1 一般 RAG 為什麼不夠

假設使用者輸入：

> 1990 年 8 月 15 日下午 2:30 出生於台北，男。

通用 RAG 的做法：把這句話丟進 embedding → 在古籍資料庫做 top-k cosine → 交給 LLM 生成。

會發生什麼事？

- 這句話的**命理結構為零**：沒有四柱、沒有日主、沒有月令
- embedding 最接近的古文可能是「論出生時辰」之類的**定義性段落**，而不是**實際適用於此命盤的規則**
- LLM 只能靠語言流暢度填補，幻覺率必然高

正確的做法是：先把「1990-08-15 14:30 @ 台北」**算成命盤**，再以命盤特徵去找文獻。

### 2.2 八字的推理不是語意相似，是條件匹配

舉個更具體的例子。使用者命盤如下：

- 日主：甲（陽木）
- 月令：申（金旺）
- 年時柱見庚、辛（官殺）
- 天干見丁（傷官）

這個命盤**應該命中**的知識是：

- 《子平真詮·論正官》正官格成立條件
- 《子平真詮·論傷官》傷官見官為禍
- 《子平真詮·論甲木》甲木性質

**不應該命中**（但語意很接近）的知識可能是：

- 《三命通會》論申月的泛論描述
- 某現代書的「八月份甲日生人運勢」白話文

差別在哪？差在「條件匹配度」而非「語意相似度」。

### 2.3 多條件並置被單 embedding 稀釋

八字查詢的典型結構是**多條件並置**：「甲木 + 申月 + 正官格 + 調候」。

若把這四個條件用 `" / ".join()` 拼成一個字串去 embed，各條件的語意訊號會互相稀釋，結果通常是：

- 高度相關但只命中單一條件的 atom（例如只講「甲木冬生調候」）被壓低
- 表面相似但條件不全對的 atom 擠進 Top-K
- 難以在日誌中定位「哪條條件貢獻了這次命中」

這是本系統後來採用 **multi-seed + score fusion**（ADR-009）的直接原因。

---

## 3. 系統定位

本系統不是「自動命理師」，而是：

### 3.1 系統目標

- 用於**八字知識檢索與解釋輔助**
- 用於**命盤特徵的結構化推導**
- 用於**格局候選的文獻佐證整理**
- 用於**教學、研究、術數數位化**
- 回答時必須能指出：
  - 為何傾向某格局
  - 為何排除某格局
  - 依據出自何書、何章、何知識原子

### 3.2 系統邊界

- **是**：知識檢索與推理輔助系統
- **不是**：自動命理判讀系統
- **不是**：吉凶宿命論斷系統
- **不是**：人生建議聊天機器人

換句話說，它回答的是：

> 「依據此命盤特徵，哪些文獻與規則適用？為什麼？還有哪些判斷信心不足？」

而不是：

> 「你這輩子注定發財/破產/離婚。」

這個邊界寫在每次 LLM 輸出的「不確定處」章節，且此章節永不可為空。

---

## 4. 核心設計原則

本系統的三層防呆骨架：

### 4.1 原則一：確定性排盤不交給 LLM

排盤是**數學問題**，不是語言問題。節氣、時區、真太陽時、曆法切換都有明確演算法，交給機率模型重新推導會引入不必要的錯誤。

本系統採獨立的 `Bazi Engine` 模組（ADR-003），包裝成熟的 `lunar-python` 函式庫，保證：

- 公曆 / 農曆 / 節氣換算可驗證
- 真太陽時計算可對照（120°E 基準，每度 4 分鐘）
- 四柱、藏干、十神皆為結構化 JSON 輸出

LLM 只讀這份 JSON，不得自行改寫。

### 4.2 原則二：規則引擎先於生成層

若直接把命盤 + 文獻片段交給 LLM，模型會根據局部語意拼接敘事，常見失誤：

- 忽略月令優先
- 混淆成格與破格
- 把描述當成規則
- 用話術掩蓋不確定性

本系統採 `Rule Engine`（ADR-005）**先**解析命盤，產出：

- 身強弱初判
- 格局候選（以月令透干為主）
- 調候需求
- 刑沖合害摘要
- 風險旗標
- Retrieval query seeds

LLM 收到的不是原始命盤，而是已經過規則判定的結構化結果。

### 4.3 原則三：結果必須 grounded 且可追溯

生成階段規定（ADR-008）：

1. 每個主要結論必須對應至少一項證據來源
2. 必須區分「規則判定」「文獻引述」「解釋說明」三類內容
3. 證據不足時必須顯示不確定性，不可自動補完
4. 引用古文必須逐字使用傳入的 atom 原文，不得改寫

這三條在 LLM 的 system prompt 中是 **hard constraints**，並由 Layer D（LLM-as-judge）自動檢查。

---

## 5. 資料源策略

不同著作在八字體系中扮演不同角色，若視為同權會導致生成結果缺乏骨幹（ADR-002）。

### 5.1 資料分層

| Priority | 著作 | 角色 | 用途 |
|---|---|---|---|
| 1 | 子平真詮 | 主骨架 | 格局、強弱、用神的理論基礎 |
| 1.5 | 滴天髓 | 高階修正 | 氣象、變格、神韻補充 |
| 2 | 三命通會 | 描述性擴展 | 案例對照與 lookup |
| 3 | 千里命稿 | 現代語境 | 白話化表達與映射 |
| 4+ | 其他現代 / 網路資料 | 參考 | 不作核心依據 |

每筆知識原子帶 `source_priority`，檢索重排時作為重要權重因子。

### 5.2 為什麼需要權威層級

古籍之間觀點並不總是一致。例如：

- 《子平真詮》偏重「月令透干定格局」
- 《滴天髓》更重「氣象與調候」
- 《三命通會》則是大量案例與描述

如果所有來源同權，LLM 遇到衝突時會把三家觀點混為一談，輸出「讀起來像命理分析」但沒有主軸的敘事。

設定權威層級等於告訴系統：**遇到衝突，先相信子平真詮**。

---

## 6. 知識本體設計

這一段是整個系統的骨架。沒有 ontology，RAG 只是在撈字。有 ontology，RAG 才是在跑結構化推理。

### 6.1 Knowledge Atom —— 最小可引用單位

通用 RAG 常用固定長度 chunking（500 tokens / 一個段落 / 一頁）。這對八字文獻是災難。

八字知識的有效檢索單位不是**頁**，也不是**段**，而是「**一個可獨立成立的命理命題**」，例如：

- 甲木冬生的調候論
- 正官格成立條件
- 傷官見官的成局與為禍條件
- 身強財旺的判定邏輯

每個 chunk 必須盡量滿足：

1. 主題單一
2. 邏輯邊界清楚
3. 可以被標註標籤
4. 可以抽出條件
5. 可以被獨立引用

本系統稱此單位為 **Knowledge Atom**（ADR-006）。

### 6.2 多重表徵

單一文本形式無法同時滿足檢索、生成、驗證需求。每個 atom 採三層表徵（ADR-004）：

**原文層**

- `original_text` —— 保留古文，作為最終引用依據

**語意層**

- `modern_interpretation` —— 現代語意轉述
- `embedding_text` —— 為向量化優化的拼接文本（術語 + 概念）

**結構層**

- `normalized_tags` —— 標準化標籤（受控詞彙表）
- `logic_type` —— 邏輯用途枚舉（pattern_definition / strength_assessment / ...）
- `conditions` —— 結構化條件表示
- `day_master_tags` / `month_branch_tags` / `pattern_tags` / `seasonal_tags` —— 高頻過濾欄位

### 6.3 範例

一筆實際 atom：

```json
{
  "atom_code": "ziping-jia-001",
  "source_book": "子平真詮",
  "source_priority": 1,
  "chapter": "論甲木",
  "title": "甲木冬生調候",
  "original_text": "甲木參天，脫胎要火。",
  "modern_interpretation": "甲木如高大樹木，寒濕過重時需火調候。",
  "embedding_text": "甲木 冬季 寒濕 調候 火 日主特性",
  "normalized_tags": ["甲木", "調候", "火", "冬季", "日主特性"],
  "logic_type": ["day_master_nature", "seasonal_adjustment"],
  "conditions": [
    {"field": "day_master", "operator": "eq", "value": "甲"},
    {"field": "season", "operator": "in", "value": ["winter", "late_autumn"]}
  ],
  "day_master_tags": ["甲"],
  "month_branch_tags": ["子", "亥"],
  "seasonal_tags": ["winter", "late_autumn"]
}
```

`original_text` 給引用、`embedding_text` 給向量搜尋、`conditions` 給規則引擎、`*_tags` 給 metadata filter。

### 6.4 Knowledge Graph —— 輕量圖譜

Atom 之間存在明確關係：

- `supports` —— 支撐同一結論
- `contradicts` —— 理論衝突（例如「正官格成立」vs「傷官見官破格」）
- `extends` —— 擴展補充
- `cites` —— 引用關係
- `applies_to` —— 條件適用

第一階段不引入 Neo4j，用 PostgreSQL 關係表 `knowledge_relations` 模擬圖譜（ADR-007）。待規模與查詢需求驗證後再考慮升級。

---

## 7. ETL 策略

### 7.1 半自動標註流程

直接讓人工把整本子平真詮標註成 atom 不切實際。本系統採 **LLM 輔助標註 + 人工覆核** 的半自動流程（Spec-003a）：

1. 人工或腳本做 **初步 chunking**（按章節或命題邊界切開）
2. LLM 依受控詞彙表 + schema 產出 atom JSON 初稿
3. 程式 **schema 驗證**（必填欄位、枚舉值、條件欄位白名單）
4. 通過驗證者以 `status='draft'` 寫入 DB
5. **人工覆核** 條件抽取與標籤正確性
6. 升級為 `status='active'` 後跑 embedding 回填

### 7.2 受控詞彙表

LLM 標註時，`normalized_tags` 必須從固定詞彙表選擇：

- 天干：甲乙丙丁戊己庚辛壬癸
- 地支：子丑寅卯辰巳午未申酉戌亥
- 十神：比肩、劫財、食神、傷官、偏財、正財、七殺、正官、偏印、正印
- 格局：正官格、七殺格、正財格、偏財格、正印格、偏印格、食神格、傷官格、比劫格、建祿格、陽刃格
- 主題：調候、用神、身強、身弱、制化、破格、變格、秀氣、貴氣、日主性質
- 關係：沖、合、刑、害、破、三會、三合

`conditions.field` 則限定為 `Bazi Engine` 輸出的欄位白名單。這兩個約束讓 LLM 無法「發明」新術語，所有標註都能被下游規則引擎與 schema 檢查接住。

### 7.3 Embedding 策略

- 模型：`text-embedding-3-small`（1536 維）
- 距離：cosine
- 索引：HNSW（`vector_cosine_ops`）
- 回填時機：atom `status` 升級為 `active` 後觸發 `backfill-embeddings` 指令

選擇 1536 維而非 3072 維的理由：實測下對古文術語的召回差異有限，但儲存與運算成本差一倍；若未來發現性能瓶頸可再升級（需 migration）。

---

## 8. 混合檢索策略

八字查詢的本質是**多條件並置**，單純向量搜尋無法精確處理。本系統採四路混合（ADR-001）：

### 8.1 四條檢索路徑

| 路徑 | 用途 | 技術 |
|---|---|---|
| Symbolic | 嚴格條件匹配（格局候選、刑沖合害） | `conditions` jsonb GIN index |
| Metadata | 標籤過濾（日主、月令、格局） | `*_tags` array GIN index |
| Vector | 語義近似描述 | pgvector HNSW cosine |
| Graph | 關係擴展（supports / contradicts） | `knowledge_relations` JOIN |

第一階段已實裝 Symbolic + Metadata + Vector，Graph 作為第二階段增強。

### 8.2 Multi-seed Query Expansion（ADR-009）

Rule Engine 產出的 `retrieval_query_seeds` 通常涵蓋 3–5 個維度，例如：

```python
[
  "甲 申月",
  "甲 申月 正官格",
  "甲 autumn 調候 火",
  "子午沖",
]
```

每條 seed **獨立向量化**、**獨立檢索**，再以 score fusion 合併。這樣可避免單 embedding 稀釋多條件訊號。

Fusion 策略有三：

- **max**（預設）：取 atom 在所有 seed 中的最高分數
- **mean**：對未命中的 seed 計 0，偏好多路共識
- **rrf**（Reciprocal Rank Fusion）：`Σ 1/(k + rank_i)`，鈍化極端分數

此外，Hit 紀錄 `hit_seed_count` 與 `top_seed`，讓檢索日誌可追溯「哪條 seed 實際命中了哪個 atom」。

### 8.3 三段式檢索管線

```
命盤 → Rule Engine → query_seeds
                          │
                          ▼
         ┌─ Query Expansion（每 seed 獨立 embed）─┐
         │                                        │
    per-seed:                                     │
    ① metadata filter（縮小候選池）               │
    ② pgvector HNSW cosine（語義召回）            │
    ③ SQL rerank（加權 rerank）                   │
                          │                       │
                          ▼                       │
                    Score Fusion ─────────────────┘
                          │
                          ▼
                        Top-K
```

**關鍵差異**：不是直接 `ORDER BY embedding <=> query`，而是**先 filter 再 vector 再 rerank**。這個順序是本系統檢索品質的主要來源。

### 8.4 SQL Rerank 權重

最終分數 = `vector_score × 0.45 + source_priority × 0.20 + symbolic_match × 0.20 + metadata_overlap × 0.15`

權重可實驗調整，每次變更需記錄版本並跑評估集。

### 8.5 為何不引入 BM25

通用 RAG 教材常建議向量 + BM25 混合。本系統**暫不採用**，理由：

- pgvector 本身不提供 BM25
- 引入 `pg_trgm` 或 `tsvector` 會增加維護成本
- 本系統已有 `normalized_tags` + 高頻標籤欄位作為 symbolic filter，邊際收益有限

列為 Phase 3 候選，視評估結果再決定。

---

## 9. 規則引擎

### 9.1 為什麼需要規則引擎

八字推理有**明顯先後順序**：

1. 排盤（Bazi Engine）
2. 強弱判定
3. 格局候選
4. 調候需求
5. 沖合刑害
6. 文獻佐證
7. 綜合解釋

若直接跳到第 6 步，前五步的結構先驗會全部遺失。LLM 會忽略月令優先、混淆破格、用話術掩蓋不確定性。

Rule Engine 就是把 1–5 步做成確定性 pipeline，產出結構化中介輸出，再交給後續層使用（Spec-005）。

### 9.2 規則層級

| 層級 | 內容 | 實作 |
|---|---|---|
| Level 1 硬規則 | 四柱關係、藏干展開、十神映射 | `rule_engine._ten_god()` |
| Level 2 骨架規則 | 身強弱、格局候選、調候方向 | `_assess_strength()`、`_candidate_patterns()` |
| Level 3 高階規則 | 破格、變格、優先序衝突 | Phase 2 再補 |

### 9.3 沖合刑害偵測

獨立模組 `conflicts.py` 處理地支關係：

- **六沖**：子午、丑未、寅申、卯酉、辰戌、巳亥
- **六合**：子丑、寅亥、卯戌、辰酉、巳申、午未
- **三刑**：寅巳申（無恩之刑）、丑戌未（恃勢之刑）、子卯（無禮之刑）
- **自刑**：辰辰、午午、酉酉、亥亥

日支涉及的沖標記 `impact=high` 並掛 `日月沖_XY` 風險旗標，檢索時會透過 `query_seeds` 召回相關文獻。

### 9.4 Query Seeds 的生成

Rule Engine 最重要的**對外輸出**之一是 `retrieval_query_seeds`。它不是直接把命盤資訊拼起來，而是：

- 為每個候選格局產一條 seed（`"甲 申月 正官格"`）
- 為調候需求產一條（`"甲 autumn 調候 火"`）
- 為每個刑沖合害產一條（`"子午沖"`）

這些 seed 設計成**檢索友善的短字串**，對應到 atom 的 `embedding_text` 風格，提升命中率。

---

## 10. 生成編排器與可追溯性

### 10.1 六區段強制格式

LLM 輸出採嚴格六區段格式（Spec-007）：

```
## 命盤結構摘要
## 核心判斷
## 依據文獻
## 規則說明
## 綜合解釋
## 不確定處
```

「不確定處」章節永不可為空 —— 系統必須誠實標示限制，不能寫「無」來混過去。

### 10.2 Prompt 結構

三段式 prompt：

**System Block**（使用 `cache_control: ephemeral`，跨請求快取省 tokens）

- 角色定義
- 絕對規則（只能引用傳入 atom、不改寫古文、不自創結論）
- 六區段輸出格式

**Context Block**

- 命盤資料（結構化摘要）
- 規則判定結果
- 相關文獻（含 atom_code、source、original_text、interpretation）

**User Instruction**

- 「請依照 system 規定輸出解盤分析」

### 10.3 Grounded Constraint

LLM 只能引用傳入的 `atom_code`。自創引用、改寫古文、跨來源硬拼矛盾結論都視為幻覺。這個約束由兩層檢查：

1. **Prompt 層**：system prompt 明示禁止
2. **審查層**：Layer D LLM-as-judge 逐條檢查引用是否逐字來自傳入 atom

---

## 11. 評估框架

系統好壞不是「讀起來像不像命理」，而是**可測量**（ADR-008、Spec-009）。

### 11.1 四層指標

| Layer | 指標 | 自動化 |
|---|---|---|
| A 排盤正確性 | 四柱 / 藏干 / 十神比對 | ✓ |
| B 規則正確性 | 格局候選命中、強弱判定 | ✓ |
| C 檢索品質 | Top-K 命中率、骨架文獻覆蓋率 | ✓ |
| D 生成品質 | Grounded、引用正確、幻覺率 | ✓（LLM-as-judge）|

### 11.2 Layer D LLM-as-judge

用獨立 Claude 呼叫對生成輸出四維度打分（0–10）：

- `groundedness` —— 結論是否都有依據
- `citation_fidelity` —— 引用是否逐字來自傳入 atom
- `format_completeness` —— 六區段是否齊全
- `uncertainty_honesty` —— 「不確定處」是否誠實標示

通過閾值：`groundedness ≥ 7` 且其他三項 `≥ 6`。

### 11.3 黃金案例集

目前 6 筆代表性案例，Phase 1 目標 30 筆（涵蓋 10 日主 × 3 代表季節）。每筆包含：

- 出生輸入
- 期望命盤（day_master / month_commander / season）
- 期望規則輸出（candidate_patterns / strength）
- 期望命中 atom_code 清單
- 期望引用書目

### 11.4 評估頻率

- 每次 schema 變更後執行完整評估
- 每次新增批量 atoms 後跑 Layer C
- 每次 prompt 調整後跑 Layer D
- 每次融合權重調整後跑 Layer C + D

---

## 12. 儲存架構

### 12.1 Postgres + pgvector 單庫

第一階段不引入獨立向量庫或圖資料庫（ADR-007）。所有資料在同一個 PostgreSQL：

- `knowledge_atoms` —— 核心知識表（含 `vector(1536)` 欄位）
- `knowledge_relations` —— 輕量圖關係
- `rule_definitions` —— 規則版本化
- `bazi_charts` —— 排盤記錄
- `retrieval_logs` / `generation_logs` —— 過程追蹤
- `evaluation_cases` —— 黃金案例

### 12.2 索引策略

**B-tree / 複合**

- `(source_priority, source_book)` —— rerank 用
- `status` —— filter 用

**GIN (array)**

- `day_master_tags`、`month_branch_tags`、`pattern_tags`、`seasonal_tags`

**GIN (JSONB)**

- `normalized_tags`、`logic_type`、`conditions`

**pgvector HNSW**

- `embedding vector_cosine_ops`

這個索引組合讓「先 metadata filter 再 vector search」在一個 SQL function `match_knowledge_atoms()` 內完成，無需跨系統。

### 12.3 為何暫不拆分

通用架構建議會推薦「Postgres + Pinecone + Neo4j」三件套。本系統第一階段刻意不拆：

- 單庫易維運、易備份、易回歸測試
- 資料量尚未驗證拆分必要性
- 拆分後的跨系統一致性問題高於單庫查詢複雜度

當資料規模證明需要時再演進。

---

## 13. Agentic 邊界的刻意選擇

通用 RAG 教材常主張「LLM 自主決定是否檢索、如何檢索、是否重試」的 agentic 模式。本系統**刻意不採用**（ADR-009）。

### 13.1 為什麼不

| 通用 agentic 模式 | 本系統為何不採用 |
|---|---|
| LLM 自行決定是否檢索 | 排盤與格局判定是確定性計算，交給機率模型會引入不必要風險 |
| 多輪 think-act-observe | 命理推理有嚴格先後順序，亂序會破壞可追溯性 |
| LLM 直接呼叫 tools | Bazi Engine / Rule Engine 是前置 pipeline，不是可呼叫工具 |

### 13.2 採用的「受限 agentic」成分

| 成分 | 位置 |
|---|---|
| Query Expansion（多 seed 分路） | `retrieve_multi_seed()` |
| Score Fusion | 同上 |
| Grounded Constraint（只能引傳入 atom） | `generation._SYSTEM_PROMPT` |
| Layer D 自審 | `judge.judge_output()` |

### 13.3 未來可評估

- **不確定性回溯檢索**：若 Rule Engine 信心低，自動用更寬鬆的 seeds 再檢索一次（由規則觸發，不由 LLM 決策）
- **Graph Retrieval 二階展開**：從已命中 atom 用 `supports/contradicts` 邊擴展

### 13.4 絕對不採用

- LLM 自行呼叫 Bazi Engine（排盤必須 deterministic）
- LLM 決定跳過檢索直接回答（grounded 不可妥協）
- 基於對話歷史的動態策略切換（命盤查詢為無狀態）

---

## 14. 系統資料流

完整端到端：

```
使用者輸入（出生時間、時區、地點）
    ↓
Input Normalizer
    ↓
Bazi Engine（lunar-python 包裝 → 結構化 JSON）
    ↓
Rule Engine（強弱 / 格局 / 調候 / 沖刑 / query_seeds）
    ↓
Retrieval Orchestrator
  ├─ Query Expansion（每 seed 獨立 embed）
  ├─ per-seed: metadata filter → pgvector HNSW → SQL rerank
  └─ Score Fusion（max / mean / rrf）
    ↓
Generation Orchestrator（Claude + prompt caching + grounded constraint）
    ↓
六區段 grounded output
    ↓
Layer D LLM-as-judge（可選）
    ↓
Retrieval / Generation logs 寫回 DB
```

任何一步的輸入輸出都可在 DB 中追溯，提供除錯與回歸測試基礎。

---

## 15. 交付路線圖

| Phase | 目標 | 狀態 |
|---|---|---|
| 0 核心原型 | Bazi Engine MVP、15 筆 atoms、基本 RAG 閉環 | ✓ |
| 1 骨架可用版 | Multi-seed 檢索、Layer D 自動化、docker-compose、6 筆評估集 | ✓ |
| 2 擴展版 | 三命通會 50+ 筆、圖譜關係填充、評估集 30+ 筆、reranking 權重實驗 | 進行中 |
| 3 穩定化 | 規則版本管理、錯誤分析報表、regression suite、ETL 自動化 | 規劃中 |

### Phase 1 完成定義

- Top-5 骨架文獻命中率 ≥ 70%
- 排盤正確率 ≥ 95%（邊界案例集）
- 幻覺率 ≤ 15%（人工抽樣 20 筆）
- 一鍵 `docker compose up` 可啟動全套環境

---

## 16. 與通用 RAG 教材的取捨對照

| 教材建議 | 本系統立場 | 理由 |
|---|---|---|
| 固定 token chunking | 不採用，用 knowledge atom | 八字邏輯單位不以字數為邊界 |
| 單純向量檢索 | 不採用，用四路混合 | 符號系統必須條件匹配 |
| LLM 自主 agentic loop | 不採用，用 rule-first | 排盤是確定性計算，不應交機率模型 |
| 單 embedding + top-k | 不採用，用 multi-seed + fusion | 多條件語意會被稀釋 |
| BM25 + 向量混合 | 暫不採用（Phase 3 候選） | 已有 symbolic filter，邊際收益有限 |
| 獨立向量庫 | 不採用，用 pgvector | 單庫維運成本低 |
| RAGAS 四指標 | 參考採用，自訂四層 A/B/C/D | 需覆蓋排盤與規則正確性 |
| 固定 prompt 無快取 | 採用 prompt caching | 跨請求重複 system block |

---

## 17. 結語

八字 RAG 不是把文言文丟進向量庫就結束。

它的真正工程挑戰在於：

1. 如何讓**確定性計算**（排盤）與**機率模型**（LLM）各司其職
2. 如何讓**符號推理**（規則）與**語意檢索**（向量）協同
3. 如何讓**權威文獻**（子平真詮）與**補充描述**（三命通會）形成可解釋的知識層級
4. 如何讓**可讀的輸出**（LLM 生成）始終**可追溯**（atom_code 引用）

本系統的答案是五層架構：

> **確定性排盤 → 規則先行 → 知識原子化 → 混合檢索 → 可追溯生成**

這不是最炫的架構，但它是可以被測試、被回歸、被維運、被人工審查的架構。

在高風險知識系統中，**「可驗證」比「很會講」重要得多**。

---

## 附錄 A：關鍵文件索引

**架構決策**

- [ADR-001 混合式檢索策略](../adr/ADR-001-hybrid-retrieval-strategy.md)
- [ADR-002 文獻權重與權威層級](../adr/ADR-002-document-priority-and-authority.md)
- [ADR-003 確定性排盤模組](../adr/ADR-003-deterministic-bazi-chart-engine.md)
- [ADR-004 多重文本表徵法](../adr/ADR-004-text-representation-strategy.md)
- [ADR-005 規則引擎先於生成](../adr/ADR-005-rule-engine-before-generation.md)
- [ADR-006 知識原子化 chunking](../adr/ADR-006-knowledge-atom-chunking-strategy.md)
- [ADR-007 儲存架構](../adr/ADR-007-storage-architecture-postgres-pgvector-graph.md)
- [ADR-008 評估與 grounded generation](../adr/ADR-008-evaluation-and-grounded-generation.md)
- [ADR-009 Multi-seed 檢索與 agentic 邊界](../adr/ADR-009-multi-seed-retrieval-and-agentic-boundary.md)

**系統總覽**

- [bazi-rag-system-plan v0.2](../architecture/bazi-rag-system-plan.md)

**實作規格**

- [Spec-001 系統總覽](../specs/spec-001-system-overview.md)
- [Spec-002 Bazi Engine](../specs/spec-002-bazi-engine.md)
- [Spec-003 知識 ETL](../specs/spec-003-knowledge-etl.md)
- [Spec-003a ETL prompt 範本](../specs/spec-003a-etl-prompt-template.md)
- [Spec-004 Knowledge Atom Schema](../specs/spec-004-knowledge-atom-schema.md)
- [Spec-005 規則引擎](../specs/spec-005-rule-engine.md)
- [Spec-006 檢索管線](../specs/spec-006-retrieval-pipeline.md)
- [Spec-007 生成編排器](../specs/spec-007-generation-orchestrator.md)
- [Spec-008 儲存層](../specs/spec-008-storage-schema.md)
- [Spec-009 評估框架](../specs/spec-009-evaluation-framework.md)
- [Spec-010 API 契約](../specs/spec-010-api-contracts.md)
- [Spec-011 路線圖](../specs/spec-011-roadmap-and-deliverables.md)

## 附錄 B：術語對照

| 術語 | 英文 / 代稱 | 說明 |
|---|---|---|
| 知識原子 | Knowledge Atom | 最小可獨立引用的命理命題 |
| 規則引擎 | Rule Engine | 確定性產出命盤特徵與格局候選 |
| 檢索編排 | Retrieval Orchestrator | 多路召回 + fusion + rerank |
| 生成編排 | Generation Orchestrator | grounded LLM 生成 |
| 查詢種子 | Query Seeds | Rule Engine 產出的多個檢索維度字串 |
| 分數融合 | Score Fusion | max / mean / rrf 三種合併策略 |
| 可追溯性 | Traceability | 每個結論可回溯到 atom_code |
| 接地生成 | Grounded Generation | 只能引用傳入證據，不可自創 |

# 八字解盤 RAG 系統架構計畫

- Version: 0.2
- Status: Draft
- Last Updated: 2026-04-15
- 變更：v0.2 依 ADR-009 audit 結論更新 §3 檢索路徑圖與 §4.5 agentic 邊界章節

## 1. 系統定位

本系統不是一個通用聊天機器人加上命理知識庫的組合。

它的核心設計假設是：

> **八字命理是一套高結構化符號系統。**
> 正確解盤的前提不是語言模型有多聰明，而是排盤必須確定、規則必須先行、知識必須可計算。

LLM 在本系統中的角色不是「主推理者」，而是「有約束的口譯員」：
它負責把規則判定結果與文獻依據，轉述成可讀的自然語言。

## 2. 三層防呆骨架

### 第一層：確定性排盤
八字排盤是數學問題，不是語言問題。
絕對不允許 LLM 自行進行節氣換算、干支推算或十神映射。

見 ADR-003。

### 第二層：規則先行
規則引擎先產出「格局候選、強弱初判、調候需求、風險旗標」，
再交給 Retrieval 做知識召回，最後才讓 LLM 生成。

這樣可以避免「很會說，但沒根據」的問題。

見 ADR-005。

### 第三層：Grounded Generation
生成結果必須明確區分：規則判定、文獻引述、模型解釋。
當證據不足時，系統必須明示不確定性，而非自動補完。

見 ADR-008。

## 3. 核心模組關係

```
┌─────────────────────────────────────────────────────┐
│                   使用者輸入                          │
│           出生年月日時 + 時區 + 地點                   │
└───────────────────┬─────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────┐
│              Input Normalizer                        │
│         清洗格式、統一型別                             │
└───────────────────┬─────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────┐
│               Bazi Engine                            │
│    節氣換算 / 真太陽時 / 四柱 / 藏干 / 十神           │
│         輸出：chart_payload（結構化 JSON）             │
└───────────────────┬─────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────┐
│               Rule Engine                            │
│   強弱判定 / 格局候選 / 調候需求 / 刑沖合害 / 風險旗標  │
│   輸出：feature_payload + query_seeds (list[str])    │
└───────────────────┬─────────────────────────────────┘
                    │  seeds = [甲 申月, 甲 申月 正官格,
                    │            甲 autumn 調候 火, 子午沖, ...]
                    │
        ┌───────────┴───────────┐
        │ Query Expansion       │
        │ 每個 seed 獨立 embed   │
        │ (batch 一次 API 呼叫)  │
        └───────────┬───────────┘
                    │
       ┌────────────┼────────────┐
       │            │            │
       ▼            ▼            ▼
    seed_1       seed_2   ...  seed_N
       │            │            │
       ▼            ▼            ▼
  ┌────────────────────────────────┐
  │  per-seed:                     │
  │  metadata filter → pgvector    │
  │  HNSW cosine → SQL rerank      │
  │  (bazi.match_knowledge_atoms)  │
  └─────────────┬──────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────────┐
│           Retrieval Orchestrator                     │
│   Score Fusion (max / mean / RRF) / Top-K 輸出      │
│   追蹤：hit_seed_count, top_seed（可觀測性）         │
└───────────────────┬─────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────┐
│          Generation Orchestrator                     │
│    Prompt 組裝 / 證據整合 / 輸出格式約束              │
└───────────────────┬─────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────┐
│                   LLM                                │
│       grounded output（有來源、有結構、有限制）        │
└───────────────────┬─────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────────────────┐
│          Evaluation Service                          │
│     記錄 / 評分 / 回歸測試 / 問題分層定位             │
└─────────────────────────────────────────────────────┘
```

## 4. 知識層設計

知識不是「一段文章」，而是「一顆可計算的知識原子」。

每顆原子有三層：

| 層次 | 欄位 | 用途 |
|------|------|------|
| 原文層 | `original_text` | 權威引用依據 |
| 語意層 | `modern_interpretation`, `embedding_text` | 向量化與生成 |
| 結構層 | `normalized_tags`, `logic_type`, `conditions`, `*_tags` | 符號搜尋與規則映射 |

見 ADR-004, ADR-006, Spec-004。

## 4.5 Retrieval 策略的 Agentic 邊界

本節明確聲明本系統採用 **Rule-first + 受限補救檢索**，而非通用 RAG 教材常見的
「LLM-driven autonomous retrieval / agentic loop」。這不是妥協，而是因應八字領域特性的刻意選擇。

### 為何不採用 LLM 自主決策檢索

| 通用 agentic RAG 典型模式 | 本系統為何不採用 |
|--------------------------|----------------|
| LLM 讀查詢 → 自行決定是否/如何檢索 | 排盤與格局判定是**確定性計算**，交給機率模型會引入不必要風險 |
| 多輪 think-act-observe，動態重新計劃 | 命理推理有嚴格先後順序（排盤→規則→文獻），亂序會破壞可追溯性 |
| LLM 直接呼叫 tools（包括排盤、檢索） | LLM 不具 tool 層權限；Bazi Engine 與 Rule Engine 為前置 pipeline，不是可呼叫工具 |

### 本系統採用的「受限 agentic」成分

| 成分 | 說明 | 位置 |
|------|------|------|
| Query Expansion | Rule Engine 產出多個 `retrieval_query_seeds`，每個獨立向量化 | `retrieval.retrieve_multi_seed()` |
| Score Fusion | 多路結果以 max/mean/RRF 融合，非單一路徑 | 同上 |
| Grounded Constraint | LLM 只能引用傳入的 atom_code，自創引用視為幻覺 | `generation._SYSTEM_PROMPT` |
| Layer D 自審 | LLM-as-judge 獨立檢查生成品質 | `judge.judge_output()` |

### 未來可能納入（需評估）

1. **不確定性回溯檢索**（ADR-009 列 MEDIUM）
   若 `strength_assessment.confidence == "low"` 或無 candidate_patterns，自動以更寬鬆的 seeds 再檢索一次，**不交由 LLM 決策**，而是由確定性規則觸發。

2. **Graph Retrieval 二階展開**（ADR-001 Phase 2）
   以 `knowledge_relations` 從已命中 atom 展開 supports / contradicts 鄰居，作為補充證據。

### 絕對不採用

- LLM 自行呼叫 Bazi Engine 或 Rule Engine（排盤必須 deterministic）
- LLM 決定是否跳過檢索直接回答（grounded 不可妥協）
- 基於對話歷史的動態 retrieval strategy 切換（命盤查詢為無狀態）

## 5. 儲存策略

Phase 0 全部放 PostgreSQL + pgvector，不引入額外基礎設施。

- `bazi.knowledge_atoms`：核心知識表 + vector 欄位
- `bazi.knowledge_relations`：輕量圖關係
- `bazi.rule_definitions`：規則版本化管理
- `bazi.bazi_charts`：排盤記錄
- `bazi.retrieval_logs`：檢索過程追蹤
- `bazi.generation_logs`：生成過程追蹤
- `bazi.evaluation_cases`：黃金評估案例

見 ADR-007, Spec-008, `migrations/001_initial_schema.sql`。

## 6. 文獻優先序

| 層級 | 著作 | 角色 |
|------|------|------|
| 1 | 子平真詮 | 格局、強弱、用神主骨架 |
| 2 | 滴天髓 | 高階修正、氣象、變格補充 |
| 3 | 三命通會 | 描述性擴展、案例對照 |
| 4 | 千里命稿 | 現代語境映射 |
| 5+ | 其他 | 僅作參考 |

見 ADR-002。

## 7. 評估指標體系

| 層次 | 指標 |
|------|------|
| 排盤正確性 | 四柱 / 藏干 / 十神正確率 |
| 規則正確性 | 格局候選命中率 / 強弱準確率 |
| 檢索品質 | Top-K 命中率 / 骨架文獻覆蓋率 |
| 生成品質 | Grounded 比例 / 幻覺率 / 引用正確率 |

見 ADR-008, Spec-009。

## 8. 關鍵文件導覽

| 類型 | 路徑 |
|------|------|
| ADR 套件 | `docs/adr/` |
| Spec 套件 | `docs/specs/` |
| JSON Schema | `schemas/` |
| SQL Migration | `migrations/001_initial_schema.sql` |

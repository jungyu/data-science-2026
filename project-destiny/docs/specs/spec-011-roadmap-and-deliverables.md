# Spec-011: 交付階段與路線圖

- Status: Draft
- Owner: Product Architect
- Last Updated: 2026-04-14

## 1. 目的

定義系統從原型到第一版產品的交付階段與完成標準。

## 2. 整體原則

> 先求可驗證的閉環，再求功能完整。

每個 phase 結束前，系統必須能跑完一條完整路徑，不允許「做了一半」的 phase。

## 3. Phase 0: 核心原型

**目標**：一條能跑的閉環，不求完整，求可驗證。

### 交付物

| 項目 | 說明 |
|------|------|
| Bazi Engine MVP | 支援主要節氣與干支計算 |
| 知識 atoms 首批 | 子平真詮前 20 筆 |
| Schema 固化 | `knowledge_atoms` 表與索引 |
| Metadata retrieval | 基於 array / jsonb 過濾 |
| Rule Engine v0 | 格局候選初版 |
| 基本生成流程 | 能產出 grounded output |
| 5 筆評估案例 | 可執行驗收 |

### 完成定義
- 能對至少 5 個真實命盤輸出有來源的解盤
- 排盤結果可對照人工驗證
- 系統可回歸測試

## 4. Phase 1: 骨架可用版

**目標**：能穩定使用，可給測試使用者試用。

### 交付物

| 項目 | 說明 |
|------|------|
| Knowledge Atom schema 完整固化 | 含 conditions / relations |
| pgvector 索引上線 | HNSW + cosine |
| Retrieval fusion | 多路召回 + SQL rerank |
| Grounded generation format | 格式穩定 |
| 黃金案例集 v1 | 20 筆以上 |
| 評估 Layer A + B 自動化 | 排盤與規則自動回歸 |

### 完成定義
- Top-5 骨架文獻命中率 ≥ 70%
- 排盤正確率 ≥ 95%（邊界案例集）
- 幻覺率 ≤ 15%（人工抽樣 20 筆）

## 5. Phase 2: 擴展版

**目標**：增加知識廣度與評估深度。

### 交付物

| 項目 | 說明 |
|------|------|
| 三命通會導入 | 至少 50 筆原子 |
| 圖譜關係表 | knowledge_relations 填充 |
| Reranking 調優 | 權重實驗記錄 |
| 評估 Layer C + D | 檢索與生成品質指標 |
| Retrieval trace UI | 可查詢每次召回路徑 |

### 完成定義
- 各路由 recall@10 有明確記錄
- 生成 grounded 比例 ≥ 80%
- 幻覺率 ≤ 10%

## 6. Phase 3: 穩定化

**目標**：可長期維運，可持續演進。

### 交付物

| 項目 | 說明 |
|------|------|
| 規則版本管理 | rule_definitions 版本化 |
| 錯誤分析報表 | 可追蹤幻覺與漏召回 |
| Prompt snapshot logging | 每次生成留完整 prompt |
| Regression suite | Phase 0-2 案例全部可回歸 |
| ETL pipeline 自動化 | 新增文獻可半自動入庫 |

### 完成定義
- 所有歷史評估案例可回歸
- 新增文獻後 24h 內可完成入庫
- 每次 schema 變更前有 migration 計劃

## 7. 依賴 ADR

- 全部 ADR-001 到 ADR-008

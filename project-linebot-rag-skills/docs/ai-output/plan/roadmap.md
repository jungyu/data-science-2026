# 開發藍圖（穩健漸進式）

## 原則

1. **不破壞現有可運作的 bot**：每個 phase 結束後，bot 必須仍能正常收發訊息
2. **每個 phase 獨立可驗收**：不依賴下一個 phase 的功能
3. **優先補完半成品**：已有架構但邏輯空白的功能，比全新功能更優先
4. **MCP Server 不在此藍圖內**（ADR-006）

---

## Phase 概覽

| Phase | 名稱 | 主題 | 預估工時 | 依賴 |
|-------|------|------|---------|------|
| **P1** | 回應品質補完 | 讓 Response Mode 與 Emotion 真正影響回覆 | 1–2 天 | 無 |
| **P2** | 檢索品質提升 | Cross-encoder Rerank + Prompt Cache | 3–5 天 | P1 |
| **P3** | 知識庫擴充 | Notion 匯入 + Skill 熱更新 + 檢索分析 | 3–5 天 | P2 |
| **P4** | 智慧演化 | LangGraph Self-RAG + Reflection | 1–2 週 | P3 |

---

## Phase 1：回應品質補完

**目標**：現有架構的「半成品」真正落地，不需要新的外部依賴。

| 項目 | 規格 | 任務 |
|------|------|------|
| Response Mode 差異化 | [spec-01](../specs/spec-01-response-mode.md) | [task-01](../tasks/task-01-response-mode.md) |
| Emotion 應對策略 | [spec-02](../specs/spec-02-emotion-handling.md) | [task-02](../tasks/task-02-emotion-handling.md) |
| Heuristic Categories 同步 | [spec-03](../specs/spec-03-heuristic-sync.md) | [task-03](../tasks/task-03-heuristic-sync.md) |

**驗收標準**
- 傳「步驟說明」類問題 → bot 回覆明顯有序號分段
- 傳「我好焦慮」→ bot 回覆更簡短、只給一個下一步
- Heuristic fallback 的 category 清單與 Router prompt 完全一致

---

## Phase 2：檢索品質提升

**目標**：讓 RAG 回覆更準確、重複問題走快取。

| 項目 | 規格 | 任務 |
|------|------|------|
| Cross-encoder Rerank | [spec-04](../specs/spec-04-cross-encoder-rerank.md) | [task-04](../tasks/task-04-cross-encoder-rerank.md) |
| Prompt Cache | [spec-05](../specs/spec-05-prompt-cache.md) | [task-05](../tasks/task-05-prompt-cache.md) |
| Knowledge Version 追蹤 | [spec-06](../specs/spec-06-knowledge-version.md) | [task-06](../tasks/task-06-knowledge-version.md) |

**驗收標準**
- 同一個問題第二次問，回覆速度明顯加快（走快取）
- 知識庫更新後，舊快取自動失效
- 技術問題的 RAG 回覆與原始文件的相關性提升（主觀評估）

---

## Phase 3：知識庫擴充

**目標**：讓知識庫的來源更多元、技術人員能在不重啟的情況下更新 skill。

| 項目 | 規格 | 任務 |
|------|------|------|
| Notion Ingestion | [spec-07](../specs/spec-07-notion-ingestion.md) | [task-07](../tasks/task-07-notion-ingestion.md) |
| Skill 熱更新 | [spec-08](../specs/spec-08-skill-hot-reload.md) | [task-08](../tasks/task-08-skill-hot-reload.md) |
| Retrieval Log 分析 | [spec-09](../specs/spec-09-retrieval-analytics.md) | [task-09](../tasks/task-09-retrieval-analytics.md) |

**驗收標準**
- 能匯入一份 Notion Export Zip 並查詢其內容
- 修改 skill system prompt 後，不重啟 App 即可生效（下一則訊息起）
- 能用一行指令看出「最常找不到資料的 query 是什麼」

---

## Phase 4：智慧演化（LangGraph）

**目標**：以 LangGraph 取代現有線性 pipeline，支援自我修正與多步推理。

| 項目 | 規格 | 任務 |
|------|------|------|
| Self-RAG（找不到資料時自動改寫 query 重試） | [spec-10](../specs/spec-10-selfrag.md) | [task-10](../tasks/task-10-selfrag.md) |
| Reflection Node（回覆自評後重生成） | [spec-11](../specs/spec-11-reflection.md) | [task-11](../tasks/task-11-reflection.md) |

**驗收標準**
- 第一次 RAG 找不到資料時，LangGraph 自動改寫 query 並重試，成功率提升
- Generator 對自己的回覆評分 < 閾值時，自動重新生成

**注意**：P4 會重構核心 pipeline，需先確認 P1–P3 穩定後再進行。

# RAG Bot 實戰課 — 課程導覽

> 本目錄是這門課的「教科書」，用 **章節** 組織學習路徑。
> 如果你剛 fork 這個 repo，**先完成 Lesson 1 和 Lesson 2，再回來這裡**。

---

## 先修：Lesson 1 + 2 必須完成

| 前置條件 | 說明 |
|----------|------|
| ✅ Supabase `private_knowledge` 表格已建立 | 見 [Lesson 1](../Lesson_1_Supabase_Vector_db/README.md) |
| ✅ 至少 30 個 chunk 已入庫 | 見 [Lesson 2](../Lesson_2_Playwright_to_Vector_db/README.md) |
| ✅ `.env` 已設定（OpenAI key + Supabase credentials） | 見 [.env.GUIDE.md](../.env.GUIDE.md) |

Lesson 3 的所有示範都假設知識庫已有資料；空庫會讓 retrieval 節點每次都走 `clarify` 分支，難以觀察 graph 的正常行為。

---

## 你會做出什麼

一個有 LangGraph 驅動、可接任意表達層的 AI 問答機器人：

```
使用者 ──→ 表達層（LINE / HTTP API / Telegram）
                    ↓
              LangGraph RAG
                    ├── route（選 skill）
                    ├── retrieve（向量 + 全文搜尋）
                    ├── sufficiency check（夠嗎？）
                    │     └── 不夠 → clarify（誠實追問）
                    ├── generate（兩段式生成）
                    ├── judge（自我審查）
                    │     └── 不過 → reflect（自我修正）
                    └── push（回傳結果）
```

完成後，你可以 **≤ 2 天換成任何領域**（醫療、法規、程式教學……）。

---

## 先修能力

| 能力 | 程度 |
|------|------|
| Python async / await | 會用就好（不需精通）|
| 呼叫過 OpenAI / Claude / Gemini API | 至少一次 |
| 向量搜尋概念 | 讀完 Lesson 1 即可 |
| LangGraph 經驗 | **不需要**，從頭教 |
| LINE Bot 經驗 | **不需要** |

---

## 章節地圖

| 章 | 主題 | 你學到什麼 | 對應週次 |
|---|------|-----------|---------|
| [Ch 00](ch00-setup.md) | 環境設定 | 跑通 `.env`、pytest、本地服務 | 前置 |
| [Ch 01](ch01-graph-basics.md) | Graph 起步 | LangGraph 核心概念、等價重構、知識庫入庫 | W1 |
| [Ch 02](ch02-multi-seed.md) | Multi-seed 檢索 | Feature Extractor、fan-out/in、RRF fusion | W2 |
| [Ch 02b](ch02b-advanced-retrieval.md) | 進階檢索三技 | HyDE、BM25 混合檢索、Reranker | W2（選修）|
| [Ch 03](ch03-sufficiency-generation.md) | 誠實追問 + 兩段式生成 | 條件分支、Answer Contract、grounded constraint | W3 |
| [Ch 04](ch04-self-correction.md) | 自我審查 | 4 軸 Judge、reflection 迴圈、三變體並陳 | W4 |
| [Ch 05](ch05-evaluation.md) | 量化 + 觀測 | Golden case set、6 個 metric、cost tracking | W5 |
| [Ch 06](ch06-channel-store.md) | 解耦 channel + store | Protocol 模式、多 channel、換 vector DB | W6 |
| [Ch 07](ch07-multiformat-hitl.md) | 多格式 + 人工介入 | PDF/CSV ingestion、page_number citation、HITL | W7 |
| [Ch 08](ch08-capstone.md) | Capstone 整合 | 換領域 4 處、評分標準、Demo 腳本 | W8 |

---

## 怎麼搭配使用

```
本目錄 (docs/lesson/)     ← 你現在在這，先讀教科書
docs/ai-agent/specs/      ← 每章對應的設計規格（深入理解用）
docs/ai-agent/tasks/      ← 每章對應的驗收清單（動手做用）
docs/ai-agent/examples/   ← 示範輸出（卡住時對照）
tests/cases/golden.yaml   ← 你的評量測試案例
```

**學習流程**：
1. 讀本章教科書（理解 why + how）
2. 按章末「✏️ 本章任務」動手做
3. 卡住時看對應的 example / spec
4. 完成「🎯 本章里程碑」才進下一章

---

## 時程選擇

| 你有多少時間 | 建議節奏 |
|------------|---------|
| 8 週（主線）| 每週 5–8 小時，一週一章 |
| 6 週（壓縮）| Ch01+Ch02 合一週，Ch06+Ch07 合一週 |
| 16 週（學術）| 每章加 paper reading，見 [lesson-plan-variants.md](../ai-agent/plan/lesson-plan-variants.md) |
| 自學（無時程）| 按依賴鏈走，每章完成 self-check 再進下一章 |

---

---

## 驗收：pytest

每章完成「🎯 本章里程碑」後，用 pytest 確認沒有退步：

```bash
# 基本健康度（每次改完程式碼都跑一次）
pytest --tb=short -q

# 特定章節驗收
pytest tests/test_rag_graph*.py -v          # Ch01 graph 等價性
pytest tests/ -k "retriever or fusion" -v   # Ch02 multi-seed
pytest tests/ -k "sufficiency or judge" -v  # Ch03/Ch04

# Ch05 eval（需要已有 golden.yaml 和真實 KB）
python scripts/eval.py \
  --cases tests/cases/golden.yaml \
  --variants selfrag reflection \
  --output reports/eval_lesson3.md
```

**通過標準**：
- `pytest` 全綠（`passed`，`SKIPPED` 可接受，`FAILED` 不行）
- Ch05 eval 三個門檻：`chunk_recall(selfrag) ≥ 0.60`、`clarify_accuracy ≥ 0.75`、`forbidden_phrase_rate(reflection) = 0.00`

---

*完整資源索引（含 spec / task / example / RAG 理論）：[docs/ai-agent/INDEX.md](../ai-agent/INDEX.md)*

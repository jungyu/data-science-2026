# 00 · 專案規劃（Planning Prompt）

> **使用時機**：從零開始規劃新功能、重構既有架構，或與 AI 對齊開發方向時使用。

---

你是資深軟體架構師。這個 repo 是一個已完整跑通的個人 LINE Bot，具備 skill 路由、Supabase RAG 與短期對話記憶。

## 現行架構（已完成）

```
LINE 用戶訊息
    ↓
LINE Webhook（FastAPI POST /api/line/webhook）
    ↓
IntentRouter — LLM 意圖分類（OpenAI Responses API）+ heuristic fallback
    ↓
RAGRetriever — pgvector 向量搜尋 + tsvector 全文搜尋 + RRF 合併
    ↓
ResponseGenerator — 依 skill system prompt 生成回覆（OpenAI Responses API）
    ↓
LINE Push API → 回覆用戶
```

**關鍵實作細節（已確認可運作）：**

- LLM 呼叫一律用 OpenAI **Responses API**（`client.responses.create()`），不是 Chat Completions
- Router 輸出 `RouterResult`（Pydantic model）：target_skill、is_rag_required、rag_query、rag_categories、emotion_state、response_mode、confidence
- `confidence < 0.55` 或 LLM 呼叫失敗 → heuristic fallback（依關鍵字選 skill）
- `rag_categories` 的值必須對應 `ingest_markdown.py --category` 的值，否則 retriever 靜默找不到資料
- Webhook 快速回 200，在 Background Task 執行 router → RAG → generator → push
- 所有 except block 必須加 `logger.exception()`，否則例外會被靜默吞掉

**資料庫（Supabase Hosted PostgreSQL）：**

- `ai_skills`：skill 元資料與 system prompt
- `private_knowledge`：向量 + 全文搜尋知識庫，`content_hash` 有 UNIQUE constraint
- `line_messages`：inbound / outbound 對話紀錄
- `retrieval_logs`：每次檢索的 query、category filter、chunk scores
- `prompt_cache`：回覆快取（目前未啟用）

## 請根據以上現況，規劃：

{在此填入你要規劃的目標，例如：「新增語音訊息支援」或「改善 RAG 準確率」}

請輸出：
- 目標與範圍（什麼做、什麼不做）
- 需要修改的模組與檔案
- 與現行架構的整合點與風險
- 驗收標準
- 測試項目

限制：
- 不引入 LangChain 或大型 agent 框架
- 個人使用，不過度工程化
- 所有 Python 腳本使用 `.venv/bin/python`，不依賴系統 PATH

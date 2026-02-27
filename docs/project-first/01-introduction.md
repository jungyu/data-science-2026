# 第一章：導論 — RAG 與企業知識管理

## 學習目標

讀完本章，你將能夠：
- 定義 RAG（Retrieval-Augmented Generation）及其與純 LLM 問答的根本差異
- 說明企業知識管理的三大痛點，以及 RAG 如何解決它們
- 理解為什麼 RAG 系統需要「治理」而非僅靠提示工程
- 描述本專案六層治理架構在 RAG 脈絡中的角色

---

## 1.1 LLM 的三大局限

### 為什麼不能只靠 GPT-4o？

大型語言模型（LLM）如 GPT-4o、Claude、Gemini 在通用知識上表現出色，  
但在企業應用中存在三個根本限制：

**局限一：知識截止日期（Knowledge Cutoff）**

模型的訓練資料有截止日期。你公司上個月更新的產品規格書、最新的法規解釋、  
今年發布的內部政策手冊，LLM 完全不知道。

**局限二：無法存取私有資料**

LLM 不知道你公司的內部 Wiki、Confluence 頁面、技術文件、HR 政策手冊，  
也不應該知道 — 這涉及資料安全和保密性。

**局限三：幻覺（Hallucination）**

LLM 會「自信地說出錯誤答案」。當用戶問「我們的退換貨政策是什麼？」，  
LLM 可能給出聽起來合理但完全錯誤的答案。對外回答客戶時，這是不可接受的風險。

### 用一個公式理解

```
純 LLM 系統：
  用戶問題  →  LLM（訓練資料）  →  答案
  問題：只知道公開知識，不知道你的企業文件

RAG 系統：
  用戶問題  →  [語意搜尋]  →  [相關文件片段]
                                      ↓
                LLM（GPT-4o / Claude）←─ 問題 + 文件片段
                                      ↓
                           有根據的企業知識答案
```

---

## 1.2 什麼是 RAG

**RAG**（Retrieval-Augmented Generation，檢索增強生成）是一種架構模式：  
在 LLM 生成答案之前，先從你的知識庫中語意搜尋相關文件，  
再把這些文件作為上下文（context）提供給 LLM。

### RAG 的核心程式碼

```python
# 檔案：src/rag/core.py

import os
import openai

client = openai.OpenAI()  # 從環境變數讀取 OPENAI_API_KEY

def rag_answer(question: str, retrieved_chunks: list[str]) -> str:
    """
    RAG 核心：把問題和檢索到的文件片段一起送給 LLM
    
    Args:
        question: 使用者的問題
        retrieved_chunks: 從向量資料庫檢索到的相關文件片段列表
    
    Returns:
        基於文件的回答
    """
    # 把多個文件片段合併成一個 context
    context = "\n\n---\n\n".join(retrieved_chunks)

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": (
                    "你是企業內部知識庫助手。"
                    "只根據以下提供的文件內容回答問題。"
                    "如果文件中沒有相關資訊，請明確說明「根據現有文件無法回答」，"
                    "不要自行推測或使用訓練資料填補。"
                    "回答時請引用文件來源。"
                )
            },
            {
                "role": "user",
                "content": f"相關文件：\n{context}\n\n問題：{question}"
            }
        ],
        temperature=0.1,  # 低溫度 = 更保守、更確定的答案
    )

    return response.choices[0].message.content
```

> 🔑 **治理重點**：`temperature=0.1` 是一個治理決策，不是隨意設定的。  
> 低溫度讓模型傾向於「保守且確定」的答案，減少幻覺風險。  
> 這條設定必須寫進 `constitution.md`，不可任意更改。

---

## 1.3 企業 RAG 系統的五個元件

```
知識來源                   索引管線                    查詢管線
(Knowledge Sources)       (Indexing Pipeline)         (Query Pipeline)

  Confluence  ──►  文件載入  ──►  文字分割  ──►  嵌入向量化  ──►  向量資料庫
  SharePoint  ──►  (Loader)      (Chunking)   (Embedding)       (Vector DB)
  PDF / Word  ──►                                                    │
  程式碼 Repo ──►                                                    │
                                                         語意搜尋  ◄─┘
  用戶輸入 ─────────────────────────────────────────►  (Retrieval)
                                                              │
                                                         相關片段
                                                              │
                                                    LLM (GPT-4o) ──► 答案
```

**五個核心元件：**

1. **知識來源（Knowledge Sources）**：Confluence、SharePoint、PDF、Word、程式碼庫、資料庫
2. **嵌入模型（Embedding Model）**：`text-embedding-3-large`（OpenAI）或本地模型
3. **向量資料庫（Vector Database）**：Chroma（本地）、Pinecone（雲端）、pgvector（PostgreSQL）
4. **檢索器（Retriever）**：語意搜尋 + 可選的關鍵字混合搜尋
5. **生成器（Generator）**：`gpt-4o` 或其他 LLM，搭配系統提示詞

---

## 1.4 為什麼需要治理

面對 RAG 系統的風險，常見的做法是「寫更好的提示詞（prompt engineering）」。  
但這就像在沒有交通規則的路上，期望每個駕駛都靠自覺安全行駛。

**RAG 系統的三大風險：**

| 風險 | 描述 | 後果 |
|------|------|------|
| **知識污染** | 過時或錯誤的文件進入知識庫 | AI 自信地回答錯誤資訊 |
| **幻覺洩漏** | 檢索失敗時 LLM 用訓練記憶填補 | 客戶得到未經授權的答案 |
| **存取越權** | 員工透過 RAG 取得無權限的文件 | 資料外洩合規風險 |

**治理（Governance）** 是建立規則、邊界和流程的系統：

| 層面 | 提示工程 | 治理 |
|------|---------|------|
| 作用時機 | 每次對話 | 持久存在 |
| 可靠性 | 依賴 LLM 的理解 | 依賴結構化規則 |
| 可追溯性 | 對話結束即消失 | 有版本控制和日誌 |
| 一致性 | 每次可能不同 | 規則固定除非版本更新 |
| 擴展性 | 單人有效 | 團隊和多系統可用 |

> **核心思想**：治理不是限制 AI 的能力，而是建立 **信任框架**。  
> 就像醫療規範不是限制醫生的才能，而是確保病人的安全。

---

## 1.5 本專案的六層治理架構

本手冊使用的案例是 **enterprise-rag** — 一個企業內部知識問答系統。  
它的 `.agent/` 目錄包含了一整套 RAG 治理體系：

```
.agent/
├── memory/               ← 長期記憶（constitution + diary）
│   ├── constitution.md   ← 5 條不可違反原則
│   └── diary.md          ← 臨時決策暫存
├── rules/                ← 模組規則（嵌入、檢索、生成、安全）
├── skills/               ← 可執行技能模組
│   ├── ingest-skill/     ← 知識攝取技能
│   ├── query-skill/      ← 查詢技能
│   └── evaluate-skill/   ← 品質評估技能
├── prompts/              ← 斜線指令（/ingest、/query、/evaluate）
├── config/               ← 設定檔（API 限制、token budget）
├── tasks/                ← 任務邊界控制（Task Pack）
├── logs/                 ← 操作日誌（Action Log）
└── mcp-servers/          ← MCP Server 設定
    ├── knowledge-mcp.yaml
    ├── document-mcp.yaml
    └── audit-mcp.yaml
```

**六層治理架構：**

```
Layer 0  憲法 (Constitution)              ← 5 條不可違反原則
────────────────────────────────────────────────────────────
Layer 1  決策日記 (Decision Diary + ADR)  ← 架構決策記錄
────────────────────────────────────────────────────────────
Layer 2  知識規則 (Skills + Rules)        ← 技能模組 + 模組規則
────────────────────────────────────────────────────────────
Layer 3  開發管線 (Slash Commands)        ← SDD-BDD 工作流
────────────────────────────────────────────────────────────
Layer 4  治理閘門 (Governance Gates)      ← 知識品質檢查點
────────────────────────────────────────────────────────────
Layer 5  任務邊界 (Task Pack + MCP)       ← 存取控制邊界
```

每一層有明確的職責：
- **Layer 0** 回答「什麼知識永遠不能被 AI 引用？」
- **Layer 1** 回答「這個嵌入策略的決策記錄在哪？」
- **Layer 2** 回答「知識攝取技能的正確流程是什麼？」
- **Layer 3** 回答「新的知識來源如何納入 RAG？」
- **Layer 4** 回答「這批文件的品質是否達到上線標準？」
- **Layer 5** 回答「這個 MCP Server 可以存取哪些知識？」

---

## 練習

1. **觀察練習**：選擇你公司或學校的一個內部系統（Confluence、SharePoint、Google Drive 等），列出如果要建立 RAG 系統，會遇到哪三個主要挑戰（技術、資料、治理各一個）。

2. **風險分析**：假設一個 HR 部門的 RAG 系統在回答「年假有幾天？」時，查詢到了三年前的舊政策文件並給出錯誤答案。這個問題屬於上述哪種風險？如何從治理角度預防？

3. **分類練習**：以下場景分別屬於六層治理架構的哪一層？
   - (a) 「所有知識文件必須有 `last_updated` 欄位，超過 180 天未更新自動標記為待審核」
   - (b) 「這次攝取任務只能處理 `hr-policies/` 目錄下的文件」
   - (c) 「新增知識來源前必須評估 Chunking 策略並記錄 ADR」

4. **設計思考**：如果你是一家 500 人公司的資訊長，決定導入 RAG 系統，你會優先解決哪個痛點？為什麼？

---

> **下一章**：[第二章：憲法式治理 — 知識庫的最高法則](02-constitutional-governance.md)  
> 我們將學習如何為 RAG 系統建立「不可違反的原則」，確保 AI 永遠不會逾越邊界。

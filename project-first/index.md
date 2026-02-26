# 企業知識 RAG 系統建構教案
## 以 OpenAI API × MCP Server × Skills 為例的完整實作指南

> **版本**: 1.0.0 | **最後更新**: 2026-02-26
> **對象**: 資訊管理 / 軟體工程相關科系學生
> **前置知識**: 基礎 Python、REST API 概念、對 LLM（大型語言模型）有概念性理解

---

## 本手冊的定位

當企業面對海量的內部文件、技術手冊、政策規範，傳統的搜尋引擎已無法滿足需求。  
**RAG（Retrieval-Augmented Generation，檢索增強生成）** 結合向量搜尋與大型語言模型，  
讓 AI 能夠以企業私有知識為基礎，精準回答員工和客戶的問題。

本手冊以一個真實的 **企業內部知識庫 RAG 系統** 為核心案例，介紹如何整合：

- **OpenAI API**（`text-embedding-3-large` + `gpt-4o`）作為核心 AI 引擎
- **MCP Server**（Model Context Protocol）作為工具與知識來源的標準化接口
- **Skills 框架**作為 AI Agent 的可執行技能模組
- **六層治理架構**確保知識系統的可信度、可追溯性與可維護性

每一章包含四個段落：
1. **學習目標** — 這一章要學會什麼
2. **原理** — 方法論的理論根源與核心概念
3. **案例** — 以企業 RAG 知識庫為範例的真實實作
4. **練習** — 動手做，鞏固理解

---

## 章節地圖

| 章 | 標題 | 核心主題 | 難度 |
|----|------|---------|------|
| [00](00-setup.md) | 環境建置 | Python, Docker, Qdrant, MCP | 入門 |
| [01](01-introduction.md) | 導論：RAG 與企業知識管理 | RAG 概念、LLM 局限、治理必要性 | 入門 |
| [02](02-constitutional-governance.md) | 憲法式治理：知識庫的最高法則 | Constitution、ADR、Decision Diary | 入門 |
| [03](03-sdd-bdd-workflow.md) | 規範驅動開發：SDD-BDD-TDD for RAG | 規格先行、Gherkin、測試策略 | 基礎 |
| [04](04-complexity-gate.md) | 複雜度門檻：適應性 RAG 工作流 | Complexity Gate、Lite/Standard/Full | 基礎 |
| [05](05-design-by-contract.md) | 契約先行：知識 API 的合約治理 | Design by Contract、Retrieval Gate | 中級 |
| [06](06-embedding-and-chunking.md) | 嵌入向量與分塊原理 | Embedding、Chunking、Vector DB | 中級 |
| [07](07-immutable-knowledge.md) | 不可變知識管理與版本控制 | 知識不可變性、版本快照、更新策略 | 中級 |
| [08](08-safety-layers.md) | 四層防護：RAG 安全體系 | Defense in Depth、HITL、幻覺防護 | 進階 |
| [09](09-mcp-server-and-skills.md) | MCP Server 與 Skills 運營模式 | MCP Protocol、Task Pack、Token Budget | 進階 |
| [10](10-putting-it-together.md) | 融會貫通：從需求到企業部署 | 完整工作流、治理體系設計 | 綜合 |

---

## 快速路徑

- **「我要先建好開發環境」** → 讀 Ch00
- **「我只想了解 RAG 基本原理」** → 讀 Ch01 + Ch06
- **「我想建置知識庫治理體系」** → 讀 Ch02 + Ch04 + Ch05
- **「我想學 MCP Server 實作」** → 讀 Ch09 + Ch10
- **「我想了解 RAG 安全防護」** → 讀 Ch07 + Ch08
- **「我要為企業設計完整方案」** → Ch01 → Ch10（依序閱讀）

---

## 核心技術棧

```
OpenAI API
  ├── text-embedding-3-large   ← 文件嵌入向量化
  └── gpt-4o                   ← 答案生成

向量資料庫（擇一）
  ├── Chroma       ← 本地開發
  ├── Pinecone     ← 雲端生產
  └── pgvector     ← PostgreSQL 擴充

MCP Server
  ├── 知識庫 MCP   ← 封裝 retrieval 操作
  ├── 文件 MCP     ← Confluence / SharePoint 串接
  └── 稽核 MCP     ← 查詢日誌與品質評分

Skills 框架
  ├── ingest-skill    ← 知識攝取技能
  ├── query-skill     ← 查詢技能
  ├── evaluate-skill  ← 品質評估技能
  └── govern-skill    ← 治理合規技能
```

---

## 符號說明

| 符號 | 意義 |
|------|------|
| **粗體英文** | 專有名詞（首次出現附中文解釋） |
| `等寬字體` | 檔案路徑、程式碼、命令 |
| > 引用區塊 | 重要提示或定義 |
| ✅ / ❌ | 推薦做法 / 反例 |
| 🔑 | 治理關鍵點 |
| 💡 | 實作提示 |

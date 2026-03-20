# RAG 完全實戰課程：從原理到上線

> **Head First 風格 · 繁體中文 · 實戰導向**
> 完成本課程後，你將交出一個包含 RAG 知識庫、MCP Server 和視覺化儀表板的完整期末作品。

---

## 學習路徑

```
第一部分：RAG Pipeline（理論 + 實作）
─────────────────────────────────────
Ch01 → Ch02 → Ch03 → Ch04 → Ch05 → Ch06
為什麼  文件    向量    組裝    代理    評估
需要RAG 切碎    魔法    系統    思考    品質
  ↓
第二部分：整合上線
─────────────────────────────────────
Pre-A  →  Module A  →  Module B
爬蟲       MCP Server   Dashboard
存資料      包裝工具     視覺化介面
（必修）   （必修）     （必修，擇一出口）
  ↓
期末作品：RAG + MCP + 可展示的視覺化介面
```

---

## 課程大綱

### 第一部分｜RAG Pipeline

| 章節 | 標題 | 核心技術 | 難度 | 預計時間 |
|------|------|----------|------|----------|
| [Ch01](ch01-why-rag.md) | 當AI遇上健忘症 | RAG 架構概覽、LLM 局限 | ⭐ | 2 小時 |
| [Ch02](ch02-etl-chunking.md) | 把大象裝進冰箱 | ETL、文件切分、Unstructured | ⭐⭐ | 3 小時 |
| [Ch03](ch03-vectors-embeddings.md) | 數字的靈魂邊界 | Embeddings、FAISS、Qdrant | ⭐⭐⭐ | 3 小時 |
| [Ch04](ch04-llamaindex.md) | 樂高積木大師 | LlamaIndex、Index 類型 | ⭐⭐⭐ | 4 小時 |
| [Ch05](ch05-agentic-rag.md) | 讓你的AI學會反思 | Agentic RAG、LangGraph | ⭐⭐⭐⭐ | 4 小時 |
| [Ch06](ch06-evaluation.md) | 你是真的懂還是在裝懂 | Ragas 評估框架 | ⭐⭐⭐⭐ | 3 小時 |

### 第二部分｜整合上線

| 模組 | 標題 | 核心技術 | 狀態 |
|------|------|----------|------|
| [Pre-A](module-pre-a-crawler.md) | ETL Pipeline — 把知識存進 Qdrant | Playwright、Chunking、Embedding | 必修 |
| [Module A](module-a-mcp-server.md) | MCP Server | FastAPI、MCP 協議、SSE | 必修 |
| [Module B](module-b-dashboard.md) | Dashboard + AI 側欄 | Next.js、Chart.js、Mermaid | 必修 |

---

## 期末作品規格

### 必要元素（計分）

| 項目 | 說明 |
|------|------|
| RAG 知識庫 | 自選主題文件（FAQ、論文、報表、政策⋯皆可） |
| MCP Server | ≥ 2 個工具（`search_knowledge_base` + 1 個自訂工具） |
| Dashboard | ≥ 2 張 Chart.js 圖表 + AI 側欄（預設問題可運作） |

### 加分元素

| 項目 | 加分 |
|------|------|
| Mermaid 動態流程圖（AI 回傳並渲染） | ⭐ |
| Ragas 評估報告（Faithfulness ≥ 0.7） | ⭐ |
| 資料來自 Supabase（非寫死） | ⭐ |
| docker-compose 完整整合可跑 | ⭐⭐ |

---

## 技術棧速查

```python
# 第一部分（RAG Pipeline）
rag_stack = {
    "llm":       ["openai", "anthropic"],
    "embedding": ["openai/text-embedding-3-small"],
    "vector_db": ["qdrant-client", "faiss-cpu"],
    "framework": ["llama-index", "langgraph"],
    "etl":       ["unstructured", "pandas", "pypdf"],
    "eval":      ["ragas"],
}

# 第二部分（整合上線）
integration_stack = {
    "mcp_server": ["mcp", "fastapi", "uvicorn"],
    "frontend":   ["next.js 15", "daisyui 4", "chart.js 4", "mermaid 11"],
    "infra":      ["docker", "nginx", "qdrant", "supabase"],
}
```

---

## 環境設定

```bash
# Python（第一部分）
python -m venv rag-env
source rag-env/bin/activate
pip install openai llama-index qdrant-client langgraph ragas
pip install unstructured pandas pypdf

# Node.js（第二部分 Module B）
cd _project-nextjs
npm install
npm run dev   # → http://localhost:4000

# Docker（第二部分整合）
cd _project-fullstack
cp .env.example .env  # 填入金鑰
docker compose up -d qdrant mcp-server
```

---

## 先決知識

- Python 基礎（function、for 迴圈、dict）
- 大學程度統計（向量、相似度概念即可）
- 用過 ChatGPT（知道什麼是 prompt）

**不需要**：機器學習學位、前端開發經驗、深度學習背景

---

## 學習建議

> **Head First 的讀法**
> 1. 先看圖和粗體字，建立整體印象
> 2. 動手做每個 Lab，不要只讀不練
> 3. 腦力激盪的問題先自己想，再往下看
> 4. 每章結束後，用自己的話解釋給朋友聽

---

*最後更新：2026-03*

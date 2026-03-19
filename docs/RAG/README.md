# RAG 完全實戰課程：從入門到精通

> **Head First 風格 · 繁體中文 · 實戰導向**

---

## 你為什麼需要這門課？

想像一下：你花了三個月建了一個 AI 聊天機器人，上線第一天就被用戶問倒——
「為什麼你不知道上個月剛發布的產品規格？」
「為什麼你說的和我們文件寫的不一樣？」
「為什麼你亂編數字？」

**這就是沒有 RAG 的 AI 的下場。**

RAG（Retrieval-Augmented Generation，檢索增強生成）是讓 AI 從「死背書的書呆子」變成「會查資料的聰明助手」的關鍵技術。這門課會帶你從零開始，親手打造一個能查閱你自己文件的 AI 系統。

---

## 課程地圖

```
你的 RAG 學習旅程
═══════════════════════════════════════════════════════════

  [起點] → Ch01 → Ch02 → Ch03 → Ch04 → Ch05 → Ch06 → [終點]

  你現在    為什麼    文件    向量    組裝    代理    評估    你是
  是個      需要     切碎    魔法    系統    思考    品質    RAG
  新手      RAG？                                          大師
```

---

## 課程大綱

| 章節 | 標題 | 核心技術 | 難度 | 預計時間 |
|------|------|----------|------|----------|
| Ch01 | 當AI遇上健忘症 | RAG 架構概覽 | ⭐ | 2 小時 |
| Ch02 | 把大象裝進冰箱 | ETL + 文件切分 | ⭐⭐ | 3 小時 |
| Ch03 | 數字的靈魂邊界 | Embeddings + 向量搜尋 | ⭐⭐⭐ | 3 小時 |
| Ch04 | 樂高積木大師 | LlamaIndex 全攻略 | ⭐⭐⭐ | 4 小時 |
| Ch05 | 讓你的AI學會反思 | Agentic RAG + LangGraph | ⭐⭐⭐⭐ | 4 小時 |
| Ch06 | 你是真的懂還是在裝懂 | Ragas 評估框架 | ⭐⭐⭐⭐ | 3 小時 |

---

## 你將學會

- **理解 RAG 的本質**：為什麼大型語言模型需要外部知識？
- **建立 ETL 管線**：從原始文件到可搜尋的知識庫
- **掌握向量技術**：Embeddings、FAISS、Qdrant 一次搞定
- **使用 LlamaIndex**：業界最流行的 RAG 框架
- **打造 Agentic RAG**：讓 AI 學會自我反思和修正
- **評估 RAG 品質**：用 Ragas 客觀衡量你的系統好不好

---

## 技術棧

```python
# 這門課用到的主要工具
dependencies = {
    "llm": ["openai", "anthropic"],
    "embeddings": ["openai", "sentence-transformers"],
    "vector_db": ["faiss-cpu", "qdrant-client"],
    "rag_framework": ["llama-index", "langchain"],
    "agent": ["langgraph"],
    "evaluation": ["ragas"],
    "data_processing": ["unstructured", "pandas", "pypdf"],
    "visualization": ["matplotlib", "scikit-learn"],
}
```

---

## 環境設定

```bash
# 建立虛擬環境
python -m venv rag-env
source rag-env/bin/activate  # Windows: rag-env\Scripts\activate

# 安裝核心套件
pip install openai llama-index llama-index-vector-stores-faiss
pip install qdrant-client sentence-transformers
pip install langgraph langchain ragas
pip install unstructured pandas pypdf matplotlib scikit-learn

# 設定 API 金鑰
export OPENAI_API_KEY="your-key-here"
```

---

## 學習建議

> **Head First 的讀法**
>
> 1. 先看圖和粗體字，建立整體印象
> 2. 動手做每一個 Lab，不要只讀不練
> 3. 腦力激盪的問題先自己想，再看答案
> 4. 每章結束後，用自己的話解釋給朋友聽

---

## 先決知識

- Python 基礎（會寫 function、class 即可）
- 大學程度統計（知道向量、相似度是什麼）
- 用過 ChatGPT（知道什麼是提示詞）

**不需要**：機器學習背景、數學博士學位、多年工程經驗

---

## 作者寄語

RAG 不是魔法，它是工程。
當你理解每個環節的原理，你就能在系統出問題時快速診斷，在業務需求改變時靈活調整。

這門課的目標不是讓你複製貼上程式碼，而是讓你**真正理解每一行程式碼為什麼存在**。

準備好了嗎？翻開第一章，讓我們從「為什麼」開始。

---

*課程持續更新中 · 最後更新：2026-03*

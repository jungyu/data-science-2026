# 第五章：讓你的 AI 學會反思

## Agentic RAG 與 LangGraph

---

> 「一個好的偵探不會只看第一眼的證據就下結論。
>  他會重新審視，質疑假設，然後再搜尋更多線索，
>  直到確信自己找到了真相。」
>
> ——每一部柯南裡都有這種橋段

---

你在第四章建的 RAG 系統有一個隱藏的問題。

試著想像這個場景：

用戶問：「我們的 API 在什麼情況下會返回 429 錯誤？有什麼解決方法？」

**基本 RAG 的流程**：
1. 把問題向量化
2. 搜尋「429 錯誤」相關的文件片段
3. 找到：「當請求頻率超過限制時，API 會返回 429 Too Many Requests」
4. 回答：「429 是請求頻率太高的錯誤」
5. **完成**

但問題的第二部分「有什麼解決方法？」呢？

搜尋「429 錯誤」的時候，可能沒有順便找到「rate limiting 解決方案」的文件——那些文件可能用不同的關鍵字寫成，在不同的章節裡。

**基本 RAG 不知道自己回答不完整，因為它沒有「反思」的能力。**

這就是 Agentic RAG 要解決的問題。

---

## 腦力激盪 🧠

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│  問題 1：你有沒有過這樣的經驗：                         │
│          問了一個問題，得到一個答案，                   │
│          然後才意識到你問的不夠精確？                   │
│          AI 能自己察覺這種情況嗎？                      │
│                                                         │
│  問題 2：如果讓 AI 可以「重新搜尋」，                   │
│          什麼時候應該停止搜尋？                         │
│          如何避免無限搜尋下去？                         │
│                                                         │
│  問題 3：Re-ranking 和 Re-retrieval 有什麼不同？        │
│          一個是在現有結果中重新排序，                   │
│          一個是重新搜尋，你知道差別嗎？                 │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 基本 RAG 的三大死穴

```
死穴 1：單次搜尋
══════════════════════════════════════════════
  問題：「請比較 Python 和 Rust 的效能特點」

  基本 RAG 做了什麼：
  ① 搜尋「Python Rust 效能」→ 找到 3 個片段
  ② 直接回答

  問題：如果找到的 3 個片段都是關於 Python，
        沒有 Rust 的資訊怎麼辦？
        → AI 不知道自己的資訊不完整


死穴 2：查詢不夠精確
══════════════════════════════════════════════
  用戶問：「怎麼處理認證問題？」

  「認證」可能指：
  - Authentication（身份驗證）
  - Authorization（授權）
  - API Key 認證
  - OAuth 認證

  基本 RAG 用原始問題直接搜尋，
  可能找到所有類型混在一起，或完全找錯方向


死穴 3：無法整合多個資訊源
══════════════════════════════════════════════
  問題：「我的訂單 #12345 什麼時候會送達？
        如果延誤了可以申請退款嗎？」

  這個問題需要：
  - 查訂單系統（外部 API）
  - 查配送政策（FAQ 文件）
  - 查退款政策（另一個 FAQ 文件）

  基本 RAG 只能查一個固定的文件庫
```

---

## Agent 的核心思想：Think → Act → Observe → Repeat

```
Agent 循環（Agent Loop）
════════════════════════════════════════════════════════════

  用戶問題
      │
      ▼
  ┌────────────────────────────────────────────────────────┐
  │  THINK：思考                                           │
  │  「我需要什麼資訊才能回答這個問題？」                  │
  │  「我應該使用哪個工具？」                              │
  └──────────────────────────┬─────────────────────────────┘
                             │
                             ▼
  ┌────────────────────────────────────────────────────────┐
  │  ACT：行動                                             │
  │  選擇工具並執行（搜尋文件、呼叫 API 等）               │
  └──────────────────────────┬─────────────────────────────┘
                             │
                             ▼
  ┌────────────────────────────────────────────────────────┐
  │  OBSERVE：觀察                                         │
  │  「我找到了什麼？這個資訊足夠嗎？」                   │
  │  「答案完整了嗎？還是需要更多資訊？」                 │
  └──────────────────────────┬─────────────────────────────┘
                             │
                    ┌────────┴────────┐
                    │                 │
                    ▼                 ▼
               還需要繼續           足夠了
               (回到 THINK)       生成最終答案
```

---

## LangGraph：把 Agent 邏輯畫成圖

LangGraph 是 LangChain 出的 Agent 框架，核心思想是把 Agent 的邏輯表達成一個**有向圖（Directed Graph）**。

```python
pip install langgraph langchain langchain-openai
```

### 最簡單的 LangGraph 範例

```python
"""
LangGraph 基礎：狀態圖的概念
"""

from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_core.messages import HumanMessage, AIMessage


# 定義「狀態」——在整個流程中傳遞的資料結構
class AgentState(TypedDict):
    # messages 是對話歷史，用 add_messages 函式合併（而不是覆蓋）
    messages: Annotated[list, add_messages]
    # 其他自訂狀態
    search_count: int
    final_answer: str


def greeting_node(state: AgentState) -> AgentState:
    """節點 1：打招呼"""
    return {
        "messages": [AIMessage(content="你好！我是 RAG 助理，有什麼可以幫你？")],
        "search_count": 0,
    }


def analyze_node(state: AgentState) -> AgentState:
    """節點 2：分析問題"""
    last_message = state["messages"][-1]
    analysis = f"分析問題：'{last_message.content[:30]}...' → 需要搜尋"
    return {
        "messages": [AIMessage(content=analysis)],
    }


# 建立圖
builder = StateGraph(AgentState)

# 加入節點
builder.add_node("greeting", greeting_node)
builder.add_node("analyze", analyze_node)

# 定義邊（流程）
builder.set_entry_point("greeting")
builder.add_edge("greeting", "analyze")
builder.add_edge("analyze", END)

# 編譯成可執行的圖
graph = builder.compile()

# 執行
result = graph.invoke({
    "messages": [HumanMessage(content="我想了解 RAG 技術")],
    "search_count": 0,
    "final_answer": "",
})
```

---

## 動手做 Lab 5.1：建立 Self-Reflection RAG Agent

這個 Agent 會在回答之後，自我評估答案是否完整，如果不夠就重新搜尋。

```python
"""
Lab 5.1：帶有自我反思的 RAG Agent

架構：
  用戶問題
      │
      ▼
  [query_rewrite] 改寫問題（讓搜尋更精確）
      │
      ▼
  [retrieve]  搜尋相關文件
      │
      ▼
  [generate]  生成初步答案
      │
      ▼
  [reflect]   自我評估：答案夠好嗎？
      │
      ├── 夠好 → [END]
      │
      └── 不夠 → [retrieve] 重新搜尋
                  （最多 3 次）
"""

from typing import TypedDict, Annotated, List, Optional
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate
from llama_index.core import VectorStoreIndex, Document
import json


# ── 狀態定義 ────────────────────────────────────────────────
class RAGState(TypedDict):
    # 對話歷史
    messages: Annotated[list, add_messages]
    # 原始問題
    original_question: str
    # 當前使用的搜尋查詢（可能被改寫）
    current_query: str
    # 搜尋到的文件片段
    retrieved_docs: List[str]
    # 當前生成的答案
    current_answer: str
    # 反思結果："good", "need_more_info", "wrong_direction"
    reflection_result: str
    # 反思的理由
    reflection_reason: str
    # 已搜尋次數（防止無限循環）
    search_count: int
    # 最大允許搜尋次數
    max_searches: int


# ── 準備知識庫 ──────────────────────────────────────────────
KNOWLEDGE_BASE_DOCS = [
    Document(text="""
    RAG（Retrieval-Augmented Generation）系統架構說明

    RAG 系統由三個主要階段組成：

    1. 文件索引階段（離線）：
       - 載入原始文件（PDF、Word、網頁等）
       - 使用文字切分器將文件切成小塊（Chunks）
       - 用 Embedding 模型將每個 Chunk 轉換成向量
       - 將向量儲存到向量資料庫（如 FAISS、Qdrant）

    2. 查詢處理階段（線上）：
       - 接收用戶問題
       - 將問題轉換成向量
       - 在向量資料庫中搜尋最相似的 Chunks（Top-K 搜尋）
       - 將搜尋結果和問題組合成 Prompt

    3. 答案生成階段（線上）：
       - 將 Prompt 送給 LLM
       - LLM 根據提供的文件生成答案
       - 返回答案給用戶

    常見的 RAG 框架包括 LlamaIndex 和 LangChain。
    """),
    Document(text="""
    向量資料庫技術比較

    FAISS（Facebook AI Similarity Search）：
    - 由 Facebook 開發的開源庫
    - 優點：極快的搜尋速度、本地部署、零成本
    - 缺點：不支援即時更新、無過濾搜尋功能
    - 適合場景：文件數量固定、離線批次處理

    Qdrant：
    - 開源的向量資料庫，有雲端和本地部署選項
    - 優點：支援即時更新、豐富的過濾功能、RESTful API
    - 缺點：需要獨立部署（Docker）
    - 適合場景：生產環境、需要動態更新的知識庫

    Pinecone：
    - 全托管的雲端向量資料庫
    - 優點：無需管理基礎設施、高可用性
    - 缺點：成本較高、資料在第三方
    - 適合場景：快速上線、無 DevOps 資源的團隊

    選擇建議：
    - 開發和原型：FAISS（簡單快速）
    - 生產但自管：Qdrant（功能完整）
    - 生產且托管：Pinecone（省心但貴）
    """),
    Document(text="""
    Chunk Size 選擇指南

    Chunk Size 是 RAG 系統中影響效果的關鍵參數之一。

    太小的 Chunk（< 100 tokens）：
    - 問題：上下文不足，每個片段無法表達完整意思
    - 症狀：AI 答案支離破碎，缺乏連貫性
    - 適用：FAQ 這種每個問答本身就是完整單位的場景

    太大的 Chunk（> 1000 tokens）：
    - 問題：搜尋精度下降，相關部分被大量無關文字稀釋
    - 症狀：AI 找到的片段包含太多無關資訊，答案偏離主題
    - 成本：每次搜尋消耗更多 token

    建議的 Chunk Size 範圍：
    - 技術文件：512-1024 tokens
    - FAQ 和條款：256-512 tokens
    - 新聞和部落格：512 tokens
    - 程式碼：以函式為單位

    Chunk Overlap（重疊）設定為 Chunk Size 的 10-20% 是常見實踐。
    重疊的目的是避免在語意邊界切斷，確保跨 Chunk 邊界的資訊不會遺失。
    """),
]

# 建立知識庫索引
from llama_index.core import VectorStoreIndex
knowledge_index = VectorStoreIndex.from_documents(KNOWLEDGE_BASE_DOCS)
retriever = knowledge_index.as_retriever(similarity_top_k=3)


# ── LLM 初始化 ──────────────────────────────────────────────
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)


# ── 節點函式 ────────────────────────────────────────────────

def query_rewrite_node(state: RAGState) -> RAGState:
    """
    節點 1：查詢改寫
    把用戶的問題改寫成更適合搜尋的形式。
    """
    question = state["original_question"]
    reflection_result = state.get("reflection_result", "")
    reflection_reason = state.get("reflection_reason", "")

    # 如果是第一次搜尋，直接改寫問題
    if not reflection_result:
        prompt = f"""
你是一個搜尋查詢優化專家。
請將以下用戶問題改寫成更適合向量搜尋的查詢。
目標是讓搜尋更精確，找到最相關的文件。

用戶問題：{question}

請直接輸出改寫後的搜尋查詢（不需要解釋）："""
    else:
        # 如果是重新搜尋，根據反思結果改寫
        prompt = f"""
你是一個搜尋查詢優化專家。
上一次搜尋的結果不夠理想，原因是：{reflection_reason}

請根據上述原因，為以下問題生成一個**不同角度**的搜尋查詢：

原始問題：{question}
上次搜尋查詢：{state.get("current_query", question)}

請直接輸出新的搜尋查詢（不需要解釋）："""

    response = llm.invoke([HumanMessage(content=prompt)])
    new_query = response.content.strip()

    print(f"\n[Query Rewrite] 原始問題：{question}")
    print(f"[Query Rewrite] 改寫後查詢：{new_query}")

    return {
        "current_query": new_query,
        "messages": [AIMessage(content=f"搜尋查詢：{new_query}")],
    }


def retrieve_node(state: RAGState) -> RAGState:
    """
    節點 2：文件檢索
    """
    query = state["current_query"]

    print(f"\n[Retrieve] 搜尋：{query}")
    nodes = retriever.retrieve(query)

    docs = [node.text for node in nodes]
    scores = [node.score for node in nodes]

    print(f"[Retrieve] 找到 {len(docs)} 個相關片段")
    for i, (doc, score) in enumerate(zip(docs, scores)):
        print(f"  片段 {i+1} (相似度: {score:.3f}): {doc[:60]}...")

    return {
        "retrieved_docs": docs,
        "search_count": state.get("search_count", 0) + 1,
    }


def generate_node(state: RAGState) -> RAGState:
    """
    節點 3：生成答案
    """
    question = state["original_question"]
    docs = state["retrieved_docs"]
    context = "\n\n---\n\n".join(docs)

    prompt = f"""你是一個知識庫問答助理。
請根據以下文件內容回答用戶的問題。
如果文件中沒有足夠的資訊，請明確說明「根據現有文件，我無法完整回答這個問題，因為...」

文件內容：
{context}

用戶問題：{question}

請提供完整、準確的答案："""

    response = llm.invoke([HumanMessage(content=prompt)])
    answer = response.content

    print(f"\n[Generate] 生成答案（前 100 字）：{answer[:100]}...")

    return {
        "current_answer": answer,
        "messages": [AIMessage(content=answer)],
    }


def reflect_node(state: RAGState) -> RAGState:
    """
    節點 4：自我反思
    評估當前答案是否完整，決定是否需要重新搜尋。
    """
    question = state["original_question"]
    answer = state["current_answer"]
    docs = state["retrieved_docs"]
    context = "\n\n---\n\n".join(docs)

    prompt = f"""你是一個嚴格的 QA 審查員。
請評估以下答案是否完整地回答了用戶的問題。

用戶問題：{question}

參考文件：
{context}

當前答案：
{answer}

請從以下三個選項中選擇，並說明理由：
1. "good" - 答案完整且準確，可以直接提供給用戶
2. "need_more_info" - 答案部分回答了問題，但需要更多資訊補充
3. "wrong_direction" - 搜尋方向錯誤，找到的文件和問題不相關

請以 JSON 格式回應：
{{
    "result": "good" | "need_more_info" | "wrong_direction",
    "reason": "評估理由（50字以內）"
}}"""

    response = llm.invoke([HumanMessage(content=prompt)])
    try:
        # 解析 JSON 回應
        reflection = json.loads(response.content.strip())
    except json.JSONDecodeError:
        # 如果解析失敗，預設為 good
        reflection = {"result": "good", "reason": "無法解析評估結果，預設接受"}

    result = reflection.get("result", "good")
    reason = reflection.get("reason", "")

    print(f"\n[Reflect] 評估結果：{result}")
    print(f"[Reflect] 理由：{reason}")

    return {
        "reflection_result": result,
        "reflection_reason": reason,
    }


def should_continue(state: RAGState) -> str:
    """
    條件邊：決定流程的下一步。
    """
    reflection = state.get("reflection_result", "good")
    search_count = state.get("search_count", 0)
    max_searches = state.get("max_searches", 3)

    # 超過最大搜尋次數，強制結束
    if search_count >= max_searches:
        print(f"\n[Router] 已達最大搜尋次數（{max_searches}），結束")
        return "end"

    if reflection == "good":
        print(f"\n[Router] 答案品質良好，結束")
        return "end"
    else:
        print(f"\n[Router] 需要重新搜尋（原因：{reflection}），繼續第 {search_count + 1} 次搜尋")
        return "rewrite"


# ── 建立圖 ──────────────────────────────────────────────────
def build_rag_agent() -> StateGraph:
    """建立 Self-Reflection RAG Agent 圖。"""
    builder = StateGraph(RAGState)

    # 加入所有節點
    builder.add_node("query_rewrite", query_rewrite_node)
    builder.add_node("retrieve", retrieve_node)
    builder.add_node("generate", generate_node)
    builder.add_node("reflect", reflect_node)

    # 定義固定邊
    builder.set_entry_point("query_rewrite")
    builder.add_edge("query_rewrite", "retrieve")
    builder.add_edge("retrieve", "generate")
    builder.add_edge("generate", "reflect")

    # 條件邊：根據反思結果決定
    builder.add_conditional_edges(
        "reflect",
        should_continue,
        {
            "end": END,
            "rewrite": "query_rewrite",  # 重新改寫查詢
        }
    )

    return builder.compile()


# ── 主程式 ──────────────────────────────────────────────────
def run_rag_agent(question: str):
    """執行 RAG Agent 並顯示完整過程。"""
    agent = build_rag_agent()

    print(f"\n{'=' * 60}")
    print(f"問題：{question}")
    print(f"{'=' * 60}")

    result = agent.invoke({
        "messages": [HumanMessage(content=question)],
        "original_question": question,
        "current_query": question,
        "retrieved_docs": [],
        "current_answer": "",
        "reflection_result": "",
        "reflection_reason": "",
        "search_count": 0,
        "max_searches": 3,
    })

    print(f"\n{'=' * 60}")
    print("最終答案：")
    print(result["current_answer"])
    print(f"\n總共搜尋了 {result['search_count']} 次")
    print(f"{'=' * 60}")

    return result


# 測試
questions = [
    "RAG 系統是由哪些部分組成的？",
    "我應該選擇 FAISS 還是 Qdrant？有什麼考慮因素？",
    "Chunk Size 要設多大？各種文件類型的建議值是什麼？",
]

for q in questions:
    run_rag_agent(q)
```

---

## Re-Ranking：篩選出真正有用的片段

Re-Ranking 是在向量搜尋之後，用更精確的模型重新對結果評分和排序。

```
一般 RAG 搜尋流程：
  問題 → 向量搜尋（速度快、精度中等）→ Top-5 片段 → 生成答案

加入 Re-Ranking：
  問題 → 向量搜尋 Top-20 →
         Re-Ranker 重新評分 →
         取最相關的 Top-5 → 生成答案
```

### 為什麼需要 Re-Ranking？

向量搜尋使用的是 Bi-Encoder（雙塔模型）：問題和文件分開 Embedding，然後計算相似度。這樣很快，但精度有限。

Re-Ranker 使用 Cross-Encoder（交叉編碼器）：把問題和文件**一起**送進模型，讓模型「讀完」再評分。這樣更精確，但更慢（因此只對少數候選結果用）。

```python
"""
Re-Ranking 實作：使用 Cohere Reranker 或本地模型
"""

from llama_index.core.postprocessor import LLMRerank
from llama_index.core import VectorStoreIndex
from llama_index.postprocessor.cohere_rerank import CohereRerank
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.query_engine import RetrieverQueryEngine


def build_reranked_query_engine(index: VectorStoreIndex) -> RetrieverQueryEngine:
    """
    建立帶有 Re-Ranking 的查詢引擎。

    兩種 Re-Ranker 選項：
    1. CohereRerank：商業 API，效果好
    2. LLMRerank：用 GPT-4 重新評分，靈活但成本高

    生產環境建議：先用 CohereRerank 測試效果
    """
    # 第一步：向量搜尋，取較多候選（Top-20）
    retriever = VectorIndexRetriever(
        index=index,
        similarity_top_k=20,  # 先取較多候選
    )

    # 第二步：選擇 Re-Ranker
    # 選項 A：Cohere Reranker（需要 Cohere API Key）
    # reranker = CohereRerank(
    #     api_key="your-cohere-api-key",
    #     top_n=5,   # Re-Ranking 後保留前 5 個
    #     model="rerank-multilingual-v3.0",  # 支援中文
    # )

    # 選項 B：LLM Reranker（不需要額外 API）
    reranker = LLMRerank(
        choice_batch_size=5,   # 每次讓 LLM 評估 5 個
        top_n=3,               # 最終保留 Top-3
    )

    # 組合成查詢引擎
    query_engine = RetrieverQueryEngine(
        retriever=retriever,
        node_postprocessors=[reranker],
    )

    return query_engine


# 比較有無 Re-Ranking 的效果
def compare_with_reranking(
    index: VectorStoreIndex,
    question: str,
):
    """對比有無 Re-Ranking 的搜尋結果。"""
    print(f"\n問題：{question}")
    print("=" * 60)

    # 無 Re-Ranking
    basic_engine = index.as_query_engine(similarity_top_k=5)
    basic_response = basic_engine.query(question)

    print("\n❌ 基本 RAG（無 Re-Ranking）：")
    for node in basic_response.source_nodes[:3]:
        print(f"  相似度：{node.score:.4f} | {node.text[:60]}...")

    # 有 Re-Ranking
    reranked_engine = build_reranked_query_engine(index)
    reranked_response = reranked_engine.query(question)

    print("\n✅ 加入 Re-Ranking 後：")
    for node in reranked_response.source_nodes[:3]:
        print(f"  相關性：{node.score:.4f} | {node.text[:60]}...")
```

---

## Corrective RAG（CRAG）：檢測並修正錯誤的搜尋結果

CRAG 的想法更進一步：不只反思答案，更要主動評估「搜尋到的文件是否相關」。

```python
"""
CRAG（Corrective RAG）實作
在生成答案之前，先評估文件相關性
"""

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
import json


class CorrectiveRAG:
    """
    Corrective RAG 實作。

    流程：
      問題
        │
        ▼
      搜尋文件
        │
        ▼
      評估文件相關性
        │
        ├── 高度相關 → 直接生成答案
        │
        ├── 部分相關 → 補充更多搜尋
        │
        └── 不相關  → 改變搜尋策略或承認不知道
    """

    def __init__(self, retriever, llm=None):
        self.retriever = retriever
        self.llm = llm or ChatOpenAI(model="gpt-4o-mini", temperature=0)

    def grade_documents(self, question: str, docs: list[str]) -> list[dict]:
        """
        對每個文件打分：評估與問題的相關性。
        回傳：[{"text": ..., "relevance": "yes"/"no", "score": 0.0-1.0}]
        """
        graded_docs = []

        for doc in docs:
            prompt = f"""你是一個文件相關性評估專家。
請評估以下文件對於回答問題的相關性。

問題：{question}

文件內容：
{doc[:500]}

請用 JSON 格式回應：
{{
    "relevance": "yes" 或 "no",
    "score": 0.0 到 1.0 之間的數字（1.0 = 完全相關）,
    "reason": "簡短說明理由"
}}"""

            response = self.llm.invoke([HumanMessage(content=prompt)])
            try:
                grade = json.loads(response.content.strip())
            except json.JSONDecodeError:
                grade = {"relevance": "yes", "score": 0.5, "reason": "解析失敗"}

            graded_docs.append({
                "text": doc,
                "relevance": grade.get("relevance", "yes"),
                "score": grade.get("score", 0.5),
                "reason": grade.get("reason", ""),
            })

        return graded_docs

    def answer(self, question: str) -> dict:
        """執行 CRAG 流程。"""
        print(f"\n問題：{question}")

        # Step 1：搜尋文件
        nodes = self.retriever.retrieve(question)
        docs = [node.text for node in nodes]
        print(f"[CRAG] 找到 {len(docs)} 個文件")

        # Step 2：評估相關性
        graded_docs = self.grade_documents(question, docs)

        relevant_docs = [d for d in graded_docs if d["relevance"] == "yes"]
        irrelevant_docs = [d for d in graded_docs if d["relevance"] == "no"]

        print(f"[CRAG] 相關文件：{len(relevant_docs)}，不相關：{len(irrelevant_docs)}")

        # Step 3：根據相關性決定策略
        relevance_ratio = len(relevant_docs) / len(graded_docs) if graded_docs else 0

        if relevance_ratio >= 0.6:
            # 大部分文件相關，直接生成答案
            strategy = "direct_answer"
            context = "\n\n".join([d["text"] for d in relevant_docs])

        elif relevance_ratio >= 0.3:
            # 部分相關，嘗試改寫問題再搜尋
            strategy = "refined_search"
            # 這裡可以加入查詢改寫邏輯
            context = "\n\n".join([d["text"] for d in graded_docs])

        else:
            # 幾乎沒有相關文件
            strategy = "insufficient"
            context = ""

        print(f"[CRAG] 策略：{strategy}（相關比例：{relevance_ratio:.1%}）")

        # Step 4：生成答案
        if strategy == "insufficient":
            answer = "根據現有知識庫，我無法找到足夠的相關資訊來回答這個問題。建議您：1. 確認問題是否屬於知識庫的涵蓋範圍，2. 嘗試用不同的方式描述您的問題。"
        else:
            prompt = f"""根據以下文件回答問題。

文件：
{context}

問題：{question}

請提供準確、完整的答案："""

            response = self.llm.invoke([HumanMessage(content=prompt)])
            answer = response.content

        return {
            "question": question,
            "answer": answer,
            "strategy": strategy,
            "relevant_docs_count": len(relevant_docs),
            "total_docs_count": len(graded_docs),
        }


# 使用範例
crag = CorrectiveRAG(retriever=retriever)

test_questions = [
    "LlamaIndex 和 LangChain 有什麼不同？",  # 知識庫可能有這個
    "台灣的股市今天漲了多少？",               # 知識庫沒有這個（測試 insufficient 場景）
]

for q in test_questions:
    result = crag.answer(q)
    print(f"\n答案：{result['answer'][:200]}")
    print(f"策略：{result['strategy']}")
```

---

## 重點回顧 📋

```
┌─────────────────────────────────────────────────────────┐
│                    第五章重點整理                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  🔑 基本 RAG 的三大限制：                               │
│     1. 單次搜尋：不知道自己找錯了                       │
│     2. 查詢不精確：用原始問題搜尋效果差                 │
│     3. 無法整合多個資料源                               │
│                                                         │
│  🔑 Agent Loop：                                        │
│     Think → Act → Observe → 重複 or 結束               │
│     關鍵：設定最大迭代次數防止無限循環                  │
│                                                         │
│  🔑 LangGraph 核心概念：                               │
│     State：整個流程共享的狀態字典                       │
│     Node：處理狀態的函式                                │
│     Edge：節點間的連線（包含條件邊）                    │
│                                                         │
│  🔑 Re-Ranking：                                        │
│     向量搜尋 Top-20 → Cross-Encoder 重新評分 → Top-5   │
│     犧牲少量速度換取更精確的搜尋結果                    │
│                                                         │
│  🔑 CRAG（Corrective RAG）：                            │
│     在生成答案之前，先評估文件相關性                    │
│     相關性低時改變策略，而不是硬生成                    │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 常見問題 FAQ

**Q: Agentic RAG 一定比基本 RAG 好嗎？**

不一定。Agentic RAG 的優勢在於複雜問題和需要自我修正的場景。但它的代價是：
- 更多 LLM 呼叫（成本更高）
- 更慢（每次反思都要呼叫 API）
- 更難偵錯（流程複雜）

對於簡單的事實查詢，基本 RAG 通常已經夠好，用 Agentic RAG 是殺雞用牛刀。

---

**Q: 如何設定最大迭代次數？**

這是一個業務決策：
- 太少（如 1）：等同基本 RAG，沒有意義
- 太多（如 10）：成本高、延遲高，用戶體驗差
- 建議：2-3 次，超過後無論如何都給出最佳可能的答案

---

**Q: Re-Ranking 用什麼模型最好？**

| 模型 | 優點 | 缺點 |
|------|------|------|
| Cohere Rerank | 效果好、支援中文 | 商業 API，有費用 |
| BGE-Reranker | 開源免費，中文效果好 | 需要本地 GPU |
| LLM Rerank（GPT-4）| 靈活，無需額外模型 | 成本高、速度慢 |

---

## 課後練習

### 練習 5.1：基礎（⭐）

修改 Lab 5.1 的 `reflect_node`，讓它的評估標準更嚴格：
- 加入一個新的評估維度：「答案是否引用了具體的文件資訊？」
- 如果答案中沒有具體事實（只有模糊的描述），也認定為 `need_more_info`

### 練習 5.2：進階（⭐⭐）

用 LangGraph 建立一個「查詢分解 Agent」：
- 當問題包含多個子問題時（用 LLM 判斷），自動拆分成多個搜尋查詢
- 分別搜尋每個子問題
- 最後把所有結果整合成一個完整答案

### 練習 5.3：挑戰（⭐⭐⭐）

用 LangGraph 實作完整的 Self-RAG 論文中的三個 Reflection 機制：
1. **Retrieve**：是否需要搜尋？（有些問題不需要搜尋就能回答）
2. **IsRel**：搜尋到的文件是否相關？
3. **IsSup**：答案是否被文件所支持（有沒有幻覺）？
4. **IsUse**：答案對用戶是否有用？

---

## 下一章預告

你已經建了一個會自我反思的 RAG 系統。但你怎麼知道它真的表現好？

**第六章：你是真的懂還是在裝懂**

> 「如何客觀地評分一個開卷考試的答案？這比你想的更難。」

我們會學習用 Ragas 框架客觀評估 RAG 系統的品質。

---

*第五章完 · 繼續閱讀 [第六章](./ch06-evaluation.md)*

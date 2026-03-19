# 第四章：樂高積木大師

## LlamaIndex 完全攻略

---

> 「小時候玩樂高，你可以用同樣的積木蓋出房子、飛機、或是一隻恐龍。
> LlamaIndex 也是一樣——同樣的積木（Node、Index、Retriever），
> 你可以組出完全不同的 RAG 系統。」

---

到目前為止，你已經手動實作了 RAG 的每一個零件：
- 用 SimpleDirectoryReader 讀取文件
- 用 SentenceSplitter 切分
- 用 FAISS 建立向量索引
- 用 OpenAI API 做 Embedding 和生成

但每次都要從頭組裝，太累了。

**LlamaIndex** 是一個框架，把這些零件都整合好了。你只需要知道哪個積木放哪裡。

---

## 腦力激盪 🧠

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│  問題 1：如果你有一本 1000 頁的法律合約，              │
│          用戶問「第一章的主要義務是什麼？」            │
│          你想讓 AI 搜尋全文，還是先找到第一章再搜尋？  │
│                                                         │
│  問題 2：「總結文件」和「回答問題」需要的搜尋策略       │
│          相同嗎？為什麼？                               │
│                                                         │
│  問題 3：如果一個問題需要比較 5 份文件的內容，         │
│          你會怎麼設計 RAG 管線？                        │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## LlamaIndex 的積木世界

讓我們先認識這些核心積木：

```
LlamaIndex 核心概念層次
════════════════════════════════════════════════════════════

  文件（Documents）
  ┌────────────────────────────────────────────────────┐
  │  原始文件載入後的物件，包含文字和中繼資料           │
  │  就像還沒切好的大塊積木                            │
  └────────────────────────────────────────────────────┘
           │ 切分
           ▼
  節點（Nodes / TextNodes）
  ┌────────────────────────────────────────────────────┐
  │  文件切分後的單個片段，是搜尋的最小單位            │
  │  就像一塊一塊的樂高小積木                          │
  │  包含：文字、Embedding、指向原文件的關係           │
  └────────────────────────────────────────────────────┘
           │ 向量化 + 組裝
           ▼
  索引（Index）
  ┌────────────────────────────────────────────────────┐
  │  儲存和組織 Nodes 的資料結構                       │
  │  就像積木的說明書——決定怎麼找到對的積木            │
  │                                                    │
  │  VectorStoreIndex：用語意相似度搜尋               │
  │  SummaryIndex：依序讀取所有 Nodes                 │
  │  TreeIndex：階層式，從粗到細搜尋                   │
  │  KeywordTableIndex：關鍵字索引                    │
  └────────────────────────────────────────────────────┘
           │ 轉換為
           ▼
  查詢引擎（Query Engines）
  ┌────────────────────────────────────────────────────┐
  │  接受問題，返回答案的端到端介面                    │
  │  包含：Retriever + Synthesizer                    │
  └────────────────────────────────────────────────────┘
```

---

## 三種索引類型：適材適所

### VectorStoreIndex：最常用的選擇

```python
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
from llama_index.core.node_parser import SentenceSplitter

# 建立最基本的向量索引
documents = SimpleDirectoryReader("./documents").load_data()
index = VectorStoreIndex.from_documents(
    documents,
    transformations=[SentenceSplitter(chunk_size=512, chunk_overlap=50)],
    show_progress=True,
)

# 用法：精確語意搜尋
query_engine = index.as_query_engine(similarity_top_k=5)
response = query_engine.query("退款流程是什麼？")
print(response)
```

**適合**：精確問答、特定問題查詢
**原理**：用問題的 Embedding 找最相似的 Top-K 節點

---

### SummaryIndex：適合摘要任務

```python
from llama_index.core import SummaryIndex

# Summary Index 按照文件順序組織節點
summary_index = SummaryIndex.from_documents(documents)

# 設定為摘要模式
summary_engine = summary_index.as_query_engine(
    response_mode="tree_summarize",  # 遞迴摘要，適合長文件
)

response = summary_engine.query("請摘要這份文件的主要內容")
print(response)
```

**適合**：文件摘要、概覽問題（「這份文件大概說什麼？」）
**原理**：讀取所有節點，遞迴生成摘要

**注意**：這個模式 token 消耗很多，因為會讀取所有節點！

---

### TreeIndex：適合層次化文件

```python
from llama_index.core import TreeIndex

# Tree Index 建立文件的樹狀摘要結構
tree_index = TreeIndex.from_documents(documents)

# 查詢時從摘要向下鑽入
tree_engine = tree_index.as_query_engine()

response = tree_engine.query("這份文件的核心論點是什麼？")
```

**適合**：有明顯層次結構的文件（書籍、報告）
**原理**：先建立各層摘要，查詢時從頂層往下搜尋

---

## 深入 Retriever：搜尋的核心

Retriever 是決定「找哪些節點」的組件。讓我們自定義它：

```python
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.postprocessor import SimilarityPostprocessor

# 自訂 Retriever
retriever = VectorIndexRetriever(
    index=index,
    similarity_top_k=10,     # 先取 Top-10，再過濾
)

# 後處理：過濾相似度太低的結果
postprocessor = SimilarityPostprocessor(
    similarity_cutoff=0.7    # 只保留相似度 > 0.7 的節點
)

# 組裝查詢引擎
query_engine = RetrieverQueryEngine(
    retriever=retriever,
    node_postprocessors=[postprocessor],
)

response = query_engine.query("什麼是 Transformer 架構？")
print(response)

# 查看使用了哪些節點
for node in response.source_nodes:
    print(f"\n[來源] 相似度：{node.score:.4f}")
    print(f"       內容：{node.text[:100]}...")
```

---

## 自訂 Response Synthesizer：決定「怎麼回答」

```python
from llama_index.core.response_synthesizers import get_response_synthesizer, ResponseMode

# 各種回答模式
RESPONSE_MODES = {
    "refine": "逐一讀取每個節點，持續精煉答案（品質最好，但最慢）",
    "compact": "把多個節點塞進一個 prompt（最常用）",
    "tree_summarize": "遞迴摘要多個節點（適合長文件摘要）",
    "simple_summarize": "把所有節點截斷成一個 prompt（最快，但可能丟失資訊）",
    "no_text": "只返回節點，不生成答案（適合自行處理）",
    "accumulate": "對每個節點單獨生成答案，然後合併（適合需要覆蓋所有節點的場景）",
}

# 使用 refine 模式（高品質）
synthesizer = get_response_synthesizer(
    response_mode=ResponseMode.REFINE,
    verbose=True,  # 顯示每次精煉的過程
)

query_engine = RetrieverQueryEngine(
    retriever=retriever,
    response_synthesizer=synthesizer,
)
```

---

## 動手做 Lab 4.1：完整的 LlamaIndex RAG 系統

我們來建一個真實的「技術文件問答系統」：

```python
"""
Lab 4.1：基於 LlamaIndex 的技術文件問答系統
用 LlamaIndex 的官方文件作為知識庫
"""

import os
from pathlib import Path
import requests

from llama_index.core import (
    VectorStoreIndex,
    SimpleDirectoryReader,
    StorageContext,
    load_index_from_storage,
    Settings,
)
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.postprocessor import SimilarityPostprocessor
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI as LlamaOpenAI


# ── 全域設定 ────────────────────────────────────────────────
Settings.llm = LlamaOpenAI(
    model="gpt-4o-mini",
    temperature=0,         # 設為 0，讓回答更確定性
)
Settings.embed_model = OpenAIEmbedding(
    model="text-embedding-3-small",
)
Settings.node_parser = SentenceSplitter(
    chunk_size=512,
    chunk_overlap=50,
)


# ── 知識庫建立 ──────────────────────────────────────────────
def build_or_load_index(
    documents_dir: str,
    persist_dir: str = "./storage",
) -> VectorStoreIndex:
    """
    建立或載入索引。
    如果已存在持久化的索引，直接載入（避免重複花費 API）。
    """
    persist_path = Path(persist_dir)

    if persist_path.exists() and any(persist_path.iterdir()):
        print("發現已存在的索引，直接載入...")
        storage_context = StorageContext.from_defaults(persist_dir=persist_dir)
        index = load_index_from_storage(storage_context)
        print("索引載入完成！")
        return index

    print("建立新索引...")
    documents = SimpleDirectoryReader(
        input_dir=documents_dir,
        recursive=True,
    ).load_data()

    print(f"載入了 {len(documents)} 份文件")

    index = VectorStoreIndex.from_documents(
        documents,
        show_progress=True,
    )

    # 持久化索引（下次直接載入）
    index.storage_context.persist(persist_dir=persist_dir)
    print(f"索引已儲存至 {persist_dir}")

    return index


# ── 問答系統 ────────────────────────────────────────────────
class DocumentQASystem:
    """
    技術文件問答系統。
    """

    def __init__(self, index: VectorStoreIndex):
        self.index = index

        # 設定 Retriever
        self.retriever = VectorIndexRetriever(
            index=index,
            similarity_top_k=5,
        )

        # 設定後處理（過濾低相似度結果）
        self.postprocessor = SimilarityPostprocessor(
            similarity_cutoff=0.6
        )

        # 組裝查詢引擎
        self.query_engine = RetrieverQueryEngine(
            retriever=self.retriever,
            node_postprocessors=[self.postprocessor],
        )

    def ask(self, question: str, verbose: bool = False) -> dict:
        """
        問問題，返回答案和來源。
        """
        response = self.query_engine.query(question)

        result = {
            "question": question,
            "answer": str(response),
            "sources": [],
        }

        for node in response.source_nodes:
            result["sources"].append({
                "text": node.text[:200] + "...",
                "score": node.score,
                "metadata": node.metadata,
            })

        if verbose:
            print(f"\n問題：{question}")
            print(f"\n答案：{response}")
            print(f"\n參考來源（{len(result['sources'])} 個節點）：")
            for i, src in enumerate(result["sources"], 1):
                print(f"  [{i}] 相似度：{src['score']:.4f}")
                print(f"       {src['text'][:80]}...")

        return result

    def chat(self):
        """互動式問答介面。"""
        # 切換到對話模式（保留歷史）
        chat_engine = self.index.as_chat_engine(
            chat_mode="condense_plus_context",
            verbose=False,
        )

        print("\n=== 文件問答系統 ===")
        print("輸入 'quit' 退出\n")

        while True:
            question = input("你：").strip()
            if question.lower() in ["quit", "exit", "q"]:
                print("再見！")
                break
            if not question:
                continue

            response = chat_engine.chat(question)
            print(f"\nAI：{response}\n")


# ── 主程式 ──────────────────────────────────────────────────
def main():
    # 建立測試文件目錄
    docs_dir = Path("./test_docs")
    docs_dir.mkdir(exist_ok=True)

    # 寫入測試文件
    (docs_dir / "product_manual.txt").write_text("""
產品使用手冊 v2.0

第一章：系統需求
本產品需要 Python 3.10 或以上版本。
作業系統支援 Windows 10、macOS 12、Ubuntu 20.04 或以上版本。
記憶體最低需求為 8GB RAM，建議 16GB 以上。
硬碟空間至少需要 10GB 可用空間。

第二章：安裝步驟
1. 下載安裝程式
   請前往官方網站 www.example.com/download 下載最新版本。

2. 執行安裝程式
   雙擊安裝程式，依照指示完成安裝。
   安裝過程中需要管理員權限。

3. 啟動軟體
   安裝完成後，在桌面或應用程式選單中找到軟體圖示。
   首次啟動需要輸入授權碼，授權碼會在購買確認信中提供。

第三章：主要功能
3.1 資料匯入
支援 CSV、Excel、JSON、XML 格式的資料匯入。
單次最大匯入限制為 1GB。

3.2 資料分析
內建 30 種統計分析方法，包含迴歸分析、聚類分析、時間序列分析。
支援自動異常值偵測功能。

3.3 報表生成
可生成 PDF、HTML、Excel 格式的報表。
支援自訂報表樣板。

第四章：故障排除
Q：軟體無法啟動怎麼辦？
A：請確認您的系統符合最低需求，並嘗試以管理員身份執行。
   如問題持續，請聯繫技術支援：support@example.com

Q：授權碼無效怎麼辦？
A：請確認授權碼是否正確輸入（區分大小寫）。
   每個授權碼只能使用一次。如需重新啟用，請聯繫客服。

第五章：技術規格
處理速度：1000 萬筆資料/分鐘
最大並行用戶數：50
API 回應時間：< 200ms（一般操作）
資料加密：AES-256
""", encoding="utf-8")

    (docs_dir / "faq.txt").write_text("""
常見問題解答（FAQ）

Q1：如何申請退款？
A1：在購買後 30 天內，您可以透過以下方式申請退款：
    方法一：登入帳號 → 訂單管理 → 申請退款
    方法二：發送郵件至 refund@example.com
    退款將在 3-5 個工作日內退回原付款方式。

Q2：可以同時在幾台電腦使用？
A2：標準版授權允許在 2 台電腦上同時使用。
    企業版授權數量依合約約定。
    如需增加使用數量，請聯繫業務部門。

Q3：有免費試用嗎？
A3：是的！我們提供 14 天免費試用，無需信用卡。
    試用期間享有完整功能存取。
    試用到期後，如不升級，資料仍可匯出 30 天。

Q4：資料安全性如何保障？
A4：所有資料使用 AES-256 加密儲存。
    傳輸過程使用 TLS 1.3 加密。
    每日自動備份，備份保留 90 天。
    符合 GDPR、ISO 27001 等安全標準。

Q5：如何聯繫技術支援？
A5：工作時間（週一至週五 09:00-18:00 台灣時間）：
    - 即時聊天：登入後點選右下角「聯繫我們」
    - 電話：0800-888-888
    - 電郵：support@example.com
    一般問題在 4 小時內回覆，緊急問題在 1 小時內回覆。
""", encoding="utf-8")

    # 建立索引
    index = build_or_load_index(
        documents_dir=str(docs_dir),
        persist_dir="./storage",
    )

    # 建立問答系統
    qa_system = DocumentQASystem(index)

    # 測試問答
    test_questions = [
        "安裝這個軟體需要多少記憶體？",
        "退款政策是什麼？",
        "一個授權可以在幾台電腦上使用？",
        "這個軟體支援哪些資料格式匯入？",
        "有免費試用期嗎？",
    ]

    print("\n=== 問答系統測試 ===")
    for question in test_questions:
        qa_system.ask(question, verbose=True)
        print()


if __name__ == "__main__":
    main()
```

---

## Lab 4.2：進階——多文件比較與路由

有時候你需要在多個文件集之間路由問題：

```python
"""
Lab 4.2：多索引路由——根據問題自動選擇對應的索引
"""

from llama_index.core import SummaryIndex, VectorStoreIndex
from llama_index.core.tools import QueryEngineTool
from llama_index.core.query_engine import RouterQueryEngine
from llama_index.core.selectors import LLMSingleSelector
from llama_index.core import Document


# 建立兩個不同主題的索引
tech_documents = [
    Document(text="Python 的 asyncio 是非同步程式設計框架，使用 async/await 語法..."),
    Document(text="Docker 是一個容器化平台，可以把應用程式和依賴打包成容器..."),
    Document(text="Kubernetes 是容器編排系統，用於自動部署和管理容器化應用..."),
]

business_documents = [
    Document(text="本季度營收達到 1.2 億台幣，較上季成長 15%..."),
    Document(text="行銷預算分配：數位廣告 40%、活動贊助 30%、內容行銷 30%..."),
    Document(text="客戶滿意度調查顯示 NPS 分數為 72，高於業界平均 55..."),
]

# 分別建立索引
tech_index = VectorStoreIndex.from_documents(tech_documents)
business_index = SummaryIndex.from_documents(business_documents)

# 把索引包裝成「工具」，並加上說明
tech_tool = QueryEngineTool.from_defaults(
    query_engine=tech_index.as_query_engine(),
    name="tech_knowledge",
    description="包含技術文件，適合回答程式設計、DevOps、系統架構相關問題",
)

business_tool = QueryEngineTool.from_defaults(
    query_engine=business_index.as_query_engine(),
    name="business_reports",
    description="包含商業報告和財務資料，適合回答業績、預算、策略相關問題",
)

# 建立路由查詢引擎
# LLMSingleSelector 會讓 LLM 決定使用哪個工具
router_engine = RouterQueryEngine(
    selector=LLMSingleSelector.from_defaults(),
    query_engine_tools=[tech_tool, business_tool],
    verbose=True,  # 顯示路由決策
)

# 測試路由
questions = [
    "如何使用 asyncio 寫非同步程式？",   # 應該路由到 tech_tool
    "本季度的業績表現如何？",              # 應該路由到 business_tool
    "客戶滿意度有多高？",                  # 應該路由到 business_tool
    "Docker 和 Kubernetes 有什麼差別？",  # 應該路由到 tech_tool
]

for q in questions:
    print(f"\n問題：{q}")
    response = router_engine.query(q)
    print(f"答案：{response}")
```

---

## Lab 4.3：查詢分解——處理複雜問題

```python
"""
Lab 4.3：Sub-question Query Engine——把複雜問題拆成小問題
"""

from llama_index.core.query_engine import SubQuestionQueryEngine
from llama_index.core.tools import QueryEngineTool
from llama_index.core import Document, VectorStoreIndex

# 準備多個文件集
q1_docs = [
    Document(text="2025年第一季：營收 3000 萬，成本 2000 萬，利潤 1000 萬"),
    Document(text="2025年第二季：營收 3500 萬，成本 2100 萬，利潤 1400 萬"),
]
q2_docs = [
    Document(text="2025年第三季：營收 4000 萬，成本 2300 萬，利潤 1700 萬"),
    Document(text="2025年第四季：營收 4500 萬，成本 2500 萬，利潤 2000 萬"),
]

idx_q1 = VectorStoreIndex.from_documents(q1_docs)
idx_q2 = VectorStoreIndex.from_documents(q2_docs)

# 建立工具
tools = [
    QueryEngineTool.from_defaults(
        query_engine=idx_q1.as_query_engine(),
        name="q1_q2_2025",
        description="2025年上半年（第一、二季）的財務數據",
    ),
    QueryEngineTool.from_defaults(
        query_engine=idx_q2.as_query_engine(),
        name="q3_q4_2025",
        description="2025年下半年（第三、四季）的財務數據",
    ),
]

# Sub-question Engine 會把複雜問題拆成小問題
sub_question_engine = SubQuestionQueryEngine.from_defaults(
    query_engine_tools=tools,
    verbose=True,
)

# 這個複雜問題需要查詢兩個索引
complex_question = "2025年全年的總營收和總利潤是多少？哪一季成長最快？"
print(f"問題：{complex_question}\n")
response = sub_question_engine.query(complex_question)
print(f"\n最終答案：{response}")
```

---

## 不同索引的使用場景比較

```
索引選擇決策樹
════════════════════════════════════════════════════════════

  你的問題類型是什麼？
       │
       ├── 精確查詢（「XX 的規格是什麼？」）
       │       └──► VectorStoreIndex ✅
       │
       ├── 全文摘要（「這份文件說了什麼？」）
       │       └──► SummaryIndex ✅
       │
       ├── 跨多個文件比較（「A 和 B 有什麼差別？」）
       │       └──► SubQuestionQueryEngine ✅
       │
       ├── 根據問題類型選不同知識庫
       │       └──► RouterQueryEngine ✅
       │
       └── 層次結構文件（書籍、大型報告）
               └──► TreeIndex ✅
```

| 索引類型 | 優點 | 缺點 | 最佳場景 |
|----------|------|------|----------|
| VectorStoreIndex | 最快、最精確 | 不適合全文摘要 | 大多數問答場景 |
| SummaryIndex | 適合全文理解 | Token 消耗大 | 文件摘要 |
| TreeIndex | 支援層次搜尋 | 建立較慢 | 書籍、大型報告 |
| KeywordTableIndex | 可解釋性高 | 精確度較低 | 關鍵字檢索 |

---

## 重點回顧 📋

```
┌─────────────────────────────────────────────────────────┐
│                    第四章重點整理                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  🔑 LlamaIndex 核心積木：                               │
│     Document → Node → Index → Query Engine             │
│                                                         │
│  🔑 三種主要索引：                                      │
│     VectorStoreIndex：語意搜尋，最常用                  │
│     SummaryIndex：全文摘要，Token 消耗大                │
│     TreeIndex：層次搜尋，適合結構化文件                 │
│                                                         │
│  🔑 Response Mode 選擇：                               │
│     compact：最常用，把節點塞進一個 prompt              │
│     refine：品質最好，逐節點精煉                        │
│     tree_summarize：摘要任務首選                        │
│                                                         │
│  🔑 進階查詢引擎：                                      │
│     RouterQueryEngine：根據問題路由到不同索引           │
│     SubQuestionQueryEngine：複雜問題拆成小問題          │
│                                                         │
│  🔑 索引持久化：                                        │
│     index.storage_context.persist() 存到磁碟            │
│     load_index_from_storage() 載入已存在的索引          │
│     避免每次都重新花費 Embedding API                    │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 常見問題 FAQ

**Q: VectorStoreIndex 和 SummaryIndex 可以同時用嗎？**

可以！在同一份文件集上建立兩個索引，然後用 RouterQueryEngine 根據問題類型自動選擇。

---

**Q: similarity_top_k 要設多少？**

這是一個 precision vs. recall 的取捨：
- **太小**（如 3）：可能漏掉相關內容，但 prompt 小、成本低
- **太大**（如 20）：覆蓋率高，但 prompt 大、成本高、LLM 注意力分散

一般建議：開始用 5，根據實際效果調整。可以先設大一點（如 10），再用 SimilarityPostprocessor 過濾低分節點。

---

**Q: 為什麼有時候 LlamaIndex 的回答和我預期的不一樣？**

常見原因：
1. **Chunk 太小**：相關資訊被切斷，每個節點只有部分資訊
2. **similarity_top_k 太小**：相關節點沒有被檢索到
3. **Response Mode 不對**：用了 compact 但文件需要 refine 精煉
4. **System Prompt 不夠明確**：沒有告訴 LLM 要嚴格根據文件回答

---

## 課後練習

### 練習 4.1：基礎（⭐）

用 Lab 4.1 建立的系統，分別測試以下兩種 Response Mode 的回答品質：
- `compact`
- `refine`

選 5 個問題，比較兩種模式的回答，記錄哪種模式在哪種問題上表現更好。

### 練習 4.2：進階（⭐⭐）

在 Lab 4.1 的基礎上，加入以下功能：
- 每次回答後，顯示「信心分數」（用最高的 source node 相似度分數代表）
- 如果信心分數 < 0.6，在答案前加上「⚠️ 注意：我對這個答案的確定性不高」的警告
- 記錄每次查詢的問題、答案、信心分數到一個 CSV 文件

### 練習 4.3：挑戰（⭐⭐⭐）

建立一個「多策略查詢系統」：
- 先用 VectorStoreIndex 搜尋，如果信心分數 < 0.7，再用 SummaryIndex 補充
- 最後把兩個來源的資訊合併，讓 LLM 生成一個綜合性答案
- 用至少 10 個問題評估這種策略是否比單一策略更好

---

## 下一章預告

你已經會建立完整的 RAG 系統了。但基本的 RAG 有一個致命弱點：它只做一次搜尋。如果第一次搜尋找錯了呢？

**第五章：讓你的 AI 學會反思**

> 「一個好的偵探不會只看第一眼的證據就下結論。
>  他會重新審視，質疑，然後再搜尋更多線索。」

我們會學習讓 AI 學會反思和自我修正的 Agentic RAG。

---

*第四章完 · 繼續閱讀 [第五章](./ch05-agentic-rag.md)*

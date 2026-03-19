# 第二章：把大象裝進冰箱

## 文件處理、切分策略與 ETL 管線

---

> 「把大象裝進冰箱只要三步：打開冰箱、把大象放進去、關上冰箱。」
>
> ——世界上最沒用的建議

---

好的，你在第一章學到了 RAG 的概念。現在你興沖沖地想說：「太好了！我們公司有 2000 份 PDF，把它們全部丟進去就行了！」

然後你打開 Python，試圖把第一份 PDF 餵給 LLM。

**系統回報：Token limit exceeded。**

歡迎來到現實世界。

把原始文件變成 AI 可以搜尋的知識庫，絕對不是「打開、放進去、關上」這麼簡單。這一章，我們要學習**文件處理的完整 ETL 管線**——Extract（萃取）、Transform（轉換）、Load（載入）。

---

## 腦力激盪 🧠

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│  問題 1：一份 100 頁的 PDF，有幾個字？                  │
│          如果 GPT-4o 的 Context Window 是 128K tokens,  │
│          一個中文字大約是 1-2 tokens，                  │
│          你能把多少頁直接塞進去？                       │
│                                                         │
│  問題 2：如果你把一本小說切成每 10 個字一段，           │
│          會有什麼問題？                                  │
│                                                         │
│  問題 3：同樣一句話放在文章的開頭和結尾，              │
│          意思會不會不一樣？                             │
│          這對 AI 理解文件有什麼影響？                   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 為什麼不能直接餵整份文件？

讓我們算一筆帳：

```python
# 粗略計算 Token 成本
document_pages = 100          # 100 頁 PDF
chinese_chars_per_page = 500  # 每頁約 500 中文字
tokens_per_char = 1.5         # 中文平均約 1.5 tokens/字

total_tokens = document_pages * chinese_chars_per_page * tokens_per_char
print(f"文件大小：{total_tokens:,} tokens")  # 75,000 tokens

# GPT-4o 的定價（2025年）
input_cost_per_1k = 0.005   # $0.005 per 1K input tokens（美金）
cost_per_query = (total_tokens / 1000) * input_cost_per_1k
print(f"每次查詢成本：${cost_per_query:.3f}")  # $0.375

# 如果每天有 1000 次查詢
daily_queries = 1000
daily_cost = cost_per_query * daily_queries
print(f"每日成本：${daily_cost:.1f}")   # $375/天
print(f"每月成本：${daily_cost * 30:.1f}")  # $11,250/月
```

**每個月要花 $11,250 美金？** 光是一份 100 頁的文件就這樣了，更別說你有 2000 份。

但成本還不是最大的問題。

---

## 大海撈針問題

想像你是一個學生，要回答一道關於「隋朝科舉制度」的問題。老師給你的是整個「中國歷史」的教科書（1000 頁）。

哪個方法更容易找到答案？

```
方法 A：把整本書從頭讀到尾，邊讀邊找答案
方法 B：先翻目錄，找到「隋唐政治」那一章（第 35 頁），
        直接翻到那頁找答案
```

顯然是方法 B。

**LLM 也一樣。** 當你把 100 頁文件全部塞進 Context Window，LLM 需要在海量文字中「關注」到正確的部分。研究發現，LLM 對文件中間段落的注意力往往較差（這叫做 **Lost in the Middle** 問題）。

RAG 的文件切分，就是讓 AI 只看「方法 B」中找到的那一章。

---

## ETL 管線全貌

```
文件 ETL 管線
════════════════════════════════════════════════════════════

  原始資料                    E（萃取）
  ┌──────────┐            ┌──────────────────────┐
  │ PDF      │            │                      │
  │ Word     ├──────────► │  文件載入器           │
  │ CSV      │            │  (Document Loaders)  │
  │ HTML     │            │                      │
  │ 資料庫   │            └──────────┬───────────┘
  └──────────┘                       │
                                     │ 純文字 + 中繼資料
                                     ▼
                           T（轉換）
                        ┌──────────────────────┐
                        │                      │
                        │  文件切分器           │
                        │  (Text Splitters)    │
                        │                      │
                        │  - 清理              │
                        │  - 切分              │
                        │  - 加入中繼資料      │
                        │                      │
                        └──────────┬───────────┘
                                   │
                                   │ 文件片段 (Chunks)
                                   ▼
                         L（載入）
                      ┌──────────────────────┐
                      │                      │
                      │  向量資料庫           │
                      │  (Vector Store)      │
                      │                      │
                      │  [Chunk 1] [1024d]   │
                      │  [Chunk 2] [1024d]   │
                      │  [Chunk 3] [1024d]   │
                      │  ...                 │
                      │                      │
                      └──────────────────────┘
```

---

## Step 1：萃取（Extract）——讀取各種格式的文件

### 最懶的方法：LlamaIndex SimpleDirectoryReader

```python
from llama_index.core import SimpleDirectoryReader

# 讀取整個目錄的所有支援格式
documents = SimpleDirectoryReader(
    input_dir="./documents",
    recursive=True,                     # 包含子目錄
    required_exts=[".pdf", ".docx", ".txt", ".csv"]
).load_data()

print(f"載入了 {len(documents)} 份文件")
for doc in documents[:3]:
    print(f"  - {doc.metadata.get('file_name', 'unknown')}: {len(doc.text)} 字")
```

### 讀取特定格式

```python
import pandas as pd
from pathlib import Path

# ── 讀取 PDF ──────────────────────────────────────────────
from pypdf import PdfReader

def load_pdf(file_path: str) -> list[dict]:
    """載入 PDF 並保留頁碼資訊。"""
    reader = PdfReader(file_path)
    pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        if text.strip():  # 跳過空白頁
            pages.append({
                "content": text,
                "metadata": {
                    "source": file_path,
                    "page": i + 1,
                    "total_pages": len(reader.pages),
                }
            })
    return pages


# ── 讀取 CSV（結構化資料） ────────────────────────────────
def load_csv_as_documents(file_path: str) -> list[dict]:
    """
    把 CSV 的每一行轉換成一個文字文件。
    適合產品目錄、FAQ 等結構化資料。
    """
    df = pd.read_csv(file_path)
    documents = []

    for _, row in df.iterrows():
        # 把每行轉成「欄位：值」的文字格式
        content = "\n".join([f"{col}: {val}" for col, val in row.items()])
        documents.append({
            "content": content,
            "metadata": {
                "source": file_path,
                "row_index": row.name,
            }
        })
    return documents


# ── 使用 Unstructured 處理複雜格式 ───────────────────────
from unstructured.partition.pdf import partition_pdf
from unstructured.partition.html import partition_html

def load_complex_pdf(file_path: str) -> list[dict]:
    """
    使用 Unstructured 庫處理有表格、圖片的複雜 PDF。
    比 pypdf 更強大，但也更慢。
    """
    elements = partition_pdf(
        filename=file_path,
        extract_images_in_pdf=False,    # 設為 True 可以提取圖片中的文字（需要 OCR）
        infer_table_structure=True,      # 嘗試識別表格結構
        include_page_breaks=True,
    )

    documents = []
    for element in elements:
        if hasattr(element, 'text') and element.text.strip():
            documents.append({
                "content": element.text,
                "metadata": {
                    "source": file_path,
                    "element_type": type(element).__name__,  # Title, NarrativeText, Table 等
                    "page": element.metadata.page_number if hasattr(element.metadata, 'page_number') else None
                }
            })
    return documents
```

---

## Step 2：轉換（Transform）——把大象切成小塊

這是整個 ETL 管線中最需要藝術感的部分。切得太小，上下文不夠；切得太大，搜尋精度下降。

### 四種主要切分策略

#### 策略 1：固定大小切分（Fixed-size Chunking）

```
  原始文字（假設用 ▓ 代表每個字）

  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
  ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓

  切成每塊 20 字，重疊 5 字（overlap）：

  Chunk 1: ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓         （第 1-20 字）
  Chunk 2:              ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓  （第 16-35 字）
  Chunk 3:                           ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ （第 31-50 字）
                            └──────┘
                           重疊區域（Overlap）
```

```python
from llama_index.core.node_parser import SentenceSplitter

# 固定大小切分
splitter = SentenceSplitter(
    chunk_size=512,        # 每塊最大 512 tokens
    chunk_overlap=50,      # 相鄰塊重疊 50 tokens（保持上下文連貫）
)

nodes = splitter.get_nodes_from_documents(documents)
print(f"切成了 {len(nodes)} 個片段")
print(f"平均大小：{sum(len(n.text) for n in nodes) / len(nodes):.0f} 字元")
```

**優點**：簡單快速，容易預測結果
**缺點**：可能在句子中間切斷，破壞語意

---

#### 策略 2：遞迴字元切分（Recursive Character Splitting）

這是最常用的策略，按照分隔符優先順序切分：

```
優先順序：段落分隔（\n\n）> 換行（\n）> 句號（。！？）> 空格 > 字元
```

```python
from llama_index.core.node_parser import SentenceSplitter

# LlamaIndex 的 SentenceSplitter 本質上就是遞迴切分
# 它會嘗試在自然的邊界切分（句子、段落等）

# 更細緻的控制，使用 LangChain 的 RecursiveCharacterTextSplitter
from langchain.text_splitter import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,          # 目標大小（字元）
    chunk_overlap=50,        # 重疊大小
    separators=[
        "\n\n",              # 首先嘗試在段落邊界切分
        "\n",                # 然後在行邊界
        "。",                # 然後在中文句號
        "！",
        "？",
        "，",                # 最後在逗號
        " ",                 # 然後在空格
        "",                  # 最後不得已才逐字切
    ],
    length_function=len,
)

chunks = splitter.split_text(long_text)
```

---

#### 策略 3：語義切分（Semantic Chunking）

這是最「聰明」的方法——根據語意相似度決定在哪裡切。

```
想法：當兩個句子的語意距離突然變大，就是切分點。

句子 1: 「今天天氣很好。」
句子 2: 「適合外出踏青。」      ← 語意相近，放在同一塊
句子 3: 「但是股市下跌了。」   ← 語意突然轉換，切分！
句子 4: 「外資大量賣出。」
句子 5: 「分析師認為還會跌。」  ← 語意相近，放在同一塊
```

```python
from llama_index.core.node_parser import SemanticSplitterNodeParser
from llama_index.embeddings.openai import OpenAIEmbedding

# 需要 Embedding 模型來計算語意相似度
embed_model = OpenAIEmbedding(model="text-embedding-3-small")

semantic_splitter = SemanticSplitterNodeParser(
    buffer_size=1,              # 每次比較相鄰的句子數
    breakpoint_percentile_threshold=95,  # 語意距離超過第幾百分位才切分
    embed_model=embed_model,
)

nodes = semantic_splitter.get_nodes_from_documents(documents)
```

**優點**：語意最完整，不會在意思說一半的地方切斷
**缺點**：需要 Embedding 計算（慢且有成本），chunk 大小不均勻

---

#### 策略 4：結構感知切分（Structure-aware Chunking）

針對有明顯結構的文件（Markdown、HTML、程式碼）使用結構本身作為切分依據。

```python
from llama_index.core.node_parser import MarkdownNodeParser

# 針對 Markdown 文件，按標題結構切分
md_parser = MarkdownNodeParser()
nodes = md_parser.get_nodes_from_documents(markdown_documents)

# 每個 Node 會包含標題層級資訊
for node in nodes[:3]:
    print(f"標題：{node.metadata.get('header_path', '無')}")
    print(f"內容（前 100 字）：{node.text[:100]}")
    print()
```

```python
from llama_index.core.node_parser import CodeSplitter

# 針對程式碼，用 AST（抽象語法樹）來切分，確保函式完整
code_parser = CodeSplitter(
    language="python",
    chunk_lines=40,             # 每塊最多 40 行
    chunk_lines_overlap=5,
    max_chars=1500,
)
```

---

## 切分策略比較

| 策略 | 速度 | 語意完整性 | 適用場景 |
|------|------|-----------|----------|
| 固定大小 | ⚡⚡⚡ 超快 | ⭐ 差 | 快速原型、文字很均勻 |
| 遞迴字元 | ⚡⚡ 快 | ⭐⭐⭐ 中等 | **大多數場景的首選** |
| 語義切分 | ⚡ 慢（需 Embedding）| ⭐⭐⭐⭐⭐ 最好 | 高品質需求、文字風格多變 |
| 結構感知 | ⚡⚡ 快 | ⭐⭐⭐⭐ 好 | Markdown 文件、程式碼、HTML |

---

## Step 3：中繼資料（Metadata）——別忘了貼標籤

切分文件就像把書切成一頁一頁。問題是：切完之後，每一頁還知道自己是哪本書的第幾頁嗎？

**中繼資料就是每個 Chunk 的「出生證明」。**

```python
from llama_index.core import Document
from datetime import datetime

def enrich_document_with_metadata(
    content: str,
    source_file: str,
    page_number: int = None,
    section: str = None,
) -> Document:
    """
    建立帶有豐富中繼資料的文件物件。
    這些資訊在後續的過濾和引用來源時非常有用。
    """
    return Document(
        text=content,
        metadata={
            # 來源資訊
            "file_name": Path(source_file).name,
            "file_path": source_file,
            "file_type": Path(source_file).suffix,

            # 位置資訊
            "page_number": page_number,
            "section": section,

            # 時間資訊
            "indexed_at": datetime.now().isoformat(),

            # 自定義標籤（根據你的業務需求加）
            "department": "技術文件",
            "version": "v2.0",
            "language": "zh-TW",
        },
        # 告訴 LlamaIndex 哪些 metadata 要包含在給 LLM 的 prompt 裡
        metadata_template="{key}: {value}",
        text_template="來源：{metadata_str}\n\n{content}",
    )
```

### 為什麼 Metadata 這麼重要？

```python
# 查詢時可以加入過濾條件
from llama_index.core.vector_stores import MetadataFilter, FilterOperator

# 只在「技術文件」且「版本 >= v2.0」的文件中搜尋
filters = [
    MetadataFilter(key="department", value="技術文件"),
    MetadataFilter(key="version", value="v2.0"),
]

# 回答問題時可以引用來源
# 例如：「根據 [product-spec.pdf, 第 15 頁] 的資訊...」
```

---

## 完整 ETL 管線實作

現在讓我們把所有東西組合起來，建立一個完整的 ETL 管線：

```python
"""
完整 RAG ETL 管線
==============
從原始文件到向量資料庫的完整流程。
"""

import os
from pathlib import Path
from typing import List, Optional
import hashlib
import json

from llama_index.core import (
    Document,
    VectorStoreIndex,
    SimpleDirectoryReader,
    StorageContext,
)
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core.schema import TextNode


class DocumentETLPipeline:
    """
    文件 ETL 管線。

    使用方式：
        pipeline = DocumentETLPipeline(
            chunk_size=512,
            chunk_overlap=50
        )
        index = pipeline.run("./documents")
    """

    def __init__(
        self,
        chunk_size: int = 512,
        chunk_overlap: int = 50,
        embed_model_name: str = "text-embedding-3-small",
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

        # 初始化切分器
        self.splitter = SentenceSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

        # 初始化 Embedding 模型
        self.embed_model = OpenAIEmbedding(model=embed_model_name)

        # 追蹤已處理的文件（避免重複處理）
        self.processed_files_cache = {}

    def extract(self, input_dir: str) -> List[Document]:
        """
        Step 1：萃取——從目錄載入所有文件。
        """
        print(f"[Extract] 掃描目錄：{input_dir}")
        reader = SimpleDirectoryReader(
            input_dir=input_dir,
            recursive=True,
            required_exts=[".pdf", ".txt", ".md", ".csv"],
        )
        documents = reader.load_data()
        print(f"[Extract] 載入了 {len(documents)} 份文件")
        return documents

    def transform(self, documents: List[Document]) -> List[TextNode]:
        """
        Step 2：轉換——清理、豐富中繼資料、切分文件。
        """
        print(f"[Transform] 開始處理 {len(documents)} 份文件...")

        # 豐富中繼資料
        enriched_docs = []
        for doc in documents:
            # 計算文件 hash（用來偵測文件是否已更新）
            doc_hash = hashlib.md5(doc.text.encode()).hexdigest()
            doc.metadata["content_hash"] = doc_hash
            doc.metadata["char_count"] = len(doc.text)
            doc.metadata["word_count"] = len(doc.text.split())
            enriched_docs.append(doc)

        # 切分文件
        nodes = self.splitter.get_nodes_from_documents(enriched_docs)
        print(f"[Transform] 切分成 {len(nodes)} 個片段")

        # 統計資訊
        sizes = [len(n.text) for n in nodes]
        print(f"[Transform] 片段大小：最小={min(sizes)}, "
              f"最大={max(sizes)}, 平均={sum(sizes)/len(sizes):.0f} 字元")

        return nodes

    def load(self, nodes: List[TextNode]) -> VectorStoreIndex:
        """
        Step 3：載入——建立向量索引。
        """
        print(f"[Load] 開始向量化 {len(nodes)} 個片段...")

        # 建立向量索引（這一步會呼叫 Embedding API）
        index = VectorStoreIndex(
            nodes,
            embed_model=self.embed_model,
            show_progress=True,
        )

        print(f"[Load] 向量索引建立完成！")
        return index

    def run(self, input_dir: str) -> VectorStoreIndex:
        """
        執行完整的 ETL 管線。
        """
        print("=" * 60)
        print("開始 ETL 管線...")
        print("=" * 60)

        documents = self.extract(input_dir)
        nodes = self.transform(documents)
        index = self.load(nodes)

        print("=" * 60)
        print(f"ETL 完成！共處理 {len(documents)} 份文件，"
              f"建立 {len(nodes)} 個可搜尋片段。")
        print("=" * 60)

        return index


# 使用範例
if __name__ == "__main__":
    pipeline = DocumentETLPipeline(
        chunk_size=512,
        chunk_overlap=50,
    )

    # 執行管線
    index = pipeline.run("./documents")

    # 立刻測試
    query_engine = index.as_query_engine()
    response = query_engine.query("這份文件的主要內容是什麼？")
    print(f"\n查詢結果：{response}")
```

---

## 動手做 Lab 2.1：視覺化不同切分策略的效果

這個 Lab 會幫助你直觀地看到不同切分策略的差異。

```python
"""
Lab 2.1：視覺化文件切分策略比較
需要安裝：pip install matplotlib
"""

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from llama_index.core.node_parser import (
    SentenceSplitter,
    TokenTextSplitter,
)

# 準備測試文件（一篇技術文章）
SAMPLE_DOCUMENT = """
人工智慧（AI）是電腦科學的一個分支，致力於開發能夠模仿人類智能的系統。

近年來，大型語言模型（LLM）的崛起徹底改變了 AI 的發展方向。GPT、Claude、
Gemini 等模型展示了驚人的語言理解和生成能力，讓許多過去被認為需要人類智慧
才能完成的任務變得可以自動化。

然而，LLM 也有明顯的限制。首先是知識截止日問題——模型只知道訓練資料截止日
之前的資訊。其次是幻覺問題——模型可能生成聽起來合理但實際上錯誤的資訊。
第三是 Context Window 限制——每次對話只能處理有限量的文字。

檢索增強生成（RAG）技術應運而生，正是為了解決上述問題。RAG 的核心思想是
讓 LLM 在回答問題之前，先從外部知識庫中檢索相關資訊，然後根據這些資訊
生成答案。這就像讓一個學生從閉卷考試改為開卷考試。

RAG 系統通常包含三個主要組件：文件索引、語意搜尋和答案生成。文件索引負責
將原始文件切分成小塊並轉換為向量表示；語意搜尋根據用戶問題找到最相關的
文件塊；答案生成則將找到的資訊和用戶問題一起交給 LLM 生成最終答案。
"""


def compare_chunking_strategies(text: str):
    """比較不同切分策略的效果。"""

    strategies = {
        "固定 128 tokens\n（小塊）": SentenceSplitter(
            chunk_size=128, chunk_overlap=0
        ),
        "固定 256 tokens\n（中塊）": SentenceSplitter(
            chunk_size=256, chunk_overlap=0
        ),
        "固定 512 tokens\n（大塊）": SentenceSplitter(
            chunk_size=512, chunk_overlap=0
        ),
        "256 tokens\n重疊 50": SentenceSplitter(
            chunk_size=256, chunk_overlap=50
        ),
    }

    from llama_index.core import Document

    doc = Document(text=text)
    results = {}

    for name, splitter in strategies.items():
        nodes = splitter.get_nodes_from_documents([doc])
        chunk_sizes = [len(n.text) for n in nodes]
        results[name] = {
            "count": len(nodes),
            "sizes": chunk_sizes,
            "avg": np.mean(chunk_sizes),
            "min": min(chunk_sizes),
            "max": max(chunk_sizes),
        }

    return results


def visualize_chunking(results: dict):
    """視覺化切分結果。"""
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle("文件切分策略比較", fontsize=16, fontweight="bold")

    strategies = list(results.keys())
    colors = ["#3498db", "#e74c3c", "#2ecc71", "#f39c12"]

    for idx, (name, data) in enumerate(results.items()):
        ax = axes[idx // 2][idx % 2]
        sizes = data["sizes"]

        # 畫長條圖（每個 Chunk 的大小）
        x = range(len(sizes))
        bars = ax.bar(x, sizes, color=colors[idx], alpha=0.8, edgecolor="white")

        # 加上平均線
        ax.axhline(
            y=data["avg"],
            color="red",
            linestyle="--",
            linewidth=1.5,
            label=f"平均：{data['avg']:.0f} 字元",
        )

        ax.set_title(f"{name}\n（共 {data['count']} 個片段）", fontsize=11)
        ax.set_xlabel("片段編號")
        ax.set_ylabel("字元數")
        ax.legend(fontsize=9)

        # 標注最小和最大值
        ax.annotate(
            f"最小：{data['min']}",
            xy=(sizes.index(data["min"]), data["min"]),
            xytext=(5, 10),
            textcoords="offset points",
            fontsize=8,
            color="blue",
        )

    plt.tight_layout()
    plt.savefig("chunking_comparison.png", dpi=150, bbox_inches="tight")
    print("圖表已儲存為 chunking_comparison.png")
    plt.show()

    # 印出統計摘要
    print("\n=== 切分策略統計摘要 ===")
    print(f"{'策略':<20} {'片段數':>8} {'平均大小':>10} {'最小':>8} {'最大':>8}")
    print("-" * 60)
    for name, data in results.items():
        clean_name = name.replace("\n", " ")
        print(
            f"{clean_name:<20} {data['count']:>8} "
            f"{data['avg']:>10.0f} {data['min']:>8} {data['max']:>8}"
        )


# 執行比較
results = compare_chunking_strategies(SAMPLE_DOCUMENT)
visualize_chunking(results)
```

### 預期輸出

```
=== 切分策略統計摘要 ===
策略                    片段數    平均大小    最小    最大
------------------------------------------------------------
固定 128 tokens（小塊）      8        156      98     204
固定 256 tokens（中塊）      4        312     198     412
固定 512 tokens（大塊）      2        624     580     668
256 tokens 重疊 50           5        298     198     412
```

---

## Lab 2.2：處理真實的 PDF 文件

```python
"""
Lab 2.2：從 PDF 到向量索引的完整流程
"""

import os
import requests
from pathlib import Path

# 下載一個測試用的 PDF（Attention Is All You Need 論文）
def download_sample_pdf():
    url = "https://arxiv.org/pdf/1706.03762.pdf"
    output_path = Path("./test_documents/attention.pdf")
    output_path.parent.mkdir(exist_ok=True)

    if not output_path.exists():
        print("下載測試 PDF...")
        response = requests.get(url)
        output_path.write_bytes(response.content)
        print(f"下載完成：{output_path}")
    return str(output_path)


# 方法 1：用 LlamaIndex 直接讀
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex
from llama_index.core.node_parser import SentenceSplitter

def build_pdf_index(pdf_path: str):
    """載入 PDF 並建立索引。"""
    # 載入
    reader = SimpleDirectoryReader(input_files=[pdf_path])
    documents = reader.load_data()
    print(f"載入了 {len(documents)} 頁")

    # 切分
    splitter = SentenceSplitter(chunk_size=512, chunk_overlap=50)
    nodes = splitter.get_nodes_from_documents(documents)
    print(f"切成了 {len(nodes)} 個片段")

    # 印出前 3 個片段預覽
    print("\n=== 片段預覽 ===")
    for i, node in enumerate(nodes[:3]):
        print(f"\n[片段 {i+1}]")
        print(f"來源頁碼：{node.metadata.get('page_label', '未知')}")
        print(f"內容：{node.text[:200]}...")
        print("-" * 40)

    # 建立索引
    index = VectorStoreIndex(nodes, show_progress=True)
    return index


# 執行
pdf_path = download_sample_pdf()
index = build_pdf_index(pdf_path)

# 測試查詢
query_engine = index.as_query_engine()
questions = [
    "What is the attention mechanism?",
    "How many layers does the Transformer have?",
    "What is the training data used?",
]

print("\n=== 查詢測試 ===")
for q in questions:
    print(f"\nQ: {q}")
    response = query_engine.query(q)
    print(f"A: {response.response[:300]}...")
```

---

## 常見問題 FAQ

**Q: Chunk Size 要設多大才對？**

沒有標準答案，但有規律可循：

| 場景 | 建議大小 | 原因 |
|------|----------|------|
| 技術文件、說明書 | 512-1024 tokens | 需要保留足夠上下文 |
| FAQ、條款文件 | 256-512 tokens | 每個問答本身就是完整單位 |
| 新聞文章、部落格 | 512-1024 tokens | 段落為基本語意單位 |
| 程式碼 | 以函式為單位 | 完整函式比硬切行數更有意義 |

**黃金法則**：Chunk 要大到包含一個完整想法，小到讓搜尋能精確定位。

---

**Q: Chunk Overlap 的作用是什麼？**

當一個問題的答案剛好橫跨兩個 Chunk 的邊界時，沒有 Overlap 可能兩個 Chunk 都找不到完整答案。Overlap 讓邊界區域在相鄰的兩個 Chunk 都有備份。

一般設定為 chunk_size 的 10%-20%。

---

**Q: 我的文件有圖表和圖片，怎麼處理？**

圖表和圖片不能直接被文字 Embedding 模型處理，有幾個選項：

1. **忽略**（最簡單）：如果圖表在文字中有說明，忽略圖表本身通常沒問題
2. **OCR**：用 Tesseract 或 unstructured 的 OCR 功能提取圖片中的文字
3. **多模態模型**：用 GPT-4V 等視覺模型先把圖表轉成文字描述，再進行向量化

---

**Q: 每次都要重新處理所有文件嗎？**

不需要。你可以：
1. 用文件的 hash 值追蹤哪些文件已處理
2. 只處理新增或修改的文件（增量更新）
3. 把向量索引持久化到磁碟，下次直接載入

```python
# 儲存索引到磁碟
index.storage_context.persist(persist_dir="./storage")

# 下次直接載入
from llama_index.core import StorageContext, load_index_from_storage
storage_context = StorageContext.from_defaults(persist_dir="./storage")
index = load_index_from_storage(storage_context)
```

---

## 重點回顧 📋

```
┌─────────────────────────────────────────────────────────┐
│                    第二章重點整理                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  🔑 為什麼要切分文件？                                  │
│     - Context Window 有上限，不能塞整份文件             │
│     - 切成小塊才能精確搜尋（大海撈針 → 小水缸撈針）    │
│     - 每次查詢只送相關片段，節省 token 成本             │
│                                                         │
│  🔑 四種切分策略：                                      │
│     - 固定大小：快，但可能切斷語意                      │
│     - 遞迴字元：大多數場景的首選                        │
│     - 語義切分：最好，但需要 Embedding（慢且有成本）    │
│     - 結構感知：適合 Markdown、HTML、程式碼             │
│                                                         │
│  🔑 中繼資料（Metadata）超重要：                       │
│     - 儲存來源文件、頁碼、章節等資訊                    │
│     - 讓搜尋可以加入過濾條件                            │
│     - 答案可以引用具體來源                              │
│                                                         │
│  🔑 ETL = Extract + Transform + Load                   │
│     Extract：從各種格式讀取文件                         │
│     Transform：清理、豐富中繼資料、切分                 │
│     Load：向量化並存入資料庫                            │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 課後練習

### 練習 2.1：基礎（⭐）

用 `SentenceSplitter` 分別用 128、256、512 token 切分同一份文件，然後回答：
- 哪個大小讓「退款政策有哪些條件？」這個問題能被最準確地回答？
- 為什麼？

### 練習 2.2：進階（⭐⭐）

在 Lab 2.1 的基礎上，加入以下功能：
- 計算並顯示每種策略的「語意完整性」：選取 5 個 Chunks，人工判斷有幾個在語意上是「完整」的（沒有被切斷的句子）
- 計算每種策略的「資訊重疊率」：有 Overlap 的策略，其重複資訊佔總資料的比例是多少？

### 練習 2.3：挑戰（⭐⭐⭐）

實作一個「智慧切分器」：
- 首先嘗試按段落（`\n\n`）切分
- 如果某個段落超過 512 tokens，再用句子切分它
- 如果某個段落小於 50 tokens，把它合併到前一個段落
- 每個 Chunk 都加入段落編號和文件來源的 Metadata

---

## 下一章預告

你已經把文件切好了。但切好的文字怎麼讓電腦「理解」，然後根據「意思」來搜尋，而不只是關鍵字比對？

**第三章：數字的靈魂邊界**

> 「king - man + woman = queen？數學怎麼懂得語意？」

我們會學習向量 Embedding 的神奇魔法，以及如何用 FAISS 和 Qdrant 建立超快速的語意搜尋引擎。

---

*第二章完 · 繼續閱讀 [第三章](./ch03-vectors-embeddings.md)*

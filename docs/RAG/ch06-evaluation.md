# 第六章：你是真的懂還是在裝懂

## RAG 評估與 Ragas 框架

---

> 「老師，我覺得我這次考試答得很好。」
>
> 「嗯⋯⋯你知道答案是錯的嗎？」
>
> 「但我說得很流暢！」

---

你花了五章的時間建了一個 RAG 系統。它看起來很棒，回答問題有條有理，引用了文件，語氣也很專業。

但你怎麼知道它的答案是**真的正確**，而不只是**聽起來正確**？

這就是評估（Evaluation）的意義。

一個沒有評估的 RAG 系統，就像一個沒有考試的教育制度——你永遠不知道學生真的學會了，還是只會背答案。

---

## 腦力激盪 🧠

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│  問題 1：如果你是評審，如何評分一個                    │
│          「開卷考試」的答案？                           │
│          你會關注什麼面向？                             │
│                                                         │
│  問題 2：假設某個 RAG 系統的「Faithfulness」（忠實度） │
│          分數是 0.3。這代表什麼？                       │
│          是好還是壞？                                   │
│                                                         │
│  問題 3：你能想到三種「聽起來正確但實際上錯的」        │
│          AI 回答場景嗎？                                │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 開卷考試的評分難題

要評估一個開卷考試的答案，你需要檢查四件事：

```
開卷考試評分維度
════════════════════════════════════════════════════════════

  學生的答案是否忠實於參考書的內容？
  ┌──────────────────────────────────────────────────────┐
  │  維度 1：忠實度（Faithfulness）                      │
  │  答案有沒有超出或矛盾參考書的內容？                  │
  │  低分代表：AI 在捏造資訊（幻覺）                    │
  └──────────────────────────────────────────────────────┘

  學生的答案是否真的回答了問題？
  ┌──────────────────────────────────────────────────────┐
  │  維度 2：答案相關性（Answer Relevance）              │
  │  答案有沒有切中問題的核心？                          │
  │  低分代表：AI 答非所問                               │
  └──────────────────────────────────────────────────────┘

  老師給的參考書有沒有涵蓋需要的內容？
  ┌──────────────────────────────────────────────────────┐
  │  維度 3：上下文召回率（Context Recall）              │
  │  搜尋到的文件有沒有覆蓋問題需要的所有資訊？          │
  │  低分代表：RAG 搜尋時遺漏了重要文件                 │
  └──────────────────────────────────────────────────────┘

  搜尋到的文件有多少是真正有用的？
  ┌──────────────────────────────────────────────────────┐
  │  維度 4：上下文精確度（Context Precision）           │
  │  找到的文件中，有多少比例是真正相關的？              │
  │  低分代表：搜尋找到太多不相關的文件（雜訊多）        │
  └──────────────────────────────────────────────────────┘
```

這四個維度，就是 **Ragas 框架**的核心指標。

---

## Ragas 安裝與設定

```bash
pip install ragas
pip install llama-index  # 如果還沒安裝
```

```python
import os
from ragas import evaluate
from ragas.metrics import (
    faithfulness,           # 忠實度
    answer_relevancy,       # 答案相關性
    context_recall,         # 上下文召回率
    context_precision,      # 上下文精確度
)
from datasets import Dataset
```

---

## 評估資料集：黃金標準

要使用 Ragas，你需要準備**評估資料集**，包含：

| 欄位 | 說明 | 是否必填 |
|------|------|--------|
| `question` | 測試問題 | ✅ 必填 |
| `answer` | RAG 系統的回答 | ✅ 必填 |
| `contexts` | RAG 搜尋到的文件片段（list） | ✅ 必填 |
| `ground_truth` | 標準答案（人工撰寫） | 計算 Context Recall 時需要 |

```python
# 評估資料集範例
evaluation_data = {
    "question": [
        "RAG 系統的退款政策是什麼？",
        "安裝需要多少記憶體？",
        "如何申請退款？",
    ],
    "answer": [
        "購買後 30 天內可申請退款，超過 30 天需要憑證。",
        "系統需要至少 8GB RAM，建議 16GB 以上。",
        "您可以透過帳號的訂單管理頁面，或發送郵件至 refund@example.com 申請退款。",
    ],
    "contexts": [
        # 每個問題對應搜尋到的文件片段（list of str）
        [
            "Q1：如何申請退款？A1：在購買後 30 天內，您可以透過以下方式...",
            "退款政策：30 天內無條件退款，超過需提供憑證...",
        ],
        [
            "系統需求：記憶體最低需求為 8GB RAM，建議 16GB 以上。",
            "作業系統支援 Windows 10、macOS 12、Ubuntu 20.04...",
        ],
        [
            "Q1：如何申請退款？A1：登入帳號 → 訂單管理 → 申請退款。也可發送郵件至 refund@example.com",
            "退款將在 3-5 個工作日內退回原付款方式。",
        ],
    ],
    "ground_truth": [
        "購買後 30 天內可申請無條件退款，超過 30 天需要提供購買憑證。",
        "安裝本產品需要最低 8GB RAM，建議 16GB 以上。",
        "申請退款的方法：1. 登入帳號 → 訂單管理 → 申請退款；2. 發送郵件至 refund@example.com。",
    ],
}
```

---

## 完整 Ragas 評估實作

```python
"""
完整 Ragas 評估管線
"""

import os
from pathlib import Path
from typing import List, Dict, Any
import pandas as pd
from datasets import Dataset

from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_recall,
    context_precision,
)
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from llama_index.core import VectorStoreIndex, Document
from llama_index.core.node_parser import SentenceSplitter


# ── 設定評估用的 LLM 和 Embedding ──────────────────────────
# Ragas 使用 LLM 作為「AI 評審」來計算某些指標
evaluator_llm = LangchainLLMWrapper(
    ChatOpenAI(model="gpt-4o-mini", temperature=0)
)
evaluator_embeddings = LangchainEmbeddingsWrapper(
    OpenAIEmbeddings(model="text-embedding-3-small")
)


class RAGEvaluator:
    """
    RAG 系統評估器。

    使用 Ragas 框架計算四個核心指標：
    - Faithfulness（忠實度）
    - Answer Relevancy（答案相關性）
    - Context Recall（上下文召回率）
    - Context Precision（上下文精確度）
    """

    def __init__(self, rag_query_engine):
        self.query_engine = rag_query_engine

    def collect_rag_responses(
        self,
        test_questions: List[str],
        ground_truths: List[str],
    ) -> Dataset:
        """
        對每個測試問題執行 RAG，收集答案和使用的文件。
        """
        print(f"收集 {len(test_questions)} 個問題的 RAG 回應...")

        answers = []
        contexts = []

        for i, question in enumerate(test_questions):
            print(f"  [{i+1}/{len(test_questions)}] 處理：{question[:40]}...")

            # 執行 RAG 查詢
            response = self.query_engine.query(question)

            # 收集答案
            answers.append(str(response))

            # 收集使用的文件片段
            context_texts = [
                node.text for node in response.source_nodes
            ]
            contexts.append(context_texts)

        # 建立 Dataset
        data = {
            "question": test_questions,
            "answer": answers,
            "contexts": contexts,
            "ground_truth": ground_truths,
        }

        return Dataset.from_dict(data)

    def evaluate(
        self,
        dataset: Dataset,
        metrics=None,
    ) -> Dict[str, float]:
        """
        執行評估，返回各指標分數。
        """
        if metrics is None:
            metrics = [
                faithfulness,
                answer_relevancy,
                context_recall,
                context_precision,
            ]

        print("\n開始評估（這需要幾分鐘，因為要多次呼叫 LLM）...")

        result = evaluate(
            dataset=dataset,
            metrics=metrics,
            llm=evaluator_llm,
            embeddings=evaluator_embeddings,
        )

        return result

    def generate_report(self, result, output_path: str = "./rag_evaluation_report.csv"):
        """
        生成評估報告。
        """
        # 轉換為 DataFrame
        df = result.to_pandas()

        # 計算整體分數
        metric_columns = [
            "faithfulness",
            "answer_relevancy",
            "context_recall",
            "context_precision",
        ]

        available_metrics = [col for col in metric_columns if col in df.columns]

        print("\n" + "=" * 60)
        print("RAG 評估報告")
        print("=" * 60)

        print("\n📊 整體指標：")
        for metric in available_metrics:
            score = df[metric].mean()
            status = self._score_to_status(score)
            print(f"  {metric:30s}: {score:.4f} {status}")

        # 找出表現最差的問題
        print("\n❌ 需要關注的問題（忠實度 < 0.7）：")
        if "faithfulness" in df.columns:
            low_faith = df[df["faithfulness"] < 0.7][
                ["question", "faithfulness", "answer"]
            ]
            if len(low_faith) > 0:
                for _, row in low_faith.iterrows():
                    print(f"\n  問題：{row['question']}")
                    print(f"  忠實度：{row['faithfulness']:.4f}")
                    print(f"  答案（前100字）：{row['answer'][:100]}...")
            else:
                print("  (所有問題的忠實度都 >= 0.7，表現良好！)")

        # 儲存詳細報告
        df.to_csv(output_path, index=False, encoding="utf-8-sig")
        print(f"\n📁 詳細報告已儲存至：{output_path}")

        return df

    @staticmethod
    def _score_to_status(score: float) -> str:
        if score >= 0.8:
            return "✅ 優秀"
        elif score >= 0.6:
            return "⚠️ 尚可（需改善）"
        else:
            return "❌ 需要重大改善"
```

---

## 動手做 Lab 6.1：評估一個完整的 RAG 系統

```python
"""
Lab 6.1：端到端評估 RAG 系統
"""

from llama_index.core import VectorStoreIndex, Document
from llama_index.core.node_parser import SentenceSplitter


# ── 準備知識庫 ──────────────────────────────────────────────
KNOWLEDGE_BASE = [
    Document(text="""
產品退款政策（更新日期：2026年1月）

標準退款政策：
購買後 30 天內，用戶可以申請無條件退款。
超過 30 天但未超過 90 天，需提供有效的購買憑證及退款理由。
超過 90 天後，不接受退款申請。

申請方式：
方式一：登入帳號 → 訂單管理 → 找到訂單 → 點擊「申請退款」
方式二：發送郵件至 refund@example.com，主旨填寫「退款申請 - 訂單編號」
方式三：撥打客服電話 0800-888-888（服務時間：週一至週五 09:00-18:00）

退款時程：
信用卡退款：3-5 個工作日
ATM 轉帳退款：5-7 個工作日
LINE Pay 退款：1-3 個工作日

特別說明：
- 已下載或使用的數位內容不予退款
- 訂閱制服務的未使用天數可按比例退款
"""),
    Document(text="""
系統需求與安裝說明

最低系統需求：
- 作業系統：Windows 10（64位元）、macOS 12 Monterey、Ubuntu 20.04 LTS
- 處理器：Intel Core i5 第八代或 AMD Ryzen 5 3000 系列（含）以上
- 記憶體：8GB RAM（建議 16GB 以上）
- 儲存空間：10GB 可用硬碟空間
- 顯示卡：支援 OpenGL 4.0 的顯示卡
- 網路：安裝及啟動需要網路連線

安裝步驟：
1. 前往 www.example.com/download 下載安裝程式
2. 確認下載的安裝程式 SHA-256 雜湊值（防止篡改）
3. 以系統管理員身份執行安裝程式
4. 依照安裝精靈的指示完成安裝（約需 5-10 分鐘）
5. 安裝完成後，輸入您的授權碼啟動軟體

常見安裝問題：
Q：安裝時提示「需要系統管理員權限」
A：右鍵點擊安裝程式，選擇「以系統管理員身份執行」

Q：Mac 上提示「無法驗證開發者」
A：前往系統偏好設定 → 安全性與隱私權 → 點擊「仍要打開」
"""),
    Document(text="""
訂閱方案說明

方案一：個人版
月費：NT$ 299/月（年繳 NT$ 2,988，等同 NT$ 249/月）
功能：
- 1 個用戶帳號
- 最多 2 台裝置同時使用
- 10GB 雲端儲存空間
- 基本技術支援（工作日 09:00-18:00）

方案二：專業版
月費：NT$ 599/月（年繳 NT$ 5,988，等同 NT$ 499/月）
功能：
- 1 個用戶帳號
- 最多 5 台裝置同時使用
- 50GB 雲端儲存空間
- 進階分析功能
- 優先技術支援（7天 × 24小時）
- API 存取權限（每月 10,000 次請求）

方案三：企業版
月費：洽詢業務（依席次計算）
功能：
- 無限用戶帳號
- 集中管理後台
- 無限雲端儲存空間
- 進階安全功能（SSO、稽核日誌）
- 專屬客戶成功經理
- SLA 保證 99.9% 可用率

升級方案：
登入帳號後，前往設定 → 訂閱管理 → 升級方案。
升級立即生效，費用按剩餘天數按日計算。

降級方案：
降級申請在下一個計費週期開始時生效。
如當前周期已付費，差額以點數退還，可在下次付費時使用。
"""),
]

# 建立 RAG 系統
documents_with_splitter = KNOWLEDGE_BASE
index = VectorStoreIndex.from_documents(
    documents_with_splitter,
    transformations=[SentenceSplitter(chunk_size=512, chunk_overlap=50)],
    show_progress=True,
)
query_engine = index.as_query_engine(similarity_top_k=3)


# ── 準備評估測試集 ──────────────────────────────────────────
TEST_QUESTIONS = [
    "購買後多久可以申請退款？",
    "安裝這個軟體需要多少記憶體？",
    "專業版方案一個月多少錢？支援幾台裝置？",
    "怎麼申請退款？有哪些方式？",
    "企業版有 SLA 保證嗎？",
]

GROUND_TRUTHS = [
    "購買後 30 天內可以申請無條件退款。超過 30 天但未超過 90 天，需提供購買憑證和退款理由。超過 90 天後不接受退款。",
    "最低需要 8GB RAM，建議 16GB 以上。",
    "專業版月費 NT$ 599/月（月繳），年繳 NT$ 5,988（等同 NT$ 499/月）。支援最多 5 台裝置同時使用。",
    "申請退款有三種方式：1. 登入帳號在訂單管理申請；2. 發郵件至 refund@example.com；3. 撥打 0800-888-888 客服電話。",
    "是的，企業版提供 SLA 保證 99.9% 可用率。",
]


# ── 執行評估 ────────────────────────────────────────────────
evaluator = RAGEvaluator(query_engine)

# 收集 RAG 的回應
dataset = evaluator.collect_rag_responses(TEST_QUESTIONS, GROUND_TRUTHS)

# 執行評估
result = evaluator.evaluate(dataset)

# 生成報告
df = evaluator.generate_report(result)
```

---

## Lab 6.2：自動生成評估資料集

手動寫測試題太慢？用 LLM 來幫你自動生成！

```python
"""
Lab 6.2：自動生成評估資料集
"""

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
import json
from typing import List, Tuple


def generate_evaluation_dataset(
    documents: list,
    n_questions: int = 20,
    question_types: list = None,
) -> list[dict]:
    """
    從知識庫文件自動生成測試問題和標準答案。

    question_types 可以是：
    - "factual"：事實性問題（「X 是什麼？」）
    - "comparison"：比較性問題（「X 和 Y 有什麼差別？」）
    - "procedural"：程序性問題（「如何做 X？」）
    - "inference"：推論性問題（需要結合多個資訊才能回答）
    """
    if question_types is None:
        question_types = ["factual", "procedural", "comparison"]

    llm = ChatOpenAI(model="gpt-4o", temperature=0.7)
    generated_data = []

    # 對每份文件生成問題
    for doc in documents:
        doc_text = doc.text if hasattr(doc, 'text') else str(doc)

        prompt = f"""你是一個測試題目設計師。
請根據以下文件內容，生成 {n_questions // len(documents)} 個測試問題和對應的標準答案。

要求：
1. 問題類型應涵蓋：{', '.join(question_types)}
2. 問題必須可以從文件中找到答案（不要問文件沒有的資訊）
3. 標準答案必須完整且正確
4. 問題難度應有所變化（簡單、中等、困難各佔三分之一）

文件內容：
{doc_text}

請用以下 JSON 格式回應：
{{
    "questions": [
        {{
            "question": "問題文字",
            "ground_truth": "標準答案",
            "type": "factual/procedural/comparison",
            "difficulty": "easy/medium/hard"
        }},
        ...
    ]
}}"""

        response = llm.invoke([HumanMessage(content=prompt)])
        try:
            data = json.loads(response.content)
            generated_data.extend(data.get("questions", []))
        except json.JSONDecodeError:
            print(f"警告：無法解析 LLM 的回應，跳過此文件")

    print(f"成功生成 {len(generated_data)} 個測試問題")
    return generated_data


# 使用示範
auto_questions = generate_evaluation_dataset(
    documents=KNOWLEDGE_BASE,
    n_questions=15,
    question_types=["factual", "procedural", "comparison"],
)

# 顯示生成的問題
print("\n=== 自動生成的評估資料集 ===")
for i, q in enumerate(auto_questions[:5], 1):
    print(f"\n[{i}] [{q.get('type', '未知')}] [{q.get('difficulty', '未知')}]")
    print(f"     問題：{q['question']}")
    print(f"     答案：{q['ground_truth'][:100]}...")
```

---

## 指標解讀指南

理解每個指標的分數代表什麼：

```
Faithfulness（忠實度）分數解讀
════════════════════════════════════════════════════════════

  0.9 - 1.0  ✅ 優秀：AI 幾乎完全根據文件回答，無幻覺
  0.7 - 0.9  ⚠️ 尚可：偶爾有輕微超出文件的推論
  0.5 - 0.7  ⚠️ 需改善：部分回答缺乏文件支持
  0.0 - 0.5  ❌ 嚴重問題：大量幻覺，嚴重不可靠

  低分的常見原因：
  - LLM 在文件之外加入了「常識」
  - 文件中有矛盾，LLM 選擇了錯誤的一邊
  - 問題超出文件範疇，LLM 仍試圖回答

  改善方法：
  - 在 System Prompt 強調「只根據提供的文件回答」
  - 如果文件中沒有答案，明確說「不知道」
  - 檢查知識庫是否有過時或衝突的資訊


Answer Relevancy（答案相關性）分數解讀
════════════════════════════════════════════════════════════

  0.9 - 1.0  ✅ 答案緊扣問題的核心
  0.7 - 0.9  ⚠️ 答案基本相關但可能包含無用資訊
  0.5 - 0.7  ⚠️ 答案部分跑題
  0.0 - 0.5  ❌ 嚴重答非所問

  低分的常見原因：
  - 問題模糊，AI 理解了不同的意思
  - 搜尋到的文件誤導了 AI
  - System Prompt 沒有足夠的指引

  改善方法：
  - 改善查詢改寫（Query Rewriting）
  - 加強 System Prompt 的指引
  - 使用 Re-Ranking 提高搜尋精確度


Context Recall（上下文召回率）分數解讀
════════════════════════════════════════════════════════════

  指標含義：標準答案所需的資訊，有多少比例被搜尋到？

  0.9 - 1.0  ✅ 幾乎所有必要資訊都被搜尋到
  0.7 - 0.9  ⚠️ 大部分資訊搜尋到，但有遺漏
  0.5 - 0.7  ⚠️ 只搜尋到約一半的必要資訊
  0.0 - 0.5  ❌ 大量必要資訊未被搜尋到

  低分的常見原因：
  - similarity_top_k 太小（找的文件不夠多）
  - Chunk Size 太大（相關資訊被稀釋在無關內容中）
  - 問題的語意和文件的語意差距太大

  改善方法：
  - 增加 similarity_top_k（找更多候選文件）
  - 縮小 Chunk Size（讓搜尋更精確）
  - 使用查詢改寫（讓問題更接近文件的語言風格）


Context Precision（上下文精確度）分數解讀
════════════════════════════════════════════════════════════

  指標含義：找到的文件中，有多少比例是真正有用的？

  0.9 - 1.0  ✅ 幾乎所有找到的文件都是相關的
  0.7 - 0.9  ⚠️ 大部分相關，有少量雜訊
  0.5 - 0.7  ⚠️ 有明顯雜訊，LLM 需要從很多無關內容中找資訊
  0.0 - 0.5  ❌ 搜尋到的文件大部分是無關的

  低分的常見原因：
  - 相似度閾值太低（什麼都搜尋到）
  - Embedding 品質不足
  - 知識庫中有太多相似但不相關的文件

  改善方法：
  - 加入 SimilarityPostprocessor 過濾低分文件
  - 使用 Re-Ranking 精確篩選
  - 加入 Metadata 過濾（只搜尋相關類別）
```

---

## A/B 測試：找出最好的配置

```python
"""
A/B 測試：比較不同 RAG 配置的效果
"""

import pandas as pd
from llama_index.core import VectorStoreIndex
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.postprocessor import SimilarityPostprocessor


def create_rag_config(
    documents: list,
    chunk_size: int = 512,
    chunk_overlap: int = 50,
    top_k: int = 5,
    similarity_cutoff: float = 0.0,
    config_name: str = "default",
) -> tuple:
    """建立特定配置的 RAG 系統。"""
    index = VectorStoreIndex.from_documents(
        documents,
        transformations=[SentenceSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )],
    )

    retriever = VectorIndexRetriever(
        index=index,
        similarity_top_k=top_k,
    )

    postprocessors = []
    if similarity_cutoff > 0:
        postprocessors.append(
            SimilarityPostprocessor(similarity_cutoff=similarity_cutoff)
        )

    query_engine = RetrieverQueryEngine(
        retriever=retriever,
        node_postprocessors=postprocessors,
    )

    return query_engine, config_name


def ab_test_rag_configs(
    documents: list,
    test_questions: list,
    ground_truths: list,
    configs: list[dict],
) -> pd.DataFrame:
    """
    對多個 RAG 配置進行 A/B 測試。

    configs 格式：
    [
        {"name": "baseline", "chunk_size": 512, "top_k": 5},
        {"name": "large_chunks", "chunk_size": 1024, "top_k": 5},
        {"name": "more_docs", "chunk_size": 512, "top_k": 10},
    ]
    """
    results = []

    for config in configs:
        name = config.pop("name", "config")
        print(f"\n測試配置：{name} ({config})")

        query_engine, _ = create_rag_config(
            documents=documents,
            config_name=name,
            **config,
        )

        evaluator = RAGEvaluator(query_engine)
        dataset = evaluator.collect_rag_responses(test_questions, ground_truths)
        eval_result = evaluator.evaluate(dataset)

        metrics = eval_result.to_pandas()[
            ["faithfulness", "answer_relevancy", "context_recall", "context_precision"]
        ].mean()

        result_row = {"config": name, **config}
        result_row.update(metrics.to_dict())
        results.append(result_row)

    results_df = pd.DataFrame(results)

    # 計算綜合分數
    metric_cols = ["faithfulness", "answer_relevancy", "context_recall", "context_precision"]
    available_metric_cols = [c for c in metric_cols if c in results_df.columns]
    results_df["overall_score"] = results_df[available_metric_cols].mean(axis=1)
    results_df = results_df.sort_values("overall_score", ascending=False)

    print("\n=== A/B 測試結果 ===")
    print(results_df.to_string(index=False))
    print(f"\n🏆 最佳配置：{results_df.iloc[0]['config']}")

    return results_df


# 執行 A/B 測試
configs_to_test = [
    {"name": "baseline_512", "chunk_size": 512, "top_k": 5},
    {"name": "large_1024", "chunk_size": 1024, "top_k": 5},
    {"name": "more_docs_k10", "chunk_size": 512, "top_k": 10},
    {"name": "filtered", "chunk_size": 512, "top_k": 10, "similarity_cutoff": 0.6},
]

ab_results = ab_test_rag_configs(
    documents=KNOWLEDGE_BASE,
    test_questions=TEST_QUESTIONS,
    ground_truths=GROUND_TRUTHS,
    configs=configs_to_test,
)
```

---

## 診斷工具：找出 RAG 系統的問題

```python
"""
RAG 診斷工具：分析失敗案例，找出改善方向
"""

def diagnose_rag_failures(evaluation_df: pd.DataFrame) -> dict:
    """
    分析評估結果，診斷 RAG 系統的問題類型。
    """
    diagnosis = {
        "hallucination_risk": [],      # 忠實度低 → 幻覺風險
        "relevance_issues": [],        # 答案相關性低 → 答非所問
        "retrieval_gaps": [],          # 召回率低 → 搜尋遺漏重要文件
        "noise_issues": [],            # 精確度低 → 搜尋到太多無關文件
    }

    for _, row in evaluation_df.iterrows():
        question = row.get("question", "")

        # 診斷幻覺風險（忠實度 < 0.6）
        if "faithfulness" in row and row["faithfulness"] < 0.6:
            diagnosis["hallucination_risk"].append({
                "question": question,
                "faithfulness": row["faithfulness"],
                "answer_preview": str(row.get("answer", ""))[:100],
            })

        # 診斷答非所問（相關性 < 0.6）
        if "answer_relevancy" in row and row["answer_relevancy"] < 0.6:
            diagnosis["relevance_issues"].append({
                "question": question,
                "relevancy": row["answer_relevancy"],
            })

        # 診斷搜尋遺漏（召回率 < 0.6）
        if "context_recall" in row and row["context_recall"] < 0.6:
            diagnosis["retrieval_gaps"].append({
                "question": question,
                "recall": row["context_recall"],
                "ground_truth_preview": str(row.get("ground_truth", ""))[:100],
            })

        # 診斷雜訊問題（精確度 < 0.6）
        if "context_precision" in row and row["context_precision"] < 0.6:
            diagnosis["noise_issues"].append({
                "question": question,
                "precision": row["context_precision"],
            })

    # 生成診斷報告
    print("\n=== RAG 系統診斷報告 ===\n")

    issue_counts = {k: len(v) for k, v in diagnosis.items()}
    total_questions = len(evaluation_df)

    print("問題分布：")
    for issue, count in issue_counts.items():
        if count > 0:
            pct = count / total_questions * 100
            print(f"  {issue}: {count}/{total_questions} 個問題 ({pct:.1f}%)")

    # 找出最主要的問題
    main_issue = max(issue_counts, key=issue_counts.get)
    if issue_counts[main_issue] > 0:
        print(f"\n🔍 主要問題：{main_issue}")

        # 給出改善建議
        suggestions = {
            "hallucination_risk": [
                "在 System Prompt 加入強制限制：「只能根據提供的文件回答」",
                "如果文件中找不到答案，讓 AI 明確說不知道",
                "檢查知識庫是否有互相矛盾的資訊",
            ],
            "relevance_issues": [
                "加入查詢改寫（Query Rewriting）節點",
                "改善 System Prompt，更清楚地指示回答範圍",
                "使用 Re-Ranking 確保找到真正相關的文件",
            ],
            "retrieval_gaps": [
                "增加 similarity_top_k（找更多候選文件）",
                "縮小 chunk_size（讓搜尋更精確）",
                "嘗試語義切分（Semantic Chunking）",
                "使用混合搜尋（向量 + 關鍵字）",
            ],
            "noise_issues": [
                "加入 SimilarityPostprocessor 過濾低分文件",
                "使用 Re-Ranking 精確篩選",
                "加入 Metadata 過濾，限縮搜尋範圍",
                "考慮提高 similarity_cutoff 閾值",
            ],
        }

        print("\n💡 改善建議：")
        for suggestion in suggestions.get(main_issue, []):
            print(f"  • {suggestion}")

    return diagnosis
```

---

## 重點回顧 📋

```
┌─────────────────────────────────────────────────────────┐
│                    第六章重點整理                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  🔑 Ragas 四大指標：                                    │
│     Faithfulness：AI 沒有捏造資訊（忠實度）            │
│     Answer Relevancy：AI 回答了正確的問題（相關性）     │
│     Context Recall：搜尋覆蓋了所有需要的資訊（召回率） │
│     Context Precision：搜尋結果大部分是有用的（精確度） │
│                                                         │
│  🔑 評估資料集三要素：                                  │
│     question：測試問題                                  │
│     contexts：RAG 搜尋到的文件片段                      │
│     ground_truth：人工撰寫的標準答案                    │
│                                                         │
│  🔑 自動生成評估資料集：                               │
│     用 GPT-4 從知識庫文件自動生成問題和答案             │
│     節省大量人工標注時間                                │
│                                                         │
│  🔑 A/B 測試找最佳配置：                               │
│     系統地比較不同 chunk_size、top_k、閾值              │
│     用整體分數（overall_score）選出最佳配置             │
│                                                         │
│  🔑 問題診斷：                                          │
│     忠實度低 → 幻覺風險 → 加強系統提示                 │
│     相關性低 → 答非所問 → 改善查詢改寫                 │
│     召回率低 → 搜尋遺漏 → 增加 top_k 或縮小 chunk      │
│     精確度低 → 雜訊太多 → 加入過濾和 Re-Ranking        │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 常見問題 FAQ

**Q: Faithfulness 分數 0.3 代表什麼？**

Faithfulness 分數 0.3 意味著：AI 的答案中，大約只有 30% 的宣告（claims）可以從提供的文件中找到支持。其餘 70% 可能是幻覺——AI 憑空捏造的資訊。

這是非常嚴重的問題，特別是在醫療、法律、財務等高風險領域。

---

**Q: 如何偵測幻覺？**

Ragas 的 Faithfulness 指標就是在偵測幻覺。它的運作方式：
1. 讓 LLM 把回答拆成一個個「宣告」（claims）
2. 對每個宣告，檢查能否從搜尋到的文件中找到支持
3. 「可以被文件支持的宣告數」÷「總宣告數」= Faithfulness 分數

---

**Q: 需要多少個測試問題才夠？**

這取決於你的知識庫大小和業務重要性：

- **快速檢查**：20-50 個問題（開發階段）
- **標準評估**：100-200 個問題（上線前）
- **全面評估**：500+ 個問題（生產環境定期評估）

建議：用自動生成工具快速建立大量問題，再人工審核去除品質差的。

---

**Q: Ragas 的評估本身有多準確？**

Ragas 使用 LLM（如 GPT-4）作為評審，本身也可能有錯。研究顯示，LLM-as-judge 方法與人類評審有約 80-85% 的一致性——對於大多數應用場景已經夠用，但不要完全依賴它。

建議：偶爾抽樣做人工評估，確認 Ragas 的分數符合實際感受。

---

## 課後練習

### 練習 6.1：基礎（⭐）

使用 Lab 6.1 的知識庫，手動撰寫 10 個測試問題和標準答案，然後執行 Ragas 評估。針對分數最低的兩個指標，寫出你認為改善的方法。

### 練習 6.2：進階（⭐⭐）

設計一個「指標間取捨」的實驗：
- 嘗試找出一種配置，讓 Faithfulness 非常高（> 0.9），但 Answer Relevancy 較低（< 0.7）
- 再找出一種配置，讓情況反過來
- 分析：這兩種「偏差」各自在什麼業務場景下更危險？

### 練習 6.3：挑戰（⭐⭐⭐）

建立一個「持續評估管線」：
- 每次知識庫更新後自動觸發評估
- 把評估結果存入資料庫（可以用 SQLite）
- 建立一個簡單的 Dashboard（用 Streamlit 或 Gradio）顯示：
  - 各指標隨時間的趨勢
  - 當前最差的 10 個問題
  - 與基準線相比的改善或退步

---

## 課程總結：你已經是 RAG 大師了！

```
你的學習旅程回顧
════════════════════════════════════════════════════════════

  ✅ 第一章：理解了 RAG 的必要性和核心架構
             閉卷考試 → 開卷考試
             Retrieve → Augment → Generate

  ✅ 第二章：掌握了文件 ETL 管線
             Extract → Transform（切分）→ Load
             四種切分策略和 Metadata 的重要性

  ✅ 第三章：深入理解了向量 Embedding
             語意搜尋 vs 關鍵字搜尋
             FAISS 和 Qdrant 的選擇

  ✅ 第四章：掌握了 LlamaIndex 框架
             三種索引類型的適用場景
             Router 和 SubQuestion 進階用法

  ✅ 第五章：學會了 Agentic RAG
             Self-Reflection 和 Corrective RAG
             用 LangGraph 建立有狀態的 Agent

  ✅ 第六章：建立了評估體系
             Ragas 四大指標
             A/B 測試和診斷工具
```

恭喜你完成了整個課程！

現在你不只會「用」RAG，更重要的是你理解了**每一個設計決策背後的原因**。當系統出問題時，你知道從哪裡開始診斷；當需求改變時，你知道如何調整。

這就是從「會用工具」到「理解系統」的差距。

繼續建造，繼續學習。

---

*第六章完 · 課程結束*

---

## 延伸閱讀

如果你想繼續深入，這些方向值得探索：

1. **GraphRAG**：用知識圖譜強化 RAG 的關係理解能力
2. **ColBERT/PLAID**：多向量 Embedding，比單一向量更精確
3. **Hypothetical Document Embeddings (HyDE)**：用生成的假文件來改善搜尋
4. **RAPTOR**：遞迴摘要構建的樹狀 RAG
5. **多模態 RAG**：讓 RAG 支援圖片、表格、影片

**推薦資源**：
- Ragas 官方文件：https://docs.ragas.io
- LlamaIndex 官方文件：https://docs.llamaindex.ai
- LangGraph 官方文件：https://langchain-ai.github.io/langgraph
- RAG 論文：「Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks」（Lewis et al., 2020）

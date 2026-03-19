# 第三章：數字的靈魂邊界

## 向量 Embeddings 與語意搜尋

---

> 「king - man + woman = queen」
>
> 第一次看到這個等式，你的反應是什麼？
> 這是數學？是魔法？還是 AI 在胡說八道？

---

讓我們回到一個你可能已經忘記的中學數學題：

「在地球上，台北的位置是北緯 25.04°、東經 121.56°。東京是北緯 35.69°、東經 139.69°。請問兩地距離多少公里？」

你知道怎麼算（或者至少知道用什麼公式）。重點是：**地球上任何一個地點，都可以用兩個數字完整描述。**

現在想像：如果每一個**詞語的意思**也可以用數字來表示呢？

「貓」是 (0.72, -0.31, 0.45, ...)
「狗」是 (0.68, -0.28, 0.43, ...)
「汽車」是 (-0.12, 0.85, -0.23, ...)

貓和狗的數字很接近（都是動物）。
貓和汽車的數字差很遠（完全不同類別）。

**這就是 Embedding 的核心思想。**

---

## 腦力激盪 🧠

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│  問題 1：如果「台北」可以用座標 (25.04, 121.56) 表示，  │
│          「台北的下一站是？」用座標怎麼回答？           │
│                                                         │
│  問題 2：用關鍵字搜尋「蘋果公司」，會不會找到           │
│          「Apple Inc.」相關的文章？                      │
│          用語意搜尋呢？                                  │
│                                                         │
│  問題 3：king - man + woman = queen                     │
│          這個等式背後代表什麼意思？                      │
│          試著用自己的話解釋「為什麼可以做到」。         │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 為什麼關鍵字搜尋不夠用？

傳統搜尋的問題：

```
用戶問：「我的狗狗最近食慾不振，是生病了嗎？」

關鍵字搜尋找到：包含「狗狗」「食慾不振」的文件
    ✅ 能找到：「狗狗食慾不振怎麼辦」
    ❌ 找不到：「犬隻進食量減少可能是腸胃炎的徵兆」
              （意思一樣，但關鍵字不同）

語意搜尋找到：意思最相近的文件
    ✅ 能找到：「狗狗食慾不振怎麼辦」
    ✅ 也能找到：「犬隻進食量減少可能是腸胃炎的徵兆」
               「寵物不肯進食的常見原因分析」
               「My dog won't eat - what should I do?」（跨語言！）
```

語意搜尋之所以厲害，是因為它理解的是**意思**，不是文字的字面形式。

---

## Embedding 的視覺化理解

想像一個多維空間（我們先用 2D 來理解）：

```
                    ↑ 生命/生物相關
                    │
         貓 ●   狗 ●│
                    │● 鳥
                    │         ● 植物
    ──────────────────────────────────────→ 動態/主動
         ● 汽車    │        ● 石頭
         ● 飛機    │
                    │
                    ↓ 無生命
```

在這個空間裡：
- **語意相近的詞，空間距離也相近**（貓和狗很近）
- **語意不相關的詞，空間距離很遠**（貓和汽車很遠）
- **有關係的詞，距離規律**（king 到 queen 的方向，和 man 到 woman 的方向一樣）

真實的 Embedding 不是 2D，而是 1536D（OpenAI text-embedding-3-small）或更高維度。但原理是一樣的。

---

## 相似度計算：三種方法

```python
import numpy as np

def cosine_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    """
    余弦相似度：最常用的語意相似度計算方式。
    測量兩個向量的「方向」是否相似，範圍 -1 到 1。
    1 = 完全相同，0 = 毫無關係，-1 = 完全相反
    """
    dot_product = np.dot(vec_a, vec_b)
    norm_a = np.linalg.norm(vec_a)
    norm_b = np.linalg.norm(vec_b)
    return dot_product / (norm_a * norm_b)


def euclidean_distance(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    """
    歐氏距離：直線距離。
    距離越小表示越相似。
    """
    return np.linalg.norm(vec_a - vec_b)


def dot_product_similarity(vec_a: np.ndarray, vec_b: np.ndarray) -> float:
    """
    點積相似度：速度最快，但對向量長度敏感。
    （長的向量會有更高的點積，即使方向不那麼相似）
    """
    return np.dot(vec_a, vec_b)


# 示範：余弦相似度為什麼適合語意搜尋
# 假設這些是簡化的 3D Embedding
cat = np.array([0.9, 0.1, 0.8])    # 動物、毛茸茸、小
dog = np.array([0.85, 0.2, 0.75])  # 動物、毛茸茸、中等
car = np.array([0.1, 0.9, 0.2])    # 機器、金屬、大

print(f"貓 vs 狗（應該很高）：{cosine_similarity(cat, dog):.4f}")
print(f"貓 vs 車（應該很低）：{cosine_similarity(cat, car):.4f}")
print(f"狗 vs 車（應該很低）：{cosine_similarity(dog, car):.4f}")
```

### 為什麼用余弦相似度？

```
情境：文件 A 很長（4000 字），文件 B 很短（200 字），
     但它們說的是同樣的事情。

     向量長度：A 的向量（模）> B 的向量（模）
     向量方向：A 和 B 的方向相近（語意相同）

     點積相似度：A vs C（和 A 語意相近但更長）會 > A vs B
     余弦相似度：只看方向，忽略長度，更公平地比較語意
```

**余弦相似度的幾何意義**：就是兩個向量之間的夾角的余弦值。夾角越小（方向越相近），余弦值越接近 1。

---

## OpenAI Embedding API 實作

```python
from openai import OpenAI
import numpy as np
from typing import List

client = OpenAI()


def get_embedding(text: str, model: str = "text-embedding-3-small") -> List[float]:
    """
    獲取文字的 Embedding 向量。

    模型選擇：
    - text-embedding-3-small：1536 維，便宜，適合大多數場景
    - text-embedding-3-large：3072 維，更準確，適合高精度需求
    - text-embedding-ada-002：1536 維，舊版，仍廣泛使用
    """
    # 清理輸入：移除換行（對 Embedding 效果有影響）
    text = text.replace("\n", " ")

    response = client.embeddings.create(
        input=[text],
        model=model,
    )
    return response.data[0].embedding


def batch_get_embeddings(
    texts: List[str],
    model: str = "text-embedding-3-small",
    batch_size: int = 100,
) -> List[List[float]]:
    """
    批次獲取 Embeddings（API 允許一次送多個文字）。
    比逐一呼叫快很多，也節省 API 呼叫次數。
    """
    all_embeddings = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        # 清理文字
        batch = [t.replace("\n", " ") for t in batch]

        response = client.embeddings.create(
            input=batch,
            model=model,
        )
        # 按照輸入順序排列（API 可能不保序）
        sorted_embeddings = sorted(response.data, key=lambda x: x.index)
        all_embeddings.extend([e.embedding for e in sorted_embeddings])

    return all_embeddings


# 實際示範語意相似度
sentences = [
    "我的貓咪今天心情很好",           # 基準
    "我家的小貓今天很開心",           # 語意相近，字詞不同
    "我的狗狗今天很快樂",             # 語意相近，主體不同
    "今天股市大跌，投資人哀鴻遍野",   # 完全不相關
    "The weather is nice today",      # 英文，語意無關
]

print("計算 Embeddings 中...")
embeddings = [get_embedding(s) for s in sentences]
base_embedding = embeddings[0]

print(f"\n基準句：「{sentences[0]}」")
print(f"{'句子':<30} {'相似度':>8}")
print("-" * 45)
for i in range(1, len(sentences)):
    sim = cosine_similarity(
        np.array(base_embedding),
        np.array(embeddings[i])
    )
    print(f"{sentences[i]:<30} {sim:>8.4f}")
```

### 預期輸出

```
基準句：「我的貓咪今天心情很好」
句子                            相似度
---------------------------------------------
我家的小貓今天很開心              0.9234  ← 非常相近！
我的狗狗今天很快樂                0.8756  ← 也很相近
今天股市大跌，投資人哀鴻遍野      0.2341  ← 不相關
The weather is nice today         0.1823  ← 語意不相關
```

---

## FAISS：Facebook 的超速向量搜尋

FAISS（Facebook AI Similarity Search）是目前最廣泛使用的向量搜尋庫。

```
傳統搜尋 vs FAISS
══════════════════════════════════════════════

  傳統暴力搜尋（Brute Force）：
  「把問題向量和資料庫裡每一個向量都比一次」

  100萬份文件 × 1536維 = 每次查詢要計算 15億次乘法
  時間：幾十秒（無法接受！）


  FAISS（近似最近鄰搜尋，ANN）：
  「把向量空間分成區塊，只搜尋相關的區塊」

  時間：幾毫秒（完全可以接受！）
  代價：不保證找到絕對最近的，但找到次優解的準確率 > 95%
```

### FAISS 索引類型

```python
import faiss
import numpy as np

dimension = 1536  # OpenAI text-embedding-3-small 的維度
n_documents = 10000  # 假設有 1 萬份文件

# ── 類型 1：FlatL2（暴力搜尋，100% 準確）────────────────
# 適合：文件數量 < 10萬，需要完全精確的結果
flat_index = faiss.IndexFlatL2(dimension)

# ── 類型 2：IndexIVFFlat（倒排索引，快速近似搜尋）──────
# 適合：文件數量 10萬 ~ 1000萬
n_clusters = 100  # 把向量空間分成 100 個區域
quantizer = faiss.IndexFlatL2(dimension)
ivf_index = faiss.IndexIVFFlat(quantizer, dimension, n_clusters)
# 注意：IVF 索引需要先 train（需要有代表性的樣本）

# ── 類型 3：IndexHNSW（層次可導航小世界，超快！）───────
# 適合：需要極低延遲，可接受輕微精度損失
hnsw_index = faiss.IndexHNSWFlat(dimension, 32)  # 32 是連結數
```

### 完整 FAISS 索引實作

```python
import faiss
import numpy as np
import pickle
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Tuple, Optional


@dataclass
class FAISSVectorStore:
    """
    簡單的 FAISS 向量資料庫封裝。
    功能：新增、搜尋、持久化。
    """
    dimension: int = 1536
    index_type: str = "flat"  # "flat", "ivf", "hnsw"

    # 儲存向量對應的文字和中繼資料
    texts: List[str] = field(default_factory=list)
    metadatas: List[dict] = field(default_factory=list)
    index: Optional[faiss.Index] = None

    def __post_init__(self):
        self._build_index()

    def _build_index(self):
        """根據設定建立 FAISS 索引。"""
        if self.index_type == "flat":
            self.index = faiss.IndexFlatIP(self.dimension)  # 內積（等同余弦相似度於正規化向量）
        elif self.index_type == "hnsw":
            self.index = faiss.IndexHNSWFlat(self.dimension, 32)
        else:
            raise ValueError(f"不支援的索引類型：{self.index_type}")

    def add(self, texts: List[str], embeddings: List[List[float]], metadatas: List[dict] = None):
        """新增向量到索引。"""
        if metadatas is None:
            metadatas = [{} for _ in texts]

        # 轉換為 numpy 陣列並正規化（讓內積等同余弦相似度）
        vectors = np.array(embeddings, dtype=np.float32)
        faiss.normalize_L2(vectors)

        self.index.add(vectors)
        self.texts.extend(texts)
        self.metadatas.extend(metadatas)

        print(f"新增了 {len(texts)} 個向量，總計：{self.index.ntotal}")

    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
    ) -> List[Tuple[str, float, dict]]:
        """
        搜尋最相近的向量。
        回傳：[(文字, 相似度分數, 中繼資料), ...]
        """
        # 正規化查詢向量
        query_vector = np.array([query_embedding], dtype=np.float32)
        faiss.normalize_L2(query_vector)

        # 搜尋
        scores, indices = self.index.search(query_vector, top_k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx != -1:  # -1 表示找不到
                results.append((
                    self.texts[idx],
                    float(score),
                    self.metadatas[idx],
                ))
        return results

    def save(self, path: str):
        """持久化索引到磁碟。"""
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)

        faiss.write_index(self.index, str(path / "index.faiss"))
        with open(path / "metadata.pkl", "wb") as f:
            pickle.dump({"texts": self.texts, "metadatas": self.metadatas}, f)
        print(f"索引已儲存至：{path}")

    @classmethod
    def load(cls, path: str) -> "FAISSVectorStore":
        """從磁碟載入索引。"""
        path = Path(path)
        index = faiss.read_index(str(path / "index.faiss"))

        with open(path / "metadata.pkl", "rb") as f:
            data = pickle.load(f)

        store = cls(dimension=index.d)
        store.index = index
        store.texts = data["texts"]
        store.metadatas = data["metadatas"]
        print(f"載入索引，共 {index.ntotal} 個向量")
        return store
```

---

## Qdrant：生產級向量資料庫

FAISS 很快，但不支援即時更新、過濾搜尋等進階功能。Qdrant 是一個設計用於生產環境的向量資料庫。

```python
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
)
import uuid


class QdrantVectorStore:
    """
    Qdrant 向量資料庫封裝。
    支援：過濾搜尋、即時更新、持久化。
    """

    def __init__(
        self,
        collection_name: str,
        dimension: int = 1536,
        url: str = "http://localhost:6333",  # 本地 Qdrant
    ):
        self.collection_name = collection_name
        self.dimension = dimension

        # 連接到 Qdrant（也可以用 in-memory 版本）
        # self.client = QdrantClient(":memory:")  # 記憶體版（測試用）
        self.client = QdrantClient(url=url)

        self._ensure_collection()

    def _ensure_collection(self):
        """確保 Collection 存在，不存在就建立。"""
        collections = [c.name for c in self.client.get_collections().collections]

        if self.collection_name not in collections:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=self.dimension,
                    distance=Distance.COSINE,  # 使用余弦相似度
                ),
            )
            print(f"建立 Collection：{self.collection_name}")
        else:
            count = self.client.count(self.collection_name).count
            print(f"載入 Collection：{self.collection_name}（已有 {count} 個向量）")

    def add(
        self,
        texts: List[str],
        embeddings: List[List[float]],
        metadatas: List[dict] = None,
    ):
        """新增向量和對應的文字到 Qdrant。"""
        if metadatas is None:
            metadatas = [{} for _ in texts]

        points = [
            PointStruct(
                id=str(uuid.uuid4()),   # 唯一 ID
                vector=embedding,
                payload={
                    "text": text,
                    **metadata,          # 把中繼資料展開存入 payload
                },
            )
            for text, embedding, metadata in zip(texts, embeddings, metadatas)
        ]

        # 批次上傳
        self.client.upsert(
            collection_name=self.collection_name,
            points=points,
        )
        print(f"新增了 {len(points)} 個向量")

    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filter_conditions: dict = None,
    ) -> List[Tuple[str, float, dict]]:
        """
        語意搜尋，支援過濾條件。

        範例 filter_conditions：
        {"department": "技術文件", "language": "zh-TW"}
        """
        # 建立過濾條件
        query_filter = None
        if filter_conditions:
            conditions = [
                FieldCondition(key=key, match=MatchValue(value=value))
                for key, value in filter_conditions.items()
            ]
            query_filter = Filter(must=conditions)

        results = self.client.query_points(
            collection_name=self.collection_name,
            query=query_embedding,
            limit=top_k,
            query_filter=query_filter,
            with_payload=True,
        ).points

        return [
            (
                result.payload.get("text", ""),
                result.score,
                {k: v for k, v in result.payload.items() if k != "text"},
            )
            for result in results
        ]

    def delete_by_filter(self, filter_conditions: dict):
        """根據中繼資料條件刪除向量（支援增量更新）。"""
        conditions = [
            FieldCondition(key=key, match=MatchValue(value=value))
            for key, value in filter_conditions.items()
        ]
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=Filter(must=conditions),
        )
```

---

## 動手做 Lab 3.1：Embedding 視覺化

用 PCA 把高維向量壓縮到 2D，讓你真正「看到」語意空間。

```python
"""
Lab 3.1：用 PCA/t-SNE 視覺化 Embedding 空間
需要安裝：pip install scikit-learn matplotlib openai
"""

import numpy as np
import matplotlib.pyplot as plt
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
from openai import OpenAI

client = OpenAI()

# 準備各種類別的句子
SENTENCES = {
    "🐱 動物（貓）": [
        "我家有一隻橘色的貓",
        "貓咪整天在睡覺",
        "小貓喜歡玩毛線球",
        "貓是獨立的動物",
    ],
    "🐕 動物（狗）": [
        "我的狗狗很愛撒嬌",
        "拉布拉多是友善的犬種",
        "帶狗散步是每天的功課",
        "狗是人類最忠實的朋友",
    ],
    "💻 科技": [
        "Python 是資料科學的首選語言",
        "機器學習需要大量的訓練資料",
        "神經網路模仿人類大腦結構",
        "GPU 加速深度學習的計算",
    ],
    "🍜 食物": [
        "台灣的牛肉麵非常有名",
        "小籠包是上海的代表美食",
        "珍珠奶茶風靡全球",
        "拉麵是日本的靈魂料理",
    ],
}

def get_all_embeddings():
    """獲取所有句子的 Embedding。"""
    all_texts = []
    all_labels = []
    all_categories = []

    for category, sentences in SENTENCES.items():
        for sentence in sentences:
            all_texts.append(sentence)
            all_labels.append(sentence[:15] + "...")
            all_categories.append(category)

    print(f"計算 {len(all_texts)} 個句子的 Embeddings...")
    embeddings = []
    for text in all_texts:
        response = client.embeddings.create(
            input=[text],
            model="text-embedding-3-small"
        )
        embeddings.append(response.data[0].embedding)

    return np.array(embeddings), all_labels, all_categories


def visualize_with_pca(embeddings, labels, categories):
    """用 PCA 降維到 2D 並視覺化。"""
    pca = PCA(n_components=2, random_state=42)
    coords_2d = pca.fit_transform(embeddings)

    fig, ax = plt.subplots(figsize=(12, 9))

    # 每個類別用不同顏色
    colors = {"🐱 動物（貓）": "#e74c3c", "🐕 動物（狗）": "#e67e22",
              "💻 科技": "#3498db", "🍜 食物": "#2ecc71"}
    markers = {"🐱 動物（貓）": "o", "🐕 動物（狗）": "s",
               "💻 科技": "^", "🍜 食物": "D"}

    for category in set(categories):
        mask = [c == category for c in categories]
        x = coords_2d[mask, 0]
        y = coords_2d[mask, 1]
        ax.scatter(x, y,
                   c=colors[category],
                   marker=markers[category],
                   s=100, label=category, alpha=0.8,
                   edgecolors="white", linewidths=1)

    # 加上文字標籤
    for i, label in enumerate(labels):
        ax.annotate(
            label,
            (coords_2d[i, 0], coords_2d[i, 1]),
            fontsize=8,
            ha="right",
            va="bottom",
        )

    variance_explained = pca.explained_variance_ratio_
    ax.set_title(
        f"Embedding 語意空間視覺化（PCA）\n"
        f"解釋變異量：{variance_explained[0]:.1%} + {variance_explained[1]:.1%} = "
        f"{sum(variance_explained):.1%}",
        fontsize=14,
    )
    ax.set_xlabel(f"第一主成分（{variance_explained[0]:.1%}）")
    ax.set_ylabel(f"第二主成分（{variance_explained[1]:.1%}）")
    ax.legend(loc="best", fontsize=10)
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig("embedding_visualization_pca.png", dpi=150)
    print("PCA 圖表已儲存")
    plt.show()


# 執行
embeddings, labels, categories = get_all_embeddings()
visualize_with_pca(embeddings, labels, categories)
```

---

## Lab 3.2：建立語意搜尋引擎

```python
"""
Lab 3.2：從零建立語意搜尋引擎，與關鍵字搜尋比較
"""

import numpy as np
import faiss
from openai import OpenAI

client = OpenAI()

# 準備知識庫
KNOWLEDGE_BASE = [
    {
        "id": 1,
        "text": "貓咪在冬天特別喜歡蜷縮在暖和的地方睡覺，牠們的新陳代謝會隨氣溫下降而減慢。",
        "category": "動物行為",
    },
    {
        "id": 2,
        "text": "Python 的 asyncio 模組允許你撰寫非同步程式碼，使用 async/await 語法可以有效地處理 I/O 密集型任務。",
        "category": "程式設計",
    },
    {
        "id": 3,
        "text": "台灣的健保制度被許多國際評比列為全球最佳醫療保險系統之一，覆蓋率超過 99%。",
        "category": "社會政策",
    },
    {
        "id": 4,
        "text": "向量資料庫透過近似最近鄰搜尋（ANN）技術，可以在毫秒內從數百萬個向量中找到最相似的結果。",
        "category": "資料庫技術",
    },
    {
        "id": 5,
        "text": "寵物貓的平均壽命約為 12-18 年，定期的獸醫檢查和均衡的飲食是延長壽命的關鍵。",
        "category": "寵物照護",
    },
    {
        "id": 6,
        "text": "深度學習中的 Transformer 架構使用自注意力機制，這讓模型能夠理解文字中遠距離的依賴關係。",
        "category": "機器學習",
    },
    {
        "id": 7,
        "text": "台灣健保的保費計算方式以投保薪資為基礎，雇主和政府也各自負擔部分費用。",
        "category": "社會政策",
    },
    {
        "id": 8,
        "text": "家貓（Felis catus）是由非洲野貓馴化而來，大約在一萬年前開始與人類共同生活。",
        "category": "生物學",
    },
]


class SemanticSearchEngine:
    """語意搜尋引擎。"""

    def __init__(self, dimension: int = 1536):
        self.dimension = dimension
        self.index = faiss.IndexFlatIP(dimension)
        self.documents = []

    def build(self, documents: list):
        """建立搜尋索引。"""
        self.documents = documents
        texts = [doc["text"] for doc in documents]

        print(f"向量化 {len(texts)} 篇文件...")
        embeddings = []
        for text in texts:
            resp = client.embeddings.create(
                input=[text], model="text-embedding-3-small"
            )
            embeddings.append(resp.data[0].embedding)

        vectors = np.array(embeddings, dtype=np.float32)
        faiss.normalize_L2(vectors)
        self.index.add(vectors)
        print("索引建立完成！")

    def search(self, query: str, top_k: int = 3) -> list:
        """語意搜尋。"""
        resp = client.embeddings.create(
            input=[query], model="text-embedding-3-small"
        )
        query_vec = np.array([resp.data[0].embedding], dtype=np.float32)
        faiss.normalize_L2(query_vec)

        scores, indices = self.index.search(query_vec, top_k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx >= 0:
                results.append({
                    "text": self.documents[idx]["text"],
                    "category": self.documents[idx]["category"],
                    "score": float(score),
                })
        return results


def keyword_search(query: str, documents: list, top_k: int = 3) -> list:
    """簡單關鍵字搜尋（TF 計分）。"""
    query_words = set(query.lower().split())
    scored = []

    for doc in documents:
        doc_words = doc["text"].lower()
        # 計算查詢詞出現在文件中的比例
        score = sum(1 for word in query_words if word in doc_words) / len(query_words)
        if score > 0:
            scored.append({
                "text": doc["text"],
                "category": doc["category"],
                "score": score,
            })

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]


def compare_search(query: str, engine: SemanticSearchEngine, documents: list):
    """對比語意搜尋和關鍵字搜尋的結果。"""
    print(f"\n{'=' * 60}")
    print(f"查詢：「{query}」")
    print("=" * 60)

    print("\n🔤 關鍵字搜尋結果：")
    keyword_results = keyword_search(query, documents)
    if keyword_results:
        for i, r in enumerate(keyword_results, 1):
            print(f"  {i}. [{r['category']}] 分數：{r['score']:.2f}")
            print(f"     {r['text'][:60]}...")
    else:
        print("  沒有找到相關文件")

    print("\n🧠 語意搜尋結果：")
    semantic_results = engine.search(query)
    for i, r in enumerate(semantic_results, 1):
        print(f"  {i}. [{r['category']}] 相似度：{r['score']:.4f}")
        print(f"     {r['text'][:60]}...")


# 執行
engine = SemanticSearchEngine()
engine.build(KNOWLEDGE_BASE)

# 測試查詢
queries = [
    "我的小貓今年幾歲了算老？",           # 包含「小貓」，語意關聯「壽命」
    "AI 如何理解語言中的長距離關係？",    # 關鍵字可能不直接出現
    "台灣的醫療保障制度",                  # 換個說法的社會政策
    "database for similarity search",       # 英文查詢，測試跨語言
]

for query in queries:
    compare_search(query, engine, KNOWLEDGE_BASE)
```

---

## FAISS vs Qdrant：如何選擇？

```
選擇決策樹
════════════════════════════════════════════════════════════

  你的場景是什麼？
      │
      ├── 原型開發 / 學習
      │       └──► FAISS（簡單、快速、免費）
      │
      ├── 文件數量 < 100萬，不需要即時更新
      │       └──► FAISS（夠用，且效能極佳）
      │
      ├── 需要過濾搜尋（只搜特定類別的文件）
      │       └──► Qdrant（有豐富的 Payload 過濾功能）
      │
      ├── 需要即時新增/刪除文件
      │       └──► Qdrant（支援即時更新，FAISS 不行）
      │
      └── 生產環境，需要高可用性
              └──► Qdrant（有持久化、備份、監控等功能）
```

| 比較項目 | FAISS | Qdrant |
|----------|-------|--------|
| 部署難度 | 超簡單（pip install） | 需要 Docker |
| 搜尋速度 | 極快 | 很快 |
| 即時更新 | 不支援（需重建） | 支援 |
| 過濾搜尋 | 不支援 | 支援 |
| 持久化 | 手動管理 | 內建 |
| 水平擴展 | 不支援 | 支援 |
| 適合場景 | 快速原型、離線批次 | 生產環境 |

---

## 重點回顧 📋

```
┌─────────────────────────────────────────────────────────┐
│                    第三章重點整理                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  🔑 Embedding 的本質：                                  │
│     把文字的「意思」轉換成高維向量                      │
│     語意相近的文字，向量距離也相近                      │
│                                                         │
│  🔑 余弦相似度：                                        │
│     測量兩個向量方向的相似程度                          │
│     範圍 -1 到 1，1 表示完全相同                        │
│     不受向量長度影響（比點積更公平）                    │
│                                                         │
│  🔑 FAISS vs Qdrant：                                   │
│     FAISS：快速、簡單、適合原型和離線場景               │
│     Qdrant：功能完整、適合生產環境                      │
│                                                         │
│  🔑 ANN（近似最近鄰）：                                 │
│     犧牲少量精確度換取極大的速度提升                    │
│     在 100 萬個向量中，毫秒內找到最相近的結果           │
│                                                         │
│  🔑 語意搜尋 vs 關鍵字搜尋：                           │
│     關鍵字：比對字面，快速但死板                        │
│     語意：理解意思，更精準且跨語言                      │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 常見問題 FAQ

**Q: Embedding 的維度越高越好嗎？**

不一定。維度越高：
- 儲存空間更大
- 計算更慢
- 可能產生「維度災難」（高維空間中所有點都很「遠」）

OpenAI 的 text-embedding-3-small（1536 維）在大多數場景效果很好。只有在需要極高精確度時才考慮 3072 維的 large 版本。

---

**Q: 為什麼要正規化（Normalize）向量？**

對向量進行 L2 正規化後，向量的「長度」（模）變成 1。這樣：
- 向量的「內積」就等同「余弦相似度」
- 讓長文字和短文字在比較時更公平
- FAISS 的 `IndexFlatIP`（內積索引）在正規化向量上的搜尋結果等同余弦相似度

---

**Q: 中文的 Embedding 效果怎麼樣？**

OpenAI 的多語言 Embedding 模型對中文支援很好，可以：
- 中文查詢找到中文結果
- 中文查詢也能找到英文結果（跨語言語意搜尋）

如果只需要中文，也可以考慮中文特化的模型，如 `BAAI/bge-large-zh-v1.5`（免費，可本地運行）。

---

## 課後練習

### 練習 3.1：基礎（⭐）

用 Lab 3.1 的視覺化程式，把以下類別的句子各加 4 句，觀察向量空間的分佈：
- 音樂相關
- 運動相關
- 金融相關

然後回答：哪些類別在向量空間中最容易被混淆？為什麼？

### 練習 3.2：進階（⭐⭐）

實作「語意聚類」：
- 使用 Lab 3.2 的知識庫
- 用 `sklearn.cluster.KMeans` 對所有文件的 Embedding 做聚類
- 把文件分成 3 組，看看 AI 自動把什麼主題的文件放在一起
- 和手動定義的 `category` 比較，有沒有一致？

### 練習 3.3：挑戰（⭐⭐⭐）

實作「混合搜尋（Hybrid Search）」：
- 把語意搜尋分數（0-1）和關鍵字匹配分數（0-1）結合
- 使用加權平均：`final_score = 0.7 * semantic + 0.3 * keyword`
- 找出 3 個「語意搜尋有優勢」和 3 個「關鍵字搜尋有優勢」的查詢範例
- 說明混合搜尋在哪些場景下比單一方法更好

---

## 下一章預告

你已經掌握了向量搜尋的核心技術。但在生產環境中，你需要一個框架來把所有零件組裝起來，並管理複雜的查詢流程。

**第四章：樂高積木大師**

> 「LlamaIndex 就像樂高——同樣的積木，可以組出完全不同的東西。」

我們會學習 LlamaIndex 的完整架構，包括各種索引類型和查詢引擎的選擇。

---

*第三章完 · 繼續閱讀 [第四章](./ch04-llamaindex.md)*

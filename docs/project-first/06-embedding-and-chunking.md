# 第六章：嵌入向量與分塊原理 — RAG 的「編譯器核心」

## 學習目標

讀完本章，你將能夠：
- 解釋嵌入向量（Embedding）的直覺概念和數學意涵
- 理解 M×N → M+N 的架構優勢如何對應到 RAG 的解耦設計
- 說明四種 Chunking 策略的適用場景和優缺點
- 理解為什麼 Chunking 和 Embedding 策略是重要的治理決策

---

## 6.1 嵌入向量：讓文字有「距離」

### 從關鍵字搜尋到語意搜尋

傳統關鍵字搜尋的問題：

```
查詢：「員工請假規定」
找到：包含「請假」「規定」的文件 ✓
找不到：含有「休假政策」「缺勤管理」的文件 ✗（語意相同，詞彙不同）
```

**嵌入向量（Embedding）** 的解法：  
把文字轉換成高維向量空間中的座標，  
語意相近的文字在空間中的距離也近。

```python
# 嵌入向量的直覺示意（實際是 1536 維向量）

"員工請假規定" → [0.23, -0.71, 0.45, ...]  # 1536 維向量
"休假政策說明" → [0.25, -0.68, 0.43, ...]  # 語意相近 → 向量相近
"財務報告 Q4"  → [-0.82, 0.12, -0.55, ...] # 語意不同 → 向量相遠
```

### 調用 OpenAI Embedding API

```python
# 檔案：src/ingestion/embedder.py

import openai
from tenacity import retry, stop_after_attempt, wait_exponential

class OpenAIEmbedder:
    """
    使用 text-embedding-3-large 將文字轉換成向量。
    由 ADR-001 決定使用此模型。
    """

    MODEL = "text-embedding-3-large"  # Constitution INV-6：不可在 code 中硬改

    def __init__(self):
        self.client = openai.OpenAI()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(min=1, max=10),
    )
    def embed(self, text: str) -> list[float]:
        """
        將單一文字嵌入為向量。

        Precondition: len(text.strip()) > 0（不嵌入空文字）
        Postcondition: len(result) == 1536（text-embedding-3-large 的維度）
        """
        if not text.strip():
            raise ValueError("不得嵌入空文字（違反 INV-1）")

        response = self.client.embeddings.create(
            model=self.MODEL,
            input=text,
        )
        vector = response.data[0].embedding
        assert len(vector) == 1536, f"預期 1536 維，得到 {len(vector)} 維"
        return vector

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        批次嵌入（最多 100 個）。
        使用批次 API 降低呼叫次數，節省 token 用量。
        """
        # 過濾空白文字
        valid_texts = [t for t in texts if t.strip()]
        if len(valid_texts) != len(texts):
            raise ValueError(f"批次中有 {len(texts) - len(valid_texts)} 個空白文字")

        if len(texts) > 100:
            raise ValueError("單次批次最多 100 個文字（API 限制）")

        response = self.client.embeddings.create(
            model=self.MODEL,
            input=valid_texts,
        )
        return [item.embedding for item in response.data]
```

---

## 6.2 M×N → M+N：RAG 的解耦架構優勢

### 為什麼要把「嵌入」和「生成」分開

這個問題和編譯器為什麼需要 IR（中間表示）的道理完全相同：

**沒有 Embedding Layer（直接 fine-tune）時：**
每種知識來源 × 每個 LLM = M × N 個 fine-tune 工程

```
HR 文件     × GPT-4o    = fine-tune 1
HR 文件     × Claude    = fine-tune 2
Legal 文件  × GPT-4o    = fine-tune 3
Legal 文件  × Claude    = fine-tune 4
...
5 種來源 × 4 個 LLM = 20 個 fine-tune（昂貴且難以維護）
```

**有 Embedding Layer（RAG 架構）時：**
只需要 M 個嵌入管線 + N 個 LLM 接口

```
HR 文件    → [Embedding] → Vector DB
Legal 文件 → [Embedding] → Vector DB
...                              ↓
                          語意搜尋
                              ↓
                          GPT-4o / Claude / Gemini（可切換）
5 種來源 + 4 個 LLM = 9 個模組（且可獨立替換）
```

> **核心洞見**：Vector DB 是 RAG 的「中間表示層（IR）」。  
> 它讓「理解文件（嵌入）」和「生成答案（LLM）」各自獨立演化。  
> 更換 LLM 不需要重新嵌入，更換嵌入模型不需要改 LLM 的呼叫方式。

---

## 6.3 四種 Chunking 策略

Chunking（文件分塊）是 RAG 的核心工程問題：  
塊太大 → LLM context 爆滿，無法比較多份文件；  
塊太小 → 語意斷裂，無法回答需要上下文的問題。

### 策略一：固定大小分塊（Fixed-size Chunking）

```python
def fixed_size_chunk(text: str, size: int = 512, overlap: int = 64) -> list[str]:
    """
    最簡單的分塊策略：每隔 size 個 token 切一刀，重疊 overlap 個 token。
    
    ✅ 優點：簡單、快速、可預測
    ❌ 缺點：常在句子或段落中間切斷，語意破碎
    適用：快速原型、結構非常規整的文件（如 CSV 轉文字）
    """
    tokens = tokenize(text)
    chunks = []
    start = 0
    while start < len(tokens):
        end = min(start + size, len(tokens))
        chunk = detokenize(tokens[start:end])
        chunks.append(chunk)
        start += size - overlap
    return chunks
```

### 策略二：遞迴分塊（Recursive Chunking）— 本專案採用

```python
# 檔案：src/ingestion/chunker.py

class RecursiveChunker:
    """
    遞迴分塊策略（ADR-002 決定採用此策略）。

    優先在自然邊界切分，依序嘗試：
    段落（\n\n）→ 句子（。！？）→ 詞（，）→ 字元

    ✅ 優點：尊重文件的自然結構，語意完整
    ✅ 優點：速度快（比語意分塊快 3 倍）
    ❌ 缺點：不同文件的 chunk 大小不均
    適用：大多數企業文件（Word、PDF、Markdown）
    """

    SEPARATORS = ["\n\n", "\n", "。", "！", "？", "，", " ", ""]

    def __init__(self, target_size: int = 600, overlap: int = 100):
        self.target_size = target_size
        self.overlap = overlap

    def split(self, text: str, metadata: dict = None) -> list["Chunk"]:
        chunks = self._recursive_split(text, self.SEPARATORS)

        result = []
        for i, chunk_text in enumerate(chunks):
            chunk_metadata = {
                **(metadata or {}),
                "chunk_index": i,
                "total_chunks": len(chunks),
            }
            result.append(Chunk(text=chunk_text, metadata=chunk_metadata))

        return result

    def _recursive_split(self, text: str, separators: list[str]) -> list[str]:
        """遞迴地用分隔符切分，直到所有塊都符合目標大小"""
        if not separators:
            # 最後手段：直接按字元切
            return [text[i:i+self.target_size]
                    for i in range(0, len(text), self.target_size - self.overlap)]

        separator = separators[0]
        splits = text.split(separator) if separator else list(text)

        chunks = []
        current = ""
        for split in splits:
            if len(tokenize(current + separator + split)) <= self.target_size:
                current += separator + split if current else split
            else:
                if current:
                    chunks.append(current)
                # 如果單個 split 本身超過 target_size，遞迴處理
                if len(tokenize(split)) > self.target_size:
                    chunks.extend(self._recursive_split(split, separators[1:]))
                    current = ""
                else:
                    current = split

        if current:
            chunks.append(current)

        return self._add_overlap(chunks)

    def _add_overlap(self, chunks: list[str]) -> list[str]:
        """在相鄰 chunks 之間加入重疊，保留跨塊上下文"""
        if len(chunks) <= 1:
            return chunks

        result = [chunks[0]]
        for i in range(1, len(chunks)):
            # 把前一個 chunk 的最後 overlap 個 token 加到當前 chunk 的開頭
            prev_tail = get_last_n_tokens(chunks[i-1], self.overlap)
            result.append(prev_tail + " " + chunks[i])
        return result
```

### 策略三：語意分塊（Semantic Chunking）

```python
# 概念示例：使用 NLP 模型偵測段落邊界

class SemanticChunker:
    """
    語意感知的分塊策略。
    
    使用嵌入向量比較相鄰句子的語意相似度，
    當相似度突然下降時，視為段落邊界並切分。
    
    ✅ 優點：最好的語意完整性
    ❌ 缺點：處理速度慢（每句都要呼叫 Embedding API）
    ❌ 缺點：成本高（呼叫 Embedding API 次數多）
    適用：高價值文件（法律合約、學術論文）
    """

    def split(self, text: str, threshold: float = 0.5) -> list[str]:
        sentences = self._split_to_sentences(text)
        sentence_vectors = self.embedder.embed_batch(sentences)

        # 計算相鄰句子的餘弦相似度
        similarities = []
        for i in range(len(sentence_vectors) - 1):
            sim = cosine_similarity(sentence_vectors[i], sentence_vectors[i+1])
            similarities.append(sim)

        # 相似度 < threshold 處視為段落邊界
        breakpoints = [i+1 for i, sim in enumerate(similarities) if sim < threshold]

        return self._merge_by_breakpoints(sentences, breakpoints)
```

### 策略四：文件結構感知分塊（Document-Aware Chunking）

```python
class DocumentAwareChunker:
    """
    利用文件結構（標題、章節）的分塊策略。
    
    解析 Markdown / Word 的標題層級，
    讓每個 chunk 完整包含一個邏輯章節。
    
    ✅ 優點：保持文件的邏輯完整性
    ✅ 優點：chunk 天然具有語意標題，可作為 metadata
    ❌ 缺點：依賴文件有良好的標題結構
    適用：技術文件、規格書、有目錄的 Word 文件
    """

    def split_markdown(self, text: str) -> list["Chunk"]:
        """按 Markdown 標題切分"""
        sections = re.split(r'\n(#{1,3} .+)\n', text)
        chunks = []
        current_title = "（無標題）"
        current_content = ""

        for i, section in enumerate(sections):
            if section.startswith('#'):
                # 儲存上一個章節
                if current_content.strip():
                    chunks.append(Chunk(
                        text=f"{current_title}\n\n{current_content}",
                        metadata={"section_title": current_title}
                    ))
                current_title = section.strip()
                current_content = ""
            else:
                current_content += section

        # 最後一個章節
        if current_content.strip():
            chunks.append(Chunk(
                text=f"{current_title}\n\n{current_content}",
                metadata={"section_title": current_title}
            ))

        return chunks
```

### 四種策略的選型指南

| 策略 | 速度 | 語意品質 | 成本 | 適用場景 |
|------|:----:|:-------:|:----:|---------|
| 固定大小 | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐ | 快速原型、結構簡單的文件 |
| 遞迴分塊 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | **大多數企業文件（推薦）** |
| 語意分塊 | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 高價值法律/學術文件 |
| 文件結構 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | 有良好結構的技術文件 |

---

## 6.4 為什麼 Chunking 是治理問題

Chunking 策略看起來是純技術問題，為什麼要納入治理？

因為 **Chunking 策略一旦選定，更換代價極高**：

```
當前狀態：5,000 份文件已用遞迴分塊策略嵌入，存入向量 DB

若要換成語意分塊策略：
1. 清空向量 DB 的所有 chunk
2. 用新策略重新分塊 5,000 份文件
3. 重新嵌入所有 chunk（API 成本 + 時間）
4. 驗證新策略的 Retrieval 品質不比舊策略差
5. 處理 re-embed 期間的服務中斷
```

這就是為什麼 ADR-002（Chunking 策略）是永久記錄，需要充分論證才能更改。

> 🔑 **治理重點**：凡是「更換代價 > 1 天工程工作量」的決策，都需要 ADR。

---

## 練習

1. **計算練習**：一份 10,000 字的 Word 文件，使用 `target_size=600, overlap=100` 的遞迴分塊策略，預估會產生幾個 chunks？（假設中文每個字約 1 token）

2. **策略選擇練習**：為以下三種文件選擇最適合的 Chunking 策略，並說明理由：
   - (a) 公司的標準合約範本（30 頁 Word，有清楚的章節結構）
   - (b) 客服工單系統的歷史記錄（CSV 格式，每行一筆對話）
   - (c) 技術部落格文章（Markdown 格式，有程式碼區塊）

3. **實作練習**：寫一個函式 `evaluate_chunking_strategy(text, chunker, test_questions, retriever)`，輸入一段文字、分塊器、測試問題列表和檢索器，輸出 Hit@3 的準確率。

4. **思考題**：如果一份文件被分成 50 個 chunks，但使用者的問題需要同時理解第 3 塊和第 48 塊的內容才能回答，傳統的 RAG 會怎麼失敗？你有什麼解決想法？

---

> **下一章**：[第七章：不可變知識管理與版本控制](07-immutable-knowledge.md)  
> 我們將學習如何設計知識庫的「不可變原則」，確保每一次知識更新都可追溯、可回滾。

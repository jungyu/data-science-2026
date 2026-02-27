# 第三章：規範驅動開發 — SDD-BDD-TDD for RAG

## 學習目標

讀完本章，你將能夠：
- 解釋 SDD → BDD → TDD 三層方法論在 RAG 開發中的角色
- 使用 Gherkin 語法撰寫知識攝取和查詢的行為規格
- 設計 RAG 系統的測試策略（單元 → 整合 → 評估）
- 理解「規格即合約」在 RAG 知識品質保證中的意義

---

## 3.1 TDD in RAG：測試驅動的知識系統

### RAG 測試的特殊挑戰

傳統軟體的測試很清楚：輸入 → 輸出，結果確定。  
RAG 系統的測試更難：同樣的問題，不同的 LLM 可能給不同的回答。

**RAG 的三層測試金字塔：**

```
                ╱╲
               ╱E2E╲         少量：完整 RAG 流程測試
              ╱──────╲        (問題 → 檢索 → 生成 → 評估)
             ╱ 評估測試 ╲
            ╱────────────╲    中量：Retrieval 準確率 + 答案品質評估
           ╱  整合測試    ╲
          ╱────────────────╲  適量：Embedding + Vector DB + 查詢管線測試
         ╱    單元測試      ╲
        ╱──────────────────  ╲ 大量：Chunking 函式、Embedding 呼叫、Metadata 驗證
```

### 單元測試範例：Chunking 函式

```python
# 檔案：tests/unit/test_chunking.py

import pytest
from src.ingestion.chunker import RecursiveChunker

class TestRecursiveChunker:
    """遞迴分塊器的單元測試"""

    def setup_method(self):
        self.chunker = RecursiveChunker(
            target_size=600,
            overlap=100,
        )

    def test_short_document_single_chunk(self):
        """短文件應該產生單一 chunk，不切分"""
        text = "這是一份很短的文件。只有一個段落。"
        chunks = self.chunker.split(text)
        assert len(chunks) == 1
        assert chunks[0].text == text

    def test_long_document_splits_at_paragraph(self):
        """長文件應該在段落邊界切分，而非句子中間"""
        # 建立兩個明顯的段落
        paragraph_1 = "第一段落內容。" * 50  # 約 350 tokens
        paragraph_2 = "第二段落內容。" * 50
        text = f"{paragraph_1}\n\n{paragraph_2}"

        chunks = self.chunker.split(text)

        # 確認切分點在段落邊界（不在句子中間）
        assert len(chunks) >= 2
        for chunk in chunks:
            assert not chunk.text.startswith("容。")  # 不在字元中間切

    def test_chunk_metadata_preserved(self):
        """每個 chunk 必須保留來源 metadata"""
        text = "測試文件內容。" * 100
        metadata = {"source": "hr-policy-v3.pdf", "owner": "hr-team"}

        chunks = self.chunker.split(text, metadata=metadata)

        for chunk in chunks:
            assert chunk.metadata["source"] == "hr-policy-v3.pdf"
            assert chunk.metadata["owner"] == "hr-team"
            assert "chunk_index" in chunk.metadata  # 自動加入的 chunk 序號

    def test_chunk_overlap_preserves_context(self):
        """相鄰 chunks 之間應該有重疊，保留跨塊上下文"""
        text = "A" * 700  # 超過單塊 600 tokens 限制
        chunks = self.chunker.split(text)

        if len(chunks) >= 2:
            # 第一塊的結尾應該出現在第二塊的開頭（重疊部分）
            chunk1_end = chunks[0].text[-50:]
            chunk2_start = chunks[1].text[:150]
            assert chunk1_end in chunk2_start

    def test_invariant_no_empty_chunks(self):
        """INV-1 的程式化驗證：不能有空白 chunk"""
        text = "\n\n\n\n\n"  # 只有換行符
        chunks = self.chunker.split(text)
        for chunk in chunks:
            assert len(chunk.text.strip()) > 0, "不應該產生空白 chunk"
```

### 評估測試：Retrieval 準確率

```python
# 檔案：tests/evaluation/test_retrieval_quality.py
# 這類測試需要真實的向量 DB 和嵌入模型，通常在 CI 的 nightly build 中執行

import pytest
from src.retrieval.retrieval_gate import RetrievalGate

# 測試集：問題 + 預期應該被檢索到的文件 ID
RETRIEVAL_TEST_CASES = [
    {
        "question": "員工的年假天數是幾天？",
        "expected_doc_ids": ["hr-leave-policy-2026", "hr-benefits-guide"],
        "should_not_contain": ["financial-report-q4"],
    },
    {
        "question": "如何申請報銷差旅費？",
        "expected_doc_ids": ["expense-policy-v2", "reimbursement-guide"],
        "should_not_contain": ["hr-leave-policy-2026"],
    },
]

class TestRetrievalQuality:

    @pytest.fixture(scope="class")
    def retriever(self):
        return KnowledgeRetriever(namespace="hr-*", top_k=5)

    @pytest.mark.parametrize("case", RETRIEVAL_TEST_CASES)
    def test_hit_at_5(self, retriever, case):
        """Hit@5：前 5 個結果中至少包含 1 個預期文件"""
        results = retriever.search(case["question"])
        result_ids = [r.doc_id for r in results]

        # 至少有一個預期文件被檢索到
        hit = any(doc_id in result_ids for doc_id in case["expected_doc_ids"])
        assert hit, f"問題「{case['question']}」未能檢索到預期文件"

    @pytest.mark.parametrize("case", RETRIEVAL_TEST_CASES)
    def test_namespace_isolation(self, retriever, case):
        """Namespace 隔離：不應該檢索到其他部門的文件"""
        results = retriever.search(case["question"])
        result_ids = [r.doc_id for r in results]

        for forbidden_id in case["should_not_contain"]:
            assert forbidden_id not in result_ids, \
                f"問題「{case['question']}」不應該檢索到 {forbidden_id}"
```

---

## 3.2 BDD：從使用者行為出發設計 RAG 功能

### Gherkin 語法在 RAG 中的應用

```gherkin
# 檔案：features/knowledge_ingestion.feature

Feature: 知識攝取（Knowledge Ingestion）
  作為 知識庫管理員
  我想要 將企業文件安全地納入 RAG 系統
  以便 員工能夠透過 AI 查詢正確的企業知識

  Background:
    Given 系統已連接到向量資料庫
    And 嵌入模型 text-embedding-3-large 已就緒

  Scenario: 成功攝取已審核的 HR 文件
    Given 一份 PDF 文件「年假政策 2026.pdf」
    And 文件的 metadata 包含 owner="hr-team", status="approved", last_updated="2026-01-15"
    When 知識庫管理員執行 /ingest hr-policies/年假政策2026.pdf
    Then 文件應該被分割成 3-8 個 chunks
    And 每個 chunk 應該被成功嵌入並存入向量 DB
    And chunk 的 namespace 應該是 "hr-leaves"
    And 系統應該回報「攝取成功，共 N 個 chunks」

  Scenario: 拒絕攝取過期文件
    Given 一份文件「報銷規定 2023.pdf」
    And 文件的 last_updated 距今超過 180 天
    When 知識庫管理員執行 /ingest finance/報銷規定2023.pdf
    Then 系統應該拒絕攝取
    And 回報錯誤「文件已超過 180 天未更新，請聯繫 owner 審核後再攝取」
    And 向量 DB 中不應該有此文件的任何 chunk

  Scenario: 攝取失敗時不留下殘餘 chunks（原子性）
    Given 一份 50 頁的文件正在攝取
    When 攝取到第 30 頁時 OpenAI API 回傳錯誤
    Then 系統應該回滾（rollback）已攝取的 30 頁 chunks
    And 向量 DB 中不應該有此批次的任何 chunk
    And 回報錯誤日誌給管理員
```

```gherkin
# 檔案：features/knowledge_query.feature

Feature: 知識查詢（Knowledge Query）
  作為 企業員工
  我想要 用自然語言詢問 AI 企業內部政策
  以便 快速找到正確答案而不需要手動翻閱文件

  Scenario: 成功查詢並引用正確來源
    Given 向量 DB 中有「年假政策 2026.pdf」的 chunks
    When 員工問「我每年有幾天年假？」
    Then 系統應該檢索到年假政策相關的 chunks（Hit@5）
    And 生成的答案應該基於這些 chunks
    And 答案末尾應該列出引用的文件來源
    And 答案不應該包含「根據現有文件無法回答」

  Scenario: 文件不存在時誠實回應
    Given 向量 DB 中沒有「股票期權政策」相關文件
    When 員工問「公司的股票期權怎麼計算？」
    Then 系統應該回應「根據現有文件無法回答」
    And 不應該自行推測或給出不確定的答案
    And 可以建議「請聯繫 HR 部門了解詳情」

  Scenario: 跨部門查詢被隔離拒絕
    Given 員工只有 HR 命名空間的存取權限
    When 員工問「Q4 的財務報告顯示什麼？」
    Then 系統不應該在財務命名空間中搜尋
    And 回應「您沒有權限查詢財務相關資訊」
```

---

## 3.3 SDD：規格驅動的 RAG 功能設計

### `/ingest` 斜線指令的規格文件

當需要新增一個知識攝取功能時，先用 `/specify` 產出規格：

```markdown
# spec.md — 批次文件攝取功能

## Problem Statement
目前的攝取流程是逐筆處理，500 份文件需要 2 小時。
需要支援批次攝取，並在失敗時只重試失敗的部分。

## Scope
- 支援批次攝取（單次最多 100 份文件）
- 每份文件獨立追蹤進度（成功/失敗/pending）
- 失敗的文件可以單獨重試
- 不在 Scope：即時攝取（streaming）、自動排程

## Assumptions
- 文件必須先上傳到 S3 或本地目錄，才能批次攝取
- 向量 DB 的並發寫入限制為 10 個連線

## Data Model
```python
@dataclass
class IngestJob:
    job_id: str                    # UUID
    files: list[str]               # 文件路徑列表
    namespace: str                 # 目標 namespace
    status: Literal["pending", "running", "completed", "partial_failed"]
    results: dict[str, IngestResult]  # key = file_path
    created_at: datetime
    completed_at: datetime | None

@dataclass
class IngestResult:
    file_path: str
    status: Literal["success", "failed", "skipped"]
    chunk_count: int | None
    error: str | None
    doc_ids: list[str]
```

## API Contract
```
POST /api/ingest/batch
  body: { files: string[], namespace: string }
  response: { job_id: string, status: "pending" }

GET /api/ingest/batch/{job_id}
  response: IngestJob

POST /api/ingest/batch/{job_id}/retry
  body: { files: string[] }  # 指定重試哪些失敗的文件
  response: { job_id: string }  # 新的 retry job
```

## Success Criteria
- 100 份文件的批次攝取在 30 分鐘內完成
- 單一文件失敗不影響其他文件的攝取
- 重試 API 只重試真正失敗的文件（不重試已成功的）
- 所有失敗有明確的錯誤訊息（非 "unknown error"）
```

---

## 3.4 三者在 RAG 中的整合流水線

```
需求：「支援批次文件攝取」

SDD 定義「做什麼」
  ↓  /specify 指令
  → spec.md（問題 + Data Model + API Contract + 成功標準）
  
BDD 定義「怎麼驗證」
  ↓  /plan-scenarios 指令
  → features/batch_ingestion.feature（Gherkin scenarios）
  
TDD 定義「怎麼實作」
  ↓  /implement 指令
  → Red（寫測試，確認失敗）
  → Green（實作，讓測試通過）
  → Refactor（清理程式碼）
```

### 三者的品質閘門

```
.agent/skills/rag-workflow/
├── 00-complexity-gate.md    ← 先評估任務複雜度
├── 01-spec-gate.md          ← 規格完整性：Data Model 有沒有定義？
├── 02-scenario-gate.md      ← 場景完整性：有沒有覆蓋失敗情境？
├── 03-build-gate.md         ← 實作品質：測試有先失敗再通過嗎？
├── 04-eval-gate.md          ← RAG 特有：Retrieval Hit@5 是否達標？
└── templates/
    ├── spec-rag-lite.md     ← Lite 模式（更新 prompt、調整參數）
    └── spec-rag-standard.md ← Standard 模式（新增知識來源、修改架構）
```

> 💡 **RAG 特有的 eval-gate**：傳統軟體只需要通過 Build Gate（單元/整合測試）；  
> RAG 系統還需要通過 Eval Gate — 確認 Retrieval 準確率達到 constitution 設定的標準（如 Hit@5 ≥ 80%）。

---

## 練習

1. **Gherkin 練習**：為「知識庫管理員刪除一份已過期文件」這個功能，寫出 3 個 Gherkin scenario（包含：正常刪除、刪除不存在的文件、刪除他人管理的文件）。

2. **SDD 練習**：為「支援從 Confluence 自動同步頁面到 RAG 知識庫」寫出一份迷你 spec.md，包含 Problem Statement、Data Model 和 API Contract。

3. **TDD 練習**：為以下函式寫出 2 個單元測試（一個正常情況、一個邊界情況）：
   ```python
   def validate_document_metadata(metadata: dict) -> tuple[bool, str]:
       """驗證文件 metadata 是否符合 Constitution Principle I"""
   ```

4. **思考題**：RAG 系統的 Eval Gate 如何在 CI/CD 中自動執行？如果 Retrieval Hit@5 從 85% 掉到 72%（可能因為新增了大量低品質文件），CI 應該怎麼處理？

---

> **下一章**：[第四章：複雜度門檻 — 適應性 RAG 工作流](04-complexity-gate.md)  
> 我們將學習如何根據任務複雜度，決定要走「快速修改」還是「完整規格開發」流程。

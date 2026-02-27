# 第五章：契約先行 — 知識 API 的合約治理

## 學習目標

讀完本章，你將能夠：
- 將 Design by Contract 的三要素應用到 RAG 的知識 API 設計
- 理解 Retrieval Gate 如何防止低品質知識進入查詢管線
- 列舉 RAG 知識系統的六大治理閘門及其觸發條件
- 說明 Knowledge Drift Detection 如何防止知識庫品質下滑

---

## 5.1 Design by Contract in RAG

### 知識 API 的合約三要素

**Design by Contract**（DbC）最初由 Bertrand Meyer 在 1986 年提出，  
定義函式的「前置條件、後置條件、不變量」。  
在 RAG 系統中，這個概念應用到每個知識操作：

```python
# 檔案：src/ingestion/ingestor.py

from dataclasses import dataclass
from typing import Literal

@dataclass
class IngestResult:
    doc_id: str
    chunk_count: int
    namespace: str

class KnowledgeIngestor:

    def ingest(
        self,
        file_path: str,
        namespace: str,
        metadata: dict,
    ) -> IngestResult:
        """
        將一份文件嵌入並存入向量資料庫。

        Preconditions（前置條件）：
          - metadata["status"] == "approved"
          - metadata["last_updated"] 距今不超過 180 天
          - namespace 必須是已授權的 namespace（在 allowed_namespaces 清單中）
          - file_path 指向的檔案必須存在且可讀取

        Postconditions（後置條件）：
          - 回傳的 IngestResult.chunk_count >= 1（至少一個 chunk）
          - 向量 DB 中確實存在 chunk_count 個屬於此 doc_id 的向量
          - 每個 chunk 的 metadata 包含 source、doc_id、chunk_index

        Invariants（不變量）：
          - INV-1: 任何 chunk 的 text 長度不得為 0
          - INV-2: 失敗時向量 DB 中不得有此批次的殘餘 chunk（原子性）
          - INV-3: namespace 必須符合 constitutional 定義的命名規範
        """

        # 前置條件驗證
        self._assert_preconditions(file_path, namespace, metadata)

        # 執行攝取（帶有 rollback 保護）
        result = self._execute_with_rollback(file_path, namespace, metadata)

        # 後置條件驗證
        self._assert_postconditions(result)

        return result

    def _assert_preconditions(self, file_path, namespace, metadata):
        """前置條件：失敗時拋出 PreconditionError，不執行任何寫入"""
        from datetime import datetime, timedelta

        if metadata.get("status") != "approved":
            raise PreconditionError(
                f"文件必須為 approved 狀態，當前狀態：{metadata.get('status')}"
            )

        last_updated = datetime.fromisoformat(metadata["last_updated"])
        if datetime.now() - last_updated > timedelta(days=180):
            raise PreconditionError(
                f"文件超過 180 天未更新（last_updated: {metadata['last_updated']}），"
                "請聯繫文件負責人審核後再攝取"
            )

        if namespace not in self.allowed_namespaces:
            raise PreconditionError(f"未授權的 namespace: {namespace}")

    def _assert_postconditions(self, result: IngestResult):
        """後置條件：驗證資料庫狀態是否符合預期"""
        actual_count = self.vector_db.count(doc_id=result.doc_id)
        if actual_count != result.chunk_count:
            raise PostconditionError(
                f"向量 DB 中的 chunk 數量（{actual_count}）"
                f"與回傳值（{result.chunk_count}）不符"
            )
```

> 🔑 **治理重點**：前置條件和後置條件的驗證不是選項，是**強制執行的合約**。  
> 任何繞過這些驗證的程式碼都違反了 Constitution Principle I。

---

## 5.2 Retrieval Gate：檢索品質的治理閘門

### 什麼是 Retrieval Gate

**Retrieval Gate** 是 RAG 版的 Contract-First Gate：

> 在生成答案之前，先驗證「檢索結果的品質是否符合標準」。  
> 品質不達標 → 不生成答案，改為回應「知識不足」。

```python
# 檔案：src/retrieval/retrieval_gate.py

from dataclasses import dataclass
from typing import Literal

@dataclass
class RetrievalGateResult:
    status: Literal["pass", "block"]
    reason: str | None
    chunks: list[dict]

class RetrievalGate:
    """
    在 LLM 生成答案前，驗證檢索結果的品質。
    這是 RAG 的 Contract-First Gate。
    """

    MIN_CHUNKS = 1           # 至少要有 1 個 chunk
    MIN_SCORE = 0.72         # 向量相似度閾值（低於此值視為不相關）
    MAX_AGE_DAYS = 180       # chunk 來源文件的最大年齡

    def validate(self, query: str, chunks: list[dict]) -> RetrievalGateResult:
        """
        驗證檢索結果是否可以交給 LLM 生成答案。

        Args:
            query: 使用者的問題
            chunks: 向量 DB 返回的 chunks（含相似度分數和 metadata）

        Returns:
            RetrievalGateResult（pass/block + 原因）
        """

        # 規則 1：必須至少有 1 個 chunk
        if len(chunks) < self.MIN_CHUNKS:
            return RetrievalGateResult(
                status="block",
                reason="knowledge_insufficient",
                chunks=[]
            )

        # 規則 2：最高分的 chunk 相似度必須達到閾值
        top_score = max(c["score"] for c in chunks)
        if top_score < self.MIN_SCORE:
            return RetrievalGateResult(
                status="block",
                reason=f"low_relevance (top score: {top_score:.2f} < {self.MIN_SCORE})",
                chunks=[]
            )

        # 規則 3：過濾掉過時的 chunks（Constitution Principle I）
        fresh_chunks = [
            c for c in chunks
            if self._is_fresh(c["metadata"].get("last_updated"))
        ]
        if not fresh_chunks:
            return RetrievalGateResult(
                status="block",
                reason="all_chunks_expired",
                chunks=[]
            )

        # 規則 4：過濾掉 deprecated 文件的 chunks
        valid_chunks = [
            c for c in fresh_chunks
            if c["metadata"].get("status") != "deprecated"
        ]
        if not valid_chunks:
            return RetrievalGateResult(
                status="block",
                reason="all_chunks_deprecated",
                chunks=[]
            )

        return RetrievalGateResult(status="pass", reason=None, chunks=valid_chunks)

    def _is_fresh(self, last_updated: str | None) -> bool:
        from datetime import datetime, timedelta
        if not last_updated:
            return False
        age = datetime.now() - datetime.fromisoformat(last_updated)
        return age.days <= self.MAX_AGE_DAYS
```

### 完整的查詢流水線（含 Gate）

```python
# 檔案：src/query/query_pipeline.py

class RAGQueryPipeline:

    def answer(self, question: str, user_namespace: str) -> dict:
        """
        完整的 RAG 查詢流水線：
        1. 嵌入問題
        2. 向量搜尋（限定 namespace）
        3. Retrieval Gate 驗證
        4. LLM 生成（Gate 通過後才執行）
        5. 記錄日誌（Constitution Principle IV）
        """

        # Step 1: 嵌入問題
        query_vector = self.embedder.embed(question)

        # Step 2: 向量搜尋（受 namespace 限制 — Principle III）
        raw_chunks = self.vector_db.search(
            vector=query_vector,
            namespace=user_namespace,
            top_k=10,
        )

        # Step 3: Retrieval Gate
        gate_result = self.retrieval_gate.validate(question, raw_chunks)

        if gate_result.status == "block":
            # Gate 阻擋 → 不調用 LLM，直接回應知識不足
            answer = self._knowledge_insufficient_response(gate_result.reason)
            sources = []
        else:
            # Gate 通過 → 調用 LLM 生成答案
            answer, sources = self._generate_answer(
                question, gate_result.chunks
            )

        # Step 4: 記錄日誌（不論成功失敗都要記錄）
        self.audit_logger.log({
            "question": question,
            "gate_status": gate_result.status,
            "chunks_used": [c["doc_id"] for c in gate_result.chunks],
            "answer_preview": answer[:100],
        })

        return {
            "answer": answer,
            "sources": sources,
            "gate_status": gate_result.status,
        }
```

---

## 5.3 六大治理閘門

| 閘門 | 觸發條件 | 作用 |
|------|---------|------|
| **Retrieval Gate** | 每次查詢 | 驗證檢索品質，防止低品質知識進入 LLM |
| **Ingest Gate** | 每次文件攝取 | 驗證 metadata、文件年齡、狀態 |
| **Namespace Gate** | 新增 namespace | 要求 ADR + 存取控制設計 |
| **Model Change Gate** | 更換嵌入/生成模型 | 要求 A/B 評估 + 分階段推出 |
| **Knowledge Drift Gate** | 定期掃描（每週） | 偵測知識庫品質下滑（陳舊文件比例） |
| **Audit Gate** | 每月 | 稽核 RAG 答案品質和使用者滿意度 |

---

## 5.4 Knowledge Drift Detection

### 什麼是知識漂移

RAG 系統最常見的長期問題不是某個 bug，而是「知識慢慢變舊了」：

```
第 1 個月：80% 的文件在有效期內 → 系統表現優秀
第 3 個月：65% 的文件在有效期內 → 系統開始出現過時答案
第 6 個月：40% 的文件在有效期內 → 用戶開始投訴 AI 說的和現實不符
第 9 個月：20% 的文件在有效期內 → 系統基本不可信
```

這個問題很隱蔽，因為系統並沒有「出錯」，只是安靜地變差了。

### Knowledge Drift Detector

```python
# 檔案：src/governance/drift_detector.py
# 建議每週由 cron job 或 GitHub Actions 自動執行

from datetime import datetime, timedelta

class KnowledgeDriftDetector:
    """
    定期掃描知識庫，偵測品質下滑的早期訊號。
    對應：Constitution Principle I（知識品質優先）
    """

    THRESHOLDS = {
        "fresh_ratio_warning": 0.75,   # 新鮮文件比例 < 75% 發出警告
        "fresh_ratio_critical": 0.60,  # 新鮮文件比例 < 60% 觸發緊急處理
        "deprecated_ratio_max": 0.10,  # 廢棄文件比例 > 10% 需要清理
    }

    def run_weekly_scan(self) -> dict:
        """執行每週知識品質掃描"""

        # 從向量 DB 取得所有文件的 metadata 摘要
        all_docs = self.vector_db.list_documents_metadata()

        report = {}
        for namespace in self.get_all_namespaces():
            ns_docs = [d for d in all_docs if d["namespace"] == namespace]
            report[namespace] = self._analyze_namespace(ns_docs)

        # 觸發告警
        self._trigger_alerts(report)
        return report

    def _analyze_namespace(self, docs: list[dict]) -> dict:
        now = datetime.now()
        total = len(docs)
        if total == 0:
            return {"status": "empty", "total": 0}

        fresh = sum(
            1 for d in docs
            if (now - datetime.fromisoformat(d["last_updated"])).days <= 180
        )
        deprecated = sum(1 for d in docs if d.get("status") == "deprecated")

        fresh_ratio = fresh / total
        deprecated_ratio = deprecated / total

        # 判定狀態
        if fresh_ratio < self.THRESHOLDS["fresh_ratio_critical"]:
            status = "critical"
        elif fresh_ratio < self.THRESHOLDS["fresh_ratio_warning"]:
            status = "warning"
        elif deprecated_ratio > self.THRESHOLDS["deprecated_ratio_max"]:
            status = "needs_cleanup"
        else:
            status = "healthy"

        return {
            "status": status,
            "total_docs": total,
            "fresh_docs": fresh,
            "fresh_ratio": round(fresh_ratio, 3),
            "deprecated_docs": deprecated,
            "oldest_doc": min(d["last_updated"] for d in docs),
        }

    def _trigger_alerts(self, report: dict):
        for namespace, stats in report.items():
            if stats["status"] == "critical":
                self.alert_manager.send_urgent(
                    f"🚨 [{namespace}] 知識庫嚴重老化！"
                    f"新鮮文件比例：{stats['fresh_ratio']:.0%}，"
                    f"立即通知各文件 owner 審核更新。"
                )
            elif stats["status"] == "warning":
                self.alert_manager.send_warning(
                    f"⚠️ [{namespace}] 知識庫開始老化，"
                    f"新鮮文件比例：{stats['fresh_ratio']:.0%}"
                )
```

---

## 5.5 不變量（Invariant）的 RAG 價值

本專案定義的 RAG 不變量（以 INV- 編號）：

```
INV-1: 任何 chunk 的 text 長度不得為 0（空白 chunk 不得存入向量 DB）
INV-2: 攝取失敗時向量 DB 不得有殘餘 chunk（原子性）
INV-3: namespace 命名必須符合 {department}-{category} 格式
INV-4: 每個 chunk 必須包含 source、doc_id、chunk_index、last_updated
INV-5: 禁止跨 namespace 的向量搜尋（除非經過 Namespace Gate 審核）
INV-6: 答案生成的 temperature 不得超過 0.3
```

這些不變量的價值：
- **明確**：不需要猜測「這樣做可以嗎？」
- **可驗證**：可以在單元測試和 CI/CD 中自動檢查
- **可共享**：MCP Server、Skills、AI Agent 都能遵守

---

## 練習

1. **DbC 練習**：為 `KnowledgeRetriever.search()` 函式設計 precondition、postcondition 和 invariant：
   - 輸入：query（字串）、namespace（字串）、top_k（整數）
   - 輸出：chunks 列表（含分數和 metadata）

2. **Gate 設計練習**：假設你要新增一個「讓外部供應商查詢產品 FAQ」的功能，設計一個 Vendor Access Gate，定義觸發條件和檢查項目。

3. **Drift Detection 練習**：為一個「每月審計」的稽核週期設計告警規則，比每週的 drift detector 更嚴格：需要追蹤哪些額外的指標（例如答案被用戶標記為「不正確」的比率）？

4. **思考題**：Retrieval Gate 的 `MIN_SCORE = 0.72` 是怎麼決定的？如果設太高（0.9），會有什麼問題？設太低（0.5），又有什麼風險？你會如何用實驗數據來校準這個值？

---

> **下一章**：[第六章：嵌入向量與分塊原理](06-embedding-and-chunking.md)  
> 我們將深入理解 Embedding 和 Chunking 的技術原理，這是 RAG 系統的「編譯器核心」。

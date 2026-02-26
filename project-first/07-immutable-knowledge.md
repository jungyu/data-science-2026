# 第七章：不可變知識管理與版本控制

## 學習目標

讀完本章，你將能夠：
- 解釋為什麼「直接覆蓋」知識庫中的文件是危險的
- 設計知識的版本快照機制和軟刪除策略
- 理解知識更新的原子性（Atomicity）如何防止部分失敗
- 說明為什麼知識不可變性是一個治理問題，而非純技術問題

---

## 7.1 知識可變狀態的問題

### 一個真實的知識庫災難情境

```
星期一下午 3:00：工程師 A 直接更新向量 DB 中的「退換貨政策」
                  （因為公司剛更新了退換貨條件）

星期一下午 3:05：更新進行到一半，OpenAI API 超時，攝取中斷

星期一下午 3:06：向量 DB 中有 23 個舊版 chunk + 7 個新版 chunk
                  查詢「退換貨政策」時，AI 混合引用了兩個版本

星期一下午 3:30：客服部門開始接到客戶投訴：「AI 說可以退換，
                  但你們的客服說不行！」

星期二下午：工程師 A 試圖回滾到舊版本，但找不到備份...
```

根源問題：**直接修改（in-place mutation）** 破壞了知識的一致性。

### 解法：知識不可變性（Knowledge Immutability）

核心原則：**知識庫只能新增，不能直接修改或刪除。**

```
❌ 錯誤的做法（直接覆蓋）：
   向量 DB [退換貨政策_v1_chunk_1, ..., 退換貨政策_v1_chunk_30]
   更新 → 直接替換為 [退換貨政策_v2_chunk_1, ..., 退換貨政策_v2_chunk_28]
   問題：更新中斷 → 混合版本 + 無法回滾

✅ 正確的做法（版本快照）：
   攝取新版本 → [退換貨政策_v2_chunk_1, ..., 退換貨政策_v2_chunk_28]
   驗證通過後 → 舊版本標記為 deprecated（不刪除）
   7 天後     → 舊版本才真正從索引中移除
   優點：任何時刻都可以回滾到舊版本，且過渡期兩個版本都存在
```

---

## 7.2 知識版本管理的設計

### 文件版本模型

```python
# 檔案：src/models/knowledge.py

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

@dataclass
class KnowledgeDocument:
    """
    知識庫中的文件版本記錄。
    每次攝取都產生新的 version，舊版本不刪除，只改 status。
    """

    doc_id: str           # 唯一文件 ID（UUID）
    source_path: str      # 原始檔案路徑
    version: str          # 語意化版本號，如 "2026.02.15-1"
    namespace: str        # 知識域
    status: Literal[
        "ingesting",      # 攝取中（鎖定狀態）
        "active",         # 當前使用中的版本
        "deprecated",     # 已廢棄（等待清理）
        "archived",       # 已封存（永久保留，不用於查詢）
        "failed",         # 攝取失敗（等待重試）
    ]
    chunk_count: int
    created_at: datetime
    deprecated_at: datetime | None = None
    metadata: dict = field(default_factory=dict)

    @property
    def is_queryable(self) -> bool:
        """只有 active 狀態的文件可以被查詢"""
        return self.status == "active"

    @property
    def should_be_cleaned(self) -> bool:
        """deprecated 且超過 7 天的文件應該被從索引中移除"""
        if self.status != "deprecated" or not self.deprecated_at:
            return False
        return (datetime.now() - self.deprecated_at).days >= 7
```

### 不可變的知識更新流程

```python
# 檔案：src/ingestion/versioned_ingestor.py

class VersionedKnowledgeIngestor:
    """
    帶版本控制的知識攝取器。
    實現「先新增、後廢棄、最後清理」的不可變更新模式。
    """

    def update_document(
        self,
        source_path: str,
        namespace: str,
        metadata: dict,
    ) -> KnowledgeDocument:
        """
        更新一份文件的完整流程：
        Phase 1: 攝取新版本（不觸碰舊版本）
        Phase 2: 驗證新版本品質
        Phase 3: 廢棄舊版本（標記，不刪除）

        Constitution Principle V：知識更新必須是原子性的。
        如果任何一個 Phase 失敗，回滾到攝取前的狀態。
        """

        # 找到現有的 active 版本（可能沒有）
        old_doc = self.registry.get_active_version(source_path, namespace)

        # Phase 1：攝取新版本（在單獨的 transaction 中進行）
        new_doc = self._ingest_new_version(source_path, namespace, metadata)

        # Phase 2：驗證新版本（Retrieval Gate 的簡化版本）
        validation = self._validate_new_version(new_doc)
        if not validation.passed:
            # 新版本品質不達標 → 刪除新版本，保留舊版本
            self._rollback_new_version(new_doc)
            raise IngestValidationError(
                f"新版本驗證失敗：{validation.reason}。舊版本維持不變。"
            )

        # Phase 3：廢棄舊版本（新版本已就緒才執行）
        if old_doc:
            self._deprecate_old_version(old_doc)

        # 記錄版本更新（Constitution Principle IV：可追溯）
        self.audit_log.record_version_update(
            old_doc_id=old_doc.doc_id if old_doc else None,
            new_doc_id=new_doc.doc_id,
            source_path=source_path,
        )

        return new_doc

    def _ingest_new_version(
        self, source_path, namespace, metadata
    ) -> KnowledgeDocument:
        """
        原子性攝取：要麼全部成功，要麼全部失敗。
        使用 transaction ID 確保中斷時可以清理殘餘 chunks。
        """
        import uuid
        transaction_id = str(uuid.uuid4())

        try:
            # 讀取文件
            text = self.document_loader.load(source_path)

            # 分塊（ADR-002 的策略）
            chunks = self.chunker.split(text, metadata={
                **metadata,
                "source": source_path,
                "transaction_id": transaction_id,
            })

            # 嵌入
            vectors = self.embedder.embed_batch([c.text for c in chunks])

            # 寫入向量 DB
            doc_id = str(uuid.uuid4())
            for i, (chunk, vector) in enumerate(zip(chunks, vectors)):
                self.vector_db.upsert(
                    id=f"{doc_id}_chunk_{i}",
                    vector=vector,
                    metadata={
                        **chunk.metadata,
                        "doc_id": doc_id,
                        "namespace": namespace,
                        "status": "active",
                    }
                )

            # 在文件 registry 中建立記錄
            new_doc = KnowledgeDocument(
                doc_id=doc_id,
                source_path=source_path,
                version=self._make_version(),
                namespace=namespace,
                status="active",
                chunk_count=len(chunks),
                created_at=datetime.now(),
                metadata=metadata,
            )
            self.registry.save(new_doc)
            return new_doc

        except Exception as e:
            # 清理此 transaction 的所有 chunks（Constitution Principle V）
            self.vector_db.delete_by_metadata(
                filter={"transaction_id": transaction_id}
            )
            raise IngestError(f"攝取失敗（已回滾）：{e}") from e

    def _deprecate_old_version(self, old_doc: KnowledgeDocument):
        """
        廢棄舊版本：不刪除，只改 status 為 deprecated。
        向量 DB 中的 chunk 也標記為 deprecated（不再被查詢到）。
        7 天後由清理任務真正移除。
        """
        # 更新 chunk 的 status（讓 Retrieval Gate 過濾掉）
        self.vector_db.update_metadata_by_filter(
            filter={"doc_id": old_doc.doc_id},
            update={"status": "deprecated"},
        )

        # 更新 registry 記錄
        old_doc.status = "deprecated"
        old_doc.deprecated_at = datetime.now()
        self.registry.save(old_doc)

    def _make_version(self) -> str:
        """產生版本號：YYYY.MM.DD-{序號}"""
        today = datetime.now().strftime("%Y.%m.%d")
        count = self.registry.count_today_versions()
        return f"{today}-{count + 1}"
```

---

## 7.3 原子性更新的 Context Manager

```python
# 檔案：src/ingestion/atomic_ingest.py

from contextlib import contextmanager

@contextmanager
def atomic_knowledge_update(vector_db, registry, transaction_id: str):
    """
    Context manager：確保知識更新的原子性。
    進入時：記錄起始狀態
    退出時：若有例外，自動清理此 transaction 的所有寫入
    
    類似 Immer 的 produce()，但針對的是向量 DB 的寫入。
    """
    # 記錄此 transaction 開始前的狀態
    snapshot = registry.create_snapshot(transaction_id)

    try:
        yield transaction_id  # 執行攝取操作
        # 成功：提交（不需要做什麼，寫入已在 DB 中）
        registry.commit_snapshot(snapshot)

    except Exception as e:
        # 失敗：回滾所有此 transaction 的寫入
        print(f"攝取失敗，回滾 transaction {transaction_id}...")

        # 清理向量 DB 中的殘餘 chunks
        deleted = vector_db.delete_by_metadata(
            filter={"transaction_id": transaction_id}
        )
        print(f"已清理 {deleted} 個殘餘 chunks")

        # 恢復 registry 到快照狀態
        registry.restore_snapshot(snapshot)

        raise  # 重新拋出例外

# 使用方式
with atomic_knowledge_update(vector_db, registry, "txn-123") as txn_id:
    chunks = chunker.split(text, metadata={"transaction_id": txn_id})
    vectors = embedder.embed_batch([c.text for c in chunks])
    vector_db.upsert_batch(chunks, vectors)
```

---

## 7.4 為什麼這是治理問題

不可變知識管理看起來是資料庫工程問題，為什麼要納入治理？

因為**如果沒有明確的規則，工程師會走「看起來更簡單」的直接覆蓋路徑：**

```python
# AI Agent 可能寫出這樣的「捷徑」程式碼
def update_document_quick(file_path, namespace):
    # 刪除舊版本的所有 chunks
    vector_db.delete_where(source=file_path, namespace=namespace)
    # 直接攝取新版本
    ingest_document(file_path, namespace)
```

這段程式碼「看起來能用」，但有三個問題：
1. **非原子性**：`delete` 成功但 `ingest` 失敗 → 知識空洞
2. **不可回滾**：刪除了舊版本，無法恢復
3. **無版本記錄**：不知道是誰在什麼時候做了這個更新

只有明確的治理規則才能防止：

> **Constitution Principle V：向量資料庫的文件只能新增新版本，不能直接刪除舊版本。所有刪除操作必須先標記為 deprecated，保留 7 天後才真正清除。**

---

## 練習

1. **Bug 找碴**：以下的文件更新程式碼有什麼問題？在什麼情況下會造成知識空洞？
   ```python
   def update_policy(file_path, namespace):
       # Step 1: 刪除舊版本
       vector_db.delete(filter={"source": file_path})
       # Step 2: 攝取新版本
       new_chunks = chunker.split(load(file_path))
       vectors = embedder.embed_batch([c.text for c in new_chunks])
       vector_db.upsert_batch(new_chunks, vectors)
   ```

2. **設計練習**：為 `KnowledgeDocument` 設計一個「版本歷史查詢」功能，能夠：
   - 查詢某份文件的所有歷史版本
   - 查詢某個版本在哪個時間段是 active 的
   - 比較兩個版本的 chunk 數量差異

3. **思考題**：RAG 系統的知識不可變性和資料庫的 ACID 特性有什麼關聯？  
   哪個 ACID 特性最重要（Atomicity / Consistency / Isolation / Durability）？

4. **實作練習**：為 `VersionedKnowledgeIngestor.update_document()` 寫一個單元測試，測試「Phase 2 驗證失敗時，舊版本必須維持 active 狀態」這個不變量。

---

> **下一章**：[第八章：四層防護 — RAG 安全體系](08-safety-layers.md)  
> 我們將學習如何為 RAG 系統建立多層安全防護，確保知識不被污染、濫用或洩漏。

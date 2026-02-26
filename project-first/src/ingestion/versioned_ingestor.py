"""
帶版本控制的知識攝取器。
實現「先新增、後廢棄、最後清理」的不可變更新模式。

來源：第七章 — 不可變的知識更新流程
"""

import uuid
from datetime import datetime, timedelta

from src.models.knowledge import KnowledgeDocument
from src.utils import IngestError, IngestValidationError, PreconditionError


class VersionedKnowledgeIngestor:
    """
    帶版本控制的知識攝取器。
    實現「先新增、後廢棄、最後清理」的不可變更新模式。
    """

    def __init__(
        self,
        registry: object,
        chunker: object,
        embedder: object,
        vector_db: object,
        document_loader: object,
        audit_log: object,
    ) -> None:
        self.registry = registry
        self.chunker = chunker
        self.embedder = embedder
        self.vector_db = vector_db
        self.document_loader = document_loader
        self.audit_log = audit_log

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
        # 前置條件驗證（與 KnowledgeIngestor 一致）
        self._assert_preconditions(namespace, metadata)

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
        self, source_path: str, namespace: str, metadata: dict
    ) -> KnowledgeDocument:
        """
        原子性攝取：要麼全部成功，要麼全部失敗。
        使用 transaction ID 確保中斷時可以清理殘餘 chunks。
        """
        transaction_id = str(uuid.uuid4())

        try:
            # 讀取文件
            text = self.document_loader.load(source_path)

            # 分塊（ADR-002 的策略）
            chunks = self.chunker.split(
                text,
                metadata={
                    **metadata,
                    "source": source_path,
                    "transaction_id": transaction_id,
                },
            )

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
                    },
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

    def _deprecate_old_version(self, old_doc: KnowledgeDocument) -> None:
        """
        廢棄舊版本：不刪除，只改 status 為 deprecated。
        向量 DB 中的 chunk 也標記為 deprecated（不再被查詢到）。
        30 天後由清理任務真正移除（Constitution Principle V）。
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

    def _validate_new_version(self, new_doc: KnowledgeDocument) -> object:
        """驗證新版本品質（簡化版 Retrieval Gate）。"""

        class ValidationResult:
            def __init__(self, passed: bool, reason: str = ""):
                self.passed = passed
                self.reason = reason

        if new_doc.chunk_count == 0:
            return ValidationResult(False, "新版本沒有任何 chunk")
        return ValidationResult(True)

    def _rollback_new_version(self, new_doc: KnowledgeDocument) -> None:
        """回滾新版本：刪除所有相關的 chunks 和 registry 記錄。"""
        self.vector_db.delete_by_metadata(filter={"doc_id": new_doc.doc_id})
        self.registry.delete(new_doc.doc_id)

    def _assert_preconditions(self, namespace: str, metadata: dict) -> None:
        """前置條件驗證：與 KnowledgeIngestor 一致（KA-2 enforcement）"""
        if metadata.get("status") != "approved":
            raise PreconditionError(
                f"文件必須為 approved 狀態，當前狀態：{metadata.get('status')}"
            )

        last_updated_str = metadata.get("last_updated")
        if last_updated_str:
            last_updated = datetime.fromisoformat(last_updated_str)
            if datetime.now() - last_updated > timedelta(days=180):
                raise PreconditionError(
                    f"文件超過 180 天未更新（last_updated: {last_updated_str}），"
                    "請聯繫文件負責人審核後再攝取"
                )

    def _make_version(self) -> str:
        """產生版本號：YYYY.MM.DD-{序號}"""
        today = datetime.now().strftime("%Y.%m.%d")
        count = self.registry.count_today_versions()
        return f"{today}-{count + 1}"

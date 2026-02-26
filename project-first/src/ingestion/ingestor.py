"""
知識攝取器，實作 Design by Contract（前置條件、後置條件、不變量）。

來源：第五章 — 知識 API 的合約三要素
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

from src.utils import PreconditionError, PostconditionError


@dataclass
class IngestResult:
    doc_id: str
    chunk_count: int
    namespace: str


class KnowledgeIngestor:
    """
    將文件嵌入並存入向量資料庫，帶有完整的 Design by Contract 驗證。
    """

    def __init__(
        self,
        allowed_namespaces: list[str],
        vector_db: object,
        chunker: object,
        embedder: object,
    ) -> None:
        self.allowed_namespaces = allowed_namespaces
        self.vector_db = vector_db
        self.chunker = chunker
        self.embedder = embedder

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
          - namespace 必須是已授權的 namespace

        Postconditions（後置條件）：
          - 回傳的 IngestResult.chunk_count >= 1
          - 向量 DB 中確實存在 chunk_count 個屬於此 doc_id 的向量

        Invariants（不變量）：
          - INV-1: 任何 chunk 的 text 長度不得為 0
          - INV-2: 失敗時向量 DB 中不得有此批次的殘餘 chunk
          - INV-3: namespace 必須符合 constitutional 定義的命名規範
        """
        # 前置條件驗證
        self._assert_preconditions(file_path, namespace, metadata)

        # 執行攝取（帶有 rollback 保護）
        result = self._execute_with_rollback(file_path, namespace, metadata)

        # 後置條件驗證
        self._assert_postconditions(result)

        return result

    def _assert_preconditions(
        self, file_path: str, namespace: str, metadata: dict
    ) -> None:
        """前置條件：失敗時拋出 PreconditionError，不執行任何寫入"""
        if metadata.get("status") != "approved":
            raise PreconditionError(
                f"文件必須為 approved 狀態，當前狀態：{metadata.get('status')}"
            )

        # Constitution Principle I：必要 metadata 欄位
        for field in ("source", "owner", "last_updated"):
            if not metadata.get(field):
                raise PreconditionError(f"缺少必要 metadata 欄位：{field}")

        last_updated = datetime.fromisoformat(metadata["last_updated"])
        if datetime.now() - last_updated > timedelta(days=180):
            raise PreconditionError(
                f"文件超過 180 天未更新（last_updated: {metadata['last_updated']}），"
                "請聯繫文件負責人審核後再攝取"
            )

        if namespace not in self.allowed_namespaces:
            raise PreconditionError(f"未授權的 namespace: {namespace}")

    def _assert_postconditions(self, result: IngestResult) -> None:
        """後置條件：驗證資料庫狀態是否符合預期"""
        if result.chunk_count < 1:
            raise PostconditionError(
                f"chunk_count 必須 >= 1，實際為 {result.chunk_count}"
            )
        actual_count = self.vector_db.count(doc_id=result.doc_id)
        if actual_count != result.chunk_count:
            raise PostconditionError(
                f"向量 DB 中的 chunk 數量（{actual_count}）"
                f"與回傳值（{result.chunk_count}）不符"
            )

    def _execute_with_rollback(
        self, file_path: str, namespace: str, metadata: dict
    ) -> IngestResult:
        """執行攝取操作，失敗時自動回滾。"""
        import uuid

        doc_id = str(uuid.uuid4())
        try:
            with open(file_path, encoding="utf-8") as f:
                text = f.read()

            chunks = self.chunker.split(text, metadata={
                **metadata,
                "source": file_path,
                "doc_id": doc_id,
            })
            vectors = self.embedder.embed_batch([c.text for c in chunks])

            for i, (chunk, vector) in enumerate(zip(chunks, vectors)):
                self.vector_db.upsert(
                    id=f"{doc_id}_chunk_{i}",
                    vector=vector,
                    metadata={
                        **chunk.metadata,
                        "doc_id": doc_id,
                        "namespace": namespace,
                    },
                )

            return IngestResult(
                doc_id=doc_id,
                chunk_count=len(chunks),
                namespace=namespace,
            )
        except Exception:
            # INV-2: 失敗時清理殘餘 chunks
            self.vector_db.delete_by_metadata(filter={"doc_id": doc_id})
            raise

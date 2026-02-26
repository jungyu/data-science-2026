"""KnowledgeIngestor 的 Design by Contract 測試。"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, mock_open, patch

import pytest

from src.ingestion.ingestor import KnowledgeIngestor
from src.utils import PreconditionError, PostconditionError, Chunk


class TestIngestorPreconditions:
    def setup_method(self):
        self.ingestor = KnowledgeIngestor(
            allowed_namespaces=["hr-leaves", "hr-benefits"],
            vector_db=MagicMock(),
            chunker=MagicMock(),
            embedder=MagicMock(),
        )
        self.valid_metadata = {
            "status": "approved",
            "source": "/data/policy.pdf",
            "owner": "hr-team",
            "last_updated": datetime.now().isoformat(),
        }

    def test_reject_unapproved_document(self):
        """前置條件：status != approved → PreconditionError"""
        meta = {**self.valid_metadata, "status": "draft"}
        with pytest.raises(PreconditionError, match="approved"):
            self.ingestor.ingest("file.pdf", "hr-leaves", meta)

    def test_reject_expired_document(self):
        """前置條件：超過 180 天 → PreconditionError"""
        old_date = (datetime.now() - timedelta(days=200)).isoformat()
        meta = {**self.valid_metadata, "last_updated": old_date}
        with pytest.raises(PreconditionError, match="180"):
            self.ingestor.ingest("file.pdf", "hr-leaves", meta)

    def test_reject_unauthorized_namespace(self):
        """前置條件：namespace 不在允許清單 → PreconditionError"""
        with pytest.raises(PreconditionError, match="未授權"):
            self.ingestor.ingest("file.pdf", "finance-reports", self.valid_metadata)

    def test_reject_missing_source(self):
        """前置條件：缺少 source 欄位 → PreconditionError"""
        meta = {**self.valid_metadata}
        del meta["source"]
        with pytest.raises(PreconditionError, match="source"):
            self.ingestor.ingest("file.pdf", "hr-leaves", meta)

    def test_reject_missing_owner(self):
        """前置條件：缺少 owner 欄位 → PreconditionError"""
        meta = {**self.valid_metadata}
        del meta["owner"]
        with pytest.raises(PreconditionError, match="owner"):
            self.ingestor.ingest("file.pdf", "hr-leaves", meta)


class TestIngestorPostconditions:
    @patch("builtins.open", mock_open(read_data="some document content"))
    def test_postcondition_chunk_count_zero(self):
        """後置條件：chunk_count == 0 → PostconditionError"""
        chunker = MagicMock()
        chunker.split.return_value = []  # 0 chunks

        embedder = MagicMock()
        embedder.embed_batch.return_value = []

        vector_db = MagicMock()
        vector_db.count.return_value = 0

        ingestor = KnowledgeIngestor(
            allowed_namespaces=["hr-leaves"],
            vector_db=vector_db,
            chunker=chunker,
            embedder=embedder,
        )

        meta = {
            "status": "approved",
            "source": "/data/policy.pdf",
            "owner": "hr-team",
            "last_updated": datetime.now().isoformat(),
        }
        with pytest.raises(PostconditionError, match="chunk_count"):
            ingestor.ingest("file.pdf", "hr-leaves", meta)


class TestIngestorRollback:
    @patch("builtins.open", mock_open(read_data="some document content"))
    def test_rollback_on_failure(self):
        """失敗時應清理殘餘 chunks（INV-2）"""
        chunker = MagicMock()
        chunker.split.side_effect = RuntimeError("chunking 失敗")

        vector_db = MagicMock()

        ingestor = KnowledgeIngestor(
            allowed_namespaces=["hr-leaves"],
            vector_db=vector_db,
            chunker=chunker,
            embedder=MagicMock(),
        )

        meta = {
            "status": "approved",
            "source": "/data/policy.pdf",
            "owner": "hr-team",
            "last_updated": datetime.now().isoformat(),
        }
        with pytest.raises(RuntimeError):
            ingestor.ingest("file.pdf", "hr-leaves", meta)

        # 應該呼叫 delete_by_metadata 清理
        vector_db.delete_by_metadata.assert_called_once()

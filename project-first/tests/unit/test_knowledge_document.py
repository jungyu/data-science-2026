"""KnowledgeDocument 資料模型的屬性測試。"""

from datetime import datetime, timedelta

from src.models.knowledge import KnowledgeDocument


class TestKnowledgeDocument:
    def _make_doc(self, status="active", deprecated_at=None):
        return KnowledgeDocument(
            doc_id="doc-001",
            source_path="/data/test.pdf",
            version="2026.02.15-1",
            namespace="hr-leaves",
            status=status,
            chunk_count=10,
            created_at=datetime.now(),
            deprecated_at=deprecated_at,
        )

    def test_is_queryable_when_active(self):
        """只有 active 狀態可查詢"""
        doc = self._make_doc(status="active")
        assert doc.is_queryable is True

    def test_not_queryable_when_deprecated(self):
        doc = self._make_doc(status="deprecated")
        assert doc.is_queryable is False

    def test_not_queryable_when_ingesting(self):
        doc = self._make_doc(status="ingesting")
        assert doc.is_queryable is False

    def test_not_queryable_when_failed(self):
        doc = self._make_doc(status="failed")
        assert doc.is_queryable is False

    def test_should_be_cleaned_after_30_days(self):
        """deprecated 超過 30 天 → 應清理（Constitution Principle V）"""
        old_date = datetime.now() - timedelta(days=31)
        doc = self._make_doc(status="deprecated", deprecated_at=old_date)
        assert doc.should_be_cleaned is True

    def test_should_not_be_cleaned_within_30_days(self):
        """deprecated 不到 30 天 → 不清理"""
        recent_date = datetime.now() - timedelta(days=15)
        doc = self._make_doc(status="deprecated", deprecated_at=recent_date)
        assert doc.should_be_cleaned is False

    def test_should_not_be_cleaned_when_active(self):
        """active 狀態不應被清理"""
        doc = self._make_doc(status="active")
        assert doc.should_be_cleaned is False

    def test_should_not_be_cleaned_without_deprecated_at(self):
        """deprecated 但沒有 deprecated_at → 不清理"""
        doc = self._make_doc(status="deprecated", deprecated_at=None)
        assert doc.should_be_cleaned is False

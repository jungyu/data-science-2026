"""RetrievalGate 的 4 條驗證規則單元測試。"""

from datetime import datetime, timedelta

from src.retrieval.retrieval_gate import RetrievalGate


class TestRetrievalGate:
    def setup_method(self):
        self.gate = RetrievalGate()
        self.fresh_date = (datetime.now() - timedelta(days=30)).isoformat()
        self.expired_date = (datetime.now() - timedelta(days=200)).isoformat()

    def _make_chunk(self, score=0.9, last_updated=None, status="active"):
        if last_updated is None:
            last_updated = self.fresh_date
        return {
            "text": "測試文字",
            "score": score,
            "doc_id": "doc-001",
            "metadata": {
                "last_updated": last_updated,
                "status": status,
            },
        }

    def test_rule1_block_when_no_chunks(self):
        """規則 1：0 個 chunk → block"""
        result = self.gate.validate("問題", [])
        assert result.status == "block"
        assert result.reason == "knowledge_insufficient"

    def test_rule2_block_when_low_relevance(self):
        """規則 2：最高分 < MIN_SCORE → block"""
        chunks = [self._make_chunk(score=0.5)]
        result = self.gate.validate("問題", chunks)
        assert result.status == "block"
        assert "low_relevance" in result.reason

    def test_rule3_block_when_all_expired(self):
        """規則 3：全部 chunk 都過期 → block"""
        chunks = [self._make_chunk(last_updated=self.expired_date)]
        result = self.gate.validate("問題", chunks)
        assert result.status == "block"
        assert result.reason == "all_chunks_expired"

    def test_rule4_block_when_all_deprecated(self):
        """規則 4：全部 chunk 都是 deprecated → block"""
        chunks = [self._make_chunk(status="deprecated")]
        result = self.gate.validate("問題", chunks)
        assert result.status == "block"
        assert result.reason == "all_chunks_deprecated"

    def test_pass_with_valid_chunks(self):
        """全部規則通過 → pass"""
        chunks = [self._make_chunk(), self._make_chunk(score=0.8)]
        result = self.gate.validate("問題", chunks)
        assert result.status == "pass"
        assert result.reason is None
        assert len(result.chunks) == 2

    def test_mixed_chunks_filter_deprecated(self):
        """混合 chunks：deprecated 被過濾，active 保留"""
        chunks = [
            self._make_chunk(status="active"),
            self._make_chunk(status="deprecated"),
        ]
        result = self.gate.validate("問題", chunks)
        assert result.status == "pass"
        assert len(result.chunks) == 1

    def test_constants_match_chapter_values(self):
        """驗證常數與教材一致"""
        assert RetrievalGate.MIN_CHUNKS == 1
        assert RetrievalGate.MIN_SCORE == 0.72
        assert RetrievalGate.MAX_AGE_DAYS == 180

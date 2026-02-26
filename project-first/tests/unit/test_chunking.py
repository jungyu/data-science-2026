"""
遞迴分塊器的單元測試。

來源：第三章 — 單元測試範例
"""

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

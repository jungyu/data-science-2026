"""
遞迴分塊策略（ADR-002 決定採用此策略）。

來源：第六章 — 四種 Chunking 策略
"""

from src.utils import Chunk, tokenize, get_last_n_tokens


class RecursiveChunker:
    """
    遞迴分塊策略（ADR-002 決定採用此策略）。

    優先在自然邊界切分，依序嘗試：
    段落（\\n\\n）→ 句子（。！？）→ 詞（，）→ 字元

    ✅ 優點：尊重文件的自然結構，語意完整
    ✅ 優點：速度快（比語意分塊快 3 倍）
    ❌ 缺點：不同文件的 chunk 大小不均
    適用：大多數企業文件（Word、PDF、Markdown）
    """

    SEPARATORS = ["\n\n", "\n", "。", "！", "？", "，", " ", ""]

    def __init__(self, target_size: int = 600, overlap: int = 100):
        self.target_size = target_size
        self.overlap = overlap

    def split(self, text: str, metadata: dict | None = None) -> list[Chunk]:
        if not text or not text.strip():
            return []

        chunks = self._recursive_split(text, self.SEPARATORS)
        cleaned_chunks = [chunk.strip() for chunk in chunks if chunk and chunk.strip()]

        result = []
        for i, chunk_text in enumerate(cleaned_chunks):
            chunk_metadata = {
                **(metadata or {}),
                "chunk_index": i,
                "total_chunks": len(cleaned_chunks),
            }
            result.append(Chunk(text=chunk_text, metadata=chunk_metadata))

        return result

    def _recursive_split(self, text: str, separators: list[str]) -> list[str]:
        """遞迴地用分隔符切分，直到所有塊都符合目標大小"""
        if not separators:
            # 最後手段：直接按字元切
            return [
                text[i : i + self.target_size]
                for i in range(0, len(text), self.target_size - self.overlap)
            ]

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
            prev_tail = get_last_n_tokens(chunks[i - 1], self.overlap)
            # 盡量對齊句界，避免從句子中間開始（例："...容。")
            sentence_boundary_indices = [prev_tail.find(p) for p in ("。", "！", "？", "\n")]
            sentence_boundary_indices = [idx for idx in sentence_boundary_indices if idx >= 0]
            if sentence_boundary_indices:
                first_boundary = min(sentence_boundary_indices)
                if first_boundary + 1 < len(prev_tail):
                    prev_tail = prev_tail[first_boundary + 1 :].lstrip()
            result.append(prev_tail + " " + chunks[i])
        return result

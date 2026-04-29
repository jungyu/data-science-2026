from __future__ import annotations

from app.rag.schemas import KnowledgeChunk


def select_top_chunks(chunks: list[KnowledgeChunk], limit: int) -> list[KnowledgeChunk]:
    return sorted(chunks, key=lambda chunk: chunk.combined_score, reverse=True)[:limit]

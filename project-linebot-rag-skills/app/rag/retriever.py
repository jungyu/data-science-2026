from __future__ import annotations

from dataclasses import dataclass

from app.rag.embedder import EmbeddingProvider
from app.rag.reranker import select_top_chunks
from app.rag.schemas import KnowledgeChunk, RetrievalLogRecord
from app.storage.knowledge_repo import KnowledgeRepository
from app.storage.logs_repo import LogsRepository


@dataclass
class RAGRetriever:
    embedder: EmbeddingProvider
    knowledge_repo: KnowledgeRepository
    logs_repo: LogsRepository
    final_context_k: int = 4

    async def retrieve(
        self,
        query: str,
        *,
        categories: list[str] | None = None,
        top_k: int = 8,
        line_user_id: str | None = None,
        skill_id: str | None = None,
    ) -> list[KnowledgeChunk]:
        try:
            embedding = await self.embedder.embed_query(query)
            chunks = await self.knowledge_repo.match_private_knowledge(
                query_embedding=embedding,
                query_text=query,
                categories=categories,
                top_k=top_k,
            )
            selected = select_top_chunks(chunks, self.final_context_k)
            await self.logs_repo.log_retrieval(
                RetrievalLogRecord(
                    line_user_id=line_user_id,
                    query=query,
                    skill_id=skill_id,
                    category_filter=categories or [],
                    retrieved_ids=[chunk.id for chunk in selected],
                    scores={
                        chunk.id: {
                            "vector_score": chunk.vector_score,
                            "keyword_score": chunk.keyword_score,
                            "combined_score": chunk.combined_score,
                        }
                        for chunk in selected
                    },
                )
            )
            return selected
        except Exception:
            return []

    def build_context(self, chunks: list[KnowledgeChunk]) -> str:
        if not chunks:
            return "No retrieved context."
        blocks: list[str] = []
        for index, chunk in enumerate(chunks[: self.final_context_k], start=1):
            title = chunk.title or f"Chunk {index}"
            blocks.append(f"[{index}] {title}\nCategory: {chunk.category}\n{chunk.content}")
        return "\n\n".join(blocks)

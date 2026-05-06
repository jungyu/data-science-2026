"""Supabase store — 既有 RPC 路徑包裝為 KnowledgeStore Protocol 實作。

對應 spec-24 / task-24 步驟 2。
"""

from __future__ import annotations

from app.rag.schemas import KnowledgeChunk
from app.storage.knowledge_repo import KnowledgeRepository
from app.storage.knowledge_store import (
    KnowledgeChunkInsert,
    SearchFilters,
)
from app.storage.supabase_client import SupabaseRestClient


class SupabaseStore:
    name = "supabase"

    def __init__(self, *, client: SupabaseRestClient, repo: KnowledgeRepository) -> None:
        self._client = client
        self._repo = repo

    async def search(
        self,
        *,
        query_embedding: list[float],
        query_text: str | None = None,
        filters: SearchFilters | None = None,
        top_k: int = 8,
    ) -> list[KnowledgeChunk]:
        return await self._repo.match_private_knowledge(
            query_embedding=query_embedding,
            query_text=query_text or "",
            categories=filters.categories if filters else None,
            top_k=top_k,
            vector_weight=filters.vector_weight if filters else 1.0,
            keyword_weight=filters.keyword_weight if filters else 0.0,
        )

    async def upsert(self, chunks: list[KnowledgeChunkInsert]) -> int:
        # Supabase schema 定 id 為 uuid 由 db 自動產生；
        # 移除 chunk.id（其它 store 用的 deterministic 字串）避免型別衝突。
        # 去重靠 content_hash unique。
        rows = []
        for chunk in chunks:
            row = chunk.model_dump()
            row.pop("id", None)
            rows.append(row)
        await self._client.upsert(
            "private_knowledge", rows, on_conflict="content_hash"
        )
        return len(rows)

    async def delete_by_source(self, source_id: str) -> int:
        # 教學版簡化：未實作刪除（學生若需要再加）
        # PostgREST DELETE 需要 supabase_client 提供對應 method；目前未提供
        return 0

    async def source_hash(self, source_id: str) -> str | None:
        rows = await self._client.select(
            "private_knowledge",
            {"source_id": f"eq.{source_id}", "select": "content_hash", "limit": "1"},
        )
        return rows[0]["content_hash"] if rows else None

    async def health_check(self) -> bool:
        try:
            await self._client.select("private_knowledge", {"limit": "1"})
            return True
        except Exception:
            return False

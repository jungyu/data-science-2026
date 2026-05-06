"""Knowledge store registry — 對應 spec-24 / task-24。

提供 `build_store(settings)` 工廠函式，依 `knowledge_store_backend` 選實作。
"""

from __future__ import annotations

from app.config import Settings
from app.storage.knowledge_store import KnowledgeStore


def build_store(settings: Settings) -> KnowledgeStore:
    backend = settings.knowledge_store_backend
    if backend == "supabase":
        from app.storage.knowledge_repo import KnowledgeRepository
        from app.storage.stores.supabase_store import SupabaseStore
        from app.storage.supabase_client import SupabaseRestClient

        client = SupabaseRestClient(settings)
        return SupabaseStore(client=client, repo=KnowledgeRepository(client))

    if backend == "sqlite_vec":
        from app.storage.stores.sqlite_vec_store import SqliteVecStore

        return SqliteVecStore(path=settings.sqlite_vec_path, dim=settings.sqlite_vec_dim)

    if backend == "pinecone":
        from app.storage.stores.pinecone_store import PineconeStore

        return PineconeStore(
            api_key=settings.pinecone_api_key,
            index_name=settings.pinecone_index,
        )

    raise ValueError(
        f"unknown knowledge_store_backend: {backend!r}. "
        "Supported: supabase | sqlite_vec | pinecone"
    )

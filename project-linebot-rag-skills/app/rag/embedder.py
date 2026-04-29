from __future__ import annotations

from typing import Protocol

from app.config import Settings


class EmbeddingProvider(Protocol):
    async def embed_query(self, text: str) -> list[float]:
        ...


class OpenAICompatibleEmbedder:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = None

    async def embed_query(self, text: str) -> list[float]:
        if self._client is None:
            from openai import AsyncOpenAI

            self._client = AsyncOpenAI(
                api_key=self._settings.openai_api_key or None,
                base_url=self._settings.openai_base_url,
            )
        response = await self._client.embeddings.create(
            model=self._settings.embedding_model,
            input=text.strip(),
        )
        return list(response.data[0].embedding)

from __future__ import annotations

from typing import Iterable

from openai import OpenAI

from destiny.config import Settings


class EmbeddingClient:
    def __init__(self, settings: Settings) -> None:
        self._client = OpenAI(api_key=settings.openai_api_key)
        self._model = settings.embedding_model
        self._dim = settings.embedding_dim

    def embed(self, text: str) -> list[float]:
        resp = self._client.embeddings.create(model=self._model, input=text)
        vec = resp.data[0].embedding
        if len(vec) != self._dim:
            raise ValueError(
                f"Embedding dim mismatch: got {len(vec)}, expected {self._dim}. "
                "Check EMBEDDING_MODEL vs knowledge_atoms.embedding vector(N)."
            )
        return vec

    def embed_many(self, texts: Iterable[str]) -> list[list[float]]:
        texts = list(texts)
        if not texts:
            return []
        resp = self._client.embeddings.create(model=self._model, input=texts)
        return [d.embedding for d in resp.data]

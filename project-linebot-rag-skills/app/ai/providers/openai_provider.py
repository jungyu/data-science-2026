from __future__ import annotations

from app.config import Settings


class OpenAILLM:
    """OpenAI Responses API — for openai.com endpoints."""

    def __init__(self, settings: Settings, model: str) -> None:
        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(
            api_key=settings.openai_api_key or None,
            base_url=settings.openai_base_url,
        )
        self._model = model

    async def complete(self, prompt: str) -> str:
        response = await self._client.responses.create(
            model=self._model,
            input=prompt,
        )
        return response.output_text


class OpenAIChatLLM:
    """OpenAI Chat Completions API — for OpenAI-compatible endpoints (GitHub Copilot, etc.)."""

    def __init__(self, api_key: str, base_url: str, model: str) -> None:
        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(api_key=api_key or None, base_url=base_url)
        self._model = model

    async def complete(self, prompt: str) -> str:
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[{"role": "user", "content": prompt}],
        )
        if not response.choices:
            raise RuntimeError(
                "OpenAI-compatible API returned no choices (possible content filter)"
            )
        return response.choices[0].message.content or ""


class OpenAIEmbedder:
    def __init__(self, settings: Settings) -> None:
        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(
            api_key=settings.openai_api_key or None,
            base_url=settings.openai_base_url,
        )
        self._model = settings.embedding_model

    async def embed_query(self, text: str) -> list[float]:
        response = await self._client.embeddings.create(
            model=self._model,
            input=text.strip(),
        )
        return list(response.data[0].embedding)

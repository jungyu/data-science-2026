from __future__ import annotations

import time

from app.config import Settings
from app.observability.tracer import record_llm_call_if_traced


class OpenAILLM:
    """OpenAI Responses API — for openai.com endpoints."""

    def __init__(self, settings: Settings, model: str, temperature: float | None = None) -> None:
        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(
            api_key=settings.openai_api_key or None,
            base_url=settings.openai_base_url,
        )
        self._model = model
        self._temperature = temperature

    async def complete(self, prompt: str) -> str:
        t0 = time.time()
        kwargs: dict = {"model": self._model, "input": prompt}
        temperature = getattr(self, "_temperature", None)
        if temperature is not None:
            kwargs["temperature"] = temperature
        response = await self._client.responses.create(**kwargs)
        usage = getattr(response, "usage", None)
        if usage is not None:
            record_llm_call_if_traced(
                model=self._model,
                provider="openai",
                input_tokens=getattr(usage, "input_tokens", 0) or 0,
                output_tokens=getattr(usage, "output_tokens", 0) or 0,
                cached_tokens=getattr(usage, "input_tokens_cached", 0) or 0,
                duration_ms=int((time.time() - t0) * 1000),
            )
        return response.output_text


class OpenAIChatLLM:
    """OpenAI Chat Completions API — for OpenAI-compatible endpoints (GitHub Copilot, etc.)."""

    def __init__(self, api_key: str, base_url: str, model: str, temperature: float | None = None) -> None:
        from openai import AsyncOpenAI

        self._client = AsyncOpenAI(api_key=api_key or None, base_url=base_url)
        self._model = model
        self._temperature = temperature

    async def complete(self, prompt: str) -> str:
        t0 = time.time()
        kwargs: dict = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
        }
        temperature = getattr(self, "_temperature", None)
        if temperature is not None:
            kwargs["temperature"] = temperature
        response = await self._client.chat.completions.create(**kwargs)
        if not response.choices:
            raise RuntimeError(
                "OpenAI-compatible API returned no choices (possible content filter)"
            )
        usage = getattr(response, "usage", None)
        if usage is not None:
            record_llm_call_if_traced(
                model=self._model,
                provider="openai-chat",
                input_tokens=getattr(usage, "prompt_tokens", 0) or 0,
                output_tokens=getattr(usage, "completion_tokens", 0) or 0,
                duration_ms=int((time.time() - t0) * 1000),
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
        t0 = time.time()
        response = await self._client.embeddings.create(
            model=self._model,
            input=text.strip(),
        )
        usage = getattr(response, "usage", None)
        if usage is not None:
            record_llm_call_if_traced(
                model=self._model,
                provider="openai-embed",
                input_tokens=getattr(usage, "prompt_tokens", 0) or 0,
                output_tokens=0,
                duration_ms=int((time.time() - t0) * 1000),
            )
        return list(response.data[0].embedding)

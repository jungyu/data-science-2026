from __future__ import annotations


class GeminiLLM:
    """Google Gemini — uses the google-genai SDK."""

    def __init__(self, api_key: str, model: str, temperature: float | None = None) -> None:
        from google import genai

        self._client = genai.Client(api_key=api_key)
        self._model = model
        self._temperature = temperature

    async def complete(self, prompt: str) -> str:
        kwargs: dict = {"model": self._model, "contents": prompt}
        temperature = getattr(self, "_temperature", None)
        if temperature is not None:
            from google.genai import types
            kwargs["config"] = types.GenerateContentConfig(temperature=temperature)
        response = await self._client.aio.models.generate_content(**kwargs)
        # response.text is None when the response is blocked by safety filters.
        if not response.text:
            raise RuntimeError(
                f"Gemini returned no text (finish_reason="
                f"{response.candidates[0].finish_reason if response.candidates else 'unknown'})"
            )
        return response.text


class GeminiEmbedder:
    def __init__(self, api_key: str, model: str) -> None:
        from google import genai

        self._client = genai.Client(api_key=api_key)
        self._model = model

    async def embed_query(self, text: str) -> list[float]:
        response = await self._client.aio.models.embed_content(
            model=self._model,
            contents=text.strip(),
        )
        if not response.embeddings:
            raise RuntimeError("Gemini embed_content returned an empty embeddings list")
        return list(response.embeddings[0].values)

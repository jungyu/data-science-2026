"""
Acceptance tests for app/ai/ — factory dispatch, provider happy paths,
and all error-handling paths introduced in the audit.
"""
from __future__ import annotations

import asyncio
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.factory import (
    EmbedBackend,
    LLMBackend,
    build_embedder,
    build_llm,
    has_llm_configured,
)
from app.config import Settings


# ─── helpers ─────────────────────────────────────────────────────────────────

def _s(**kw) -> Settings:
    """Minimal Settings with all keys blanked; caller supplies what matters."""
    base = dict(
        line_channel_secret="x",
        line_channel_access_token="x",
        supabase_url="https://test.supabase.co",
        supabase_service_role_key="x",
        openai_api_key="",
        anthropic_api_key="",
        gemini_api_key="",
        github_copilot_token="",
    )
    base.update(kw)
    return Settings(**base)


def _fake_google_modules() -> dict:
    """Minimal sys.modules patch that satisfies `from google import genai`."""
    mock_genai = MagicMock()
    mock_genai.Client = MagicMock(return_value=MagicMock())
    mock_google = MagicMock()
    mock_google.genai = mock_genai
    return {"google": mock_google, "google.genai": mock_genai}


def _fake_anthropic_module() -> dict:
    """Minimal sys.modules patch that satisfies `import anthropic`."""
    mock_mod = MagicMock()
    mock_mod.AsyncAnthropic = MagicMock(return_value=MagicMock())
    return {"anthropic": mock_mod}


# ─── Factory: has_llm_configured ─────────────────────────────────────────────

class TestHasLlmConfigured:
    def test_openai_with_key(self):
        assert has_llm_configured(_s(ai_provider="openai", openai_api_key="sk-x")) is True

    def test_openai_empty_key(self):
        assert has_llm_configured(_s(ai_provider="openai", openai_api_key="")) is False

    def test_claude_with_key(self):
        assert has_llm_configured(_s(ai_provider="claude", anthropic_api_key="sk-ant-x")) is True

    def test_claude_empty_key(self):
        assert has_llm_configured(_s(ai_provider="claude", anthropic_api_key="")) is False

    def test_gemini_with_key(self):
        assert has_llm_configured(_s(ai_provider="gemini", gemini_api_key="AIza-x")) is True

    def test_github_copilot_with_token(self):
        assert has_llm_configured(_s(ai_provider="github_copilot", github_copilot_token="ghp_x")) is True

    def test_github_copilot_empty_token(self):
        assert has_llm_configured(_s(ai_provider="github_copilot", github_copilot_token="")) is False

    def test_unknown_provider_returns_false(self):
        assert has_llm_configured(_s(ai_provider="mystery_llm")) is False


# ─── Factory: build_llm dispatch ─────────────────────────────────────────────

class TestBuildLlm:
    def test_openai_returns_llm_backend(self):
        with patch("openai.AsyncOpenAI", return_value=MagicMock()):
            result = build_llm(_s(ai_provider="openai", openai_api_key="sk-x"), "router")
        assert isinstance(result, LLMBackend)

    def test_router_role_uses_router_model(self):
        with patch("openai.AsyncOpenAI", return_value=MagicMock()):
            result = build_llm(
                _s(ai_provider="openai", openai_api_key="sk-x", router_model="gpt-4o-mini"),
                "router",
            )
        assert result._model == "gpt-4o-mini"

    def test_generator_role_uses_generator_model(self):
        with patch("openai.AsyncOpenAI", return_value=MagicMock()):
            result = build_llm(
                _s(ai_provider="openai", openai_api_key="sk-x", generator_model="gpt-4o"),
                "generator",
            )
        assert result._model == "gpt-4o"

    def test_claude_dispatch(self):
        with patch.dict(sys.modules, _fake_anthropic_module()):
            result = build_llm(_s(ai_provider="claude", anthropic_api_key="sk-ant-x"), "generator")
        assert isinstance(result, LLMBackend)

    def test_gemini_dispatch(self):
        with patch.dict(sys.modules, _fake_google_modules()):
            result = build_llm(_s(ai_provider="gemini", gemini_api_key="AIza-x"), "generator")
        assert isinstance(result, LLMBackend)

    def test_github_copilot_dispatch(self):
        with patch("openai.AsyncOpenAI", return_value=MagicMock()):
            result = build_llm(
                _s(ai_provider="github_copilot", github_copilot_token="ghp_x"),
                "router",
            )
        assert isinstance(result, LLMBackend)

    def test_unknown_provider_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown AI provider"):
            build_llm(_s(ai_provider="mystery_llm"), "router")


# ─── Factory: build_embedder dispatch ────────────────────────────────────────

class TestBuildEmbedder:
    def test_openai_returns_embed_backend(self):
        with patch("openai.AsyncOpenAI", return_value=MagicMock()):
            result = build_embedder(_s(embedding_provider="openai", openai_api_key="sk-x"))
        assert isinstance(result, EmbedBackend)

    def test_gemini_dispatch(self):
        with patch.dict(sys.modules, _fake_google_modules()):
            result = build_embedder(_s(embedding_provider="gemini", gemini_api_key="AIza-x"))
        assert isinstance(result, EmbedBackend)

    def test_unknown_provider_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown embedding provider"):
            build_embedder(_s(embedding_provider="azure_ai"))


# ─── OpenAILLM ───────────────────────────────────────────────────────────────

class TestOpenAILLM:
    def _make(self, mock_client) -> object:
        from app.ai.providers.openai_provider import OpenAILLM

        inst = OpenAILLM.__new__(OpenAILLM)
        inst._client = mock_client
        inst._model = "gpt-4o"
        return inst

    def test_complete_returns_output_text(self):
        mock_client = MagicMock()
        mock_client.responses.create = AsyncMock(return_value=MagicMock(output_text="Hello!"))

        result = asyncio.run(self._make(mock_client).complete("Hi"))

        assert result == "Hello!"
        mock_client.responses.create.assert_awaited_once()

    def test_complete_passes_prompt_as_input(self):
        mock_client = MagicMock()
        mock_client.responses.create = AsyncMock(return_value=MagicMock(output_text="ok"))

        asyncio.run(self._make(mock_client).complete("tell me something"))

        call_kwargs = mock_client.responses.create.call_args.kwargs
        assert call_kwargs["input"] == "tell me something"
        assert call_kwargs["model"] == "gpt-4o"


# ─── OpenAIChatLLM ───────────────────────────────────────────────────────────

class TestOpenAIChatLLM:
    def _make(self, mock_client) -> object:
        from app.ai.providers.openai_provider import OpenAIChatLLM

        inst = OpenAIChatLLM.__new__(OpenAIChatLLM)
        inst._client = mock_client
        inst._model = "gpt-4o-mini"
        return inst

    def _response(self, content: str | None):
        return MagicMock(choices=[MagicMock(message=MagicMock(content=content))])

    def test_complete_returns_message_content(self):
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=self._response("Good answer"))

        result = asyncio.run(self._make(mock_client).complete("Q"))

        assert result == "Good answer"

    def test_none_content_returns_empty_string(self):
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=self._response(None))

        result = asyncio.run(self._make(mock_client).complete("Q"))

        assert result == ""

    def test_empty_choices_raises_runtime_error(self):
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=MagicMock(choices=[]))

        with pytest.raises(RuntimeError, match="no choices"):
            asyncio.run(self._make(mock_client).complete("Q"))

    def test_prompt_sent_as_user_message(self):
        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=self._response("ok"))

        asyncio.run(self._make(mock_client).complete("hello"))

        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert call_kwargs["messages"] == [{"role": "user", "content": "hello"}]


# ─── OpenAIEmbedder ──────────────────────────────────────────────────────────

class TestOpenAIEmbedder:
    def _make(self, mock_client) -> object:
        from app.ai.providers.openai_provider import OpenAIEmbedder

        inst = OpenAIEmbedder.__new__(OpenAIEmbedder)
        inst._client = mock_client
        inst._model = "text-embedding-3-small"
        return inst

    def test_returns_embedding_vector(self):
        mock_client = MagicMock()
        mock_client.embeddings.create = AsyncMock(
            return_value=MagicMock(data=[MagicMock(embedding=[0.1, 0.2, 0.3])])
        )

        result = asyncio.run(self._make(mock_client).embed_query("test"))

        assert result == [0.1, 0.2, 0.3]

    def test_strips_surrounding_whitespace(self):
        mock_client = MagicMock()
        mock_client.embeddings.create = AsyncMock(
            return_value=MagicMock(data=[MagicMock(embedding=[0.5])])
        )

        asyncio.run(self._make(mock_client).embed_query("  hello  "))

        assert mock_client.embeddings.create.call_args.kwargs["input"] == "hello"


# ─── AnthropicLLM ────────────────────────────────────────────────────────────

class TestAnthropicLLM:
    def _make(self, mock_client) -> object:
        from app.ai.providers.anthropic_provider import AnthropicLLM

        inst = AnthropicLLM.__new__(AnthropicLLM)
        inst._client = mock_client
        inst._model = "claude-sonnet-4-6"
        return inst

    def _block(self, kind: str, text: str = ""):
        b = MagicMock()
        b.type = kind
        b.text = text
        return b

    def test_complete_returns_text_block_content(self):
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=MagicMock(
            content=[self._block("text", "回答內容")],
            stop_reason="end_turn",
        ))

        result = asyncio.run(self._make(mock_client).complete("問題"))

        assert result == "回答內容"

    def test_skips_tool_use_block_returns_text(self):
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=MagicMock(
            content=[self._block("tool_use"), self._block("text", "文字回應")],
            stop_reason="tool_use",
        ))

        result = asyncio.run(self._make(mock_client).complete("問題"))

        assert result == "文字回應"

    def test_no_text_block_raises_runtime_error(self):
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=MagicMock(
            content=[self._block("tool_use")],
            stop_reason="tool_use",
        ))

        with pytest.raises(RuntimeError, match="no text block"):
            asyncio.run(self._make(mock_client).complete("問題"))

    def test_empty_content_raises_runtime_error(self):
        mock_client = MagicMock()
        mock_client.messages.create = AsyncMock(return_value=MagicMock(
            content=[],
            stop_reason="end_turn",
        ))

        with pytest.raises(RuntimeError, match="no text block"):
            asyncio.run(self._make(mock_client).complete("問題"))


# ─── GeminiLLM ───────────────────────────────────────────────────────────────

class TestGeminiLLM:
    def _make(self, mock_client) -> object:
        from app.ai.providers.gemini_provider import GeminiLLM

        inst = GeminiLLM.__new__(GeminiLLM)
        inst._client = mock_client
        inst._model = "gemini-2.0-flash"
        return inst

    def test_complete_returns_text(self):
        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(
            return_value=MagicMock(text="Gemini 回應")
        )

        result = asyncio.run(self._make(mock_client).complete("問題"))

        assert result == "Gemini 回應"

    def test_none_text_raises_with_finish_reason(self):
        mock_candidate = MagicMock()
        mock_candidate.finish_reason = "SAFETY"
        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(
            return_value=MagicMock(text=None, candidates=[mock_candidate])
        )

        with pytest.raises(RuntimeError, match="no text"):
            asyncio.run(self._make(mock_client).complete("問題"))

    def test_empty_string_text_raises(self):
        mock_client = MagicMock()
        mock_client.aio.models.generate_content = AsyncMock(
            return_value=MagicMock(text="", candidates=[])
        )

        with pytest.raises(RuntimeError, match="no text"):
            asyncio.run(self._make(mock_client).complete("問題"))


# ─── GeminiEmbedder ──────────────────────────────────────────────────────────

class TestGeminiEmbedder:
    def _make(self, mock_client) -> object:
        from app.ai.providers.gemini_provider import GeminiEmbedder

        inst = GeminiEmbedder.__new__(GeminiEmbedder)
        inst._client = mock_client
        inst._model = "text-embedding-004"
        return inst

    def test_returns_embedding_vector(self):
        mock_client = MagicMock()
        mock_client.aio.models.embed_content = AsyncMock(
            return_value=MagicMock(embeddings=[MagicMock(values=[0.1, 0.2, 0.3])])
        )

        result = asyncio.run(self._make(mock_client).embed_query("text"))

        assert result == [0.1, 0.2, 0.3]

    def test_empty_embeddings_raises_runtime_error(self):
        mock_client = MagicMock()
        mock_client.aio.models.embed_content = AsyncMock(
            return_value=MagicMock(embeddings=[])
        )

        with pytest.raises(RuntimeError, match="empty embeddings"):
            asyncio.run(self._make(mock_client).embed_query("text"))

    def test_strips_surrounding_whitespace(self):
        mock_client = MagicMock()
        mock_client.aio.models.embed_content = AsyncMock(
            return_value=MagicMock(embeddings=[MagicMock(values=[0.5])])
        )

        asyncio.run(self._make(mock_client).embed_query("  hello  "))

        assert mock_client.aio.models.embed_content.call_args.kwargs["contents"] == "hello"

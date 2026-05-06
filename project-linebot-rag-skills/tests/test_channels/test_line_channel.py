"""LineChannel 單元測試。對應 task-23 步驟 3。"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.channels.base import ChannelInput
from app.channels.line import LineChannel


class _Settings:
    line_channel_secret = "test-secret"
    line_channel_access_token = "tok"
    line_api_base = "https://api.line.me"
    line_max_message_chars = 100


class _MessagesRepo:
    def __init__(self, history: str = "user: prev"):
        self._history = history

    async def build_recent_history(self, external_user_id, limit=5):
        return self._history


def test_build_thread_id():
    ch = LineChannel(_Settings(), _MessagesRepo())
    inp = ChannelInput(
        channel="line",
        external_user_id="U_x",
        external_message_id="msg_1",
        raw_text="hi",
    )
    assert ch.build_thread_id(inp) == "line-U_x-msg_1"


def test_format_splits_long_messages():
    """LINE 上限 100 chars（test settings），長文本應被切段。"""
    ch = LineChannel(_Settings(), _MessagesRepo())
    long_text = "a" * 250
    out = ch.format(long_text)
    assert len(out) >= 2
    assert all(len(s) <= 100 for s in out)


@pytest.mark.asyncio
async def test_load_recent_history_delegates_to_repo():
    repo = _MessagesRepo(history="prev exchange")
    ch = LineChannel(_Settings(), repo)
    out = await ch.load_recent_history(external_user_id="U_x")
    assert out == "prev exchange"


@pytest.mark.asyncio
async def test_load_recent_history_returns_default_on_repo_failure():
    class _BrokenRepo:
        async def build_recent_history(self, *a, **k):
            raise RuntimeError("db down")

    ch = LineChannel(_Settings(), _BrokenRepo())
    out = await ch.load_recent_history(external_user_id="U_x")
    assert out == "No recent conversation."


@pytest.mark.asyncio
async def test_push_calls_underlying_client(monkeypatch):
    ch = LineChannel(_Settings(), _MessagesRepo())
    push_mock = AsyncMock()
    monkeypatch.setattr(ch._client, "push_text", push_mock)
    await ch.push(recipient_id="U_x", messages=["hi"])
    push_mock.assert_awaited_once_with("U_x", ["hi"])

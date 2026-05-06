"""StubChannel 單元測試。對應 task-23 步驟 5。"""

from __future__ import annotations

import pytest

from app.channels.base import ChannelInput
from app.channels.stub import StubChannel


def _inp(user_id: str = "u1", msg_id: str = "m1") -> ChannelInput:
    return ChannelInput(
        channel="stub",
        external_user_id=user_id,
        external_message_id=msg_id,
        raw_text="hello",
    )


def test_thread_id_format():
    ch = StubChannel()
    assert ch.build_thread_id(_inp("u1", "m1")) == "stub-u1-m1"


def test_format_does_not_split():
    ch = StubChannel()
    assert ch.format("very long markdown") == ["very long markdown"]


@pytest.mark.asyncio
async def test_push_records_recipient_and_messages():
    ch = StubChannel()
    await ch.push(recipient_id="u1", messages=["hi"])
    await ch.push(recipient_id="u2", messages=["bye", "later"])
    assert ch.pushed == [("u1", ["hi"]), ("u2", ["bye", "later"])]


@pytest.mark.asyncio
async def test_history_returns_empty_string():
    ch = StubChannel()
    assert await ch.load_recent_history(external_user_id="u1") == ""

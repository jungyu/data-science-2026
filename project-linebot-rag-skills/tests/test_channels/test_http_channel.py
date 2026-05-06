"""HttpChannel 單元測試。對應 task-23 步驟 4。"""

from __future__ import annotations

import pytest

from app.channels.base import ChannelInput
from app.channels.http import HttpChannel


def _inp() -> ChannelInput:
    return ChannelInput(
        channel="http",
        external_user_id="user-1",
        external_message_id="sess-abc",
        raw_text="ping",
    )


def test_thread_id_distinct_from_line():
    ch = HttpChannel()
    assert ch.build_thread_id(_inp()).startswith("http-")
    # 與 LINE 命名清楚分離（避免 HITL thread 撞）
    assert "line-" not in ch.build_thread_id(_inp())


def test_format_keeps_full_markdown():
    ch = HttpChannel()
    long_md = "# Title\n" + "段" * 10000  # 超過 LINE 上限
    out = ch.format(long_md)
    assert out == [long_md]
    assert len(out) == 1


@pytest.mark.asyncio
async def test_push_is_no_op():
    ch = HttpChannel()
    # HTTP push 是 no-op；不該 raise
    await ch.push(recipient_id="u1", messages=["whatever"])


@pytest.mark.asyncio
async def test_load_recent_history_default_empty():
    ch = HttpChannel()
    assert await ch.load_recent_history(external_user_id="u1") == "No recent conversation."

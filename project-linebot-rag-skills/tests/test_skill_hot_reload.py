"""spec-08 Skill hot reload 驗收：

1. SkillRegistry.from_supabase 從 ai_skills 表載入合法 row
2. reload_from_supabase 失敗時保留舊 skills（fallback）
3. reload 成功後 lookup 拿到新版 system_prompt
4. malformed row 被 skip，不會炸整個 reload
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

from app.skills.registry import (
    SkillRegistry,
    skill_reload_loop,
)


class _FakeSupabase:
    def __init__(
        self,
        *,
        rows: list[dict[str, Any]] | None = None,
        raises: Exception | None = None,
    ) -> None:
        self._rows = rows or []
        self._raises = raises
        self.select_calls = 0

    async def select(self, table: str, params: dict[str, str]) -> list[dict]:
        self.select_calls += 1
        if self._raises is not None:
            raise self._raises
        assert table == "ai_skills"
        assert params.get("enabled") == "eq.true"
        return self._rows


def _row(skill_id: str, prompt: str) -> dict:
    return {
        "skill_id": skill_id,
        "name": skill_id,
        "description": f"{skill_id} desc",
        "category": "general",
        "system_prompt": prompt,
        "enabled": True,
    }


def _run(coro):
    return asyncio.run(coro)


# ── from_supabase ────────────────────────────────────────────────────────────


def test_from_supabase_loads_enabled_skills():
    client = _FakeSupabase(rows=[
        _row("tech_architect", "你是技術架構師"),
        _row("data_scientist", "你是資料科學家"),
    ])
    reg = _run(SkillRegistry.from_supabase(client))
    assert {s.skill_id for s in reg.list()} == {"tech_architect", "data_scientist"}
    assert reg.require("tech_architect").system_prompt == "你是技術架構師"


def test_from_supabase_raises_when_empty():
    """首次啟動就讀不到 → 明顯失敗，避免靜默退化成空 registry。"""
    client = _FakeSupabase(rows=[])
    with pytest.raises(RuntimeError, match="seed_skills"):
        _run(SkillRegistry.from_supabase(client))


def test_from_supabase_skips_malformed_rows():
    """缺欄位的 row 應被 skip，不該整批失敗。"""
    rows = [
        _row("ok_skill", "valid prompt"),
        {"skill_id": "broken", "name": "broken"},  # missing required fields
    ]
    client = _FakeSupabase(rows=rows)
    reg = _run(SkillRegistry.from_supabase(client))
    assert [s.skill_id for s in reg.list()] == ["ok_skill"]


# ── reload_from_supabase ─────────────────────────────────────────────────────


def test_reload_replaces_in_memory_skills():
    initial = _FakeSupabase(rows=[_row("s1", "v1 prompt")])
    reg = _run(SkillRegistry.from_supabase(initial))
    assert reg.require("s1").system_prompt == "v1 prompt"

    # 第二個 client 模擬 DB 已被改
    updated = _FakeSupabase(rows=[_row("s1", "v2 prompt")])
    ok = _run(reg.reload_from_supabase(updated))
    assert ok is True
    assert reg.require("s1").system_prompt == "v2 prompt"


def test_reload_keeps_old_skills_on_supabase_error(caplog):
    """spec-08 §Fallback：Supabase 拉取失敗保留舊 skills，記 warning。"""
    import logging

    initial = _FakeSupabase(rows=[_row("s1", "v1 prompt")])
    reg = _run(SkillRegistry.from_supabase(initial))

    broken = _FakeSupabase(raises=RuntimeError("supabase down"))
    with caplog.at_level(logging.WARNING):
        ok = _run(reg.reload_from_supabase(broken))
    assert ok is False
    # 舊 skill 還在
    assert reg.require("s1").system_prompt == "v1 prompt"
    assert any("skill reload failed" in rec.message for rec in caplog.records)


def test_reload_keeps_old_when_supabase_returns_empty():
    """DB 暫時清空（migration 中）不該瞬間清空 registry。"""
    initial = _FakeSupabase(rows=[_row("s1", "v1 prompt")])
    reg = _run(SkillRegistry.from_supabase(initial))
    empty = _FakeSupabase(rows=[])
    ok = _run(reg.reload_from_supabase(empty))
    assert ok is False
    assert reg.require("s1") is not None


# ── skill_reload_loop ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_skill_reload_loop_calls_reload_periodically():
    initial = _FakeSupabase(rows=[_row("s1", "v1")])
    reg = await SkillRegistry.from_supabase(initial)

    # 模擬連兩次 reload
    client = _FakeSupabase(rows=[_row("s1", "v2")])
    task = asyncio.create_task(skill_reload_loop(reg, client, interval_seconds=0.01))
    # 等幾個 tick
    await asyncio.sleep(0.05)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    assert client.select_calls >= 1
    assert reg.require("s1").system_prompt == "v2"


@pytest.mark.asyncio
async def test_skill_reload_loop_disabled_when_interval_zero():
    """interval<=0 表停用，loop 立刻 return。"""
    reg = await SkillRegistry.from_supabase(_FakeSupabase(rows=[_row("s1", "x")]))
    client = _FakeSupabase(rows=[_row("s1", "y")])
    # 不會卡住（不 cancel 也能完成）
    await asyncio.wait_for(
        skill_reload_loop(reg, client, interval_seconds=0), timeout=1.0
    )
    assert client.select_calls == 0

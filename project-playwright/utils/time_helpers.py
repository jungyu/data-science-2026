"""UTC 時間字串工具（共用於 worker 與 ch08 腳本）。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone


def now_iso() -> str:
    """UTC 當前時間 ISO 8601 字串。"""
    return datetime.now(timezone.utc).isoformat()


def future_iso(minutes: int) -> str:
    """UTC 當前時間 + N 分鐘的 ISO 8601 字串。"""
    return (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat()

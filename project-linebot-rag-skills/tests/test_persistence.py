"""Checkpointer factory 測試。對應 task-21 步驟 9。"""

from __future__ import annotations

from app.config import Settings
from app.graph.checkpoint import build_checkpointer


def test_memory_backend_returns_saver():
    s = Settings(checkpoint_backend="memory")
    cp = build_checkpointer(s)
    assert cp is not None


def test_none_backend_returns_none():
    s = Settings(checkpoint_backend="none")
    assert build_checkpointer(s) is None


def test_sqlite_backend_returns_none_with_warning(caplog):
    """sqlite 需 async setup；factory 同步路徑回 None 並 log warning。"""
    s = Settings(checkpoint_backend="sqlite")
    import logging

    with caplog.at_level(logging.WARNING):
        cp = build_checkpointer(s)
    assert cp is None
    assert any("async setup" in r.getMessage() for r in caplog.records)


def test_unknown_backend_raises():
    s = Settings(checkpoint_backend="nonsense")
    import pytest

    with pytest.raises(ValueError):
        build_checkpointer(s)

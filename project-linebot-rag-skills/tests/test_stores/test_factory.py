"""build_store factory 測試 — 對應 task-24 §registry。"""

from __future__ import annotations

import pytest

from app.config import Settings
from app.storage.stores import build_store


def test_factory_supports_sqlite_vec(tmp_path):
    s = Settings(
        knowledge_store_backend="sqlite_vec",
        sqlite_vec_path=str(tmp_path / "test.db"),
        sqlite_vec_dim=3,
    )
    store = build_store(s)
    assert store.name == "sqlite_vec"


def test_factory_rejects_unknown():
    s = Settings(knowledge_store_backend="nonsense")
    with pytest.raises(ValueError, match="unknown knowledge_store_backend"):
        build_store(s)

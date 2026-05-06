"""Checkpointer factory — 對應 spec-21 / task-21 步驟 2。

兩種預設 backend：
- `memory`：教學 / 測試用 InMemorySaver；每次 process restart 重置
- `sqlite`：跨 restart 持久化；需 `pip install -e ".[hitl]"` + 在 FastAPI startup
  hook 內 await async setup（本實作提供 build_sqlite_saver_async 給 startup 用）

`none`：不啟用 checkpointer（HITL / persistence 都關閉）。
"""

from __future__ import annotations

import logging
from typing import Any

from app.config import Settings

logger = logging.getLogger(__name__)


def build_checkpointer(settings: Settings) -> Any | None:
    """同步建構：memory / none 立即可用。sqlite 回 None 並提示走 async setup。"""
    backend = settings.checkpoint_backend
    if backend in ("none", ""):
        return None
    if backend == "memory":
        from langgraph.checkpoint.memory import InMemorySaver
        return InMemorySaver()
    if backend == "sqlite":
        logger.warning(
            "checkpoint_backend=sqlite needs async setup; "
            "use build_sqlite_saver_async() in FastAPI startup hook. "
            "Falling back to None for now."
        )
        return None
    raise ValueError(f"unknown checkpoint_backend: {backend!r}")


async def build_sqlite_saver_async(path: str):
    """在 FastAPI startup（async context）建構 AsyncSqliteSaver。

    用法：
        async def startup():
            services = get_runtime_services()
            services.checkpointer = await build_sqlite_saver_async(
                services.settings.checkpoint_sqlite_path
            )
            services.rag_graph = build_rag_graph(services)  # rebuild with checkpointer
    """
    import aiosqlite
    from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
    from pathlib import Path

    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = await aiosqlite.connect(path)
    saver = AsyncSqliteSaver(conn)
    await saver.setup()
    return saver

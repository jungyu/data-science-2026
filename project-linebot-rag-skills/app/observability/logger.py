"""結構化 JSON logging — 對應 spec-22 §「介面契約」`logger.py`。

提供：
- `get_trace_logger()`：拿到名為 "observability" 的 logger（GraphTracer 已用）
- `configure_observability(settings)`：在 FastAPI startup / scripts 入口呼叫一次，
  設好 JSON formatter + log level + LangSmith env hook

`python-json-logger` 為 opt-in dep；未安裝時 fallback 到 stdlib `logging`
的純文字輸出（學生本機可正常運作，CI 接 ELK 才需要 JSON 格式）。
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from typing import Any


def get_trace_logger() -> logging.Logger:
    return logging.getLogger("observability")


class _FallbackJsonFormatter(logging.Formatter):
    """python-json-logger 未安裝時的最小 JSON formatter。

    只輸出常見欄位，不處理 LogRecord.extra 自動展開。
    """

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created))
            + f".{int(record.msecs):03d}Z",
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_observability(settings: Any) -> None:
    """設定 JSON formatter + 對應 log level。

    重複呼叫安全（同一 logger 不會掛多份 handler）。
    `OBSERVABILITY_ENABLED=False` 時直接 return，不影響既有 logging 配置。
    """
    enabled = getattr(settings, "observability_enabled", True)
    if not enabled:
        return

    # LangSmith hook：env 已設則保留，沒設不主動開（屬學生選用）
    if not os.environ.get("LANGCHAIN_TRACING_V2"):
        os.environ.setdefault("LANGCHAIN_TRACING_V2", "false")

    # 選 formatter
    try:
        from pythonjsonlogger import jsonlogger  # type: ignore

        formatter = jsonlogger.JsonFormatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s"
        )
    except ImportError:
        formatter = _FallbackJsonFormatter()

    root = logging.getLogger()
    # 避免重複掛 handler：如果第一個 handler 已是 JSON 格式就跳過
    if not any(
        isinstance(h, logging.StreamHandler)
        and isinstance(getattr(h, "formatter", None), type(formatter))
        for h in root.handlers
    ):
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(formatter)
        root.addHandler(handler)

    level_name = str(getattr(settings, "log_level", "INFO")).upper()
    root.setLevel(getattr(logging, level_name, logging.INFO))
    get_trace_logger().setLevel(root.level)

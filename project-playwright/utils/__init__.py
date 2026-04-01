"""
project-playwright 共用工具模組。

提供瀏覽器管理、日誌記錄和主控台相容等共用功能。
"""

from .browser import BrowserManager
from .console import setup_stdout
from .logger import setup_logger

__all__ = ["BrowserManager", "setup_logger", "setup_stdout"]

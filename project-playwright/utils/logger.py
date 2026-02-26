"""
日誌記錄工具。

提供統一的 logging 設定，支援 console 和檔案輸出。

使用方式：
    from utils.logger import setup_logger

    logger = setup_logger("my_scraper")
    logger.info("開始爬取...")
    logger.error("爬取失敗", exc_info=True)
"""

import logging
import sys
from pathlib import Path

LOG_DIR = Path(__file__).parent.parent / "output" / "logs"


def setup_logger(
    name: str,
    level: int = logging.INFO,
    log_to_file: bool = False,
) -> logging.Logger:
    """建立並設定 logger。

    Args:
        name: Logger 名稱
        level: 日誌等級（預設 INFO）
        log_to_file: 是否同時寫入檔案

    Returns:
        設定好的 Logger 實例
    """
    logger = logging.getLogger(name)

    # 避免重複加入 handler
    if logger.handlers:
        return logger

    logger.setLevel(level)

    # 格式化
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File handler（選用）
    if log_to_file:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(
            LOG_DIR / f"{name}.log",
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger

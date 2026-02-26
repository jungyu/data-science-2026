"""
原子性知識更新的 Context Manager。

來源：第七章 — 原子性更新的 Context Manager
"""

import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)


@contextmanager
def atomic_knowledge_update(vector_db: object, registry: object, transaction_id: str):
    """
    Context manager：確保知識更新的原子性。
    進入時：記錄起始狀態
    退出時：若有例外，自動清理此 transaction 的所有寫入

    類似 Immer 的 produce()，但針對的是向量 DB 的寫入。
    """
    # 記錄此 transaction 開始前的狀態
    snapshot = registry.create_snapshot(transaction_id)

    try:
        yield transaction_id  # 執行攝取操作
        # 成功：提交（不需要做什麼，寫入已在 DB 中）
        registry.commit_snapshot(snapshot)

    except Exception:
        # 失敗：回滾所有此 transaction 的寫入
        logger.warning("攝取失敗，回滾 transaction %s...", transaction_id)

        # 清理向量 DB 中的殘餘 chunks
        deleted = vector_db.delete_by_metadata(
            filter={"transaction_id": transaction_id}
        )
        logger.warning("已清理 %d 個殘餘 chunks", deleted)

        # 恢復 registry 到快照狀態
        registry.restore_snapshot(snapshot)

        raise  # 重新拋出例外

"""
知識庫文件版本模型。

來源：第七章 — 知識版本管理的設計
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal


@dataclass
class KnowledgeDocument:
    """
    知識庫中的文件版本記錄。
    每次攝取都產生新的 version，舊版本不刪除，只改 status。
    """

    doc_id: str              # 唯一文件 ID（UUID）
    source_path: str         # 原始檔案路徑
    version: str             # 語意化版本號，如 "2026.02.15-1"
    namespace: str           # 知識域
    status: Literal[
        "ingesting",         # 攝取中（鎖定狀態）
        "active",            # 當前使用中的版本
        "deprecated",        # 已廢棄（等待清理）
        "archived",          # 已封存（永久保留，不用於查詢）
        "failed",            # 攝取失敗（等待重試）
    ]
    chunk_count: int
    created_at: datetime
    deprecated_at: datetime | None = None
    metadata: dict = field(default_factory=dict)

    @property
    def is_queryable(self) -> bool:
        """只有 active 狀態的文件可以被查詢"""
        return self.status == "active"

    @property
    def should_be_cleaned(self) -> bool:
        """deprecated 且超過 30 天的文件應該被從索引中移除（Constitution Principle V）"""
        if self.status != "deprecated" or not self.deprecated_at:
            return False
        return (datetime.now() - self.deprecated_at).days >= 30

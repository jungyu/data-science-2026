"""
Retrieval Gate：在 LLM 生成答案前，驗證檢索結果的品質。

來源：第五章 — Retrieval Gate：檢索品質的治理閘門
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal


@dataclass
class RetrievalGateResult:
    status: Literal["pass", "block"]
    reason: str | None
    chunks: list[dict]


class RetrievalGate:
    """
    在 LLM 生成答案前，驗證檢索結果的品質。
    這是 RAG 的 Contract-First Gate。
    """

    MIN_CHUNKS = 1            # 至少要有 1 個 chunk
    MIN_SCORE = 0.72          # 向量相似度閾值（低於此值視為不相關）
    MAX_AGE_DAYS = 180        # chunk 來源文件的最大年齡

    def validate(self, query: str, chunks: list[dict]) -> RetrievalGateResult:
        """
        驗證檢索結果是否可以交給 LLM 生成答案。

        Args:
            query: 使用者的問題
            chunks: 向量 DB 返回的 chunks（含相似度分數和 metadata）

        Returns:
            RetrievalGateResult（pass/block + 原因）
        """
        # 規則 1：必須至少有 1 個 chunk
        if len(chunks) < self.MIN_CHUNKS:
            return RetrievalGateResult(
                status="block",
                reason="knowledge_insufficient",
                chunks=[],
            )

        # 規則 2：最高分的 chunk 相似度必須達到閾值
        top_score = max(c["score"] for c in chunks)
        if top_score < self.MIN_SCORE:
            return RetrievalGateResult(
                status="block",
                reason=f"low_relevance (top score: {top_score:.2f} < {self.MIN_SCORE})",
                chunks=[],
            )

        # 規則 3：過濾掉過時的 chunks（Constitution Principle I）
        fresh_chunks = [
            c
            for c in chunks
            if self._is_fresh(c["metadata"].get("last_updated"))
        ]
        if not fresh_chunks:
            return RetrievalGateResult(
                status="block",
                reason="all_chunks_expired",
                chunks=[],
            )

        # 規則 4：過濾掉 deprecated 文件的 chunks
        valid_chunks = [
            c
            for c in fresh_chunks
            if c["metadata"].get("status") != "deprecated"
        ]
        if not valid_chunks:
            return RetrievalGateResult(
                status="block",
                reason="all_chunks_deprecated",
                chunks=[],
            )

        return RetrievalGateResult(status="pass", reason=None, chunks=valid_chunks)

    def _is_fresh(self, last_updated: str | None) -> bool:
        if not last_updated:
            return False
        age = datetime.now() - datetime.fromisoformat(last_updated)
        return age.days <= self.MAX_AGE_DAYS

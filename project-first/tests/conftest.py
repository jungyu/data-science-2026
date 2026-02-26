"""Shared pytest fixtures for enterprise-rag tests."""

import sys
from pathlib import Path

import pytest

# Ensure src/ is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture
def sample_text() -> str:
    """A sample document for chunking tests."""
    return (
        "企業年假政策\n\n"
        "第一條：適用範圍\n"
        "本政策適用於所有正式員工。試用期員工不適用年假規定。\n\n"
        "第二條：年假天數\n"
        "年資滿一年者，每年享有七日年假。年資每增加一年，年假增加一日，"
        "最高以三十日為限。\n\n"
        "第三條：請假程序\n"
        "員工應於休假三日前提出申請，經主管核准後方可休假。"
        "緊急情況得事後補假。\n\n"
        "第四條：未休假處理\n"
        "年度終了未休畢之年假，得遞延至次年度使用，但不得超過十日。"
        "超過部分依日薪折算發給。"
    )


@pytest.fixture
def sample_chunks() -> list[dict]:
    """Pre-chunked sample data for retrieval tests."""
    return [
        {"text": "年資滿一年者，每年享有七日年假。", "score": 0.92, "metadata": {"source": "hr-policy", "chunk_id": 1, "last_updated": "2026-01-15", "status": "active", "doc_id": "hr-leave-policy-2026"}},
        {"text": "員工應於休假三日前提出申請。", "score": 0.85, "metadata": {"source": "hr-policy", "chunk_id": 2, "last_updated": "2026-01-15", "status": "active", "doc_id": "hr-leave-policy-2026"}},
        {"text": "年度終了未休畢之年假，得遞延至次年度使用。", "score": 0.78, "metadata": {"source": "hr-policy", "chunk_id": 3, "last_updated": "2026-01-15", "status": "active", "doc_id": "hr-leave-policy-2026"}},
    ]

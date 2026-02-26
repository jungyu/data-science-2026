"""
檢索品質評測。
這類測試需要真實的向量 DB 和嵌入模型，通常在 CI 的 nightly build 中執行。

來源：第三章 — 評估測試：Retrieval 準確率
"""

import pytest

# 測試集：問題 + 預期應該被檢索到的文件 ID
RETRIEVAL_TEST_CASES = [
    {
        "question": "員工的年假天數是幾天？",
        "expected_doc_ids": ["hr-leave-policy-2026", "hr-benefits-guide"],
        "should_not_contain": ["financial-report-q4"],
    },
    {
        "question": "如何申請報銷差旅費？",
        "expected_doc_ids": ["expense-policy-v2", "reimbursement-guide"],
        "should_not_contain": ["hr-leave-policy-2026"],
    },
]


@pytest.mark.integration
class TestRetrievalQuality:
    """
    檢索品質評測（需要向量 DB 和嵌入模型）。
    執行方式：pytest -m integration tests/evaluation/
    """

    @pytest.fixture(scope="class")
    def retriever(self):
        """需要真實向量 DB 連線。跳過條件：Qdrant 未啟動。"""
        try:
            from qdrant_client import QdrantClient

            client = QdrantClient(host="localhost", port=6333, timeout=5)
            client.get_collections()  # 測試連線
        except Exception:
            pytest.skip("Qdrant 未啟動或無法連線，跳過 integration 測試")

        # 建立一個簡易的 retriever wrapper
        class SimpleRetriever:
            def __init__(self, namespace: str, top_k: int = 5):
                self.namespace = namespace
                self.top_k = top_k

            def search(self, question: str) -> list:
                """
                需要實際的 embedding + 向量搜尋實作。
                TODO: 完成 Ch06 實作後，接入真實的 embedder + vector DB。
                """
                return []  # 空結果 — 測試會因 Hit@5 斷言失敗而非 skip

        return SimpleRetriever(namespace="hr-*", top_k=5)

    @pytest.mark.parametrize("case", RETRIEVAL_TEST_CASES)
    def test_hit_at_5(self, retriever, case):
        """Hit@5：前 5 個結果中至少包含 1 個預期文件"""
        results = retriever.search(case["question"])
        result_ids = [r.doc_id for r in results]

        # 至少有一個預期文件被檢索到
        hit = any(doc_id in result_ids for doc_id in case["expected_doc_ids"])
        assert hit, f"問題「{case['question']}」未能檢索到預期文件"

    @pytest.mark.parametrize("case", RETRIEVAL_TEST_CASES)
    def test_namespace_isolation(self, retriever, case):
        """Namespace 隔離：不應該檢索到其他部門的文件"""
        results = retriever.search(case["question"])
        result_ids = [r.doc_id for r in results]

        for forbidden_id in case["should_not_contain"]:
            assert forbidden_id not in result_ids, (
                f"問題「{case['question']}」不應該檢索到 {forbidden_id}"
            )

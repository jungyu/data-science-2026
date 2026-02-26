"""
完整的 RAG 查詢流水線（含 Retrieval Gate）。

來源：第五章 — 完整的查詢流水線
"""

import logging

from src.retrieval.retrieval_gate import RetrievalGate
from src.query.hallucination_shield import HallucinationShield

logger = logging.getLogger(__name__)


class RAGQueryPipeline:
    """
    完整的 RAG 查詢管線：嵌入 → 搜尋 → Gate 驗證 → LLM 生成 → 幻覺防護 → 日誌。
    """

    def __init__(
        self,
        embedder: object,
        vector_db: object,
        retrieval_gate: RetrievalGate | None = None,
        hallucination_shield: HallucinationShield | None = None,
        audit_logger: object | None = None,
    ) -> None:
        self.embedder = embedder
        self.vector_db = vector_db
        self.retrieval_gate = retrieval_gate or RetrievalGate()
        self.hallucination_shield = hallucination_shield
        self.audit_logger = audit_logger

    def answer(self, question: str, user_namespace: str) -> dict:
        """
        完整的 RAG 查詢流水線：
        1. 嵌入問題
        2. 向量搜尋（限定 namespace）
        3. Retrieval Gate 驗證
        4. LLM 生成（Gate 通過後才執行）
        5. 記錄日誌（Constitution Principle IV）
        """
        # Step 1: 嵌入問題
        query_vector = self.embedder.embed(question)

        # Step 2: 向量搜尋（受 namespace 限制 — Principle III）
        raw_chunks = self.vector_db.search(
            vector=query_vector,
            namespace=user_namespace,
            top_k=10,
        )

        # Step 3: Retrieval Gate
        gate_result = self.retrieval_gate.validate(question, raw_chunks)

        if gate_result.status == "block":
            # Gate 阻擋 → 不調用 LLM，直接回應知識不足
            answer_text = self._knowledge_insufficient_response(gate_result.reason)
            sources: list[str] = []
        else:
            # Gate 通過 → 調用 LLM 生成答案
            answer_text, sources = self._generate_answer(
                question, gate_result.chunks
            )

            # Step 3.5: Hallucination Shield（生成後防護）
            if self.hallucination_shield:
                shield_result = self.hallucination_shield.validate_answer(
                    question, answer_text, gate_result.chunks
                )
                if not shield_result["grounded"]:
                    logger.warning(
                        "HallucinationShield 攔截：score=%.2f, reason=%s",
                        shield_result["reliability_score"],
                        shield_result.get("reason", ""),
                    )
                    answer_text = self._knowledge_insufficient_response(
                        "答案可信度未達標準"
                    )

        # Step 4: 記錄日誌（Constitution Principle IV：不論成功失敗都要記錄）
        if not self.audit_logger:
            logger.warning("audit_logger 未設定，違反 Principle IV 可追溯性要求")
        if self.audit_logger:
            self.audit_logger.log(
                {
                    "question": question,
                    "gate_status": gate_result.status,
                    "chunks_used": [c.get("doc_id", "") for c in gate_result.chunks],
                    "answer_preview": answer_text[:100],
                }
            )

        return {
            "answer": answer_text,
            "sources": sources,
            "gate_status": gate_result.status,
        }

    def _knowledge_insufficient_response(self, reason: str | None) -> str:
        """Gate 阻擋時的標準回覆。"""
        return (
            f"根據現有知識庫無法回答您的問題（原因：{reason}）。"
            "建議聯繫相關部門取得更多資訊。"
        )

    def _generate_answer(
        self, question: str, chunks: list[dict]
    ) -> tuple[str, list[str]]:
        """調用 LLM 生成答案（需要子類實現或注入 LLM client）。"""
        from src.rag.core import rag_answer

        chunk_texts = [c["text"] for c in chunks if "text" in c]
        answer_text = rag_answer(question, chunk_texts)
        sources = [c.get("doc_id", "") for c in chunks]
        return answer_text, sources

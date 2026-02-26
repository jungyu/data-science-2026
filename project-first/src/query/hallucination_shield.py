"""
幻覺防護層：在生成答案後，驗證答案是否有足夠的文件支撐。

來源：第八章 — 幻覺防護層（Hallucination Shield）
"""

import re

from src.utils import cosine_similarity


class HallucinationShield:
    """
    幻覺防護層：在生成答案後，驗證答案是否有足夠的文件支撐。

    核心原則（對應 WFGY 的「零破壞性」）：
    - Shield 永遠不修改 LLM 的原始輸出
    - 只能標記、評分和建議
    - 使用者看到原始答案 + Shield 的可信度評分
    """

    def __init__(self, embedder: object) -> None:
        self.embedder = embedder

    def validate_answer(
        self,
        question: str,
        answer: str,
        source_chunks: list[dict],
    ) -> dict:
        """
        驗證 LLM 的答案是否有文件支撐。

        Returns:
            {
                "answer": str,              # 原始答案（不修改）
                "reliability_score": float,  # 0.0 ~ 1.0
                "grounded": bool,           # 是否有文件支撐
                "warnings": list[str],      # 警告
                "sources": list[str],       # 引用的文件 ID
            }
        """
        # 計算答案與文件的語意相似度
        answer_vector = self.embedder.embed(answer)
        chunk_vectors = [self.embedder.embed(c["text"]) for c in source_chunks]

        max_similarity = max(
            cosine_similarity(answer_vector, cv) for cv in chunk_vectors
        )

        # 檢查答案是否包含文件中未出現的關鍵數字/日期
        ungrounded_claims = self._detect_ungrounded_claims(answer, source_chunks)

        reliability_score = max_similarity * (1.0 - 0.2 * len(ungrounded_claims))
        reliability_score = max(0.0, min(1.0, reliability_score))

        warnings: list[str] = []
        if ungrounded_claims:
            warnings.append(
                f"答案中有 {len(ungrounded_claims)} 個聲明無法在來源文件中找到依據"
            )
        if reliability_score < 0.6:
            warnings.append("答案可信度偏低，建議人工驗證")

        return {
            "answer": answer,  # 絕對不修改原始答案
            "reliability_score": round(reliability_score, 3),
            "grounded": reliability_score >= 0.7,
            "warnings": warnings,
            "sources": [c["doc_id"] for c in source_chunks],
        }

    def _detect_ungrounded_claims(
        self, answer: str, source_chunks: list[dict]
    ) -> list[str]:
        """
        偵測答案中未在來源文件出現的數字和日期。
        """
        # 合併所有來源文字
        source_text = " ".join(c["text"] for c in source_chunks)

        # 擷取答案中的數字和日期
        answer_numbers = set(re.findall(r"\d+(?:\.\d+)?", answer))
        source_numbers = set(re.findall(r"\d+(?:\.\d+)?", source_text))

        # 找出答案中有、但來源文件中沒有的數字
        ungrounded = answer_numbers - source_numbers

        # 過濾掉太短的數字（如 "1", "2" 這類常見數字）
        ungrounded = [n for n in ungrounded if len(n) >= 2]

        return ungrounded

"""
LLM 的硬性設定限制。
這些值來自 Constitution，不允許在 runtime 動態修改。

來源：第八章 — Layer 1：技術層
"""

from src.utils import ConfigViolationError


class LLMConfig:
    """
    LLM 的硬性設定限制。
    這些值來自 Constitution，不允許在 runtime 動態修改。
    (Constitution INV-6、INV-7)
    """

    # 絕對不允許的模型（精簡模型不用於生產環境問答）
    FORBIDDEN_MODELS = frozenset([
        "gpt-4o-mini",
        "gpt-3.5-turbo",
        "gpt-3.5-turbo-16k",
    ])

    # 溫度上限（Constitution Principle II）
    MAX_TEMPERATURE = 0.3

    # 最大輸出 token（防止超長幻覺）
    MAX_TOKENS = 1000

    @classmethod
    def validate(cls, model: str, temperature: float, max_tokens: int = 1000) -> None:
        """硬性驗證：違反規則直接拋出例外，不執行 API 呼叫"""
        if model in cls.FORBIDDEN_MODELS:
            raise ConfigViolationError(
                f"模型 '{model}' 被 Constitution 禁止用於生產環境問答。"
                f"請使用 gpt-4o 或 gpt-4-turbo。"
            )
        if temperature > cls.MAX_TEMPERATURE:
            raise ConfigViolationError(
                f"temperature={temperature} 超過上限 {cls.MAX_TEMPERATURE}。"
                f"（Constitution Principle II：幻覺零容忍）"
            )
        if max_tokens > cls.MAX_TOKENS:
            raise ConfigViolationError(
                f"max_tokens={max_tokens} 超過上限 {cls.MAX_TOKENS}。"
            )

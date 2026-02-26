"""LLMConfig 硬性驗證的單元測試。"""

import pytest

from src.config.llm_config import LLMConfig
from src.utils import ConfigViolationError


class TestLLMConfig:
    def test_valid_config_passes(self):
        """合法設定不拋例外"""
        LLMConfig.validate(model="gpt-4o", temperature=0.1, max_tokens=500)

    def test_forbidden_model_raises(self):
        """被禁止的模型 → ConfigViolationError"""
        with pytest.raises(ConfigViolationError, match="gpt-4o-mini"):
            LLMConfig.validate(model="gpt-4o-mini", temperature=0.1)

    def test_all_forbidden_models(self):
        """驗證所有 forbidden models"""
        for model in LLMConfig.FORBIDDEN_MODELS:
            with pytest.raises(ConfigViolationError):
                LLMConfig.validate(model=model, temperature=0.1)

    def test_temperature_exceeds_max_raises(self):
        """temperature 超過上限 → ConfigViolationError"""
        with pytest.raises(ConfigViolationError, match="temperature"):
            LLMConfig.validate(model="gpt-4o", temperature=0.5)

    def test_temperature_at_boundary_passes(self):
        """temperature 剛好等於上限 → 通過"""
        LLMConfig.validate(model="gpt-4o", temperature=0.3)

    def test_max_tokens_exceeds_limit_raises(self):
        """max_tokens 超過上限 → ConfigViolationError"""
        with pytest.raises(ConfigViolationError, match="max_tokens"):
            LLMConfig.validate(model="gpt-4o", temperature=0.1, max_tokens=2000)

    def test_max_tokens_at_boundary_passes(self):
        """max_tokens 剛好等於上限 → 通過"""
        LLMConfig.validate(model="gpt-4o", temperature=0.1, max_tokens=1000)

    def test_constants_match_chapter_values(self):
        """驗證常數與教材一致"""
        assert LLMConfig.MAX_TEMPERATURE == 0.3
        assert LLMConfig.MAX_TOKENS == 1000
        assert "gpt-4o-mini" in LLMConfig.FORBIDDEN_MODELS
        assert "gpt-3.5-turbo" in LLMConfig.FORBIDDEN_MODELS

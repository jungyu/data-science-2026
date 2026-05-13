"""spec-01 / spec-02 驗收：synthesis prompt 對 response_mode 與 emotion_state
產生明顯不同的指令片段。"""

from __future__ import annotations

import pytest

from app.generator.prompts import (
    _emotion_instruction,
    _mode_instruction,
    render_synthesis_prompt,
)


# ── spec-01 _mode_instruction ────────────────────────────────────────────────

class TestModeInstruction:
    @pytest.mark.parametrize("mode", [
        "brief", "structured", "step_by_step",
        "decision_support", "debugging", "reflection",
    ])
    def test_all_six_modes_have_distinct_text(self, mode: str):
        text = _mode_instruction(mode)
        assert text, f"mode={mode} returned empty instruction"

    def test_each_mode_produces_unique_text(self):
        modes = ["brief", "structured", "step_by_step",
                 "decision_support", "debugging", "reflection"]
        texts = {m: _mode_instruction(m) for m in modes}
        # 6 種 mode 兩兩不同
        assert len(set(texts.values())) == 6

    def test_step_by_step_mentions_完成後確認(self):
        """spec-01 表格明示 step_by_step 結尾必須加「完成後確認：xxx」"""
        assert "完成後確認" in _mode_instruction("step_by_step")

    def test_decision_support_mentions_風險(self):
        assert "風險" in _mode_instruction("decision_support")

    def test_debugging_three_section_structure(self):
        text = _mode_instruction("debugging")
        assert "可能原因" in text
        assert "驗證" in text
        assert "修法" in text

    def test_brief_mentions_句數限制(self):
        assert "3 句" in _mode_instruction("brief") or "三句" in _mode_instruction("brief")

    def test_unknown_mode_falls_back_to_brief(self):
        assert _mode_instruction("unknown_mode") == _mode_instruction("brief")


# ── spec-02 _emotion_instruction ─────────────────────────────────────────────

class TestEmotionInstruction:
    @pytest.mark.parametrize("emotion", [
        "neutral", "curious", "urgent", "confused",
        "frustrated", "anxious", "reflective",
    ])
    def test_all_seven_emotions_have_text(self, emotion: str):
        assert _emotion_instruction(emotion)

    def test_anxious_caps_length_and_actions(self):
        """spec-02 §「驗收標準」：anxious → ≤3 句、只給 1 個行動、有鼓勵句"""
        text = _emotion_instruction("anxious")
        assert "3 句" in text
        assert "1 個" in text
        assert "鼓勵" in text

    def test_frustrated_caps_length_and_no_options(self):
        text = _emotion_instruction("frustrated")
        assert "3 句" in text
        assert "1 個" in text
        assert "不列選項" in text or "不給選項" in text

    def test_urgent_drops_background(self):
        text = _emotion_instruction("urgent")
        assert "省略背景" in text

    def test_unknown_emotion_falls_back_to_neutral(self):
        assert _emotion_instruction("nope") == _emotion_instruction("neutral")


# ── 端到端：render_synthesis_prompt 對不同組合產生不同 prompt ────────────────

class TestRenderSynthesisPrompt:
    def _render(self, mode: str, emotion: str) -> str:
        return render_synthesis_prompt(
            skill_name="x",
            skill_system_prompt="sys",
            user_input="q",
            recent_history="",
            emotion_state=emotion,
            response_mode=mode,
            rag_context="",
        )

    def test_step_by_step_differs_from_brief(self):
        a = self._render("brief", "neutral")
        b = self._render("step_by_step", "neutral")
        assert a != b
        # step_by_step 的 prompt 含「完成後確認」、brief 不含
        assert "完成後確認" in b
        assert "完成後確認" not in a

    def test_anxious_emotion_changes_prompt(self):
        a = self._render("structured", "neutral")
        b = self._render("structured", "anxious")
        assert a != b
        assert "鼓勵" in b
        assert "鼓勵" not in a

    def test_anxious_overlays_mode(self):
        """spec-02 §「與 Response Mode 的優先順序」：anxious + step_by_step
        應同時帶 mode 與 emotion 的關鍵詞。"""
        text = self._render("step_by_step", "anxious")
        assert "完成後確認" in text  # mode 結構保留
        assert "3 句" in text          # emotion 覆寫長度
        assert "1 個" in text          # emotion 覆寫選項數量

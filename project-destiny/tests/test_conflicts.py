from __future__ import annotations

from destiny.conflicts import detect_relations


def _types(rels: list) -> set[str]:
    return {r.type for r in rels}


def test_zi_wu_chong_detected() -> None:
    # 年=子 月=卯 日=午 時=酉 → 子午沖 + 卯酉沖
    rels = detect_relations(["子", "卯", "午", "酉"])
    chong = [r for r in rels if r.type == "沖"]
    assert len(chong) == 2
    assert any(r.impact == "high" for r in chong), "日支涉及的沖應為 high"


def test_liu_he_detected() -> None:
    # 子丑合
    rels = detect_relations(["子", "丑", "寅", "卯"])
    assert "合" in _types(rels)


def test_san_xing_yin_si_shen() -> None:
    rels = detect_relations(["寅", "巳", "申", "子"])
    xings = [r for r in rels if r.type == "刑"]
    assert any(r.impact == "high" for r in xings), "寅巳申三刑應為 high"


def test_zixing() -> None:
    rels = detect_relations(["辰", "辰", "子", "丑"])
    assert any(r.type == "刑" and r.from_ == "辰" and r.to == "辰" for r in rels)


def test_no_false_positive() -> None:
    # 寅卯辰 會東方，無沖
    rels = detect_relations(["寅", "卯", "辰", "巳"])
    assert "沖" not in _types(rels)

"""Bazi Engine smoke tests。

這些案例只驗證排盤管線可跑與關鍵欄位存在，並不主張命理結果的權威正確性。
欄位層面的正確性應以 bazi.evaluation_cases 的黃金資料集在集成測試中驗證。
"""

from __future__ import annotations

from destiny.bazi_engine import compute_chart
from destiny.rule_engine import run_rules


def test_compute_chart_minimal() -> None:
    chart = compute_chart("1990-08-15T14:30:00", "Asia/Taipei")
    assert chart.day_master in "甲乙丙丁戊己庚辛壬癸"
    assert chart.month_commander in "子丑寅卯辰巳午未申酉戌亥"
    assert chart.season in {
        "spring", "summer", "autumn", "winter",
        "late_spring", "late_summer", "late_autumn", "late_winter",
    }
    assert set(chart.four_pillars) == {"year", "month", "day", "hour"}
    assert chart.four_pillars["day"].stem == chart.day_master


def test_true_solar_time_requires_longitude() -> None:
    import pytest
    with pytest.raises(ValueError):
        compute_chart("1990-08-15T14:30:00", "Asia/Taipei", use_true_solar_time=True)


def test_rule_engine_produces_seeds() -> None:
    chart = compute_chart("1990-08-15T14:30:00", "Asia/Taipei")
    out = run_rules(chart)
    assert out.chart_id == chart.chart_id
    assert out.retrieval_query_seeds, "rule engine 必須輸出至少一個檢索種子"
    assert out.strength_assessment.day_master_strength in {
        "very_strong", "strong", "moderately_strong", "neutral",
        "moderately_weak", "weak", "very_weak",
    }

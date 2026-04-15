"""Pydantic models — 對應 schemas/*.schema.json。

這些模型作為模組之間的 typed contract：
- BaziChart    ← Bazi Engine 輸出
- RuleOutput   ← Rule Engine 輸出
- 其他 (Retrieval / Analysis) 目前用 dataclass；若需 API 層嚴格校驗再補。
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

HeavenlyStem = Literal["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
EarthlyBranch = Literal["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
Season = Literal[
    "spring", "summer", "autumn", "winter",
    "late_spring", "late_summer", "late_autumn", "late_winter",
]
TenGod = Literal[
    "比肩", "劫財", "食神", "傷官", "偏財", "正財",
    "七殺", "正官", "偏印", "正印",
]
Strength = Literal[
    "very_strong", "strong", "moderately_strong", "neutral",
    "moderately_weak", "weak", "very_weak",
]
Confidence = Literal["high", "medium", "low"]


class Pillar(BaseModel):
    stem: HeavenlyStem
    branch: EarthlyBranch


class CalculationMeta(BaseModel):
    timezone: str
    solar_term_boundary_used: bool = False
    adjusted_datetime: str | None = None


class BaziChart(BaseModel):
    chart_id: str
    four_pillars: dict[Literal["year", "month", "day", "hour"], Pillar]
    day_master: HeavenlyStem
    hidden_stems: dict[str, list[str]]
    ten_gods: dict[str, str] = Field(default_factory=dict)
    month_commander: EarthlyBranch
    season: Season
    true_solar_time_applied: bool
    calculation_meta: CalculationMeta


class StrengthAssessment(BaseModel):
    day_master_strength: Strength
    supporting_elements: list[str] = Field(default_factory=list)
    draining_elements: list[str] = Field(default_factory=list)
    controlling_elements: list[str] = Field(default_factory=list)
    confidence: Confidence = "medium"


class CandidatePattern(BaseModel):
    pattern: str
    confidence: Confidence
    basis: str | None = None


class SpecialRelation(BaseModel):
    type: Literal["沖", "合", "刑", "害", "破"]
    from_: str = Field(alias="from")
    to: str
    impact: Literal["high", "moderate", "low"] = "moderate"

    model_config = {"populate_by_name": True}


class RuleOutput(BaseModel):
    chart_id: str
    strength_assessment: StrengthAssessment
    candidate_patterns: list[CandidatePattern]
    seasonal_adjustment_needed: list[str] = Field(default_factory=list)
    special_relations: list[SpecialRelation] = Field(default_factory=list)
    risk_flags: list[str] = Field(default_factory=list)
    retrieval_query_seeds: list[str]

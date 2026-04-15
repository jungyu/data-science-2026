"""Rule Engine v0 — 骨架規則（Spec-005）。

僅覆蓋 Phase 0 最小集合：
- 月令生扶日主 → 身強因子（粗略）
- 月令透干十神 → 格局候選
- 日主 + 季節 → 調候需求
- 傷官見官 → 風險旗標
- 產出 retrieval_query_seeds

高階規則（變格、破格修正、身弱逢殺等）留給後續 migration 擴充至 rule_definitions 表。
"""

from __future__ import annotations

from destiny.conflicts import detect_relations
from destiny.models import (
    BaziChart,
    CandidatePattern,
    RuleOutput,
    StrengthAssessment,
)

# 天干五行
_STEM_ELEMENT = {
    "甲": "木", "乙": "木",
    "丙": "火", "丁": "火",
    "戊": "土", "己": "土",
    "庚": "金", "辛": "金",
    "壬": "水", "癸": "水",
}
_STEM_YIN_YANG = {s: ("陽" if i % 2 == 0 else "陰") for i, s in enumerate(_STEM_ELEMENT)}

# 五行生剋
_GENERATES = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
_CONTROLS = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}


def _element_of(stem: str) -> str:
    return _STEM_ELEMENT[stem]


def _ten_god(day_master: str, other_stem: str) -> str:
    """以日主為參照判定另一干的十神。"""
    dm_elem = _element_of(day_master)
    other_elem = _element_of(other_stem)
    same_polarity = _STEM_YIN_YANG[day_master] == _STEM_YIN_YANG[other_stem]

    if other_elem == dm_elem:
        return "比肩" if same_polarity else "劫財"
    if _GENERATES[dm_elem] == other_elem:
        return "食神" if same_polarity else "傷官"
    if _CONTROLS[dm_elem] == other_elem:
        return "偏財" if same_polarity else "正財"
    if _CONTROLS[other_elem] == dm_elem:
        return "七殺" if same_polarity else "正官"
    if _GENERATES[other_elem] == dm_elem:
        return "偏印" if same_polarity else "正印"
    raise ValueError(f"無法判定 {day_master} vs {other_stem} 的十神關係")


def _visible_ten_gods(chart: BaziChart) -> set[str]:
    """命中所有可見天干（四柱 + 藏干）對日主的十神集合。"""
    dm = chart.day_master
    stems: set[str] = set()
    for p in chart.four_pillars.values():
        if p.stem != dm:
            stems.add(p.stem)
    for hidden in chart.hidden_stems.values():
        for s in hidden:
            if s != dm:
                stems.add(s)
    return {_ten_god(dm, s) for s in stems}


def _month_hidden_ten_god(chart: BaziChart) -> list[str]:
    dm = chart.day_master
    month_branch = chart.month_commander
    hidden = chart.hidden_stems.get(month_branch, [])
    return [_ten_god(dm, s) for s in hidden if s != dm]


# 身強/身弱：Phase 0 只用「月令是否生扶日主」做粗略判定
# 日主五行被月支藏干所含或所生 → 得令 → strong；被剋/洩 → weak；否則 neutral
def _assess_strength(chart: BaziChart) -> StrengthAssessment:
    dm_elem = _element_of(chart.day_master)
    month_hidden = chart.hidden_stems.get(chart.month_commander, [])
    month_elements = {_element_of(s) for s in month_hidden}

    supports: list[str] = []
    drains: list[str] = []
    controls: list[str] = []
    score = 0

    for e in month_elements:
        if e == dm_elem:
            supports.append(e); score += 2
        elif _GENERATES[e] == dm_elem:
            supports.append(e); score += 1
        elif _CONTROLS[e] == dm_elem:
            controls.append(e); score -= 2
        elif _GENERATES[dm_elem] == e:
            drains.append(e); score -= 1
        elif _CONTROLS[dm_elem] == e:
            drains.append(e); score -= 1

    if score >= 3:
        strength = "strong"
    elif score >= 1:
        strength = "moderately_strong"
    elif score == 0:
        strength = "neutral"
    elif score >= -2:
        strength = "moderately_weak"
    else:
        strength = "weak"

    return StrengthAssessment(
        day_master_strength=strength,  # type: ignore[arg-type]
        supporting_elements=supports,
        draining_elements=drains,
        controlling_elements=controls,
        confidence="low",  # v0 粗略判定，信心保守
    )


_PATTERN_BY_TEN_GOD = {
    "正官": "正官格", "七殺": "七殺格",
    "正財": "正財格", "偏財": "偏財格",
    "正印": "正印格", "偏印": "偏印格",
    "食神": "食神格", "傷官": "傷官格",
    "比肩": "建祿格", "劫財": "陽刃格",
}


def _candidate_patterns(chart: BaziChart) -> list[CandidatePattern]:
    month_tgs = _month_hidden_ten_god(chart)
    # 月令本氣（第一個藏干）優先
    patterns: list[CandidatePattern] = []
    seen: set[str] = set()
    for idx, tg in enumerate(month_tgs):
        pat = _PATTERN_BY_TEN_GOD.get(tg)
        if pat is None or pat in seen:
            continue
        seen.add(pat)
        conf = "high" if idx == 0 else "medium"
        patterns.append(CandidatePattern(
            pattern=pat,
            confidence=conf,  # type: ignore[arg-type]
            basis=f"月令{chart.month_commander}藏干透{tg}",
        ))
    return patterns


def _seasonal_adjustment(chart: BaziChart) -> list[str]:
    """Phase 0：只覆蓋「冬木需火 / 夏木需水 / 冬火需木火 / 夏火需水」等經典調候。"""
    dm_elem = _element_of(chart.day_master)
    season = chart.season
    is_winter = season in ("winter", "late_winter", "late_autumn")
    is_summer = season in ("summer", "late_summer")

    if dm_elem == "木" and is_winter:
        return ["火"]
    if dm_elem == "木" and is_summer:
        return ["水"]
    if dm_elem == "火" and is_winter:
        return ["木", "火"]
    if dm_elem == "火" and is_summer:
        return ["水"]
    if dm_elem == "金" and is_summer:
        return ["水"]
    if dm_elem == "水" and is_winter:
        return ["火"]
    return []


def _risk_flags(chart: BaziChart, visible: set[str]) -> list[str]:
    flags: list[str] = []
    if "傷官" in visible and "正官" in visible and "正印" not in visible:
        flags.append("傷官見官")
    return flags


def _query_seeds(
    chart: BaziChart,
    patterns: list[CandidatePattern],
    seasonal: list[str],
) -> list[str]:
    dm = chart.day_master
    mb = chart.month_commander
    seeds = [f"{dm}木" if _element_of(dm) == "木" else f"{dm}"]
    seeds = [f"{dm} {mb}月"]
    for p in patterns:
        seeds.append(f"{dm} {mb}月 {p.pattern}")
    if seasonal:
        seeds.append(f"{dm} {chart.season} 調候 {' '.join(seasonal)}")
    return seeds


def run_rules(chart: BaziChart) -> RuleOutput:
    strength = _assess_strength(chart)
    patterns = _candidate_patterns(chart)
    seasonal = _seasonal_adjustment(chart)
    visible = _visible_ten_gods(chart)
    risks = _risk_flags(chart, visible)
    seeds = _query_seeds(chart, patterns, seasonal)

    branches = [chart.four_pillars[k].branch for k in ("year", "month", "day", "hour")]
    relations = detect_relations(branches)

    # 日月沖額外掛風險旗標
    for r in relations:
        if r.type == "沖" and r.impact == "high":
            risks.append(f"日月沖_{r.from_}{r.to}")
        if r.type == "刑" and r.impact == "high":
            risks.append(f"三刑")

    # 若偵測到沖合刑害，加到查詢種子以便召回相關文獻
    for r in relations[:3]:  # 避免 seed 爆炸
        seeds.append(f"{r.from_}{r.to}{r.type}")

    return RuleOutput(
        chart_id=chart.chart_id,
        strength_assessment=strength,
        candidate_patterns=patterns,
        seasonal_adjustment_needed=seasonal,
        special_relations=relations,
        risk_flags=risks,
        retrieval_query_seeds=seeds,
    )

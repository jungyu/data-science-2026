"""地支沖合刑害偵測 — Rule Engine v1 的結構推理補強。

參考子平學派主流定義；破害略去，因實務影響較小且流派分歧大。
輸出配合 models.SpecialRelation，impact 分級依干擾強度粗估。
"""

from __future__ import annotations

from destiny.models import SpecialRelation

# 六沖：對宮相沖
_LIU_CHONG: set[frozenset[str]] = {
    frozenset({"子", "午"}),
    frozenset({"丑", "未"}),
    frozenset({"寅", "申"}),
    frozenset({"卯", "酉"}),
    frozenset({"辰", "戌"}),
    frozenset({"巳", "亥"}),
}

# 六合
_LIU_HE: set[frozenset[str]] = {
    frozenset({"子", "丑"}),
    frozenset({"寅", "亥"}),
    frozenset({"卯", "戌"}),
    frozenset({"辰", "酉"}),
    frozenset({"巳", "申"}),
    frozenset({"午", "未"}),
}

# 三刑 — 僅取最常用的三組
# 寅巳申（無恩之刑）、丑戌未（恃勢之刑）、子卯（無禮之刑）
_SAN_XING_GROUPS: list[set[str]] = [
    {"寅", "巳", "申"},
    {"丑", "戌", "未"},
]
_ZI_MAO_XING: frozenset[str] = frozenset({"子", "卯"})
_ZIXING: set[str] = {"辰", "午", "酉", "亥"}  # 自刑（同支兩見）


def detect_relations(branches: list[str]) -> list[SpecialRelation]:
    """輸入四柱地支 [年, 月, 日, 時]，輸出所有偵測到的沖合刑關係。"""
    relations: list[SpecialRelation] = []
    seen_pairs: set[frozenset[str]] = set()

    # 成對關係：沖 / 合 / 子卯刑
    for i, a in enumerate(branches):
        for b in branches[i + 1:]:
            pair = frozenset({a, b})
            if len(pair) != 2:
                continue
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)

            if pair in _LIU_CHONG:
                # 日月沖影響最大，年時沖影響次之
                impact = "high" if a == branches[2] or b == branches[2] else "moderate"
                relations.append(SpecialRelation(
                    type="沖", **{"from": a}, to=b, impact=impact,  # type: ignore[arg-type]
                ))
            elif pair in _LIU_HE:
                relations.append(SpecialRelation(
                    type="合", **{"from": a}, to=b, impact="moderate",  # type: ignore[arg-type]
                ))
            elif pair == _ZI_MAO_XING:
                relations.append(SpecialRelation(
                    type="刑", **{"from": a}, to=b, impact="moderate",  # type: ignore[arg-type]
                ))

    # 三刑：寅巳申 / 丑戌未，三支齊見
    branch_set = set(branches)
    for group in _SAN_XING_GROUPS:
        if group.issubset(branch_set):
            ordered = [b for b in branches if b in group]
            relations.append(SpecialRelation(
                type="刑", **{"from": ordered[0]}, to="+".join(ordered[1:]),  # type: ignore[arg-type]
                impact="high",
            ))

    # 自刑：同支出現兩次以上
    for zx in _ZIXING:
        if branches.count(zx) >= 2:
            relations.append(SpecialRelation(
                type="刑", **{"from": zx}, to=zx, impact="low",  # type: ignore[arg-type]
            ))

    return relations

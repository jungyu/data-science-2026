"""Bazi Engine — 確定性排盤模組（ADR-003 / Spec-002）。

實作策略：
    包裝 lunar-python（Java 6tail/lunar 的 Python port），它已處理：
    - 公曆 / 農曆 / 節氣邊界
    - 四柱推算（含早晚子時）
    - 藏干
    - 十神（以日主為參照）

本層只做：輸入清洗、欄位對應、schema 化輸出。
不自行換算節氣——若未來需更換實作，只需替換 _compute() 內部。
"""

from __future__ import annotations

import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

from lunar_python import Solar

from destiny.models import BaziChart, CalculationMeta, Pillar

# 月支 → 季節
_BRANCH_TO_SEASON = {
    "寅": "spring", "卯": "spring", "辰": "late_spring",
    "巳": "summer", "午": "summer", "未": "late_summer",
    "申": "autumn", "酉": "autumn", "戌": "late_autumn",
    "亥": "winter", "子": "winter", "丑": "late_winter",
}

# 真太陽時：相對經度 120°E 每度 4 分鐘
_REFERENCE_LONGITUDE = 120.0


def _true_solar_offset_seconds(longitude: float) -> int:
    return int((longitude - _REFERENCE_LONGITUDE) * 4 * 60)


def compute_chart(
    birth_datetime: str,
    timezone: str,
    longitude: float | None = None,
    use_true_solar_time: bool = False,
    chart_id: str | None = None,
) -> BaziChart:
    """排盤主入口。

    Args:
        birth_datetime: ISO 8601，例如 "1990-08-15T14:30:00"
        timezone: IANA tz，例如 "Asia/Taipei"
        longitude: 出生地經度（度），真太陽時用；東經正值，西經負值
        use_true_solar_time: 是否套用真太陽時
        chart_id: 自訂識別碼，省略則自動產生
    """
    tz = ZoneInfo(timezone)
    dt = datetime.fromisoformat(birth_datetime).replace(tzinfo=tz)

    adjusted_dt = dt
    if use_true_solar_time:
        if longitude is None:
            raise ValueError("use_true_solar_time=True 時必須提供 longitude")
        offset = _true_solar_offset_seconds(longitude)
        adjusted_dt = dt.fromtimestamp(dt.timestamp() + offset, tz=tz)

    solar = Solar.fromYmdHms(
        adjusted_dt.year, adjusted_dt.month, adjusted_dt.day,
        adjusted_dt.hour, adjusted_dt.minute, adjusted_dt.second,
    )
    lunar = solar.getLunar()
    eight_char = lunar.getEightChar()

    pillars = {
        "year":  Pillar(stem=eight_char.getYearGan(),  branch=eight_char.getYearZhi()),
        "month": Pillar(stem=eight_char.getMonthGan(), branch=eight_char.getMonthZhi()),
        "day":   Pillar(stem=eight_char.getDayGan(),   branch=eight_char.getDayZhi()),
        "hour":  Pillar(stem=eight_char.getTimeGan(),  branch=eight_char.getTimeZhi()),
    }

    hidden_stems = {
        pillars["year"].branch:  list(eight_char.getYearHideGan()),
        pillars["month"].branch: list(eight_char.getMonthHideGan()),
        pillars["day"].branch:   list(eight_char.getDayHideGan()),
        pillars["hour"].branch:  list(eight_char.getTimeHideGan()),
    }

    day_master = pillars["day"].stem
    month_branch = pillars["month"].branch

    return BaziChart(
        chart_id=chart_id or f"chart_{uuid.uuid4().hex[:12]}",
        four_pillars=pillars,
        day_master=day_master,
        hidden_stems=hidden_stems,
        ten_gods={},  # 可選：lunar-python 也可回傳十神，初版先留空由 Rule Engine 視需要補
        month_commander=month_branch,
        season=_BRANCH_TO_SEASON[month_branch],
        true_solar_time_applied=use_true_solar_time,
        calculation_meta=CalculationMeta(
            timezone=timezone,
            solar_term_boundary_used=True,
            adjusted_datetime=adjusted_dt.isoformat() if use_true_solar_time else None,
        ),
    )

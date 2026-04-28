from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Any


WEEKDAYS = {
    "一": 0,
    "1": 0,
    "二": 1,
    "2": 1,
    "三": 2,
    "3": 2,
    "四": 3,
    "4": 3,
    "五": 4,
    "5": 4,
    "六": 5,
    "6": 5,
    "日": 6,
    "天": 6,
    "7": 6,
}


def validate_recurrence(kind: str, recurrence: Any) -> list[str]:
    errors: list[str] = []
    if kind != "daily":
        return errors
    if not isinstance(recurrence, dict):
        return ["daily task must have recurrence metadata"]
    if recurrence.get("freq") != "daily":
        errors.append("daily recurrence.freq must be daily")
    value = recurrence.get("time")
    if not isinstance(value, str) or not re.fullmatch(r"[0-2]\d:[0-5]\d", value):
        errors.append("daily recurrence.time must be HH:MM")
    elif int(value[:2]) > 23:
        errors.append("daily recurrence.time hour must be 00-23")
    return errors


def parse_due_text(text: str, base: date | None = None) -> str | None:
    base = base or date.today()
    match = re.search(r"(20\d{2})[-/.年](\d{1,2})[-/.月](\d{1,2})日?", text)
    if match:
        return safe_date(int(match.group(1)), int(match.group(2)), int(match.group(3)))

    if "五一" in text:
        parsed = date(base.year, 5, 1)
        if parsed < base:
            parsed = date(base.year + 1, 5, 1)
        return parsed.isoformat()

    match = re.search(r"(\d{1,2})月(\d{1,2})[日号]?", text)
    if match:
        parsed = safe_date(base.year, int(match.group(1)), int(match.group(2)))
        if parsed and date.fromisoformat(parsed) < base:
            parsed = safe_date(base.year + 1, int(match.group(1)), int(match.group(2)))
        return parsed

    if "后天" in text:
        return (base + timedelta(days=2)).isoformat()
    if "明天" in text:
        return (base + timedelta(days=1)).isoformat()
    if "今天" in text:
        return base.isoformat()

    match = re.search(r"(本周|这周|下周)([一二三四五六日天1-7])", text)
    if match:
        target = WEEKDAYS[match.group(2)]
        if match.group(1) == "下周":
            monday = base + timedelta(days=7 - base.weekday())
            return (monday + timedelta(days=target)).isoformat()
        return (base + timedelta(days=(target - base.weekday()) % 7)).isoformat()

    match = re.search(r"(?:周|星期)([一二三四五六日天1-7])", text)
    if match:
        target = WEEKDAYS[match.group(1)]
        return (base + timedelta(days=(target - base.weekday()) % 7)).isoformat()

    return None


def parse_daily_time(text: str) -> str:
    match = re.search(r"([01]?\d|2[0-3]):([0-5]\d)", text)
    if match:
        return f"{int(match.group(1)):02d}:{match.group(2)}"

    match = re.search(r"(上午|早上|中午|下午|晚上)?\s*([0-9一二三四五六七八九十]{1,3})\s*点(?:半)?", text)
    if not match:
        return "21:00"
    hour = parse_small_number(match.group(2))
    period = match.group(1) or ""
    if period in {"下午", "晚上"} and hour < 12:
        hour += 12
    if period == "中午" and hour < 11:
        hour += 12
    minute = "30" if "点半" in match.group(0) else "00"
    return f"{hour % 24:02d}:{minute}"


def parse_small_number(value: str) -> int:
    if value.isdigit():
        return int(value)
    table = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
    if value in table:
        return table[value]
    if value.startswith("十"):
        return 10 + table.get(value[1:], 0)
    if "十" in value:
        left, _, right = value.partition("十")
        return table.get(left, 1) * 10 + table.get(right, 0)
    return 21


def safe_date(year: int, month: int, day: int) -> str | None:
    try:
        return date(year, month, day).isoformat()
    except ValueError:
        return None

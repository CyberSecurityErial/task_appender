from __future__ import annotations

import re
from typing import Any

from .errors import TaskError


RULE_RE = re.compile(r"([0-9]+)d@([0-2][0-9]:[0-5][0-9])\Z")
TIME_RE = re.compile(r"([01][0-9]|2[0-3]):[0-5][0-9]\Z")


def parse_reminder_rule(value: str) -> dict[str, Any]:
    match = RULE_RE.fullmatch(value.strip())
    if not match or int(match.group(1)) > 3650 or not TIME_RE.fullmatch(match.group(2)):
        raise TaskError(f"invalid reminder rule, expected Nd@HH:MM: {value}")
    return {"days_before": int(match.group(1)), "time": match.group(2)}


def normalize_reminders(value: Any) -> Any:
    if value is None:
        return []
    if not isinstance(value, list):
        return value
    result: list[Any] = []
    for rule in value:
        if isinstance(rule, dict):
            result.append(
                {
                    "days_before": rule.get("days_before"),
                    "time": str(rule.get("time", "")).strip(),
                }
            )
        else:
            result.append(rule)
    return result


def validate_reminders(kind: str, due_at: Any, reminders: Any) -> list[str]:
    if reminders is None:
        reminders = []
    if not isinstance(reminders, list):
        return ["reminders must be a list"]
    if kind == "daily" and reminders:
        return ["daily task reminders must be empty"]
    if reminders and not due_at:
        return ["reminders requires due_at"]

    errors: list[str] = []
    seen: set[tuple[int, str]] = set()
    for index, rule in enumerate(reminders):
        if not isinstance(rule, dict):
            errors.append(f"reminders[{index}] must be a mapping")
            continue
        days = rule.get("days_before")
        time_value = rule.get("time")
        if type(days) is not int or not 0 <= days <= 3650:
            errors.append(
                f"reminders[{index}].days_before must be an integer from 0 to 3650"
            )
        if not isinstance(time_value, str) or not TIME_RE.fullmatch(time_value):
            errors.append(f"reminders[{index}].time must be HH:MM")
        if type(days) is int and isinstance(time_value, str):
            key = (days, time_value)
            if key in seen:
                errors.append(f"reminders[{index}] duplicate reminder rule")
            seen.add(key)
    return errors


def format_reminders(reminders: Any) -> str:
    if not isinstance(reminders, list) or not reminders:
        return "-"
    labels: list[str] = []
    for rule in reminders:
        days = int(rule["days_before"])
        prefix = "当天" if days == 0 else f"提前 {days} 天"
        labels.append(f"{prefix} {rule['time']}")
    return "；".join(labels)

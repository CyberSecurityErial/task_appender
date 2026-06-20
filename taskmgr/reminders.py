from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, tzinfo
from pathlib import Path
from typing import Any, Iterator
from zoneinfo import ZoneInfo

from .errors import TaskError
from .graph import validate_data
from .settings import load_ledger, load_settings, save_ledger
from .store import load_data, normalize_for_save


ACTIVE_STATUSES = {"todo", "doing", "blocked"}
RETRY_MINUTES = (1, 5, 15, 30)
LEDGER_RETENTION_DAYS = 90


@dataclass(frozen=True)
class ReminderOccurrence:
    key: str
    task_id: str
    title: str
    scheduled_at: datetime
    message: str


def delivery_key(task_id: str, family: str, scheduled_at: datetime, rule: str) -> str:
    raw = f"{task_id}|{family}|{scheduled_at.isoformat()}|{rule}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def build_occurrences(
    tasks: list[dict[str, Any]],
    now: datetime,
    settings: dict[str, Any],
) -> list[ReminderOccurrence]:
    timezone = ZoneInfo(str(settings["timezone"]))
    local_now = _as_timezone(now, timezone)
    grace = timedelta(minutes=int(settings["missed_grace_minutes"]))
    window_start = local_now - grace
    events: list[ReminderOccurrence] = []

    for task in tasks:
        if task.get("status") not in ACTIVE_STATUSES:
            continue
        if task.get("kind") == "daily":
            recurrence = task.get("recurrence")
            if (
                not isinstance(recurrence, dict)
                or recurrence.get("freq") != "daily"
                or not recurrence.get("time")
            ):
                continue
            for scheduled_date in _dates_between(window_start.date(), local_now.date()):
                scheduled_at = _scheduled_datetime(
                    scheduled_date, str(recurrence["time"]), timezone
                )
                if window_start <= scheduled_at <= local_now:
                    events.append(
                        _occurrence(
                            task,
                            "daily",
                            scheduled_at,
                            str(recurrence["time"]),
                            f"{task['title']} — 每日 {recurrence['time']}",
                        )
                    )
            continue

        due_value = task.get("due_at")
        reminders = task.get("reminders")
        if not due_value or not isinstance(reminders, list):
            continue
        due_date = date.fromisoformat(str(due_value))
        for rule in reminders:
            days_before = int(rule["days_before"])
            time_value = str(rule["time"])
            scheduled_date = due_date - timedelta(days=days_before)
            scheduled_at = _scheduled_datetime(scheduled_date, time_value, timezone)
            if not window_start <= scheduled_at <= local_now:
                continue
            timing = (
                f"当天 {time_value}"
                if days_before == 0
                else f"提前 {days_before} 天 {time_value}"
            )
            events.append(
                _occurrence(
                    task,
                    "due",
                    scheduled_at,
                    f"{due_date.isoformat()}|{days_before}d@{time_value}",
                    f"{task['title']} — 截止 {due_date.isoformat()}（{timing}）",
                )
            )

    return sorted(events, key=lambda event: (event.scheduled_at, event.task_id, event.key))


def run_reminder_scan(
    db_path: Path,
    *,
    now: datetime | None = None,
    notifier: Any | None = None,
) -> dict[str, int]:
    db_path = Path(db_path).expanduser()
    settings = load_settings(db_path)
    result = {"sent": 0, "failed": 0, "skipped": 0}
    if not settings["enabled"]:
        return result

    timezone = ZoneInfo(settings["timezone"])
    local_now = _as_timezone(now or datetime.now(timezone), timezone)
    data = load_data(db_path)
    normalize_for_save(data)
    validation = validate_data(data)
    if validation.errors:
        raise TaskError("; ".join(validation.errors))

    if notifier is None:
        from .notifier import NativeNotifier

        notifier = NativeNotifier()

    ledger = load_ledger(db_path)
    events_state = ledger["events"]
    changed = _prune_ledger(events_state, local_now)
    occurrences = build_occurrences(data.get("tasks", []), local_now, settings)

    for occurrence in occurrences:
        record = events_state.get(occurrence.key, {})
        if record.get("delivered_at"):
            result["skipped"] += 1
            continue
        next_retry = _parse_timestamp(record.get("next_retry_at"), timezone)
        if next_retry and next_retry > local_now:
            result["skipped"] += 1
            continue

        try:
            notifier.send(
                f"任务提醒 · {occurrence.task_id}",
                occurrence.message,
                settings["default_sound"],
            )
        except Exception as exc:
            failure_count = int(record.get("failure_count", 0)) + 1
            delay = RETRY_MINUTES[min(failure_count - 1, len(RETRY_MINUTES) - 1)]
            events_state[occurrence.key] = {
                "scheduled_at": occurrence.scheduled_at.isoformat(),
                "failure_count": failure_count,
                "next_retry_at": (local_now + timedelta(minutes=delay)).isoformat(),
                "last_error": str(exc),
                "updated_at": local_now.isoformat(),
            }
            result["failed"] += 1
            changed = True
            continue

        events_state[occurrence.key] = {
            "scheduled_at": occurrence.scheduled_at.isoformat(),
            "delivered_at": local_now.isoformat(),
            "updated_at": local_now.isoformat(),
        }
        result["sent"] += 1
        changed = True

    if changed:
        save_ledger(db_path, ledger)
    return result


def _occurrence(
    task: dict[str, Any],
    family: str,
    scheduled_at: datetime,
    rule: str,
    message: str,
) -> ReminderOccurrence:
    task_id = str(task["id"])
    return ReminderOccurrence(
        key=delivery_key(task_id, family, scheduled_at, rule),
        task_id=task_id,
        title=str(task["title"]),
        scheduled_at=scheduled_at,
        message=message,
    )


def _scheduled_datetime(
    scheduled_date: date, time_value: str, timezone: ZoneInfo
) -> datetime:
    return datetime.combine(scheduled_date, time.fromisoformat(time_value), tzinfo=timezone)


def _as_timezone(value: datetime, timezone: tzinfo) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone)
    return value.astimezone(timezone)


def _dates_between(start: date, end: date) -> Iterator[date]:
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def _prune_ledger(events: dict[str, Any], now: datetime) -> bool:
    cutoff = now - timedelta(days=LEDGER_RETENTION_DAYS)
    stale: list[str] = []
    for key, record in events.items():
        if not isinstance(record, dict):
            stale.append(key)
            continue
        timestamp = (
            record.get("updated_at")
            or record.get("delivered_at")
            or record.get("scheduled_at")
        )
        if not timestamp:
            stale.append(key)
            continue
        parsed = _parse_timestamp(timestamp, now.tzinfo)
        if parsed is None:
            stale.append(key)
            continue
        if parsed < cutoff:
            stale.append(key)
    for key in stale:
        del events[key]
    return bool(stale)


def _parse_timestamp(value: Any, timezone: tzinfo) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return _as_timezone(datetime.fromisoformat(value), timezone)
    except ValueError:
        return None

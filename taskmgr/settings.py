from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import yaml

from .errors import TaskError


DEFAULT_SETTINGS: dict[str, Any] = {
    "enabled": False,
    "timezone": "Asia/Shanghai",
    "default_sound": "Glass",
    "missed_grace_minutes": 120,
    "check_interval_seconds": 60,
}


def settings_path_for_db(db_path: Path) -> Path:
    return Path(db_path).expanduser().with_name("settings.yaml")


def state_path_for_db(db_path: Path) -> Path:
    return Path(db_path).expanduser().with_name("reminder_state.json")


def load_settings(db_path: Path) -> dict[str, Any]:
    path = settings_path_for_db(db_path)
    if not path.exists():
        return dict(DEFAULT_SETTINGS)
    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise TaskError(f"settings YAML parse failed: {path}: {exc}") from exc
    if not isinstance(loaded, dict):
        raise TaskError("settings must be a mapping")
    source = loaded.get("notifications", loaded)
    if not isinstance(source, dict):
        raise TaskError("notifications settings must be a mapping")
    return normalize_settings(source)


def save_settings(db_path: Path, values: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(values, dict):
        raise TaskError("notifications settings must be a mapping")
    normalized = normalize_settings(values)
    path = settings_path_for_db(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"version": 1, "notifications": normalized}
    text = yaml.safe_dump(payload, allow_unicode=True, sort_keys=False)
    _atomic_write_text(path, text)
    return normalized


def normalize_settings(values: dict[str, Any]) -> dict[str, Any]:
    result = dict(DEFAULT_SETTINGS)
    for key in DEFAULT_SETTINGS:
        if key in values:
            result[key] = values[key]
    validate_settings(result)
    return result


def validate_settings(settings: dict[str, Any]) -> None:
    if type(settings.get("enabled")) is not bool:
        raise TaskError("notifications.enabled must be boolean")

    timezone = settings.get("timezone")
    if not isinstance(timezone, str) or not timezone.strip():
        raise TaskError("notifications.timezone must be an IANA timezone")
    try:
        ZoneInfo(timezone)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise TaskError(f"notifications.timezone is invalid: {timezone}") from exc

    if not isinstance(settings.get("default_sound"), str):
        raise TaskError("notifications.default_sound must be a string")

    grace = settings.get("missed_grace_minutes")
    if type(grace) is not int or not 0 <= grace <= 1440:
        raise TaskError("notifications.missed_grace_minutes must be an integer from 0 to 1440")

    interval = settings.get("check_interval_seconds")
    if type(interval) is not int or not 15 <= interval <= 3600:
        raise TaskError("notifications.check_interval_seconds must be an integer from 15 to 3600")


def load_ledger(db_path: Path) -> dict[str, Any]:
    path = state_path_for_db(db_path)
    if not path.exists():
        return {"version": 1, "events": {}}
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise TaskError(f"reminder state JSON parse failed: {path}: {exc}") from exc
    if not isinstance(loaded, dict) or not isinstance(loaded.get("events"), dict):
        raise TaskError("reminder state must contain an events mapping")
    return {"version": 1, "events": loaded["events"]}


def save_ledger(db_path: Path, ledger: dict[str, Any]) -> dict[str, Any]:
    events = ledger.get("events") if isinstance(ledger, dict) else None
    if not isinstance(events, dict):
        raise TaskError("reminder state must contain an events mapping")
    normalized = {"version": 1, "events": events}
    path = state_path_for_db(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write_text(path, json.dumps(normalized, ensure_ascii=False, indent=2) + "\n")
    return normalized


def _atomic_write_text(path: Path, content: str) -> None:
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(content, encoding="utf-8")
    tmp_path.replace(path)

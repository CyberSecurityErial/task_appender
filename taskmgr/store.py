from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from .model import Task, TaskError, dedupe


APP_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATA_PATH = APP_ROOT / "data" / "tasks.yaml"
STORE_VERSION = 1


def empty_data() -> dict[str, Any]:
    return {"version": STORE_VERSION, "next_id": 1, "tasks": []}


def load_data(path: Path | str = DEFAULT_DATA_PATH) -> dict[str, Any]:
    db_path = Path(path)
    if not db_path.exists():
        return empty_data()
    try:
        loaded = yaml.safe_load(db_path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise TaskError(f"YAML parse failed: {db_path}: {exc}") from exc
    if loaded is None:
        return empty_data()
    if not isinstance(loaded, dict):
        raise TaskError(f"Task store must be a mapping: {db_path}")
    loaded.setdefault("version", STORE_VERSION)
    loaded.setdefault("next_id", 1)
    loaded.setdefault("tasks", [])
    if not isinstance(loaded["tasks"], list):
        raise TaskError("tasks must be a list")
    return loaded


def save_data(data: dict[str, Any], path: Path | str = DEFAULT_DATA_PATH) -> None:
    db_path = Path(path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    data["tasks"] = sorted(data.get("tasks", []), key=lambda task: str(task.get("id", "")))
    payload = yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=1000)
    tmp_path = db_path.with_suffix(db_path.suffix + ".tmp")
    tmp_path.write_text(payload, encoding="utf-8")
    tmp_path.replace(db_path)


def tasks_by_id(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(task.get("id")): task for task in data.get("tasks", []) if isinstance(task, dict)}


def normalize_for_save(data: dict[str, Any]) -> None:
    normalized: list[dict[str, Any]] = []
    for raw in data.get("tasks", []):
        if not isinstance(raw, dict):
            continue
        normalized.append(Task.from_dict(raw).to_dict())
    data["tasks"] = normalized
    rebuild_children(data)
    data["next_id"] = max(int(data.get("next_id", 1)), max_existing_numeric_id(data) + 1)


def rebuild_children(data: dict[str, Any]) -> None:
    index = tasks_by_id(data)
    for task in index.values():
        task["children"] = []
    for task in index.values():
        parent = task.get("parent")
        if parent and parent in index:
            index[parent]["children"] = dedupe(index[parent].get("children", []) + [task["id"]])


def allocate_id(data: dict[str, Any]) -> str:
    next_id = max(int(data.get("next_id", 1)), max_existing_numeric_id(data) + 1)
    while True:
        task_id = f"T-{next_id:04d}"
        next_id += 1
        if task_id not in tasks_by_id(data):
            data["next_id"] = next_id
            return task_id


def max_existing_numeric_id(data: dict[str, Any]) -> int:
    max_seen = 0
    for task_id in tasks_by_id(data):
        match = re.fullmatch(r"T-(\d+)", task_id)
        if match:
            max_seen = max(max_seen, int(match.group(1)))
    return max_seen


def resolve_task(data: dict[str, Any], ref: str | None) -> str:
    if not ref:
        raise TaskError("task reference is empty")
    text = ref.strip()
    index = tasks_by_id(data)
    if text in index:
        return text
    lowered = text.lower()
    exact = [task_id for task_id, task in index.items() if str(task.get("title", "")).lower() == lowered]
    if len(exact) == 1:
        return exact[0]
    fuzzy = [
        task_id
        for task_id, task in index.items()
        if lowered in str(task.get("title", "")).lower() or str(task.get("title", "")).lower() in lowered
    ]
    if len(fuzzy) == 1:
        return fuzzy[0]
    if len(fuzzy) > 1:
        choices = ", ".join(f"{task_id}:{index[task_id].get('title', '')}" for task_id in fuzzy[:8])
        raise TaskError(f"task reference is ambiguous, use id: {choices}")
    raise TaskError(f"task not found: {ref}")


def find_title(data: dict[str, Any], title: str) -> str | None:
    lowered = title.strip().lower()
    for task_id, task in tasks_by_id(data).items():
        if str(task.get("title", "")).strip().lower() == lowered:
            return task_id
    return None

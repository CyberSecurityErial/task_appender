from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from .model import VALID_KINDS, VALID_STATUSES
from .recurrence import validate_recurrence


@dataclass
class ValidationResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def validate_data(data: dict[str, Any]) -> ValidationResult:
    result = ValidationResult()
    raw_tasks = data.get("tasks")
    if not isinstance(raw_tasks, list):
        result.errors.append("tasks must be a list")
        return result

    seen: set[str] = set()
    tasks: dict[str, dict[str, Any]] = {}
    for index, task in enumerate(raw_tasks):
        if not isinstance(task, dict):
            result.errors.append(f"task[{index}] must be a mapping")
            continue
        task_id = str(task.get("id", "")).strip()
        if not task_id:
            result.errors.append(f"task[{index}] missing required field: id")
            continue
        if task_id in seen:
            result.errors.append(f"duplicate task id: {task_id}")
        seen.add(task_id)
        tasks[task_id] = task

        for field_name in ("title", "kind", "status", "created_at"):
            if not str(task.get(field_name, "")).strip():
                result.errors.append(f"{task_id} missing required field: {field_name}")
        if task.get("kind") not in VALID_KINDS:
            result.errors.append(f"{task_id} invalid kind: {task.get('kind')}")
        if task.get("status") not in VALID_STATUSES:
            result.errors.append(f"{task_id} invalid status: {task.get('status')}")
        validate_date_field(result, task_id, "created_at", task.get("created_at"), required=True)
        validate_date_field(result, task_id, "due_at", task.get("due_at"), required=False)
        validate_date_field(result, task_id, "completed_at", task.get("completed_at"), required=False)
        if task.get("completed_at") and task.get("status") not in {"done", "archived"}:
            result.warnings.append(f"{task_id} completed_at is set but status is {task.get('status')}")
        if not isinstance(task.get("priority"), int) or not 1 <= task.get("priority") <= 5:
            result.errors.append(f"{task_id} priority must be an integer from 1 to 5")
        if not isinstance(task.get("tags"), list):
            result.errors.append(f"{task_id} tags must be a list")
        if not isinstance(task.get("depends_on"), list):
            result.errors.append(f"{task_id} depends_on must be a list")
        if not isinstance(task.get("children"), list):
            result.errors.append(f"{task_id} children must be a list")
        for error in validate_recurrence(str(task.get("kind")), task.get("recurrence")):
            result.errors.append(f"{task_id} {error}")
        if task.get("kind") == "short" and not task.get("due_at"):
            result.warnings.append(f"{task_id} short task has no due_at")

    for task_id, task in tasks.items():
        parent = task.get("parent")
        if parent:
            if parent not in tasks:
                result.errors.append(f"{task_id} parent does not exist: {parent}")
            elif parent == task_id:
                result.errors.append(f"{task_id} cannot be its own parent")
            elif task_id not in tasks[parent].get("children", []):
                result.errors.append(f"{task_id} parent {parent} does not list it as child")

        for child_id in task.get("children", []):
            if child_id not in tasks:
                result.errors.append(f"{task_id} child does not exist: {child_id}")
            elif tasks[child_id].get("parent") != task_id:
                result.errors.append(f"{task_id} child {child_id} has parent {tasks[child_id].get('parent')}")

        for dependency in task.get("depends_on", []):
            if dependency not in tasks:
                result.errors.append(f"{task_id} dependency does not exist: {dependency}")
            elif dependency == task_id:
                result.errors.append(f"{task_id} cannot depend on itself")

    dependency_cycle = find_cycle({task_id: list(task.get("depends_on", [])) for task_id, task in tasks.items()})
    if dependency_cycle:
        result.errors.append("dependency cycle: " + " -> ".join(dependency_cycle))

    parent_cycle = find_cycle({task_id: [task.get("parent")] if task.get("parent") else [] for task_id, task in tasks.items()})
    if parent_cycle:
        result.errors.append("parent cycle: " + " -> ".join(parent_cycle))

    return result


def validate_date_field(
    result: ValidationResult, task_id: str, field_name: str, value: Any, *, required: bool
) -> None:
    if value in (None, ""):
        if required:
            result.errors.append(f"{task_id} {field_name} is required")
        return
    try:
        date.fromisoformat(str(value))
    except ValueError:
        result.errors.append(f"{task_id} {field_name} must be YYYY-MM-DD")


def find_cycle(adjacency: dict[str, list[str]]) -> list[str]:
    visiting: set[str] = set()
    visited: set[str] = set()
    path: list[str] = []

    def visit(node: str) -> list[str]:
        if node in visiting:
            start = path.index(node)
            return path[start:] + [node]
        if node in visited:
            return []
        visiting.add(node)
        path.append(node)
        for nxt in adjacency.get(node, []):
            if nxt not in adjacency:
                continue
            cycle = visit(nxt)
            if cycle:
                return cycle
        path.pop()
        visiting.remove(node)
        visited.add(node)
        return []

    for node in adjacency:
        cycle = visit(node)
        if cycle:
            return cycle
    return []

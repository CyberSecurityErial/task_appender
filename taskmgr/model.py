from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any


VALID_KINDS = {"short", "long", "daily", "milestone"}
VALID_STATUSES = {"todo", "doing", "blocked", "done", "archived"}
DEFAULT_KIND = "short"
DEFAULT_STATUS = "todo"


class TaskError(Exception):
    """Raised for invalid task graph operations."""


def today_iso() -> str:
    return date.today().isoformat()


def dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        result.append(value)
    return result


@dataclass
class Task:
    id: str
    title: str
    kind: str = DEFAULT_KIND
    status: str = DEFAULT_STATUS
    created_at: str = field(default_factory=today_iso)
    due_at: str | None = None
    priority: int = 3
    tags: list[str] = field(default_factory=list)
    parent: str | None = None
    depends_on: list[str] = field(default_factory=list)
    children: list[str] = field(default_factory=list)
    recurrence: dict[str, Any] | None = None
    notes: str = ""

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Task":
        return cls(
            id=str(raw.get("id", "")).strip(),
            title=str(raw.get("title", "")).strip(),
            kind=str(raw.get("kind", DEFAULT_KIND)).strip(),
            status=str(raw.get("status", DEFAULT_STATUS)).strip(),
            created_at=str(raw.get("created_at", today_iso())).strip(),
            due_at=none_if_empty(raw.get("due_at")),
            priority=int(raw.get("priority", 3)),
            tags=dedupe([str(tag).strip() for tag in raw.get("tags", []) if str(tag).strip()]),
            parent=none_if_empty(raw.get("parent")),
            depends_on=dedupe([str(ref).strip() for ref in raw.get("depends_on", []) if str(ref).strip()]),
            children=dedupe([str(ref).strip() for ref in raw.get("children", []) if str(ref).strip()]),
            recurrence=raw.get("recurrence"),
            notes=str(raw.get("notes", "")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "kind": self.kind,
            "status": self.status,
            "created_at": self.created_at,
            "due_at": self.due_at,
            "priority": self.priority,
            "tags": list(self.tags),
            "parent": self.parent,
            "depends_on": list(self.depends_on),
            "children": list(self.children),
            "recurrence": self.recurrence,
            "notes": self.notes,
        }


def none_if_empty(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def task_sort_key(task: dict[str, Any]) -> tuple[int, str, str]:
    status_order = {"doing": 0, "blocked": 1, "todo": 2, "done": 3, "archived": 4}
    due = str(task.get("due_at") or "9999-12-31")
    return (status_order.get(str(task.get("status", "todo")), 9), due, str(task.get("id", "")))

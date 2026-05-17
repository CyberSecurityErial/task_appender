from __future__ import annotations

import json
import re
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from .graph import validate_data
from .model import Task, TaskError, VALID_KINDS, VALID_STATUSES, dedupe, today_iso
from .recurrence import parse_daily_time
from .render import render_html, write_rendered
from .store import (
    APP_ROOT,
    DEFAULT_DATA_PATH,
    allocate_id,
    load_data,
    normalize_for_save,
    resolve_task,
    save_data,
    tasks_by_id,
)


DEFAULT_EXPORTS = {
    "mermaid": APP_ROOT / "exports" / "graph.mmd",
    "dot": APP_ROOT / "exports" / "graph.dot",
    "markdown": APP_ROOT / "exports" / "tasks.md",
    "html": APP_ROOT / "exports" / "graph.html",
    "scoreboard": APP_ROOT / "exports" / "scoreboard.html",
}


class TaskGraphHTTPServer(HTTPServer):
    def __init__(self, server_address: tuple[str, int], db_path: Path):
        super().__init__(server_address, TaskGraphHandler)
        self.db_path = db_path
        self.undo_stack: list[str] = []


class TaskGraphHandler(BaseHTTPRequestHandler):
    server: TaskGraphHTTPServer

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        try:
            if path in {"/", "/index.html"}:
                data = load_normalized_data(self.server.db_path)
                self.send_html(render_html(data, live_api=True))
                return
            if path == "/api/tasks":
                data = load_normalized_data(self.server.db_path)
                self.send_json({"tasks": data.get("tasks", [])})
                return
            if path == "/api/health":
                self.send_json({"ok": True})
                return
            self.send_error(404, "not found")
        except TaskError as exc:
            self.send_json({"error": str(exc)}, status=400)
        except Exception as exc:
            self.send_json({"error": str(exc)}, status=500)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            if path == "/api/tasks":
                payload = self.read_json()
                task = mutate_data(self.server.db_path, lambda data: create_task(data, payload), self.server.undo_stack)
                self.send_json({"task": task}, status=201)
                return
            if path == "/api/undo":
                data = undo_last_change(self.server.db_path, self.server.undo_stack)
                self.send_json({"tasks": data.get("tasks", [])})
                return
            self.send_error(404, "not found")
        except TaskError as exc:
            self.send_json({"error": str(exc)}, status=400)
        except Exception as exc:
            self.send_json({"error": str(exc)}, status=500)

    def do_PATCH(self) -> None:
        path = urlparse(self.path).path
        match = re.fullmatch(r"/api/tasks/([^/]+)", path)
        try:
            if match:
                task_id = unquote(match.group(1))
                payload = self.read_json()
                task = mutate_data(self.server.db_path, lambda data: update_task(data, task_id, payload), self.server.undo_stack)
                self.send_json({"task": task})
                return
            self.send_error(404, "not found")
        except TaskError as exc:
            self.send_json({"error": str(exc)}, status=400)
        except Exception as exc:
            self.send_json({"error": str(exc)}, status=500)

    def read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length") or "0")
        if length <= 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise TaskError(f"invalid JSON: {exc}") from exc
        if not isinstance(payload, dict):
            raise TaskError("JSON payload must be an object")
        return payload

    def send_html(self, content: str, *, status: int = 200) -> None:
        body = content.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, payload: dict[str, Any], *, status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        return


def serve(db_path: Path, *, host: str = "127.0.0.1", port: int = 8765) -> None:
    server = TaskGraphHTTPServer((host, port), db_path.expanduser())
    actual_host, actual_port = server.server_address
    print(f"serving task graph UI at http://{actual_host}:{actual_port}/")
    print("press Ctrl-C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        server.server_close()


def load_normalized_data(db_path: Path) -> dict[str, Any]:
    data = load_data(db_path)
    normalize_for_save(data)
    ensure_valid(data)
    return data


def mutate_data(db_path: Path, mutator: Any, undo_stack: list[str] | None = None) -> dict[str, Any]:
    snapshot = db_path.read_text(encoding="utf-8") if db_path.exists() else ""
    data = load_data(db_path)
    normalize_for_save(data)
    task = mutator(data)
    normalize_for_save(data)
    ensure_valid(data)
    if undo_stack is not None:
        undo_stack.append(snapshot)
        del undo_stack[:-20]
    save_data_and_autosync(data, db_path)
    if isinstance(task, dict) and task.get("id") in tasks_by_id(data):
        return tasks_by_id(data)[str(task["id"])]
    return task


def undo_last_change(db_path: Path, undo_stack: list[str]) -> dict[str, Any]:
    if not undo_stack:
        raise TaskError("nothing to undo")
    snapshot = undo_stack.pop()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db_path.write_text(snapshot, encoding="utf-8")
    data = load_data(db_path)
    normalize_for_save(data)
    ensure_valid(data)
    save_data_and_autosync(data, db_path)
    return data


def create_task(data: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    title = str(payload.get("title") or "").strip()
    if not title:
        raise TaskError("title is required")
    kind = normalize_choice(payload.get("kind") or "short", VALID_KINDS, "kind")
    status = normalize_choice(payload.get("status") or "todo", VALID_STATUSES, "status")
    parent = resolve_task(data, str(payload["parent"])) if payload.get("parent") else None
    dependencies = [resolve_task(data, ref) for ref in normalize_refs(payload.get("depends_on"))]
    child_ids = [resolve_task(data, ref) for ref in normalize_refs(payload.get("children"))]
    recurrence = None
    if kind == "daily":
        recurrence = {"freq": "daily", "time": parse_daily_time(str(payload.get("time") or "21:00"))}
    task = Task(
        id=allocate_id(data),
        title=title,
        kind=kind,
        status=status,
        created_at=today_iso(),
        due_at=none_if_blank(payload.get("due_at")),
        priority=int(payload.get("priority") or 3),
        tags=dedupe(normalize_refs(payload.get("tags"))),
        parent=parent,
        depends_on=dependencies,
        recurrence=recurrence,
        completed_at=today_iso() if status in {"done", "archived"} else None,
        notes=str(payload.get("notes") or ""),
    )
    data["tasks"].append(task.to_dict())
    index = tasks_by_id(data)
    for child_id in child_ids:
        index[child_id]["parent"] = task.id
    return task.to_dict()


def update_task(data: dict[str, Any], task_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    index = tasks_by_id(data)
    if task_id not in index:
        raise TaskError(f"task not found: {task_id}")
    task = index[task_id]
    if "title" in payload:
        title = str(payload.get("title") or "").strip()
        if not title:
            raise TaskError("title is required")
        task["title"] = title
    if "kind" in payload:
        task["kind"] = normalize_choice(payload.get("kind"), VALID_KINDS, "kind")
    if "status" in payload:
        status = normalize_choice(payload.get("status"), VALID_STATUSES, "status")
        task["status"] = status
        if status in {"done", "archived"}:
            task["completed_at"] = task.get("completed_at") or today_iso()
        else:
            task["completed_at"] = None
    if "due_at" in payload:
        task["due_at"] = none_if_blank(payload.get("due_at"))
    if "priority" in payload:
        task["priority"] = int(payload.get("priority") or 3)
    if "tags" in payload:
        task["tags"] = dedupe(normalize_refs(payload.get("tags")))
    if "parent" in payload:
        parent = resolve_task(data, str(payload["parent"])) if payload.get("parent") else None
        if parent == task_id:
            raise TaskError("task cannot be its own parent")
        task["parent"] = parent
    if "depends_on" in payload:
        dependencies = [resolve_task(data, ref) for ref in normalize_refs(payload.get("depends_on"))]
        if task_id in dependencies:
            raise TaskError("task cannot depend on itself")
        task["depends_on"] = dedupe(dependencies)
    if "children" in payload:
        children = [resolve_task(data, ref) for ref in normalize_refs(payload.get("children"))]
        if task_id in children:
            raise TaskError("task cannot be its own child")
        desired = set(children)
        for other in index.values():
            if other.get("parent") == task_id and other.get("id") not in desired:
                other["parent"] = None
        for child_id in children:
            index[child_id]["parent"] = task_id
        task["children"] = dedupe(children)
    if "notes" in payload:
        task["notes"] = str(payload.get("notes") or "")
    if task.get("kind") == "daily":
        existing_time = "21:00"
        if isinstance(task.get("recurrence"), dict):
            existing_time = str(task["recurrence"].get("time") or existing_time)
        task["recurrence"] = {"freq": "daily", "time": parse_daily_time(str(payload.get("time") or existing_time))}
    elif "kind" in payload:
        task["recurrence"] = None
    return task


def normalize_choice(value: Any, valid: set[str], field: str) -> str:
    text = str(value or "").strip()
    if text not in valid:
        raise TaskError(f"invalid {field}: {text}")
    return text


def normalize_refs(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [item for item in re.split(r"[,\s，、]+", str(value)) if item]


def none_if_blank(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def ensure_valid(data: dict[str, Any]) -> None:
    result = validate_data(data)
    if result.errors:
        raise TaskError("; ".join(result.errors))


def save_data_and_autosync(data: dict[str, Any], db_path: Path) -> None:
    save_data(data, db_path)
    for format_name, output in exports_for_db(db_path).items():
        write_rendered(data, format_name, output)


def is_default_db(db_path: Path) -> bool:
    return db_path.expanduser().resolve() == DEFAULT_DATA_PATH.resolve()


def exports_for_db(db_path: Path) -> dict[str, Path]:
    if is_default_db(db_path):
        return dict(DEFAULT_EXPORTS)
    output_dir = db_path.expanduser().resolve().parent / "exports"
    return {format_name: output_dir / default_output.name for format_name, default_output in DEFAULT_EXPORTS.items()}

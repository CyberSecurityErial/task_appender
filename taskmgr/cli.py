from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

from .graph import validate_data
from .analytics import build_progress, format_progress_cli
from .model import Task, TaskError, VALID_KINDS, VALID_STATUSES, dedupe, task_sort_key, today_iso
from .recurrence import parse_daily_time, parse_due_text
from .render import write_rendered
from .store import (
    APP_ROOT,
    DEFAULT_DATA_PATH,
    allocate_id,
    find_title,
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


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    db_path = Path(args.db).expanduser()
    try:
        return args.func(args, db_path)
    except TaskError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="taskmgr", description="Local-first personal task graph manager.")
    parser.add_argument("--db", default=str(DEFAULT_DATA_PATH), help="YAML task database path")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("add", help="add a task")
    p.add_argument("--kind", required=True, choices=sorted(VALID_KINDS))
    p.add_argument("--title", required=True)
    p.add_argument("--due", "--due-at", dest="due_at")
    p.add_argument("--parent")
    p.add_argument("--depends-on", action="append", default=[])
    p.add_argument("--tag", action="append", default=[])
    p.add_argument("--priority", type=int, default=3)
    p.add_argument("--status", choices=sorted(VALID_STATUSES), default="todo")
    p.add_argument("--time", help="daily recurrence time, HH:MM or natural Chinese time")
    p.add_argument("--notes", default="")
    p.set_defaults(func=cmd_add)

    p = sub.add_parser("list", help="list tasks")
    p.add_argument("--kind", choices=sorted(VALID_KINDS))
    p.add_argument("--status", choices=sorted(VALID_STATUSES))
    p.add_argument("--tag")
    p.add_argument("--blocked", action="store_true", help="show tasks with unfinished dependencies")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("today", help="list due and daily tasks for today")
    p.set_defaults(func=cmd_today)

    p = sub.add_parser("scoreboard", help="show XP, levels, outputs, and gains")
    p.set_defaults(func=cmd_scoreboard)

    p = sub.add_parser("done", help="mark task done")
    p.add_argument("ref")
    p.set_defaults(func=cmd_done)

    p = sub.add_parser("link", help="add dependency: task depends on depends-on")
    p.add_argument("--task", required=True)
    p.add_argument("--depends-on", required=True)
    p.set_defaults(func=cmd_link)

    p = sub.add_parser("unlink", help="remove dependency")
    p.add_argument("--task", required=True)
    p.add_argument("--depends-on", required=True)
    p.set_defaults(func=cmd_unlink)

    p = sub.add_parser("move", help="set or clear a task parent")
    p.add_argument("--task", required=True)
    parent_group = p.add_mutually_exclusive_group(required=True)
    parent_group.add_argument("--parent", help="new parent task")
    parent_group.add_argument("--root", "--clear-parent", action="store_true", help="move task to root level")
    p.set_defaults(func=cmd_move)

    p = sub.add_parser("validate", help="validate task graph")
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("render", help="render exports")
    p.add_argument("--format", choices=sorted(DEFAULT_EXPORTS), default="mermaid")
    p.add_argument("--output", "-o")
    p.set_defaults(func=cmd_render)

    p = sub.add_parser("sync", help="validate and render all exports")
    p.add_argument("--output-dir", help="directory for all rendered export files")
    p.set_defaults(func=cmd_sync)

    p = sub.add_parser("serve", help="serve local task graph UI with write APIs")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8765)
    p.set_defaults(func=cmd_serve)

    p = sub.add_parser("apply-inbox", help="parse markdown inbox bullets into tasks")
    p.add_argument("path", nargs="?", default=str(APP_ROOT / "TASK_INBOX.md"))
    p.set_defaults(func=cmd_apply_inbox)

    return parser


def cmd_add(args: argparse.Namespace, db_path: Path) -> int:
    data = load_data(db_path)
    normalize_for_save(data)
    parent = resolve_task(data, args.parent) if args.parent else None
    dependencies = [resolve_task(data, ref) for ref in args.depends_on]
    recurrence = None
    if args.kind == "daily":
        recurrence = {"freq": "daily", "time": normalize_time(args.time or "21:00")}
    task = Task(
        id=allocate_id(data),
        title=args.title.strip(),
        kind=args.kind,
        status=args.status,
        created_at=today_iso(),
        due_at=args.due_at,
        priority=args.priority,
        tags=dedupe([tag.strip() for tag in args.tag if tag.strip()]),
        parent=parent,
        depends_on=dependencies,
        recurrence=recurrence,
        completed_at=today_iso() if args.status == "done" else None,
        notes=args.notes,
    )
    data["tasks"].append(task.to_dict())
    normalize_for_save(data)
    ensure_valid(data)
    save_data_and_autosync(data, db_path)
    print(f"created {task.id}: {task.title}")
    return 0


def cmd_list(args: argparse.Namespace, db_path: Path) -> int:
    data = load_data(db_path)
    normalize_for_save(data)
    tasks = list(data.get("tasks", []))
    if args.kind:
        tasks = [task for task in tasks if task.get("kind") == args.kind]
    if args.status:
        tasks = [task for task in tasks if task.get("status") == args.status]
    if args.tag:
        tasks = [task for task in tasks if args.tag in task.get("tags", [])]
    if args.blocked:
        tasks = [task for task in tasks if blocking_reasons(data, task)]
    print_tasks(data, sorted(tasks, key=task_sort_key), show_blockers=args.blocked)
    return 0


def cmd_today(args: argparse.Namespace, db_path: Path) -> int:
    data = load_data(db_path)
    normalize_for_save(data)
    today = date.today().isoformat()
    tasks = [
        task
        for task in data.get("tasks", [])
        if task.get("status") not in {"done", "archived"}
        and (task.get("kind") == "daily" or (task.get("due_at") and task.get("due_at") <= today))
    ]
    print_tasks(data, sorted(tasks, key=task_sort_key), show_blockers=True)
    return 0


def cmd_scoreboard(args: argparse.Namespace, db_path: Path) -> int:
    data = load_data(db_path)
    normalize_for_save(data)
    print(format_progress_cli(build_progress(data)))
    return 0


def cmd_done(args: argparse.Namespace, db_path: Path) -> int:
    data = load_data(db_path)
    task_id = resolve_task(data, args.ref)
    task = tasks_by_id(data)[task_id]
    task["status"] = "done"
    task["completed_at"] = task.get("completed_at") or today_iso()
    normalize_for_save(data)
    ensure_valid(data)
    save_data_and_autosync(data, db_path)
    print(f"done {task_id}")
    return 0


def cmd_link(args: argparse.Namespace, db_path: Path) -> int:
    data = load_data(db_path)
    task_id = resolve_task(data, args.task)
    dependency = resolve_task(data, args.depends_on)
    if task_id == dependency:
        raise TaskError("task cannot depend on itself")
    task = tasks_by_id(data)[task_id]
    task["depends_on"] = dedupe(task.get("depends_on", []) + [dependency])
    normalize_for_save(data)
    ensure_valid(data)
    save_data_and_autosync(data, db_path)
    print(f"linked {dependency} -> {task_id}")
    return 0


def cmd_unlink(args: argparse.Namespace, db_path: Path) -> int:
    data = load_data(db_path)
    task_id = resolve_task(data, args.task)
    dependency = resolve_task(data, args.depends_on)
    task = tasks_by_id(data)[task_id]
    task["depends_on"] = [ref for ref in task.get("depends_on", []) if ref != dependency]
    normalize_for_save(data)
    ensure_valid(data)
    save_data_and_autosync(data, db_path)
    print(f"unlinked {dependency} -> {task_id}")
    return 0


def cmd_move(args: argparse.Namespace, db_path: Path) -> int:
    data = load_data(db_path)
    normalize_for_save(data)
    task_id = resolve_task(data, args.task)
    parent_id = None if args.root else resolve_task(data, args.parent)
    if task_id == parent_id:
        raise TaskError("task cannot be its own parent")
    tasks_by_id(data)[task_id]["parent"] = parent_id
    normalize_for_save(data)
    ensure_valid(data)
    save_data_and_autosync(data, db_path)
    destination = parent_id if parent_id else "root"
    print(f"moved {task_id} under {destination}")
    return 0


def cmd_validate(args: argparse.Namespace, db_path: Path) -> int:
    data = load_data(db_path)
    result = validate_data(data)
    for warning in result.warnings:
        print(f"warning: {warning}")
    if result.ok:
        print("valid")
        return 0
    for error in result.errors:
        print(f"error: {error}", file=sys.stderr)
    return 2


def cmd_render(args: argparse.Namespace, db_path: Path) -> int:
    data = load_data(db_path)
    ensure_valid(data)
    output = Path(args.output).expanduser() if args.output else exports_for_db(db_path)[args.format]
    write_rendered(data, args.format, output)
    print(f"wrote {output}")
    return 0


def cmd_sync(args: argparse.Namespace, db_path: Path) -> int:
    data = load_data(db_path)
    result = validate_data(data)
    for warning in result.warnings:
        print(f"warning: {warning}")
    if result.errors:
        raise TaskError("; ".join(result.errors))
    print("valid")
    output_dir = Path(args.output_dir).expanduser() if args.output_dir else None
    export_targets = exports_for_db(db_path)
    for format_name, default_output in export_targets.items():
        output = output_dir / default_output.name if output_dir else default_output
        write_rendered(data, format_name, output)
        print(f"wrote {output}")
    return 0


def cmd_serve(args: argparse.Namespace, db_path: Path) -> int:
    from .server import serve

    serve(db_path, host=args.host, port=args.port)
    return 0


def cmd_apply_inbox(args: argparse.Namespace, db_path: Path) -> int:
    inbox_path = Path(args.path).expanduser()
    if not inbox_path.exists():
        raise TaskError(f"inbox not found: {inbox_path}")
    data = load_data(db_path)
    normalize_for_save(data)
    created: list[str] = []
    for item in parse_inbox(inbox_path.read_text(encoding="utf-8")):
        spec = infer_inbox_task(item)
        if find_title(data, spec["title"]):
            continue
        task = Task(id=allocate_id(data), created_at=today_iso(), **spec)
        data["tasks"].append(task.to_dict())
        created.append(task.id)
    normalize_for_save(data)
    ensure_valid(data)
    save_data_and_autosync(data, db_path)
    print(f"created {len(created)} task(s): {', '.join(created) if created else '-'}")
    return 0


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


def ensure_valid(data: dict[str, Any]) -> None:
    result = validate_data(data)
    if result.errors:
        raise TaskError("; ".join(result.errors))


def print_tasks(data: dict[str, Any], tasks: list[dict[str, Any]], *, show_blockers: bool = False) -> None:
    if not tasks:
        print("no tasks")
        return
    rows = []
    for task in tasks:
        blockers = ",".join(blocking_reasons(data, task)) if show_blockers else ""
        rows.append(
            [
                task["id"],
                task["status"],
                task["kind"],
                task.get("due_at") or "-",
                ",".join(task.get("tags", [])) or "-",
                task["title"],
                blockers,
            ]
        )
    headers = ["ID", "STATUS", "KIND", "DUE", "TAGS", "TITLE"]
    if show_blockers:
        headers.append("BLOCKED_BY")
    else:
        rows = [row[:-1] for row in rows]
    widths = [len(header) for header in headers]
    for row in rows:
        for index, value in enumerate(row):
            widths[index] = min(max(widths[index], len(str(value))), 36 if index == len(row) - 1 else 18)
    print("  ".join(header.ljust(widths[index]) for index, header in enumerate(headers)))
    print("  ".join("-" * width for width in widths))
    for row in rows:
        print("  ".join(truncate(str(value), widths[index]).ljust(widths[index]) for index, value in enumerate(row)))


def blocking_reasons(data: dict[str, Any], task: dict[str, Any]) -> list[str]:
    index = tasks_by_id(data)
    blockers: list[str] = []
    for ref in task.get("depends_on", []):
        other = index.get(ref)
        if other and other.get("status") != "done":
            blockers.append(ref)
    return blockers


def parse_inbox(text: str) -> list[str]:
    items: list[str] = []
    for line in text.splitlines():
        match = re.match(r"\s*(?:[-*]|\d+[.)、])\s+(.+?)\s*$", line)
        if match:
            items.append(match.group(1).strip())
    return items


def infer_inbox_task(text: str) -> dict[str, Any]:
    kind = "short"
    if "每日" in text or "每天" in text:
        kind = "daily"
    elif "长期目标" in text or text.startswith("长期"):
        kind = "long"
    elif "里程碑" in text:
        kind = "milestone"

    title = clean_inbox_title(text)
    due_at = parse_due_text(text) if kind in {"short", "milestone"} else None
    tags = re.findall(r"#([A-Za-z0-9_\-\u4e00-\u9fff]+)", text)
    recurrence = {"freq": "daily", "time": parse_daily_time(text)} if kind == "daily" else None
    return {
        "title": title,
        "kind": kind,
        "status": "todo",
        "due_at": due_at,
        "priority": 3,
        "tags": tags,
        "parent": None,
        "depends_on": [],
        "children": [],
        "recurrence": recurrence,
        "notes": text,
    }


def clean_inbox_title(text: str) -> str:
    title = re.sub(r"^\s*(短期任务|长期目标|每日任务|里程碑)[:：]\s*", "", text)
    title = re.sub(r"#([A-Za-z0-9_\-\u4e00-\u9fff]+)", "", title)
    title = re.sub(r"(本周[一二三四五六日天]|下周[一二三四五六日天]|五一|今天|明天|后天|20\d{2}-\d{1,2}-\d{1,2}|\d{1,2}月\d{1,2}[日号]?)(前|之前)?", "", title)
    title = re.sub(r"(我想|我要|需要|完成|每天|每日|晚上|上午|下午|早上|中午|\d{1,2}:\d{2}|[一二三四五六七八九十0-9]+点半?)", "", title)
    title = re.sub(r"\s+", " ", title)
    title = title.strip(" ，,。；;：:")
    return title or text.strip()


def normalize_time(value: str) -> str:
    if re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", value):
        return value
    return parse_daily_time(value)


def truncate(value: str, width: int) -> str:
    if len(value) <= width:
        return value
    return value[: max(0, width - 1)] + "…"


if __name__ == "__main__":
    raise SystemExit(main())

# Notification Reminders Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add self-contained macOS reminders for daily and due-date tasks, configured in the existing CLI/Web UI and active only while `start_ui.sh` is running.

**Architecture:** Task reminder rules stay in `tasks.yaml`, notification preferences and the delivery ledger live beside that database, and a worker owned by `taskmgr serve` scans for due occurrences. A bundled AppleScript application submits native macOS notifications; no external Notification checkout or login-start scheduler is required.

**Tech Stack:** Python 3.10+ standard library, PyYAML, `http.server`, macOS `osacompile`/`codesign`/`open`, AppleScript, unittest, pytest.

---

## File Map

- Create `taskmgr/settings.py`: notification settings and delivery-ledger persistence.
- Create `taskmgr/errors.py`: cycle-free home for `TaskError`; `taskmgr.model` re-exports the imported name for compatibility.
- Create `taskmgr/reminder_rules.py`: cycle-free reminder parsing, normalization, validation, and display formatting.
- Create `taskmgr/reminders.py`: occurrence calculation, retry decisions, scan execution, and worker loop.
- Create `taskmgr/notifier.py`: native app build/setup/status/send adapter.
- Create `scripts/notification-agent.applescript`: bundled native notification application.
- Create `tests/test_settings.py`, `tests/test_reminders.py`, `tests/test_notifier.py`: focused unit tests.
- Modify `taskmgr/model.py`, `taskmgr/graph.py`: persist and validate `reminders`.
- Modify `taskmgr/cli.py`: task reminder mutation commands.
- Modify `taskmgr/server.py`: worker lifecycle, settings/setup/test APIs, task reminder payloads.
- Modify `taskmgr/render.py`: reminder summaries, task rule editor, settings dialog, browser-side API calls.
- Modify `start_ui.sh`: run through Conda `agent`; server owns the worker.
- Modify `tests/test_model.py`, `tests/test_graph.py`, `tests/test_cli.py`: regression and integration coverage.
- Modify `README.md`, `USAGE.md`: user-facing setup, limitations, and CLI syntax.
- Regenerate `exports/graph.mmd`, `exports/graph.dot`, `exports/tasks.md`, `exports/graph.html`, `exports/scoreboard.html`.

### Task 1: Add the reminder rule contract to the task model

**Files:**
- Create: `taskmgr/errors.py`
- Create: `taskmgr/reminder_rules.py`
- Modify: `taskmgr/model.py:33-85`
- Modify: `taskmgr/graph.py:43-66`
- Modify: `tests/test_model.py`
- Modify: `tests/test_graph.py`
- Create: `tests/test_reminders.py`

- [ ] **Step 1: Write failing model and validation tests**

Add these cases:

```python
# tests/test_reminders.py
import unittest

from taskmgr.model import TaskError
from taskmgr.reminder_rules import format_reminders, parse_reminder_rule, validate_reminders


class ReminderRuleTests(unittest.TestCase):
    def test_parse_and_format_due_rules(self):
        rules = [parse_reminder_rule("1d@09:00"), parse_reminder_rule("0d@09:00")]
        self.assertEqual(rules, [{"days_before": 1, "time": "09:00"}, {"days_before": 0, "time": "09:00"}])
        self.assertEqual(format_reminders(rules), "提前 1 天 09:00；当天 09:00")

    def test_parse_rejects_invalid_rule(self):
        with self.assertRaisesRegex(TaskError, "Nd@HH:MM"):
            parse_reminder_rule("tomorrow")

    def test_validate_rejects_duplicate_and_missing_due(self):
        duplicate = [{"days_before": 1, "time": "09:00"}, {"days_before": 1, "time": "09:00"}]
        self.assertIn("duplicate", " ".join(validate_reminders("short", "2026-07-04", duplicate)))
        self.assertIn("requires due_at", " ".join(validate_reminders("short", None, duplicate[:1])))

    def test_daily_task_cannot_add_due_rules(self):
        errors = validate_reminders("daily", None, [{"days_before": 0, "time": "09:00"}])
        self.assertIn("daily task reminders must be empty", errors)


if __name__ == "__main__":
    unittest.main()
```

In `tests/test_model.py`, assign a legacy mapping to `raw`, then assert it gains `reminders: []` after `Task.from_dict(raw).to_dict()`. In `tests/test_graph.py`, assert invalid reminder rules appear as task-prefixed validation errors.

- [ ] **Step 2: Run the focused tests and verify they fail**

Run:

```bash
conda run -n agent python -m unittest tests.test_reminders tests.test_model tests.test_graph
```

Expected: import failure for `taskmgr.reminder_rules` or missing `reminders` field.

- [ ] **Step 3: Implement parsing, formatting, normalization, and validation**

Create `taskmgr/errors.py`:

```python
class TaskError(Exception):
    """Raised for invalid task graph operations."""
```

Delete the class body from `taskmgr/model.py` and add `from .errors import TaskError`. Existing `from taskmgr.model import TaskError` imports remain compatible because the imported name is still present in the model module.

Create `taskmgr/reminder_rules.py` with these public rule helpers:

```python
from __future__ import annotations

import re
from typing import Any

from .errors import TaskError


RULE_RE = re.compile(r"(\d+)d@([0-2]\d:[0-5]\d)\Z")
TIME_RE = re.compile(r"([01]\d|2[0-3]):[0-5]\d\Z")


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
    result: list[dict[str, Any]] = []
    for rule in value:
        if isinstance(rule, dict):
            result.append({"days_before": rule.get("days_before"), "time": str(rule.get("time", "")).strip()})
        else:
            result.append(rule)
    return result


def validate_reminders(kind: str, due_at: Any, reminders: Any) -> list[str]:
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
        if not isinstance(days, int) or not 0 <= days <= 3650:
            errors.append(f"reminders[{index}].days_before must be an integer from 0 to 3650")
        if not isinstance(time_value, str) or not TIME_RE.fullmatch(time_value):
            errors.append(f"reminders[{index}].time must be HH:MM")
        if isinstance(days, int) and isinstance(time_value, str):
            key = (days, time_value)
            if key in seen:
                errors.append(f"reminders[{index}] duplicate reminder rule")
            seen.add(key)
    return errors


def format_reminders(reminders: Any) -> str:
    if not isinstance(reminders, list) or not reminders:
        return "-"
    labels = []
    for rule in reminders:
        days = int(rule["days_before"])
        prefix = "当天" if days == 0 else f"提前 {days} 天"
        labels.append(f"{prefix} {rule['time']}")
    return "；".join(labels)
```

Add `reminders: list[dict[str, Any]] = field(default_factory=list)` to `Task`, normalize it in `from_dict`, and emit it in `to_dict`. Call `validate_reminders(str(task.get("kind")), task.get("due_at"), task.get("reminders"))` from `validate_data` after recurrence validation.

- [ ] **Step 4: Run focused tests and verify they pass**

Run:

```bash
conda run -n agent python -m unittest tests.test_reminders tests.test_model tests.test_graph
```

Expected: all selected tests pass.

- [ ] **Step 5: Commit the rule contract**

```bash
git add taskmgr/errors.py taskmgr/reminder_rules.py taskmgr/model.py taskmgr/graph.py tests/test_model.py tests/test_graph.py tests/test_reminders.py
git commit -m "feat: add task reminder rules"
```

### Task 2: Add CLI reminder mutations and export summaries

**Files:**
- Modify: `taskmgr/cli.py:48-151`
- Modify: `taskmgr/render.py:105-153,174-186,1766-1828`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write failing CLI and rendering tests**

Add a CLI test that creates and then replaces rules:

```python
def test_add_set_and_clear_reminders(self):
    with tempfile.TemporaryDirectory() as tmpdir:
        db = Path(tmpdir) / "tasks.yaml"
        code, _, err = self.run_cli(
            "--db", str(db), "add", "--kind", "short", "--title", "交作业",
            "--due", "2026-07-04", "--reminder", "1d@09:00", "--reminder", "0d@09:00",
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(len(tasks_by_id(load_data(db))["T-0001"]["reminders"]), 2)

        self.assertEqual(self.run_cli(
            "--db", str(db), "reminders", "set", "--task", "T-0001", "--rule", "2d@20:00"
        )[0], 0)
        self.assertEqual(tasks_by_id(load_data(db))["T-0001"]["reminders"], [{"days_before": 2, "time": "20:00"}])

        self.assertEqual(self.run_cli("--db", str(db), "reminders", "clear", "--task", "T-0001")[0], 0)
        self.assertEqual(tasks_by_id(load_data(db))["T-0001"]["reminders"], [])
```

Extend the existing HTML/Markdown assertions to require `提前 1 天 09:00` after rendering a task with a rule.

- [ ] **Step 2: Run the CLI test and verify it fails**

```bash
conda run -n agent python -m unittest tests.test_cli.CliTests.test_add_set_and_clear_reminders
```

Expected: argparse rejects `--reminder` or the `reminders` command.

- [ ] **Step 3: Implement atomic CLI mutations**

Add repeatable `--reminder` to `add`, and nested reminder commands:

```python
p.add_argument("--reminder", action="append", default=[], help="due reminder as Nd@HH:MM")

p = sub.add_parser("reminders", help="replace or clear due reminder rules")
reminder_sub = p.add_subparsers(dest="reminder_command", required=True)
set_parser = reminder_sub.add_parser("set")
set_parser.add_argument("--task", required=True)
set_parser.add_argument("--rule", action="append", required=True)
set_parser.set_defaults(func=cmd_reminders_set)
clear_parser = reminder_sub.add_parser("clear")
clear_parser.add_argument("--task", required=True)
clear_parser.set_defaults(func=cmd_reminders_clear)
```

Set `reminders=[parse_reminder_rule(value) for value in args.reminder]` in `cmd_add`. Implement both mutation commands through this shared function:

```python
def replace_reminders(db_path: Path, ref: str, rules: list[dict[str, Any]]) -> str:
    data = load_data(db_path)
    normalize_for_save(data)
    task_id = resolve_task(data, ref)
    tasks_by_id(data)[task_id]["reminders"] = rules
    normalize_for_save(data)
    ensure_valid(data)
    save_data_and_autosync(data, db_path)
    return task_id
```

Add `format_reminders(task.get("reminders"))` to Markdown task detail lines, HTML table rows, inspector metadata, and SVG `data-reminders`. Do not change Mermaid/DOT graph topology.

- [ ] **Step 4: Run CLI and render tests**

```bash
conda run -n agent python -m unittest tests.test_cli
```

Expected: all CLI tests pass and custom-database exports are regenerated.

- [ ] **Step 5: Commit CLI and summaries**

```bash
git add taskmgr/cli.py taskmgr/render.py tests/test_cli.py
git commit -m "feat: edit reminders from cli"
```

### Task 3: Persist notification settings and the delivery ledger

**Files:**
- Create: `taskmgr/settings.py`
- Create: `tests/test_settings.py`

- [ ] **Step 1: Write failing settings tests**

```python
import json
import tempfile
import unittest
from pathlib import Path

from taskmgr.model import TaskError
from taskmgr.settings import load_ledger, load_settings, save_ledger, save_settings, settings_path_for_db, state_path_for_db


class SettingsTests(unittest.TestCase):
    def test_defaults_and_custom_database_paths(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Path(tmpdir) / "tasks.yaml"
            settings = load_settings(db)
            self.assertFalse(settings["enabled"])
            self.assertEqual(settings["timezone"], "Asia/Shanghai")
            self.assertEqual(settings_path_for_db(db), Path(tmpdir) / "settings.yaml")
            self.assertEqual(state_path_for_db(db), Path(tmpdir) / "reminder_state.json")

    def test_save_round_trip_and_invalid_timezone(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Path(tmpdir) / "tasks.yaml"
            saved = save_settings(db, {"enabled": True, "timezone": "Asia/Shanghai", "default_sound": "Glass", "missed_grace_minutes": 120, "check_interval_seconds": 60})
            self.assertEqual(load_settings(db), saved)
            with self.assertRaisesRegex(TaskError, "timezone"):
                save_settings(db, {**saved, "timezone": "Mars/Olympus"})

    def test_ledger_round_trip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Path(tmpdir) / "tasks.yaml"
            save_ledger(db, {"events": {"key": {"delivered_at": "2026-06-20T09:00:00+08:00"}}})
            self.assertEqual(load_ledger(db)["events"]["key"]["delivered_at"], "2026-06-20T09:00:00+08:00")
            json.loads(state_path_for_db(db).read_text(encoding="utf-8"))
```

- [ ] **Step 2: Verify settings tests fail**

```bash
conda run -n agent python -m unittest tests.test_settings
```

Expected: import failure for `taskmgr.settings`.

- [ ] **Step 3: Implement validated atomic persistence**

Implement these public functions in `taskmgr/settings.py`:

```python
DEFAULT_SETTINGS = {
    "enabled": False,
    "timezone": "Asia/Shanghai",
    "default_sound": "Glass",
    "missed_grace_minutes": 120,
    "check_interval_seconds": 60,
}


def settings_path_for_db(db_path: Path) -> Path:
    return db_path.expanduser().resolve().with_name("settings.yaml")


def state_path_for_db(db_path: Path) -> Path:
    return db_path.expanduser().resolve().with_name("reminder_state.json")
```

`load_settings` returns defaults when missing, requires a mapping with `version: 1` or a direct notification mapping, merges only the five allowed keys, and calls `validate_settings`. `save_settings` validates before writing:

```python
payload = {"version": 1, "notifications": normalized}
tmp_path = path.with_suffix(path.suffix + ".tmp")
tmp_path.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")
tmp_path.replace(path)
```

Validate timezone with `ZoneInfo`, bounds exactly as specified, boolean type for enabled, and string type for sound. Implement JSON ledger load/save with `{"version": 1, "events": {}}` defaults and the same temporary-file replacement pattern.

- [ ] **Step 4: Run settings tests**

```bash
conda run -n agent python -m unittest tests.test_settings
```

Expected: all settings tests pass.

- [ ] **Step 5: Commit settings persistence**

```bash
git add taskmgr/settings.py tests/test_settings.py
git commit -m "feat: persist notification settings"
```

### Task 4: Calculate occurrences, deduplicate delivery, and retry failures

**Files:**
- Create: `taskmgr/reminders.py`
- Modify: `tests/test_reminders.py`

- [ ] **Step 1: Write failing occurrence and retry tests**

Add tests using fixed aware datetimes:

```python
from datetime import datetime
from zoneinfo import ZoneInfo

from taskmgr.reminders import build_occurrences, run_reminder_scan


def active_task(**updates):
    task = {"id": "T-0001", "title": "交作业", "kind": "short", "status": "todo", "due_at": "2026-06-21", "reminders": [{"days_before": 1, "time": "09:00"}], "recurrence": None}
    task.update(updates)
    return task


class FakeNotifier:
    def __init__(self, fail=False):
        self.fail = fail
        self.sent = []

    def send(self, title, message, sound=""):
        self.sent.append((title, message, sound))
        if self.fail:
            raise RuntimeError("backend failed")


class OccurrenceTests(unittest.TestCase):
    def test_due_and_daily_occurrences_inside_grace_window(self):
        now = datetime(2026, 6, 20, 9, 30, tzinfo=ZoneInfo("Asia/Shanghai"))
        tasks = [active_task(), active_task(id="T-0002", kind="daily", due_at=None, reminders=[], recurrence={"freq": "daily", "time": "09:15"})]
        events = build_occurrences(tasks, now, {"timezone": "Asia/Shanghai", "missed_grace_minutes": 120})
        self.assertEqual([event.task_id for event in events], ["T-0001", "T-0002"])

    def test_done_and_old_occurrences_are_skipped(self):
        now = datetime(2026, 6, 20, 12, 1, tzinfo=ZoneInfo("Asia/Shanghai"))
        self.assertEqual(build_occurrences([active_task(status="done")], now, {"timezone": "Asia/Shanghai", "missed_grace_minutes": 120}), [])
        self.assertEqual(build_occurrences([active_task()], now, {"timezone": "Asia/Shanghai", "missed_grace_minutes": 120}), [])

    def test_success_is_deduplicated(self):
        notifier = FakeNotifier()
        run_reminder_scan(self.db, now=self.now, notifier=notifier)
        run_reminder_scan(self.db, now=self.now, notifier=notifier)
        self.assertEqual(len(notifier.sent), 1)

    def test_failure_retries_only_after_backoff(self):
        notifier = FakeNotifier(fail=True)
        run_reminder_scan(self.db, now=self.now, notifier=notifier)
        run_reminder_scan(self.db, now=self.now, notifier=notifier)
        self.assertEqual(len(notifier.sent), 1)
        run_reminder_scan(self.db, now=self.now.replace(minute=31), notifier=notifier)
        self.assertEqual(len(notifier.sent), 2)
```

Use `setUp` to create a temporary `tasks.yaml`, enabled settings, and `self.now = 2026-06-20 09:30 +08:00`.

- [ ] **Step 2: Run occurrence tests and verify failure**

```bash
conda run -n agent python -m unittest tests.test_reminders
```

Expected: missing occurrence/scan APIs.

- [ ] **Step 3: Implement occurrence and scan APIs**

Add this value object and public functions:

```python
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


```

Implement `build_occurrences(tasks: list[dict[str, Any]], now: datetime, settings: dict[str, Any]) -> list[ReminderOccurrence]` and `run_reminder_scan(db_path: Path, *, now: datetime | None = None, notifier: Any | None = None) -> dict[str, int]` with the rules below.

`build_occurrences` must:

1. Construct `ZoneInfo(settings["timezone"])` and convert `now` to it.
2. Ignore statuses outside `{"todo", "doing", "blocked"}`.
3. Build the current-date daily occurrence from `recurrence.time`.
4. Build every due occurrence from `due_at - timedelta(days=days_before)` and rule time.
5. Keep only `now - grace <= scheduled_at <= now`.
6. Sort by `(scheduled_at, task_id, key)`.

Use the exact title `任务提醒 · {task_id}` in `run_reminder_scan`. Message format is `{task title} — 每日 HH:MM`, `{task title} — 截止 YYYY-MM-DD（当天 HH:MM）`, or `{task title} — 截止 YYYY-MM-DD（提前 N 天 HH:MM）`.

`run_reminder_scan` loads normalized task data, settings, and ledger. It returns `{"sent": int, "failed": int, "skipped": int}`. For each occurrence:

- Skip an event with `delivered_at`.
- Skip a failed event until `next_retry_at <= now`.
- On success, write `delivered_at` and remove retry fields.
- On failure, increment `failure_count`, choose delays `(1, 5, 15, 30)` by attempt index with 30-minute cap, and write `next_retry_at` plus `last_error`.
- Re-check the current task status before every retry.
- Prune entries whose last timestamp is older than 90 days.
- Save the ledger once after processing the batch.

- [ ] **Step 4: Run reminder-engine tests**

```bash
conda run -n agent python -m unittest tests.test_reminders
```

Expected: all rule, occurrence, deduplication, and retry tests pass.

- [ ] **Step 5: Commit reminder engine**

```bash
git add taskmgr/reminders.py tests/test_reminders.py
git commit -m "feat: schedule and deduplicate reminders"
```

### Task 5: Bundle and test the native macOS notifier

**Files:**
- Create: `taskmgr/notifier.py`
- Create: `scripts/notification-agent.applescript`
- Create: `tests/test_notifier.py`

- [ ] **Step 1: Write failing native adapter tests**

Create fakes that record arguments and snapshot request files, then test:

```python
class NotifierTests(unittest.TestCase):
    def test_setup_builds_named_signed_app(self):
        notifier = self.make_notifier()
        notifier.setup()
        self.assertTrue((self.app / "Contents" / "Info.plist").exists())
        info = plistlib.loads((self.app / "Contents" / "Info.plist").read_bytes())
        self.assertEqual(info["CFBundleIdentifier"], "local.notification.agent")
        self.assertIn(str(self.app), self.codesign_log.read_text(encoding="utf-8"))

    def test_send_treats_metacharacters_as_data(self):
        notifier = self.make_notifier()
        notifier.setup()
        notifier.send('任务 "A"', "Finished $HOME; $(touch marker)", "Glass")
        self.assertEqual((self.snapshot / "title.txt").read_text(encoding="utf-8"), '任务 "A"')
        self.assertEqual((self.snapshot / "message.txt").read_text(encoding="utf-8"), "Finished $HOME; $(touch marker)")

    def test_send_requires_initialized_app_and_propagates_open_failure(self):
        notifier = self.make_notifier()
        with self.assertRaisesRegex(NotificationError, "initialize"):
            notifier.send("Title", "Message")
        notifier.setup()
        self.open_status = 7
        with self.assertRaisesRegex(NotificationError, "status 7"):
            notifier.send("Title", "Message")
```

The fake `osacompile` must create `Contents/Resources/Scripts/main.scpt` and a minimal binary plist or XML plist. The fake `open` snapshots request files before the temporary directory is removed.

- [ ] **Step 2: Run notifier tests and verify failure**

```bash
conda run -n agent python -m unittest tests.test_notifier
```

Expected: import failure for `taskmgr.notifier`.

- [ ] **Step 3: Implement the adapter and bundled AppleScript**

Implement:

```python
class NotificationError(TaskError):
    pass


class NativeNotifier:
    def __init__(self, app_path=APP_ROOT / "build" / "Notification Agent.app", source_path=APP_ROOT / "scripts" / "notification-agent.applescript", osacompile="/usr/bin/osacompile", codesign="/usr/bin/codesign", open_command="/usr/bin/open"):
        self.app_path = Path(app_path)
        self.source_path = Path(source_path)
        self.osacompile = str(osacompile)
        self.codesign = str(codesign)
        self.open_command = str(open_command)

    def status(self) -> dict[str, bool]:
        compiled = self.app_path / "Contents" / "Resources" / "Scripts" / "main.scpt"
        return {"app_built": compiled.is_file()}
```

`setup` rebuilds when the app or compiled script is missing or source is newer, updates `Info.plist` with `plistlib`, signs with argument-array `subprocess.run`, and opens the app with `-W -n -a`. `send` rejects empty title/message and missing app, writes UTF-8 request files in `TemporaryDirectory`, and runs `[open_command, "-W", "-n", "-a", app_path, request_dir]`. Capture stderr and include non-zero status and diagnostic in `NotificationError`.

Create `scripts/notification-agent.applescript` with the full bundled handler:

```applescript
property agentTitle : "Notification Agent"

on run
	display notification "Notification Agent is ready to send task notifications." with title agentTitle
end run

on open openedItems
	if (count of openedItems) < 1 then
		error "Notification request folder is required." number 64
	end if

	set requestFolder to item 1 of openedItems
	set requestFolderPath to requestFolder as text
	set notificationTitle to my readRequiredText(requestFolderPath, "title.txt", "title")
	set notificationMessage to my readRequiredText(requestFolderPath, "message.txt", "message")
	set soundName to my readOptionalText(requestFolderPath, "sound.txt")

	if soundName is not "" then
		display notification notificationMessage with title notificationTitle sound name soundName
	else
		display notification notificationMessage with title notificationTitle
	end if
end open

on readRequiredText(folderPath, fileName, fieldName)
	set valueText to my readOptionalText(folderPath, fileName)
	if valueText is "" then
		error fieldName & " must not be empty." number 64
	end if
	return valueText
end readRequiredText

on readOptionalText(folderPath, fileName)
	set filePath to folderPath & fileName
	try
		set fileAlias to filePath as alias
	on error
		return ""
	end try
	set fileRef to open for access fileAlias
	try
		set valueText to read fileRef as «class utf8»
		close access fileRef
	on error errorMessage number errorNumber
		try
			close access fileRef
		end try
		error errorMessage number errorNumber
	end try
	return valueText
end readOptionalText
```

- [ ] **Step 4: Run notifier tests**

```bash
conda run -n agent python -m unittest tests.test_notifier
```

Expected: all notifier tests pass without displaying real notifications.

- [ ] **Step 5: Commit native notifier**

```bash
git add taskmgr/notifier.py scripts/notification-agent.applescript tests/test_notifier.py
git commit -m "feat: bundle native macos notifier"
```

### Task 6: Run the reminder worker with the Web server and expose APIs

**Files:**
- Modify: `taskmgr/reminders.py`
- Modify: `taskmgr/server.py:35-151,183-272`
- Modify: `tests/test_reminders.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write failing worker and server-helper tests**

Add deterministic worker tests:

```python
class WorkerTests(unittest.TestCase):
    def test_worker_scans_immediately_and_stops(self):
        called = threading.Event()
        worker = ReminderWorker(self.db, scan=lambda _: called.set(), interval_loader=lambda _: 3600)
        worker.start()
        self.assertTrue(called.wait(1))
        worker.stop()
        worker.join(1)
        self.assertFalse(worker.is_alive())

    def test_worker_contains_scan_errors(self):
        calls = []
        worker = ReminderWorker(self.db, scan=lambda _: calls.append(1) or (_ for _ in ()).throw(RuntimeError("boom")), interval_loader=lambda _: 0.01)
        worker.start()
        time.sleep(0.04)
        worker.stop()
        worker.join(1)
        self.assertGreaterEqual(len(calls), 2)
```

Extend `test_server_create_and_update_task_helpers` so `create_task` and `update_task` accept a reminders list and preserve it. Add direct handler-independent tests for `notification_status`, `setup_notification`, `test_notification`, `get_notification_settings`, and `put_notification_settings` helper functions.

- [ ] **Step 2: Verify worker/server tests fail**

```bash
conda run -n agent python -m unittest tests.test_reminders tests.test_cli
```

Expected: missing `ReminderWorker` and server helper functions.

- [ ] **Step 3: Implement worker lifecycle and endpoint helpers**

Implement `ReminderWorker(threading.Thread)` with this exact public lifecycle:

```python
class ReminderWorker(threading.Thread):
    def __init__(self, db_path: Path, *, scan=run_reminder_scan, interval_loader=None):
        super().__init__(name="taskmgr-reminders", daemon=True)
        self.db_path = Path(db_path)
        self.scan = scan
        self.interval_loader = interval_loader or (lambda path: load_settings(path)["check_interval_seconds"])
        self.stop_event = threading.Event()
        self.scan_lock = threading.Lock()

    def stop(self) -> None:
        self.stop_event.set()

    def run(self) -> None:
        while not self.stop_event.is_set():
            if self.scan_lock.acquire(blocking=False):
                try:
                    self.scan(self.db_path)
                except Exception as exc:
                    print(f"reminder worker: {exc}", file=sys.stderr)
                finally:
                    self.scan_lock.release()
            interval = max(0.01, float(self.interval_loader(self.db_path)))
            if self.stop_event.wait(interval):
                return
```

Change `serve` to this lifecycle:

```python
worker = ReminderWorker(db_path.expanduser())
worker.start()
try:
    server.serve_forever()
except KeyboardInterrupt:
    print("\nstopped")
finally:
    worker.stop()
    worker.join(timeout=5)
    server.server_close()
```

Add reminder normalization to `create_task` and `update_task`:

```python
reminders=normalize_reminders(payload.get("reminders")),
```

and:

```python
if "reminders" in payload:
    task["reminders"] = normalize_reminders(payload.get("reminders"))
```

Add these helper signatures so tests do not need a live socket:

```python
def get_notification_settings(db_path: Path) -> dict[str, Any]:
    return load_settings(db_path)


def put_notification_settings(db_path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    source = payload.get("notifications", payload)
    if not isinstance(source, dict):
        raise TaskError("notifications settings must be an object")
    return save_settings(db_path, source)


def notification_status(notifier: NativeNotifier) -> dict[str, Any]:
    return notifier.status()


def setup_notification(notifier: NativeNotifier) -> dict[str, Any]:
    notifier.setup()
    return {**notifier.status(), "submitted": True}


def test_notification(notifier: NativeNotifier, settings: dict[str, Any]) -> dict[str, Any]:
    notifier.send("task_appender 测试通知", "通知请求已由 task_appender 提交。", settings["default_sound"])
    return {"submitted": True}
```

Add `do_PUT` for `/api/settings/notifications`, GET routes for settings/status, and POST routes for setup/test. `is_loopback_client(client)` must return `ipaddress.ip_address(client).is_loopback`; setup/test return HTTP 403 otherwise.

- [ ] **Step 4: Run worker and server tests**

```bash
conda run -n agent python -m unittest tests.test_reminders tests.test_cli
```

Expected: all selected tests pass.

- [ ] **Step 5: Commit worker and APIs**

```bash
git add taskmgr/reminders.py taskmgr/server.py tests/test_reminders.py tests/test_cli.py
git commit -m "feat: run reminders with task ui"
```

### Task 7: Add reminder and settings controls to the existing Web UI

**Files:**
- Modify: `taskmgr/render.py:174-1040,1766-1828`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write failing rendered-UI assertions**

Extend the existing HTML render test:

```python
self.assertIn('id="notification-settings"', html)
self.assertIn('id="reminder-rules"', html)
self.assertIn('id="add-reminder-rule"', html)
self.assertIn("/api/settings/notifications", html)
self.assertIn("/api/notifications/setup", html)
self.assertIn("/api/notifications/test", html)
self.assertIn('data-reminders=', html)
```

Extend the server helper test so a payload with two reminder mappings survives create/update normalization.

- [ ] **Step 2: Run the HTML test and verify failure**

```bash
conda run -n agent python -m unittest tests.test_cli.CliTests.test_add_validate_render
```

Expected: missing Web control IDs.

- [ ] **Step 3: Implement the task rule editor and settings dialog**

Add a toolbar button `通知设置`, a settings backdrop/form, and this reminder editor inside the existing task form:

```html
<section class="reminder-editor" id="reminder-editor">
  <div class="reminder-heading">
    <span>截止提醒</span>
    <button type="button" id="add-reminder-rule">＋ 添加提醒</button>
  </div>
  <div id="reminder-rules"></div>
</section>
```

Add this settings form as a sibling of the task dialog:

```html
<div class="task-dialog-backdrop" id="notification-settings" hidden>
  <form class="task-dialog" id="notification-settings-form">
    <h2>通知设置</h2>
    <label><input name="enabled" type="checkbox"> 启用任务通知</label>
    <label>时区 <input name="timezone" value="Asia/Shanghai" required></label>
    <label>默认声音 <input name="default_sound" value="Glass"></label>
    <label>错过后补发窗口（分钟） <input name="missed_grace_minutes" type="number" min="0" max="1440" value="120"></label>
    <label>检查间隔（秒） <input name="check_interval_seconds" type="number" min="15" max="3600" value="60"></label>
    <p id="notification-app-status">通知 App 状态未知</p>
    <div class="dialog-actions">
      <button type="button" id="setup-notification-app">初始化通知 App</button>
      <button type="button" id="test-notification">发送测试通知</button>
      <button type="button" id="cancel-notification-settings">取消</button>
      <button type="submit" class="primary">保存</button>
    </div>
  </form>
</div>
```

Each generated row must contain `input[name="reminder_days_before"]`, `input[name="reminder_time"]`, and a remove button. Implement these exact browser helpers:

```javascript
function addReminderRow(rule) {
  const row = document.createElement("div");
  row.className = "reminder-row";
  row.innerHTML = '<label>提前天数 <input name="reminder_days_before" type="number" min="0" max="3650"></label>' +
    '<label>时间 <input name="reminder_time" type="time"></label>' +
    '<button type="button" class="remove-reminder">移除</button>';
  row.querySelector('[name="reminder_days_before"]').value = String(rule && rule.days_before != null ? rule.days_before : 0);
  row.querySelector('[name="reminder_time"]').value = String(rule && rule.time ? rule.time : "09:00");
  row.querySelector(".remove-reminder").addEventListener("click", () => row.remove());
  reminderRules.appendChild(row);
}

function collectReminders() {
  return Array.from(reminderRules.querySelectorAll(".reminder-row")).map((row) => ({
    days_before: Number(row.querySelector('[name="reminder_days_before"]').value),
    time: String(row.querySelector('[name="reminder_time"]').value),
  }));
}
```

Parse `node.dataset.reminders` as JSON when opening edit mode and include `reminders: collectReminders()` in `payloadFromForm`. Disable and clear the reminder editor when there is no due date or kind is daily.

The settings dialog loads GET settings/status on open, PUTs normalized fields on save, and calls setup/test only after `window.confirm`. Show API errors through `showStatus`; never state that a banner was displayed. Escape reminder JSON with the existing SVG attribute escape helper.

- [ ] **Step 4: Run CLI/render tests**

```bash
conda run -n agent python -m unittest tests.test_cli
```

Expected: all HTML, API helper, and existing UI tests pass.

- [ ] **Step 5: Commit Web UI controls**

```bash
git add taskmgr/render.py taskmgr/server.py tests/test_cli.py
git commit -m "feat: manage reminders in web ui"
```

### Task 8: Update startup and user documentation

**Files:**
- Modify: `start_ui.sh`
- Modify: `README.md`
- Modify: `USAGE.md`

- [ ] **Step 1: Add a startup regression assertion**

Add to `tests/test_cli.py`:

```python
def test_start_ui_uses_agent_environment(self):
    script = (Path(__file__).resolve().parents[1] / "start_ui.sh").read_text(encoding="utf-8")
    self.assertIn("conda run -n agent python -m taskmgr.cli serve", script)
    self.assertNotIn("exec python3", script)
```

- [ ] **Step 2: Run the startup test and verify failure**

```bash
conda run -n agent python -m unittest tests.test_cli.CliTests.test_start_ui_uses_agent_environment
```

Expected: assertion fails because `start_ui.sh` uses `python3`.

- [ ] **Step 3: Update startup script and documentation**

Replace the final line of `start_ui.sh` with:

```bash
exec conda run -n agent python -m taskmgr.cli serve --host "$HOST" --port "$PORT"
```

Document these exact user flows:

```text
1. Run ./start_ui.sh.
2. Open 通知设置, click 初始化通知 App, and allow macOS notification permission.
3. Click 发送测试通知; success means the request was submitted, not that a banner was necessarily visible.
4. Enable notifications and save settings.
5. Add due reminder rows in a task or use --reminder Nd@HH:MM.
6. Keep start_ui.sh running; closing it stops reminder checks.
```

Document Focus limitations, `reminders set/clear`, settings paths, the 120-minute default catch-up window, and that there is no launchd/system service installation.

- [ ] **Step 4: Run startup and documentation-adjacent tests**

```bash
conda run -n agent python -m unittest tests.test_cli
```

Expected: all CLI tests pass.

- [ ] **Step 5: Commit startup and docs**

```bash
git add start_ui.sh README.md USAGE.md tests/test_cli.py
git commit -m "docs: explain task reminder workflow"
```

### Task 9: Regenerate every dependent artifact and verify the branch

**Files:**
- Regenerate: `exports/graph.mmd`
- Regenerate: `exports/graph.dot`
- Regenerate: `exports/tasks.md`
- Regenerate: `exports/graph.html`
- Regenerate: `exports/scoreboard.html`

- [ ] **Step 1: Validate the clean-baseline task database**

```bash
conda run -n agent python -m taskmgr.cli validate
```

Expected: `valid`, with warnings allowed but no errors.

- [ ] **Step 2: Regenerate all five exports serially**

```bash
conda run -n agent python -m taskmgr.cli render --format mermaid
conda run -n agent python -m taskmgr.cli render --format dot
conda run -n agent python -m taskmgr.cli render --format markdown
conda run -n agent python -m taskmgr.cli render --format html
conda run -n agent python -m taskmgr.cli render --format scoreboard
```

Expected: each command prints its output path and all five files have fresh content. Do not run these writes in parallel.

- [ ] **Step 3: Run both required test runners**

```bash
conda run -n agent python -m unittest discover -s tests
conda run -n agent python -m pytest
```

Expected: both suites pass with zero failures.

- [ ] **Step 4: Run static consistency checks**

```bash
git diff --check
rg -n "Notification|reminder|提醒" README.md USAGE.md taskmgr tests
git status --short
```

Expected: no whitespace errors; documentation, implementation, and tests all contain the feature; only intended branch files are modified.

- [ ] **Step 5: Commit generated artifacts**

```bash
git add exports/graph.mmd exports/graph.dot exports/tasks.md exports/graph.html exports/scoreboard.html
git commit -m "chore: regenerate task graph exports"
```

- [ ] **Step 6: Review PR scope before publishing**

```bash
git log --oneline origin/main..HEAD
git diff --stat origin/main...HEAD
git diff --name-only origin/main...HEAD
```

Expected: the branch contains `.gitignore`, design/plan docs, reminder source/tests/docs, and clean-baseline exports; it does not contain the original worktree's personal `data/tasks.yaml` changes.

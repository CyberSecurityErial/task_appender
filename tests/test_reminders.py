import unittest
import tempfile
import contextlib
import io
import threading
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

from taskmgr.model import TaskError
from taskmgr.reminder_rules import format_reminders, parse_reminder_rule, validate_reminders
from taskmgr.reminders import ReminderWorker, build_occurrences, run_reminder_scan
from taskmgr.settings import load_ledger, save_ledger, save_settings


class ReminderRuleTests(unittest.TestCase):
    def test_parse_and_format_due_rules(self):
        rules = [parse_reminder_rule("1d@09:00"), parse_reminder_rule("0d@09:00")]

        self.assertEqual(
            rules,
            [
                {"days_before": 1, "time": "09:00"},
                {"days_before": 0, "time": "09:00"},
            ],
        )
        self.assertEqual(format_reminders(rules), "提前 1 天 09:00；当天 09:00")

    def test_parse_rejects_invalid_rule(self):
        with self.assertRaisesRegex(TaskError, "Nd@HH:MM"):
            parse_reminder_rule("tomorrow")

    def test_validate_rejects_duplicate_and_missing_due(self):
        duplicate = [
            {"days_before": 1, "time": "09:00"},
            {"days_before": 1, "time": "09:00"},
        ]

        self.assertIn(
            "duplicate",
            " ".join(validate_reminders("short", "2026-07-04", duplicate)),
        )
        self.assertIn(
            "requires due_at",
            " ".join(validate_reminders("short", None, duplicate[:1])),
        )

    def test_daily_task_cannot_add_due_rules(self):
        errors = validate_reminders(
            "daily", None, [{"days_before": 0, "time": "09:00"}]
        )

        self.assertIn("daily task reminders must be empty", errors)


def active_task(**updates):
    task = {
        "id": "T-0001",
        "title": "交作业",
        "kind": "short",
        "status": "todo",
        "created_at": "2026-06-01",
        "due_at": "2026-06-21",
        "priority": 3,
        "tags": [],
        "parent": None,
        "depends_on": [],
        "children": [],
        "reminders": [{"days_before": 1, "time": "09:00"}],
        "recurrence": None,
        "completed_at": None,
        "notes": "",
    }
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
        tasks = [
            active_task(),
            active_task(
                id="T-0002",
                title="每日复盘",
                kind="daily",
                due_at=None,
                reminders=[],
                recurrence={"freq": "daily", "time": "09:15"},
            ),
        ]

        events = build_occurrences(
            tasks,
            now,
            {"timezone": "Asia/Shanghai", "missed_grace_minutes": 120},
        )

        self.assertEqual([event.task_id for event in events], ["T-0001", "T-0002"])
        self.assertIn("截止 2026-06-21", events[0].message)
        self.assertIn("每日 09:15", events[1].message)

    def test_done_and_old_occurrences_are_skipped(self):
        now = datetime(2026, 6, 20, 12, 1, tzinfo=ZoneInfo("Asia/Shanghai"))
        settings = {"timezone": "Asia/Shanghai", "missed_grace_minutes": 120}

        self.assertEqual(build_occurrences([active_task(status="done")], now, settings), [])
        self.assertEqual(build_occurrences([active_task()], now, settings), [])

    def test_daily_catch_up_crosses_midnight(self):
        now = datetime(2026, 6, 21, 0, 15, tzinfo=ZoneInfo("Asia/Shanghai"))
        task = active_task(
            kind="daily",
            due_at=None,
            reminders=[],
            recurrence={"freq": "daily", "time": "23:30"},
        )

        events = build_occurrences(
            [task], now, {"timezone": "Asia/Shanghai", "missed_grace_minutes": 120}
        )

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].scheduled_at.date().isoformat(), "2026-06-20")

    def test_due_date_is_part_of_occurrence_identity(self):
        now = datetime(2026, 6, 20, 9, 30, tzinfo=ZoneInfo("Asia/Shanghai"))
        settings = {"timezone": "Asia/Shanghai", "missed_grace_minutes": 120}

        first = build_occurrences([active_task()], now, settings)[0]
        second = build_occurrences(
            [
                active_task(
                    due_at="2026-06-22",
                    reminders=[{"days_before": 2, "time": "09:00"}],
                )
            ],
            now,
            settings,
        )[0]

        self.assertNotEqual(first.key, second.key)


class ReminderScanTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.db = Path(self.tmpdir.name) / "tasks.yaml"
        self.now = datetime(2026, 6, 20, 9, 30, tzinfo=ZoneInfo("Asia/Shanghai"))
        self.write_tasks([active_task()])
        save_settings(
            self.db,
            {
                "enabled": True,
                "timezone": "Asia/Shanghai",
                "default_sound": "Glass",
                "missed_grace_minutes": 120,
                "check_interval_seconds": 60,
            },
        )

    def write_tasks(self, tasks):
        self.db.write_text(
            yaml.safe_dump({"version": 1, "next_id": 2, "tasks": tasks}, sort_keys=False),
            encoding="utf-8",
        )

    def test_success_is_deduplicated(self):
        notifier = FakeNotifier()

        first = run_reminder_scan(self.db, now=self.now, notifier=notifier)
        second = run_reminder_scan(self.db, now=self.now, notifier=notifier)

        self.assertEqual(first["sent"], 1)
        self.assertEqual(second["sent"], 0)
        self.assertEqual(len(notifier.sent), 1)
        self.assertEqual(notifier.sent[0][0], "任务提醒 · T-0001")
        self.assertEqual(notifier.sent[0][2], "Glass")

    def test_failure_retries_after_backoff(self):
        notifier = FakeNotifier(fail=True)

        run_reminder_scan(self.db, now=self.now, notifier=notifier)
        run_reminder_scan(self.db, now=self.now, notifier=notifier)
        run_reminder_scan(self.db, now=self.now.replace(minute=31), notifier=notifier)

        self.assertEqual(len(notifier.sent), 2)

    def test_completion_before_retry_suppresses_delivery(self):
        notifier = FakeNotifier(fail=True)
        run_reminder_scan(self.db, now=self.now, notifier=notifier)
        self.write_tasks([active_task(status="done", completed_at="2026-06-20")])

        run_reminder_scan(self.db, now=self.now.replace(minute=31), notifier=notifier)

        self.assertEqual(len(notifier.sent), 1)

    def test_scan_prunes_ledger_records_older_than_90_days(self):
        self.write_tasks([active_task(status="done", completed_at="2026-06-20")])
        save_ledger(
            self.db,
            {
                "events": {
                    "old": {
                        "delivered_at": "2026-01-01T09:00:00+08:00",
                        "updated_at": "2026-01-01T09:00:00+08:00",
                    }
                }
            },
        )

        run_reminder_scan(self.db, now=self.now, notifier=FakeNotifier())

        self.assertEqual(load_ledger(self.db)["events"], {})


class WorkerTests(unittest.TestCase):
    def test_worker_scans_immediately_and_stops(self):
        called = threading.Event()
        worker = ReminderWorker(
            Path("tasks.yaml"),
            scan=lambda _: called.set(),
            interval_loader=lambda _: 3600,
        )

        worker.start()
        self.assertTrue(called.wait(1))
        worker.stop()
        worker.join(1)

        self.assertFalse(worker.is_alive())

    def test_worker_contains_scan_errors(self):
        calls = []

        def failing_scan(_):
            calls.append(1)
            raise RuntimeError("boom")

        worker = ReminderWorker(
            Path("tasks.yaml"),
            scan=failing_scan,
            interval_loader=lambda _: 0.01,
        )
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            worker.start()
            time.sleep(0.04)
            worker.stop()
            worker.join(1)

        self.assertGreaterEqual(len(calls), 2)
        self.assertIn("reminder worker: boom", stderr.getvalue())

    def test_worker_survives_invalid_interval_settings(self):
        called = threading.Event()

        def invalid_interval(_):
            raise TaskError("invalid interval")

        worker = ReminderWorker(
            Path("tasks.yaml"),
            scan=lambda _: called.set(),
            interval_loader=invalid_interval,
        )
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            worker.start()
            self.assertTrue(called.wait(1))
            time.sleep(0.02)
            self.assertTrue(worker.is_alive())
            worker.stop()
            worker.join(1)

        self.assertIn("reminder worker interval", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()

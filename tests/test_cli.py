import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from taskmgr.cli import main
from taskmgr.server import (
    create_task,
    get_notification_settings,
    is_loopback_client,
    mutate_data,
    notification_status,
    put_notification_settings,
    setup_notification,
    test_notification as submit_test_notification,
    undo_last_change,
    update_task,
)
from taskmgr.store import empty_data, load_data, normalize_for_save, tasks_by_id


class CliTests(unittest.TestCase):
    def run_cli(self, *args):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = main(list(args))
        return code, stdout.getvalue(), stderr.getvalue()

    def test_add_validate_render(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Path(tmpdir) / "tasks.yaml"
            out = Path(tmpdir) / "graph.mmd"

            code, _, err = self.run_cli("--db", str(db), "add", "--kind", "long", "--title", "学习 Triton", "--tag", "triton")
            self.assertEqual(code, 0, err)

            code, _, err = self.run_cli(
                "--db",
                str(db),
                "add",
                "--kind",
                "short",
                "--title",
                "写 matmul demo",
                "--parent",
                "T-0001",
                "--due",
                "2026-05-01",
                "--reminder",
                "1d@09:00",
            )
            self.assertEqual(code, 0, err)
            self.assertTrue((Path(tmpdir) / "exports" / "scoreboard.html").exists())

            code, stdout, err = self.run_cli("--db", str(db), "validate")
            self.assertEqual(code, 0, err)
            self.assertIn("valid", stdout)

            code, _, err = self.run_cli("--db", str(db), "render", "--format", "mermaid", "--output", str(out))
            self.assertEqual(code, 0, err)
            self.assertTrue(out.exists())
            self.assertIn("flowchart", out.read_text(encoding="utf-8"))

            html_out = Path(tmpdir) / "graph.html"
            code, _, err = self.run_cli("--db", str(db), "render", "--format", "html", "--output", str(html_out))
            self.assertEqual(code, 0, err)
            html = html_out.read_text(encoding="utf-8")
            self.assertIn("<!doctype html>", html)
            self.assertIn("<svg", html)
            self.assertIn("data-task-graph-ui", html)
            self.assertIn('class="task-node"', html)
            self.assertIn("save-layout", html)
            self.assertIn("new-task", html)
            self.assertIn("task-context-menu", html)
            self.assertIn('id="notification-settings"', html)
            self.assertIn('id="notification-settings-form"', html)
            self.assertIn('id="reminder-rules"', html)
            self.assertIn('id="add-reminder-rule"', html)
            self.assertIn("/api/settings/notifications", html)
            self.assertIn("/api/notifications/setup", html)
            self.assertIn("/api/notifications/test", html)
            self.assertIn('data-reminders="', html)
            self.assertIn("学习 Triton", html)
            self.assertIn("提前 1 天 09:00", html)

            markdown_out = Path(tmpdir) / "tasks.md"
            code, _, err = self.run_cli(
                "--db", str(db), "render", "--format", "markdown", "--output", str(markdown_out)
            )
            self.assertEqual(code, 0, err)
            self.assertIn("提前 1 天 09:00", markdown_out.read_text(encoding="utf-8"))

            scoreboard_out = Path(tmpdir) / "scoreboard.html"
            code, _, err = self.run_cli("--db", str(db), "render", "--format", "scoreboard", "--output", str(scoreboard_out))
            self.assertEqual(code, 0, err)
            scoreboard = scoreboard_out.read_text(encoding="utf-8")
            self.assertIn("成长计分板", scoreboard)
            self.assertIn("任务池经验", scoreboard)
            self.assertIn("技能树", scoreboard)
            self.assertIn("等级谱注脚", scoreboard)

    def test_done_sets_completed_at_and_scoreboard(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Path(tmpdir) / "tasks.yaml"
            self.assertEqual(
                self.run_cli(
                    "--db",
                    str(db),
                    "add",
                    "--kind",
                    "short",
                    "--title",
                    "写 MuP 博客",
                    "--due",
                    "2026-05-01",
                    "--tag",
                    "blog",
                    "--tag",
                    "mup",
                )[0],
                0,
            )

            code, stdout, err = self.run_cli("--db", str(db), "done", "T-0001")

            self.assertEqual(code, 0, err)
            self.assertIn("done T-0001", stdout)
            task = tasks_by_id(load_data(db))["T-0001"]
            self.assertEqual(task["status"], "done")
            self.assertRegex(task["completed_at"], r"^\d{4}-\d{2}-\d{2}$")

            code, stdout, err = self.run_cli("--db", str(db), "scoreboard")
            self.assertEqual(code, 0, err)
            self.assertIn("Lv.", stdout)
            self.assertIn("最近收获", stdout)
            self.assertIn("星核主干", stdout)
            self.assertIn("等级谱", stdout)

    def test_add_set_and_clear_reminders(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Path(tmpdir) / "tasks.yaml"

            code, _, err = self.run_cli(
                "--db",
                str(db),
                "add",
                "--kind",
                "short",
                "--title",
                "交作业",
                "--due",
                "2026-07-04",
                "--reminder",
                "1d@09:00",
                "--reminder",
                "0d@09:00",
            )

            self.assertEqual(code, 0, err)
            self.assertEqual(
                tasks_by_id(load_data(db))["T-0001"]["reminders"],
                [
                    {"days_before": 1, "time": "09:00"},
                    {"days_before": 0, "time": "09:00"},
                ],
            )

            code, _, err = self.run_cli(
                "--db",
                str(db),
                "reminders",
                "set",
                "--task",
                "T-0001",
                "--rule",
                "2d@20:00",
            )
            self.assertEqual(code, 0, err)
            self.assertEqual(
                tasks_by_id(load_data(db))["T-0001"]["reminders"],
                [{"days_before": 2, "time": "20:00"}],
            )

            code, _, err = self.run_cli(
                "--db", str(db), "reminders", "clear", "--task", "T-0001"
            )
            self.assertEqual(code, 0, err)
            self.assertEqual(tasks_by_id(load_data(db))["T-0001"]["reminders"], [])

    def test_render_includes_reminder_summary(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Path(tmpdir) / "tasks.yaml"
            self.assertEqual(
                self.run_cli(
                    "--db",
                    str(db),
                    "add",
                    "--kind",
                    "short",
                    "--title",
                    "交作业",
                    "--due",
                    "2026-07-04",
                    "--reminder",
                    "1d@09:00",
                )[0],
                0,
            )

            markdown = (Path(tmpdir) / "exports" / "tasks.md").read_text(encoding="utf-8")
            html = (Path(tmpdir) / "exports" / "graph.html").read_text(encoding="utf-8")
            self.assertIn("提前 1 天 09:00", markdown)
            self.assertIn("提前 1 天 09:00", html)
            self.assertIn('data-reminders="', html)

    def test_reject_cycle(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Path(tmpdir) / "tasks.yaml"
            self.assertEqual(self.run_cli("--db", str(db), "add", "--kind", "short", "--title", "A", "--due", "2026-05-01")[0], 0)
            self.assertEqual(self.run_cli("--db", str(db), "add", "--kind", "short", "--title", "B", "--due", "2026-05-01")[0], 0)
            self.assertEqual(self.run_cli("--db", str(db), "link", "--task", "T-0001", "--depends-on", "T-0002")[0], 0)

            code, _, err = self.run_cli("--db", str(db), "link", "--task", "T-0002", "--depends-on", "T-0001")

            self.assertEqual(code, 2)
            self.assertIn("cycle", err)

    def test_move_rebuilds_parent_children(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Path(tmpdir) / "tasks.yaml"
            self.assertEqual(self.run_cli("--db", str(db), "add", "--kind", "long", "--title", "A")[0], 0)
            self.assertEqual(self.run_cli("--db", str(db), "add", "--kind", "long", "--title", "B")[0], 0)
            self.assertEqual(
                self.run_cli(
                    "--db",
                    str(db),
                    "add",
                    "--kind",
                    "short",
                    "--title",
                    "C",
                    "--parent",
                    "T-0001",
                    "--due",
                    "2026-05-01",
                )[0],
                0,
            )

            code, stdout, err = self.run_cli("--db", str(db), "move", "--task", "T-0003", "--parent", "T-0002")

            self.assertEqual(code, 0, err)
            self.assertIn("moved T-0003 under T-0002", stdout)
            index = tasks_by_id(load_data(db))
            self.assertEqual(index["T-0003"]["parent"], "T-0002")
            self.assertEqual(index["T-0001"]["children"], [])
            self.assertEqual(index["T-0002"]["children"], ["T-0003"])

            code, stdout, err = self.run_cli("--db", str(db), "move", "--task", "T-0003", "--root")

            self.assertEqual(code, 0, err)
            self.assertIn("moved T-0003 under root", stdout)
            index = tasks_by_id(load_data(db))
            self.assertIsNone(index["T-0003"]["parent"])
            self.assertEqual(index["T-0002"]["children"], [])

    def test_move_rejects_parent_cycle(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Path(tmpdir) / "tasks.yaml"
            self.assertEqual(self.run_cli("--db", str(db), "add", "--kind", "long", "--title", "A")[0], 0)
            self.assertEqual(self.run_cli("--db", str(db), "add", "--kind", "long", "--title", "B", "--parent", "T-0001")[0], 0)

            code, _, err = self.run_cli("--db", str(db), "move", "--task", "T-0001", "--parent", "T-0002")

            self.assertEqual(code, 2)
            self.assertIn("parent cycle", err)

    def test_sync_renders_all_exports(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Path(tmpdir) / "tasks.yaml"
            output_dir = Path(tmpdir) / "exports"
            self.assertEqual(self.run_cli("--db", str(db), "add", "--kind", "long", "--title", "A")[0], 0)

            code, stdout, err = self.run_cli("--db", str(db), "sync", "--output-dir", str(output_dir))

            self.assertEqual(code, 0, err)
            self.assertIn("graph.mmd", stdout)
            self.assertIn("graph.dot", stdout)
            self.assertIn("tasks.md", stdout)
            self.assertIn("graph.html", stdout)
            self.assertIn("scoreboard.html", stdout)
            self.assertTrue((output_dir / "graph.mmd").exists())
            self.assertTrue((output_dir / "graph.dot").exists())
            self.assertTrue((output_dir / "tasks.md").exists())
            self.assertTrue((output_dir / "graph.html").exists())
            self.assertTrue((output_dir / "scoreboard.html").exists())

    def test_apply_inbox(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Path(tmpdir) / "tasks.yaml"
            inbox = Path(tmpdir) / "TASK_INBOX.md"
            inbox.write_text(
                "- 短期任务：本周日前完成 Triton autotune demo。 #triton\n"
                "- 长期目标：系统学习 Mooncake 的 PD 分离和 KVCache 设计。 #mooncake\n"
                "- 每日任务：每天晚上 11 点整理当天学到的一个系统知识点。 #daily\n",
                encoding="utf-8",
            )

            code, stdout, err = self.run_cli("--db", str(db), "apply-inbox", str(inbox))

            self.assertEqual(code, 0, err)
            self.assertIn("created 3", stdout)
            self.assertEqual(self.run_cli("--db", str(db), "validate")[0], 0)

    def test_server_create_and_update_task_helpers(self):
        data = empty_data()

        parent = create_task(data, {"title": "父任务", "kind": "long", "status": "todo"})
        child = create_task(data, {"title": "从 UI 新建任务", "kind": "short", "status": "todo", "tags": ["ui"]})
        dependency = create_task(data, {"title": "依赖任务", "kind": "short", "status": "todo"})
        normalize_for_save(data)
        updated = update_task(
            data,
            child["id"],
            {
                "title": "从 UI 编辑任务",
                "status": "done",
                "due_at": "2026-06-01",
                "priority": 1,
                "tags": ["ui", "edit"],
                "parent": parent["id"],
                "depends_on": [dependency["id"]],
                "notes": "edited in map",
                "reminders": [{"days_before": 1, "time": "09:00"}],
            },
        )
        normalize_for_save(data)
        index = tasks_by_id(data)
        update_task(data, parent["id"], {"children": [dependency["id"]]})
        normalize_for_save(data)
        index = tasks_by_id(data)

        self.assertEqual(parent["id"], "T-0001")
        self.assertEqual(child["id"], "T-0002")
        self.assertEqual(index["T-0002"]["title"], "从 UI 编辑任务")
        self.assertEqual(updated["status"], "done")
        self.assertRegex(updated["completed_at"], r"^\d{4}-\d{2}-\d{2}$")
        self.assertEqual(index["T-0002"]["due_at"], "2026-06-01")
        self.assertEqual(index["T-0002"]["priority"], 1)
        self.assertEqual(index["T-0002"]["tags"], ["ui", "edit"])
        self.assertEqual(index["T-0002"]["depends_on"], ["T-0003"])
        self.assertEqual(index["T-0002"]["notes"], "edited in map")
        self.assertEqual(index["T-0002"]["reminders"], [{"days_before": 1, "time": "09:00"}])
        self.assertIsNone(index["T-0002"]["parent"])
        self.assertEqual(index["T-0001"]["children"], ["T-0003"])
        self.assertEqual(index["T-0003"]["parent"], "T-0001")

    def test_server_undo_restores_previous_store(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Path(tmpdir) / "tasks.yaml"
            undo_stack: list[str] = []

            mutate_data(db, lambda data: create_task(data, {"title": "UI task", "kind": "short"}), undo_stack)
            self.assertIn("UI task", db.read_text(encoding="utf-8"))

            data = undo_last_change(db, undo_stack)

            self.assertEqual(data["tasks"], [])
            self.assertEqual(load_data(db)["tasks"], [])

    def test_notification_settings_and_native_helpers(self):
        class FakeNotifier:
            def __init__(self):
                self.setup_calls = 0
                self.sent = []

            def status(self):
                return {"app_built": self.setup_calls > 0}

            def setup(self):
                self.setup_calls += 1

            def send(self, title, message, sound=""):
                self.sent.append((title, message, sound))

        with tempfile.TemporaryDirectory() as tmpdir:
            db = Path(tmpdir) / "tasks.yaml"
            saved = put_notification_settings(
                db,
                {
                    "enabled": True,
                    "timezone": "Asia/Shanghai",
                    "default_sound": "Glass",
                    "missed_grace_minutes": 120,
                    "check_interval_seconds": 60,
                },
            )
            notifier = FakeNotifier()

            self.assertEqual(get_notification_settings(db), saved)
            self.assertEqual(notification_status(notifier), {"app_built": False})
            self.assertTrue(setup_notification(notifier)["submitted"])
            self.assertTrue(submit_test_notification(notifier, saved)["submitted"])
            self.assertEqual(notifier.sent[0][2], "Glass")
            self.assertTrue(is_loopback_client("127.0.0.1"))
            self.assertTrue(is_loopback_client("::1"))
            self.assertFalse(is_loopback_client("192.0.2.1"))

    def test_start_ui_uses_agent_environment(self):
        script = (Path(__file__).resolve().parents[1] / "start_ui.sh").read_text(
            encoding="utf-8"
        )

        self.assertIn("conda run -n agent python -m taskmgr.cli serve", script)
        self.assertNotIn("exec python3", script)


if __name__ == "__main__":
    unittest.main()

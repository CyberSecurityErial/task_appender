import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from taskmgr.cli import main
from taskmgr.store import load_data, tasks_by_id


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
            self.assertIn("学习 Triton", html)

            scoreboard_out = Path(tmpdir) / "scoreboard.html"
            code, _, err = self.run_cli("--db", str(db), "render", "--format", "scoreboard", "--output", str(scoreboard_out))
            self.assertEqual(code, 0, err)
            scoreboard = scoreboard_out.read_text(encoding="utf-8")
            self.assertIn("成长计分板", scoreboard)
            self.assertIn("任务池经验", scoreboard)

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


if __name__ == "__main__":
    unittest.main()

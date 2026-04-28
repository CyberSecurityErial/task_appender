import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from taskmgr.cli import main


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

    def test_reject_cycle(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Path(tmpdir) / "tasks.yaml"
            self.assertEqual(self.run_cli("--db", str(db), "add", "--kind", "short", "--title", "A", "--due", "2026-05-01")[0], 0)
            self.assertEqual(self.run_cli("--db", str(db), "add", "--kind", "short", "--title", "B", "--due", "2026-05-01")[0], 0)
            self.assertEqual(self.run_cli("--db", str(db), "link", "--task", "T-0001", "--depends-on", "T-0002")[0], 0)

            code, _, err = self.run_cli("--db", str(db), "link", "--task", "T-0002", "--depends-on", "T-0001")

            self.assertEqual(code, 2)
            self.assertIn("cycle", err)

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

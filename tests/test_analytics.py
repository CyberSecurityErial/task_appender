import unittest

from taskmgr.analytics import build_progress


def task(task_id, title, **overrides):
    raw = {
        "id": task_id,
        "title": title,
        "kind": "short",
        "status": "todo",
        "created_at": "2026-05-01",
        "due_at": "2026-05-02",
        "priority": 3,
        "tags": [],
        "parent": None,
        "depends_on": [],
        "children": [],
        "recurrence": None,
        "completed_at": None,
        "notes": "",
    }
    raw.update(overrides)
    return raw


class AnalyticsTests(unittest.TestCase):
    def test_progress_extracts_outputs_and_gains(self):
        data = {
            "version": 1,
            "next_id": 3,
            "tasks": [
                task(
                    "T-0001",
                    "写 MuP 博客",
                    status="done",
                    tags=["blog", "mup"],
                    completed_at="2026-05-03",
                    notes="MuP 博客：整理 MuP 的核心问题、直觉和实践细节。",
                ),
                task("T-0002", "跑通 UCX demo", tags=["experiment", "ucx"], notes="准备实验记录。"),
            ],
        }

        progress = build_progress(data)

        self.assertEqual(progress["completed_tasks"], 1)
        self.assertGreater(progress["earned_xp"], 0)
        self.assertGreater(progress["available_xp"], 0)
        self.assertTrue(any(item["label"] == "博客/文章" for item in progress["artifacts"]))
        self.assertEqual(progress["gains"][0]["task_id"], "T-0001")
        self.assertIn("输出", progress["gains"][0]["gain"])


if __name__ == "__main__":
    unittest.main()

import unittest

from taskmgr.model import Task


class TaskModelTests(unittest.TestCase):
    def test_task_round_trip(self):
        task = Task(
            id="T-0001",
            title="学习 Triton",
            kind="long",
            tags=["triton", "gpu", "triton"],
            depends_on=["T-0002", "T-0002"],
            completed_at="2026-05-05",
        )

        raw = task.to_dict()
        restored = Task.from_dict(raw)

        self.assertEqual(restored.id, "T-0001")
        self.assertEqual(restored.title, "学习 Triton")
        self.assertEqual(restored.tags, ["triton", "gpu"])
        self.assertEqual(restored.depends_on, ["T-0002"])
        self.assertEqual(restored.completed_at, "2026-05-05")

    def test_legacy_task_normalizes_missing_reminders(self):
        raw = {
            "id": "T-0001",
            "title": "学习 Triton",
            "kind": "long",
            "status": "todo",
            "created_at": "2026-06-20",
        }

        normalized = Task.from_dict(raw).to_dict()

        self.assertEqual(normalized["reminders"], [])


if __name__ == "__main__":
    unittest.main()

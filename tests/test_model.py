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
        )

        raw = task.to_dict()
        restored = Task.from_dict(raw)

        self.assertEqual(restored.id, "T-0001")
        self.assertEqual(restored.title, "学习 Triton")
        self.assertEqual(restored.tags, ["triton", "gpu"])
        self.assertEqual(restored.depends_on, ["T-0002"])


if __name__ == "__main__":
    unittest.main()

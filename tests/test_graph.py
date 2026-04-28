import unittest

from taskmgr.graph import validate_data


def base_task(task_id, title, **overrides):
    task = {
        "id": task_id,
        "title": title,
        "kind": "short",
        "status": "todo",
        "created_at": "2026-04-29",
        "due_at": "2026-05-01",
        "priority": 3,
        "tags": [],
        "parent": None,
        "depends_on": [],
        "children": [],
        "recurrence": None,
        "notes": "",
    }
    task.update(overrides)
    return task


class GraphValidationTests(unittest.TestCase):
    def test_valid_parent_and_dependency_graph(self):
        data = {
            "version": 1,
            "next_id": 3,
            "tasks": [
                base_task("T-0001", "长期目标", kind="long", due_at=None, children=["T-0002"]),
                base_task("T-0002", "短期任务", parent="T-0001", depends_on=[]),
            ],
        }

        self.assertTrue(validate_data(data).ok)

    def test_reject_dependency_cycle(self):
        data = {
            "version": 1,
            "next_id": 3,
            "tasks": [
                base_task("T-0001", "A", depends_on=["T-0002"]),
                base_task("T-0002", "B", depends_on=["T-0001"]),
            ],
        }

        result = validate_data(data)

        self.assertFalse(result.ok)
        self.assertTrue(any("dependency cycle" in error for error in result.errors))

    def test_reject_missing_parent(self):
        data = {
            "version": 1,
            "next_id": 2,
            "tasks": [base_task("T-0001", "Child", parent="T-9999")],
        }

        result = validate_data(data)

        self.assertFalse(result.ok)
        self.assertTrue(any("parent does not exist" in error for error in result.errors))


if __name__ == "__main__":
    unittest.main()

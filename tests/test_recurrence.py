import unittest
from datetime import date

from taskmgr.recurrence import parse_daily_time, parse_due_text, validate_recurrence


class RecurrenceTests(unittest.TestCase):
    def test_parse_due_text(self):
        self.assertEqual(parse_due_text("本周日前完成", base=date(2026, 4, 29)), "2026-05-03")
        self.assertEqual(parse_due_text("五一前完成", base=date(2026, 4, 29)), "2026-05-01")

    def test_parse_daily_time(self):
        self.assertEqual(parse_daily_time("每天晚上 11 点复盘"), "23:00")
        self.assertEqual(parse_daily_time("每天 21:30 复盘"), "21:30")

    def test_validate_daily_recurrence(self):
        self.assertEqual(validate_recurrence("daily", {"freq": "daily", "time": "21:30"}), [])
        self.assertTrue(validate_recurrence("daily", None))


if __name__ == "__main__":
    unittest.main()

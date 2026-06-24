import json
import tempfile
import unittest
from pathlib import Path

from taskmgr.model import TaskError
from taskmgr.settings import (
    load_ledger,
    load_settings,
    save_ledger,
    save_settings,
    settings_path_for_db,
    state_path_for_db,
)


class SettingsTests(unittest.TestCase):
    def test_defaults_and_custom_database_paths(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Path(tmpdir) / "tasks.yaml"

            settings = load_settings(db)

            self.assertFalse(settings["enabled"])
            self.assertEqual(settings["timezone"], "Asia/Shanghai")
            self.assertEqual(settings["missed_grace_minutes"], 120)
            self.assertEqual(settings["check_interval_seconds"], 60)
            self.assertEqual(settings_path_for_db(db), Path(tmpdir) / "settings.yaml")
            self.assertEqual(state_path_for_db(db), Path(tmpdir) / "reminder_state.json")

    def test_save_round_trip_and_invalid_values(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Path(tmpdir) / "tasks.yaml"
            expected = {
                "enabled": True,
                "timezone": "Asia/Shanghai",
                "default_sound": "Glass",
                "missed_grace_minutes": 120,
                "check_interval_seconds": 60,
            }

            saved = save_settings(db, expected)

            self.assertEqual(saved, expected)
            self.assertEqual(load_settings(db), expected)
            with self.assertRaisesRegex(TaskError, "timezone"):
                save_settings(db, {**expected, "timezone": "Mars/Olympus"})
            with self.assertRaisesRegex(TaskError, "enabled"):
                save_settings(db, {**expected, "enabled": "yes"})
            with self.assertRaisesRegex(TaskError, "missed_grace_minutes"):
                save_settings(db, {**expected, "missed_grace_minutes": 1441})

    def test_invalid_save_preserves_last_valid_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Path(tmpdir) / "tasks.yaml"
            valid = save_settings(db, {"enabled": True})

            with self.assertRaises(TaskError):
                save_settings(db, {"timezone": "invalid"})

            self.assertEqual(load_settings(db), valid)

    def test_ledger_round_trip_is_valid_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            db = Path(tmpdir) / "tasks.yaml"
            payload = {
                "events": {
                    "key": {"delivered_at": "2026-06-20T09:00:00+08:00"}
                }
            }

            save_ledger(db, payload)

            self.assertEqual(
                load_ledger(db)["events"]["key"]["delivered_at"],
                "2026-06-20T09:00:00+08:00",
            )
            json.loads(state_path_for_db(db).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

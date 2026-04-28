from __future__ import annotations

import contextlib
import io
import shlex
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from taskmgr.cli import main
from taskmgr.graph import validate_data
from taskmgr.store import load_data


def run() -> int:
    scenarios = yaml.safe_load((ROOT / "harness" / "scenarios.yaml").read_text(encoding="utf-8"))["scenarios"]
    failures: list[str] = []
    for scenario in scenarios:
        with tempfile.TemporaryDirectory(prefix=f"taskmgr_{scenario['name']}_") as tmpdir:
            db = Path(tmpdir) / "tasks.yaml"
            failed_as_expected = False
            for command in scenario["commands"]:
                stdout = io.StringIO()
                stderr = io.StringIO()
                with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                    code = main(["--db", str(db), *shlex.split(command)])
                if code != 0:
                    expected = scenario.get("expect_error")
                    output = stdout.getvalue() + stderr.getvalue()
                    failed_as_expected = bool(expected and expected in output)
                    if not expected:
                        failures.append(f"{scenario['name']} failed command: {command}")
                    elif not failed_as_expected:
                        failures.append(f"{scenario['name']} expected error containing {expected!r}, got {output!r}")
                    break
            if scenario.get("expect_error"):
                if not failed_as_expected:
                    failures.append(f"{scenario['name']} expected an error")
                continue
            data = load_data(db)
            result = validate_data(data)
            if not result.ok:
                failures.append(f"{scenario['name']} invalid graph: {result.errors}")
            expected_count = scenario.get("expect", {}).get("task_count")
            if expected_count is not None and len(data.get("tasks", [])) != expected_count:
                failures.append(f"{scenario['name']} task_count expected {expected_count}, got {len(data.get('tasks', []))}")

    if failures:
        for failure in failures:
            print(f"FAIL {failure}")
        return 1
    print(f"PASS {len(scenarios)} scenario(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())

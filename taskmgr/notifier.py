from __future__ import annotations

import plistlib
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from .errors import TaskError
from .store import APP_ROOT


class NotificationError(TaskError):
    """Raised when the native notification adapter cannot submit a request."""


class NativeNotifier:
    def __init__(
        self,
        app_path: Path = APP_ROOT / "build" / "Notification Agent.app",
        source_path: Path = APP_ROOT / "scripts" / "notification-agent.applescript",
        osacompile: str | Path = "/usr/bin/osacompile",
        codesign: str | Path = "/usr/bin/codesign",
        open_command: str | Path = "/usr/bin/open",
    ):
        self.app_path = Path(app_path)
        self.source_path = Path(source_path)
        self.osacompile = str(osacompile)
        self.codesign = str(codesign)
        self.open_command = str(open_command)

    def status(self) -> dict[str, Any]:
        return {"app_built": self._compiled_script().is_file()}

    def setup(self) -> None:
        self._ensure_built()
        self._run_checked(
            [self.open_command, "-W", "-n", "-a", str(self.app_path)],
            "notification app setup",
        )

    def send(self, title: str, message: str, sound: str = "") -> None:
        if not title.strip():
            raise NotificationError("notification title must not be empty")
        if not message.strip():
            raise NotificationError("notification message must not be empty")
        if not self._compiled_script().is_file():
            raise NotificationError("notification app is not initialized; initialize it in notification settings")

        with tempfile.TemporaryDirectory(prefix="task-appender-notification-") as tmpdir:
            request_dir = Path(tmpdir)
            (request_dir / "title.txt").write_text(title, encoding="utf-8")
            (request_dir / "message.txt").write_text(message, encoding="utf-8")
            if sound:
                (request_dir / "sound.txt").write_text(sound, encoding="utf-8")
            self._run_checked(
                [
                    self.open_command,
                    "-W",
                    "-n",
                    "-a",
                    str(self.app_path),
                    str(request_dir),
                ],
                "notification submission",
            )

    def _ensure_built(self) -> None:
        if not self.source_path.is_file():
            raise NotificationError(f"notification app source is missing: {self.source_path}")
        compiled = self._compiled_script()
        if compiled.is_file() and compiled.stat().st_mtime >= self.source_path.stat().st_mtime:
            return
        if self.app_path.exists():
            shutil.rmtree(self.app_path)
        self.app_path.parent.mkdir(parents=True, exist_ok=True)
        self._run_checked(
            [self.osacompile, "-o", str(self.app_path), str(self.source_path)],
            "notification app compilation",
        )
        info_path = self.app_path / "Contents" / "Info.plist"
        if not info_path.is_file():
            raise NotificationError(f"compiled notification app is missing Info.plist: {info_path}")
        try:
            with info_path.open("rb") as handle:
                info = plistlib.load(handle)
            info.update(
                {
                    "CFBundleIdentifier": "local.notification.agent",
                    "CFBundleName": "Notification Agent",
                    "CFBundleDisplayName": "Notification Agent",
                }
            )
            with info_path.open("wb") as handle:
                plistlib.dump(info, handle)
        except (OSError, plistlib.InvalidFileException) as exc:
            raise NotificationError(f"notification app Info.plist could not be updated: {exc}") from exc
        self._run_checked(
            [self.codesign, "--force", "--sign", "-", str(self.app_path)],
            "notification app signing",
        )

    def _compiled_script(self) -> Path:
        return self.app_path / "Contents" / "Resources" / "Scripts" / "main.scpt"

    @staticmethod
    def _diagnostic(result: subprocess.CompletedProcess[str]) -> str:
        return (result.stderr or result.stdout or "").strip()

    def _run_checked(self, command: list[str], operation: str) -> None:
        try:
            result = subprocess.run(command, text=True, capture_output=True, check=False)
        except OSError as exc:
            raise NotificationError(f"{operation} failed: {exc}") from exc
        if result.returncode != 0:
            detail = self._diagnostic(result)
            suffix = f": {detail}" if detail else ""
            raise NotificationError(f"{operation} failed with status {result.returncode}{suffix}")

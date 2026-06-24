import plistlib
import shlex
import tempfile
import unittest
from pathlib import Path

from taskmgr.notifier import NativeNotifier, NotificationError


class NotifierTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.root = Path(self.tmpdir.name)
        self.app = self.root / "Notification Agent.app"
        self.source = self.root / "notification-agent.applescript"
        self.source.write_text("on run\nend run\n", encoding="utf-8")
        self.compile_log = self.root / "compile.log"
        self.codesign_log = self.root / "codesign.log"
        self.open_log = self.root / "open.log"
        self.open_status = self.root / "open.status"
        self.snapshot = self.root / "request-snapshot"
        self.open_status.write_text("0", encoding="utf-8")
        self.osacompile = self.make_script(
            "fake-osacompile",
            f"""#!/usr/bin/env bash
set -eu
output=""
while [[ $# -gt 0 ]]; do
  if [[ "$1" == "-o" ]]; then shift; output="$1"; fi
  shift
done
mkdir -p "$output/Contents/Resources/Scripts"
cat > "$output/Contents/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD Plist 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict><key>CFBundleIdentifier</key><string>placeholder</string></dict></plist>
PLIST
touch "$output/Contents/Resources/Scripts/main.scpt"
printf '%s\n' "$output" > {shlex.quote(str(self.compile_log))}
""",
        )
        self.codesign = self.make_script(
            "fake-codesign",
            f"#!/usr/bin/env bash\nprintf '%s\\n' \"$*\" > {shlex.quote(str(self.codesign_log))}\n",
        )
        self.open_command = self.make_script(
            "fake-open",
            f"""#!/usr/bin/env bash
set -u
printf '%s\n' "$@" > {shlex.quote(str(self.open_log))}
last=""
for value in "$@"; do last="$value"; done
if [[ -d "$last" && -f "$last/title.txt" ]]; then
  rm -rf {shlex.quote(str(self.snapshot))}
  mkdir -p {shlex.quote(str(self.snapshot))}
  cp "$last/title.txt" {shlex.quote(str(self.snapshot / 'title.txt'))}
  cp "$last/message.txt" {shlex.quote(str(self.snapshot / 'message.txt'))}
  if [[ -f "$last/sound.txt" ]]; then cp "$last/sound.txt" {shlex.quote(str(self.snapshot / 'sound.txt'))}; fi
fi
exit "$(cat {shlex.quote(str(self.open_status))})"
""",
        )

    def make_script(self, name, content):
        path = self.root / name
        path.write_text(content, encoding="utf-8")
        path.chmod(0o755)
        return path

    def make_notifier(self):
        return NativeNotifier(
            app_path=self.app,
            source_path=self.source,
            osacompile=self.osacompile,
            codesign=self.codesign,
            open_command=self.open_command,
        )

    def test_setup_builds_named_signed_app(self):
        notifier = self.make_notifier()

        notifier.setup()

        info_path = self.app / "Contents" / "Info.plist"
        info = plistlib.loads(info_path.read_bytes())
        self.assertEqual(info["CFBundleIdentifier"], "local.notification.agent")
        self.assertEqual(info["CFBundleDisplayName"], "Notification Agent")
        self.assertIn(str(self.app), self.codesign_log.read_text(encoding="utf-8"))
        self.assertTrue(notifier.status()["app_built"])

    def test_send_treats_metacharacters_as_data(self):
        notifier = self.make_notifier()
        notifier.setup()
        marker = self.root / "should-not-exist"
        message = f"Finished $HOME; $(touch {marker})"

        notifier.send('任务 "A"', message, "Glass")

        self.assertEqual((self.snapshot / "title.txt").read_text(encoding="utf-8"), '任务 "A"')
        self.assertEqual((self.snapshot / "message.txt").read_text(encoding="utf-8"), message)
        self.assertEqual((self.snapshot / "sound.txt").read_text(encoding="utf-8"), "Glass")
        self.assertFalse(marker.exists())

    def test_send_requires_initialized_app(self):
        with self.assertRaisesRegex(NotificationError, "initialize"):
            self.make_notifier().send("Title", "Message")

    def test_send_omits_sound_file_when_sound_is_empty(self):
        notifier = self.make_notifier()
        notifier.setup()

        notifier.send("Title", "Message")

        self.assertFalse((self.snapshot / "sound.txt").exists())

    def test_open_failure_is_propagated(self):
        notifier = self.make_notifier()
        notifier.setup()
        self.open_status.write_text("7", encoding="utf-8")

        with self.assertRaisesRegex(NotificationError, "status 7"):
            notifier.send("Title", "Message")


if __name__ == "__main__":
    unittest.main()

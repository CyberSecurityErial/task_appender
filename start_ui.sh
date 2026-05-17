#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8765}"

echo "Starting task_appender UI..."
echo "Open: http://${HOST}:${PORT}/"
echo "Stop: press Ctrl-C in this terminal"

exec python3 -m taskmgr.cli serve --host "$HOST" --port "$PORT"

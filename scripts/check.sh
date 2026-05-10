#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [ ! -x "$ROOT_DIR/.venv/bin/python" ]; then
  "$ROOT_DIR/scripts/bootstrap.sh"
fi

".venv/bin/python" -m codex_usage doctor
".venv/bin/python" -m compileall codex_usage
".venv/bin/python" -m unittest discover -s tests

echo "All checks passed."


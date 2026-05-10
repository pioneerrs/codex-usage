#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [ ! -x "$ROOT_DIR/.venv/bin/python" ]; then
  "$ROOT_DIR/scripts/bootstrap.sh"
fi

DEMO_DIR="$(mktemp -d "${TMPDIR:-/tmp}/codex-usage-demo.XXXXXX")"
trap 'rm -rf "$DEMO_DIR"' EXIT

cat > "$DEMO_DIR/transcript.md" <<'EOF'
<!-- codex-usage:user -->
Can you summarize this tiny repo?

<!-- codex-usage:assistant -->
This repo is a local CLI for estimating Codex subscription usage from visible transcripts.

<!-- codex-usage:tool -->
$ rg --files
README.md
codex_usage/cli.py
EOF

pushd "$DEMO_DIR" >/dev/null
"$ROOT_DIR/.venv/bin/codex-usage" init
"$ROOT_DIR/.venv/bin/codex-usage" group create "demo-run" --label demo
"$ROOT_DIR/.venv/bin/codex-usage" snapshot --group demo-run --usage 10 --note "demo start"
"$ROOT_DIR/.venv/bin/codex-usage" turn add \
  --group demo-run \
  --file transcript.md \
  --task-type simple_chat \
  --requests 1 \
  --tool-calls 1
"$ROOT_DIR/.venv/bin/codex-usage" snapshot --group demo-run --usage 10.2 --note "demo end"
"$ROOT_DIR/.venv/bin/codex-usage" report --group demo-run
"$ROOT_DIR/.venv/bin/codex-usage" export --format csv --output usage.csv
popd >/dev/null

echo
echo "Demo completed in an isolated temporary directory."


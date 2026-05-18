#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PUBLISH=0
REMOTE="${CODEX_USAGE_REMOTE:-git@github.com:crisxuan/codex-usage.git}"
PAGES_BRANCH="${CODEX_USAGE_PAGES_BRANCH:-gh-pages}"
INTERVAL_HOURS="${CODEX_USAGE_INTERVAL_HOURS:-3}"
WINDOW="${CODEX_USAGE_WINDOW:-${INTERVAL_HOURS}h}"
LANGUAGE="${CODEX_USAGE_LANG:-zh}"
MAX_SNAPSHOTS="${CODEX_USAGE_MAX_SNAPSHOTS:-240}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --publish)
      PUBLISH=1
      shift
      ;;
    --no-publish)
      PUBLISH=0
      shift
      ;;
    --remote)
      REMOTE="$2"
      shift 2
      ;;
    --pages-branch)
      PAGES_BRANCH="$2"
      shift 2
      ;;
    --interval-hours)
      INTERVAL_HOURS="$2"
      shift 2
      ;;
    --window)
      WINDOW="$2"
      shift 2
      ;;
    --lang)
      LANGUAGE="$2"
      shift 2
      ;;
    --max-snapshots)
      MAX_SNAPSHOTS="$2"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

if [[ ! -x "$ROOT_DIR/.venv/bin/python" ]]; then
  "$ROOT_DIR/scripts/bootstrap.sh"
fi

PYTHON="$ROOT_DIR/.venv/bin/python"

render_dashboard() {
  local output_dir="$1"
  mkdir -p "$output_dir/usage"
  "$PYTHON" -m codex_usage codex dashboard \
    --since "$WINDOW" \
    --lang "$LANGUAGE" \
    --interval-hours "$INTERVAL_HOURS" \
    --max-snapshots "$MAX_SNAPSHOTS" \
    --history "$output_dir/usage/hourly-history.json" \
    --output "$output_dir/usage/hourly-latest.html"
}

if [[ "$PUBLISH" != "1" ]]; then
  render_dashboard "$ROOT_DIR/docs"
  echo "Local dashboard written to $ROOT_DIR/docs/usage/hourly-latest.html"
  exit 0
fi

TMP_DIR="$(mktemp -d /tmp/codex-usage-pages.XXXXXX)"
cleanup() {
  git -C "$ROOT_DIR" worktree remove "$TMP_DIR" --force >/dev/null 2>&1 || rm -rf "$TMP_DIR"
}
trap cleanup EXIT

if git ls-remote --exit-code "$REMOTE" "refs/heads/$PAGES_BRANCH" >/dev/null 2>&1; then
  git fetch "$REMOTE" "$PAGES_BRANCH"
  git worktree add -B "$PAGES_BRANCH" "$TMP_DIR" FETCH_HEAD
else
  git worktree add --detach "$TMP_DIR" HEAD
  git -C "$TMP_DIR" switch --orphan "$PAGES_BRANCH" >/dev/null
  git -C "$TMP_DIR" rm -rf . >/dev/null 2>&1 || true
  find "$TMP_DIR" -mindepth 1 -maxdepth 1 ! -name .git -exec rm -rf {} +
fi

rsync -a --exclude "usage/hourly-history.json" "$ROOT_DIR/docs/" "$TMP_DIR/"
render_dashboard "$TMP_DIR"
touch "$TMP_DIR/.nojekyll"

git -C "$TMP_DIR" add .
if git -C "$TMP_DIR" diff --cached --quiet; then
  echo "No GitHub Pages changes to publish."
else
  git -C "$TMP_DIR" commit -m "Publish Codex usage pulse"
  git -C "$TMP_DIR" push "$REMOTE" "$PAGES_BRANCH"
fi

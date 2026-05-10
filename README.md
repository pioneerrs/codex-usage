# Codex Usage Estimator

Local CLI for estimating Codex subscription usage from visible transcripts.

This project is intentionally built so a user can ask an AI coding agent to clone it and run one command.

## AI Agent Entry Point

```bash
./run.sh
```

That command will:

- create `.venv`
- install the package in editable mode
- verify dependencies with `codex-usage doctor`
- run a complete isolated demo

Manual equivalent:

```bash
./scripts/bootstrap.sh
./scripts/demo.sh
./scripts/check.sh
```

## Human Quick Start

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/codex-usage init
.venv/bin/codex-usage group create "quick-chat"
.venv/bin/codex-usage snapshot --group quick-chat --usage 10
.venv/bin/codex-usage turn add --group quick-chat --file examples/marked-transcript.md --task-type simple_chat --requests 1
.venv/bin/codex-usage snapshot --group quick-chat --usage 10.2
.venv/bin/codex-usage report --group quick-chat
```

## What It Records

- task groups
- manual subscription usage snapshots
- visible transcript turns
- estimated user, assistant, tool, and file-context tokens
- estimated requests and tool call counts
- aggregate reports by task group, model, mode, and time window
- CSV or JSON exports

All token values are estimated from locally visible text. They are not OpenAI billing tokens or Codex internal token counts.

所有 token 数值均基于本地可见文本估算，不代表 OpenAI 账单 token 或 Codex 内部真实 token。

## Main Commands

```bash
codex-usage init
codex-usage doctor
codex-usage group create "repo-refactor" --label code
codex-usage group list
codex-usage snapshot --group repo-refactor --usage 42
codex-usage turn add --group repo-refactor --file transcript.md --task-type medium_code_task --requests 4 --tool-calls 12
codex-usage report --group repo-refactor
codex-usage report --since 7d
codex-usage export --format csv --output usage.csv
```

## Transcript Markers

```markdown
<!-- codex-usage:user -->
User text

<!-- codex-usage:assistant -->
Assistant text

<!-- codex-usage:tool -->
Tool output

<!-- codex-usage:file-context -->
Visible file context
```

If no markers are present, the whole file is treated as assistant-visible text by default.

## Storage

By default data is stored in:

```text
.codex-usage/
  groups.jsonl
  snapshots.jsonl
  turns.jsonl
  config.json
```

`.codex-usage/` is ignored by git because it may contain personal transcripts and usage notes.

## Codex Integration Direction

The intended integration model is:

```text
CLI core + Codex Skill + Codex Plugin packaging
```

The CLI is the durable open-source engine. A Codex Skill can teach Codex when and how to call the CLI, and a Plugin can package the skill, scripts, and manifest for installation.


# Codex Usage Estimator

Local CLI for Codex token usage reports.

[中文文档](README.zh-CN.md)

## Community

WeChat group:

<img src="docs/assets/wechat-group-qrcode.jpg" alt="WeChat group QR code" width="260" />

Valid until 2026-05-18.

## Run

```bash
./run.sh
```

```bash
./scripts/bootstrap.sh
./scripts/demo.sh
./scripts/check.sh
```

## Quick Start

Native Codex logs:

```bash
.venv/bin/codex-usage codex report --today
.venv/bin/codex-usage codex report --date 2026-05-10 --lang zh
.venv/bin/codex-usage codex export --date 2026-05-10 --format csv --output codex-logs.csv
```

Imported transcript estimate:

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

## Records

- Codex local `token_count` logs
- input tokens
- cached input tokens
- non-cached input tokens
- output tokens
- reasoning output tokens
- total tokens
- primary and secondary rate-limit percentages
- task groups
- manual subscription usage snapshots
- imported transcript turns
- estimated user, assistant, tool, and file-context tokens
- estimated requests and tool call counts
- aggregate reports by task group, model, mode, and time window
- CSV or JSON exports

Codex log reports use local Codex `token_count` records. Imported transcript reports are estimated from visible text.

## Commands

```bash
codex-usage codex report --today
codex-usage codex report --date 2026-05-10
codex-usage codex report --since 7d
codex-usage codex export --date 2026-05-10 --format csv --output codex-logs.csv

codex-usage init
codex-usage doctor
codex-usage group create "repo-refactor" --label code
codex-usage group list
codex-usage snapshot --group repo-refactor --usage 42
codex-usage turn add --group repo-refactor --file transcript.md --task-type medium_code_task --requests 4 --tool-calls 12
codex-usage report --group repo-refactor
codex-usage report --group repo-refactor --lang zh
codex-usage report --since 7d
codex-usage export --format csv --output usage.csv
```

## Native Codex Logs

```text
~/.codex/sessions/**/*.jsonl
~/.codex/archived_sessions/*.jsonl
```

The `codex` commands read `token_count` events from these files.

## Language

```bash
codex-usage codex report --lang auto
codex-usage codex report --lang zh
codex-usage codex report --lang en
codex-usage report --lang auto
codex-usage report --lang zh
codex-usage report --lang en
```

Set `defaultLanguage` in `.codex-usage/config.json` to `auto`, `en`, or `zh`.

`auto` follows the terminal locale. Codex/Skill integrations can pass `--lang zh` or `--lang en` from the user prompt.

## Transcript Markers

Transcript means an imported conversation or run log.

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

## Storage

```text
.codex-usage/
  groups.jsonl
  snapshots.jsonl
  turns.jsonl
  config.json
```

`.codex-usage/` is ignored by git because it may contain personal transcripts and usage notes.

## Codex Integration

- CLI core
- Codex Skill
- Codex Plugin packaging

## License

MIT

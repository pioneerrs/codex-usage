# Codex Usage Estimator

Local CLI for Codex token usage reports.

[中文文档](README.zh-CN.md)

Usage dashboard: [GitHub Pages](https://crisxuan.github.io/codex-usage/) · [rolling dashboard example](https://crisxuan.github.io/codex-usage/usage/hourly-latest.html) · [latest weekly report](https://crisxuan.github.io/codex-usage/usage/weekly-latest.html)

## Preview

<p align="center">
  <img src="docs/assets/codex-usage-summary.svg" alt="Codex usage monitor preview" width="760" />
</p>

<p align="center">
  <img src="docs/assets/codex-cost-breakdown.svg" alt="Codex cost estimate preview" width="360" />
  <img src="docs/assets/codex-session-hotspots.svg" alt="Codex cadence and privacy preview" width="360" />
</p>

<p align="center">
  <sub>Preview images use anonymized example data. Real reports come from local Codex <code>token_count</code> logs.</sub>
</p>

## Community

WeChat group:

<img src="docs/assets/wechat-group-qrcode.jpg" alt="WeChat group QR code" width="260" />

Valid until 2026-05-18.

## Requirements

- Python 3.9+
- Codex local session logs

## Run

macOS, Linux, or WSL:

```bash
./run.sh
```

Windows PowerShell:

```powershell
.\run.ps1
```

If PowerShell blocks local scripts:

```powershell
powershell -ExecutionPolicy Bypass -File .\run.ps1
```

Manual setup:

```bash
./scripts/bootstrap.sh
./scripts/demo.sh
./scripts/check.sh
```

```powershell
.\scripts\bootstrap.ps1
.\scripts\demo.ps1
.\scripts\check.ps1
```

## Quick Start

Native Codex logs:

```bash
.venv/bin/codex-usage codex report --today
.venv/bin/codex-usage codex summary --today
.venv/bin/codex-usage codex chart --today --output usage.html
.venv/bin/codex-usage codex cost --today
.venv/bin/codex-usage codex cost-chart --today --output cost.html
.venv/bin/codex-usage codex report --date 2026-05-10 --lang zh
.venv/bin/codex-usage codex export --date 2026-05-10 --format csv --output codex-logs.csv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\codex-usage.exe codex report --today
.\.venv\Scripts\codex-usage.exe codex summary --today
.\.venv\Scripts\codex-usage.exe codex chart --today --output usage.html
.\.venv\Scripts\codex-usage.exe codex cost --today
.\.venv\Scripts\codex-usage.exe codex cost-chart --today --output cost.html
.\.venv\Scripts\codex-usage.exe codex report --date 2026-05-10 --lang zh
.\.venv\Scripts\codex-usage.exe codex export --date 2026-05-10 --format csv --output codex-logs.csv
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

Windows PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\codex-usage.exe init
.\.venv\Scripts\codex-usage.exe group create "quick-chat"
.\.venv\Scripts\codex-usage.exe snapshot --group quick-chat --usage 10
.\.venv\Scripts\codex-usage.exe turn add --group quick-chat --file examples\marked-transcript.md --task-type simple_chat --requests 1
.\.venv\Scripts\codex-usage.exe snapshot --group quick-chat --usage 10.2
.\.venv\Scripts\codex-usage.exe report --group quick-chat
```

## Records

- Codex local `token_count` logs
- input tokens
- cached input tokens
- non-cached input tokens
- output tokens
- reasoning output tokens
- total tokens
- primary and secondary used / remaining rate-limit percentages
- API-equivalent cost estimate
- Codex credits equivalent estimate
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
codex-usage codex summary --today
codex-usage codex report --date 2026-05-10
codex-usage codex report --since 7d
codex-usage codex chart --today --output usage.html
codex-usage codex cost --today
codex-usage codex cost-chart --today --output cost.html
codex-usage codex dashboard --since 3h --lang zh --output docs/usage/hourly-latest.html
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

macOS, Linux, or WSL:

```text
~/.codex/sessions/**/*.jsonl
~/.codex/archived_sessions/*.jsonl
```

Windows:

```text
%USERPROFILE%\.codex\sessions\**\*.jsonl
%USERPROFILE%\.codex\archived_sessions\*.jsonl
```

The `codex` commands read `token_count` events from these files.

If your Codex home is elsewhere:

```bash
codex-usage codex report --today --codex-home /path/to/.codex
```

```powershell
.\.venv\Scripts\codex-usage.exe codex report --today --codex-home "C:\Users\you\.codex"
```

## Charts

```bash
codex-usage codex summary --today
codex-usage codex chart --today --lang zh --output usage.html
codex-usage codex chart --date 2026-05-10 --output usage.html
codex-usage codex cost-chart --today --output cost.html
```

The chart command writes a static HTML file with inline SVG charts. It does not require Node.js, a browser server, or external CDN assets.

`summary` prints token, cost, rate-limit, and hot-session highlights and writes `codex-usage.html` plus `codex-cost.html` by default. Terminal-only output:

```bash
codex-usage codex summary --today --no-charts
```

Rolling dashboard snapshots:

```bash
codex-usage codex dashboard --since 3h --lang zh --history docs/usage/hourly-history.json --output docs/usage/hourly-latest.html
scripts/publish_usage_dashboard.sh --publish
```

The dashboard interval is configurable. The public GitHub Pages site in this repository is only my 3-hour example; use `--since`, `--interval-hours`, or `CODEX_USAGE_INTERVAL_HOURS` to publish your own daily, hourly, or custom cadence.

The dashboard keeps a public JSON history of aggregate snapshots and renders a static GitHub Pages view. It does not include local paths, full session names, or raw Codex logs.

## Cost Estimates

```bash
codex-usage codex cost --today
codex-usage codex cost --today --json
codex-usage codex cost-chart --today --output cost.html
```

Cost estimates default to a GPT-5.5-style rate card:

```text
non-cached input: $5 / 1M tokens
cached input: $0.5 / 1M tokens
output: $30 / 1M tokens
Codex credits: 25 credits / $1
```

Override rates when the model or rate card changes:

```bash
codex-usage codex cost --today \
  --input-rate 5 \
  --cached-input-rate 0.5 \
  --output-rate 30 \
  --credits-per-usd 25
```

Cost output is an API-equivalent estimate from local Codex `token_count` logs, not a subscription bill. Reasoning tokens are displayed for context and are already included in output tokens, so they are not billed again.

## Troubleshooting

PowerShell script blocked:

```powershell
powershell -ExecutionPolicy Bypass -File .\run.ps1
```

Python not found on Windows:

```powershell
$env:PYTHON = "C:\Path\To\python.exe"
.\run.ps1
```

No Codex records found:

```bash
codex-usage doctor
codex-usage codex report --today --codex-home /path/to/.codex
```

```powershell
.\.venv\Scripts\codex-usage.exe doctor
.\.venv\Scripts\codex-usage.exe codex report --today --codex-home "C:\Users\you\.codex"
```

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

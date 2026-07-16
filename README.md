# Codex Usage Estimator

Local CLI for Codex token usage reports.

[中文文档](README.zh-CN.md)

## Preview

<p align="center">
  <img src="docs/assets/codex-usage-summary.svg" alt="Codex usage summary preview" width="860" />
</p>

<p align="center">
  <img src="docs/assets/codex-cost-breakdown.svg" alt="Codex cost breakdown preview" width="420" />
  <img src="docs/assets/codex-session-hotspots.svg" alt="Codex hot sessions preview" width="420" />
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

The repository enforces LF line endings for shell and Python launchers so a Windows checkout remains executable from WSL.

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
- primary and secondary rate-limit percentages
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

The `codex` commands read `session_meta`, `turn_context` model fields, `token_count`, and `rate_limits` from these files. Token deltas follow file line order; timestamps only select the reporting window and timeline bucket. Counter resets begin a new cumulative segment, while component-only regressions are clamped and audited.

Forked sessions can contain a copied prefix of the parent's cumulative counters. A fork is `resolved` only when at least two consecutive child usage snapshots form a suffix of the parent's usage sequence and reach the fork-time baseline. Smaller first counters are `not_replayed`; incomplete evidence is `ambiguous`; missing parents or baselines are `unresolved`. Existing token and cost fields are the inclusive upper estimate. Additive `verifiedUsage` / verified-cost fields provide the confirmed lower estimate, and `unverifiedUsage` is their non-negative difference. Damaged statistical JSONL lines and invalid token events in files relevant to the selected window are skipped, counted, and shown as data-quality warnings without exposing line contents.

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

`summary` prints inclusive, verified, and unverified token/cost totals plus rate-limit and hot-session highlights. It writes usage and cost charts to the `output/` directory by default. Files include the period, generation timestamp, and a unique suffix to prevent overwriting (for example, `codex-usage-0716-20260717-103000-123456-a1b2c3d4.html`). Terminal-only output:

```bash
codex-usage codex summary --today --no-charts
```

**Output Directory**: All HTML charts are saved to the `output/` directory by default. Each file includes a timestamp in its filename to prevent overwriting previous results. You can still specify a custom output path with the `--output` flag.

## Cost Estimates

```bash
codex-usage codex cost --today
codex-usage codex cost --today --json
codex-usage codex cost-chart --today --output cost.html
```

When model tracking is available, cost estimates use these API-equivalent rate cards (non-cached input / cached input / output, USD per 1M tokens):

```text
gpt-5.6, gpt-5.6-sol:  $5 / $0.5 / $30
gpt-5.6-terra:         $2.5 / $0.25 / $15
gpt-5.6-luna:          $1 / $0.1 / $6
gpt-5.3-codex:         $1.75 / $0.175 / $14
gpt-5.2:               $1.75 / $0.175 / $14
Codex Credits = API-equivalent USD x 25
```

`gpt-5.3-codex-spark` is treated as unpriced and uses the GPT-5.5 fallback with a warning; other unknown models use the same fallback. `codex-auto-review` keeps the repository-internal rate card and is labeled accordingly. JSON exposes `rateCardStatus`, `rateCardSource`, and `rateCardAsOf`; `--flat-rate` is labeled `user-supplied`.

Use `--flat-rate` with the rate flags to override per-model pricing:

```bash
codex-usage codex cost --today \
  --input-rate 5 \
  --cached-input-rate 0.5 \
  --output-rate 30 \
  --credits-per-usd 25
```

These are four separate metrics: token usage is the local log count; API-equivalent USD applies the table above; Codex Credits are an equivalent conversion using `--credits-per-usd` (default `25`); subscription limits are the observed primary/secondary percentages. Inclusive, verified, and unverified Credits always equal their corresponding USD value times `creditsPerUSD`. Neither USD nor Credits is a subscription bill. Reasoning tokens are already included in output tokens and are not billed again. The estimator intentionally does not apply API-only long-context, Priority, or Fast-mode multipliers.

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

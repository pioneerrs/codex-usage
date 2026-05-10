# AI Agent Quick Start

## First Command

```bash
./run.sh
```

## Useful Commands

```bash
./scripts/bootstrap.sh
./scripts/demo.sh
./scripts/check.sh
.venv/bin/codex-usage codex report --today
.venv/bin/codex-usage codex report --today --lang zh
.venv/bin/codex-usage --help
```

## Language

When reporting usage for a user, match the user's prompt language:

- Chinese prompt: pass `--lang zh`.
- English prompt: pass `--lang en`.
- Explicit language request: follow the requested language.
- No prompt context: use `--lang auto`.

## Real User Data

Real usage data lives in `.codex-usage/`. It is ignored by git. Do not delete or overwrite it unless the user explicitly asks.

Create a fresh local usage database:

```bash
.venv/bin/codex-usage init
```

## What This Tool Can and Cannot Do

Reads Codex local `token_count` logs.

Estimates imported transcript usage from locally visible text.

Does not read hidden prompts or subscription billing internals.

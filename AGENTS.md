# AI Agent Quick Start

This repo is designed to be cloned and run by coding agents with minimal context.

## First Command

Run this from the repository root:

```bash
./run.sh
```

It creates `.venv`, installs the package in editable mode, runs a dependency doctor, and executes an isolated demo in a temporary directory.

## Useful Commands

```bash
./scripts/bootstrap.sh
./scripts/demo.sh
./scripts/check.sh
.venv/bin/codex-usage --help
```

## Real User Data

Real usage data lives in `.codex-usage/` and is intentionally ignored by git. Do not delete or overwrite it unless the user explicitly asks.

For a fresh local usage database:

```bash
.venv/bin/codex-usage init
```

## What This Tool Can and Cannot Do

It estimates token usage from locally visible text. It does not read Codex internal token counts, hidden prompts, reasoning tokens, or subscription billing internals.


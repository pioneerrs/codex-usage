# Codex Usage Estimator

Codex token 用量统计命令行工具。

[English](README.md)

## 运行

```bash
./run.sh
```

```bash
./scripts/bootstrap.sh
./scripts/demo.sh
./scripts/check.sh
```

## 快速开始

Codex 本地日志：

```bash
.venv/bin/codex-usage codex report --today
.venv/bin/codex-usage codex report --date 2026-05-10 --lang zh
.venv/bin/codex-usage codex export --date 2026-05-10 --format csv --output codex-logs.csv
```

导入对话记录估算：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
.venv/bin/codex-usage init
.venv/bin/codex-usage group create "quick-chat"
.venv/bin/codex-usage snapshot --group quick-chat --usage 10
.venv/bin/codex-usage turn add --group quick-chat --file examples/marked-transcript.md --task-type simple_chat --requests 1
.venv/bin/codex-usage snapshot --group quick-chat --usage 10.2
.venv/bin/codex-usage report --group quick-chat --lang zh
```

## 记录内容

- Codex 本地 `token_count` 日志
- input tokens
- cached input tokens
- non-cached input tokens
- output tokens
- reasoning output tokens
- total tokens
- primary / secondary 限额百分比
- 任务组
- 手动订阅用量快照
- 导入的对话记录 turn
- 用户、助手、工具、文件上下文的 estimated token
- 估算请求数和工具调用次数
- 按任务组、模型、执行模式、时间窗口汇总的报告
- CSV 或 JSON 导出

Codex 日志报告读取本地 `token_count` 记录。导入对话记录报告基于可见文本估算。

## 常用命令

```bash
codex-usage codex report --today
codex-usage codex report --date 2026-05-10 --lang zh
codex-usage codex report --since 7d --lang zh
codex-usage codex export --date 2026-05-10 --format csv --output codex-logs.csv

codex-usage init
codex-usage doctor
codex-usage group create "repo-refactor" --label code
codex-usage group list
codex-usage snapshot --group repo-refactor --usage 42
codex-usage turn add --group repo-refactor --file transcript.md --task-type medium_code_task --requests 4 --tool-calls 12
codex-usage report --group repo-refactor --lang zh
codex-usage report --since 7d --lang zh
codex-usage export --format csv --output usage.csv
```

## Codex 本地日志

```text
~/.codex/sessions/**/*.jsonl
~/.codex/archived_sessions/*.jsonl
```

`codex` 命令会读取这些文件里的 `token_count` 事件。

## 语言切换

```bash
codex-usage codex report --lang auto
codex-usage codex report --lang zh
codex-usage codex report --lang en
codex-usage report --lang auto
codex-usage report --lang zh
codex-usage report --lang en
```

在 `.codex-usage/config.json` 中可设置 `defaultLanguage` 为 `auto`、`en` 或 `zh`。

`auto` 跟随终端 locale。Codex/Skill 集成可以根据用户提示传入 `--lang zh` 或 `--lang en`。

## Transcript 标记

Transcript 指导入的对话记录或运行日志。

```markdown
<!-- codex-usage:user -->
用户文本

<!-- codex-usage:assistant -->
助手文本

<!-- codex-usage:tool -->
工具输出

<!-- codex-usage:file-context -->
可见文件上下文
```

## 存储

```text
.codex-usage/
  groups.jsonl
  snapshots.jsonl
  turns.jsonl
  config.json
```

`.codex-usage/` 会被 git 忽略，因为它可能包含个人 transcript 和用量备注。

## Codex 集成

- CLI core
- Codex Skill
- Codex Plugin packaging

## License

MIT

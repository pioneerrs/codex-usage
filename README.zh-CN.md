# Codex Usage Estimator

基于本地可见 transcript 估算 Codex 订阅用量的命令行工具。

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

- 任务组
- 手动订阅用量快照
- 可见 transcript turn
- 用户、助手、工具、文件上下文的 estimated token
- 估算请求数和工具调用次数
- 按任务组、模型、执行模式、时间窗口汇总的报告
- CSV 或 JSON 导出

所有 token 数值均基于本地可见文本估算，不代表 OpenAI 账单 token 或 Codex 内部真实 token。

## 常用命令

```bash
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

## 语言切换

```bash
codex-usage report --lang zh
```

在 `.codex-usage/config.json` 中可设置 `defaultLanguage` 为 `en` 或 `zh`。

## Transcript 标记

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

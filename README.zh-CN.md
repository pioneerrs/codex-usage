# Codex Usage Estimator

基于本地可见 transcript 估算 Codex 订阅用量的命令行工具。

[English](README.md)

这个项目特意做成了适合 AI coding agent 拉取并一条命令跑起来的形态。

## AI Agent 入口

```bash
./run.sh
```

这个命令会：

- 创建 `.venv`
- 以 editable 模式安装项目
- 通过 `codex-usage doctor` 检查依赖
- 在临时目录里跑完整 demo

等价的手动命令：

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

报告默认输出英文。使用 `--lang zh` 输出中文：

```bash
codex-usage report --lang zh
```

也可以在 `.codex-usage/config.json` 中把 `defaultLanguage` 设置成 `en` 或 `zh`。

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

如果没有标记，整份文件默认作为助手可见文本处理。

## 存储

默认数据目录：

```text
.codex-usage/
  groups.jsonl
  snapshots.jsonl
  turns.jsonl
  config.json
```

`.codex-usage/` 会被 git 忽略，因为它可能包含个人 transcript 和用量备注。

## Codex 集成方向

推荐集成模型：

```text
CLI core + Codex Skill + Codex Plugin packaging
```

CLI 是稳定的开源核心。Codex Skill 可以告诉 Codex 什么时候、如何调用这个 CLI；Plugin 可以打包 skill、脚本和 manifest，方便安装。

## License

MIT


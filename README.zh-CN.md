# Codex Usage Estimator

Codex token 用量统计命令行工具。

[English](README.md)

## 统计预览

<p align="center">
  <img src="docs/assets/codex-usage-summary.svg" alt="Codex 用量统计预览" width="860" />
</p>

<p align="center">
  <img src="docs/assets/codex-cost-breakdown.svg" alt="Codex 费用拆分预览" width="420" />
  <img src="docs/assets/codex-session-hotspots.svg" alt="Codex 高消耗 session 预览" width="420" />
</p>

<p align="center">
  <sub>图中是匿名示例数据。实际报告由本机 Codex <code>token_count</code> 日志生成。</sub>
</p>

## 交流群

微信群：

<img src="docs/assets/wechat-group-qrcode.jpg" alt="微信群二维码" width="260" />

有效期至 2026-05-18。

## 环境要求

- Python 3.9+
- 本机已有 Codex session 日志

## 运行

macOS、Linux 或 WSL：

```bash
./run.sh
```

仓库通过 `.gitattributes` 强制 shell 和 Python launcher 使用 LF，因此 Windows checkout 也可以直接从 WSL 执行。

Windows PowerShell：

```powershell
.\run.ps1
```

如果 PowerShell 阻止本地脚本：

```powershell
powershell -ExecutionPolicy Bypass -File .\run.ps1
```

手动执行：

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

## 快速开始

Codex 本地日志：

```bash
.venv/bin/codex-usage codex report --today
.venv/bin/codex-usage codex summary --today --lang zh
.venv/bin/codex-usage codex chart --today --lang zh --output usage.html
.venv/bin/codex-usage codex cost --today --lang zh
.venv/bin/codex-usage codex cost-chart --today --lang zh --output cost.html
.venv/bin/codex-usage codex report --date 2026-05-10 --lang zh
.venv/bin/codex-usage codex export --date 2026-05-10 --format csv --output codex-logs.csv
```

Windows PowerShell：

```powershell
.\.venv\Scripts\codex-usage.exe codex report --today --lang zh
.\.venv\Scripts\codex-usage.exe codex summary --today --lang zh
.\.venv\Scripts\codex-usage.exe codex chart --today --lang zh --output usage.html
.\.venv\Scripts\codex-usage.exe codex cost --today --lang zh
.\.venv\Scripts\codex-usage.exe codex cost-chart --today --lang zh --output cost.html
.\.venv\Scripts\codex-usage.exe codex report --date 2026-05-10 --lang zh
.\.venv\Scripts\codex-usage.exe codex export --date 2026-05-10 --format csv --output codex-logs.csv
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

Windows PowerShell：

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\codex-usage.exe init
.\.venv\Scripts\codex-usage.exe group create "quick-chat"
.\.venv\Scripts\codex-usage.exe snapshot --group quick-chat --usage 10
.\.venv\Scripts\codex-usage.exe turn add --group quick-chat --file examples\marked-transcript.md --task-type simple_chat --requests 1
.\.venv\Scripts\codex-usage.exe snapshot --group quick-chat --usage 10.2
.\.venv\Scripts\codex-usage.exe report --group quick-chat --lang zh
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
- API 等价费用估算
- Codex credits 等价估算
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
codex-usage codex summary --today --lang zh
codex-usage codex report --date 2026-05-10 --lang zh
codex-usage codex report --since 7d --lang zh
codex-usage codex chart --today --lang zh --output usage.html
codex-usage codex cost --today --lang zh
codex-usage codex cost-chart --today --lang zh --output cost.html
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

macOS、Linux 或 WSL：

```text
~/.codex/sessions/**/*.jsonl
~/.codex/archived_sessions/*.jsonl
```

Windows：

```text
%USERPROFILE%\.codex\sessions\**\*.jsonl
%USERPROFILE%\.codex\archived_sessions\*.jsonl
```

`codex` 命令只读取这些文件里的 `session_meta`、`turn_context` 模型字段、`token_count` 和 `rate_limits`。Token 差值严格按文件行号顺序计算；时间戳只用于时间窗口筛选和 timeline 分桶。累计总数回退会开始一个新计数段，只有组件回退则钳为 0 并计入审计字段。

Fork 子会话可能复制父会话的累计计数器前缀。只有至少两个连续子 usage 快照构成父 usage 序列的后缀并抵达 fork 时刻 baseline，才标记为 `resolved`。首个计数明显较小时标记 `not_replayed`，证据不完整时标记 `ambiguous`，父日志或 baseline 缺失时标记 `unresolved`。原有 token 和费用字段继续表示 inclusive 上限；新增 `verifiedUsage` / verified 费用表示已确认下限，`unverifiedUsage` 表示两者的非负差额。与所选窗口有关的文件中，损坏的统计 JSONL 行和无效 token 事件会被跳过、计数并显示数据质量警告，不会输出原始行内容。

如果 Codex home 不在默认位置：

```bash
codex-usage codex report --today --codex-home /path/to/.codex
```

```powershell
.\.venv\Scripts\codex-usage.exe codex report --today --lang zh --codex-home "C:\Users\you\.codex"
```

## 图表

```bash
codex-usage codex summary --today --lang zh
codex-usage codex chart --today --lang zh --output usage.html
codex-usage codex chart --date 2026-05-10 --lang zh --output usage.html
codex-usage codex cost-chart --today --lang zh --output cost.html
```

图表命令会生成一个静态 HTML 文件，图表使用内联 SVG，不需要 Node.js、浏览器服务或外部 CDN。

`summary` 会同时输出 Inclusive、Verified、Unverified token/费用、限额和重点 session，并默认将图表保存到 `output/` 目录。文件名包含统计周期、生成时间和唯一后缀以防止覆盖（例如 `codex-usage-0716-20260717-103000-123456-a1b2c3d4.html`）。如果只想看终端报告：

```bash
codex-usage codex summary --today --lang zh --no-charts
```

**输出目录**：所有 HTML 图表默认保存到 `output/` 目录。每个文件名都包含时间戳，防止覆盖之前的结果。你仍然可以使用 `--output` 参数指定自定义输出路径。

## 费用估算

```bash
codex-usage codex cost --today --lang zh
codex-usage codex cost --today --lang zh --json
codex-usage codex cost-chart --today --lang zh --output cost.html
```

能够追踪模型时，费用估算会使用以下 API 等价费率（依次为非缓存 input / cached input / output，单位为每百万 token 的美元）：

```text
gpt-6-astra:           $10 / $1 / $50
gpt-5.6、gpt-5.6-sol: $4 / $0.4 / $20
gpt-5.6-terra:        $2 / $0.2 / $12
gpt-5.6-luna:         $0.2 / $0.02 / $1.2
gpt-5.3-codex:        $1.75 / $0.175 / $14
gpt-5.2:              $1.75 / $0.175 / $14
Codex Credits = API 等价美元 x 25
```

`gpt-5.3-codex-spark` 当前按“未定价”处理，回退到 GPT-5.5 并发出警告；其他未知模型也使用 GPT-5.5 fallback。`codex-auto-review` 保留仓库内部费率并明确标记来源。JSON 会输出 `rateCardStatus`、`rateCardSource`、`rateCardAsOf`；`--flat-rate` 标记为 `user-supplied`。

需要统一覆盖所有模型费率时，使用 `--flat-rate` 和以下参数：

```bash
codex-usage codex cost --today \
  --input-rate 5 \
  --cached-input-rate 0.5 \
  --output-rate 30 \
  --credits-per-usd 25
```

这里有四种不同指标：token 用量是本地日志计数；API 等价美元按上表换算；Codex Credits 按 `--credits-per-usd` 换算（默认 `25`）；订阅限额则是日志中观察到的 primary / secondary 百分比。Inclusive、Verified、Unverified Credits 都严格等于对应美元值乘以 `creditsPerUSD`。美元和 Credits 都不代表订阅真实账单。Reasoning token 已包含在 output 中，不重复计费。本工具有意不实现仅适用于 API 的长上下文、Priority 或 Fast 模式倍率。

## 常见问题

PowerShell 阻止脚本：

```powershell
powershell -ExecutionPolicy Bypass -File .\run.ps1
```

Windows 找不到 Python：

```powershell
$env:PYTHON = "C:\Path\To\python.exe"
.\run.ps1
```

没有找到 Codex 记录：

```bash
codex-usage doctor
codex-usage codex report --today --codex-home /path/to/.codex
```

```powershell
.\.venv\Scripts\codex-usage.exe doctor
.\.venv\Scripts\codex-usage.exe codex report --today --lang zh --codex-home "C:\Users\you\.codex"
```

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

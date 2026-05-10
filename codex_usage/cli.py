from __future__ import annotations

import argparse
import sys
import uuid
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .codex_logs import (
    aggregate_codex_logs,
    default_codex_home,
    discover_session_files,
    export_codex_report,
    render_codex_report,
    resolve_time_window as resolve_codex_time_window,
)
from .errors import UsageError
from .reporting import (
    TEXT,
    aggregate_breakdown,
    aggregate_rows,
    export_rows,
    filter_turns,
    normalize_lang,
    render_breakdown,
    render_report,
)
from .storage import (
    append_group,
    append_snapshot,
    append_turn,
    find_group,
    init_storage,
    load_config,
    load_groups,
    load_snapshots,
    load_turns,
    now_iso,
    storage_dir_from,
)
from .tokens import count_tokens
from .transcript import parse_transcript


TASK_TYPES = (
    "simple_chat",
    "small_code_change",
    "medium_code_task",
    "large_repo_task",
    "long_running_agent",
    "unknown",
)
MODES = ("local", "cloud", "unknown")
SNAPSHOT_SOURCES = ("manual", "screenshot", "dom", "log")
KINDS = ("user", "assistant", "tool", "file-context", "mixed")


def entrypoint() -> None:
    sys.exit(main())


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.func(args)
    except UsageError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="codex-usage",
        description="Estimate Codex subscription usage from locally visible transcripts.",
    )
    parser.add_argument(
        "--data-dir",
        help="Storage directory. Defaults to .codex-usage or CODEX_USAGE_DIR.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Initialize local JSONL storage.")
    init_parser.set_defaults(func=cmd_init)

    doctor_parser = subparsers.add_parser("doctor", help="Check runtime dependencies and storage status.")
    doctor_parser.set_defaults(func=cmd_doctor)

    group_parser = subparsers.add_parser("group", help="Manage task groups.")
    group_subparsers = group_parser.add_subparsers(dest="group_command", required=True)
    group_create = group_subparsers.add_parser("create", help="Create a task group.")
    group_create.add_argument("name")
    group_create.add_argument("--description")
    group_create.add_argument("--label", action="append", default=[])
    group_create.set_defaults(func=cmd_group_create)

    group_list = group_subparsers.add_parser("list", help="List task groups.")
    group_list.set_defaults(func=cmd_group_list)

    snapshot = subparsers.add_parser("snapshot", help="Record a subscription usage snapshot.")
    snapshot.add_argument("--group", required=True, help="Task group name or id.")
    snapshot.add_argument("--usage", type=float, help="Used subscription percentage.")
    snapshot.add_argument("--remaining", type=float, help="Remaining subscription percentage.")
    snapshot.add_argument("--source", choices=SNAPSHOT_SOURCES, default="manual")
    snapshot.add_argument("--note")
    snapshot.set_defaults(func=cmd_snapshot)

    turn = subparsers.add_parser("turn", help="Manage turn records.")
    turn_subparsers = turn.add_subparsers(dest="turn_command", required=True)
    turn_add = turn_subparsers.add_parser("add", help="Import a transcript or visible log as a turn.")
    turn_add.add_argument("--group", required=True, help="Task group name or id.")
    input_group = turn_add.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--file", help="Path to transcript or log file.")
    input_group.add_argument("--stdin", action="store_true", help="Read transcript from stdin.")
    turn_add.add_argument("--kind", choices=KINDS, default="mixed")
    turn_add.add_argument("--model")
    turn_add.add_argument("--mode", choices=MODES)
    turn_add.add_argument("--task-type", choices=TASK_TYPES, default="unknown")
    turn_add.add_argument("--requests", type=int, default=1)
    turn_add.add_argument("--tool-calls", type=int, default=0)
    turn_add.set_defaults(func=cmd_turn_add)

    report = subparsers.add_parser("report", help="Print an estimated usage report.")
    add_report_filters(report)
    report.add_argument(
        "--breakdown",
        choices=("none", "model", "mode", "all"),
        default="none",
        help="Optional extra aggregation breakdown.",
    )
    report.set_defaults(func=cmd_report)

    export = subparsers.add_parser("export", help="Export aggregated usage data.")
    add_report_filters(export, include_lang=False)
    export.add_argument("--format", choices=("csv", "json"), default="csv")
    export.add_argument("--output", required=True)
    export.set_defaults(func=cmd_export)

    codex = subparsers.add_parser("codex", help="Report native Codex local session logs.")
    codex_subparsers = codex.add_subparsers(dest="codex_command", required=True)
    codex_report = codex_subparsers.add_parser("report", help="Print usage from Codex token_count logs.")
    add_codex_log_filters(codex_report)
    codex_report.set_defaults(func=cmd_codex_report)

    codex_export = codex_subparsers.add_parser("export", help="Export usage from Codex token_count logs.")
    add_codex_log_filters(codex_export, include_lang=False)
    codex_export.add_argument("--format", choices=("csv", "json"), default="csv")
    codex_export.add_argument("--output", required=True)
    codex_export.set_defaults(func=cmd_codex_export)

    return parser


def add_report_filters(parser: argparse.ArgumentParser, include_lang: bool = True) -> None:
    parser.add_argument("--group", help="Task group name or id.")
    parser.add_argument("--since", help='Relative time filter, such as "7d", "12h", or "30m".')
    parser.add_argument("--from", dest="from_value", help="Start date, YYYY-MM-DD or ISO timestamp.")
    parser.add_argument("--to", dest="to_value", help="End date, YYYY-MM-DD or ISO timestamp.")
    parser.add_argument("--model", help="Only include turns for this model.")
    parser.add_argument("--mode", choices=MODES, help="Only include turns for this execution mode.")
    if include_lang:
        parser.add_argument(
            "--lang",
            choices=("auto", "en", "zh"),
            help="Output language. Defaults to config defaultLanguage; auto follows locale.",
        )


def add_codex_log_filters(parser: argparse.ArgumentParser, include_lang: bool = True) -> None:
    date_group = parser.add_mutually_exclusive_group()
    date_group.add_argument("--today", action="store_true", help="Use today's local time window. Default.")
    date_group.add_argument("--date", help="Use one local calendar day, YYYY-MM-DD.")
    date_group.add_argument("--since", help='Relative time filter, such as "7d", "12h", or "30m".')
    parser.add_argument("--from", dest="from_value", help="Start date, YYYY-MM-DD or ISO timestamp.")
    parser.add_argument("--to", dest="to_value", help="End date, YYYY-MM-DD or ISO timestamp.")
    parser.add_argument("--codex-home", default=str(default_codex_home()), help="Codex home directory.")
    parser.add_argument(
        "--no-archived",
        action="store_true",
        help="Do not scan ~/.codex/archived_sessions.",
    )
    if include_lang:
        parser.add_argument(
            "--lang",
            choices=("auto", "en", "zh"),
            help="Output language. Defaults to config defaultLanguage; auto follows locale.",
        )


def cmd_init(args: argparse.Namespace) -> None:
    data_dir = storage_dir_from(args.data_dir)
    init_storage(data_dir)
    print(f"Initialized Codex usage storage at {data_dir}")


def cmd_doctor(args: argparse.Namespace) -> None:
    import platform

    data_dir = storage_dir_from(args.data_dir)
    print("Codex Usage Estimator Doctor")
    print(f"Python: {platform.python_version()}")
    try:
        import tiktoken

        version = getattr(tiktoken, "__version__", "unknown")
        print(f"tiktoken: available ({version})")
    except ModuleNotFoundError:
        print("tiktoken: missing")
        print("Install with `python3 -m pip install -r requirements.txt` or run `./scripts/bootstrap.sh`.")

    if data_dir.exists():
        required = ["groups.jsonl", "snapshots.jsonl", "turns.jsonl", "config.json"]
        missing = [name for name in required if not (data_dir / name).exists()]
        if missing:
            print(f"storage: incomplete at {data_dir} (missing {', '.join(missing)})")
        else:
            print(f"storage: initialized at {data_dir}")
    else:
        print(f"storage: not initialized at {data_dir}")
        print("Run `codex-usage init` when you are ready to record real usage.")

    codex_home = default_codex_home()
    print(f"codex home: {codex_home}")
    if codex_home.exists():
        print(f"codex session logs: {len(discover_session_files(codex_home))}")
    else:
        print("codex session logs: unavailable")


def cmd_group_create(args: argparse.Namespace) -> None:
    data_dir = storage_dir_from(args.data_dir)
    groups = load_groups(data_dir)
    if any(group.get("name") == args.name for group in groups):
        raise UsageError(
            f'Task group "{args.name}" already exists. '
            "Use `codex-usage group list` to find its id."
        )
    record: Dict[str, Any] = {
        "id": _new_id("tg"),
        "name": args.name,
        "createdAt": now_iso(),
    }
    if args.description:
        record["description"] = args.description
    if args.label:
        record["labels"] = args.label
    append_group(data_dir, record)
    print(f'Created task group "{record["name"]}" ({record["id"]})')


def cmd_group_list(args: argparse.Namespace) -> None:
    data_dir = storage_dir_from(args.data_dir)
    groups = load_groups(data_dir)
    if not groups:
        print("No task groups yet. Create one with `codex-usage group create \"quick-chat\"`.")
        return
    rows = []
    for group in groups:
        labels = ",".join(group.get("labels", []))
        rows.append([group.get("id", ""), group.get("name", ""), labels, group.get("createdAt", "")[:16]])
    _print_table(["ID", "Name", "Labels", "Created"], rows)


def cmd_snapshot(args: argparse.Namespace) -> None:
    _validate_snapshot_percentages(args.usage, args.remaining)
    data_dir = storage_dir_from(args.data_dir)
    group = find_group(load_groups(data_dir), args.group)
    record: Dict[str, Any] = {
        "id": _new_id("us"),
        "taskGroupId": group["id"],
        "timestamp": now_iso(),
        "source": args.source,
    }
    if args.usage is not None:
        record["usagePercent"] = args.usage
    if args.remaining is not None:
        record["remainingPercent"] = args.remaining
    if args.note:
        record["note"] = args.note
    append_snapshot(data_dir, record)
    print(f'Recorded usage snapshot for "{group["name"]}" ({record["id"]})')


def cmd_turn_add(args: argparse.Namespace) -> None:
    if args.requests < 0:
        raise UsageError("`--requests` must be 0 or greater.")
    if args.tool_calls < 0:
        raise UsageError("`--tool-calls` must be 0 or greater.")

    data_dir = storage_dir_from(args.data_dir)
    config = load_config(data_dir)
    group = find_group(load_groups(data_dir), args.group)
    text, source, source_path = _read_turn_input(args)
    model = args.model or config.get("defaultModel", "unknown")
    mode = args.mode or config.get("defaultMode", "unknown")
    parts = parse_transcript(text, args.kind)
    encoding_name = config.get("defaultEncoding", "o200k_base")

    user_tokens = count_tokens(parts["userText"], model=model, encoding_name=encoding_name)
    assistant_tokens = count_tokens(parts["assistantText"], model=model, encoding_name=encoding_name)
    tool_tokens = count_tokens(parts["toolText"], model=model, encoding_name=encoding_name)
    file_context_tokens = count_tokens(
        parts["fileContextText"], model=model, encoding_name=encoding_name
    )
    visible = user_tokens + assistant_tokens + tool_tokens + file_context_tokens
    multiplier = float(config.get("multipliers", {}).get(args.task_type, 3))

    record: Dict[str, Any] = {
        "id": _new_id("tr"),
        "taskGroupId": group["id"],
        "timestamp": now_iso(),
        "model": model,
        "mode": mode,
        "taskType": args.task_type,
        "source": source,
        "userTokensEstimated": user_tokens,
        "assistantTokensEstimated": assistant_tokens,
        "toolTokensEstimated": tool_tokens,
        "fileContextTokensEstimated": file_context_tokens,
        "visibleTokensEstimated": visible,
        "effectiveTokensEstimated": int(round(visible * multiplier)),
        "requestCountEstimated": args.requests,
        "toolCallCount": args.tool_calls,
    }
    if source_path:
        record["sourcePath"] = source_path
    for key, value in parts.items():
        if value:
            record[key] = value

    append_turn(data_dir, record)
    print(
        f'Added turn "{record["id"]}" to "{group["name"]}": '
        f'{visible:,} visible tokens estimated, '
        f'{record["effectiveTokensEstimated"]:,} effective tokens estimated.'
    )


def cmd_report(args: argparse.Namespace) -> None:
    data_dir = storage_dir_from(args.data_dir)
    config = load_config(data_dir)
    lang = normalize_lang(args.lang or config.get("defaultLanguage", "auto"))
    groups = load_groups(data_dir)
    snapshots = load_snapshots(data_dir)
    turns = load_turns(data_dir)
    rows = _aggregate_from_args(groups, snapshots, turns, args)
    breakdown_turns = _filter_turns_from_args(groups, turns, args)
    print(render_report(rows, lang=lang))
    if args.breakdown in ("model", "all"):
        print("")
        print(
            render_breakdown(
                TEXT[lang]["breakdown_model"],
                aggregate_breakdown(breakdown_turns, "model"),
                lang=lang,
            )
        )
    if args.breakdown in ("mode", "all"):
        print("")
        print(
            render_breakdown(
                TEXT[lang]["breakdown_mode"],
                aggregate_breakdown(breakdown_turns, "mode"),
                lang=lang,
            )
        )


def cmd_export(args: argparse.Namespace) -> None:
    data_dir = storage_dir_from(args.data_dir)
    rows = _aggregate_from_args(load_groups(data_dir), load_snapshots(data_dir), load_turns(data_dir), args)
    output = Path(args.output)
    export_rows(rows, output, args.format)
    print(f"Exported {len(rows)} row(s) to {output}")


def cmd_codex_report(args: argparse.Namespace) -> None:
    data_dir = storage_dir_from(args.data_dir)
    try:
        config = load_config(data_dir)
    except UsageError:
        config = {}
    lang = normalize_lang(args.lang or config.get("defaultLanguage", "auto"))
    report = _codex_report_from_args(args)
    print(render_codex_report(report, lang=lang))


def cmd_codex_export(args: argparse.Namespace) -> None:
    report = _codex_report_from_args(args)
    output = Path(args.output)
    export_codex_report(report, output, args.format)
    print(f"Exported {len(report['sessions'])} Codex session row(s) to {output}")


def _codex_report_from_args(args: argparse.Namespace) -> Dict[str, Any]:
    start, end = resolve_codex_time_window(
        today=args.today,
        date_value=args.date,
        since=args.since,
        from_value=args.from_value,
        to_value=args.to_value,
    )
    return aggregate_codex_logs(
        start=start,
        end=end,
        codex_home=Path(args.codex_home),
        include_archived=not args.no_archived,
    )


def _aggregate_from_args(
    groups: List[Dict[str, Any]],
    snapshots: List[Dict[str, Any]],
    turns: List[Dict[str, Any]],
    args: argparse.Namespace,
) -> List[Dict[str, Any]]:
    return aggregate_rows(
        groups,
        snapshots,
        turns,
        group_value=args.group,
        since=args.since,
        from_value=args.from_value,
        to_value=args.to_value,
        model=args.model,
        mode=args.mode,
    )


def _filter_turns_from_args(
    groups: List[Dict[str, Any]],
    turns: List[Dict[str, Any]],
    args: argparse.Namespace,
) -> List[Dict[str, Any]]:
    return filter_turns(
        groups,
        turns,
        group_value=args.group,
        since=args.since,
        from_value=args.from_value,
        to_value=args.to_value,
        model=args.model,
        mode=args.mode,
    )


def _read_turn_input(args: argparse.Namespace) -> tuple:
    if args.stdin:
        return sys.stdin.read(), "manual", None

    path = Path(args.file)
    if not path.exists():
        raise UsageError(f'File "{path}" was not found. Check the path and retry.')
    if not path.is_file():
        raise UsageError(f'Path "{path}" is not a file.')
    return path.read_text(encoding="utf-8"), "file", str(path)


def _validate_snapshot_percentages(usage: Optional[float], remaining: Optional[float]) -> None:
    if usage is None and remaining is None:
        raise UsageError("Provide `--usage` or `--remaining` for the snapshot.")
    for label, value in (("usage", usage), ("remaining", remaining)):
        if value is not None and not 0 <= value <= 100:
            raise UsageError(f"`--{label}` must be between 0 and 100.")
    if usage is not None and remaining is not None and abs((usage + remaining) - 100) > 0.1:
        raise UsageError(
            "`--usage` and `--remaining` are inconsistent. "
            "They should add up to 100, allowing 0.1 floating-point tolerance."
        )


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _print_table(headers: Iterable[str], rows: Iterable[Iterable[str]]) -> None:
    rows_list = [[str(value) for value in row] for row in rows]
    headers_list = list(headers)
    widths = [len(header) for header in headers_list]
    for row in rows_list:
        for index, value in enumerate(row):
            widths[index] = max(widths[index], len(value))

    def format_row(row: Iterable[str]) -> str:
        values = list(row)
        return "  ".join(values[index].ljust(widths[index]) for index in range(len(values)))

    print(format_row(headers_list))
    print(format_row(["-" * width for width in widths]))
    for row in rows_list:
        print(format_row(row))


if __name__ == "__main__":
    entrypoint()

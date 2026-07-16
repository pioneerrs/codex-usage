from __future__ import annotations

import csv
import json
import os
import re
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set

from tzlocal import get_localzone

from .errors import UsageError


LOCAL_TIMEZONE = get_localzone()

DISCLAIMER_EN = (
    "All token values are estimated from locally visible text. "
    "They are not OpenAI billing tokens or Codex internal token counts."
)
DISCLAIMER_ZH = "所有 token 数值均基于本地可见文本估算，不代表 OpenAI 账单 token 或 Codex 内部真实 token。"

TEXT = {
    "en": {
        "report_title": "Recorded Estimated Codex Usage Report",
        "no_matching_records": "No matching records.",
        "recorded_only": "This report only covers turns explicitly recorded or imported into `.codex-usage/`.",
        "recorded_only_store": "This report only covers turns explicitly recorded or imported into the local data store.",
        "not_included": "Unrecorded long-running goals, hidden context, reasoning tokens, and Codex internals are not included.",
        "effective_note": "Effective tokens are heuristic and calibrated by task type multiplier.",
        "notes": "Notes:",
        "disclaimer": DISCLAIMER_EN,
        "unavailable": "unavailable",
        "negative": "negative",
        "breakdown_model": "Estimated Breakdown by Model",
        "breakdown_mode": "Estimated Breakdown by Mode",
        "headers": [
            "Task Group",
            "Turns",
            "Requests Est.",
            "Tool Calls",
            "Visible Tokens Est.",
            "Effective Tokens Est.",
            "Usage Δ",
            "Visible / 1% Est.",
            "Visible / Request Est.",
            "Visible / Tool Est.",
        ],
        "breakdown_headers": [
            "Key",
            "Turns",
            "Requests Est.",
            "Tool Calls",
            "Visible Tokens Est.",
            "Effective Tokens Est.",
        ],
    },
    "zh": {
        "report_title": "已记录的 Codex 用量估算报告",
        "no_matching_records": "没有匹配的记录。",
        "recorded_only": "本报告只统计已显式记录或导入 `.codex-usage/` 的 turn。",
        "recorded_only_store": "本报告只统计已显式记录或导入本地数据目录的 turn。",
        "not_included": "未记录的长时间 goal、隐藏上下文、reasoning token 和 Codex 内部数据不会计入。",
        "effective_note": "有效 token 是按任务类型 multiplier 计算的启发式估算值。",
        "notes": "说明：",
        "disclaimer": DISCLAIMER_ZH,
        "unavailable": "不可用",
        "negative": "负数",
        "breakdown_model": "按模型估算汇总",
        "breakdown_mode": "按执行模式估算汇总",
        "headers": [
            "任务组",
            "轮次",
            "估算请求",
            "工具调用",
            "可见Token估算",
            "有效Token估算",
            "用量变化",
            "每1%可见估算",
            "每请求可见估算",
            "每工具可见估算",
        ],
        "breakdown_headers": [
            "类别",
            "轮次",
            "估算请求",
            "工具调用",
            "可见Token估算",
            "有效Token估算",
        ],
    },
}


def normalize_lang(lang: Optional[str]) -> str:
    if not lang:
        return _detect_lang_from_locale()
    normalized = lang.lower()
    if normalized == "auto":
        return _detect_lang_from_locale()
    if normalized in ("zh-cn", "zh_hans", "zh-hans", "cn"):
        return "zh"
    if normalized not in TEXT:
        raise UsageError('Unsupported language. Use "auto", "en", or "zh".')
    return normalized


def _detect_lang_from_locale() -> str:
    for key in ("LC_ALL", "LC_MESSAGES", "LANGUAGE", "LANG"):
        value = os.environ.get(key, "").lower()
        if not value:
            continue
        if value.startswith("zh") or "zh_cn" in value or "zh-" in value:
            return "zh"
    return "en"


def parse_datetime_filter(value: Optional[str], end_of_day: bool = False) -> Optional[datetime]:
    if not value:
        return None
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            parsed_date = date.fromisoformat(value)
            parsed_time = time.max if end_of_day else time.min
            return datetime.combine(parsed_date, parsed_time, tzinfo=LOCAL_TIMEZONE)
        return _normalize_datetime(datetime.fromisoformat(value))
    except ValueError:
        raise UsageError(
            f'Could not parse date "{value}". Use YYYY-MM-DD or an ISO timestamp.'
        )


def parse_since(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    match = re.fullmatch(r"(\d+)([dhm])", value.strip())
    if not match:
        raise UsageError('Could not parse --since. Use values like "7d", "12h", or "30m".')
    amount = int(match.group(1))
    unit = match.group(2)
    delta = {
        "d": timedelta(days=amount),
        "h": timedelta(hours=amount),
        "m": timedelta(minutes=amount),
    }[unit]
    return datetime.now(LOCAL_TIMEZONE) - delta


def parse_record_timestamp(record: Dict[str, Any]) -> datetime:
    value = record.get("timestamp") or record.get("createdAt")
    if not value:
        return datetime.min.replace(tzinfo=LOCAL_TIMEZONE)
    try:
        return _normalize_datetime(datetime.fromisoformat(value))
    except ValueError:
        raise UsageError(f'Could not parse timestamp "{value}" in record `{record.get("id", "?")}`.')


def _normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=LOCAL_TIMEZONE)
    return value.astimezone(LOCAL_TIMEZONE)


def aggregate_rows(
    groups: Sequence[Dict[str, Any]],
    snapshots: Sequence[Dict[str, Any]],
    turns: Sequence[Dict[str, Any]],
    group_value: Optional[str] = None,
    since: Optional[str] = None,
    from_value: Optional[str] = None,
    to_value: Optional[str] = None,
    model: Optional[str] = None,
    mode: Optional[str] = None,
) -> List[Dict[str, Any]]:
    group_by_id = {group["id"]: group for group in groups}
    selected_group_ids = resolve_group_ids(groups, group_value)
    from_dt, to_dt = resolve_time_window(since, from_value, to_value)
    filtered_turns = filter_turns(
        groups,
        turns,
        group_value=group_value,
        since=since,
        from_value=from_value,
        to_value=to_value,
        model=model,
        mode=mode,
    )

    filtered_snapshots = []
    for snapshot in snapshots:
        if snapshot.get("taskGroupId") not in selected_group_ids:
            continue
        timestamp = parse_record_timestamp(snapshot)
        if from_dt and timestamp < from_dt:
            continue
        if to_dt and timestamp > to_dt:
            continue
        filtered_snapshots.append(snapshot)

    rows: List[Dict[str, Any]] = []
    ids_with_turns = {turn.get("taskGroupId") for turn in filtered_turns}
    ids_with_snapshots = {snapshot.get("taskGroupId") for snapshot in filtered_snapshots}
    active_group_ids = selected_group_ids.intersection(ids_with_turns.union(ids_with_snapshots))
    if group_value:
        active_group_ids = selected_group_ids

    for group_id in sorted(active_group_ids, key=lambda item: group_by_id.get(item, {}).get("name", item)):
        group_turns = [turn for turn in filtered_turns if turn.get("taskGroupId") == group_id]
        group_snapshots = [
            snapshot for snapshot in filtered_snapshots if snapshot.get("taskGroupId") == group_id
        ]
        visible = sum(int(turn.get("visibleTokensEstimated") or 0) for turn in group_turns)
        effective = sum(int(round(float(turn.get("effectiveTokensEstimated") or 0))) for turn in group_turns)
        requests = sum(int(turn.get("requestCountEstimated") or 0) for turn in group_turns)
        tool_calls = sum(int(turn.get("toolCallCount") or 0) for turn in group_turns)
        usage_delta = compute_usage_delta(group_snapshots)

        row = {
            "taskGroupId": group_id,
            "taskGroupName": group_by_id.get(group_id, {}).get("name", group_id),
            "turns": len(group_turns),
            "requestsEstimated": requests,
            "toolCalls": tool_calls,
            "visibleTokensEstimated": visible,
            "effectiveTokensEstimated": effective,
            "usageDeltaPercent": usage_delta,
            "visibleTokensPerUsagePercentEstimated": _divide(visible, usage_delta),
            "effectiveTokensPerUsagePercentEstimated": _divide(effective, usage_delta),
            "visibleTokensPerRequestEstimated": _divide(visible, requests),
            "visibleTokensPerToolCallEstimated": _divide(visible, tool_calls),
        }
        rows.append(row)

    return rows


def filter_turns(
    groups: Sequence[Dict[str, Any]],
    turns: Sequence[Dict[str, Any]],
    group_value: Optional[str] = None,
    since: Optional[str] = None,
    from_value: Optional[str] = None,
    to_value: Optional[str] = None,
    model: Optional[str] = None,
    mode: Optional[str] = None,
) -> List[Dict[str, Any]]:
    selected_group_ids = resolve_group_ids(groups, group_value)
    from_dt, to_dt = resolve_time_window(since, from_value, to_value)
    filtered_turns = []
    for turn in turns:
        if turn.get("taskGroupId") not in selected_group_ids:
            continue
        if model and turn.get("model") != model:
            continue
        if mode and turn.get("mode") != mode:
            continue
        timestamp = parse_record_timestamp(turn)
        if from_dt and timestamp < from_dt:
            continue
        if to_dt and timestamp > to_dt:
            continue
        filtered_turns.append(turn)
    return filtered_turns


def resolve_group_ids(groups: Sequence[Dict[str, Any]], group_value: Optional[str]) -> Set[str]:
    if not group_value:
        return {group["id"] for group in groups}
    from .storage import find_group

    return {find_group(groups, group_value)["id"]}


def resolve_time_window(
    since: Optional[str] = None,
    from_value: Optional[str] = None,
    to_value: Optional[str] = None,
) -> tuple:
    from_dt = parse_datetime_filter(from_value)
    to_dt = parse_datetime_filter(to_value, end_of_day=True)
    since_dt = parse_since(since)
    if since_dt and from_dt:
        from_dt = max(from_dt, since_dt)
    elif since_dt:
        from_dt = since_dt
    if from_dt and to_dt and from_dt > to_dt:
        raise UsageError("The report start date is after the end date. Check --from/--to/--since.")
    return from_dt, to_dt


def compute_usage_delta(snapshots: Sequence[Dict[str, Any]]) -> Optional[float]:
    usable = [snapshot for snapshot in snapshots if _usage_value(snapshot) is not None]
    if len(usable) < 2:
        return None
    ordered = sorted(usable, key=parse_record_timestamp)
    before = _usage_value(ordered[0])
    after = _usage_value(ordered[-1])
    if before is None or after is None:
        return None
    return round(after - before, 4)


def _usage_value(snapshot: Dict[str, Any]) -> Optional[float]:
    if snapshot.get("usagePercent") is not None:
        return float(snapshot["usagePercent"])
    if snapshot.get("remainingPercent") is not None:
        return 100.0 - float(snapshot["remainingPercent"])
    return None


def _divide(numerator: float, denominator: Optional[float]) -> Optional[float]:
    if denominator is None or denominator <= 0:
        return None
    return numerator / denominator


def render_report(rows: Sequence[Dict[str, Any]], lang: str = "en") -> str:
    text = TEXT[normalize_lang(lang)]
    lines = [text["report_title"], ""]
    if not rows:
        lines.append(text["no_matching_records"])
        lines.extend(
            [
                "",
                text["disclaimer"],
                text["recorded_only_store"],
            ]
        )
        return "\n".join(lines)

    table_rows = [
        [
            row["taskGroupName"],
            str(row["turns"]),
            str(row["requestsEstimated"]),
            str(row["toolCalls"]),
            _format_int(row["visibleTokensEstimated"]),
            _format_int(row["effectiveTokensEstimated"]),
            _format_percent(row["usageDeltaPercent"], lang),
            _format_optional_number(row["visibleTokensPerUsagePercentEstimated"], lang),
            _format_optional_number(row["visibleTokensPerRequestEstimated"], lang),
            _format_optional_number(row["visibleTokensPerToolCallEstimated"], lang),
        ]
        for row in rows
    ]
    lines.extend(
        render_table(
            text["headers"],
            table_rows,
        )
    )
    lines.extend(
        [
            "",
            text["notes"],
            f"- {text['recorded_only']}",
            f"- {text['not_included']}",
            f"- {text['disclaimer']}",
            f"- {text['effective_note']}",
        ]
    )
    return "\n".join(lines)


def render_breakdown(title: str, rows: Sequence[Dict[str, Any]], lang: str = "en") -> str:
    text = TEXT[normalize_lang(lang)]
    lines = [title, ""]
    table_rows = [
        [
            row["key"],
            str(row["turns"]),
            str(row["requestsEstimated"]),
            str(row["toolCalls"]),
            _format_int(row["visibleTokensEstimated"]),
            _format_int(row["effectiveTokensEstimated"]),
        ]
        for row in rows
    ]
    lines.extend(
        render_table(
            text["breakdown_headers"],
            table_rows,
        )
    )
    return "\n".join(lines)


def aggregate_breakdown(turns: Sequence[Dict[str, Any]], key_name: str) -> List[Dict[str, Any]]:
    buckets: Dict[str, Dict[str, Any]] = {}
    for turn in turns:
        key = str(turn.get(key_name) or "unknown")
        bucket = buckets.setdefault(
            key,
            {
                "key": key,
                "turns": 0,
                "requestsEstimated": 0,
                "toolCalls": 0,
                "visibleTokensEstimated": 0,
                "effectiveTokensEstimated": 0,
            },
        )
        bucket["turns"] += 1
        bucket["requestsEstimated"] += int(turn.get("requestCountEstimated") or 0)
        bucket["toolCalls"] += int(turn.get("toolCallCount") or 0)
        bucket["visibleTokensEstimated"] += int(turn.get("visibleTokensEstimated") or 0)
        bucket["effectiveTokensEstimated"] += int(round(float(turn.get("effectiveTokensEstimated") or 0)))
    return sorted(buckets.values(), key=lambda row: row["key"])


def render_table(headers: Sequence[str], rows: Sequence[Sequence[str]]) -> List[str]:
    widths = [len(header) for header in headers]
    for row in rows:
        for index, value in enumerate(row):
            widths[index] = max(widths[index], len(value))

    def format_row(row: Sequence[str]) -> str:
        return "  ".join(value.ljust(widths[index]) for index, value in enumerate(row))

    output = [format_row(headers), format_row(["-" * width for width in widths])]
    output.extend(format_row(row) for row in rows)
    return output


def export_rows(rows: Sequence[Dict[str, Any]], output: Path, fmt: str) -> None:
    if fmt == "json":
        output.write_text(json.dumps(list(rows), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return
    if fmt != "csv":
        raise UsageError("MVP export supports CSV and JSON formats.")
    fieldnames = [
        "taskGroupId",
        "taskGroupName",
        "turns",
        "requestsEstimated",
        "toolCalls",
        "visibleTokensEstimated",
        "effectiveTokensEstimated",
        "usageDeltaPercent",
        "visibleTokensPerUsagePercentEstimated",
        "effectiveTokensPerUsagePercentEstimated",
        "visibleTokensPerRequestEstimated",
        "visibleTokensPerToolCallEstimated",
    ]
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in fieldnames})


def _format_int(value: Any) -> str:
    return f"{int(value):,}"


def _format_percent(value: Optional[float], lang: str = "en") -> str:
    text = TEXT[normalize_lang(lang)]
    if value is None:
        return text["unavailable"]
    if value < 0:
        return f"{text['negative']} {value:g}%"
    return f"{value:g}%"


def _format_optional_number(value: Optional[float], lang: str = "en") -> str:
    text = TEXT[normalize_lang(lang)]
    if value is None:
        return text["unavailable"]
    return f"{round(value):,}"

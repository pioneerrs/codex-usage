from __future__ import annotations

import csv
import json
import os
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .errors import UsageError
from .reporting import normalize_lang, render_table


TOKEN_KEYS = (
    "input_tokens",
    "cached_input_tokens",
    "output_tokens",
    "reasoning_output_tokens",
    "total_tokens",
)

TEXT = {
    "en": {
        "title": "Codex Local Log Usage Report",
        "window": "Window",
        "sources": "Sources",
        "no_records": "No Codex token_count records found for this window.",
        "sessions": "Sessions",
        "events": "Token Events",
        "notes": "Notes:",
        "note_recorded": "Values come from local Codex session token_count events.",
        "note_cached": "cached input is included in input and is usually cheaper than fresh input.",
        "note_limits": "Primary and secondary percentages are observed rate-limit snapshots, not cash balances.",
        "headers": [
            "Sessions",
            "Events",
            "Input",
            "Cached Input",
            "Non-cached Input",
            "Output",
            "Reasoning",
            "Total",
        ],
        "rate_headers": ["Limit", "First", "Latest", "Delta", "Max", "Reset"],
        "session_headers": ["Session", "Last Event", "Total", "Output", "Reasoning"],
        "primary": "primary",
        "secondary": "secondary",
        "unavailable": "unavailable",
    },
    "zh": {
        "title": "Codex 本地日志用量报告",
        "window": "时间窗口",
        "sources": "数据来源",
        "no_records": "这个时间窗口内没有找到 Codex token_count 记录。",
        "sessions": "Session 数",
        "events": "Token 事件数",
        "notes": "说明：",
        "note_recorded": "数值来自本机 Codex session 日志里的 token_count 事件。",
        "note_cached": "cached input 是 input 的子集，通常比非缓存 input 便宜。",
        "note_limits": "primary 和 secondary 百分比是观察到的限额快照，不是现金余额。",
        "headers": [
            "Sessions",
            "事件数",
            "Input",
            "Cached Input",
            "Non-cached Input",
            "Output",
            "Reasoning",
            "Total",
        ],
        "rate_headers": ["限额", "起始", "最新", "变化", "最高", "重置时间"],
        "session_headers": ["Session", "最后事件", "Total", "Output", "Reasoning"],
        "primary": "primary",
        "secondary": "secondary",
        "unavailable": "不可用",
    },
}


def default_codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex")


def resolve_time_window(
    today: bool = False,
    date_value: Optional[str] = None,
    since: Optional[str] = None,
    from_value: Optional[str] = None,
    to_value: Optional[str] = None,
) -> Tuple[datetime, datetime]:
    now = datetime.now().astimezone()
    if (today or date_value) and (from_value or to_value):
        raise UsageError("Use either --today/--date or --from/--to, not both.")
    if date_value:
        parsed = _parse_date(date_value)
        return _day_bounds(parsed)
    if today or not any([since, from_value, to_value]):
        return _day_bounds(now.date(), end=now)

    start = _parse_datetime_filter(from_value, end_of_day=False) if from_value else None
    end = _parse_datetime_filter(to_value, end_of_day=True) if to_value else now
    if since:
        since_start = now - _parse_since_delta(since)
        start = max(start, since_start) if start else since_start
    if not start:
        start = datetime.min.replace(tzinfo=now.tzinfo)
    if start > end:
        raise UsageError("The Codex log report start time is after the end time.")
    return start, end


def discover_session_files(codex_home: Optional[Path] = None, include_archived: bool = True) -> List[Path]:
    home = codex_home or default_codex_home()
    candidates: List[Path] = []
    sessions = home / "sessions"
    if sessions.exists():
        candidates.extend(path for path in sessions.rglob("*.jsonl") if path.is_file())
    archived = home / "archived_sessions"
    if include_archived and archived.exists():
        candidates.extend(path for path in archived.glob("*.jsonl") if path.is_file())

    by_name: Dict[str, Path] = {}
    for path in candidates:
        previous = by_name.get(path.name)
        if previous is None or path.stat().st_size > previous.stat().st_size:
            by_name[path.name] = path
    return sorted(by_name.values())


def aggregate_codex_logs(
    start: datetime,
    end: datetime,
    codex_home: Optional[Path] = None,
    include_archived: bool = True,
) -> Dict[str, Any]:
    files = discover_session_files(codex_home=codex_home, include_archived=include_archived)
    session_rows: List[Dict[str, Any]] = []
    totals = _empty_totals()
    timeline_buckets = _new_timeline_buckets(start, end)
    rate_events: List[Dict[str, Any]] = []
    token_event_count = 0

    for path in files:
        events = read_token_events(path)
        if not events:
            continue
        before: Optional[Dict[str, Any]] = None
        in_window: List[Dict[str, Any]] = []
        for event in events:
            if event["timestamp"] < start:
                before = event
            elif start <= event["timestamp"] <= end:
                in_window.append(event)
        if not in_window:
            continue

        first_event = in_window[0]
        last_event = in_window[-1]
        base_usage = before["usage"] if before else _empty_totals()
        delta = _usage_delta(base_usage, last_event["usage"])
        previous_usage = base_usage
        token_event_count += len(in_window)
        for key in TOKEN_KEYS:
            totals[key] += delta[key]
        for event in in_window:
            event_delta = _usage_delta(previous_usage, event["usage"])
            _add_event_to_timeline(timeline_buckets, start, event, event_delta)
            previous_usage = event["usage"]

        session_rate_events = [_rate_snapshot(event) for event in in_window]
        rate_events.extend(snapshot for snapshot in session_rate_events if snapshot)
        session_rows.append(
            {
                "sessionFile": path.name,
                "sourcePath": str(path),
                "firstEventAt": first_event["timestamp"].isoformat(),
                "lastEventAt": last_event["timestamp"].isoformat(),
                "tokenEvents": len(in_window),
                **_public_usage(delta),
                **_rate_summary_fields(session_rate_events),
            }
        )

    summary = {
        "windowStart": start.isoformat(),
        "windowEnd": end.isoformat(),
        "sourceRoot": str(codex_home or default_codex_home()),
        "sessionCount": len(session_rows),
        "tokenEventCount": token_event_count,
        **_public_usage(totals),
    }
    summary.update(_rate_summary_fields(rate_events))
    return {
        "summary": summary,
        "sessions": session_rows,
        "timeline": _public_timeline(timeline_buckets),
    }


def read_token_events(path: Path) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if "token_count" not in line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            payload = record.get("payload") or {}
            if payload.get("type") != "token_count":
                continue
            usage = (payload.get("info") or {}).get("total_token_usage") or {}
            if not usage.get("total_tokens"):
                continue
            timestamp = _parse_timestamp(record.get("timestamp"))
            if not timestamp:
                continue
            events.append(
                {
                    "timestamp": timestamp,
                    "lineNumber": line_number,
                    "usage": {key: int(usage.get(key) or 0) for key in TOKEN_KEYS},
                    "rateLimits": payload.get("rate_limits") or {},
                }
            )
    events.sort(key=lambda event: (event["timestamp"], event["lineNumber"]))
    return events


def render_codex_report(report: Dict[str, Any], lang: str = "en") -> str:
    text = TEXT[normalize_lang(lang)]
    summary = report["summary"]
    lines = [
        text["title"],
        "",
        f"{text['window']}: {summary['windowStart']} -> {summary['windowEnd']}",
        f"{text['sources']}: {summary['sourceRoot']}",
        "",
    ]
    if summary["sessionCount"] == 0:
        lines.append(text["no_records"])
        return "\n".join(lines)

    lines.extend(
        render_table(
            text["headers"],
            [
                [
                    str(summary["sessionCount"]),
                    str(summary["tokenEventCount"]),
                    _format_int(summary["inputTokens"]),
                    _format_int(summary["cachedInputTokens"]),
                    _format_int(summary["nonCachedInputTokens"]),
                    _format_int(summary["outputTokens"]),
                    _format_int(summary["reasoningOutputTokens"]),
                    _format_int(summary["totalTokens"]),
                ]
            ],
        )
    )

    rate_rows = [
        _rate_row(text["primary"], "primary", summary, text["unavailable"]),
        _rate_row(text["secondary"], "secondary", summary, text["unavailable"]),
    ]
    lines.extend(["", *render_table(text["rate_headers"], rate_rows)])

    session_rows = sorted(report["sessions"], key=lambda row: row["lastEventAt"])[-8:]
    lines.extend(
        [
            "",
            *render_table(
                text["session_headers"],
                [
                    [
                        row["sessionFile"],
                        row["lastEventAt"],
                        _format_int(row["totalTokens"]),
                        _format_int(row["outputTokens"]),
                        _format_int(row["reasoningOutputTokens"]),
                    ]
                    for row in session_rows
                ],
            ),
        ]
    )

    lines.extend(
        [
            "",
            text["notes"],
            f"- {text['note_recorded']}",
            f"- {text['note_cached']}",
            f"- {text['note_limits']}",
        ]
    )
    return "\n".join(lines)


def export_codex_report(report: Dict[str, Any], output: Path, fmt: str) -> None:
    if fmt == "json":
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return
    if fmt != "csv":
        raise UsageError("Codex log export supports CSV and JSON formats.")

    fieldnames = [
        "sessionFile",
        "sourcePath",
        "firstEventAt",
        "lastEventAt",
        "tokenEvents",
        "inputTokens",
        "cachedInputTokens",
        "nonCachedInputTokens",
        "outputTokens",
        "reasoningOutputTokens",
        "totalTokens",
        "primaryUsedPercentFirst",
        "primaryUsedPercentLatest",
        "primaryUsedPercentDelta",
        "primaryUsedPercentMax",
        "primaryResetsAt",
        "secondaryUsedPercentFirst",
        "secondaryUsedPercentLatest",
        "secondaryUsedPercentDelta",
        "secondaryUsedPercentMax",
        "secondaryResetsAt",
    ]
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in report["sessions"]:
            writer.writerow({key: row.get(key) for key in fieldnames})
        summary = {"sessionFile": "TOTAL", "tokenEvents": report["summary"]["tokenEventCount"]}
        summary.update({key: report["summary"].get(key) for key in fieldnames if key in report["summary"]})
        writer.writerow({key: summary.get(key) for key in fieldnames})


def _rate_snapshot(event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    limits = event.get("rateLimits") or {}
    primary = limits.get("primary") or {}
    secondary = limits.get("secondary") or {}
    if not primary and not secondary:
        return None
    if not _is_effective_rate(primary, secondary):
        return None
    return {
        "timestamp": event["timestamp"],
        "primaryUsedPercent": _optional_float(primary.get("used_percent")),
        "primaryResetsAt": _timestamp_from_epoch(primary.get("resets_at")),
        "secondaryUsedPercent": _optional_float(secondary.get("used_percent")),
        "secondaryResetsAt": _timestamp_from_epoch(secondary.get("resets_at")),
    }


def _is_effective_rate(primary: Dict[str, Any], secondary: Dict[str, Any]) -> bool:
    primary_used = _optional_float(primary.get("used_percent")) or 0.0
    secondary_used = _optional_float(secondary.get("used_percent")) or 0.0
    return primary_used > 0 or secondary_used > 0


def _rate_summary_fields(events: Sequence[Optional[Dict[str, Any]]]) -> Dict[str, Any]:
    snapshots = [event for event in events if event]
    fields: Dict[str, Any] = {}
    for prefix in ("primary", "secondary"):
        key = f"{prefix}UsedPercent"
        values = [snapshot for snapshot in snapshots if snapshot.get(key) is not None]
        if not values:
            fields[f"{key}First"] = None
            fields[f"{key}Latest"] = None
            fields[f"{key}Delta"] = None
            fields[f"{key}Max"] = None
            fields[f"{prefix}ResetsAt"] = None
            continue
        values.sort(key=lambda item: item["timestamp"])
        first = values[0][key]
        latest = values[-1][key]
        fields[f"{key}First"] = first
        fields[f"{key}Latest"] = latest
        fields[f"{key}Delta"] = round(latest - first, 4) if first is not None and latest is not None else None
        fields[f"{key}Max"] = max(value[key] for value in values)
        fields[f"{prefix}ResetsAt"] = values[-1].get(f"{prefix}ResetsAt")
    return fields


def _rate_row(label: str, prefix: str, summary: Dict[str, Any], unavailable: str) -> List[str]:
    key = f"{prefix}UsedPercent"
    return [
        label,
        _format_percent(summary.get(f"{key}First"), unavailable),
        _format_percent(summary.get(f"{key}Latest"), unavailable),
        _format_percent(summary.get(f"{key}Delta"), unavailable, signed=True),
        _format_percent(summary.get(f"{key}Max"), unavailable),
        str(summary.get(f"{prefix}ResetsAt") or unavailable),
    ]


def _usage_delta(base: Dict[str, int], current: Dict[str, int]) -> Dict[str, int]:
    return {key: max(int(current.get(key) or 0) - int(base.get(key) or 0), 0) for key in TOKEN_KEYS}


def _new_timeline_buckets(start: datetime, end: datetime) -> List[Dict[str, Any]]:
    span = _timeline_bucket_span(start, end)
    buckets: List[Dict[str, Any]] = []
    cursor = start
    while cursor <= end:
        bucket_end = min(cursor + span, end)
        buckets.append(
            {
                "bucketStart": cursor,
                "bucketEnd": bucket_end,
                "tokenEvents": 0,
                "rateTimestamp": None,
                "primaryUsedPercent": None,
                "secondaryUsedPercent": None,
                **_empty_totals(),
            }
        )
        cursor = bucket_end
        if cursor == end:
            break
    if not buckets:
        buckets.append(
            {
                "bucketStart": start,
                "bucketEnd": end,
                "tokenEvents": 0,
                "rateTimestamp": None,
                "primaryUsedPercent": None,
                "secondaryUsedPercent": None,
                **_empty_totals(),
            }
        )
    return buckets


def _timeline_bucket_span(start: datetime, end: datetime) -> timedelta:
    duration = end - start
    if duration <= timedelta(days=2):
        return timedelta(hours=1)
    if duration <= timedelta(days=31):
        return timedelta(days=1)
    return timedelta(days=7)


def _add_event_to_timeline(
    buckets: List[Dict[str, Any]],
    start: datetime,
    event: Dict[str, Any],
    delta: Dict[str, int],
) -> None:
    if not buckets:
        return
    first_span = buckets[0]["bucketEnd"] - buckets[0]["bucketStart"]
    if first_span.total_seconds() <= 0:
        index = 0
    else:
        seconds = max((event["timestamp"] - start).total_seconds(), 0)
        index = int(seconds // first_span.total_seconds())
    bucket = buckets[min(max(index, 0), len(buckets) - 1)]
    bucket["tokenEvents"] += 1
    for key in TOKEN_KEYS:
        bucket[key] += delta[key]

    snapshot = _rate_snapshot(event)
    if not snapshot:
        return
    if bucket["rateTimestamp"] and snapshot["timestamp"] < bucket["rateTimestamp"]:
        return
    bucket["rateTimestamp"] = snapshot["timestamp"]
    bucket["primaryUsedPercent"] = snapshot.get("primaryUsedPercent")
    bucket["secondaryUsedPercent"] = snapshot.get("secondaryUsedPercent")


def _public_timeline(buckets: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for bucket in buckets:
        row = {
            "bucketStart": bucket["bucketStart"].isoformat(),
            "bucketEnd": bucket["bucketEnd"].isoformat(),
            "tokenEvents": bucket["tokenEvents"],
            **_public_usage(bucket),
            "primaryUsedPercent": bucket.get("primaryUsedPercent"),
            "secondaryUsedPercent": bucket.get("secondaryUsedPercent"),
        }
        rows.append(row)
    return rows


def _public_usage(usage: Dict[str, int]) -> Dict[str, int]:
    input_tokens = int(usage.get("input_tokens") or 0)
    cached = int(usage.get("cached_input_tokens") or 0)
    return {
        "inputTokens": input_tokens,
        "cachedInputTokens": cached,
        "nonCachedInputTokens": max(input_tokens - cached, 0),
        "outputTokens": int(usage.get("output_tokens") or 0),
        "reasoningOutputTokens": int(usage.get("reasoning_output_tokens") or 0),
        "totalTokens": int(usage.get("total_tokens") or 0),
    }


def _empty_totals() -> Dict[str, int]:
    return {key: 0 for key in TOKEN_KEYS}


def _parse_timestamp(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.astimezone()


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise UsageError(f'Could not parse date "{value}". Use YYYY-MM-DD.')


def _day_bounds(value: date, end: Optional[datetime] = None) -> Tuple[datetime, datetime]:
    now = datetime.now().astimezone()
    start = datetime.combine(value, time.min).replace(tzinfo=now.tzinfo)
    if end:
        return start, end
    return start, datetime.combine(value, time.max).replace(tzinfo=now.tzinfo)


def _parse_datetime_filter(value: str, end_of_day: bool = False) -> datetime:
    if len(value) == 10:
        parsed_date = _parse_date(value)
        parsed_time = time.max if end_of_day else time.min
        return datetime.combine(parsed_date, parsed_time).astimezone()
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise UsageError(f'Could not parse datetime "{value}". Use YYYY-MM-DD or an ISO timestamp.')
    return parsed.astimezone()


def _parse_since_delta(value: str) -> timedelta:
    import re

    match = re.fullmatch(r"(\d+)([dhm])", value.strip())
    if not match:
        raise UsageError('Could not parse --since. Use values like "7d", "12h", or "30m".')
    amount = int(match.group(1))
    unit = match.group(2)
    return {"d": timedelta(days=amount), "h": timedelta(hours=amount), "m": timedelta(minutes=amount)}[unit]


def _optional_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _timestamp_from_epoch(value: Any) -> Optional[str]:
    if value is None:
        return None
    try:
        return datetime.fromtimestamp(float(value)).astimezone().isoformat()
    except (TypeError, ValueError, OSError):
        return None


def _format_int(value: Any) -> str:
    return f"{int(value or 0):,}"


def _format_percent(value: Optional[float], unavailable: str, signed: bool = False) -> str:
    if value is None:
        return unavailable
    if signed and value > 0:
        return f"+{value:g}%"
    return f"{value:g}%"

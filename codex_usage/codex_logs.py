from __future__ import annotations

import csv
import json
import os
from datetime import date, datetime, time, timedelta, timezone, tzinfo
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from tzlocal import get_localzone

from .errors import UsageError
from .reporting import normalize_lang, render_table


LOCAL_TIMEZONE = get_localzone()

TOKEN_KEYS = (
    "input_tokens",
    "cached_input_tokens",
    "output_tokens",
    "reasoning_output_tokens",
    "total_tokens",
)

# Desktop rewrites copied token events just after fork creation; large prefixes
# can take several seconds to emit, so only the first minute is considered replay.
_FORK_PREFIX_GRACE = timedelta(minutes=1)

TEXT = {
    "en": {
        "title": "Codex Local Log Usage Report",
        "fork_audit": "Fork replay audit",
        "fork_audit_detail": "{forks} forks, {resolved} resolved, {unresolved} unresolved, {excluded} inherited tokens excluded.",
        "fork_warning": "Warning: unresolved forks are counted without correction because their inherited baseline could not be verified.",
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
        "session_headers": ["Session", "Model", "Last Event", "Total", "Output", "Reasoning"],
        "by_model": "By Model",
        "model_headers": ["Model", "Sessions", "Input", "Cached Input", "Output", "Total"],
        "primary": "primary",
        "secondary": "secondary",
        "unavailable": "unavailable",
    },
    "zh": {
        "fork_audit": "Fork 继承审计",
        "fork_audit_detail": "{forks} 个 fork，{resolved} 个已解析，{unresolved} 个无法解析，排除 {excluded} 个继承 token。",
        "fork_warning": "警告：无法解析的 fork 未做扣减，因为其继承基线无法精确验证。",
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
        "session_headers": ["Session", "Model", "最后事件", "Total", "Output", "Reasoning"],
        "by_model": "按模型分组",
        "model_headers": ["Model", "Sessions", "Input", "Cached Input", "Output", "Total"],
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
    tz: Optional[tzinfo] = None,
) -> Tuple[datetime, datetime]:
    local_tz = tz or LOCAL_TIMEZONE
    now = datetime.now(local_tz)
    if (today or date_value) and (from_value or to_value):
        raise UsageError("Use either --today/--date or --from/--to, not both.")
    if date_value:
        parsed = _parse_date(date_value)
        return _day_bounds(parsed, tz=local_tz)
    if today or not any([since, from_value, to_value]):
        return _day_bounds(now.date(), end=now, tz=local_tz)

    start = _parse_datetime_filter(from_value, end_of_day=False, tz=local_tz) if from_value else None
    end = _parse_datetime_filter(to_value, end_of_day=True, tz=local_tz) if to_value else now
    if since:
        since_start = now - _parse_since_delta(since)
        start = max(start, since_start) if start else since_start
    if not start:
        start = datetime.min.replace(tzinfo=local_tz)
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
    model_filter: Optional[str] = None,
) -> Dict[str, Any]:
    files = discover_session_files(codex_home=codex_home, include_archived=include_archived)
    metadata_by_path = {path: read_session_metadata(path) for path in files}
    path_by_session_id = {
        metadata["sessionId"]: path
        for path, metadata in metadata_by_path.items()
        if metadata.get("sessionId")
    }
    referenced_parent_ids = {
        metadata.get("forkedFromId")
        for metadata in metadata_by_path.values()
        if metadata.get("forkedFromId")
    }
    cached_parent_paths = {
        path_by_session_id[session_id]
        for session_id in referenced_parent_ids
        if session_id in path_by_session_id
    }
    parsed_by_path: Dict[Path, Dict[str, Any]] = {}

    def parsed_log(path: Path) -> Dict[str, Any]:
        cached = parsed_by_path.get(path)
        if cached is not None:
            return cached
        parsed = _read_session_log(path)
        if path in cached_parent_paths:
            parsed_by_path[path] = parsed
        return parsed

    def cached_events(path: Path) -> List[Dict[str, Any]]:
        return parsed_log(path)["events"]

    session_rows: List[Dict[str, Any]] = []
    totals = _empty_totals()
    verified_totals = _empty_totals()
    timeline_buckets = _new_timeline_buckets(start, end)
    rate_events: List[Dict[str, Any]] = []
    token_event_count = 0
    by_model_totals: Dict[str, Dict[str, int]] = {}
    verified_by_model_totals: Dict[str, Dict[str, int]] = {}
    by_model_session_count: Dict[str, int] = {}
    by_model_audit: Dict[str, Dict[str, int]] = {}
    fork_session_count = 0
    resolved_fork_count = 0
    unresolved_fork_count = 0
    ambiguous_fork_count = 0
    not_replayed_fork_count = 0
    fork_replay_tokens_excluded = 0
    counter_reset_count = 0
    counter_anomaly_count = 0
    damaged_line_count = 0
    invalid_token_event_count = 0

    for path in files:
        metadata = metadata_by_path[path]
        forked_from_id = metadata.get("forkedFromId")
        created_at = metadata.get("createdAt")
        if forked_from_id and created_at is not None and created_at > end:
            continue

        parsed = parsed_log(path)
        session_model = parsed["firstModel"] or "unknown"
        events = parsed["events"]
        if not events:
            continue

        fork_baseline_status: Optional[str] = None
        inherited_usage: Optional[Dict[str, int]] = None
        effective_events = events
        if forked_from_id:
            fork_baseline_status, inherited_usage, effective_events = _resolve_fork_events(
                events,
                metadata,
                path_by_session_id,
                cached_events,
            )

        eligible_events = _eligible_child_events(events, metadata) if forked_from_id else events
        if forked_from_id:
            eligible_lines = {event["lineNumber"] for event in eligible_events}
            effective_events = [
                event for event in effective_events if event["lineNumber"] in eligible_lines
            ]
        raw_in_window = [
            event for event in eligible_events if start <= event["timestamp"] <= end
        ]

        initial_base = (
            inherited_usage
            if fork_baseline_status == "resolved" and inherited_usage
            else _empty_totals()
        )
        inclusive_rows, inclusive_delta, session_resets, session_anomalies = _event_deltas_for_window(
            effective_events,
            start,
            end,
            initial_base,
        )
        verified_base = initial_base
        if fork_baseline_status == "ambiguous" and inherited_usage:
            verified_base = inherited_usage
        elif fork_baseline_status == "unresolved" and effective_events:
            verified_base = min(effective_events, key=lambda item: item["lineNumber"])["usage"]
        verified_rows, verified_delta, _, _ = _event_deltas_for_window(
            effective_events,
            start,
            end,
            verified_base,
        )
        if model_filter:
            inclusive_rows = [
                row
                for row in inclusive_rows
                if (row["event"].get("model") or session_model) == model_filter
            ]
            verified_rows = [
                row
                for row in verified_rows
                if (row["event"].get("model") or session_model) == model_filter
            ]
            inclusive_delta = _sum_delta_rows(inclusive_rows)
            verified_delta = _sum_delta_rows(verified_rows)
            session_resets = sum(int(row["reset"]) for row in inclusive_rows)
            session_anomalies = sum(int(row["anomaly"]) for row in inclusive_rows)
        unverified_delta = _usage_difference(inclusive_delta, verified_delta)
        raw_delta_rows, raw_delta, _, _ = _event_deltas_for_window(
            events, start, end, _empty_totals()
        )
        corrected_all_rows, unfiltered_inclusive_delta, _, _ = _event_deltas_for_window(
            effective_events, start, end, initial_base
        )
        if model_filter:
            raw_delta = _sum_delta_rows(
                [
                    row
                    for row in raw_delta_rows
                    if (row["event"].get("model") or session_model) == model_filter
                ]
            )
            unfiltered_inclusive_delta = _sum_delta_rows(
                [
                    row
                    for row in corrected_all_rows
                    if (row["event"].get("model") or session_model) == model_filter
                ]
            )
        replay_excluded = max(
            raw_delta["total_tokens"] - unfiltered_inclusive_delta["total_tokens"], 0
        )

        fork_is_relevant = bool(
            forked_from_id
            and any(
                not model_filter
                or (event.get("model") or session_model) == model_filter
                for event in raw_in_window
            )
            and (created_at is None or created_at <= end)
        )
        if fork_is_relevant:
            fork_session_count += 1
            fork_replay_tokens_excluded += replay_excluded
            if fork_baseline_status == "resolved":
                resolved_fork_count += 1
            elif fork_baseline_status == "ambiguous":
                ambiguous_fork_count += 1
            elif fork_baseline_status == "not_replayed":
                not_replayed_fork_count += 1
            elif fork_baseline_status == "unresolved":
                unresolved_fork_count += 1

        if inclusive_rows or fork_is_relevant:
            damaged_line_count += parsed["damagedLineCount"]
            invalid_token_event_count += parsed["invalidTokenEventCount"]

        if not inclusive_rows:
            continue

        in_window = [row["event"] for row in inclusive_rows]
        first_event = min(in_window, key=lambda event: (event["timestamp"], event["lineNumber"]))
        last_event = max(in_window, key=lambda event: (event["timestamp"], event["lineNumber"]))
        delta = inclusive_delta
        token_event_count += len(in_window)
        counter_reset_count += session_resets
        counter_anomaly_count += session_anomalies
        for key in TOKEN_KEYS:
            totals[key] += delta[key]
            verified_totals[key] += verified_delta[key]
        verified_by_line = {
            row["event"]["lineNumber"]: row["delta"] for row in verified_rows
        }
        for row in inclusive_rows:
            event = row["event"]
            event_delta = row["delta"]
            event_verified_delta = verified_by_line.get(event["lineNumber"], _empty_totals())
            _add_event_to_timeline(
                timeline_buckets,
                event,
                event_delta,
                event_verified_delta,
                int(row["reset"]),
                int(row["anomaly"]),
            )

            # Per-event model attribution for accurate by-model accounting.
            event_model = event.get("model") or session_model
            model_bucket = by_model_totals.setdefault(event_model, _empty_totals())
            verified_model_bucket = verified_by_model_totals.setdefault(
                event_model, _empty_totals()
            )
            model_audit = by_model_audit.setdefault(event_model, _empty_audit())
            for key in TOKEN_KEYS:
                model_bucket[key] += event_delta[key]
                verified_model_bucket[key] += event_verified_delta[key]
            model_audit["counterResetCount"] += int(row["reset"])
            model_audit["counterAnomalyCount"] += int(row["anomaly"])

        # Track which models appeared in this session for session counting.
        session_models = set(
            (e.get("model") or session_model) for e in in_window
        )
        for sm in session_models:
            by_model_session_count[sm] = by_model_session_count.get(sm, 0) + 1
        audit_model = session_model if session_model in session_models else sorted(session_models)[0]
        audit = by_model_audit.setdefault(audit_model, _empty_audit())
        audit["damagedLineCount"] += parsed["damagedLineCount"]
        audit["invalidTokenEventCount"] += parsed["invalidTokenEventCount"]
        if fork_baseline_status:
            audit[_fork_status_count_key(fork_baseline_status)] += 1
        _add_session_audit_to_timeline(
            timeline_buckets,
            first_event,
            parsed["damagedLineCount"],
            parsed["invalidTokenEventCount"],
            fork_baseline_status,
        )

        session_rate_events = [_rate_snapshot(event) for event in in_window]
        rate_events.extend(snapshot for snapshot in session_rate_events if snapshot)
        session_rows.append(
            {
                "sessionFile": path.name,
                "sourcePath": str(path),
                "model": session_model,
                "firstEventAt": first_event["timestamp"].isoformat(),
                "lastEventAt": last_event["timestamp"].isoformat(),
                "tokenEvents": len(in_window),
                "forkedFromId": forked_from_id,
                "forkBaselineStatus": fork_baseline_status,
                "forkReplayTokensExcluded": replay_excluded,
                "forkSessionCount": int(bool(forked_from_id)),
                "resolvedForkCount": int(fork_baseline_status == "resolved"),
                "unresolvedForkCount": int(fork_baseline_status == "unresolved"),
                "ambiguousForkCount": int(fork_baseline_status == "ambiguous"),
                "notReplayedForkCount": int(fork_baseline_status == "not_replayed"),
                "counterResetCount": session_resets,
                "counterAnomalyCount": session_anomalies,
                "damagedLineCount": parsed["damagedLineCount"],
                "invalidTokenEventCount": parsed["invalidTokenEventCount"],
                **_public_usage(delta),
                "verifiedUsage": _public_usage(verified_delta),
                "unverifiedUsage": _public_usage(unverified_delta),
                "usageConfidence": (
                    "verified" if unverified_delta["total_tokens"] == 0 else "unverified"
                ),
                **_rate_summary_fields(session_rate_events),
            }
        )

    by_model: Dict[str, Dict[str, Any]] = {}
    for model in by_model_totals:
        model_verified = verified_by_model_totals.get(model, _empty_totals())
        model_audit = by_model_audit.get(model, _empty_audit())
        by_model[model] = {
            **_public_usage(by_model_totals[model]),
            "verifiedUsage": _public_usage(model_verified),
            "unverifiedUsage": _public_usage(
                _usage_difference(by_model_totals[model], model_verified)
            ),
            "sessionCount": by_model_session_count.get(model, 0),
            "usageConfidence": (
                "verified"
                if by_model_totals[model]["total_tokens"] == model_verified["total_tokens"]
                else "unverified"
            ),
            **model_audit,
        }

    unverified_totals = _usage_difference(totals, verified_totals)
    summary = {
        "windowStart": start.isoformat(),
        "windowEnd": end.isoformat(),
        "sourceRoot": str(codex_home or default_codex_home()),
        "sessionCount": len(session_rows),
        "tokenEventCount": token_event_count,
        "forkSessionCount": fork_session_count,
        "resolvedForkCount": resolved_fork_count,
        "unresolvedForkCount": unresolved_fork_count,
        "ambiguousForkCount": ambiguous_fork_count,
        "notReplayedForkCount": not_replayed_fork_count,
        "forkReplayTokensExcluded": fork_replay_tokens_excluded,
        "counterResetCount": counter_reset_count,
        "counterAnomalyCount": counter_anomaly_count,
        "damagedLineCount": damaged_line_count,
        "invalidTokenEventCount": invalid_token_event_count,
        **_public_usage(totals),
        "verifiedUsage": _public_usage(verified_totals),
        "unverifiedUsage": _public_usage(unverified_totals),
        "usageConfidence": (
            "verified" if unverified_totals["total_tokens"] == 0 else "unverified"
        ),
        "byModel": by_model,
    }
    summary.update(_rate_summary_fields(rate_events))
    return {
        "summary": summary,
        "sessions": session_rows,
        "timeline": _public_timeline(timeline_buckets),
    }


def read_token_events(path: Path) -> List[Dict[str, Any]]:
    """Read token_count events from a Codex session JSONL file.

    Each event includes a ``model`` field derived from the preceding
    ``turn_context`` event in the same file.  When no ``turn_context``
    has been seen yet (or the turn_context has no model), the field
    is ``None``.

    The single-pass scan also updates a running model state from
    turn_context events, making this more efficient than the previous
    two-pass approach (separate read_session_model + read_token_events).
    """
    return _read_session_log(path)["events"]


def _read_session_log(path: Path) -> Dict[str, Any]:
    events: List[Dict[str, Any]] = []
    current_model: Optional[str] = None
    first_model: Optional[str] = None
    damaged_line_count = 0
    invalid_token_event_count = 0
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line_number, line in enumerate(handle, start=1):
            replacement_seen = "\ufffd" in line
            if replacement_seen:
                damaged_line_count += 1
            has_tc = "turn_context" in line
            has_tk = "token_count" in line
            if not has_tc and not has_tk:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                if not replacement_seen:
                    damaged_line_count += 1
                continue

            if has_tc and record.get("type") == "turn_context":
                model = (record.get("payload") or {}).get("model")
                if model:
                    current_model = model
                    if first_model is None:
                        first_model = model
                continue

            if has_tk:
                payload = record.get("payload") or {}
                if payload.get("type") != "token_count":
                    continue
                usage = _validated_usage((payload.get("info") or {}).get("total_token_usage"))
                if usage is None:
                    invalid_token_event_count += 1
                    continue
                timestamp = _parse_timestamp(record.get("timestamp"))
                if not timestamp:
                    invalid_token_event_count += 1
                    continue
                events.append(
                    {
                        "timestamp": timestamp,
                        "lineNumber": line_number,
                        "usage": usage,
                        "rateLimits": payload.get("rate_limits") or {},
                        "model": current_model,
                    }
                )
    return {
        "events": events,
        "firstModel": first_model,
        "damagedLineCount": damaged_line_count,
        "invalidTokenEventCount": invalid_token_event_count,
    }


def _validated_usage(value: Any) -> Optional[Dict[str, int]]:
    if not isinstance(value, dict) or "total_tokens" not in value:
        return None
    usage: Dict[str, int] = {}
    for key in TOKEN_KEYS:
        raw = value.get(key, 0)
        if isinstance(raw, bool):
            return None
        try:
            parsed = int(raw)
        except (TypeError, ValueError, OverflowError):
            return None
        if parsed < 0 or (isinstance(raw, float) and not raw.is_integer()):
            return None
        usage[key] = parsed
    return usage


def read_session_metadata(path: Path) -> Dict[str, Any]:
    """Read only the first session_meta record, which belongs to this file."""
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line_number, line in enumerate(handle, start=1):
            if "session_meta" not in line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if record.get("type") != "session_meta":
                continue
            payload = record.get("payload") or {}
            return {
                "sessionId": payload.get("id"),
                "forkedFromId": payload.get("forked_from_id"),
                "createdAt": _parse_timestamp(payload.get("timestamp") or record.get("timestamp")),
                "sessionMetaLine": line_number,
            }
    return {
        "sessionId": None,
        "forkedFromId": None,
        "createdAt": None,
        "sessionMetaLine": None,
    }


def read_session_model(path: Path) -> Optional[str]:
    """Extract the model name from the first turn_context event in a session file.

    For multi-model sessions (rare, <2% in practice), this returns the model
    from the first turn_context, which is a reasonable approximation for
    session-level aggregation.

    Returns None if no turn_context event is found in the file.
    """
    return _read_session_log(path)["firstModel"]


def _resolve_fork_events(
    child_events: List[Dict[str, Any]],
    metadata: Dict[str, Any],
    path_by_session_id: Dict[str, Path],
    cached_events: Any,
) -> Tuple[str, Optional[Dict[str, int]], List[Dict[str, Any]]]:
    parent_path = path_by_session_id.get(metadata.get("forkedFromId"))
    created_at = metadata.get("createdAt")
    if parent_path is None or created_at is None:
        return "unresolved", None, child_events

    parent_events = sorted(
        (
            event
            for event in cached_events(parent_path)
            if event["timestamp"] <= created_at
        ),
        key=lambda item: item["lineNumber"],
    )
    parent_baseline = parent_events[-1] if parent_events else None
    if parent_baseline is None:
        return "unresolved", None, child_events

    prefix_end = created_at + _FORK_PREFIX_GRACE
    eligible_events = _eligible_child_events(child_events, metadata)
    prefix_events = [
        event for event in eligible_events if event["timestamp"] <= prefix_end
    ]
    cutoff_line = _matching_replay_cutoff(prefix_events, parent_events, parent_baseline)
    if cutoff_line is not None:
        effective_events = [event for event in eligible_events if event["lineNumber"] > cutoff_line]
        return "resolved", parent_baseline["usage"], effective_events
    if not prefix_events:
        return "not_replayed", None, child_events
    first_usage = min(prefix_events, key=lambda item: item["lineNumber"])["usage"]
    if first_usage["total_tokens"] < parent_baseline["usage"]["total_tokens"]:
        return "not_replayed", None, eligible_events
    return "ambiguous", parent_baseline["usage"], eligible_events


def _eligible_child_events(
    child_events: Sequence[Dict[str, Any]], metadata: Dict[str, Any]
) -> List[Dict[str, Any]]:
    created_at = metadata.get("createdAt")
    meta_line = metadata.get("sessionMetaLine")
    return [
        event
        for event in child_events
        if (meta_line is None or event["lineNumber"] > meta_line)
        and (created_at is None or event["timestamp"] >= created_at)
    ]


def _matching_replay_cutoff(
    child_prefix: Sequence[Dict[str, Any]],
    parent_events: Sequence[Dict[str, Any]],
    parent_baseline: Dict[str, Any],
) -> Optional[int]:
    ordered_child = sorted(child_prefix, key=lambda item: item["lineNumber"])
    ordered_parent = sorted(parent_events, key=lambda item: item["lineNumber"])
    cutoffs: List[int] = []
    for index, event in enumerate(ordered_child):
        candidate = ordered_child[: index + 1]
        if len(candidate) < 2 or len(candidate) > len(ordered_parent):
            continue
        if not _usage_matches(event["usage"], parent_baseline["usage"]):
            continue
        parent_suffix = ordered_parent[-len(candidate) :]
        if all(
            _usage_matches(child["usage"], parent["usage"])
            for child, parent in zip(candidate, parent_suffix)
        ):
            cutoffs.append(event["lineNumber"])
    return max(cutoffs) if cutoffs else None


def _usage_matches(left: Dict[str, int], right: Dict[str, int]) -> bool:
    return all(int(left.get(key) or 0) == int(right.get(key) or 0) for key in TOKEN_KEYS)


def render_codex_report(report: Dict[str, Any], lang: str = "en") -> str:
    normalized = normalize_lang(lang)
    text = TEXT[normalized]
    summary = report["summary"]
    confidence_labels = (
        ("Inclusive", "Verified", "Unverified")
        if normalized == "en"
        else ("Inclusive（含不确定量）", "Verified（已验证）", "Unverified（未验证）")
    )
    lines = [
        text["title"],
        "",
        f"{text['window']}: {summary['windowStart']} -> {summary['windowEnd']}",
        f"{text['sources']}: {summary['sourceRoot']}",
        "",
        f"{text['fork_audit']}: "
        + text["fork_audit_detail"].format(
            forks=summary.get("forkSessionCount", 0),
            resolved=summary.get("resolvedForkCount", 0),
            unresolved=summary.get("unresolvedForkCount", 0),
            excluded=_format_int(summary.get("forkReplayTokensExcluded")),
        ),
    ]
    if normalized == "en":
        lines.append(
            f"Fork states: ambiguous={summary.get('ambiguousForkCount', 0)}, "
            f"not_replayed={summary.get('notReplayedForkCount', 0)}."
        )
    else:
        lines.append(
            f"Fork 状态：ambiguous={summary.get('ambiguousForkCount', 0)}，"
            f"not_replayed={summary.get('notReplayedForkCount', 0)}。"
        )
    if summary.get("unresolvedForkCount"):
        lines.extend([text["fork_warning"], ""])
    lines.extend(
        [
            f"{confidence_labels[0]} Total: {_format_int(summary.get('totalTokens'))}",
            f"{confidence_labels[1]} Total: {_format_int((summary.get('verifiedUsage') or {}).get('totalTokens'))}",
            f"{confidence_labels[2]} Total: {_format_int((summary.get('unverifiedUsage') or {}).get('totalTokens'))}",
        ]
    )
    if summary.get("unverifiedUsage", {}).get("totalTokens"):
        lines.append(
            "Warning: inclusive usage contains an unverified amount."
            if normalized == "en"
            else "警告：Inclusive 用量中包含尚未验证的部分。"
        )
    if summary.get("damagedLineCount") or summary.get("invalidTokenEventCount"):
        warning = (
            "Data quality warning"
            if normalized == "en"
            else "数据质量警告"
        )
        lines.extend(
            [
                f"{warning}: damaged lines={summary.get('damagedLineCount', 0)}, "
                f"invalid token events={summary.get('invalidTokenEventCount', 0)}",
                "",
            ]
        )
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

    by_model = summary.get("byModel") or {}
    if by_model:
        lines.extend(
            [
                "",
                text["by_model"],
                *render_table(
                    text["model_headers"],
                    [
                        [
                            model,
                            str(data.get("sessionCount") or 0),
                            _format_int(data.get("inputTokens")),
                            _format_int(data.get("cachedInputTokens")),
                            _format_int(data.get("outputTokens")),
                            _format_int(data.get("totalTokens")),
                        ]
                        for model, data in sorted(by_model.items())
                    ],
                ),
            ]
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
                        row.get("model") or "unknown",
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
        "model",
        "sourcePath",
        "firstEventAt",
        "lastEventAt",
        "tokenEvents",
        "forkedFromId",
        "forkBaselineStatus",
        "forkSessionCount",
        "resolvedForkCount",
        "unresolvedForkCount",
        "forkReplayTokensExcluded",
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
        "verifiedInputTokens",
        "verifiedCachedInputTokens",
        "verifiedNonCachedInputTokens",
        "verifiedOutputTokens",
        "verifiedReasoningOutputTokens",
        "verifiedTotalTokens",
        "unverifiedInputTokens",
        "unverifiedCachedInputTokens",
        "unverifiedNonCachedInputTokens",
        "unverifiedOutputTokens",
        "unverifiedReasoningOutputTokens",
        "unverifiedTotalTokens",
        "usageConfidence",
        "ambiguousForkCount",
        "notReplayedForkCount",
        "damagedLineCount",
        "invalidTokenEventCount",
        "counterResetCount",
        "counterAnomalyCount",
    ]
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in report["sessions"]:
            flattened = dict(row)
            flattened.update(_flatten_usage("verified", row.get("verifiedUsage") or {}))
            flattened.update(_flatten_usage("unverified", row.get("unverifiedUsage") or {}))
            writer.writerow({key: flattened.get(key) for key in fieldnames})
        summary = {"sessionFile": "TOTAL", "tokenEvents": report["summary"]["tokenEventCount"]}
        summary.update({key: report["summary"].get(key) for key in fieldnames if key in report["summary"]})
        summary.update(_flatten_usage("verified", report["summary"].get("verifiedUsage") or {}))
        summary.update(_flatten_usage("unverified", report["summary"].get("unverifiedUsage") or {}))
        writer.writerow({key: summary.get(key) for key in fieldnames})


def _flatten_usage(prefix: str, usage: Dict[str, Any]) -> Dict[str, int]:
    return {
        f"{prefix}InputTokens": int(usage.get("inputTokens") or 0),
        f"{prefix}CachedInputTokens": int(usage.get("cachedInputTokens") or 0),
        f"{prefix}NonCachedInputTokens": int(usage.get("nonCachedInputTokens") or 0),
        f"{prefix}OutputTokens": int(usage.get("outputTokens") or 0),
        f"{prefix}ReasoningOutputTokens": int(usage.get("reasoningOutputTokens") or 0),
        f"{prefix}TotalTokens": int(usage.get("totalTokens") or 0),
    }


def _rate_snapshot(event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    limits = event.get("rateLimits") or {}
    primary = limits.get("primary") or {}
    secondary = limits.get("secondary") or {}
    if not primary and not secondary:
        return None
    return {
        "timestamp": event["timestamp"],
        "primaryUsedPercent": _optional_float(primary.get("used_percent")),
        "primaryResetsAt": _timestamp_from_epoch(primary.get("resets_at")),
        "secondaryUsedPercent": _optional_float(secondary.get("used_percent")),
        "secondaryResetsAt": _timestamp_from_epoch(secondary.get("resets_at")),
    }


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


def _event_deltas_for_window(
    events: Sequence[Dict[str, Any]],
    start: datetime,
    end: datetime,
    initial_base: Dict[str, int],
) -> Tuple[List[Dict[str, Any]], Dict[str, int], int, int]:
    rows: List[Dict[str, Any]] = []
    totals = _empty_totals()
    previous = initial_base
    reset_count = 0
    anomaly_count = 0
    for event in sorted(events, key=lambda item: item["lineNumber"]):
        current = event["usage"]
        reset = int(current["total_tokens"] < previous["total_tokens"])
        if reset:
            delta = {key: int(current.get(key) or 0) for key in TOKEN_KEYS}
        else:
            delta = _usage_delta(previous, current)
        anomaly = int(
            not reset
            and any(
                int(current.get(key) or 0) < int(previous.get(key) or 0)
                for key in TOKEN_KEYS
                if key != "total_tokens"
            )
        )
        previous = current
        if not start <= event["timestamp"] <= end:
            continue
        rows.append({"event": event, "delta": delta, "reset": reset, "anomaly": anomaly})
        for key in TOKEN_KEYS:
            totals[key] += delta[key]
        reset_count += reset
        anomaly_count += anomaly
    return rows, totals, reset_count, anomaly_count


def _sum_delta_rows(rows: Sequence[Dict[str, Any]]) -> Dict[str, int]:
    totals = _empty_totals()
    for row in rows:
        for key in TOKEN_KEYS:
            totals[key] += int(row["delta"].get(key) or 0)
    return totals


def _usage_delta(base: Dict[str, int], current: Dict[str, int]) -> Dict[str, int]:
    return {key: max(int(current.get(key) or 0) - int(base.get(key) or 0), 0) for key in TOKEN_KEYS}


def _usage_difference(left: Dict[str, int], right: Dict[str, int]) -> Dict[str, int]:
    return {
        key: max(int(left.get(key) or 0) - int(right.get(key) or 0), 0)
        for key in TOKEN_KEYS
    }


def _new_timeline_buckets(start: datetime, end: datetime) -> List[Dict[str, Any]]:
    span = _timeline_bucket_span(start, end)
    buckets: List[Dict[str, Any]] = []
    display_tz = start.tzinfo
    utc_end = end.astimezone(timezone.utc)
    calendar_aligned = span >= timedelta(days=1)
    cursor = start if calendar_aligned else start.astimezone(timezone.utc)
    while cursor.astimezone(timezone.utc) <= utc_end:
        candidate_end = cursor + span
        bucket_end = end if candidate_end.astimezone(timezone.utc) > utc_end else candidate_end
        buckets.append(
            {
                "bucketStart": cursor.astimezone(display_tz),
                "bucketEnd": bucket_end.astimezone(display_tz),
                "tokenEvents": 0,
                "rateTimestamp": None,
                "primaryUsedPercent": None,
                "secondaryUsedPercent": None,
                "verifiedTotals": _empty_totals(),
                **_empty_audit(),
                **_empty_totals(),
            }
        )
        cursor = bucket_end
        if cursor.astimezone(timezone.utc) == utc_end:
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
                "verifiedTotals": _empty_totals(),
                **_empty_audit(),
                **_empty_totals(),
            }
        )
    return buckets


def _timeline_bucket_span(start: datetime, end: datetime) -> timedelta:
    duration = end.astimezone(timezone.utc) - start.astimezone(timezone.utc)
    if duration <= timedelta(days=2):
        return timedelta(hours=1)
    if duration <= timedelta(days=31):
        return timedelta(days=1)
    return timedelta(days=7)


def _add_event_to_timeline(
    buckets: List[Dict[str, Any]],
    event: Dict[str, Any],
    delta: Dict[str, int],
    verified_delta: Dict[str, int],
    reset: int,
    anomaly: int,
) -> None:
    if not buckets:
        return
    bucket = buckets[_timeline_bucket_index(buckets, event["timestamp"])]
    bucket["tokenEvents"] += 1
    bucket["counterResetCount"] += reset
    bucket["counterAnomalyCount"] += anomaly
    for key in TOKEN_KEYS:
        bucket[key] += delta[key]
        bucket["verifiedTotals"][key] += verified_delta[key]

    snapshot = _rate_snapshot(event)
    if not snapshot:
        return
    if bucket["rateTimestamp"] and snapshot["timestamp"] < bucket["rateTimestamp"]:
        return
    bucket["rateTimestamp"] = snapshot["timestamp"]
    bucket["primaryUsedPercent"] = snapshot.get("primaryUsedPercent")
    bucket["secondaryUsedPercent"] = snapshot.get("secondaryUsedPercent")


def _add_session_audit_to_timeline(
    buckets: List[Dict[str, Any]],
    event: Dict[str, Any],
    damaged_lines: int,
    invalid_events: int,
    fork_status: Optional[str],
) -> None:
    if not buckets:
        return
    bucket = buckets[_timeline_bucket_index(buckets, event["timestamp"])]
    bucket["damagedLineCount"] += damaged_lines
    bucket["invalidTokenEventCount"] += invalid_events
    if fork_status:
        bucket[_fork_status_count_key(fork_status)] += 1


def _timeline_bucket_index(
    buckets: Sequence[Dict[str, Any]], timestamp: datetime
) -> int:
    target = timestamp.astimezone(timezone.utc)
    low = 0
    high = len(buckets)
    while low < high:
        middle = (low + high) // 2
        bucket_start = buckets[middle]["bucketStart"].astimezone(timezone.utc)
        if bucket_start <= target:
            low = middle + 1
        else:
            high = middle
    return min(max(low - 1, 0), len(buckets) - 1)


def _public_timeline(buckets: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for bucket in buckets:
        verified = bucket["verifiedTotals"]
        row = {
            "bucketStart": bucket["bucketStart"].isoformat(),
            "bucketEnd": bucket["bucketEnd"].isoformat(),
            "tokenEvents": bucket["tokenEvents"],
            **_public_usage(bucket),
            "verifiedUsage": _public_usage(verified),
            "unverifiedUsage": _public_usage(_usage_difference(bucket, verified)),
            "usageConfidence": (
                "verified" if bucket["total_tokens"] == verified["total_tokens"] else "unverified"
            ),
            **{key: bucket[key] for key in _empty_audit()},
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


def _empty_audit() -> Dict[str, int]:
    return {
        "resolvedForkCount": 0,
        "unresolvedForkCount": 0,
        "ambiguousForkCount": 0,
        "notReplayedForkCount": 0,
        "damagedLineCount": 0,
        "invalidTokenEventCount": 0,
        "counterResetCount": 0,
        "counterAnomalyCount": 0,
    }


def _fork_status_count_key(status: str) -> str:
    return {
        "resolved": "resolvedForkCount",
        "unresolved": "unresolvedForkCount",
        "ambiguous": "ambiguousForkCount",
        "not_replayed": "notReplayedForkCount",
    }[status]


def _parse_timestamp(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.astimezone(LOCAL_TIMEZONE)


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise UsageError(f'Could not parse date "{value}". Use YYYY-MM-DD.')


def _day_bounds(
    value: date,
    end: Optional[datetime] = None,
    tz: Optional[tzinfo] = None,
) -> Tuple[datetime, datetime]:
    local_tz = tz or LOCAL_TIMEZONE
    start = datetime.combine(value, time.min, tzinfo=local_tz)
    if end:
        return start, end
    return start, datetime.combine(value, time.max, tzinfo=local_tz)


def _parse_datetime_filter(
    value: str,
    end_of_day: bool = False,
    tz: Optional[tzinfo] = None,
) -> datetime:
    local_tz = tz or LOCAL_TIMEZONE
    if len(value) == 10:
        parsed_date = _parse_date(value)
        parsed_time = time.max if end_of_day else time.min
        return datetime.combine(parsed_date, parsed_time, tzinfo=local_tz)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise UsageError(f'Could not parse datetime "{value}". Use YYYY-MM-DD or an ISO timestamp.')
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=local_tz)
    return parsed.astimezone(local_tz)


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
        return datetime.fromtimestamp(float(value), tz=LOCAL_TIMEZONE).isoformat()
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

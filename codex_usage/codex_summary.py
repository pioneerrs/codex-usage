from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from .codex_cost import _format_credits, _format_money
from .reporting import normalize_lang, render_table


TEXT = {
    "en": {
        "title": "Codex Usage Summary",
        "window": "Window",
        "source": "Source",
        "overview": "Overview",
        "rate_limits": "Rate Limits",
        "rate_windows": "Rate-limit Windows",
        "hot_sessions": "Hot Sessions",
        "charts": "Charts",
        "notes": "Notes:",
        "total_tokens": "Total Tokens",
        "non_cached_input": "Non-cached Input",
        "cached_input": "Cached Input",
        "output": "Output",
        "reasoning": "Reasoning",
        "api_cost": "API Equivalent",
        "credits": "Codex Credits",
        "sessions": "Sessions",
        "events": "Token Events",
        "limit": "Limit",
        "used_first": "Used First",
        "used_latest": "Used Latest",
        "remaining_latest": "Remaining",
        "used_delta": "Used Delta",
        "used_max": "Used Max",
        "reset": "Reset",
        "latest_event": "Latest Event",
        "used": "Used",
        "remaining": "Remaining",
        "snapshots": "Snapshots",
        "primary": "primary",
        "secondary": "secondary",
        "session": "Session",
        "metric": "Metric",
        "value": "Value",
        "last_event": "Last Event",
        "largest_total": "Largest total",
        "largest_output": "Largest output",
        "largest_cached": "Largest cached input",
        "longest_active": "Longest active window",
        "cache_ratio": "Cache ratio",
        "output_ratio": "Output ratio",
        "usage_chart": "Usage chart",
        "cost_chart": "Cost chart",
        "unavailable": "unavailable",
        "not_written": "not written",
        "note_estimate": "Token values come from local Codex token_count logs. Cost is an API-equivalent estimate, not a subscription bill.",
        "note_reasoning": "Reasoning tokens are already included in output tokens and are not charged again.",
        "note_window": "Session duration is measured only inside the selected report window.",
        "note_rate_windows": "If multiple rate-limit reset windows appear, compare the Reset value with Settings before treating one as current.",
    },
    "zh": {
        "title": "Codex 用量总览",
        "window": "时间窗口",
        "source": "数据来源",
        "overview": "总览",
        "rate_limits": "限额",
        "rate_windows": "限额窗口",
        "hot_sessions": "重点 Session",
        "charts": "图表",
        "notes": "说明：",
        "total_tokens": "Total Tokens",
        "non_cached_input": "非缓存 Input",
        "cached_input": "Cached Input",
        "output": "Output",
        "reasoning": "Reasoning",
        "api_cost": "API 等价金额",
        "credits": "Codex Credits",
        "sessions": "Sessions",
        "events": "Token 事件数",
        "limit": "限额",
        "used_first": "已用起始",
        "used_latest": "已用最新",
        "remaining_latest": "剩余最新",
        "used_delta": "已用变化",
        "used_max": "已用最高",
        "reset": "重置时间",
        "latest_event": "最后快照",
        "used": "已用",
        "remaining": "剩余",
        "snapshots": "快照数",
        "primary": "primary",
        "secondary": "secondary",
        "session": "Session",
        "metric": "指标",
        "value": "数值",
        "last_event": "最后事件",
        "largest_total": "最大 total",
        "largest_output": "最大 output",
        "largest_cached": "最大 cached input",
        "longest_active": "最长活跃窗口",
        "cache_ratio": "Cache 占比",
        "output_ratio": "Output 占比",
        "usage_chart": "用量图表",
        "cost_chart": "费用图表",
        "unavailable": "不可用",
        "not_written": "未写入",
        "note_estimate": "Token 数值来自本机 Codex token_count 日志。费用是 API 等价估算，不代表订阅真实账单。",
        "note_reasoning": "Reasoning token 已包含在 output token 中，不重复计费。",
        "note_window": "Session 活跃时长只按当前统计窗口内的首尾事件估算。",
        "note_rate_windows": "如果出现多个限额重置窗口，先用 Settings 里的重置日期匹配对应窗口，再判断当前剩余额度。",
    },
}


def build_codex_summary(
    usage_report: Dict[str, Any],
    cost_report: Dict[str, Any],
    usage_chart_path: Optional[str] = None,
    cost_chart_path: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "usage": usage_report["summary"],
        "cost": cost_report["summary"],
        "hotSessions": _hot_sessions(usage_report.get("sessions") or []),
        "charts": {
            "usage": usage_chart_path,
            "cost": cost_chart_path,
        },
    }


def render_codex_summary(summary: Dict[str, Any], lang: str = "en") -> str:
    text = TEXT[normalize_lang(lang)]
    usage = summary["usage"]
    cost = summary["cost"]
    hot_sessions = summary.get("hotSessions") or []
    charts = summary.get("charts") or {}

    lines = [
        text["title"],
        "",
        f"{text['window']}: {usage['windowStart']} -> {usage['windowEnd']}",
        f"{text['source']}: {usage['sourceRoot']}",
        "",
        text["overview"],
    ]
    lines.extend(
        render_table(
            [text["total_tokens"], text["cached_input"], text["non_cached_input"], text["output"], text["reasoning"], text["api_cost"], text["credits"]],
            [
                [
                    _format_int(usage.get("totalTokens")),
                    _format_int(usage.get("cachedInputTokens")),
                    _format_int(usage.get("nonCachedInputTokens")),
                    _format_int(usage.get("outputTokens")),
                    _format_int(usage.get("reasoningOutputTokens")),
                    _format_money(cost.get("totalCostUSD") or 0.0),
                    _format_credits(cost.get("totalCredits") or 0.0),
                ]
            ],
        )
    )
    lines.extend(
        [
            "",
            text["rate_limits"],
            *render_table(
                [
                    text["limit"],
                    text["used_first"],
                    text["used_latest"],
                    text["remaining_latest"],
                    text["used_delta"],
                    text["used_max"],
                    text["reset"],
                ],
                [
                    _rate_row("primary", usage, text),
                    _rate_row("secondary", usage, text),
                ],
            ),
            "",
            text["rate_windows"],
            *render_table(
                [text["limit"], text["reset"], text["latest_event"], text["used"], text["remaining"], text["snapshots"]],
                _rate_window_rows(usage, text),
            ),
            "",
            text["hot_sessions"],
            *render_table(
                [
                    text["metric"],
                    text["session"],
                    text["value"],
                    text["cache_ratio"],
                    text["output_ratio"],
                    text["last_event"],
                ],
                [
                    [
                        text[item["metric"]],
                        item["sessionFile"],
                        item["displayValue"],
                        _format_ratio(item.get("cacheRatio"), text["unavailable"]),
                        _format_ratio(item.get("outputRatio"), text["unavailable"]),
                        item["lastEventAt"],
                    ]
                    for item in hot_sessions
                ],
            ),
            "",
            text["charts"],
            *render_table(
                [text["metric"], text["value"]],
                [
                    [text["usage_chart"], charts.get("usage") or text["not_written"]],
                    [text["cost_chart"], charts.get("cost") or text["not_written"]],
                ],
            ),
            "",
            text["notes"],
            f"- {text['note_estimate']}",
            f"- {text['note_reasoning']}",
            f"- {text['note_window']}",
            f"- {text['note_rate_windows']}",
        ]
    )
    return "\n".join(lines)


def _hot_sessions(sessions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not sessions:
        return []

    items: List[Dict[str, Any]] = []
    for metric, key in (
        ("largest_total", "totalTokens"),
        ("largest_output", "outputTokens"),
        ("largest_cached", "cachedInputTokens"),
    ):
        row = max(sessions, key=lambda item: int(item.get(key) or 0))
        items.append(_session_metric(metric, row, _format_int(row.get(key))))

    longest = max(sessions, key=_session_duration_seconds)
    duration = _format_duration(_session_duration_seconds(longest))
    items.append(_session_metric("longest_active", longest, duration))

    return items


def _session_metric(metric: str, row: Dict[str, Any], display_value: str) -> Dict[str, Any]:
    return {
        "metric": metric,
        "sessionFile": str(row.get("sessionFile") or ""),
        "displayValue": display_value,
        "lastEventAt": str(row.get("lastEventAt") or ""),
        "cacheRatio": _ratio(row.get("cachedInputTokens"), row.get("inputTokens")),
        "outputRatio": _ratio(row.get("outputTokens"), row.get("totalTokens")),
    }


def _session_duration_seconds(row: Dict[str, Any]) -> int:
    start = _parse_datetime(row.get("firstEventAt"))
    end = _parse_datetime(row.get("lastEventAt"))
    if not start or not end or end < start:
        return 0
    return int((end - start).total_seconds())


def _parse_datetime(value: Any) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _rate_row(prefix: str, usage: Dict[str, Any], text: Dict[str, str]) -> List[str]:
    key = f"{prefix}UsedPercent"
    return [
        text[prefix],
        _format_percent(usage.get(f"{key}First"), text["unavailable"]),
        _format_percent(usage.get(f"{key}Latest"), text["unavailable"]),
        _format_percent(usage.get(f"{prefix}RemainingPercentLatest"), text["unavailable"]),
        _format_percent(usage.get(f"{key}Delta"), text["unavailable"], signed=True),
        _format_percent(usage.get(f"{key}Max"), text["unavailable"]),
        str(usage.get(f"{prefix}ResetsAt") or text["unavailable"]),
    ]


def _rate_window_rows(usage: Dict[str, Any], text: Dict[str, str]) -> List[List[str]]:
    rows: List[List[str]] = []
    for prefix in ("primary", "secondary"):
        for window in usage.get(f"{prefix}Windows") or []:
            rows.append(
                [
                    text[prefix],
                    str(window.get("resetsAt") or text["unavailable"]),
                    str(window.get("latestAt") or text["unavailable"]),
                    _format_percent(window.get("usedPercentLatest"), text["unavailable"]),
                    _format_percent(window.get("remainingPercentLatest"), text["unavailable"]),
                    _format_int(window.get("snapshotCount")),
                ]
            )
    if rows:
        return rows
    return [[text["unavailable"], text["unavailable"], text["unavailable"], text["unavailable"], text["unavailable"], "0"]]


def _format_int(value: Any) -> str:
    return f"{int(value or 0):,}"


def _format_percent(value: Any, unavailable: str, signed: bool = False) -> str:
    if value is None:
        return unavailable
    number = float(value)
    sign = "+" if signed and number > 0 else ""
    return f"{sign}{number:g}%"


def _ratio(part: Any, total: Any) -> Optional[float]:
    denominator = float(total or 0)
    if denominator <= 0:
        return None
    return float(part or 0) / denominator


def _format_duration(seconds: int) -> str:
    if seconds <= 0:
        return "0m"
    minutes = seconds // 60
    hours = minutes // 60
    days = hours // 24
    if days:
        return f"{days}d {hours % 24}h"
    if hours:
        return f"{hours}h {minutes % 60}m"
    return f"{minutes}m"


def _format_ratio(value: Any, unavailable: str) -> str:
    if value is None:
        return unavailable
    return f"{float(value) * 100:.1f}%"

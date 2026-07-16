from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from .codex_cost import _format_credits, _format_money
from .reporting import normalize_lang, render_table


TEXT = {
    "en": {
        "title": "Codex Usage Summary",
        "fork_audit": "Fork replay audit: {forks} forks, {resolved} resolved, {unresolved} unresolved, {excluded} inherited tokens excluded.",
        "unknown_warning": "Warning: unknown model(s) {models} used the fallback rate card.",
        "window": "Window",
        "source": "Source",
        "overview": "Overview",
        "rate_limits": "Rate Limits",
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
        "first": "First",
        "latest": "Latest",
        "delta": "Delta",
        "max": "Max",
        "reset": "Reset",
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
    },
    "zh": {
        "fork_audit": "Fork 继承审计：{forks} 个 fork，{resolved} 个已解析，{unresolved} 个无法解析，排除 {excluded} 个继承 token。",
        "unknown_warning": "警告：未知模型 {models} 使用了默认费率。",
        "title": "Codex 用量总览",
        "window": "时间窗口",
        "source": "数据来源",
        "overview": "总览",
        "rate_limits": "限额",
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
        "first": "起始",
        "latest": "最新",
        "delta": "变化",
        "max": "最高",
        "reset": "重置时间",
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
        "unknownModels": cost_report.get("unknownModels") or [],
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
        text["fork_audit"].format(
            forks=usage.get("forkSessionCount", 0),
            resolved=usage.get("resolvedForkCount", 0),
            unresolved=usage.get("unresolvedForkCount", 0),
            excluded=_format_int(usage.get("forkReplayTokensExcluded")),
        ),
        text["overview"],
    ]
    unknown_models = summary.get("unknownModels") or []
    if unknown_models:
        lines.insert(-1, text["unknown_warning"].format(models=", ".join(unknown_models)))
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
                [text["limit"], text["first"], text["latest"], text["delta"], text["max"], text["reset"]],
                [
                    _rate_row("primary", usage, text),
                    _rate_row("secondary", usage, text),
                ],
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
        _format_percent(usage.get(f"{key}Delta"), text["unavailable"], signed=True),
        _format_percent(usage.get(f"{key}Max"), text["unavailable"]),
        str(usage.get(f"{prefix}ResetsAt") or text["unavailable"]),
    ]


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

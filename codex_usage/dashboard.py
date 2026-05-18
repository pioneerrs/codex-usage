from __future__ import annotations

import json
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .codex_cost import _format_credits, _format_money
from .codex_logs import _format_int, _format_percent
from .reporting import normalize_lang


TEXT = {
    "en": {
        "title": "Codex Usage Pulse",
        "subtitle": "Public rolling dashboard generated from local Codex token_count aggregates. Pick any cadence you want; this repository publishes a 3-hour example.",
        "generated": "Generated",
        "window": "Snapshot Window",
        "latest": "Latest Snapshot",
        "history": "Rolling History",
        "snapshots": "Snapshots",
        "total_tokens": "Tokens",
        "api_cost": "API Equivalent",
        "credits": "Credits",
        "remaining": "Weekly Remaining",
        "events": "Events",
        "sessions": "Sessions",
        "token_mix": "Token Mix",
        "rate_limit": "Rate Limit",
        "non_cached_input": "Non-cached input",
        "cached_input": "Cached input",
        "output": "Output",
        "reasoning": "Reasoning",
        "primary": "primary",
        "secondary": "secondary",
        "reset": "Reset",
        "used": "Used",
        "table_time": "Time",
        "table_window": "Window",
        "table_tokens": "Tokens",
        "table_cost": "API Equivalent",
        "table_remaining": "Remaining",
        "empty": "No snapshots yet.",
        "note": "Cost is an API-equivalent estimate, not a subscription bill. Reasoning tokens are included in output tokens and are not charged again.",
        "written": "Wrote Codex usage dashboard to",
    },
    "zh": {
        "title": "Codex 用量脉搏",
        "subtitle": "公开版滚动看板，来自本机 Codex token_count 日志的聚合结果。监控周期可以自行配置；这个仓库公开的是 3 小时示例。",
        "generated": "生成时间",
        "window": "快照窗口",
        "latest": "最新快照",
        "history": "滚动走势",
        "snapshots": "快照记录",
        "total_tokens": "Tokens",
        "api_cost": "API 等价金额",
        "credits": "Credits",
        "remaining": "Weekly 剩余",
        "events": "事件数",
        "sessions": "Sessions",
        "token_mix": "Token 构成",
        "rate_limit": "限额",
        "non_cached_input": "非缓存 input",
        "cached_input": "Cached input",
        "output": "Output",
        "reasoning": "Reasoning",
        "primary": "primary",
        "secondary": "secondary",
        "reset": "重置",
        "used": "已用",
        "table_time": "时间",
        "table_window": "窗口",
        "table_tokens": "Tokens",
        "table_cost": "API 等价",
        "table_remaining": "剩余",
        "empty": "还没有快照。",
        "note": "费用是 API 等价估算，不代表订阅真实账单。Reasoning token 已包含在 output token 中，不重复计费。",
        "written": "已写入 Codex 用量看板:",
    },
}


def build_dashboard_snapshot(
    usage_report: Dict[str, Any],
    cost_report: Dict[str, Any],
    interval_hours: int = 3,
    generated_at: Optional[datetime] = None,
) -> Dict[str, Any]:
    now = generated_at or datetime.now().astimezone()
    usage = usage_report["summary"]
    cost = cost_report["summary"]
    return {
        "generatedAt": now.isoformat(timespec="seconds"),
        "bucketStart": _bucket_start(now, interval_hours).isoformat(timespec="seconds"),
        "windowStart": usage.get("windowStart"),
        "windowEnd": usage.get("windowEnd"),
        "sessionCount": int(usage.get("sessionCount") or 0),
        "tokenEventCount": int(usage.get("tokenEventCount") or 0),
        "inputTokens": int(usage.get("inputTokens") or 0),
        "cachedInputTokens": int(usage.get("cachedInputTokens") or 0),
        "nonCachedInputTokens": int(usage.get("nonCachedInputTokens") or 0),
        "outputTokens": int(usage.get("outputTokens") or 0),
        "reasoningOutputTokens": int(usage.get("reasoningOutputTokens") or 0),
        "totalTokens": int(usage.get("totalTokens") or 0),
        "totalCostUSD": float(cost.get("totalCostUSD") or 0.0),
        "totalCredits": float(cost.get("totalCredits") or 0.0),
        "primaryUsedPercentLatest": usage.get("primaryUsedPercentLatest"),
        "primaryRemainingPercentLatest": usage.get("primaryRemainingPercentLatest"),
        "primaryResetsAt": usage.get("primaryResetsAt"),
        "secondaryUsedPercentLatest": usage.get("secondaryUsedPercentLatest"),
        "secondaryRemainingPercentLatest": usage.get("secondaryRemainingPercentLatest"),
        "secondaryResetsAt": usage.get("secondaryResetsAt"),
    }


def load_dashboard_history(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if isinstance(payload, dict):
        rows = payload.get("snapshots")
    else:
        rows = payload
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def write_dashboard_history(path: Path, history: Sequence[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "updatedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        "snapshots": list(history),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def upsert_dashboard_snapshot(
    history: Sequence[Dict[str, Any]],
    snapshot: Dict[str, Any],
    max_snapshots: int = 240,
) -> List[Dict[str, Any]]:
    rows = [dict(row) for row in history if row.get("generatedAt")]
    bucket = snapshot.get("bucketStart")
    replaced = False
    for index, row in enumerate(rows):
        if row.get("bucketStart") == bucket:
            rows[index] = snapshot
            replaced = True
            break
    if not replaced:
        rows.append(snapshot)
    rows.sort(key=lambda row: str(row.get("generatedAt") or ""))
    if max_snapshots > 0:
        rows = rows[-max_snapshots:]
    return rows


def render_dashboard_html(history: Sequence[Dict[str, Any]], lang: str = "en") -> str:
    normalized = normalize_lang(lang)
    text = TEXT[normalized]
    rows = sorted([row for row in history if row.get("generatedAt")], key=lambda row: str(row["generatedAt"]))
    latest = rows[-1] if rows else {}
    generated = datetime.now().astimezone().isoformat(timespec="seconds")
    html_lang = "zh-CN" if normalized == "zh" else "en"

    return "\n".join(
        [
            "<!doctype html>",
            f'<html lang="{html_lang}">',
            "<head>",
            '<meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1">',
            f"<title>{escape(text['title'])}</title>",
            f"<style>{_css()}</style>",
            "</head>",
            "<body>",
            '<main class="page">',
            '<p class="crumb"><a href="../index.html">Codex Usage Estimator</a> / Usage Pulse</p>',
            "<header>",
            f"<h1>{escape(text['title'])}</h1>",
            f"<p class=\"subtitle\">{escape(text['subtitle'])}</p>",
            f"<p class=\"meta\">{escape(text['generated'])}: {escape(generated)}</p>",
            "</header>",
            _metric_grid(latest, text),
            _section(text["history"], _history_svg(rows, text)),
            _section(text["token_mix"], _token_mix_svg(latest, text)),
            _section(text["rate_limit"], _rate_limit_html(latest, text)),
            _section(text["snapshots"], _snapshot_table(rows, text)),
            f"<p class=\"footnote\">{escape(text['note'])}</p>",
            "</main>",
            "</body>",
            "</html>",
            "",
        ]
    )


def _metric_grid(latest: Dict[str, Any], text: Dict[str, str]) -> str:
    return "\n".join(
        [
            '<section class="metrics" aria-label="summary metrics">',
            _metric(text["total_tokens"], _format_int(latest.get("totalTokens")), _window_label(latest)),
            _metric(text["api_cost"], _format_money(float(latest.get("totalCostUSD") or 0.0)), _format_credits(float(latest.get("totalCredits") or 0.0))),
            _metric(text["remaining"], _best_remaining(latest), _best_reset(latest, text)),
            _metric(text["events"], _format_int(latest.get("tokenEventCount")), f"{text['sessions']}: {_format_int(latest.get('sessionCount'))}"),
            "</section>",
        ]
    )


def _metric(label: str, value: str, note: str) -> str:
    return "\n".join(
        [
            '<div class="metric">',
            f'<div class="label">{escape(label)}</div>',
            f'<div class="value">{escape(value)}</div>',
            f'<div class="note">{escape(note)}</div>',
            "</div>",
        ]
    )


def _section(title: str, body: str) -> str:
    return "\n".join(
        [
            '<section class="panel">',
            f"<h2>{escape(title)}</h2>",
            body,
            "</section>",
        ]
    )


def _history_svg(rows: Sequence[Dict[str, Any]], text: Dict[str, str]) -> str:
    if not rows:
        return f'<p class="empty">{escape(text["empty"])}</p>'
    visible = list(rows)[-56:]
    width = 1060
    height = 360
    left = 72
    top = 34
    chart_w = 910
    chart_h = 220
    bottom = top + chart_h
    max_tokens = max([int(row.get("totalTokens") or 0) for row in visible] + [1])
    slot = chart_w / max(len(visible), 1)
    bar_w = max(5, min(24, slot * 0.56))

    parts: List[str] = [
        f'<svg class="chart" viewBox="0 0 {width} {height}" role="img" aria-label="{escape(text["history"])}">',
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="#ffffff"/>',
        *_grid(left, top, chart_w, chart_h, max_tokens),
    ]
    points: List[Tuple[float, float]] = []
    for index, row in enumerate(visible):
        tokens = int(row.get("totalTokens") or 0)
        x = left + slot * index + (slot - bar_w) / 2
        bar_h = chart_h * tokens / max_tokens
        y = bottom - bar_h
        parts.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{bar_w:.2f}" height="{bar_h:.2f}" rx="4" fill="#3772ff"/>')
        remaining = _remaining_number(row)
        if remaining is not None:
            point_x = left + slot * index + slot / 2
            point_y = bottom - chart_h * max(0.0, min(100.0, remaining)) / 100
            points.append((point_x, point_y))
        if index == 0 or index == len(visible) - 1 or index % max(1, len(visible) // 6) == 0:
            parts.append(
                f'<text x="{left + slot * index:.2f}" y="{bottom + 28}" fill="#62656f" font-size="12">'
                f'{escape(_short_time(row.get("generatedAt")))}</text>'
            )
    if len(points) >= 2:
        parts.append(
            '<polyline points="'
            + " ".join(f"{x:.2f},{y:.2f}" for x, y in points)
            + '" fill="none" stroke="#0f9d58" stroke-width="3"/>'
        )
    for x, y in points[-10:]:
        parts.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="4" fill="#0f9d58"/>')
    parts.extend(
        [
            f'<text x="{left}" y="{height - 34}" fill="#202124" font-size="13">■ {escape(text["total_tokens"])}</text>',
            f'<text x="{left + 150}" y="{height - 34}" fill="#0f9d58" font-size="13">● {escape(text["remaining"])}</text>',
            "</svg>",
        ]
    )
    return "\n".join(parts)


def _token_mix_svg(latest: Dict[str, Any], text: Dict[str, str]) -> str:
    segments = [
        (text["cached_input"], int(latest.get("cachedInputTokens") or 0), "#2563eb"),
        (text["non_cached_input"], int(latest.get("nonCachedInputTokens") or 0), "#0f766e"),
        (text["output"], int(latest.get("outputTokens") or 0), "#d9801f"),
    ]
    total = sum(value for _, value, _ in segments)
    if total <= 0:
        return f'<p class="empty">{escape(text["empty"])}</p>'
    width = 1060
    parts = [
        f'<svg class="chart" viewBox="0 0 {width} 170" role="img" aria-label="{escape(text["token_mix"])}">',
        f'<rect x="0" y="0" width="{width}" height="170" fill="#ffffff"/>',
    ]
    x = 50.0
    bar_w = 960.0
    for label, value, color in segments:
        segment_w = bar_w * value / total
        parts.append(f'<rect x="{x:.2f}" y="46" width="{segment_w:.2f}" height="38" fill="{color}"/>')
        if segment_w > 70:
            parts.append(
                f'<text x="{x + 10:.2f}" y="70" fill="#ffffff" font-size="13" font-weight="700">'
                f'{escape(label)}</text>'
            )
        x += segment_w
    legend_x = 50
    for label, value, color in segments:
        parts.append(f'<rect x="{legend_x}" y="116" width="12" height="12" rx="2" fill="{color}"/>')
        parts.append(
            f'<text x="{legend_x + 18}" y="127" fill="#202124" font-size="13">'
            f'{escape(label)} · {escape(_format_int(value))}</text>'
        )
        legend_x += 310
    reasoning = int(latest.get("reasoningOutputTokens") or 0)
    parts.append(
        f'<text x="50" y="154" fill="#62656f" font-size="12">{escape(text["reasoning"])}: {escape(_format_int(reasoning))}</text>'
    )
    parts.append("</svg>")
    return "\n".join(parts)


def _rate_limit_html(latest: Dict[str, Any], text: Dict[str, str]) -> str:
    rows = []
    for prefix in ("primary", "secondary"):
        used = latest.get(f"{prefix}UsedPercentLatest")
        remaining = latest.get(f"{prefix}RemainingPercentLatest")
        reset = latest.get(f"{prefix}ResetsAt") or "-"
        rows.append(
            "<tr>"
            f"<td>{escape(text[prefix])}</td>"
            f"<td>{escape(_format_percent(used, '-'))}</td>"
            f"<td>{escape(_format_percent(remaining, '-'))}</td>"
            f"<td>{escape(str(reset))}</td>"
            "</tr>"
        )
    return (
        '<table><thead><tr>'
        f'<th>{escape(text["rate_limit"])}</th><th>{escape(text["used"])}</th>'
        f'<th>{escape(text["remaining"])}</th><th>{escape(text["reset"])}</th>'
        "</tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table>"
    )


def _snapshot_table(rows: Sequence[Dict[str, Any]], text: Dict[str, str]) -> str:
    if not rows:
        return f'<p class="empty">{escape(text["empty"])}</p>'
    body = []
    for row in list(rows)[-18:][::-1]:
        body.append(
            "<tr>"
            f"<td>{escape(_short_time(row.get('generatedAt')))}</td>"
            f"<td>{escape(_window_label(row))}</td>"
            f"<td>{escape(_format_int(row.get('totalTokens')))}</td>"
            f"<td>{escape(_format_money(float(row.get('totalCostUSD') or 0.0)))}</td>"
            f"<td>{escape(_best_remaining(row))}</td>"
            "</tr>"
        )
    return (
        '<table><thead><tr>'
        f'<th>{escape(text["table_time"])}</th><th>{escape(text["table_window"])}</th>'
        f'<th>{escape(text["table_tokens"])}</th><th>{escape(text["table_cost"])}</th>'
        f'<th>{escape(text["table_remaining"])}</th>'
        "</tr></thead><tbody>"
        + "".join(body)
        + "</tbody></table>"
    )


def _grid(left: int, top: int, chart_w: int, chart_h: int, max_value: int) -> List[str]:
    parts = []
    bottom = top + chart_h
    for step in range(5):
        y = bottom - chart_h * step / 4
        value = int(max_value * step / 4)
        parts.append(f'<line x1="{left}" y1="{y:.2f}" x2="{left + chart_w}" y2="{y:.2f}" stroke="#e6e8ee"/>')
        parts.append(f'<text x="18" y="{y + 4:.2f}" fill="#62656f" font-size="12">{escape(_compact_int(value))}</text>')
    return parts


def _bucket_start(value: datetime, interval_hours: int) -> datetime:
    interval = max(int(interval_hours), 1)
    hour = value.hour - (value.hour % interval)
    return value.replace(hour=hour, minute=0, second=0, microsecond=0)


def _remaining_number(row: Dict[str, Any]) -> Optional[float]:
    for key in ("secondaryRemainingPercentLatest", "primaryRemainingPercentLatest"):
        value = row.get(key)
        if value is not None:
            return float(value)
    return None


def _best_remaining(row: Dict[str, Any]) -> str:
    value = _remaining_number(row)
    return _format_percent(value, "-")


def _best_reset(row: Dict[str, Any], text: Dict[str, str]) -> str:
    reset = row.get("secondaryResetsAt") or row.get("primaryResetsAt")
    if not reset:
        return "-"
    return f"{text['reset']}: {reset}"


def _window_label(row: Dict[str, Any]) -> str:
    start = _short_time(row.get("windowStart"))
    end = _short_time(row.get("windowEnd"))
    if not start and not end:
        return "-"
    return f"{start} -> {end}"


def _short_time(value: Any) -> str:
    if not value:
        return ""
    text = str(value)
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return text[:16]
    return parsed.strftime("%m-%d %H:%M")


def _compact_int(value: int) -> str:
    if value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.1f}B"
    if value >= 1_000_000:
        return f"{value / 1_000_000:.0f}M"
    if value >= 1_000:
        return f"{value / 1_000:.0f}K"
    return str(value)


def _css() -> str:
    return """
    :root {
      color-scheme: light;
      --bg: #f6f7fb;
      --panel: #ffffff;
      --ink: #202124;
      --muted: #62656f;
      --line: #dfe3ea;
      --blue: #3772ff;
      --green: #0f9d58;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font: 15px/1.65 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    .page {
      width: min(1120px, calc(100vw - 32px));
      margin: 32px auto 56px;
    }
    h1, h2, p { margin: 0; }
    h1 {
      font-size: clamp(30px, 5vw, 52px);
      line-height: 1.1;
      letter-spacing: 0;
    }
    h2 {
      margin-bottom: 14px;
      font-size: 20px;
    }
    a { color: var(--blue); text-decoration: none; font-weight: 700; }
    .crumb, .meta, .subtitle, .note, .footnote, .empty { color: var(--muted); }
    .crumb { margin-bottom: 16px; }
    .subtitle { margin-top: 12px; max-width: 860px; }
    .meta { margin-top: 10px; font-size: 13px; }
    .metrics {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      margin-top: 24px;
    }
    .metric, .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
    }
    .metric {
      min-height: 112px;
      padding: 16px;
    }
    .panel {
      margin-top: 16px;
      padding: 20px;
    }
    .label {
      color: var(--muted);
      font-size: 13px;
    }
    .value {
      margin-top: 8px;
      font-size: 28px;
      line-height: 1.1;
      font-weight: 760;
    }
    .note {
      margin-top: 8px;
      font-size: 13px;
    }
    .chart {
      display: block;
      width: 100%;
      height: auto;
    }
    table {
      width: 100%;
      border-collapse: collapse;
    }
    th, td {
      border-bottom: 1px solid var(--line);
      padding: 10px 8px;
      text-align: left;
      vertical-align: top;
    }
    th {
      color: var(--muted);
      font-weight: 650;
    }
    td:not(:first-child), th:not(:first-child) {
      text-align: right;
      font-variant-numeric: tabular-nums;
    }
    .footnote {
      margin-top: 18px;
      font-size: 13px;
    }
    @media (max-width: 800px) {
      .page { width: min(100vw - 20px, 1120px); margin-top: 20px; }
      .metrics { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      .value { font-size: 23px; }
      .panel { padding: 14px; overflow-x: auto; }
    }
    """.strip()

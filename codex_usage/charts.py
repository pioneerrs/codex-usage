from __future__ import annotations

from datetime import datetime
from html import escape
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .reporting import normalize_lang


TEXT = {
    "en": {
        "title": "Codex Usage Chart",
        "subtitle": "Local token_count log visualization",
        "window": "Window",
        "source": "Source",
        "generated": "Generated",
        "summary": "Summary",
        "token_mix": "Token Mix",
        "timeline": "Usage Over Time",
        "rate_limits": "Rate Limits",
        "session_ranking": "Session Ranking",
        "notes": "Notes",
        "no_records": "No Codex token_count records found for this window.",
        "no_rate_data": "No rate-limit snapshots found for this window.",
        "input": "Input",
        "cached_input": "Cached Input",
        "non_cached_input": "Non-cached Input",
        "output": "Output",
        "reasoning": "Reasoning",
        "total": "Total",
        "events": "Events",
        "sessions": "Sessions",
        "primary": "primary used",
        "secondary": "secondary used",
        "session": "Session",
        "last_event": "Last Event",
        "note_local": "Values come from local Codex session token_count events.",
        "note_cached": "Cached input is included in input.",
        "note_reasoning": "Reasoning is shown separately; it is not added again to the token mix.",
        "written": "Wrote Codex usage chart to",
    },
    "zh": {
        "title": "Codex 用量图表",
        "subtitle": "基于本地 token_count 日志生成",
        "window": "时间窗口",
        "source": "数据来源",
        "generated": "生成时间",
        "summary": "总览",
        "token_mix": "Token 构成",
        "timeline": "随时间变化",
        "rate_limits": "限额变化",
        "session_ranking": "Session 排行",
        "notes": "说明",
        "no_records": "这个时间窗口内没有找到 Codex token_count 记录。",
        "no_rate_data": "这个时间窗口内没有找到限额快照。",
        "input": "Input",
        "cached_input": "Cached Input",
        "non_cached_input": "Non-cached Input",
        "output": "Output",
        "reasoning": "Reasoning",
        "total": "Total",
        "events": "事件数",
        "sessions": "Sessions",
        "primary": "primary 已用",
        "secondary": "secondary 已用",
        "session": "Session",
        "last_event": "最后事件",
        "note_local": "数值来自本机 Codex session 日志里的 token_count 事件。",
        "note_cached": "Cached Input 是 Input 的子集。",
        "note_reasoning": "Reasoning 单独展示，不会在 Token 构成里重复相加。",
        "written": "已写入 Codex 用量图表:",
    },
}


COLORS = {
    "cached": "#2563eb",
    "fresh": "#0f766e",
    "output": "#f59e0b",
    "reasoning": "#7c3aed",
    "primary": "#dc2626",
    "secondary": "#4f46e5",
    "grid": "#d8dee9",
    "axis": "#667085",
    "text": "#1f2937",
    "muted": "#667085",
}


def render_codex_chart_html(report: Dict[str, Any], lang: str = "en") -> str:
    normalized = normalize_lang(lang)
    text = TEXT[normalized]
    summary = report["summary"]
    generated = datetime.now().astimezone().isoformat(timespec="seconds")

    if int(summary.get("sessionCount") or 0) == 0:
        main = _section(text["summary"], f'<p class="empty">{escape(text["no_records"])}</p>')
    else:
        main = "\n".join(
            [
                _section(text["summary"], _summary_cards(summary, text)),
                _section(text["token_mix"], _token_mix_svg(summary, text)),
                _section(text["timeline"], _timeline_svg(report.get("timeline") or [], text)),
                _section(text["rate_limits"], _rate_svg(report.get("timeline") or [], text)),
                _section(text["session_ranking"], _session_table(report.get("sessions") or [], text)),
                _section(text["notes"], _notes(text)),
            ]
        )

    return "\n".join(
        [
            "<!doctype html>",
            f'<html lang="{escape(normalized)}">',
            "<head>",
            '<meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1">',
            f"<title>{escape(text['title'])}</title>",
            f"<style>{_css()}</style>",
            "</head>",
            "<body>",
            '<main class="page">',
            '<header class="hero">',
            f"<h1>{escape(text['title'])}</h1>",
            f"<p>{escape(text['subtitle'])}</p>",
            '<div class="meta-grid">',
            f"<div><span>{escape(text['window'])}</span>{escape(summary['windowStart'])} -> {escape(summary['windowEnd'])}</div>",
            f"<div><span>{escape(text['source'])}</span>{escape(summary['sourceRoot'])}</div>",
            f"<div><span>{escape(text['generated'])}</span>{escape(generated)}</div>",
            "</div>",
            "</header>",
            main,
            "</main>",
            "</body>",
            "</html>",
            "",
        ]
    )


def _css() -> str:
    return """
:root {
  color-scheme: light;
  --bg: #f7f8fb;
  --panel: #ffffff;
  --text: #1f2937;
  --muted: #667085;
  --border: #d8dee9;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
.page {
  width: min(1120px, calc(100vw - 32px));
  margin: 0 auto;
  padding: 32px 0 48px;
}
.hero {
  padding: 8px 0 18px;
}
h1 {
  margin: 0;
  font-size: 34px;
  line-height: 1.18;
  letter-spacing: 0;
}
.hero p {
  margin: 8px 0 18px;
  color: var(--muted);
}
.meta-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}
.meta-grid div,
.card,
.panel {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 8px;
}
.meta-grid div {
  padding: 12px;
  overflow-wrap: anywhere;
  font-size: 13px;
}
.meta-grid span,
.card span {
  display: block;
  color: var(--muted);
  font-size: 12px;
  margin-bottom: 5px;
}
.panel {
  padding: 18px;
  margin-top: 18px;
}
h2 {
  margin: 0 0 14px;
  font-size: 18px;
  letter-spacing: 0;
}
.cards {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}
.card {
  padding: 14px;
}
.card strong {
  display: block;
  font-size: 24px;
  line-height: 1.15;
  overflow-wrap: anywhere;
}
.chart {
  width: 100%;
  height: auto;
  display: block;
}
.legend {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 10px;
  color: var(--muted);
  font-size: 13px;
}
.legend i {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 2px;
  margin-right: 6px;
}
table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}
th, td {
  padding: 10px 8px;
  border-bottom: 1px solid var(--border);
  text-align: right;
}
th:first-child, td:first-child,
th:nth-child(2), td:nth-child(2) {
  text-align: left;
}
td:first-child {
  overflow-wrap: anywhere;
}
.empty,
.notes {
  color: var(--muted);
  margin: 0;
}
.notes li {
  margin: 6px 0;
}
@media (max-width: 760px) {
  .page { width: min(100vw - 20px, 1120px); padding-top: 18px; }
  .meta-grid,
  .cards { grid-template-columns: 1fr; }
  h1 { font-size: 28px; }
  .card strong { font-size: 22px; }
}
""".strip()


def _section(title: str, body: str) -> str:
    return f'<section class="panel"><h2>{escape(title)}</h2>{body}</section>'


def _summary_cards(summary: Dict[str, Any], text: Dict[str, str]) -> str:
    cards = [
        (text["total"], summary.get("totalTokens")),
        (text["input"], summary.get("inputTokens")),
        (text["cached_input"], summary.get("cachedInputTokens")),
        (text["non_cached_input"], summary.get("nonCachedInputTokens")),
        (text["output"], summary.get("outputTokens")),
        (text["reasoning"], summary.get("reasoningOutputTokens")),
        (text["sessions"], summary.get("sessionCount")),
        (text["events"], summary.get("tokenEventCount")),
    ]
    return '<div class="cards">' + "".join(
        f'<div class="card"><span>{escape(label)}</span><strong>{_format_int(value)}</strong></div>'
        for label, value in cards
    ) + "</div>"


def _token_mix_svg(summary: Dict[str, Any], text: Dict[str, str]) -> str:
    segments = [
        (text["cached_input"], int(summary.get("cachedInputTokens") or 0), COLORS["cached"]),
        (text["non_cached_input"], int(summary.get("nonCachedInputTokens") or 0), COLORS["fresh"]),
        (text["output"], int(summary.get("outputTokens") or 0), COLORS["output"]),
    ]
    total = sum(value for _, value, _ in segments)
    if total <= 0:
        return f'<p class="empty">{escape(text["no_records"])}</p>'

    width = 900
    bar_x = 28
    bar_y = 34
    bar_w = 844
    bar_h = 34
    x = bar_x
    rects: List[str] = []
    labels: List[str] = []
    for index, (label, value, color) in enumerate(segments):
        segment_w = bar_w * value / total
        if index == len(segments) - 1:
            segment_w = bar_x + bar_w - x
        rects.append(
            f'<rect x="{x:.2f}" y="{bar_y}" width="{max(segment_w, 0):.2f}" height="{bar_h}" fill="{color}" />'
        )
        labels.append(
            f'<span><i style="background:{color}"></i>{escape(label)}: {_format_int(value)} ({_format_percent(value, total)})</span>'
        )
        x += segment_w

    return "\n".join(
        [
            f'<svg class="chart" viewBox="0 0 {width} 116" role="img" aria-label="{escape(text["token_mix"])}">',
            f'<rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="{bar_h}" fill="#eef2f7" rx="6" />',
            *rects,
            f'<text x="{bar_x}" y="24" fill="{COLORS["muted"]}" font-size="13">{escape(text["total"])}: {_format_int(total)}</text>',
            "</svg>",
            '<div class="legend">' + "".join(labels) + "</div>",
        ]
    )


def _timeline_svg(timeline: Sequence[Dict[str, Any]], text: Dict[str, str]) -> str:
    buckets = list(timeline)
    max_value = max((int(row.get("totalTokens") or 0) for row in buckets), default=0)
    if max_value <= 0:
        return f'<p class="empty">{escape(text["no_records"])}</p>'

    width = 960
    height = 330
    left = 78
    top = 26
    chart_w = 842
    chart_h = 220
    bottom = top + chart_h
    count = len(buckets)
    slot = chart_w / max(count, 1)
    bar_w = max(min(slot * 0.68, 34), 2)
    bars: List[str] = []
    for index, row in enumerate(buckets):
        x = left + index * slot + (slot - bar_w) / 2
        cursor = bottom
        for key, color in (
            ("cachedInputTokens", COLORS["cached"]),
            ("nonCachedInputTokens", COLORS["fresh"]),
            ("outputTokens", COLORS["output"]),
        ):
            value = int(row.get(key) or 0)
            segment_h = chart_h * value / max_value
            cursor -= segment_h
            if segment_h > 0:
                bars.append(
                    f'<rect x="{x:.2f}" y="{cursor:.2f}" width="{bar_w:.2f}" height="{segment_h:.2f}" fill="{color}" />'
                )

    grid = _y_grid(left, top, chart_w, chart_h, max_value)
    labels = _x_labels(buckets, left, bottom, slot)
    legend = _legend(
        [
            (text["cached_input"], COLORS["cached"]),
            (text["non_cached_input"], COLORS["fresh"]),
            (text["output"], COLORS["output"]),
        ]
    )
    return "\n".join(
        [
            f'<svg class="chart" viewBox="0 0 {width} {height}" role="img" aria-label="{escape(text["timeline"])}">',
            *grid,
            *bars,
            f'<line x1="{left}" y1="{bottom}" x2="{left + chart_w}" y2="{bottom}" stroke="{COLORS["axis"]}" />',
            *labels,
            "</svg>",
            legend,
        ]
    )


def _rate_svg(timeline: Sequence[Dict[str, Any]], text: Dict[str, str]) -> str:
    buckets = list(timeline)
    has_rate = any(
        row.get("primaryUsedPercent") is not None or row.get("secondaryUsedPercent") is not None
        for row in buckets
    )
    if not has_rate:
        return f'<p class="empty">{escape(text["no_rate_data"])}</p>'

    width = 960
    height = 290
    left = 78
    top = 26
    chart_w = 842
    chart_h = 190
    bottom = top + chart_h
    count = len(buckets)

    def x_at(index: int) -> float:
        if count <= 1:
            return left + chart_w / 2
        return left + chart_w * index / (count - 1)

    def y_at(value: float) -> float:
        return bottom - chart_h * max(min(value, 100), 0) / 100

    series = [
        (text["primary"], "primaryUsedPercent", COLORS["primary"]),
        (text["secondary"], "secondaryUsedPercent", COLORS["secondary"]),
    ]
    parts = _percent_grid(left, top, chart_w, chart_h)
    for label, key, color in series:
        points = [
            (x_at(index), y_at(float(row[key])), float(row[key]))
            for index, row in enumerate(buckets)
            if row.get(key) is not None
        ]
        if len(points) >= 2:
            path = " ".join(
                ("M" if index == 0 else "L") + f" {x:.2f} {y:.2f}"
                for index, (x, y, _) in enumerate(points)
            )
            parts.append(f'<path d="{path}" fill="none" stroke="{color}" stroke-width="3" />')
        for x, y, value in points:
            parts.append(
                f'<circle cx="{x:.2f}" cy="{y:.2f}" r="4" fill="{color}">'
                f'<title>{escape(label)} {_format_percent_label(value)}</title>'
                "</circle>"
            )

    labels = _x_point_labels(buckets, left, bottom, chart_w, line_y=bottom + 24)
    legend = _legend([(text["primary"], COLORS["primary"]), (text["secondary"], COLORS["secondary"])])
    return "\n".join(
        [
            f'<svg class="chart" viewBox="0 0 {width} {height}" role="img" aria-label="{escape(text["rate_limits"])}">',
            *parts,
            f'<line x1="{left}" y1="{bottom}" x2="{left + chart_w}" y2="{bottom}" stroke="{COLORS["axis"]}" />',
            *labels,
            "</svg>",
            legend,
        ]
    )


def _session_table(sessions: Sequence[Dict[str, Any]], text: Dict[str, str]) -> str:
    rows = sorted(sessions, key=lambda row: int(row.get("totalTokens") or 0), reverse=True)[:8]
    if not rows:
        return f'<p class="empty">{escape(text["no_records"])}</p>'
    body = []
    for row in rows:
        body.append(
            "<tr>"
            f"<td>{escape(str(row.get('sessionFile') or ''))}</td>"
            f"<td>{escape(str(row.get('lastEventAt') or ''))}</td>"
            f"<td>{_format_int(row.get('totalTokens'))}</td>"
            f"<td>{_format_int(row.get('outputTokens'))}</td>"
            f"<td>{_format_int(row.get('reasoningOutputTokens'))}</td>"
            "</tr>"
        )
    return "\n".join(
        [
            "<table>",
            "<thead><tr>"
            f"<th>{escape(text['session'])}</th>"
            f"<th>{escape(text['last_event'])}</th>"
            f"<th>{escape(text['total'])}</th>"
            f"<th>{escape(text['output'])}</th>"
            f"<th>{escape(text['reasoning'])}</th>"
            "</tr></thead>",
            "<tbody>",
            *body,
            "</tbody>",
            "</table>",
        ]
    )


def _notes(text: Dict[str, str]) -> str:
    return "\n".join(
        [
            '<ul class="notes">',
            f"<li>{escape(text['note_local'])}</li>",
            f"<li>{escape(text['note_cached'])}</li>",
            f"<li>{escape(text['note_reasoning'])}</li>",
            "</ul>",
        ]
    )


def _y_grid(left: int, top: int, chart_w: int, chart_h: int, max_value: int) -> List[str]:
    lines: List[str] = []
    for step in range(5):
        value = max_value * step / 4
        y = top + chart_h - chart_h * step / 4
        lines.append(
            f'<line x1="{left}" y1="{y:.2f}" x2="{left + chart_w}" y2="{y:.2f}" stroke="{COLORS["grid"]}" />'
        )
        lines.append(
            f'<text x="{left - 10}" y="{y + 4:.2f}" fill="{COLORS["muted"]}" font-size="12" text-anchor="end">{escape(_format_compact(value))}</text>'
        )
    return lines


def _percent_grid(left: int, top: int, chart_w: int, chart_h: int) -> List[str]:
    lines: List[str] = []
    for value in (0, 25, 50, 75, 100):
        y = top + chart_h - chart_h * value / 100
        lines.append(
            f'<line x1="{left}" y1="{y:.2f}" x2="{left + chart_w}" y2="{y:.2f}" stroke="{COLORS["grid"]}" />'
        )
        lines.append(
            f'<text x="{left - 10}" y="{y + 4:.2f}" fill="{COLORS["muted"]}" font-size="12" text-anchor="end">{value}%</text>'
        )
    return lines


def _x_labels(
    buckets: Sequence[Dict[str, Any]],
    left: int,
    bottom: float,
    slot: float,
    line_y: Optional[float] = None,
) -> List[str]:
    count = len(buckets)
    if count == 0:
        return []
    step = max(1, count // 8)
    labels: List[str] = []
    for index, row in enumerate(buckets):
        if index % step != 0 and index != count - 1:
            continue
        if slot <= 0:
            x = left
        else:
            x = left + index * slot + slot / 2
        labels.append(
            f'<text x="{x:.2f}" y="{line_y or bottom + 24:.2f}" fill="{COLORS["muted"]}" font-size="12" text-anchor="middle">{escape(_bucket_label(row))}</text>'
        )
    return labels


def _x_point_labels(
    buckets: Sequence[Dict[str, Any]],
    left: int,
    bottom: float,
    chart_w: int,
    line_y: Optional[float] = None,
) -> List[str]:
    count = len(buckets)
    if count == 0:
        return []
    step = max(1, count // 8)
    labels: List[str] = []
    for index, row in enumerate(buckets):
        if index % step != 0 and index != count - 1:
            continue
        if count <= 1:
            x = left + chart_w / 2
        else:
            x = left + chart_w * index / (count - 1)
        labels.append(
            f'<text x="{x:.2f}" y="{line_y or bottom + 24:.2f}" fill="{COLORS["muted"]}" font-size="12" text-anchor="middle">{escape(_bucket_label(row))}</text>'
        )
    return labels


def _bucket_label(row: Dict[str, Any]) -> str:
    start = _parse_iso(row.get("bucketStart"))
    end = _parse_iso(row.get("bucketEnd"))
    if not start:
        return str(row.get("bucketStart") or "")
    if end and (end - start).total_seconds() <= 3600 * 2:
        return start.strftime("%H:%M")
    return start.strftime("%m-%d")


def _parse_iso(value: Any) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _legend(items: Sequence[Tuple[str, str]]) -> str:
    return '<div class="legend">' + "".join(
        f'<span><i style="background:{color}"></i>{escape(label)}</span>' for label, color in items
    ) + "</div>"


def _format_int(value: Any) -> str:
    return f"{int(value or 0):,}"


def _format_percent(value: int, total: int) -> str:
    if total <= 0:
        return "0%"
    return f"{value / total * 100:.1f}%"


def _format_percent_label(value: float) -> str:
    return f"{value:g}%"


def _format_compact(value: float) -> str:
    value = float(value)
    absolute = abs(value)
    if absolute >= 1_000_000_000:
        return f"{value / 1_000_000_000:.1f}B"
    if absolute >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    if absolute >= 1_000:
        return f"{value / 1_000:.1f}K"
    return f"{value:.0f}"

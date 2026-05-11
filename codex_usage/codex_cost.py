from __future__ import annotations

import json
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any, Dict, List

from .reporting import normalize_lang, render_table


DEFAULT_MODEL_LABEL = "gpt-5.5"
DEFAULT_INPUT_RATE_PER_M = 5.0
DEFAULT_CACHED_INPUT_RATE_PER_M = 0.5
DEFAULT_OUTPUT_RATE_PER_M = 30.0
DEFAULT_CREDITS_PER_USD = 25.0


TEXT = {
    "en": {
        "title": "Codex API-Equivalent Cost Estimate",
        "window": "Window",
        "source": "Source",
        "pricing": "Pricing",
        "summary": "Summary",
        "cost_mix": "Cost Mix",
        "details": "Details",
        "notes": "Notes:",
        "type": "Type",
        "tokens": "Tokens",
        "rate": "Rate",
        "cost": "Cost USD",
        "credits": "Codex Credits",
        "total": "Total",
        "non_cached_input": "Non-cached input",
        "cached_input": "Cached input",
        "output": "Output",
        "reasoning": "Reasoning",
        "sessions": "Sessions",
        "events": "Token Events",
        "total_tokens": "Total Tokens",
        "api_equivalent": "API equivalent",
        "note_estimate": "This is an API-equivalent estimate from local Codex token_count logs, not a subscription bill.",
        "note_reasoning": "Reasoning tokens are displayed for context and are already included in output tokens, so they are not billed again.",
        "note_rates": "Use rate flags to update pricing when the model or rate card changes.",
        "written": "Wrote Codex cost chart to",
    },
    "zh": {
        "title": "Codex API 等价费用估算",
        "window": "时间窗口",
        "source": "数据来源",
        "pricing": "计价口径",
        "summary": "总览",
        "cost_mix": "费用构成",
        "details": "明细",
        "notes": "说明：",
        "type": "类型",
        "tokens": "Tokens",
        "rate": "单价",
        "cost": "美元估算",
        "credits": "Codex Credits",
        "total": "合计",
        "non_cached_input": "非缓存 input",
        "cached_input": "Cached input",
        "output": "Output",
        "reasoning": "Reasoning",
        "sessions": "Sessions",
        "events": "Token 事件数",
        "total_tokens": "Total Tokens",
        "api_equivalent": "API 等价金额",
        "note_estimate": "这是基于本机 Codex token_count 日志的 API 等价估算，不代表订阅真实账单。",
        "note_reasoning": "Reasoning token 只做展示，已经包含在 output 口径里，不重复计费。",
        "note_rates": "模型或 rate card 变化时，可以通过费率参数调整单价。",
        "written": "已写入 Codex 费用图表:",
    },
}


COLORS = {
    "non_cached_input": "#0f766e",
    "cached_input": "#2563eb",
    "output": "#f59e0b",
    "grid": "#d8dee9",
    "text": "#1f2937",
    "muted": "#667085",
}


def build_codex_cost_report(
    usage_report: Dict[str, Any],
    model_label: str = DEFAULT_MODEL_LABEL,
    input_rate_per_m: float = DEFAULT_INPUT_RATE_PER_M,
    cached_input_rate_per_m: float = DEFAULT_CACHED_INPUT_RATE_PER_M,
    output_rate_per_m: float = DEFAULT_OUTPUT_RATE_PER_M,
    credits_per_usd: float = DEFAULT_CREDITS_PER_USD,
) -> Dict[str, Any]:
    summary = usage_report["summary"]
    line_items = [
        _line_item(
            "non_cached_input",
            int(summary.get("nonCachedInputTokens") or 0),
            input_rate_per_m,
            credits_per_usd,
        ),
        _line_item(
            "cached_input",
            int(summary.get("cachedInputTokens") or 0),
            cached_input_rate_per_m,
            credits_per_usd,
        ),
        _line_item(
            "output",
            int(summary.get("outputTokens") or 0),
            output_rate_per_m,
            credits_per_usd,
        ),
    ]
    total_cost = sum(item["costUSD"] for item in line_items)
    total_credits = total_cost * credits_per_usd
    total_billable_tokens = sum(item["tokens"] for item in line_items)

    return {
        "summary": {
            "windowStart": summary.get("windowStart"),
            "windowEnd": summary.get("windowEnd"),
            "sourceRoot": summary.get("sourceRoot"),
            "modelLabel": model_label,
            "sessionCount": int(summary.get("sessionCount") or 0),
            "tokenEventCount": int(summary.get("tokenEventCount") or 0),
            "totalTokens": int(summary.get("totalTokens") or 0),
            "billableTokens": total_billable_tokens,
            "reasoningOutputTokens": int(summary.get("reasoningOutputTokens") or 0),
            "totalCostUSD": total_cost,
            "totalCredits": total_credits,
            "creditsPerUSD": credits_per_usd,
            "ratesPerMillion": {
                "input": input_rate_per_m,
                "cachedInput": cached_input_rate_per_m,
                "output": output_rate_per_m,
            },
        },
        "lineItems": line_items,
    }


def render_codex_cost_report(cost_report: Dict[str, Any], lang: str = "en") -> str:
    text = TEXT[normalize_lang(lang)]
    summary = cost_report["summary"]
    line_items = cost_report["lineItems"]
    lines = [
        text["title"],
        "",
        f"{text['window']}: {summary['windowStart']} -> {summary['windowEnd']}",
        f"{text['source']}: {summary['sourceRoot']}",
        (
            f"{text['pricing']}: {summary['modelLabel']} "
            f"(input ${summary['ratesPerMillion']['input']:g}/1M, "
            f"cached input ${summary['ratesPerMillion']['cachedInput']:g}/1M, "
            f"output ${summary['ratesPerMillion']['output']:g}/1M)"
        ),
        "",
    ]

    lines.extend(
        render_table(
            [text["type"], text["tokens"], text["rate"], text["cost"], text["credits"]],
            [
                [
                    text[item["type"]],
                    _format_int(item["tokens"]),
                    f"${item['ratePerMillion']:g} / 1M",
                    _format_money(item["costUSD"]),
                    _format_credits(item["credits"]),
                ]
                for item in line_items
            ]
            + [
                [
                    text["total"],
                    _format_int(summary["billableTokens"]),
                    "-",
                    _format_money(summary["totalCostUSD"]),
                    _format_credits(summary["totalCredits"]),
                ]
            ],
        )
    )
    lines.extend(
        [
            "",
            text["summary"],
            f"- {text['total_tokens']}: {_format_int(summary['totalTokens'])}",
            f"- {text['reasoning']}: {_format_int(summary['reasoningOutputTokens'])}",
            f"- {text['sessions']}: {_format_int(summary['sessionCount'])}",
            f"- {text['events']}: {_format_int(summary['tokenEventCount'])}",
            "",
            text["notes"],
            f"- {text['note_estimate']}",
            f"- {text['note_reasoning']}",
            f"- {text['note_rates']}",
        ]
    )
    return "\n".join(lines)


def export_codex_cost_report(cost_report: Dict[str, Any], output: Path) -> None:
    output.write_text(json.dumps(cost_report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def render_codex_cost_chart_html(cost_report: Dict[str, Any], lang: str = "en") -> str:
    normalized = normalize_lang(lang)
    text = TEXT[normalized]
    summary = cost_report["summary"]
    line_items = cost_report["lineItems"]
    generated = datetime.now().astimezone().isoformat(timespec="seconds")

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
            f"<p>{escape(text['window'])}: {escape(str(summary['windowStart']))} -> {escape(str(summary['windowEnd']))}</p>",
            '<div class="meta-grid">',
            f"<div><span>{escape(text['api_equivalent'])}</span>{escape(_format_money(summary['totalCostUSD']))}</div>",
            f"<div><span>{escape(text['credits'])}</span>{escape(_format_credits(summary['totalCredits']))}</div>",
            f"<div><span>{escape(text['total_tokens'])}</span>{escape(_format_int(summary['totalTokens']))}</div>",
            f"<div><span>{escape(text['reasoning'])}</span>{escape(_format_int(summary['reasoningOutputTokens']))}</div>",
            f"<div><span>{escape(text['source'])}</span>{escape(str(summary['sourceRoot']))}</div>",
            f"<div><span>{escape('Generated')}</span>{escape(generated)}</div>",
            "</div>",
            "</header>",
            _section(text["cost_mix"], _cost_mix_svg(line_items, text)),
            _section(text["details"], _cost_table(line_items, summary, text)),
            _section(text["notes"], _notes(text)),
            "</main>",
            "</body>",
            "</html>",
            "",
        ]
    )


def _line_item(item_type: str, tokens: int, rate_per_million: float, credits_per_usd: float) -> Dict[str, Any]:
    cost = tokens / 1_000_000 * rate_per_million
    return {
        "type": item_type,
        "tokens": tokens,
        "ratePerMillion": rate_per_million,
        "costUSD": cost,
        "credits": cost * credits_per_usd,
    }


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
  width: min(1080px, calc(100vw - 32px));
  margin: 0 auto;
  padding: 32px 0 48px;
}
.hero { padding: 8px 0 18px; }
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
.panel {
  background: var(--panel);
  border: 1px solid var(--border);
  border-radius: 8px;
}
.meta-grid div {
  padding: 12px;
  overflow-wrap: anywhere;
  font-size: 18px;
  font-weight: 700;
}
.meta-grid span {
  display: block;
  color: var(--muted);
  font-size: 12px;
  font-weight: 400;
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
th:first-child, td:first-child { text-align: left; }
.notes {
  color: var(--muted);
  margin: 0;
}
.notes li { margin: 6px 0; }
@media (max-width: 760px) {
  .page { width: min(100vw - 20px, 1080px); padding-top: 18px; }
  .meta-grid { grid-template-columns: 1fr; }
  h1 { font-size: 28px; }
}
""".strip()


def _section(title: str, body: str) -> str:
    return f'<section class="panel"><h2>{escape(title)}</h2>{body}</section>'


def _cost_mix_svg(line_items: List[Dict[str, Any]], text: Dict[str, str]) -> str:
    max_cost = max((float(item["costUSD"]) for item in line_items), default=0.0)
    if max_cost <= 0:
        max_cost = 1.0

    width = 920
    left = 150
    top = 28
    row_h = 58
    chart_w = 700
    parts = [
        f'<svg class="chart" viewBox="0 0 {width} 230" role="img" aria-label="{escape(text["cost_mix"])}">'
    ]
    labels = []
    for index, item in enumerate(line_items):
        y = top + index * row_h
        color = COLORS[item["type"]]
        bar_w = chart_w * float(item["costUSD"]) / max_cost
        parts.extend(
            [
                f'<text x="22" y="{y + 22}" fill="{COLORS["text"]}" font-size="15">{escape(text[item["type"]])}</text>',
                f'<rect x="{left}" y="{y}" width="{bar_w:.2f}" height="30" rx="4" fill="{color}" />',
                f'<text x="{min(left + bar_w + 12, width - 22):.2f}" y="{y + 21}" fill="{COLORS["text"]}" font-size="15">{escape(_format_money(item["costUSD"]))}</text>',
            ]
        )
        labels.append(
            f'<span><i style="background:{color}"></i>{escape(text[item["type"]])}: {escape(_format_percent(item["costUSD"], sum(row["costUSD"] for row in line_items)))}</span>'
        )
    parts.append("</svg>")
    parts.append('<div class="legend">' + "".join(labels) + "</div>")
    return "\n".join(parts)


def _cost_table(line_items: List[Dict[str, Any]], summary: Dict[str, Any], text: Dict[str, str]) -> str:
    rows = []
    for item in line_items:
        rate_text = f"${item['ratePerMillion']:g} / 1M"
        rows.append(
            "<tr>"
            f"<td>{escape(text[item['type']])}</td>"
            f"<td>{escape(_format_int(item['tokens']))}</td>"
            f"<td>{escape(rate_text)}</td>"
            f"<td>{escape(_format_money(item['costUSD']))}</td>"
            f"<td>{escape(_format_credits(item['credits']))}</td>"
            "</tr>"
        )
    rows.append(
        "<tr>"
        f"<td><strong>{escape(text['total'])}</strong></td>"
        f"<td><strong>{escape(_format_int(summary['billableTokens']))}</strong></td>"
        "<td>-</td>"
        f"<td><strong>{escape(_format_money(summary['totalCostUSD']))}</strong></td>"
        f"<td><strong>{escape(_format_credits(summary['totalCredits']))}</strong></td>"
        "</tr>"
    )
    return "\n".join(
        [
            "<table>",
            "<thead><tr>"
            f"<th>{escape(text['type'])}</th>"
            f"<th>{escape(text['tokens'])}</th>"
            f"<th>{escape(text['rate'])}</th>"
            f"<th>{escape(text['cost'])}</th>"
            f"<th>{escape(text['credits'])}</th>"
            "</tr></thead>",
            "<tbody>",
            *rows,
            "</tbody>",
            "</table>",
        ]
    )


def _notes(text: Dict[str, str]) -> str:
    return "\n".join(
        [
            '<ul class="notes">',
            f"<li>{escape(text['note_estimate'])}</li>",
            f"<li>{escape(text['note_reasoning'])}</li>",
            f"<li>{escape(text['note_rates'])}</li>",
            "</ul>",
        ]
    )


def _format_int(value: Any) -> str:
    return f"{int(value or 0):,}"


def _format_money(value: float) -> str:
    return f"${value:,.2f}"


def _format_credits(value: float) -> str:
    return f"{value:,.2f}"


def _format_percent(value: float, total: float) -> str:
    if total <= 0:
        return "0%"
    return f"{value / total * 100:.1f}%"

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
RATE_CARD_AS_OF = "2026-07-17"

MODEL_RATE_CARD = {
    "gpt-5.6": {
        "input_rate_per_m": 5.0,
        "cached_input_rate_per_m": 0.5,
        "output_rate_per_m": 30.0,
    },
    "gpt-5.6-sol": {
        "input_rate_per_m": 5.0,
        "cached_input_rate_per_m": 0.5,
        "output_rate_per_m": 30.0,
    },
    "gpt-5.6-terra": {
        "input_rate_per_m": 2.5,
        "cached_input_rate_per_m": 0.25,
        "output_rate_per_m": 15.0,
    },
    "gpt-5.6-luna": {
        "input_rate_per_m": 1.0,
        "cached_input_rate_per_m": 0.1,
        "output_rate_per_m": 6.0,
    },
    "gpt-5.5": {
        "input_rate_per_m": 5.0,
        "cached_input_rate_per_m": 0.5,
        "output_rate_per_m": 30.0,
    },
    "gpt-5.4": {
        "input_rate_per_m": 2.5,
        "cached_input_rate_per_m": 0.25,
        "output_rate_per_m": 15.0,
    },
    "gpt-5.4-mini": {
        "input_rate_per_m": 0.75,
        "cached_input_rate_per_m": 0.075,
        "output_rate_per_m": 4.5,
    },
    "gpt-5.3-codex": {
        "input_rate_per_m": 1.75,
        "cached_input_rate_per_m": 0.175,
        "output_rate_per_m": 14.0,
    },
    "gpt-5.2": {
        "input_rate_per_m": 1.75,
        "cached_input_rate_per_m": 0.175,
        "output_rate_per_m": 14.0,
    },
    "codex-auto-review": {
        "input_rate_per_m": 2.5,
        "cached_input_rate_per_m": 0.25,
        "output_rate_per_m": 15.0,
    },
}
UNPRICED_MODELS = {"gpt-5.3-codex-spark"}


def get_model_rate_card(model: str) -> Dict[str, Any]:
    """Return the rate card for the given model.

    Falls back to the gpt-5.5 rate card if the model is not found.
    """
    matched = model in MODEL_RATE_CARD
    card = dict(MODEL_RATE_CARD.get(model, MODEL_RATE_CARD["gpt-5.5"]))
    if model in UNPRICED_MODELS:
        status = "unpriced-fallback"
        source = "openai-official"
    elif not matched:
        status = "fallback"
        source = "fallback-gpt-5.5"
    else:
        status = "priced"
        source = "repository-internal" if model == "codex-auto-review" else "openai-official"
    card.update(
        {
            "rate_card_status": status,
            "rate_card_source": source,
            "rate_card_as_of": RATE_CARD_AS_OF,
        }
    )
    return card


TEXT = {
    "en": {
        "title": "Codex API-Equivalent Cost Estimate",
        "unknown_warning": "Warning: unknown model(s) {models} used the gpt-5.5 fallback rate card.",
        "unpriced_warning": "Warning: unpriced model(s) {models} used the gpt-5.5 fallback rate card.",
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
        "by_model": "By Model",
        "model": "Model",
        "model_rate_card": "Rate Card",
        "inclusive": "Inclusive",
        "verified": "Verified",
        "unverified": "Unverified",
        "rate_card": "Rate card",
        "warning": "Warning",
    },
    "zh": {
        "unknown_warning": "警告：未知模型 {models} 使用了 gpt-5.5 默认费率。",
        "unpriced_warning": "警告：未定价模型 {models} 使用了 gpt-5.5 fallback 费率。",
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
        "by_model": "按模型分组",
        "model": "Model",
        "model_rate_card": "费率卡",
        "inclusive": "Inclusive（含不确定量）",
        "verified": "Verified（已验证）",
        "unverified": "Unverified（未验证）",
        "rate_card": "费率卡",
        "warning": "警告",
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
    use_model_rates: bool = True,
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
    verified_summary = summary.get("verifiedUsage") or summary
    verified_line_items = [
        _line_item(
            "non_cached_input",
            int(verified_summary.get("nonCachedInputTokens") or 0),
            input_rate_per_m,
            credits_per_usd,
        ),
        _line_item(
            "cached_input",
            int(verified_summary.get("cachedInputTokens") or 0),
            cached_input_rate_per_m,
            credits_per_usd,
        ),
        _line_item(
            "output",
            int(verified_summary.get("outputTokens") or 0),
            output_rate_per_m,
            credits_per_usd,
        ),
    ]
    verified_cost = sum(item["costUSD"] for item in verified_line_items)
    unverified_cost = max(total_cost - verified_cost, 0.0)

    result: Dict[str, Any] = {
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
            "verifiedCostUSD": verified_cost,
            "unverifiedCostUSD": unverified_cost,
            "verifiedCredits": verified_cost * credits_per_usd,
            "unverifiedCredits": unverified_cost * credits_per_usd,
            "creditsPerUSD": credits_per_usd,
            "rateCardStatus": "user-supplied",
            "rateCardSource": "user-supplied",
            "rateCardAsOf": None,
            "ratesPerMillion": {
                "input": input_rate_per_m,
                "cachedInput": cached_input_rate_per_m,
                "output": output_rate_per_m,
            },
        },
        "lineItems": line_items,
        "unknownModels": [],
        "unpricedModels": [],
    }

    by_model_usage = summary.get("byModel") or {}
    if use_model_rates and by_model_usage:
        by_model_cost: Dict[str, Dict[str, Any]] = {}
        unknown_models: List[str] = []
        unpriced_models: List[str] = []
        for model, model_data in sorted(by_model_usage.items()):
            rate_card = get_model_rate_card(model)
            rate_card_matched = model in MODEL_RATE_CARD
            if model in UNPRICED_MODELS:
                unpriced_models.append(model)
            elif not rate_card_matched:
                unknown_models.append(model)
            model_input = int(model_data.get("nonCachedInputTokens") or 0)
            model_cached = int(model_data.get("cachedInputTokens") or 0)
            model_output = int(model_data.get("outputTokens") or 0)
            model_line_items = [
                _line_item("non_cached_input", model_input, rate_card["input_rate_per_m"], credits_per_usd),
                _line_item("cached_input", model_cached, rate_card["cached_input_rate_per_m"], credits_per_usd),
                _line_item("output", model_output, rate_card["output_rate_per_m"], credits_per_usd),
            ]
            model_cost = sum(item["costUSD"] for item in model_line_items)
            model_credits = model_cost * credits_per_usd
            verified_model_data = model_data.get("verifiedUsage") or model_data
            verified_model_line_items = [
                _line_item(
                    "non_cached_input",
                    int(verified_model_data.get("nonCachedInputTokens") or 0),
                    rate_card["input_rate_per_m"],
                    credits_per_usd,
                ),
                _line_item(
                    "cached_input",
                    int(verified_model_data.get("cachedInputTokens") or 0),
                    rate_card["cached_input_rate_per_m"],
                    credits_per_usd,
                ),
                _line_item(
                    "output",
                    int(verified_model_data.get("outputTokens") or 0),
                    rate_card["output_rate_per_m"],
                    credits_per_usd,
                ),
            ]
            model_verified_cost = sum(item["costUSD"] for item in verified_model_line_items)
            model_unverified_cost = max(model_cost - model_verified_cost, 0.0)
            by_model_cost[model] = {
                "modelLabel": model,
                "sessionCount": int(model_data.get("sessionCount") or 0),
                "totalTokens": int(model_data.get("totalTokens") or 0),
                "billableTokens": model_input + model_cached + model_output,
                "totalCostUSD": model_cost,
                "totalCredits": model_credits,
                "verifiedCostUSD": model_verified_cost,
                "unverifiedCostUSD": model_unverified_cost,
                "verifiedCredits": model_verified_cost * credits_per_usd,
                "unverifiedCredits": model_unverified_cost * credits_per_usd,
                "rateCardMatched": rate_card_matched,
                "rateCardStatus": rate_card["rate_card_status"],
                "rateCardSource": rate_card["rate_card_source"],
                "rateCardAsOf": rate_card["rate_card_as_of"],
                "ratesPerMillion": {
                    "input": rate_card["input_rate_per_m"],
                    "cachedInput": rate_card["cached_input_rate_per_m"],
                    "output": rate_card["output_rate_per_m"],
                },
                "lineItems": model_line_items,
            }
        result["byModel"] = by_model_cost
        result["unknownModels"] = unknown_models
        result["unpricedModels"] = unpriced_models

        # Override the global summary cost with the sum of per-model costs
        total_cost_by_model = sum(m["totalCostUSD"] for m in by_model_cost.values())
        total_credits_by_model = total_cost_by_model * credits_per_usd
        result["summary"]["totalCostUSD"] = total_cost_by_model
        result["summary"]["totalCredits"] = total_credits_by_model
        verified_cost_by_model = sum(m["verifiedCostUSD"] for m in by_model_cost.values())
        unverified_cost_by_model = max(total_cost_by_model - verified_cost_by_model, 0.0)
        result["summary"]["verifiedCostUSD"] = verified_cost_by_model
        result["summary"]["unverifiedCostUSD"] = unverified_cost_by_model
        result["summary"]["verifiedCredits"] = verified_cost_by_model * credits_per_usd
        result["summary"]["unverifiedCredits"] = unverified_cost_by_model * credits_per_usd
        statuses = {m["rateCardStatus"] for m in by_model_cost.values()}
        sources = {m["rateCardSource"] for m in by_model_cost.values()}
        result["summary"]["rateCardStatus"] = next(iter(statuses)) if len(statuses) == 1 else "mixed"
        result["summary"]["rateCardSource"] = next(iter(sources)) if len(sources) == 1 else "mixed"
        result["summary"]["rateCardAsOf"] = RATE_CARD_AS_OF
        # Update line items to reflect per-model cost aggregation
        result["lineItems"] = _aggregate_line_items_from_models(by_model_cost)

    return result


def render_codex_cost_report(cost_report: Dict[str, Any], lang: str = "en") -> str:
    text = TEXT[normalize_lang(lang)]
    summary = cost_report["summary"]
    line_items = cost_report["lineItems"]
    by_model_cost = cost_report.get("byModel") or {}
    if by_model_cost:
        pricing_line = f"{text['pricing']}: {text['by_model'].lower()}"
    else:
        pricing_line = (
            f"{text['pricing']}: {summary['modelLabel']} "
            f"(input ${summary['ratesPerMillion']['input']:g}/1M, "
            f"cached input ${summary['ratesPerMillion']['cachedInput']:g}/1M, "
            f"output ${summary['ratesPerMillion']['output']:g}/1M)"
        )
    lines = [
        text["title"],
        "",
        f"{text['window']}: {summary['windowStart']} -> {summary['windowEnd']}",
        f"{text['source']}: {summary['sourceRoot']}",
        pricing_line,
        f"{text['rate_card']}: {summary.get('rateCardStatus')} / {summary.get('rateCardSource')} / {summary.get('rateCardAsOf') or 'user supplied'}",
        "",
    ]
    unknown_models = cost_report.get("unknownModels") or []
    if unknown_models:
        lines.extend([text["unknown_warning"].format(models=", ".join(unknown_models)), ""])
    unpriced_models = cost_report.get("unpricedModels") or []
    if unpriced_models:
        warning = text.get(
            "unpriced_warning",
            "Warning: unpriced model(s) {models} used the gpt-5.5 fallback rate card.",
        )
        lines.extend([warning.format(models=", ".join(unpriced_models)), ""])

    lines.extend(
        [
            f"{text['inclusive']}: {_format_money(summary['totalCostUSD'])} / {_format_credits(summary['totalCredits'])} credits",
            f"{text['verified']}: {_format_money(summary['verifiedCostUSD'])} / {_format_credits(summary['verifiedCredits'])} credits",
            f"{text['unverified']}: {_format_money(summary['unverifiedCostUSD'])} / {_format_credits(summary['unverifiedCredits'])} credits",
            "",
        ]
    )

    lines.extend(
        render_table(
            [text["type"], text["tokens"], text["rate"], text["cost"], text["credits"]],
            [
                [
                    text[item["type"]],
                    _format_int(item["tokens"]),
                    "(mixed)"
                    if item.get("rateIsMixed")
                    else f"${item['ratePerMillion']:g} / 1M",
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

    if by_model_cost:
        lines.extend(
            [
                "",
                text["by_model"],
                *render_table(
                    [text["model"], text["model_rate_card"], text["cost"], text["credits"]],
                    [
                        [
                            model,
                            (
                                f"in:${data['ratesPerMillion']['input']:g} "
                                f"ci:${data['ratesPerMillion']['cachedInput']:g} "
                                f"out:${data['ratesPerMillion']['output']:g}"
                            ),
                            _format_money(data["totalCostUSD"]),
                            _format_credits(data["totalCredits"]),
                        ]
                        for model, data in sorted(by_model_cost.items())
                    ],
                ),
            ]
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
    by_model = cost_report.get("byModel") or {}

    sections = [
        _section(text["cost_mix"], _cost_mix_svg(line_items, text)),
        _section(text["details"], _cost_table(line_items, summary, text)),
    ]
    if by_model:
        sections.insert(1, _section(text["by_model"], _cost_by_model_section(by_model, text)))
    warning_messages = []
    if cost_report.get("unknownModels"):
        warning_messages.append(
            text["unknown_warning"].format(models=", ".join(cost_report["unknownModels"]))
        )
    if cost_report.get("unpricedModels"):
        warning_messages.append(
            text.get(
                "unpriced_warning",
                "Warning: unpriced model(s) {models} used the gpt-5.5 fallback rate card.",
            ).format(models=", ".join(cost_report["unpricedModels"]))
        )
    if warning_messages:
        sections.insert(0, _section(text["warning"], "".join(f"<p>{escape(message)}</p>" for message in warning_messages)))

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
            f"<div><span>{escape(text['inclusive'])} {escape(text['api_equivalent'])}</span>{escape(_format_money(summary['totalCostUSD']))}</div>",
            f"<div><span>{escape(text['inclusive'])} {escape(text['credits'])}</span>{escape(_format_credits(summary['totalCredits']))}</div>",
            f"<div><span>{escape(text['verified'])} {escape(text['api_equivalent'])}</span>{escape(_format_money(summary['verifiedCostUSD']))}</div>",
            f"<div><span>{escape(text['unverified'])} {escape(text['api_equivalent'])}</span>{escape(_format_money(summary['unverifiedCostUSD']))}</div>",
            f"<div><span>{escape(text['verified'])} Credits</span>{escape(_format_credits(summary['verifiedCredits']))}</div>",
            f"<div><span>{escape(text['unverified'])} Credits</span>{escape(_format_credits(summary['unverifiedCredits']))}</div>",
            f"<div><span>{escape(text['total_tokens'])}</span>{escape(_format_int(summary['totalTokens']))}</div>",
            f"<div><span>{escape(text['reasoning'])}</span>{escape(_format_int(summary['reasoningOutputTokens']))}</div>",
            f"<div><span>{escape(text['source'])}</span>{escape(str(summary['sourceRoot']))}</div>",
            f"<div><span>{escape(text['rate_card'])}</span>{escape(str(summary.get('rateCardStatus')))} / {escape(str(summary.get('rateCardSource')))}</div>",
            f"<div><span>{escape('Generated')}</span>{escape(generated)}</div>",
            "</div>",
            "</header>",
            *sections,
            _section(text["notes"], _notes(text)),
            "</main>",
            "</body>",
            "</html>",
            "",
        ]
    )


def _aggregate_line_items_from_models(by_model_cost: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Aggregate per-model line items into global line items (sum of costs across models)."""
    from collections import defaultdict

    by_type: Dict[str, Dict[str, float]] = defaultdict(lambda: {"tokens": 0, "costUSD": 0.0, "credits": 0.0})
    rates_by_type: Dict[str, set] = defaultdict(set)
    for model_data in by_model_cost.values():
        for item in model_data.get("lineItems") or []:
            bucket = by_type[item["type"]]
            bucket["tokens"] += item["tokens"]
            bucket["costUSD"] += item["costUSD"]
            bucket["credits"] += item["credits"]
            rates_by_type[item["type"]].add(float(item["ratePerMillion"]))
    result = []
    for item_type in ("non_cached_input", "cached_input", "output"):
        bucket = by_type[item_type]
        rates = rates_by_type[item_type]
        mixed = len(rates) > 1
        result.append(
            {
                "type": item_type,
                "tokens": int(bucket["tokens"]),
                "ratePerMillion": 0.0 if mixed or not rates else next(iter(rates)),
                "rateIsMixed": mixed,
                "costUSD": bucket["costUSD"],
                "credits": bucket["credits"],
            }
        )
    return result


def _line_item(item_type: str, tokens: int, rate_per_million: float, credits_per_usd: float) -> Dict[str, Any]:
    cost = tokens / 1_000_000 * rate_per_million
    return {
        "type": item_type,
        "tokens": tokens,
        "ratePerMillion": rate_per_million,
        "rateIsMixed": False,
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
        rate_text = (
            "(mixed)"
            if item.get("rateIsMixed")
            else f"${item['ratePerMillion']:g} / 1M"
        )
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


def _cost_by_model_section(by_model: Dict[str, Dict[str, Any]], text: Dict[str, str]) -> str:
    """Render the 'Cost by Model' section with a bar chart and table."""
    max_cost = max((float(m["totalCostUSD"]) for m in by_model.values()), default=0.0)
    if max_cost <= 0:
        max_cost = 1.0

    model_colors = ["#0f766e", "#2563eb", "#f59e0b", "#dc2626", "#7c3aed", "#4f46e5", "#059669"]
    width = 920
    left = 150
    top = 28
    row_h = 58
    chart_w = 700
    parts = [
        f'<svg class="chart" viewBox="0 0 {width} {top + len(by_model) * row_h + 40}" role="img" aria-label="{escape(text["by_model"])}">'
    ]
    labels = []
    for index, (model, data) in enumerate(sorted(by_model.items())):
        y = top + index * row_h
        color = model_colors[index % len(model_colors)]
        bar_w = chart_w * float(data["totalCostUSD"]) / max_cost
        parts.extend(
            [
                f'<text x="22" y="{y + 22}" fill="{COLORS["text"]}" font-size="15">{escape(model)}</text>',
                f'<rect x="{left}" y="{y}" width="{bar_w:.2f}" height="30" rx="4" fill="{color}" />',
                f'<text x="{min(left + bar_w + 12, width - 22):.2f}" y="{y + 21}" fill="{COLORS["text"]}" font-size="15">{escape(_format_money(data["totalCostUSD"]))}</text>',
            ]
        )
        labels.append(
            f'<span><i style="background:{color}"></i>{escape(model)}: {escape(_format_money(data["totalCostUSD"]))} ({escape(_format_credits(data["totalCredits"]))} credits)</span>'
        )
    parts.append("</svg>")
    parts.append('<div class="legend">' + "".join(labels) + "</div>")

    # Table
    table_rows = []
    for model, data in sorted(by_model.items()):
        rates = data.get("ratesPerMillion") or {}
        rate_text = (
            f"in:${rates.get('input', 0):g} "
            f"ci:${rates.get('cachedInput', 0):g} "
            f"out:${rates.get('output', 0):g}"
        )
        table_rows.append(
            "<tr>"
            f"<td>{escape(model)}</td>"
            f"<td>{escape(str(data.get('sessionCount') or 0))}</td>"
            f"<td>{escape(_format_int(data.get('totalTokens') or 0))}</td>"
            f"<td>{escape(rate_text)}</td>"
            f"<td>{escape(_format_money(data.get('totalCostUSD') or 0))}</td>"
            f"<td>{escape(_format_credits(data.get('totalCredits') or 0))}</td>"
            "</tr>"
        )

    table = "\n".join(
        [
            "<table>",
            "<thead><tr>"
            f"<th>{escape(text['model'])}</th>"
            f"<th>{escape(text['sessions'])}</th>"
            f"<th>{escape(text['total_tokens'])}</th>"
            f"<th>{escape(text['model_rate_card'])}</th>"
            f"<th>{escape(text['cost'])}</th>"
            f"<th>{escape(text['credits'])}</th>"
            "</tr></thead>",
            "<tbody>",
            *table_rows,
            "</tbody>",
            "</table>",
        ]
    )

    return "\n".join(parts) + "\n" + table


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

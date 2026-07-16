"""Regression tests for GPT-5.6 rate cards and Credits estimates."""

import unittest

from codex_usage.codex_cost import build_codex_cost_report, get_model_rate_card, render_codex_cost_report
from codex_usage.codex_summary import build_codex_summary, render_codex_summary


def usage_summary(by_model):
    total = sum(row["totalTokens"] for row in by_model.values())
    return {"summary": {
        "windowStart": "2026-07-16T00:00:00+08:00",
        "windowEnd": "2026-07-16T23:59:59+08:00",
        "sourceRoot": "test",
        "sessionCount": len(by_model),
        "tokenEventCount": len(by_model),
        "inputTokens": sum(row["inputTokens"] for row in by_model.values()),
        "cachedInputTokens": sum(row["cachedInputTokens"] for row in by_model.values()),
        "nonCachedInputTokens": sum(row["nonCachedInputTokens"] for row in by_model.values()),
        "outputTokens": sum(row["outputTokens"] for row in by_model.values()),
        "reasoningOutputTokens": 0,
        "totalTokens": total,
        "byModel": by_model,
    }}


def one_million_each():
    return {
        "sessionCount": 1,
        "inputTokens": 2_000_000,
        "cachedInputTokens": 1_000_000,
        "nonCachedInputTokens": 1_000_000,
        "outputTokens": 1_000_000,
        "reasoningOutputTokens": 0,
        "totalTokens": 3_000_000,
    }


class CostModelTests(unittest.TestCase):
    def test_gpt_5_6_rate_cards(self):
        expected = {
            "gpt-5.6": (5.0, 0.5, 30.0),
            "gpt-5.6-sol": (5.0, 0.5, 30.0),
            "gpt-5.6-terra": (2.5, 0.25, 15.0),
            "gpt-5.6-luna": (1.0, 0.1, 6.0),
        }
        for model, rates in expected.items():
            with self.subTest(model=model):
                card = get_model_rate_card(model)
                self.assertEqual(
                    (card["input_rate_per_m"], card["cached_input_rate_per_m"], card["output_rate_per_m"]),
                    rates,
                )

    def test_current_official_codex_rate_cards(self):
        for model in ("gpt-5.3-codex", "gpt-5.2"):
            with self.subTest(model=model):
                card = get_model_rate_card(model)
                self.assertEqual(
                    (card["input_rate_per_m"], card["cached_input_rate_per_m"], card["output_rate_per_m"]),
                    (1.75, 0.175, 14.0),
                )
                self.assertEqual(card["rate_card_status"], "priced")
                self.assertEqual(card["rate_card_source"], "openai-official")

    def test_per_model_costs_and_default_credits(self):
        by_model = {
            "gpt-5.6-sol": one_million_each(),
            "gpt-5.6-terra": one_million_each(),
            "gpt-5.6-luna": one_million_each(),
        }
        report = build_codex_cost_report(usage_summary(by_model))
        self.assertAlmostEqual(report["byModel"]["gpt-5.6-sol"]["totalCostUSD"], 35.5)
        self.assertAlmostEqual(report["byModel"]["gpt-5.6-terra"]["totalCostUSD"], 17.75)
        self.assertAlmostEqual(report["byModel"]["gpt-5.6-luna"]["totalCostUSD"], 7.1)
        self.assertAlmostEqual(report["summary"]["totalCostUSD"], 60.35)
        self.assertEqual(report["summary"]["creditsPerUSD"], 25.0)
        self.assertAlmostEqual(report["summary"]["totalCredits"], 60.35 * 25)

    def test_custom_credits_multiplier(self):
        report = build_codex_cost_report(
            usage_summary({"gpt-5.6-luna": one_million_each()}),
            credits_per_usd=10,
        )
        self.assertAlmostEqual(report["summary"]["totalCredits"], report["summary"]["totalCostUSD"] * 10)

    def test_unknown_model_falls_back_and_warns(self):
        report = build_codex_cost_report(usage_summary({"future-model": one_million_each()}))
        self.assertEqual(report["unknownModels"], ["future-model"])
        self.assertFalse(report["byModel"]["future-model"]["rateCardMatched"])
        self.assertAlmostEqual(report["byModel"]["future-model"]["totalCostUSD"], 35.5)
        rendered = render_codex_cost_report(report, lang="en")
        self.assertIn("future-model", rendered)
        self.assertIn("fallback", rendered.lower())
        summary = build_codex_summary({"summary": usage_summary({"future-model": one_million_each()})["summary"]}, report)
        self.assertIn("future-model", render_codex_summary(summary, lang="en"))

    def test_unpriced_spark_uses_fallback_and_warns(self):
        report = build_codex_cost_report(usage_summary({"gpt-5.3-codex-spark": one_million_each()}))

        model = report["byModel"]["gpt-5.3-codex-spark"]
        self.assertEqual(report["unpricedModels"], ["gpt-5.3-codex-spark"])
        self.assertEqual(model["rateCardStatus"], "unpriced-fallback")
        self.assertAlmostEqual(model["totalCostUSD"], 35.5)
        self.assertIn("unpriced", render_codex_cost_report(report, lang="en").lower())
        summary = build_codex_summary(usage_summary({"gpt-5.3-codex-spark": one_million_each()}), report)
        self.assertIn("unpriced", render_codex_summary(summary, lang="en").lower())

    def test_internal_alias_and_flat_rate_sources_are_explicit(self):
        internal = build_codex_cost_report(usage_summary({"codex-auto-review": one_million_each()}))
        flat = build_codex_cost_report(
            usage_summary({"gpt-5.6-sol": one_million_each()}), use_model_rates=False
        )

        self.assertEqual(
            internal["byModel"]["codex-auto-review"]["rateCardSource"],
            "repository-internal",
        )
        self.assertEqual(flat["summary"]["rateCardStatus"], "user-supplied")
        self.assertEqual(flat["summary"]["rateCardSource"], "user-supplied")

    def test_verified_and_unverified_cost_credit_identities(self):
        usage = one_million_each()
        usage["verifiedUsage"] = {
            "inputTokens": 1_000_000,
            "cachedInputTokens": 500_000,
            "nonCachedInputTokens": 500_000,
            "outputTokens": 500_000,
            "reasoningOutputTokens": 0,
            "totalTokens": 1_500_000,
        }
        report = build_codex_cost_report(usage_summary({"gpt-5.6-sol": usage}))
        summary = report["summary"]

        self.assertAlmostEqual(summary["totalCostUSD"], 35.5)
        self.assertAlmostEqual(summary["verifiedCostUSD"], 17.75)
        self.assertAlmostEqual(summary["unverifiedCostUSD"], 17.75)
        self.assertEqual(summary["totalCredits"], summary["totalCostUSD"] * 25)
        self.assertEqual(summary["verifiedCredits"], summary["verifiedCostUSD"] * 25)
        self.assertEqual(summary["unverifiedCredits"], summary["unverifiedCostUSD"] * 25)

    def test_mixed_rate_marker_does_not_mislabel_user_supplied_zero_rate(self):
        mixed = build_codex_cost_report(
            usage_summary(
                {
                    "gpt-5.6-sol": one_million_each(),
                    "gpt-5.6-terra": one_million_each(),
                }
            )
        )
        zero = build_codex_cost_report(
            usage_summary({"gpt-5.6-sol": one_million_each()}),
            input_rate_per_m=0,
            cached_input_rate_per_m=0,
            output_rate_per_m=0,
            use_model_rates=False,
        )

        self.assertTrue(mixed["lineItems"][0]["rateIsMixed"])
        self.assertFalse(zero["lineItems"][0]["rateIsMixed"])


if __name__ == "__main__":
    unittest.main()

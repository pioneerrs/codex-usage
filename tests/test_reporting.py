import json
import tempfile
import unittest
from pathlib import Path

from codex_usage.errors import UsageError
from codex_usage.reporting import (
    aggregate_breakdown,
    aggregate_rows,
    export_rows,
    filter_turns,
    render_breakdown,
    render_report,
    resolve_time_window,
)


class ReportingTests(unittest.TestCase):
    def test_aggregate_rows_applies_group_time_model_and_mode_filters(self):
        groups = [
            {"id": "tg_a", "name": "alpha"},
            {"id": "tg_b", "name": "beta"},
        ]
        snapshots = [
            {"taskGroupId": "tg_a", "timestamp": "2026-05-10T09:00:00+08:00", "usagePercent": 10},
            {"taskGroupId": "tg_a", "timestamp": "2026-05-10T12:00:00+08:00", "usagePercent": 12.5},
            {"taskGroupId": "tg_b", "timestamp": "2026-05-10T12:00:00+08:00", "usagePercent": 99},
        ]
        turns = [
            {
                "taskGroupId": "tg_a",
                "timestamp": "2026-05-10T10:00:00+08:00",
                "model": "gpt-5",
                "mode": "local",
                "visibleTokensEstimated": 100,
                "effectiveTokensEstimated": 250,
                "requestCountEstimated": 2,
                "toolCallCount": 4,
            },
            {
                "taskGroupId": "tg_a",
                "timestamp": "2026-05-10T13:00:00+08:00",
                "model": "gpt-5",
                "mode": "cloud",
                "visibleTokensEstimated": 999,
                "effectiveTokensEstimated": 999,
                "requestCountEstimated": 1,
                "toolCallCount": 0,
            },
            {
                "taskGroupId": "tg_b",
                "timestamp": "2026-05-10T10:00:00+08:00",
                "model": "gpt-5",
                "mode": "local",
                "visibleTokensEstimated": 500,
                "effectiveTokensEstimated": 500,
                "requestCountEstimated": 1,
                "toolCallCount": 1,
            },
        ]

        rows = aggregate_rows(
            groups,
            snapshots,
            turns,
            group_value="alpha",
            from_value="2026-05-10T08:30:00+08:00",
            to_value="2026-05-10T12:30:00+08:00",
            model="gpt-5",
            mode="local",
        )

        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["taskGroupName"], "alpha")
        self.assertEqual(row["turns"], 1)
        self.assertEqual(row["visibleTokensEstimated"], 100)
        self.assertEqual(row["effectiveTokensEstimated"], 250)
        self.assertEqual(row["requestsEstimated"], 2)
        self.assertEqual(row["toolCalls"], 4)
        self.assertEqual(row["usageDeltaPercent"], 2.5)
        self.assertEqual(row["visibleTokensPerUsagePercentEstimated"], 40)
        self.assertEqual(row["visibleTokensPerRequestEstimated"], 50)
        self.assertEqual(row["visibleTokensPerToolCallEstimated"], 25)

    def test_breakdown_groups_unknown_keys_and_sums_usage(self):
        turns = [
            {"model": "gpt-5", "visibleTokensEstimated": 10, "effectiveTokensEstimated": 25},
            {"model": "gpt-5", "visibleTokensEstimated": 15, "effectiveTokensEstimated": 38},
            {"visibleTokensEstimated": 2, "effectiveTokensEstimated": 6, "requestCountEstimated": 3},
        ]

        self.assertEqual(
            aggregate_breakdown(turns, "model"),
            [
                {
                    "key": "gpt-5",
                    "turns": 2,
                    "requestsEstimated": 0,
                    "toolCalls": 0,
                    "visibleTokensEstimated": 25,
                    "visibleSharePercent": 92.6,
                    "effectiveTokensEstimated": 63,
                    "effectiveSharePercent": 91.3,
                },
                {
                    "key": "unknown",
                    "turns": 1,
                    "requestsEstimated": 3,
                    "toolCalls": 0,
                    "visibleTokensEstimated": 2,
                    "visibleSharePercent": 7.4,
                    "effectiveTokensEstimated": 6,
                    "effectiveSharePercent": 8.7,
                },
            ],
        )

    def test_breakdown_render_includes_model_share_percentages(self):
        rows = aggregate_breakdown(
            [
                {"model": "gpt-5", "visibleTokensEstimated": 75, "effectiveTokensEstimated": 150},
                {"model": "gpt-4.1", "visibleTokensEstimated": 25, "effectiveTokensEstimated": 50},
            ],
            "model",
        )

        report = render_breakdown("Estimated Breakdown by Model", rows, lang="en")

        self.assertIn("Visible Share", report)
        self.assertIn("Effective Share", report)
        self.assertIn("75%", report)
        self.assertIn("25%", report)

    def test_report_and_json_export_handle_empty_rows(self):
        report = render_report([], lang="zh")
        self.assertIn("没有匹配的记录", report)
        self.assertIn("所有 token 数值均基于本地可见文本估算", report)

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "rows.json"
            export_rows([], output, "json")
            self.assertEqual(json.loads(output.read_text(encoding="utf-8")), [])

    def test_filter_turns_rejects_invalid_window(self):
        with self.assertRaisesRegex(UsageError, "start date is after"):
            resolve_time_window(from_value="2026-05-11", to_value="2026-05-10")

        with self.assertRaisesRegex(UsageError, "Could not parse --since"):
            filter_turns([], [], since="yesterday")


if __name__ == "__main__":
    unittest.main()

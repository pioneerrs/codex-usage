import unittest

from codex_usage.charts import render_codex_chart_html


class ChartTests(unittest.TestCase):
    def test_rate_limit_chart_shows_visible_latest_percent_labels(self):
        html = render_codex_chart_html(
            {
                "summary": {
                    "windowStart": "2026-05-11T00:00:00+08:00",
                    "windowEnd": "2026-05-11T23:59:59+08:00",
                    "sourceRoot": "/tmp/codex",
                    "sessionCount": 1,
                    "tokenEventCount": 2,
                    "inputTokens": 160,
                    "cachedInputTokens": 40,
                    "nonCachedInputTokens": 120,
                    "outputTokens": 25,
                    "reasoningOutputTokens": 5,
                    "totalTokens": 185,
                },
                "timeline": [
                    {
                        "bucketStart": "2026-05-11T09:00:00+08:00",
                        "bucketEnd": "2026-05-11T10:00:00+08:00",
                        "tokenEvents": 1,
                        "cachedInputTokens": 20,
                        "nonCachedInputTokens": 80,
                        "outputTokens": 10,
                        "totalTokens": 110,
                        "primaryUsedPercent": 5,
                        "secondaryUsedPercent": 7,
                    },
                    {
                        "bucketStart": "2026-05-11T10:00:00+08:00",
                        "bucketEnd": "2026-05-11T11:00:00+08:00",
                        "tokenEvents": 1,
                        "cachedInputTokens": 20,
                        "nonCachedInputTokens": 40,
                        "outputTokens": 15,
                        "totalTokens": 75,
                        "primaryUsedPercent": 9,
                        "secondaryUsedPercent": 11,
                    },
                ],
                "sessions": [
                    {
                        "sessionFile": "session.jsonl",
                        "lastEventAt": "2026-05-11T10:00:00+08:00",
                        "totalTokens": 185,
                        "outputTokens": 25,
                        "reasoningOutputTokens": 5,
                    }
                ],
            },
            lang="en",
        )

        self.assertIn("Rate Limits", html)
        self.assertIn("primary 9%", html)
        self.assertIn("secondary 11%", html)


if __name__ == "__main__":
    unittest.main()

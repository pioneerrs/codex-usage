import csv
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from codex_usage.codex_logs import (
    aggregate_codex_logs,
    discover_session_files,
    export_codex_report,
    read_token_events,
    render_codex_report,
    resolve_time_window,
)
from codex_usage.errors import UsageError


class CodexLogTests(unittest.TestCase):
    def test_read_token_events_skips_malformed_and_non_token_lines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "session.jsonl"
            path.write_text(
                "\n".join(
                    [
                        "{not-json",
                        json.dumps({"timestamp": "2026-05-10T08:00:00+08:00", "payload": {"type": "note"}}),
                        json.dumps(token_count_event("not-a-date", total_tokens=100)),
                        json.dumps(token_count_event("2026-05-10T09:00:00+08:00", total_tokens=0)),
                        json.dumps(
                            token_count_event(
                                "2026-05-10T10:00:00+08:00",
                                input_tokens=12,
                                cached_input_tokens=5,
                                output_tokens=4,
                                reasoning_output_tokens=1,
                                total_tokens=16,
                                primary=7,
                                secondary=9,
                            )
                        ),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            events = read_token_events(path)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["usage"]["input_tokens"], 12)
        self.assertEqual(events[0]["usage"]["cached_input_tokens"], 5)
        self.assertEqual(events[0]["rateLimits"]["primary"]["used_percent"], 7)

    def test_discover_session_files_deduplicates_by_filename_preferring_larger_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            active = home / "sessions" / "2026" / "05" / "10"
            archived = home / "archived_sessions"
            active.mkdir(parents=True)
            archived.mkdir()
            (active / "same.jsonl").write_text("short\n", encoding="utf-8")
            (archived / "same.jsonl").write_text("longer archived copy\n", encoding="utf-8")
            (archived / "archived-only.jsonl").write_text("{}\n", encoding="utf-8")

            files = discover_session_files(home)
            files_without_archived = discover_session_files(home, include_archived=False)

        self.assertEqual([path.name for path in files], ["archived-only.jsonl", "same.jsonl"])
        self.assertIn("archived_sessions", str(files[1]))
        self.assertEqual([path.name for path in files_without_archived], ["same.jsonl"])
        self.assertNotIn("archived_sessions", str(files_without_archived[0]))

    def test_aggregate_uses_window_delta_and_exports_csv_total_row(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            session_dir = home / "sessions" / "2026" / "05" / "10"
            session_dir.mkdir(parents=True)
            (session_dir / "session.jsonl").write_text(
                "\n".join(
                    [
                        json.dumps(
                            token_count_event(
                                "2026-05-10T08:00:00+08:00",
                                input_tokens=100,
                                cached_input_tokens=20,
                                output_tokens=10,
                                reasoning_output_tokens=2,
                                total_tokens=110,
                                primary=10,
                                secondary=20,
                            )
                        ),
                        json.dumps(
                            token_count_event(
                                "2026-05-10T10:00:00+08:00",
                                input_tokens=250,
                                cached_input_tokens=70,
                                output_tokens=40,
                                reasoning_output_tokens=8,
                                total_tokens=290,
                                primary=15,
                                secondary=25,
                            )
                        ),
                        json.dumps(
                            token_count_event(
                                "2026-05-10T11:00:00+08:00",
                                input_tokens=300,
                                cached_input_tokens=90,
                                output_tokens=45,
                                reasoning_output_tokens=9,
                                total_tokens=345,
                                primary=17,
                                secondary=30,
                            )
                        ),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            report = aggregate_codex_logs(
                start=datetime.fromisoformat("2026-05-10T09:00:00+08:00").astimezone(),
                end=datetime.fromisoformat("2026-05-10T12:00:00+08:00").astimezone(),
                codex_home=home,
            )
            output = home / "report.csv"
            export_codex_report(report, output, "csv")
            rows = list(csv.DictReader(output.read_text(encoding="utf-8").splitlines()))

        self.assertEqual(report["summary"]["sessionCount"], 1)
        self.assertEqual(report["summary"]["tokenEventCount"], 2)
        self.assertEqual(report["summary"]["inputTokens"], 200)
        self.assertEqual(report["summary"]["cachedInputTokens"], 70)
        self.assertEqual(report["summary"]["nonCachedInputTokens"], 130)
        self.assertEqual(report["summary"]["outputTokens"], 35)
        self.assertEqual(report["summary"]["reasoningOutputTokens"], 7)
        self.assertEqual(report["summary"]["totalTokens"], 235)
        self.assertEqual(report["summary"]["primaryUsedPercentDelta"], 2)
        self.assertEqual(rows[-1]["sessionFile"], "TOTAL")
        self.assertEqual(rows[-1]["tokenEvents"], "2")
        self.assertEqual(rows[-1]["totalTokens"], "235")

    def test_report_no_records_and_invalid_window_errors_are_user_facing(self):
        report = {
            "summary": {
                "windowStart": "2026-05-10T00:00:00+08:00",
                "windowEnd": "2026-05-10T23:59:59+08:00",
                "sourceRoot": "/tmp/codex",
                "sessionCount": 0,
                "tokenEventCount": 0,
                "inputTokens": 0,
                "cachedInputTokens": 0,
                "nonCachedInputTokens": 0,
                "outputTokens": 0,
                "reasoningOutputTokens": 0,
                "totalTokens": 0,
            },
            "sessions": [],
            "timeline": [],
        }
        self.assertIn("没有找到 Codex token_count 记录", render_codex_report(report, lang="zh"))

        with self.assertRaisesRegex(UsageError, "not both"):
            resolve_time_window(today=True, from_value="2026-05-10")

        with self.assertRaisesRegex(UsageError, "start time is after"):
            resolve_time_window(from_value="2026-05-11", to_value="2026-05-10")


def token_count_event(
    timestamp,
    input_tokens=0,
    cached_input_tokens=0,
    output_tokens=0,
    reasoning_output_tokens=0,
    total_tokens=0,
    primary=0,
    secondary=0,
):
    return {
        "timestamp": timestamp,
        "type": "event_msg",
        "payload": {
            "type": "token_count",
            "info": {
                "total_token_usage": {
                    "input_tokens": input_tokens,
                    "cached_input_tokens": cached_input_tokens,
                    "output_tokens": output_tokens,
                    "reasoning_output_tokens": reasoning_output_tokens,
                    "total_tokens": total_tokens,
                }
            },
            "rate_limits": {
                "primary": {
                    "used_percent": primary,
                    "window_minutes": 300,
                    "resets_at": 1778428491,
                },
                "secondary": {
                    "used_percent": secondary,
                    "window_minutes": 10080,
                    "resets_at": 1778654082,
                },
            },
        },
    }


if __name__ == "__main__":
    unittest.main()

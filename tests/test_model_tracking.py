"""Tests for per-model token tracking via turn_context events."""
import json
import tempfile
import unittest
from pathlib import Path

from codex_usage.codex_logs import aggregate_codex_logs, read_token_events, render_codex_report
from codex_usage.charts import render_codex_chart_html
from datetime import datetime


def turn_context_event(timestamp, model, turn_id="turn-001"):
    """Create a synthetic turn_context event."""
    return {
        "timestamp": timestamp,
        "type": "turn_context",
        "payload": {
            "turn_id": turn_id,
            "model": model,
            "cwd": "/tmp",
            "current_date": "2026-05-10",
            "timezone": "Asia/Shanghai",
        },
    }


def token_count_event(
    timestamp,
    input_tokens,
    cached_input_tokens,
    output_tokens,
    reasoning_output_tokens,
    total_tokens,
    primary=1,
    secondary=10,
):
    """Create a synthetic token_count event (inside event_msg)."""
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


class ReadTokenEventsModelTrackingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def _write_session(self, lines):
        path = Path(self.tmp.name) / "session.jsonl"
        path.write_text(
            "\n".join(json.dumps(obj) for obj in lines) + "\n",
            encoding="utf-8",
        )
        return path

    def test_single_model_events_get_model(self):
        path = self._write_session([
            turn_context_event("2026-05-10T10:00:00+08:00", "gpt-5.5", "turn-1"),
            token_count_event("2026-05-10T10:00:05+08:00", 100, 40, 10, 2, 110),
            token_count_event("2026-05-10T10:00:10+08:00", 300, 140, 30, 5, 330),
        ])
        events = read_token_events(path)
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]["model"], "gpt-5.5")
        self.assertEqual(events[1]["model"], "gpt-5.5")

    def test_no_turn_context_model_is_none(self):
        path = self._write_session([
            token_count_event("2026-05-10T10:00:05+08:00", 100, 40, 10, 2, 110),
        ])
        events = read_token_events(path)
        self.assertEqual(len(events), 1)
        self.assertIsNone(events[0]["model"])

    def test_model_updates_on_new_turn_context(self):
        path = self._write_session([
            turn_context_event("2026-05-10T10:00:00+08:00", "gpt-5.5", "turn-1"),
            token_count_event("2026-05-10T10:00:05+08:00", 100, 40, 10, 2, 110),
            turn_context_event("2026-05-10T10:05:00+08:00", "gpt-5.4-mini", "turn-2"),
            token_count_event("2026-05-10T10:05:05+08:00", 500, 200, 50, 10, 550),
        ])
        events = read_token_events(path)
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]["model"], "gpt-5.5")
        self.assertEqual(events[1]["model"], "gpt-5.4-mini")

    def test_empty_session_returns_no_events(self):
        path = self._write_session([])
        events = read_token_events(path)
        self.assertEqual(len(events), 0)

    def test_turn_context_without_model_keeps_previous(self):
        tc_no_model = {
            "timestamp": "2026-05-10T10:05:00+08:00",
            "type": "turn_context",
            "payload": {"turn_id": "turn-2"},
        }
        path = self._write_session([
            turn_context_event("2026-05-10T10:00:00+08:00", "gpt-5.5", "turn-1"),
            token_count_event("2026-05-10T10:00:05+08:00", 100, 40, 10, 2, 110),
            tc_no_model,
            token_count_event("2026-05-10T10:05:05+08:00", 500, 200, 50, 10, 550),
        ])
        events = read_token_events(path)
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]["model"], "gpt-5.5")
        self.assertEqual(events[1]["model"], "gpt-5.5")

    def test_other_event_types_ignored(self):
        other_event = {
            "timestamp": "2026-05-10T10:00:03+08:00",
            "type": "event_msg",
            "payload": {"type": "agent_message", "message": "hello"},
        }
        path = self._write_session([
            turn_context_event("2026-05-10T10:00:00+08:00", "gpt-5.5", "turn-1"),
            other_event,
            token_count_event("2026-05-10T10:00:05+08:00", 100, 40, 10, 2, 110),
        ])
        events = read_token_events(path)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["model"], "gpt-5.5")


class AggregatePerModelTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.codex_home = Path(self.tmp.name) / "codex-home"
        self.session_dir = self.codex_home / "sessions" / "2026" / "05" / "10"
        self.session_dir.mkdir(parents=True)

    def _write_session(self, filename, lines):
        path = self.session_dir / filename
        path.write_text(
            "\n".join(json.dumps(obj) for obj in lines) + "\n",
            encoding="utf-8",
        )
        return path

    def test_by_model_uses_per_event_attribution(self):
        self._write_session("multi-model.jsonl", [
            turn_context_event("2026-05-10T10:00:00+08:00", "gpt-5.5", "turn-1"),
            token_count_event("2026-05-10T10:00:05+08:00", 1000, 400, 100, 20, 1100),
            turn_context_event("2026-05-10T10:05:00+08:00", "gpt-5.4-mini", "turn-2"),
            token_count_event("2026-05-10T10:05:05+08:00", 2000, 800, 200, 40, 2200),
        ])

        start = datetime(2026, 5, 10).astimezone()
        end = datetime(2026, 5, 10, 23, 59, 59).astimezone()
        report = aggregate_codex_logs(start, end, codex_home=self.codex_home)

        by_model = report["summary"]["byModel"]
        self.assertIn("gpt-5.5", by_model)
        self.assertIn("gpt-5.4-mini", by_model)
        self.assertEqual(by_model["gpt-5.5"]["totalTokens"], 1100)
        self.assertEqual(by_model["gpt-5.4-mini"]["totalTokens"], 1100)

    def test_total_tokens_match_by_model_sum(self):
        self._write_session("single.jsonl", [
            turn_context_event("2026-05-10T10:00:00+08:00", "gpt-5.5", "turn-1"),
            token_count_event("2026-05-10T10:00:05+08:00", 1000, 400, 100, 20, 1100),
        ])

        start = datetime(2026, 5, 10).astimezone()
        end = datetime(2026, 5, 10, 23, 59, 59).astimezone()
        report = aggregate_codex_logs(start, end, codex_home=self.codex_home)

        total = report["summary"]["totalTokens"]
        by_model_sum = sum(d["totalTokens"] for d in report["summary"]["byModel"].values())
        self.assertEqual(total, by_model_sum)

    def test_session_row_uses_session_level_model(self):
        self._write_session("multi.jsonl", [
            turn_context_event("2026-05-10T10:00:00+08:00", "gpt-5.5", "turn-1"),
            token_count_event("2026-05-10T10:00:05+08:00", 1000, 400, 100, 20, 1100),
            turn_context_event("2026-05-10T10:05:00+08:00", "gpt-5.4-mini", "turn-2"),
            token_count_event("2026-05-10T10:05:05+08:00", 2000, 800, 200, 40, 2200),
        ])

        start = datetime(2026, 5, 10).astimezone()
        end = datetime(2026, 5, 10, 23, 59, 59).astimezone()
        report = aggregate_codex_logs(start, end, codex_home=self.codex_home)

        self.assertEqual(len(report["sessions"]), 1)
        self.assertEqual(report["sessions"][0]["model"], "gpt-5.5")

    def test_counter_reset_uses_one_delta_stream_everywhere(self):
        self._write_session("reset.jsonl", [
            turn_context_event("2026-05-10T10:00:00+08:00", "gpt-5.5", "turn-1"),
            token_count_event("2026-05-10T10:00:05+08:00", 90, 40, 10, 2, 100),
            token_count_event("2026-05-10T10:01:05+08:00", 8, 3, 2, 1, 10),
            turn_context_event("2026-05-10T10:02:00+08:00", "gpt-5.4-mini", "turn-2"),
            token_count_event("2026-05-10T10:02:05+08:00", 24, 8, 6, 2, 30),
        ])

        start = datetime(2026, 5, 10).astimezone()
        end = datetime(2026, 5, 10, 23, 59, 59).astimezone()
        report = aggregate_codex_logs(start, end, codex_home=self.codex_home)

        summary = report["summary"]
        session_total = sum(row["totalTokens"] for row in report["sessions"])
        timeline_total = sum(row["totalTokens"] for row in report["timeline"])
        model_total = sum(row["totalTokens"] for row in summary["byModel"].values())
        self.assertEqual(summary["totalTokens"], 130)
        self.assertEqual({summary["totalTokens"], session_total, timeline_total, model_total}, {130})
        self.assertEqual(summary["counterResetCount"], 1)

    def test_model_filter_applies_to_event_deltas(self):
        self._write_session("multi-filter.jsonl", [
            turn_context_event("2026-05-10T10:00:00+08:00", "gpt-5.5", "turn-1"),
            token_count_event("2026-05-10T10:00:05+08:00", 90, 40, 10, 2, 100),
            turn_context_event("2026-05-10T10:05:00+08:00", "gpt-5.4-mini", "turn-2"),
            token_count_event("2026-05-10T10:05:05+08:00", 135, 60, 15, 3, 150),
        ])

        start = datetime(2026, 5, 10).astimezone()
        end = datetime(2026, 5, 10, 23, 59, 59).astimezone()
        first = aggregate_codex_logs(start, end, codex_home=self.codex_home, model_filter="gpt-5.5")
        second = aggregate_codex_logs(start, end, codex_home=self.codex_home, model_filter="gpt-5.4-mini")

        self.assertEqual(first["summary"]["totalTokens"], 100)
        self.assertEqual(set(first["summary"]["byModel"]), {"gpt-5.5"})
        self.assertEqual(second["summary"]["totalTokens"], 50)
        self.assertEqual(set(second["summary"]["byModel"]), {"gpt-5.4-mini"})

    def test_component_regression_is_clamped_and_audited(self):
        self._write_session("component-regression.jsonl", [
            turn_context_event("2026-05-10T10:00:00+08:00", "gpt-5.5"),
            token_count_event("2026-05-10T10:00:05+08:00", 90, 40, 10, 2, 100),
            token_count_event("2026-05-10T10:01:05+08:00", 80, 30, 40, 5, 120),
        ])
        start = datetime(2026, 5, 10).astimezone()
        end = datetime(2026, 5, 10, 23, 59, 59).astimezone()

        summary = aggregate_codex_logs(start, end, codex_home=self.codex_home)["summary"]

        self.assertEqual(summary["inputTokens"], 90)
        self.assertEqual(summary["totalTokens"], 120)
        self.assertEqual(summary["counterAnomalyCount"], 1)

    def test_duplicate_snapshot_counts_event_but_adds_zero_delta(self):
        event = token_count_event("2026-05-10T10:00:05+08:00", 90, 40, 10, 2, 100)
        duplicate = dict(event, timestamp="2026-05-10T10:01:05+08:00")
        self._write_session("duplicate.jsonl", [
            turn_context_event("2026-05-10T10:00:00+08:00", "gpt-5.5"),
            event,
            duplicate,
        ])
        start = datetime(2026, 5, 10).astimezone()
        end = datetime(2026, 5, 10, 23, 59, 59).astimezone()

        summary = aggregate_codex_logs(start, end, codex_home=self.codex_home)["summary"]

        self.assertEqual(summary["totalTokens"], 100)
        self.assertEqual(summary["tokenEventCount"], 2)

    def test_zero_total_snapshot_is_a_valid_counter_reset(self):
        self._write_session("zero-reset.jsonl", [
            turn_context_event("2026-05-10T10:00:00+08:00", "gpt-5.5"),
            token_count_event("2026-05-10T10:00:05+08:00", 90, 40, 10, 2, 100),
            token_count_event("2026-05-10T10:01:05+08:00", 0, 0, 0, 0, 0),
            token_count_event("2026-05-10T10:02:05+08:00", 8, 3, 2, 1, 10),
        ])
        start = datetime(2026, 5, 10).astimezone()
        end = datetime(2026, 5, 10, 23, 59, 59).astimezone()

        summary = aggregate_codex_logs(start, end, codex_home=self.codex_home)["summary"]

        self.assertEqual(summary["totalTokens"], 110)
        self.assertEqual(summary["tokenEventCount"], 3)
        self.assertEqual(summary["counterResetCount"], 1)

    def test_line_order_wins_over_out_of_order_timestamps(self):
        self._write_session("out-of-order.jsonl", [
            turn_context_event("2026-05-10T10:00:00+08:00", "gpt-5.5"),
            token_count_event("2026-05-10T10:05:05+08:00", 90, 40, 10, 2, 100),
            token_count_event("2026-05-10T10:01:05+08:00", 135, 60, 15, 3, 150),
        ])
        start = datetime(2026, 5, 10).astimezone()
        end = datetime(2026, 5, 10, 23, 59, 59).astimezone()

        report = aggregate_codex_logs(start, end, codex_home=self.codex_home)

        self.assertEqual(report["summary"]["totalTokens"], 150)
        self.assertEqual(sum(row["totalTokens"] for row in report["timeline"]), 150)

    def test_zero_rate_limit_snapshot_is_preserved_as_reset(self):
        self._write_session("rate-reset.jsonl", [
            turn_context_event("2026-05-10T10:00:00+08:00", "gpt-5.5"),
            token_count_event("2026-05-10T10:00:05+08:00", 90, 40, 10, 2, 100, primary=90),
            token_count_event("2026-05-10T10:01:05+08:00", 90, 40, 10, 2, 100, primary=0),
        ])
        start = datetime(2026, 5, 10).astimezone()
        end = datetime(2026, 5, 10, 23, 59, 59).astimezone()

        summary = aggregate_codex_logs(start, end, codex_home=self.codex_home)["summary"]

        self.assertEqual(summary["primaryUsedPercentLatest"], 0)
        self.assertEqual(summary["primaryUsedPercentDelta"], -90)

    def test_damaged_and_invalid_lines_are_counted_without_leaking_content(self):
        path = self.session_dir / "damaged.jsonl"
        valid = token_count_event("2026-05-10T10:00:05+08:00", 90, 40, 10, 2, 100)
        invalid_usage = token_count_event("2026-05-10T10:01:05+08:00", 90, 40, 10, 2, "not-a-number")
        invalid_time = token_count_event("not-a-time", 100, 40, 10, 2, 110)
        payload = (
            json.dumps(turn_context_event("2026-05-10T10:00:00+08:00", "gpt-5.5")).encode()
            + b"\n{\"private-marker\":\xff}\n"
            + b'{"type":"event_msg","payload":{"type":"token_count"}\n'
            + json.dumps(invalid_usage).encode() + b"\n"
            + json.dumps(invalid_time).encode() + b"\n"
            + json.dumps(valid).encode() + b"\n"
        )
        path.write_bytes(payload)
        start = datetime(2026, 5, 10).astimezone()
        end = datetime(2026, 5, 10, 23, 59, 59).astimezone()

        report = aggregate_codex_logs(start, end, codex_home=self.codex_home)
        rendered = render_codex_report(report, lang="en")
        chart = render_codex_chart_html(report, lang="en")

        self.assertEqual(report["summary"]["damagedLineCount"], 2)
        self.assertEqual(report["summary"]["invalidTokenEventCount"], 2)
        self.assertNotIn("private-marker", rendered)
        self.assertIn("Data Quality Warning", chart)
        self.assertNotIn("private-marker", chart)


if __name__ == "__main__":
    unittest.main()

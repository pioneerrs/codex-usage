"""Tests for per-model token tracking via turn_context events."""
import json
import tempfile
import unittest
from pathlib import Path

from codex_usage.codex_logs import read_token_events, aggregate_codex_logs
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


if __name__ == "__main__":
    unittest.main()

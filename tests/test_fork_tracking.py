"""Regression tests for inherited token counters in forked sessions."""

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from codex_usage.codex_logs import aggregate_codex_logs, render_codex_report


SHANGHAI = timezone(timedelta(hours=8))


def session_meta(timestamp, session_id, forked_from_id=None):
    payload = {"id": session_id, "timestamp": timestamp}
    if forked_from_id:
        payload["forked_from_id"] = forked_from_id
    return {"timestamp": timestamp, "type": "session_meta", "payload": payload}


def turn_context(timestamp, model):
    return {
        "timestamp": timestamp,
        "type": "turn_context",
        "payload": {"turn_id": timestamp, "model": model},
    }


def token_event(timestamp, total, model_input=None, cached=None, output=None, reasoning=None):
    input_tokens = total - 20 if model_input is None else model_input
    cached_tokens = max(input_tokens - 40, 0) if cached is None else cached
    output_tokens = total - input_tokens if output is None else output
    reasoning_tokens = output_tokens // 2 if reasoning is None else reasoning
    return {
        "timestamp": timestamp,
        "type": "event_msg",
        "payload": {
            "type": "token_count",
            "info": {
                "total_token_usage": {
                    "input_tokens": input_tokens,
                    "cached_input_tokens": cached_tokens,
                    "output_tokens": output_tokens,
                    "reasoning_output_tokens": reasoning_tokens,
                    "total_tokens": total,
                }
            },
            "rate_limits": {
                "primary": {"used_percent": total % 100},
                "secondary": {"used_percent": (total + 1) % 100},
            },
        },
    }


class ForkTrackingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.codex_home = Path(self.tmp.name) / "codex-home"

    def _write(self, day, name, lines):
        directory = self.codex_home / "sessions" / day.strftime("%Y") / day.strftime("%m") / day.strftime("%d")
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{name}.jsonl"
        path.write_text("\n".join(json.dumps(line) for line in lines) + "\n", encoding="utf-8")
        return path

    def _report(self, day=datetime(2026, 7, 16, tzinfo=SHANGHAI)):
        start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        end = day.replace(hour=23, minute=59, second=59, microsecond=999999)
        return aggregate_codex_logs(start, end, codex_home=self.codex_home)

    def test_replayed_parent_baseline_is_excluded_everywhere(self):
        day = datetime(2026, 7, 16, tzinfo=SHANGHAI)
        self._write(day, "parent", [
            session_meta("2026-07-16T09:00:00+08:00", "parent"),
            turn_context("2026-07-16T09:00:01+08:00", "gpt-5.6-sol"),
            token_event("2026-07-16T09:30:00+08:00", 300, 280, 240, 20, 10),
        ])
        self._write(day, "child", [
            session_meta("2026-07-16T10:00:00+08:00", "child", "parent"),
            turn_context("2026-07-16T10:00:00.001+08:00", "gpt-5.6-sol"),
            token_event("2026-07-16T10:00:06+08:00", 300, 280, 240, 20, 10),
            turn_context("2026-07-16T10:05:00+08:00", "gpt-5.6-terra"),
            token_event("2026-07-16T10:05:05+08:00", 350, 325, 260, 25, 12),
        ])

        report = self._report()
        summary = report["summary"]
        self.assertEqual(summary["totalTokens"], 350)
        self.assertEqual(summary["tokenEventCount"], 2)
        self.assertEqual(summary["forkSessionCount"], 1)
        self.assertEqual(summary["resolvedForkCount"], 1)
        self.assertEqual(summary["unresolvedForkCount"], 0)
        self.assertEqual(summary["forkReplayTokensExcluded"], 300)
        self.assertEqual(sum(row["totalTokens"] for row in report["timeline"]), 350)
        self.assertEqual(sum(row["totalTokens"] for row in summary["byModel"].values()), 350)
        self.assertEqual(summary["byModel"]["gpt-5.6-sol"]["totalTokens"], 300)
        self.assertEqual(summary["byModel"]["gpt-5.6-terra"]["totalTokens"], 50)

        child = next(row for row in report["sessions"] if row["sessionFile"] == "child.jsonl")
        self.assertEqual(child["forkedFromId"], "parent")
        self.assertEqual(child["forkBaselineStatus"], "resolved")
        self.assertEqual(child["forkReplayTokensExcluded"], 300)
        self.assertEqual(child["tokenEvents"], 1)
        self.assertEqual(child["totalTokens"], 50)
        self.assertEqual(child["primaryUsedPercentLatest"], 50)

    def test_sibling_nested_and_pure_replay_forks(self):
        day = datetime(2026, 7, 16, tzinfo=SHANGHAI)
        self._write(day, "parent", [
            session_meta("2026-07-16T08:00:00+08:00", "parent"),
            turn_context("2026-07-16T08:00:01+08:00", "gpt-5.6-sol"),
            token_event("2026-07-16T08:10:00+08:00", 100),
        ])
        self._write(day, "sibling-a", [
            session_meta("2026-07-16T09:00:00+08:00", "sibling-a", "parent"),
            turn_context("2026-07-16T09:00:00.001+08:00", "gpt-5.6-sol"),
            token_event("2026-07-16T09:00:00.002+08:00", 100),
            token_event("2026-07-16T09:10:00+08:00", 130),
        ])
        self._write(day, "sibling-b", [
            session_meta("2026-07-16T09:30:00+08:00", "sibling-b", "parent"),
            turn_context("2026-07-16T09:30:00.001+08:00", "gpt-5.6-sol"),
            token_event("2026-07-16T09:30:00.002+08:00", 100),
            token_event("2026-07-16T09:40:00+08:00", 140),
        ])
        self._write(day, "nested", [
            session_meta("2026-07-16T10:00:00+08:00", "nested", "sibling-a"),
            turn_context("2026-07-16T10:00:00.001+08:00", "gpt-5.6-sol"),
            token_event("2026-07-16T10:00:00.002+08:00", 130),
            token_event("2026-07-16T10:10:00+08:00", 150),
        ])
        self._write(day, "pure-copy", [
            session_meta("2026-07-16T11:00:00+08:00", "pure-copy", "parent"),
            turn_context("2026-07-16T11:00:00.001+08:00", "gpt-5.6-sol"),
            token_event("2026-07-16T11:00:00.002+08:00", 100),
        ])

        report = self._report()
        self.assertEqual(report["summary"]["totalTokens"], 190)
        self.assertEqual(report["summary"]["forkSessionCount"], 4)
        self.assertEqual(report["summary"]["resolvedForkCount"], 4)
        self.assertEqual(report["summary"]["forkReplayTokensExcluded"], 430)
        self.assertNotIn("pure-copy.jsonl", {row["sessionFile"] for row in report["sessions"]})

    def test_cross_day_fork_uses_inherited_baseline(self):
        parent_day = datetime(2026, 7, 15, tzinfo=SHANGHAI)
        report_day = datetime(2026, 7, 16, tzinfo=SHANGHAI)
        self._write(parent_day, "parent", [
            session_meta("2026-07-15T20:00:00+08:00", "parent"),
            turn_context("2026-07-15T20:00:01+08:00", "gpt-5.6-sol"),
            token_event("2026-07-15T20:10:00+08:00", 400),
        ])
        self._write(parent_day, "child", [
            session_meta("2026-07-15T21:00:00+08:00", "child", "parent"),
            turn_context("2026-07-15T21:00:00.001+08:00", "gpt-5.6-sol"),
            token_event("2026-07-15T21:00:00.002+08:00", 400),
            token_event("2026-07-16T08:00:00+08:00", 460),
        ])

        report = self._report(report_day)
        self.assertEqual(report["summary"]["totalTokens"], 60)
        self.assertEqual(report["summary"]["forkSessionCount"], 1)
        self.assertEqual(report["summary"]["resolvedForkCount"], 1)
        self.assertEqual(report["summary"]["forkReplayTokensExcluded"], 0)

    def test_old_format_without_replay_is_counted_normally(self):
        day = datetime(2026, 7, 16, tzinfo=SHANGHAI)
        self._write(day, "parent", [
            session_meta("2026-07-16T08:00:00+08:00", "parent"),
            turn_context("2026-07-16T08:00:01+08:00", "gpt-5.6-sol"),
            token_event("2026-07-16T08:10:00+08:00", 300),
        ])
        self._write(day, "old-child", [
            session_meta("2026-07-16T09:00:00+08:00", "old-child", "parent"),
            turn_context("2026-07-16T09:10:00+08:00", "gpt-5.6-luna"),
            token_event("2026-07-16T09:10:01+08:00", 40),
        ])

        report = self._report()
        child = next(row for row in report["sessions"] if row["sessionFile"] == "old-child.jsonl")
        self.assertEqual(child["forkBaselineStatus"], "not_replayed")
        self.assertEqual(child["totalTokens"], 40)
        self.assertEqual(report["summary"]["totalTokens"], 340)
        self.assertEqual(report["summary"]["unresolvedForkCount"], 0)

    def test_missing_parent_and_mismatched_early_replay_are_unresolved(self):
        day = datetime(2026, 7, 16, tzinfo=SHANGHAI)
        self._write(day, "parent", [
            session_meta("2026-07-16T08:00:00+08:00", "parent"),
            turn_context("2026-07-16T08:00:01+08:00", "gpt-5.6-sol"),
            token_event("2026-07-16T08:10:00+08:00", 300),
        ])
        self._write(day, "missing-parent", [
            session_meta("2026-07-16T09:00:00+08:00", "missing-parent", "absent"),
            turn_context("2026-07-16T09:00:00.001+08:00", "gpt-5.6-sol"),
            token_event("2026-07-16T09:00:00.002+08:00", 200),
            token_event("2026-07-16T09:05:00+08:00", 220),
        ])
        self._write(day, "mismatch", [
            session_meta("2026-07-16T10:00:00+08:00", "mismatch", "parent"),
            turn_context("2026-07-16T10:00:00.001+08:00", "gpt-5.6-sol"),
            token_event("2026-07-16T10:00:00.002+08:00", 299),
            token_event("2026-07-16T10:05:00+08:00", 330),
        ])

        report = self._report()
        self.assertEqual(report["summary"]["unresolvedForkCount"], 2)
        self.assertEqual(report["summary"]["resolvedForkCount"], 0)
        self.assertEqual(report["summary"]["totalTokens"], 850)
        statuses = {row["sessionFile"]: row["forkBaselineStatus"] for row in report["sessions"]}
        self.assertEqual(statuses["missing-parent.jsonl"], "unresolved")
        self.assertEqual(statuses["mismatch.jsonl"], "unresolved")
        self.assertIn("Warning: unresolved forks", render_codex_report(report, lang="en"))


if __name__ == "__main__":
    unittest.main()

import contextlib
import io
import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path

from codex_usage import cli


class FakeEncoding:
    def encode(self, text):
        return text.split()


class CliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cwd = os.getcwd()
        os.chdir(self.tmp.name)
        self.addCleanup(lambda: os.chdir(self.cwd))
        self.old_tiktoken = sys.modules.get("tiktoken")
        fake_tiktoken = types.SimpleNamespace(
            get_encoding=lambda name: FakeEncoding(),
            encoding_for_model=lambda model: FakeEncoding(),
        )
        sys.modules["tiktoken"] = fake_tiktoken
        self.addCleanup(self._restore_tiktoken)

    def _restore_tiktoken(self):
        if self.old_tiktoken is None:
            sys.modules.pop("tiktoken", None)
        else:
            sys.modules["tiktoken"] = self.old_tiktoken

    def run_cli(self, *args, stdin=None):
        stdout = io.StringIO()
        stderr = io.StringIO()
        old_stdin = sys.stdin
        if stdin is not None:
            sys.stdin = io.StringIO(stdin)
        try:
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                code = cli.main(list(args))
        finally:
            sys.stdin = old_stdin
        return code, stdout.getvalue(), stderr.getvalue()

    def test_acceptance_flow_and_report(self):
        self.assertEqual(self.run_cli("init")[0], 0)
        self.assertEqual(self.run_cli("group", "create", "quick-chat", "--label", "chat")[0], 0)
        self.assertEqual(self.run_cli("snapshot", "--group", "quick-chat", "--usage", "10")[0], 0)
        Path("chat.md").write_text(
            "<!-- codex-usage:user -->\nhello codex\n"
            "<!-- codex-usage:assistant -->\nhello user\n",
            encoding="utf-8",
        )
        code, _, err = self.run_cli(
            "turn",
            "add",
            "--group",
            "quick-chat",
            "--file",
            "chat.md",
            "--task-type",
            "simple_chat",
            "--requests",
            "1",
        )
        self.assertEqual(code, 0, err)
        self.assertEqual(self.run_cli("snapshot", "--group", "quick-chat", "--usage", "10.2")[0], 0)

        code, out, err = self.run_cli("report", "--group", "quick-chat", "--lang", "en")
        self.assertEqual(code, 0, err)
        self.assertIn("quick-chat", out)
        self.assertIn("0.2%", out)
        self.assertIn("All token values are estimated", out)
        self.assertNotIn("所有 token 数值均基于本地可见文本估算", out)

        code, zh_out, err = self.run_cli("report", "--group", "quick-chat", "--lang", "zh")
        self.assertEqual(code, 0, err)
        self.assertIn("已记录的 Codex 用量估算报告", zh_out)
        self.assertIn("所有 token 数值均基于本地可见文本估算", zh_out)
        self.assertNotIn("All token values are estimated", zh_out)

        turns = [
            json.loads(line)
            for line in Path(".codex-usage/turns.jsonl").read_text(encoding="utf-8").splitlines()
        ]
        self.assertEqual(turns[0]["userTokensEstimated"], 2)
        self.assertEqual(turns[0]["assistantTokensEstimated"], 2)
        self.assertEqual(turns[0]["visibleTokensEstimated"], 4)
        self.assertEqual(turns[0]["effectiveTokensEstimated"], 6)

    def test_export_csv(self):
        self.run_cli("init")
        self.run_cli("group", "create", "repo-refactor")
        self.run_cli("snapshot", "--group", "repo-refactor", "--remaining", "58")
        self.run_cli("turn", "add", "--group", "repo-refactor", "--stdin", stdin="one two three")
        self.run_cli("snapshot", "--group", "repo-refactor", "--remaining", "57")
        code, out, err = self.run_cli("export", "--format", "csv", "--output", "usage.csv")
        self.assertEqual(code, 0, err)
        self.assertIn("Exported 1 row", out)
        self.assertIn("repo-refactor", Path("usage.csv").read_text(encoding="utf-8"))

    def test_snapshot_validation(self):
        self.run_cli("init")
        self.run_cli("group", "create", "bad-percent")
        code, _, err = self.run_cli(
            "snapshot",
            "--group",
            "bad-percent",
            "--usage",
            "70",
            "--remaining",
            "40",
        )
        self.assertEqual(code, 1)
        self.assertIn("inconsistent", err)

    def test_codex_log_export_uses_window_delta(self):
        codex_home = Path("codex-home")
        session_dir = codex_home / "sessions" / "2026" / "05" / "10"
        session_dir.mkdir(parents=True)
        session_file = session_dir / "rollout-test.jsonl"
        session_file.write_text(
            "\n".join(
                [
                    json.dumps(
                        token_count_event(
                            "2026-05-09T23:59:00+08:00",
                            input_tokens=100,
                            cached_input_tokens=40,
                            output_tokens=10,
                            reasoning_output_tokens=2,
                            total_tokens=110,
                            primary=1,
                            secondary=10,
                        )
                    ),
                    json.dumps(
                        token_count_event(
                            "2026-05-10T10:00:00+08:00",
                            input_tokens=300,
                            cached_input_tokens=140,
                            output_tokens=30,
                            reasoning_output_tokens=5,
                            total_tokens=330,
                            primary=2,
                            secondary=11,
                        )
                    ),
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        code, out, err = self.run_cli(
            "codex",
            "export",
            "--date",
            "2026-05-10",
            "--codex-home",
            str(codex_home),
            "--format",
            "json",
            "--output",
            "codex.json",
        )
        self.assertEqual(code, 0, err)
        self.assertIn("Exported 1 Codex session row", out)
        payload = json.loads(Path("codex.json").read_text(encoding="utf-8"))
        self.assertEqual(payload["summary"]["inputTokens"], 200)
        self.assertEqual(payload["summary"]["cachedInputTokens"], 100)
        self.assertEqual(payload["summary"]["nonCachedInputTokens"], 100)
        self.assertEqual(payload["summary"]["outputTokens"], 20)
        self.assertEqual(payload["summary"]["reasoningOutputTokens"], 3)
        self.assertEqual(payload["summary"]["totalTokens"], 220)
        self.assertEqual(payload["summary"]["secondaryUsedPercentLatest"], 11)
        self.assertEqual(sum(row["totalTokens"] for row in payload["timeline"]), 220)

        code, report, err = self.run_cli(
            "codex",
            "report",
            "--date",
            "2026-05-10",
            "--codex-home",
            str(codex_home),
            "--lang",
            "zh",
        )
        self.assertEqual(code, 0, err)
        self.assertIn("Codex 本地日志用量报告", report)
        self.assertIn("220", report)

        code, out, err = self.run_cli(
            "codex",
            "chart",
            "--date",
            "2026-05-10",
            "--codex-home",
            str(codex_home),
            "--output",
            "chart.html",
            "--lang",
            "en",
        )
        self.assertEqual(code, 0, err)
        self.assertIn("Wrote Codex usage chart to chart.html", out)
        chart = Path("chart.html").read_text(encoding="utf-8")
        self.assertIn("Codex Usage Chart", chart)
        self.assertIn("<svg", chart)
        self.assertIn("Cached Input", chart)
        self.assertIn("220", chart)

    def test_auto_language_uses_locale(self):
        self.run_cli("init")
        old_env = {key: os.environ.get(key) for key in ("LC_ALL", "LC_MESSAGES", "LANGUAGE", "LANG")}
        try:
            for key in old_env:
                os.environ.pop(key, None)
            os.environ["LANG"] = "zh_CN.UTF-8"
            code, out, err = self.run_cli("report", "--lang", "auto")
        finally:
            for key, value in old_env.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
        self.assertEqual(code, 0, err)
        self.assertIn("已记录的 Codex 用量估算报告", out)
        self.assertIn("没有匹配的记录", out)


if __name__ == "__main__":
    unittest.main()


def token_count_event(
    timestamp,
    input_tokens,
    cached_input_tokens,
    output_tokens,
    reasoning_output_tokens,
    total_tokens,
    primary,
    secondary,
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

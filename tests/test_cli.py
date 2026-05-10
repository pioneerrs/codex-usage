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

        code, out, err = self.run_cli("report", "--group", "quick-chat")
        self.assertEqual(code, 0, err)
        self.assertIn("quick-chat", out)
        self.assertIn("0.2%", out)
        self.assertIn("All token values are estimated", out)
        self.assertIn("所有 token 数值均基于本地可见文本估算", out)

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


if __name__ == "__main__":
    unittest.main()

